"""Roll N1-N3 into one long table, and adjust for multiplicity within the N family alone.

N1-N3 are a new Benjamini-Hochberg family.  They are **not** pooled with the 21-trajectory,
15-orientation, A1-A5 or B1-B4 families: pooling would change *q* values that are already
in the manuscript, and the N steps ask a different question of the same cached scores.  The
family size is recorded rather than left implicit.

Only formal tests enter the family.  N3 produces intervals rather than tests and contributes
no *p*, so it appears in the long table with an empty ``bh_family`` and does not inflate the
denominator.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib_n import HERE, bh_adjust, df_to_md, write_manifest  # noqa: E402

OUT = HERE / "collect_results"


def _row(analysis, quantity, value, lo=np.nan, hi=np.nan, p=np.nan, *, family="all",
         family_label="All", cohort="all", cohort_label="All", unit="", note="") -> dict:
    return {
        "analysis": analysis,
        "quantity": quantity,
        "family": family,
        "family_label": family_label,
        "cohort": cohort,
        "cohort_label": cohort_label,
        "value": value,
        "ci_lo": lo,
        "ci_hi": hi,
        "p_value": p,
        "unit": unit,
        "note": note,
    }


def _n1() -> list[dict]:
    frame = pd.read_csv(HERE / "n1_uniform_placement" / "n1_uniform_placement.csv")
    rows = []
    for r in frame.itertuples():
        rows.append(
            _row("N1", "observed_ratio_median", r.observed_ratio_median,
                 r.observed_ratio_ci_lo, r.observed_ratio_ci_hi,
                 family=r.family, family_label=r.family_label,
                 cohort=r.cohort, cohort_label=r.cohort_label, unit="ratio")
        )
        rows.append(
            _row("N1", "excess_over_uniform_null", r.excess_ratio,
                 p=r.p_value, family=r.family, family_label=r.family_label,
                 cohort=r.cohort, cohort_label=r.cohort_label, unit="ratio",
                 note="observed median ratio minus uniform-placement null")
        )
    return rows


def _n2() -> list[dict]:
    frame = pd.read_csv(HERE / "n2_score_shuffle" / "n2_score_shuffle.csv")
    rows = []
    for r in frame.itertuples():
        rows.append(
            _row("N2", f"excess_ratio_vs_shuffle_{r.variant}", r.excess_ratio,
                 p=r.p_ratio, family=r.family, family_label=r.family_label,
                 cohort=r.cohort, cohort_label=r.cohort_label, unit="ratio",
                 note=f"observed minus cross-case shuffle null ({r.variant})")
        )
        rows.append(
            _row("N2", f"excess_spearman_vs_shuffle_{r.variant}", r.excess_spearman,
                 p=r.p_spearman, family=r.family, family_label=r.family_label,
                 cohort=r.cohort, cohort_label=r.cohort_label, unit="rho",
                 note=f"observed minus cross-case shuffle null ({r.variant})")
        )
        rows.append(
            _row("N2", f"null_ratio_mean_{r.variant}", r.null_ratio_mean,
                 r.null_ratio_ci_lo, r.null_ratio_ci_hi,
                 family=r.family, family_label=r.family_label,
                 cohort=r.cohort, cohort_label=r.cohort_label, unit="ratio")
        )
        rows.append(
            _row("N2", f"null_spearman_mean_{r.variant}", r.null_spearman_mean,
                 r.null_spearman_ci_lo, r.null_spearman_ci_hi,
                 family=r.family, family_label=r.family_label,
                 cohort=r.cohort, cohort_label=r.cohort_label, unit="rho")
        )
    return rows


def _n3() -> list[dict]:
    summary = pd.read_csv(HERE / "n3_stratified" / "n3_summary.csv")
    strata = pd.read_csv(HERE / "n3_stratified" / "n3_strata.csv")
    rows = []
    for r in summary.itertuples():
        rows.append(
            _row("N3", "lead_gradient_q1_to_q5", r.lead_gradient_min,
                 r.lead_gradient_ci_lo, r.lead_gradient_ci_hi,
                 family=r.family, family_label=r.family_label,
                 cohort=r.cohort, cohort_label=r.cohort_label, unit="minutes",
                 note=f"{r.n_bands} realised bands; censored={r.censored}")
        )
        rows.append(
            _row("N3", "lead_min_per_window_min", r.lead_per_window_minute,
                 r.lead_per_window_ci_lo, r.lead_per_window_ci_hi,
                 family=r.family, family_label=r.family_label,
                 cohort=r.cohort, cohort_label=r.cohort_label, unit="ratio")
        )
    for r in strata.itertuples():
        rows.append(
            _row("N3", f"lead_median_q{r.stratum}", r.lead_median, r.lead_ci_lo, r.lead_ci_hi,
                 family=r.family, family_label=r.family_label,
                 cohort=r.cohort, cohort_label=r.cohort_label, unit="minutes",
                 note=f"n={r.n_cases}, window median {r.window_median:.0f} min")
        )
    return rows


def _n4() -> list[dict]:
    """Detection rate by band. Intervals only -- no test, so the BH family of 75 is unchanged."""
    summary = pd.read_csv(HERE / "n4_band_detection" / "n4_detection_summary.csv")
    strata = pd.read_csv(HERE / "n4_band_detection" / "n4_band_detection.csv")
    rows = []
    for r in summary.itertuples():
        rows.append(
            _row("N4", "detection_gradient_lowest_to_highest_band", r.detection_gradient,
                 r.detection_gradient_ci_lo, r.detection_gradient_ci_hi,
                 family=r.family, family_label=r.family_label,
                 cohort=r.cohort, cohort_label=r.cohort_label, unit="proportion",
                 note=(f"{r.n_bands} bands cut on all {r.n_event_cases} event cases; "
                       "negative means longer-observed cases are detected less often"))
        )
    for r in strata.itertuples():
        rows.append(
            _row("N4", f"detection_rate_band{r.stratum}", r.detection_rate,
                 r.detection_ci_lo, r.detection_ci_hi,
                 family=r.family, family_label=r.family_label,
                 cohort=r.cohort, cohort_label=r.cohort_label, unit="proportion",
                 note=(f"{r.n_detected} of {r.n_event_cases} event cases, "
                       f"window median {r.window_median:.0f} min"))
        )
    return rows


def _n5() -> list[dict]:
    """Replacement estimands. Intervals only, for the same reason as ``_n4``."""
    horizons = pd.read_csv(HERE / "n5_time_to_alert" / "n5_fixed_horizon.csv")
    summary = pd.read_csv(HERE / "n5_time_to_alert" / "n5_time_to_alert.csv")
    rows = []
    for r in horizons.itertuples():
        rows.append(
            _row("N5", f"fixed_horizon_detection_{r.horizon_min}min",
                 r.fixed_horizon_detection, r.fixed_horizon_ci_lo, r.fixed_horizon_ci_hi,
                 family=r.family, family_label=r.family_label,
                 cohort=r.cohort, cohort_label=r.cohort_label, unit="proportion",
                 note=(f"{r.n_detected_at_least_horizon} of "
                       f"{r.n_observed_at_least_horizon} event cases observed "
                       f"at least {r.horizon_min} min"))
        )
    for r in summary.itertuples():
        rows.append(
            _row("N5", "lead_median_fully_observed", r.lead_median_fully_observed,
                 r.lead_median_fully_observed_ci_lo, r.lead_median_fully_observed_ci_hi,
                 family=r.family, family_label=r.family_label,
                 cohort=r.cohort, cohort_label=r.cohort_label, unit="minutes",
                 note=(f"{r.n_fully_observed_detected} detected of {r.n_fully_observed} "
                       "event cases observed for the whole 60-minute window"))
        )
        rows.append(
            _row("N5", "unalerted_by_elapsed_min1", r.km_unalerted_by_min1,
                 r.km_unalerted_by_min1_ci_lo, r.km_unalerted_by_min1_ci_hi,
                 family=r.family, family_label=r.family_label,
                 cohort=r.cohort, cohort_label=r.cohort_label, unit="proportion",
                 note="Kaplan-Meier survival, censored at each case's own observation window")
        )
    return rows


def run() -> tuple[pd.DataFrame, int]:
    OUT.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(_n1() + _n2() + _n3() + _n4() + _n5())
    frame["bh_family"] = np.where(frame["p_value"].notna(), "N1-N3", "")
    members = frame["bh_family"] == "N1-N3"
    frame["q_value"] = np.nan
    frame.loc[members, "q_value"] = bh_adjust(frame.loc[members, "p_value"])
    frame["significant_q05"] = frame["q_value"] < 0.05
    frame["bh_family_size"] = np.where(members, int(members.sum()), np.nan)
    frame.to_csv(OUT / "n_results_long.csv", index=False)
    frame.to_json(OUT / "n_results_long.json", orient="records", indent=2)
    return frame, int(members.sum())


def _write_report(frame: pd.DataFrame, family_size: int) -> None:
    tests = frame[frame["bh_family"] == "N1-N3"]
    significant = int(tests["significant_q05"].sum())
    lines = [
        "# N1-N3 — collected results",
        "",
        f"{len(frame):,} reported quantities, of which **{family_size} are formal tests**.",
        "",
        "## Multiplicity",
        "",
        f"Benjamini-Hochberg across the {family_size} formal tests in N1-N3, adjusted within "
        "this family alone. **Not pooled** with the 21-trajectory, 15-orientation, A1-A5 or "
        "B1-B4 families: pooling would move *q* values already in the manuscript, and the N "
        "steps ask a different question of the same cached scores. "
        f"**{significant} of {family_size}** are significant at *q* < 0.05.",
        "",
        "N3 produces intervals rather than tests and contributes no *p*, so it does not "
        "enter the family.",
        "",
        "## Counts by analysis",
        "",
        df_to_md(
            frame.groupby("analysis")
            .agg(quantities=("quantity", "size"), tests=("p_value", "count"))
            .reset_index()
        ),
        "",
    ]
    (OUT / "collect_results.md").write_text("\n".join(lines))


def main() -> None:
    frame, family_size = run()
    _write_report(frame, family_size)
    write_manifest(
        OUT,
        "n_collect_results",
        [],
        extra={"n_quantities": int(len(frame)), "bh_family_size": family_size},
        hash_inputs=False,
    )
    tests = frame[frame["bh_family"] == "N1-N3"]
    print(
        f"collect_results: {len(frame)} quantities, {family_size} tests, "
        f"{int(tests['significant_q05'].sum())} significant at q<0.05"
    )


if __name__ == "__main__":
    main()
