"""N5 - replacement estimands: a statistic that does not inherit the window's length.

Sections 3 and 4 diagnose the median alert lead time and Section 5 shows that two natural
repairs fail.  Diagnosis without a replacement invites the obvious reviewer question: why not
condition on window length, or treat the first alert as a time-to-event with the observation
window as administrative censoring?  This step computes three answers so the paper can propose
an estimand rather than only a disclosure.

**1. Fixed-horizon detection rate.**  Among event cases observed for at least X minutes before
onset, the share whose first alert came at least X minutes before onset.  Numerator and
denominator move together, so the statistic cannot be inflated by a cohort that happens to be
watched for longer, and it answers the question a clinician actually asks -- "how often does
this thing give me X minutes?" -- in a form that a reader cannot mistake for anything else.

**2. Median lead restricted to the full alert window.**  The same median the paper criticises,
computed only on cases observed for the whole 60 minutes, so the window is a constant rather
than a covariate.  This is the top band of Table 1 read as an estimand instead of a stratum.

**3. Kaplan-Meier time to first alert**, on elapsed monitoring minutes, with each case's own
observation window as administrative censoring and a case that never alerts censored at the end
of its window.

The third is reported with a caveat that is not a formality: **the censoring here is not
independent of the event.**  For an event case the observable run-up *is* its time to onset, so
a short window is not a case that was watched briefly by accident -- it is an early-onset
event, and Appendix A.7's balance table shows short- and long-run-up cases are different
patients.  The curve is therefore a description of what the rule did under the observation this
cohort supplied, not an estimate of when the alert would have fired under longer monitoring.
Reported because the framing will be raised, and reported with its limit for the same reason.

Nothing here retrains, re-scores or reselects.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib_n import (  # noqa: E402
    ALERT_WINDOW_MIN,
    COHORT_LABELS,
    FAMILY_LABELS,
    N_BOOTSTRAP_PATIENT,
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

OUT = Path(__file__).resolve().parent / "n5_time_to_alert"

#: Horizons in minutes before onset.  60 is the alert window itself, so the last column is the
#: share of fully observed cases that alerted at the very first opportunity.
HORIZONS = (5, 10, 15, 20, 30, 45, 60)

#: Elapsed-minute marks at which the survival curve is reported.
SURVIVAL_MARKS = (1, 5, 10, 20, 30)


def _weighted_km(time: np.ndarray, event: np.ndarray, w: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Kaplan-Meier survival on integer-multiplicity weights.

    Returns ``(times, survival)`` over the distinct event times only.  ``time`` is elapsed
    monitoring minutes to the first alert for a case that alerts, and the length of its own
    observation window for one that does not; ``event`` marks the former.
    """
    order = np.argsort(time, kind="stable")
    time, event, w = time[order], event[order], w[order]
    distinct = np.unique(time[event & (w > 0)])
    survival = np.empty(distinct.size)
    running = 1.0
    for index, moment in enumerate(distinct):
        at_risk = float(w[time >= moment].sum())
        failures = float(w[event & (time == moment)].sum())
        if at_risk > 0:
            running *= 1.0 - failures / at_risk
        survival[index] = running
    return distinct, survival


def _survival_at(times: np.ndarray, survival: np.ndarray, mark: float) -> float:
    """``S(mark)``, the survival after every event at or before ``mark``."""
    reached = survival[times <= mark]
    return float(reached[-1]) if reached.size else 1.0


def _cell(family: str, cohort: str, cut: float) -> tuple[list[dict], dict]:
    per_case = per_case_all(family, cohort, cut)
    events = per_case[(per_case["label"] == 1) & (per_case["observed_min"] > 0)].copy()
    events = events.reset_index(drop=True)

    observed = events["observed_min"].to_numpy(float)
    lead = events["lead"].to_numpy(float)
    alerted = events["lead"].notna().to_numpy()
    codes, weights = cluster_bootstrap(events, "n5", family, cohort)

    # --- 1. fixed-horizon detection rate ---
    horizon_rows: list[dict] = []
    for horizon in HORIZONS:
        at_risk = observed >= horizon
        if at_risk.sum() < 3:
            continue
        # ``lead`` is the earliest crossing, so ``lead >= horizon`` is exactly "first alert at
        # least ``horizon`` minutes before onset".  NaN compares false, which is the miss.
        in_time = at_risk & alerted & (lead >= horizon)
        draws = np.empty(N_BOOTSTRAP_PATIENT)
        for replicate in range(N_BOOTSTRAP_PATIENT):
            w = weights[replicate][codes]
            draws[replicate] = weighted_fraction(in_time[at_risk], w[at_risk])
        row = {
            "family": family,
            "family_label": FAMILY_LABELS[family],
            "cohort": cohort,
            "cohort_label": COHORT_LABELS[cohort],
            "horizon_min": horizon,
            "n_observed_at_least_horizon": int(at_risk.sum()),
            "n_detected_at_least_horizon": int(in_time.sum()),
            "fixed_horizon_detection": float(in_time[at_risk].mean()),
        }
        row["fixed_horizon_ci_lo"], row["fixed_horizon_ci_hi"] = percentile_ci(draws)
        horizon_rows.append(row)

    # --- 2. median lead on the fully observed cases only ---
    full = observed >= float(ALERT_WINDOW_MIN)
    full_detected = full & alerted
    full_draws = np.empty(N_BOOTSTRAP_PATIENT)
    # --- 3. Kaplan-Meier time to first alert ---
    elapsed = np.where(alerted, observed - lead, observed)
    km_draws = {mark: np.empty(N_BOOTSTRAP_PATIENT) for mark in SURVIVAL_MARKS}
    for replicate in range(N_BOOTSTRAP_PATIENT):
        w = weights[replicate][codes]
        full_draws[replicate] = weighted_median(lead, np.where(full_detected, w, 0))
        times, survival = _weighted_km(elapsed, alerted, w)
        for mark in SURVIVAL_MARKS:
            km_draws[mark][replicate] = _survival_at(times, survival, mark)

    times, survival = _weighted_km(elapsed, alerted, np.ones(len(events), int))
    summary = {
        "family": family,
        "family_label": FAMILY_LABELS[family],
        "cohort": cohort,
        "cohort_label": COHORT_LABELS[cohort],
        "n_event_cases": int(len(events)),
        "n_fully_observed": int(full.sum()),
        "n_fully_observed_detected": int(full_detected.sum()),
        "detection_fully_observed": float(alerted[full].mean()) if full.any() else np.nan,
        "lead_median_fully_observed": (
            float(np.median(lead[full_detected])) if full_detected.any() else np.nan
        ),
    }
    summary["lead_median_fully_observed_ci_lo"], summary["lead_median_fully_observed_ci_hi"] = (
        percentile_ci(full_draws)
    )
    for mark in SURVIVAL_MARKS:
        summary[f"km_unalerted_by_min{mark}"] = _survival_at(times, survival, mark)
        lo, hi = percentile_ci(km_draws[mark])
        summary[f"km_unalerted_by_min{mark}_ci_lo"] = lo
        summary[f"km_unalerted_by_min{mark}_ci_hi"] = hi
    return horizon_rows, summary


