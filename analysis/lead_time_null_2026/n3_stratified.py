"""N3 — median lead in minutes, inside quintiles of observed window length.

This is the most legible form of the finding and it leads the paper's Results.

The ratio ``lead / observed_window`` is a compact summary but it invites the reply that a
ratio of a quantity to its own bound must look like something.  Stratifying removes the
ratio from the argument.  Inside a quintile of observed window length the window is nearly
constant, so the median **absolute lead in minutes** is directly comparable across cases,
and the question becomes simple: does the number of minutes of warning depend on how long
the patient happened to be watched?

* If median lead in minutes is flat across quintiles, the ratio is arithmetic and the metric
  is reporting something about the model.
* If median lead in minutes rises with the quintile, the metric is reporting observation
  length, and it does so in units a reader already interprets as warning time.

Quintile cut points are computed **within cell**, because the cohorts' window-length
distributions differ so much that a pooled cut would leave whole cells in one bin -- the
transformer on VitalDB has a median observed window of 20 minutes, XGBoost on MOVER (SIS)
of 60.  Where the window is censored at the 60-minute alert-window cap the upper quintiles
collapse onto a single value; the table reports the realised edges and the count in each
bin so a collapsed quintile is visible rather than hidden, and cells with fewer than three
distinct edges are flagged rather than dropped.

Post-hoc on cached scores.  Nothing is retrained, refitted or re-scored.
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
    bootstrap_p_two_sided,
    cells,
    cluster_bootstrap,
    df_to_md,
    headline_cuts,
    per_case_leads,
    percentile_ci,
    weighted_median,
    weighted_spearman,
    write_manifest,
)

OUT = Path(__file__).resolve().parent / "n3_stratified"

#: A cell needs at least this many distinct quintile edges before the strata are read as
#: five separate bands rather than as a censored distribution.
MIN_DISTINCT_EDGES = 3


def _cell(family: str, cohort: str, cut: float) -> tuple[list[dict], dict]:
    detected = per_case_leads(family, cohort, cut)
    observed = detected["observed_min"].to_numpy(float)
    lead = detected["lead"].to_numpy(float)
    ratio = detected["ratio"].to_numpy(float)

    quantiles = np.linspace(0, 1, N_STRATA + 1)
    edges = np.quantile(observed, quantiles)
    distinct = np.unique(edges)
    # ``duplicates="drop"`` collapses censored upper quintiles instead of raising.
    stratum = pd.qcut(observed, N_STRATA, labels=False, duplicates="drop")
    n_bands = int(pd.Series(stratum).nunique())

    codes, weights = cluster_bootstrap(detected, "n3", family, cohort)

    rows: list[dict] = []
    # The gradient is a difference of two band medians, so its interval needs the *draws*, not
    # the point estimates. The weight matrix is already drawn once per cell and reused across
    # bands, which is exactly what makes the difference below a paired difference; the draws
    # were simply being thrown away.
    band_lead_draws: list[np.ndarray] = []
    for band in range(n_bands):
        keep = stratum == band
        if keep.sum() < 3:
            continue
        band_lead = lead[keep]
        band_ratio = ratio[keep]
        band_observed = observed[keep]
        lead_draws = np.empty(N_BOOTSTRAP_PATIENT)
        ratio_draws = np.empty(N_BOOTSTRAP_PATIENT)
        for replicate in range(N_BOOTSTRAP_PATIENT):
            w = weights[replicate][codes][keep]
            lead_draws[replicate] = weighted_median(band_lead, w)
            ratio_draws[replicate] = weighted_median(band_ratio, w)
        row = {
            "family": family,
            "family_label": FAMILY_LABELS[family],
            "cohort": cohort,
            "cohort_label": COHORT_LABELS[cohort],
            "stratum": band + 1,
            "n_bands": n_bands,
            "n_cases": int(keep.sum()),
            "window_min": float(band_observed.min()),
            "window_max": float(band_observed.max()),
            "window_median": float(np.median(band_observed)),
            "lead_median": float(np.median(band_lead)),
            "ratio_median": float(np.median(band_ratio)),
        }
        row["lead_ci_lo"], row["lead_ci_hi"] = percentile_ci(lead_draws)
        row["ratio_ci_lo"], row["ratio_ci_hi"] = percentile_ci(ratio_draws)
        rows.append(row)
        band_lead_draws.append(lead_draws)

    # The across-quintile gradient, which is what the table is read for.
    band_medians = pd.DataFrame(rows)
    if len(band_medians) >= 2:
        gradient = float(
            band_medians["lead_median"].iloc[-1] - band_medians["lead_median"].iloc[0]
        )
        window_span = float(
            band_medians["window_median"].iloc[-1] - band_medians["window_median"].iloc[0]
        )
        # ``window_span`` is held fixed at its full-sample value rather than resampled. It is a
        # property of the band design, not an estimate, and letting it vary would put a random
        # denominator under the ratio and make the interval unreadable. The band edges are held
        # fixed for the same reason, so every replicate compares the same two bands.
        gradient_draws = band_lead_draws[-1] - band_lead_draws[0]
        gradient_ci = percentile_ci(gradient_draws)
        gradient_p = bootstrap_p_two_sided(gradient_draws, 0.0)
        per_window_ci = (
            tuple(bound / window_span for bound in gradient_ci)
            if window_span
            else (float("nan"), float("nan"))
        )
    else:
        gradient = float("nan")
        window_span = float("nan")
        gradient_ci = (float("nan"), float("nan"))
        per_window_ci = (float("nan"), float("nan"))
        gradient_p = float("nan")

    summary = {
        "family": family,
        "family_label": FAMILY_LABELS[family],
        "cohort": cohort,
        "cohort_label": COHORT_LABELS[cohort],
        "n_detected": int(len(detected)),
        "n_bands": n_bands,
        "n_distinct_edges": int(distinct.size),
        "censored": bool(distinct.size < MIN_DISTINCT_EDGES),
        "lead_median_lowest_band": float(band_medians["lead_median"].iloc[0]),
        "lead_median_highest_band": float(band_medians["lead_median"].iloc[-1]),
        "lead_gradient_min": gradient,
        "lead_gradient_ci_lo": gradient_ci[0],
        "lead_gradient_ci_hi": gradient_ci[1],
        "lead_gradient_p": gradient_p,
        "window_median_lowest_band": float(band_medians["window_median"].iloc[0]),
        "window_median_highest_band": float(band_medians["window_median"].iloc[-1]),
        "window_span_min": window_span,
        "lead_per_window_minute": gradient / window_span if window_span else float("nan"),
        "lead_per_window_ci_lo": per_window_ci[0],
        "lead_per_window_ci_hi": per_window_ci[1],
        "spearman_lead_vs_window": float(
            weighted_spearman(observed, lead, np.ones(len(detected), int))
        ),
    }
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
    strata_frame = pd.DataFrame(strata)
    summary_frame = pd.DataFrame(summaries)
    strata_frame.to_csv(OUT / "n3_strata.csv", index=False)
    summary_frame.to_csv(OUT / "n3_summary.csv", index=False)
    return strata_frame, summary_frame


def _write_report(strata: pd.DataFrame, summary: pd.DataFrame) -> None:
    lo, hi = summary["lead_gradient_min"].min(), summary["lead_gradient_min"].max()
    rising = int((summary["lead_gradient_min"] > 0).sum())
    censored = int(summary["censored"].sum())

    headline = strata[strata["family"] == "transformer"]
    headline_display = pd.DataFrame(
        {
            "Cohort": headline["cohort_label"],
            "Quintile": headline["stratum"],
            "n": headline["n_cases"],
            "Window, min (median)": headline["window_median"].map("{:.0f}".format),
            "Median lead, min (95% CI)": [
                f"{r.lead_median:.0f} ({r.lead_ci_lo:.0f}–{r.lead_ci_hi:.0f})"
                for r in headline.itertuples()
            ],
            "Median ratio (95% CI)": [
                f"{r.ratio_median:.2f} ({r.ratio_ci_lo:.2f}–{r.ratio_ci_hi:.2f})"
                for r in headline.itertuples()
            ],
        }
    )

    gradient_display = pd.DataFrame(
        {
            "Model": summary["family_label"],
            "Cohort": summary["cohort_label"],
            "Bands": summary["n_bands"],
            "Window Q1→Q5, min": [
                f"{r.window_median_lowest_band:.0f} → {r.window_median_highest_band:.0f}"
                for r in summary.itertuples()
            ],
            "Lead Q1→Q5, min": [
                f"{r.lead_median_lowest_band:.0f} → {r.lead_median_highest_band:.0f}"
                for r in summary.itertuples()
            ],
            "Gradient, min": summary["lead_gradient_min"].map("{:+.0f}".format),
            "Lead min per window min": summary["lead_per_window_minute"].map("{:.2f}".format),
            "Censored": np.where(summary["censored"], "yes", ""),
        }
    )

    lines = [
        "# N3 — median lead inside quintiles of observed window length",
        "",
        "Stratifying takes the ratio out of the argument. Inside a quintile the observed "
        "window is nearly constant, so the median **absolute lead in minutes** is directly "
        "comparable, and the question is whether minutes of warning depend on how long the "
        "patient happened to be watched.",
        "",
        "## Headline",
        "",
        f"Median lead rises from the shortest to the longest quintile in **{rising} of 15** "
        f"cells, by **{lo:+.0f} to {hi:+.0f} minutes**. The reported median lead is not a "
        "constant amount of warning that happens to be measured in a window; it moves with "
        "the window.",
        "",
        f"{censored} of 15 cells are censored at the 60-minute alert-window cap and are "
        "flagged in the gradient table.",
        "",
        "## Transformer, all three cohorts",
        "",
        df_to_md(headline_display),
        "",
        "## Gradient across all fifteen cells",
        "",
        "`Lead min per window min` is the change in median lead divided by the change in "
        "median window between the lowest and highest quintile. A value near 1 means an "
        "extra minute of observation buys an extra minute of reported lead.",
        "",
        df_to_md(gradient_display),
        "",
        "## Method",
        "",
        "Quintile cut points are computed within cell, because the cohorts' window-length "
        "distributions differ too much for a pooled cut to be meaningful. Where the window "
        "is censored at the 60-minute cap the upper quintiles collapse; `pd.qcut` drops the "
        "duplicate edges and the realised band count is reported rather than assumed. "
        f"Cells with fewer than {MIN_DISTINCT_EDGES} distinct edges are flagged as censored. "
        f"Every median carries a {N_BOOTSTRAP_PATIENT:,}-replicate cluster bootstrap, "
        "clustering on patient for MOVER (EPIC) and VitalDB and on case for MOVER (SIS); "
        "one weight matrix is drawn per cell and reused across bands, so band-to-band "
        "differences are paired.",
        "",
    ]
    (OUT / "n3_stratified.md").write_text("\n".join(lines))


def main() -> None:
    strata, summary = run()
    _write_report(strata, summary)
    write_manifest(
        OUT,
        "n3_stratified",
        [],
        extra={
            "n_cells": int(len(summary)),
            "n_strata": N_STRATA,
            "n_bootstrap": N_BOOTSTRAP_PATIENT,
            "n_censored_cells": int(summary["censored"].sum()),
        },
        hash_inputs=False,
    )
    print(
        f"N3: lead gradient Q1→Q5 {summary['lead_gradient_min'].min():+.0f} to "
        f"{summary['lead_gradient_min'].max():+.0f} min; "
        f"{int((summary['lead_gradient_min'] > 0).sum())}/15 cells rising"
    )


if __name__ == "__main__":
    main()
