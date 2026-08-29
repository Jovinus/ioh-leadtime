"""N4 - is the band gradient partly survivorship? The detection rate the tables condition on.

Table 1 and Table A1 stratify **detected** event cases by how long they had been observed, and
report that the median lead rises with the stratum.  Detection is itself a function of window
length: a case watched for eight minutes has eight chances to cross a threshold and a case
watched for sixty has sixty.  Conditioning on detection is therefore a collider, and part of
the reported association is manufactured by the conditioning rather than measured through it.

The band ``n`` values already imply this -- 139, 111, 121 and 240 in MOVER (EPIC) test are not
the equal fifths that quintiles of a common population would give -- but the rate itself is
never stated anywhere in the paper.  This step states it.

**The band edges are cut on all event cases, not on the detected ones.**  N3 cuts quintiles of
``observed_min`` within the detected subset, which is the right choice for a statistic computed
on detected cases and the wrong one here: a within-band detection rate needs every event case
of that window length in its denominator, and edges cut on the detected subset are edges
selected on the outcome.  So this step re-cuts the bands on all event cases with a positive
observed window and reports the detection rate *and* the re-banded median lead on that one set
of edges, so the numerator and the denominator are never on different bands.  The consequence
is that the median leads here are close to N3's but not identical, and the band ``n`` values
are event-case counts rather than N3's detected counts.  Both differences are intended.

Nothing here retrains, re-scores or reselects: it reads the same cached per-minute scores at
the same transported threshold as every other step.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib_n import (  # noqa: E402
    COHORT_LABELS,
    FAMILY_LABELS,
    N_BOOTSTRAP_PATIENT,
    N_STRATA,
    cells,
    cluster_bootstrap,
    df_to_md,
    headline_cuts,
    per_case_all,
    percentile_ci,
    weighted_fraction,
    weighted_median,
    write_manifest,
)

OUT = Path(__file__).resolve().parent / "n4_band_detection"


def _cell(family: str, cohort: str, cut: float) -> tuple[list[dict], dict]:
    per_case = per_case_all(family, cohort, cut)
    events = per_case[(per_case["label"] == 1) & (per_case["observed_min"] > 0)].copy()
    events = events.reset_index(drop=True)

    observed = events["observed_min"].to_numpy(float)
    lead = events["lead"].to_numpy(float)
    detected = events["lead"].notna().to_numpy()

    stratum = pd.qcut(observed, N_STRATA, labels=False, duplicates="drop")
    n_bands = int(pd.Series(stratum).nunique())
    codes, weights = cluster_bootstrap(events, "n4", family, cohort)

    rows: list[dict] = []
    band_detection_draws: list[np.ndarray] = []
    for band in range(n_bands):
        keep = stratum == band
        if keep.sum() < 3:
            continue
        band_detected = detected[keep]
        band_observed = observed[keep]
        # Median lead is over the detected cases inside the band; the detection rate is over
        # every event case in it.  The two therefore have different denominators by design,
        # which is the whole point of the step.
        band_lead = lead[keep][band_detected]
        detection_draws = np.empty(N_BOOTSTRAP_PATIENT)
        lead_draws = np.empty(N_BOOTSTRAP_PATIENT)
        for replicate in range(N_BOOTSTRAP_PATIENT):
            w = weights[replicate][codes][keep]
            detection_draws[replicate] = weighted_fraction(band_detected, w)
            lead_draws[replicate] = weighted_median(
                lead[keep], np.where(band_detected, w, 0)
            )
        row = {
            "family": family,
            "family_label": FAMILY_LABELS[family],
            "cohort": cohort,
            "cohort_label": COHORT_LABELS[cohort],
            "stratum": band + 1,
            "n_bands": n_bands,
            "n_event_cases": int(keep.sum()),
            "n_detected": int(band_detected.sum()),
            "window_min": float(band_observed.min()),
            "window_max": float(band_observed.max()),
            "window_median": float(np.median(band_observed)),
            "detection_rate": float(band_detected.mean()),
            "lead_median": float(np.median(band_lead)) if band_lead.size else np.nan,
        }
        row["detection_ci_lo"], row["detection_ci_hi"] = percentile_ci(detection_draws)
        row["lead_ci_lo"], row["lead_ci_hi"] = percentile_ci(lead_draws)
        rows.append(row)
        band_detection_draws.append(detection_draws)

    bands = pd.DataFrame(rows)
    gradient = float(
        bands["detection_rate"].iloc[-1] - bands["detection_rate"].iloc[0]
    )
    gradient_draws = band_detection_draws[-1] - band_detection_draws[0]
    summary = {
        "family": family,
        "family_label": FAMILY_LABELS[family],
        "cohort": cohort,
        "cohort_label": COHORT_LABELS[cohort],
        "n_event_cases": int(len(events)),
        "n_detected": int(detected.sum()),
        "n_bands": n_bands,
        "detection_rate_overall": float(detected.mean()),
        "detection_lowest_band": float(bands["detection_rate"].iloc[0]),
        "detection_highest_band": float(bands["detection_rate"].iloc[-1]),
        "detection_gradient": gradient,
        "window_median_lowest_band": float(bands["window_median"].iloc[0]),
        "window_median_highest_band": float(bands["window_median"].iloc[-1]),
    }
    summary["detection_gradient_ci_lo"], summary["detection_gradient_ci_hi"] = percentile_ci(
        gradient_draws
    )
    return rows, summary


def run() -> tuple[pd.DataFrame, pd.DataFrame]:
    OUT.mkdir(parents=True, exist_ok=True)
    cuts = headline_cuts()
    strata: list[dict] = []
    summaries: list[dict] = []
    for family, cohort in cells():
        rows, summary = _cell(family, cohort, float(cuts[family]))
        strata.extend(rows)
        summaries.append(summary)
        print(f"  n4 {family} / {cohort}", flush=True)

    strata_frame = pd.DataFrame(strata)
    summary_frame = pd.DataFrame(summaries)
    strata_frame.to_csv(OUT / "n4_band_detection.csv", index=False)
    summary_frame.to_csv(OUT / "n4_detection_summary.csv", index=False)
    _write_report(strata_frame, summary_frame)
    write_manifest(
        OUT,
        "n4_band_detection",
        [],
        extra={
            "n_bootstrap": N_BOOTSTRAP_PATIENT,
            "n_strata_requested": N_STRATA,
            "band_edges": (
                "quantiles of observed_min over ALL event cases with observed_min > 0, not "
                "over the detected subset N3 cuts on; a within-band detection rate needs "
                "every event case of that window length in its denominator"
            ),
            "why": (
                "Table 1 and Table A1 condition on detected cases, and detection probability "
                "rises with window length, so the conditioning is a collider; this step "
                "reports the rate the tables condition on"
            ),
        },
    )
    return strata_frame, summary_frame


def _write_report(strata: pd.DataFrame, summary: pd.DataFrame) -> None:
    lines = [
        "# N4 - detection rate by band of observed pre-onset window\n",
        "Bands are quantiles of the observed window over **all** event cases, so the detection "
        "rate has every event case of that window length in its denominator. N3's bands are cut "
        "on the detected subset instead, which is correct for a statistic computed on detected "
        "cases and wrong for this one, so the median leads below are close to N3's without being "
        "identical.\n",
        "## Detection rate, lowest to highest band\n",
        df_to_md(
            pd.DataFrame(
                {
                    "Model": summary["family_label"],
                    "Cohort": summary["cohort_label"],
                    "Event cases": summary["n_event_cases"],
                    "Bands": summary["n_bands"],
                    "Overall": summary["detection_rate_overall"].map("{:.3f}".format),
                    "Lowest band": summary["detection_lowest_band"].map("{:.3f}".format),
                    "Highest band": summary["detection_highest_band"].map("{:.3f}".format),
                    "Gradient (95% CI)": [
                        f"{r.detection_gradient:+.3f} "
                        f"({r.detection_gradient_ci_lo:+.3f}–{r.detection_gradient_ci_hi:+.3f})"
                        for r in summary.itertuples()
                    ],
                }
            )
        ),
        "",
        "## Every band\n",
        df_to_md(
            pd.DataFrame(
                {
                    "Model": strata["family_label"],
                    "Cohort": strata["cohort_label"],
                    "Band": strata["stratum"],
                    "Event cases": strata["n_event_cases"],
                    "Detected": strata["n_detected"],
                    "Window median, min": strata["window_median"].map("{:.0f}".format),
                    "Detection rate (95% CI)": [
                        f"{r.detection_rate:.3f} ({r.detection_ci_lo:.3f}–{r.detection_ci_hi:.3f})"
                        for r in strata.itertuples()
                    ],
                    "Median lead, min (95% CI)": [
                        f"{r.lead_median:.0f} ({r.lead_ci_lo:.0f}–{r.lead_ci_hi:.0f})"
                        for r in strata.itertuples()
                    ],
                }
            )
        ),
        "",
    ]
    (OUT / "n4_band_detection.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    _, summary = run()
    print("\nDetection rate, lowest vs highest band of observed window:")
    print(
        summary[
            ["family", "cohort", "n_event_cases", "detection_lowest_band",
             "detection_highest_band", "detection_gradient",
             "detection_gradient_ci_lo", "detection_gradient_ci_hi"]
        ].round(3).to_string(index=False)
    )


if __name__ == "__main__":
    main()