def run() -> tuple[pd.DataFrame, pd.DataFrame]:
    OUT.mkdir(parents=True, exist_ok=True)
    cuts = headline_cuts()
    horizons: list[dict] = []
    summaries: list[dict] = []
    for family, cohort in cells():
        rows, summary = _cell(family, cohort, float(cuts[family]))
        horizons.extend(rows)
        summaries.append(summary)
        print(f"  n5 {family} / {cohort}", flush=True)

    horizon_frame = pd.DataFrame(horizons)
    summary_frame = pd.DataFrame(summaries)
    horizon_frame.to_csv(OUT / "n5_fixed_horizon.csv", index=False)
    summary_frame.to_csv(OUT / "n5_time_to_alert.csv", index=False)
    _write_report(horizon_frame, summary_frame)
    write_manifest(
        OUT,
        "n5_time_to_alert",
        [],
        extra={
            "n_bootstrap": N_BOOTSTRAP_PATIENT,
            "horizons_min": list(HORIZONS),
            "survival_marks_min": list(SURVIVAL_MARKS),
            "fixed_horizon_definition": (
                "among event cases with observed_min >= X, the share whose earliest crossing "
                "was at least X minutes before onset; numerator and denominator move together"
            ),
            "censoring": (
                "administrative, at each case's own observed_min; NOT independent of the event, "
                "because for an event case a short observable run-up is an early-onset event "
                "rather than missing data"
            ),
        },
    )
    return horizon_frame, summary_frame


def _write_report(horizons: pd.DataFrame, summary: pd.DataFrame) -> None:
    wide = horizons.pivot_table(
        index=["family_label", "cohort_label"], columns="horizon_min",
        values="fixed_horizon_detection",
    ).round(3)
    lines = [
        "# N5 - replacement estimands for the median alert lead time\n",
        "## 1. Fixed-horizon detection rate\n",
        "Among event cases observed for at least X minutes before onset, the share whose first "
        "alert came at least X minutes before onset. Numerator and denominator move together, "
        "so a cohort watched for longer cannot inflate it.\n",
        wide.to_markdown(),
        "",
        "## 2. Median lead on the fully observed cases, and time to first alert\n",
        "The window is a constant in the first column rather than a covariate. `Unalerted by` is "
        "the Kaplan-Meier survival at that elapsed monitoring minute, with each case censored at "
        "the end of its own window. The censoring is **not** independent of the event: a short "
        "run-up is an early-onset event, not a case watched briefly by accident.\n",
        df_to_md(
            pd.DataFrame(
                {
                    "Model": summary["family_label"],
                    "Cohort": summary["cohort_label"],
                    "Fully observed n": summary["n_fully_observed"],
                    "Detected": summary["detection_fully_observed"].map("{:.3f}".format),
                    "Median lead, min (95% CI)": [
                        f"{r.lead_median_fully_observed:.0f} "
                        f"({r.lead_median_fully_observed_ci_lo:.0f}–"
                        f"{r.lead_median_fully_observed_ci_hi:.0f})"
                        for r in summary.itertuples()
                    ],
                    "Unalerted by min 1": summary["km_unalerted_by_min1"].map("{:.3f}".format),
                    "Unalerted by min 10": summary["km_unalerted_by_min10"].map("{:.3f}".format),
                    "Unalerted by min 30": summary["km_unalerted_by_min30"].map("{:.3f}".format),
                }
            )
        ),
        "",
    ]
    (OUT / "n5_time_to_alert.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    horizons, summary = run()
    print("\nFixed-horizon detection rate (share of cases observed >= X detected >= X before onset):")
    print(
        horizons.pivot_table(
            index=["family", "cohort"], columns="horizon_min",
            values="fixed_horizon_detection",
        ).round(3).to_string()
    )
    print("\nRestricted to the full 60-minute window:")
    print(
        summary[["family", "cohort", "n_fully_observed", "detection_fully_observed",
                 "lead_median_fully_observed", "km_unalerted_by_min1"]]
        .round(3).to_string(index=False)
    )


if __name__ == "__main__":
    main()
