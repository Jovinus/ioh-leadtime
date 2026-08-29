"""One machine-readable file holding every new B1-B4 number, its interval, and where it could go.

Three jobs.

**Collect.** Every estimate the four analyses produce, long, one row per number, with the
analysis that produced it, the family and cohort it belongs to, its interval, and its
candidate destination. Nothing in the write-up should be transcribed from a REPORT.md when
this file exists.

**Adjust.** B1-B4 are a new multiplicity family. Benjamini-Hochberg control is applied
across the formal tests in B alone and the family size is recorded. They are deliberately
not pooled with the 21-trajectory family, the 15-orientation family, or the A1-A5 families:
pooling would change published q values, and those are fixed.

**Flag.** The seed discrepancy is written into the output rather than harmonised. A previously
published analysis states 20260706 as its default resampling base and records 20260729 for the
episode-metric family, which it uses throughout. B1-B4 use 20260706 with distinct offsets. That
is three bases coexisting, documented in two places and stated as one in that publication's
methods, and it is reported here as an outstanding inconsistency, not fixed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib_b import (  # noqa: E402
    BOOTSTRAP_SEED,
    COHORT_LABELS,
    FAMILY_LABELS,
    HEADLINE_TARGET,
    HERE,
    SEED_OFFSETS,
    bh_adjust,
    df_to_md,
    write_manifest,
)

OUT = HERE / "collect_results"

#: Candidate destinations.  A label, not a decision: the output configuration is chosen by
#: the author after reading the decision package, and nothing here applies one.
MAIN = "main text candidate"
SUPP = "supplement"
WORKSHOP = "workshop candidate"


def _row(analysis, quantity, value, lo=np.nan, hi=np.nan, p=np.nan, *, family="all",
         cohort="all", unit="", destination=SUPP, note="") -> dict:
    return {
        "analysis": analysis,
        "quantity": quantity,
        "family": family,
        "family_label": FAMILY_LABELS.get(family, family),
        "cohort": cohort,
        "cohort_label": COHORT_LABELS.get(cohort, cohort),
        "value": value,
        "ci_lo": lo,
        "ci_hi": hi,
        "p_value": p,
        "unit": unit,
        "destination": destination,
        "note": note,
    }


def _b1() -> list[dict]:
    frame = pd.read_csv(HERE / "b1_prevalent_incident" / "b1_summary.csv")
    head = frame[
        (frame["target_sensitivity"] == HEADLINE_TARGET)
        & (frame["first_minute_definition"] == "window")
    ]
    rows: list[dict] = []
    for record in head.itertuples():
        key = {"family": record.family, "cohort": record.cohort}
        rows += [
            _row("B1", "prop_prevalent", record.prop_prevalent, record.prop_prevalent_ci_lo,
                 record.prop_prevalent_ci_hi, **key, unit="proportion", destination=MAIN,
                 note="detected event alerts already above threshold at the window's first minute"),
            _row("B1", "prop_warmup", record.prop_warmup, record.prop_warmup_ci_lo,
                 record.prop_warmup_ci_hi, **key, unit="proportion", destination=MAIN,
                 note="incident crossings within the first 5 minutes of monitoring"),
            _row("B1", "prop_settled", record.prop_settled, **key, unit="proportion",
                 destination=MAIN, note="neither prevalent nor warm-up"),
            _row("B1", "lead_median_all", record.lead_median_all, record.lead_median_all_ci_lo,
                 record.lead_median_all_ci_hi, **key, unit="min", destination=SUPP,
                 note="published Table 2 quantity, reproduced"),
            _row("B1", "lead_median_incident", record.lead_median_incident,
                 record.lead_median_incident_ci_lo, record.lead_median_incident_ci_hi, **key,
                 unit="min", destination=MAIN),
            _row("B1", "lead_median_settled", record.lead_median_settled,
                 record.lead_median_settled_ci_lo, record.lead_median_settled_ci_hi, **key,
                 unit="min", destination=MAIN),
            _row("B1", "lead_shift_all_minus_incident", record.lead_shift_all_minus_incident,
                 record.lead_shift_ci_lo, record.lead_shift_ci_hi, record.lead_shift_p, **key,
                 unit="min", destination=MAIN, note="paired; BH family B"),
            _row("B1", "lead_shift_all_minus_settled", record.lead_shift_all_minus_settled,
                 record.lead_shift_settled_ci_lo, record.lead_shift_settled_ci_hi,
                 record.lead_shift_settled_p, **key, unit="min", destination=MAIN,
                 note="paired; BH family B"),
            _row("B1", "prop_control_prevalent", record.prop_control_prevalent,
                 record.prop_control_prevalent_ci_lo, record.prop_control_prevalent_ci_hi,
                 **key, unit="proportion", destination=MAIN,
                 note="control cases flagged at their own first eligible minute"),
            _row("B1", "prop_control_prevalent_or_warmup_of_alerting",
                 record.prop_control_prevalent_or_warmup_of_alerting, **key, unit="proportion",
                 destination=MAIN, note="share of alerting controls flagged on arrival or during warm-up"),
        ]
    return rows


def _b1b() -> list[dict]:
    suppression = pd.read_csv(HERE / "b1b_suppression" / "b1b_suppression.csv")
    mechanism = pd.read_csv(HERE / "b1b_suppression" / "b1b_lead_vs_observation.csv")
    rows: list[dict] = []
    for record in suppression.itertuples():
        key = {"family": record.family, "cohort": record.cohort}
        note = f"suppress={record.suppress_min:.0f} min"
        destination = MAIN if record.suppress_min in (0, 5) else SUPP
        rows += [
            _row("B1b", "sensitivity", record.sensitivity, record.sensitivity_ci_lo,
                 record.sensitivity_ci_hi, **key, unit="proportion", destination=destination,
                 note=note + ("; reproduces Table 2" if record.suppress_min == 0 else "")),
            _row("B1b", "specificity", record.specificity, record.specificity_ci_lo,
                 record.specificity_ci_hi, **key, unit="proportion", destination=destination,
                 note=note),
            _row("B1b", "lead_median", record.lead_median, record.lead_median_ci_lo,
                 record.lead_median_ci_hi, **key, unit="min", destination=destination, note=note),
            _row("B1b", "ppv", record.ppv, record.ppv_ci_lo, record.ppv_ci_hi, **key,
                 unit="proportion", destination=destination, note=note),
            _row("B1b", "nne", record.nne, record.nne_ci_lo, record.nne_ci_hi, **key,
                 unit="cases per event", destination=destination, note=note),
        ]
    for record in mechanism.itertuples():
        key = {"family": record.family, "cohort": record.cohort}
        rows += [
            _row("B1b", "lead_over_observed_window", record.lead_over_observed_median,
                 record.lead_over_observed_ci_lo, record.lead_over_observed_ci_hi, **key,
                 unit="ratio", destination=MAIN,
                 note="median lead divided by the case's own observed pre-onset window, capped at 60 min"),
            _row("B1b", "spearman_lead_vs_observed", record.spearman_lead_vs_observed,
                 record.spearman_ci_lo, record.spearman_ci_hi, **key, unit="rho",
                 destination=MAIN,
                 note="bounded above by the window length, so the ratio is the primary quantity"),
            _row("B1b", "median_above_fraction_events", record.median_above_fraction_events,
                 record.median_above_fraction_events_ci_lo,
                 record.median_above_fraction_events_ci_hi,
                 **key, unit="proportion", destination=SUPP,
                 note="share of a case's monitored minutes at or above threshold"),
            _row("B1b", "median_above_fraction_controls", record.median_above_fraction_controls,
                 record.median_above_fraction_controls_ci_lo,
                 record.median_above_fraction_controls_ci_hi,
                 **key, unit="proportion", destination=SUPP),
        ]
    return rows


def _b2() -> list[dict]:
    frame = pd.read_csv(HERE / "b2_departure_timing" / "b2_summary.csv")
    rows: list[dict] = []
    for record in frame.itertuples():
        key = {"family": record.family, "cohort": record.cohort}
        primary = record.rule == "primary"
        destination = MAIN if primary else SUPP
        note = f"rule={record.rule}"
        rows += [
            _row("B2", "difference_median_min", record.difference_median_min,
                 getattr(record, "difference_median_ci_lo", np.nan),
                 getattr(record, "difference_median_ci_hi", np.nan),
                 getattr(record, "difference_median_p", np.nan), **key, unit="min",
                 destination=destination,
                 note=note + "; score departure minus MAP departure, positive = score first; BH family B"),
            _row("B2", "prop_score_first", record.prop_score_first,
                 getattr(record, "prop_score_first_ci_lo", np.nan),
                 getattr(record, "prop_score_first_ci_hi", np.nan),
                 getattr(record, "prop_score_first_vs_half_p", np.nan), **key,
                 unit="proportion", destination=destination, note=note + "; BH family B"),
            _row("B2", "prop_both_departed", record.prop_both, **key, unit="proportion",
                 destination=destination, note=note),
            _row("B2", "prop_no_score_departure", record.prop_neither + record.prop_map_only,
                 **key, unit="proportion", destination=destination,
                 note=note + "; episodes in which the model never signalled"),
            _row("B2", "score_baseline_median", record.score_baseline_median, **key,
                 unit="score", destination=destination,
                 note=note + "; median of an episode's first 10 eligible minutes"),
            _row("B2", "prop_baseline_above_alert_threshold",
                 record.prop_baseline_above_alert_threshold, **key, unit="proportion",
                 destination=destination,
                 note=note + "; baseline already at or above the 80%-target transformer threshold"),
        ]
    return rows


def _b3() -> list[dict]:
    frame = pd.read_csv(HERE / "b3_cross_family_path" / "b3_comparison.csv")
    overlap = pd.read_csv(HERE / "b3_cross_family_path" / "b3_directedness_overlap.csv")
    rows: list[dict] = []
    for record in frame.itertuples():
        key = {"family": record.family, "cohort": record.cohort}
        window = f"60-{record.endpoint_min}"
        rows += [
            _row("B3", f"directedness[{window}]", record.directedness_median,
                 record.directedness_median_ci_lo, record.directedness_median_ci_hi, **key,
                 unit="ratio", destination=MAIN, note="net change / total path length"),
            _row("B3", f"delta[{window}]", record.delta_median, **key, unit="score",
                 destination=SUPP),
            _row("B3", f"gross_up[{window}]", record.gross_up_median, **key, unit="score",
                 destination=SUPP),
            _row("B3", f"gross_down[{window}]", record.gross_down_median, **key, unit="score",
                 destination=SUPP),
            _row("B3", f"max_up_share[{window}]", record.max_up_share_median,
                 record.max_up_share_median_ci_lo, record.max_up_share_median_ci_hi, **key,
                 unit="proportion", destination=SUPP),
            _row("B3", f"path_per_net[{window}]", record.path_per_net, **key, unit="ratio",
                 destination=MAIN, note="path length per unit of absolute net displacement"),
        ]
    for record in overlap[overlap["family_a"] == "ALL PAIRS"].itertuples():
        rows.append(
            _row("B3", f"directedness_all_pairs_overlap[60-{record.endpoint_min}]",
                 float(bool(record.intervals_overlap)), cohort=record.cohort,
                 unit="boolean", destination=MAIN,
                 note="1 = every pairwise interval overlaps, so the value is not family-specific")
        )
    return rows


def _b4() -> list[dict]:
    frame = pd.read_csv(HERE / "b4_divergence_asymmetry" / "b4_decomposition.csv")
    end = frame[frame["bin_center_min"] == 5]
    rows: list[dict] = []
    for record in end.itertuples():
        key = {"family": record.family, "cohort": record.cohort}
        rows += [
            _row("B4", "event_side_change", record.event_side_change,
                 record.event_side_change_ci_lo, record.event_side_change_ci_hi, **key,
                 unit="score", destination=MAIN),
            _row("B4", "control_side_change", record.control_side_change,
                 record.control_side_change_ci_lo, record.control_side_change_ci_hi, **key,
                 unit="score", destination=MAIN),
            _row("B4", "event_side_share", record.event_side_share,
                 record.event_side_share_ci_lo, record.event_side_share_ci_hi,
                 record.event_share_vs_half_p, **key, unit="proportion", destination=MAIN,
                 note="share of the gap widening attributable to the event side; BH family B"),
            _row("B4", "control_side_share", record.control_side_share,
                 record.control_side_share_ci_lo, record.control_side_share_ci_hi, **key,
                 unit="proportion", destination=MAIN),
            _row("B4", "gap_widening", record.gap_widening, **key, unit="score",
                 destination=SUPP),
        ]
    return rows


def _figure_rows() -> list[dict]:
    path = HERE / "figures" / "figure_nt_annotations.json"
    if not path.is_file():
        return []
    annotations = json.loads(path.read_text(encoding="utf-8"))
    rows: list[dict] = []
    for cohort, values in annotations.items():
        rows += [
            _row("A7-figure", "horizon_all_cases_min", values["horizon_all_cases_min"],
                 cohort=cohort, unit="min", destination=MAIN),
            _row("A7-figure", "horizon_fixed_cohort_min", values["horizon_fixed_cohort_min"],
                 cohort=cohort, unit="min", destination=MAIN),
            _row("A7-figure", "crossing_min", values["crossing_min"], cohort=cohort,
                 unit="min", destination=MAIN,
                 note="interpolated innermost sign change of fixed minus all-cases AUROC"),
        ]
    return rows


#: The cross-cell rank correlations are permutations over which operating point is paired with
#: which reported lead, so their unit is a cell and not a patient.  They are a separate BH
#: family for that reason: folding them into B1-B4 would resize a published family of
#: patient-level tests with tests of a different kind, and move every q-value in it.
CELL_FAMILY = "B1b-cells"


def _b1b_operating_point() -> list[dict]:
    frame = pd.read_csv(HERE / "b1b_suppression" / "b1b_lead_vs_operating_point.csv")
    rows: list[dict] = []
    for record in frame.itertuples():
        scope = {"family": "all", "cohort": record.scope}
        note = (
            f"{record.n_cells} cells; permutation over cell pairings, not a cluster bootstrap; "
            f"{record.n_pairs_longer_lead_lower_specificity} of {record.n_untied_pairs} untied "
            "pairs put the longer lead with the lower specificity"
        )
        rows += [
            _row("B1b-cells", "spearman_lead_vs_specificity",
                 record.spearman_lead_vs_specificity, p=record.p_permutation_specificity,
                 **scope, unit="rho", destination=MAIN, note=note),
            _row("B1b-cells", "spearman_lead_vs_ppv_lift",
                 record.spearman_lead_vs_ppv_lift, p=record.p_permutation_ppv_lift,
                 **scope, unit="rho", destination=SUPP,
                 note="PPV minus prevalence, because prevalence runs 0.359 to 0.560"),
        ]
    return rows


def run() -> pd.DataFrame:
    OUT.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(
        _b1() + _b1b() + _b2() + _b3() + _b4() + _b1b_operating_point() + _figure_rows()
    )

    # Benjamini-Hochberg inside B alone.  Every row carrying a finite p-value is a member;
    # the family size is written to the manifest so a later addition cannot silently change
    # the adjustment without the count changing with it.
    frame["bh_family"] = np.where(frame["p_value"].notna(), "B1-B4", "")
    # The cross-cell correlations are their own family; see CELL_FAMILY.  Assigning them here
    # rather than in the blanket rule above is what keeps B1-B4's size, and so every q-value
    # already published from it, unchanged by this addition.
    frame.loc[frame["analysis"] == CELL_FAMILY, "bh_family"] = CELL_FAMILY
    frame["q_value"] = np.nan
    members = frame["bh_family"] == "B1-B4"
    frame.loc[members, "q_value"] = bh_adjust(frame.loc[members, "p_value"])
    cell_members = frame["bh_family"] == CELL_FAMILY
    frame.loc[cell_members, "q_value"] = bh_adjust(frame.loc[cell_members, "p_value"])
    frame["significant_q05"] = frame["q_value"] < 0.05

    frame.to_csv(OUT / "b_results_long.csv", index=False)
    frame.to_json(OUT / "b_results_long.json", orient="records", indent=2)
    _write_report(frame, int(members.sum()))
    write_manifest(
        OUT,
        "collect_results",
        [],
        extra={
            "n_numbers": int(len(frame)),
            "bh_family": "B1-B4",
            "bh_family_size": int(members.sum()),
            "bh_not_pooled_with": [
                "21 transformer trajectory tests",
                "15 orientation tests",
                "A1-A5 families",
                f"{CELL_FAMILY}, whose unit is a cell and not a patient",
            ],
            "cell_family": CELL_FAMILY,
            "cell_family_size": int((frame["bh_family"] == CELL_FAMILY).sum()),
            "seed_base": BOOTSTRAP_SEED,
            "seed_offsets": SEED_OFFSETS,
            "seed_discrepancy_flagged": {
                "supplementary_methods_11": 20260706,
                "supplementary_methods_10": 20260729,
                "published_episode_metric_analysis": 20260729,
                "main_text_methods_states": 20260706,
                "b1_b4_use": BOOTSTRAP_SEED,
                "status": "reported, not harmonised; harmonising would move published q values",
            },
        },
    )
    return frame


def _write_report(frame: pd.DataFrame, family_size: int) -> None:
    tested = frame[frame["p_value"].notna()].sort_values("p_value")
    cell_size = int((frame["bh_family"] == CELL_FAMILY).sum())
    lines = [
        "# B1-B4 collected results\n",
        f"{len(frame)} numbers. `b_results_long.csv` and `.json` are the machine-readable "
        "forms; every write-up number should come from there rather than from a REPORT.md.\n",
        f"## Multiplicity\n\nBenjamini-Hochberg across the {family_size} formal tests in "
        "B1-B4, treated as one family and **not** pooled with the 21-trajectory, "
        "15-orientation or A1-A5 families. Pooling would move published *q* values.\n",
        f"The {cell_size} `{CELL_FAMILY}` tests are adjusted separately. Their unit is a "
        "model-by-cohort cell rather than a patient, and they are permutations of which "
        "operating point is paired with which reported lead, so they are not the same kind of "
        "test as the rest of B; folding them in would resize a published family.\n",
        df_to_md(
            tested[["analysis", "quantity", "family_label", "cohort_label", "value",
                    "p_value", "q_value", "significant_q05"]].round(5)
        ),
        "",
        "## Candidate destinations\n",
        df_to_md(
            frame.groupby(["analysis", "destination"]).size().reset_index(name="n_numbers")
        ),
        "",
        "## Outstanding seed inconsistency\n",
        "Three resampling bases coexist. A previously published analysis states 20260706 "
        "as its default and records 20260729 for the truncated-window orientation family, "
        "which is the base it uses throughout; its main-text methods state 20260706 alone. "
        "B1-B4 use 20260706 with offsets 100,000-130,000. This is reported, not harmonised: "
        "rerunning the published families on one base would move *q* values that are already "
        "published.\n",
    ]
    (OUT / "collect_results.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    frame = run()
    print(f"{len(frame)} numbers collected")
    print(frame.groupby(["analysis", "destination"]).size().to_string())
    for family in ("B1-B4", CELL_FAMILY):
        tested = frame[frame["bh_family"] == family]
        print(
            f"\nBH family {family}: size {len(tested)}; "
            f"{int((tested['q_value'] < 0.05).sum())} at q<0.05"
        )


if __name__ == "__main__":
    main()
