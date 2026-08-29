"""Generate NUMBER_PROVENANCE.md by reading every headline number from its source CSV.

**Never hand-edit the output.** Keeping a provenance summary by hand is exactly what
retired an earlier decision log: the summary drifted from the sources it
described, and a reader could not tell which was right.

This and ``verify_numbers.py`` are deliberately two independent gates over the same facts.
This one writes down what the sources say; that one asserts the paper agrees. A single
script doing both could be self-consistently wrong.

Each entry names the quantity as the paper phrases it, the file it comes from, how it is
derived from that file, and the value as of this run.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "analysis" / "lead_time_null_2026"))

from lib_n import HEADLINE_TARGET, headline_cuts  # noqa: E402

B = REPO / "analysis" / "lead_time_origin_2026"
N = REPO / "analysis" / "lead_time_null_2026"
A = REPO / "analysis" / "patient_trajectory_2026"


def rel(path: Path) -> str:
    return str(path.relative_to(REPO))


def main() -> None:
    rows: list[tuple[str, str, str, str, str]] = []

    def add(section: str, quantity: str, source: Path, how: str, value: str) -> None:
        rows.append((section, quantity, rel(source), how, value))

    # --- §2 cohorts ---------------------------------------------------------------------
    from lib_n import COHORT_ORDER, load_scored  # noqa: PLC0415

    labels = {"epic_test": "MOVER (EPIC) test", "vitaldb": "VitalDB", "mover": "MOVER (SIS)"}
    for cohort in COHORT_ORDER:
        frame = load_scored("transformer", cohort)
        cases = frame.groupby("case_id").agg(
            label=("label", "first"), cluster=("cluster_id", "first")
        )
        add(
            "§2", f"{labels[cohort]} cases / events / subjects",
            REPO / "outputs" / "runs" / "gap0",
            "distinct case_id, label==1, distinct cluster_id in predictions_raw.parquet",
            f"{len(cases):,} / {int((cases['label'] == 1).sum()):,} / "
            f"{cases['cluster'].nunique():,}",
        )

    # --- operating point ----------------------------------------------------------------
    cuts = headline_cuts()
    threshold_csv = (
        REPO / "analysis" / "pre_submission_revision_2026" / "results"
        / "validation_calibration_and_thresholds.csv"
    )
    for family, cut in cuts.items():
        add(
            "§2, §4.1", f"transported threshold, {family}", threshold_csv,
            f"record=='operating_point', target_sensitivity=={HEADLINE_TARGET}, scale raw",
            f"{cut:.6f}",
        )

    # --- §3.1 stratification --------------------------------------------------------------
    summary = pd.read_csv(N / "n3_stratified" / "n3_summary.csv")
    src = N / "n3_stratified" / "n3_summary.csv"
    add("§3.1", "cells with a positive Q1→Q_last gradient", src,
        "count of lead_gradient_min > 0",
        f"{int((summary['lead_gradient_min'] > 0).sum())} of {len(summary)}")
    add("§3.1", "gradient range, minutes", src,
        "min/max of lead_gradient_min",
        f"+{summary['lead_gradient_min'].min():.0f} to "
        f"+{summary['lead_gradient_min'].max():.0f}")
    add("§3.1", "lead minutes per window minute", src,
        "min/max of lead_per_window_minute",
        f"{summary['lead_per_window_minute'].min():.2f} to "
        f"{summary['lead_per_window_minute'].max():.2f}")

    strata = pd.read_csv(N / "n3_stratified" / "n3_strata.csv")
    src = N / "n3_stratified" / "n3_strata.csv"
    add("§3.1, Table 1", "every quintile median and interval", src,
        "lead_median, lead_ci_lo/hi, ratio_median, ratio_ci_lo/hi, per cell and stratum",
        f"{len(strata)} rows, transformer rows shown in Table 1")

    # --- §3.2 observed ----------------------------------------------------------------------
    observed = pd.read_csv(B / "b1b_suppression" / "b1b_lead_vs_observation.csv")
    src = B / "b1b_suppression" / "b1b_lead_vs_observation.csv"
    add("§3.2", "median lead / observed window, all cells", src,
        "min/max of lead_over_observed_median",
        f"{observed['lead_over_observed_median'].min():.3f} to "
        f"{observed['lead_over_observed_median'].max():.3f}")
    add("§3.2", "Spearman lead vs window, all cells", src,
        "min/max of spearman_lead_vs_observed",
        f"{observed['spearman_lead_vs_observed'].min():.3f} to "
        f"{observed['spearman_lead_vs_observed'].max():.3f}")
    tr = observed[observed["family"] == "transformer"]
    add("§3.2", "transformer ratio / rho", src,
        "same columns, family=='transformer'",
        f"{tr['lead_over_observed_median'].min():.3f}–"
        f"{tr['lead_over_observed_median'].max():.3f} / "
        f"{tr['spearman_lead_vs_observed'].min():.3f}–"
        f"{tr['spearman_lead_vs_observed'].max():.3f}")
    add("§4.1", "share of monitored minutes at or above threshold", src,
        "median_above_fraction_events / _controls, transformer vs the rest",
        f"transformer {tr['median_above_fraction_events'].min() * 100:.1f}–"
        f"{tr['median_above_fraction_events'].max() * 100:.1f}% event, "
        f"{tr['median_above_fraction_controls'].min() * 100:.1f}–"
        f"{tr['median_above_fraction_controls'].max() * 100:.1f}% control")

    # --- §3.3 nulls ---------------------------------------------------------------------------
    n1 = pd.read_csv(N / "n1_uniform_placement" / "n1_uniform_placement.csv")
    src = N / "n1_uniform_placement" / "n1_uniform_placement.csv"
    n1_tr = n1[n1["family"] == "transformer"]
    add("§3.3", "excess over the uniform null, transformer", src,
        "min/max of excess_ratio, family=='transformer'",
        f"+{n1_tr['excess_ratio'].min():.3f} to +{n1_tr['excess_ratio'].max():.3f}")
    add("§3.3", "cells below the uniform null", src,
        "count of excess_ratio < 0, with the cell names",
        f"{int((n1['excess_ratio'] < 0).sum())} "
        f"({', '.join(n1[n1['excess_ratio'] < 0]['family'] + '/' + n1[n1['excess_ratio'] < 0]['cohort'])})")

    n2 = pd.read_csv(N / "n2_score_shuffle" / "n2_score_shuffle.csv")
    src = N / "n2_score_shuffle" / "n2_score_shuffle.csv"
    hold = n2[n2["variant"] == "hold"]
    longer = n2[n2["variant"] == "longer"]
    add("§3.3", "shuffle null median ratio (hold)", src,
        "min/max of null_ratio_mean, variant=='hold'",
        f"{hold['null_ratio_mean'].min():.2f} to {hold['null_ratio_mean'].max():.2f}")
    add("§3.3", "shuffle null Spearman (hold)", src,
        "min/max of null_spearman_mean, variant=='hold'",
        f"{hold['null_spearman_mean'].min():.2f} to {hold['null_spearman_mean'].max():.2f}")
    add("§3.3", "cells with observed at or below the null", src,
        "count of excess_ratio <= 0, variant=='hold'",
        f"{int((hold['excess_ratio'] <= 0).sum())} of 15")
    add("§3.3", "rho indistinguishable from the null (length-matched)", src,
        "count of p_spearman >= 0.05, variant=='longer'",
        f"{int((longer['p_spearman'] >= 0.05).sum())} of 15")

    # --- §4.1 plateau --------------------------------------------------------------------------
    profile = pd.read_csv(B / "b1_prevalent_incident" / "b1_score_profile.csv")
    src = B / "b1_prevalent_incident" / "b1_score_profile.csv"
    for cohort in ("epic_test", "vitaldb", "mover"):
        cell = profile[(profile["family"] == "transformer") & (profile["cohort"] == cohort)]
        pairs = []
        for elapsed in (0, 1, 5):
            row = cell[cell["elapsed"] == elapsed]
            control = float(row[row["label"] == 0]["score_median"].iloc[0])
            event = float(row[row["label"] == 1]["score_median"].iloc[0])
            pairs.append(f"min {elapsed}: {control:.3f}/{event:.3f}")
        add("§4.1", f"transformer score profile, {labels[cohort]}", src,
            "score_median by elapsed and label (control/event)", "; ".join(pairs))

    # --- §4.2 path -----------------------------------------------------------------------------
    b3 = pd.read_csv(B / "b3_cross_family_path" / "b3_comparison.csv")
    src = B / "b3_cross_family_path" / "b3_comparison.csv"
    b3 = b3[b3["endpoint_min"] == 5]
    add("§4.2, Table A2", "directedness, all cells", src,
        "min/max of directedness_median, endpoint_min==5 (the 60→5 window only)",
        f"+{b3['directedness_median'].min():.3f} to +{b3['directedness_median'].max():.3f}")
    add("§4.2, Table A2", "path per unit net displacement", src,
        "min/max of path_per_net, endpoint_min==5",
        f"{b3['path_per_net'].min():.1f} to {b3['path_per_net'].max():.1f}")

    # --- §5 --------------------------------------------------------------------------------------
    b1 = pd.read_csv(B / "b1_prevalent_incident" / "b1_summary.csv")
    src = B / "b1_prevalent_incident" / "b1_summary.csv"
    b1 = b1[
        (b1["target_sensitivity"] == HEADLINE_TARGET)
        & (b1["first_minute_definition"] == "window")
    ]
    add("§5.1", "prevalent share of detected event cases", src,
        "min/max of prop_prevalent",
        f"{b1['prop_prevalent'].min() * 100:.1f}% to {b1['prop_prevalent'].max() * 100:.1f}%")
    loss = b1["lead_median_all"] - b1["lead_median_incident"]
    add("§5.1", "median lead lost by dropping prevalent alerts", src,
        "lead_median_all minus lead_median_incident",
        f"{loss.min():.0f} to {loss.max():.0f} minutes, all 15 cells")

    supp = pd.read_csv(B / "b1b_suppression" / "b1b_suppression.csv")
    src = B / "b1b_suppression" / "b1b_suppression.csv"
    wide = supp.pivot_table(
        index=["family", "cohort"], columns="suppress_min",
        values=["sensitivity", "specificity", "lead_median"],
    )
    d_sens = (wide[("sensitivity", 0)] - wide[("sensitivity", 5)]) * 100
    d_spec = (wide[("specificity", 5)] - wide[("specificity", 0)]) * 100
    d_lead = wide[("lead_median", 5)] - wide[("lead_median", 0)]
    add("§5.2", "sensitivity lost at N=5", src,
        "sensitivity at suppress_min 0 minus at 5, x100",
        f"{d_sens.min():.1f} to {d_sens.max():.1f} points")
    add("§5.2", "specificity gained at N=5", src,
        "specificity at 5 minus at 0, x100",
        f"{d_spec.min():.1f} to {d_spec.max():.1f} points")
    add("§5.2", "median lead change at N=5", src,
        "lead_median at 5 minus at 0; positive means lead increased",
        f"{d_lead.min():+.0f} to {d_lead.max():+.0f} minutes "
        f"({int((d_lead > 0).sum())} cells increased)")

    # --- Table 1 and Table A4, the case-level operating point ------------------------------------
    src = B / "b1b_suppression" / "b1b_suppression.csv"
    op = pd.read_csv(src)
    op = op[op["suppress_min"] == 0]
    tr = op[op["family"] == "transformer"]
    add("§4.1", "transformer case-level specificity", src,
        "specificity at suppress_min==0, family=='transformer'",
        ", ".join(f"{v:.3f}" for v in tr["specificity"]))
    add("§4.1", "transformer PPV", src,
        "ppv at suppress_min==0, family=='transformer'",
        ", ".join(f"{v:.3f}" for v in tr["ppv"]))
    prevalence = op["n_event"] / (op["n_event"] + op["n_control"])
    lift = (op["ppv"] - prevalence)[op["family"] == "transformer"]
    add("§4.1", "transformer PPV in excess of prevalence", src,
        "ppv minus n_event/(n_event+n_control), family=='transformer'",
        ", ".join(f"{v:+.3f}" for v in lift))
    add("§4.1", "control cases alerting, transformer", src,
        "1 minus specificity, family=='transformer', as a percentage",
        f"{(1 - tr['specificity']).min() * 100:.0f} to {(1 - tr['specificity']).max() * 100:.0f}%")

    src = B / "b1b_suppression" / "b1b_lead_vs_operating_point.csv"
    cross = pd.read_csv(src).set_index("scope")
    pooled = cross.loc["pooled"]
    add("§4.1", "Spearman(median lead, specificity) across combinations", src,
        "scope=='pooled'; permutation over cell pairings, not a cluster bootstrap",
        f"{pooled.spearman_lead_vs_specificity:.3f} (P = {pooled.p_permutation_specificity:.4f})")
    add("§4.1", "Spearman(median lead, PPV lift) across combinations", src,
        "scope=='pooled'",
        f"{pooled.spearman_lead_vs_ppv_lift:.3f} "
        f"(P = {pooled.p_permutation_ppv_lift:.4f})")
    add("§4.1", "cell pairs with the longer lead at the lower specificity", src,
        "n_pairs_longer_lead_lower_specificity of n_untied_pairs, scope=='pooled'",
        f"{int(pooled.n_pairs_longer_lead_lower_specificity)} of {int(pooled.n_untied_pairs)}")

    # --- §3.1 and Table A5, detection rate by band -----------------------------------------------
    src = N / "n4_band_detection" / "n4_detection_summary.csv"
    n4 = pd.read_csv(src)
    sequence = n4[n4["family"].isin(["transformer", "lstm"])]["detection_gradient"]
    tabular = n4[~n4["family"].isin(["transformer", "lstm"])]["detection_gradient"]
    add("§3.1", "detection-rate gradient, magnitude across cells", src,
        "abs(detection_gradient), min and max over all fifteen cells",
        f"{n4['detection_gradient'].abs().min():.3f} to "
        f"{n4['detection_gradient'].abs().max():.3f}")
    add("§3.1", "detection-rate gradient, sequence families", src,
        "detection_gradient, family in (transformer, lstm)",
        f"{sequence.min():+.3f} to {sequence.max():+.3f}")
    add("§3.1", "detection-rate gradient, tabular families", src,
        "detection_gradient, family in (xgb, rf, logreg)",
        f"{tabular.min():+.3f} to {tabular.max():+.3f}")

    # --- §5.3 and Tables A6, A7, the replacement estimands ---------------------------------------
    src = N / "n5_time_to_alert" / "n5_fixed_horizon.csv"
    fh = pd.read_csv(src)
    for horizon_min in (10, 30):
        at = fh[fh["horizon_min"] == horizon_min]["fixed_horizon_detection"]
        add("§5.3", f"fixed-horizon detection at {horizon_min} min", src,
            f"fixed_horizon_detection, horizon_min=={horizon_min}, over fifteen cells",
            f"{at.min():.3f} to {at.max():.3f}")
    src = N / "n5_time_to_alert" / "n5_time_to_alert.csv"
    n5 = pd.read_csv(src)
    tr5 = n5[n5["family"] == "transformer"]
    add("§5.3", "median lead on the full window, transformer", src,
        "lead_median_fully_observed, family=='transformer'",
        ", ".join(f"{v:.0f}" for v in tr5["lead_median_fully_observed"]))
    add("§5.3", "detected on the full window, transformer", src,
        "detection_fully_observed, family=='transformer'",
        ", ".join(f"{v:.3f}" for v in tr5["detection_fully_observed"]))
    strong = n5[n5["family"].isin(["xgb", "rf"])]["detection_fully_observed"]
    add("§5.3", "detected on the full window, XGBoost and random forest", src,
        "detection_fully_observed, family in (xgb, rf)",
        f"{strong.min():.3f} to {strong.max():.3f}")
    discarded = 1 - n5["n_fully_observed"] / n5["n_event_cases"]
    add("§5.3", "event cases discarded by the full-window restriction", src,
        "1 minus n_fully_observed/n_event_cases, as a percentage",
        f"{discarded.min() * 100:.0f} to {discarded.max() * 100:.0f}%")

    # --- §6.2 N(t) ---------------------------------------------------------------------------------
    a7 = pd.read_csv(A / "a7_observability" / "a7_auroc_by_sample.csv")
    src = A / "a7_observability" / "a7_auroc_by_sample.csv"
    a7 = a7[a7["sample"] == "all"]
    spans = []
    for cohort in ("epic_test", "vitaldb", "mover"):
        cell = a7[a7["cohort"] == cohort]
        n0 = int(cell[cell["bin_center_min"] == 0]["n_cases"].iloc[0])
        n60 = int(cell[cell["bin_center_min"] == 60]["n_cases"].iloc[0])
        spans.append(f"{n0:,}→{n60:,}")
    add("§6.2", "risk set at onset vs 60 min before", src,
        "n_cases at bin_center_min 0 and 60, sample=='all'", ", ".join(spans))

    # --- A.6 horizons and crossings ----------------------------------------------------------------
    # horizon() and crossing() are the figure builder's, so the provenance record, the
    # assertion in verify_numbers.py and the curve drawn in Figure A3 share one definition.
    sys.path.insert(0, str(HERE))
    from build_conf_figures import FIXED_SAMPLE, crossing, horizon  # noqa: E402

    a7_full = pd.read_csv(src)
    h_all, h_fixed, xings = [], [], []
    for cohort in ("epic_test", "vitaldb", "mover"):
        cell = a7_full[a7_full["cohort"] == cohort]
        varying = cell[cell["sample"] == "all"]
        fixed = cell[cell["sample"] == FIXED_SAMPLE]
        h_all.append(horizon(varying))
        h_fixed.append(horizon(fixed))
        xings.append(crossing(varying, fixed))
    add("A.6", "first bin reaching AUROC 0.70, varying denominator", src,
        "max bin_center_min with auroc >= 0.70, sample=='all'",
        ", ".join(f"{h:.0f}" for h in h_all))
    add("A.6", "first bin reaching AUROC 0.70, fixed cohort", src,
        f"same, sample=='{FIXED_SAMPLE}'",
        ", ".join(f"{h:.0f}" for h in h_fixed))
    add("A.6", "where the two curves cross", src,
        "innermost sign change of fixed minus all, linearly interpolated",
        ", ".join(f"{x:.1f}" for x in xings))

    # --- A.7 event and control mean score ----------------------------------------------------------
    a4_src = A / "a4_event_control_divergence" / "a4_event_control_means.csv"
    a4 = pd.read_csv(a4_src)
    a4 = a4[(a4["grid"] == "published_13_bin") & a4["mean_score_event"].notna()]

    def _a4(family: str, cohort: str) -> pd.DataFrame:
        part = a4[(a4["family"] == family) & (a4["cohort"] == cohort)]
        return part.sort_values("bin_center_min", ascending=False)

    far_gaps, seps, rises, falls = [], [], [], []
    for cohort in ("epic_test", "vitaldb", "mover"):
        cell = _a4("transformer", cohort)
        far, near = cell.iloc[0], cell.iloc[-1]
        far_gaps.append(
            f"{far['gap_event_minus_control']:.3f} "
            f"[{far['gap_ci_lo']:.3f}, {far['gap_ci_hi']:.3f}]"
        )
        seps.append(int(cell[cell["gap_ci_lo"] > 0]["bin_center_min"].max()))
        rises.append(near["mean_score_event"] - far["mean_score_event"])
        falls.append(near["mean_score_control"] - far["mean_score_control"])

    add("A.7", "transformer event-minus-control gap at 60 min", a4_src,
        "gap_event_minus_control with CI at bin_center_min 60, published_13_bin",
        "; ".join(far_gaps))
    add("A.7", "farthest bin whose gap excludes zero, transformer", a4_src,
        "max bin_center_min with gap_ci_lo > 0",
        ", ".join(f"{s} min" for s in seps))
    add("A.7", "transformer event mean, 60 min to 5 min", a4_src,
        "mean_score_event at bin 5 minus bin 60",
        ", ".join(f"{r:+.3f}" for r in rises))
    add("A.7", "transformer control mean, 60 min to 5 min", a4_src,
        "mean_score_control at bin 5 minus bin 60",
        ", ".join(f"{f:+.3f}" for f in falls))

    tab_far = [
        _a4(fam, coh).iloc[0]["gap_event_minus_control"]
        for fam in ("xgb", "rf", "logreg")
        for coh in ("epic_test", "vitaldb", "mover")
    ]
    tab_ctrl = [
        _a4(fam, coh).iloc[-1]["mean_score_control"] - _a4(fam, coh).iloc[0]["mean_score_control"]
        for fam in ("xgb", "rf", "logreg")
        for coh in ("epic_test", "vitaldb", "mover")
    ]
    add("A.7", "tabular families' gap at 60 min", a4_src,
        "gap_event_minus_control at bin 60, XGBoost / RF / logistic regression, nine cells",
        f"+{min(tab_far):.3f} to +{max(tab_far):.3f}")
    add("A.7", "tabular families' control mean movement", a4_src,
        "mean_score_control at bin 5 minus bin 60, same nine cells",
        f"{min(tab_ctrl):+.3f} to {max(tab_ctrl):+.3f}")

    # --- write -------------------------------------------------------------------------------------
    lines = [
        "# Number provenance",
        "",
        "<!-- GENERATED by build_provenance.py — do not hand-edit. -->",
        "",
        "Every headline number in `PAPER.md`, the file it is read from, and how. Regenerate "
        "with `conda run -n torch python build_provenance.py`.",
        "",
        "This file and `verify_numbers.py` are two independent gates over the same facts: this "
        "one records what the sources say, that one asserts the paper agrees. Keeping a "
        "provenance summary by hand is what retired an earlier decision log.",
        "",
        "| Section | Quantity | Source | Derivation | Value |",
        "|---|---|---|---|---|",
    ]
    for section, quantity, source, how, value in rows:
        lines.append(f"| {section} | {quantity} | `{source}` | {how} | {value} |")
    lines += [
        "",
        f"{len(rows)} quantities. No model was trained, refitted or re-scored to produce any "
        "of them, and no threshold, split, seed or operating point was reselected.",
        "",
    ]
    (HERE / "NUMBER_PROVENANCE.md").write_text("\n".join(lines))
    print(f"NUMBER_PROVENANCE.md written ({len(rows)} quantities)")


if __name__ == "__main__":
    main()
