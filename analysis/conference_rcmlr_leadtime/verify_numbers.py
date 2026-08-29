"""Assert that every number in PAPER.md agrees with the CSV it came from.

Each check reads a value from its source file, formats it the way the paper does, and
asserts that string appears in the paper.  Nothing is transcribed from a REPORT.md: reports
round, and a report that drifts from its own source would take the paper with it.

Exit status is 1 on any mismatch, so this can gate a commit.

Coverage grows with the draft.  Sections 3 and 4 are written; §1, §2, §5, §6, §7 and the
appendix are not, and their checks are added as they land.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "analysis" / "lead_time_null_2026"))

from lib_n import ALERT_WINDOW_MIN as ALERT_WINDOW  # noqa: E402
from lib_n import HEADLINE_TARGET, headline_cuts  # noqa: E402

_RAW = (HERE / "PAPER.md").read_text()
#: Whitespace-normalised copy.  Markdown hard-wraps prose, so a check written as one line
#: would fail purely because the sentence broke across a newline.  Every membership test
#: runs against this, and check strings are written with single spaces.
PAPER = " ".join(_RAW.split())

B = REPO / "analysis" / "lead_time_origin_2026"
N = REPO / "analysis" / "lead_time_null_2026"

#: House style spells small counts. Keeping the mapping here means the assertion still
#: derives from the data rather than from the prose.
WORDS = {
    0: "no", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven",
    8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen",
    14: "fourteen", 15: "fifteen",
}

FAILURES: list[str] = []
PASSED = 0


def check(label: str, passed: bool, detail: str) -> None:
    global PASSED
    if passed:
        PASSED += 1
    else:
        FAILURES.append(f"{label}: expected {detail}")


def present(label: str, text: str) -> None:
    check(label, text in PAPER, repr(text))


def main() -> int:
    # ---- §2: cohort sizes and clustering unit ------------------------------------------
    sys.path.insert(0, str(REPO / "analysis" / "lead_time_null_2026"))
    from lib_n import COHORT_ORDER, load_scored  # noqa: PLC0415

    sizes = {}
    for cohort in COHORT_ORDER:
        frame = load_scored("transformer", cohort)
        cases = frame.groupby("case_id").agg(
            label=("label", "first"), cluster=("cluster_id", "first")
        )
        sizes[cohort] = (
            len(cases), int((cases["label"] == 1).sum()), cases["cluster"].nunique()
        )

    n_cases, n_event, n_subj = sizes["epic_test"]
    present(
        "EPIC cohort size",
        f"{n_cases:,} cases, {n_event} with a sustained event, {n_subj:,} subjects",
    )
    n_cases, n_event, n_subj = sizes["vitaldb"]
    present(
        "VitalDB cohort size",
        f"with {n_cases:,} cases, {n_event:,} events and {n_subj:,} subjects",
    )
    n_cases, n_event, _ = sizes["mover"]
    present("MOVER SIS cohort size", f"with {n_cases:,} cases and {n_event:,} events")

    from ioh_prediction.data.eligibility import INDUCTION_DROP_MIN  # noqa: PLC0415

    present(
        "induction exclusion",
        f"{INDUCTION_DROP_MIN['mover_epic']} minutes where the record is anchored on "
        f"anesthesia start, {INDUCTION_DROP_MIN['vitaldb']} where it is anchored on "
        "surgical start",
    )
    present("alert window in setting", f"the {int(ALERT_WINDOW)} minutes before the event")
    # "an 80%", not "a 80%": the article follows the spoken form of the numeral, and the
    # paper is written that way. Hard-coding "an" here would break at a target like 70%.
    article = "an" if f"{HEADLINE_TARGET:.0%}".startswith(("8", "11", "18")) else "a"
    present(
        "sensitivity target",
        f"{article} {HEADLINE_TARGET:.0%} case-level sensitivity target",
    )

    # ---- §3.1 and Table 1: N3 strata -------------------------------------------------
    strata = pd.read_csv(N / "n3_stratified" / "n3_strata.csv")
    summary = pd.read_csv(N / "n3_stratified" / "n3_summary.csv")

    transformer = strata[strata["family"] == "transformer"]
    for row in transformer.itertuples():
        present(
            f"Table 1 lead, {row.cohort} Q{row.stratum}",
            f"| {row.lead_median:.0f} [{row.lead_ci_lo:.0f}, {row.lead_ci_hi:.0f}] "
            f"| {row.ratio_median:.2f} [{row.ratio_ci_lo:.2f}, {row.ratio_ci_hi:.2f}] |",
        )
        present(f"Table 1 n, {row.cohort} Q{row.stratum}", f"| {row.n_cases} |")

    rising = int((summary["lead_gradient_min"] > 0).sum())
    present("N3 cells rising", f"**{rising} of 15**")
    present(
        "N3 gradient range",
        f"**+{summary['lead_gradient_min'].min():.0f} to "
        f"+{summary['lead_gradient_min'].max():.0f} minutes**",
    )
    present(
        "N3 slope range",
        f"**{summary['lead_per_window_minute'].min():.2f} to "
        f"{summary['lead_per_window_minute'].max():.2f} minutes of lead per minute of window difference**",
    )

    # §3.1 prose: the transformer's Q1 and last-quintile spans, and the published median.
    tr_strata = strata[strata["family"] == "transformer"]
    first = tr_strata.groupby("cohort")["stratum"].min()
    last = tr_strata.groupby("cohort")["stratum"].max()
    q1 = [
        tr_strata[(tr_strata["cohort"] == c) & (tr_strata["stratum"] == first[c])]
        ["lead_median"].iloc[0]
        for c in first.index
    ]
    q5 = [
        tr_strata[(tr_strata["cohort"] == c) & (tr_strata["stratum"] == last[c])]
        ["lead_median"].iloc[0]
        for c in last.index
    ]
    present(
        "transformer Q1 span",
        f"reports {min(q1):.0f} to {max(q1):.0f} minutes of median lead",
    )
    present("transformer last-quintile span", f"and {min(q5):.0f} to {max(q5):.0f} for its longest")

    published = pd.read_csv(B / "b1b_suppression" / "b1b_lead_vs_observation.csv")
    published_tr = published[published["family"] == "transformer"]["median_lead_min"]
    present(
        "pooled median lead span",
        f"the pooled {published_tr.min():.0f} to {published_tr.max():.0f} minutes",
    )

    # ---- §3.2: observed ratio and rho -------------------------------------------------
    observed = pd.read_csv(B / "b1b_suppression" / "b1b_lead_vs_observation.csv")
    present(
        "observed ratio range",
        f"is {observed['lead_over_observed_median'].min():.3f} to "
        f"{observed['lead_over_observed_median'].max():.3f}",
    )
    present(
        "observed rho range",
        f"is {observed['spearman_lead_vs_observed'].min():.3f} to "
        f"{observed['spearman_lead_vs_observed'].max():.3f}",
    )
    tr = observed[observed["family"] == "transformer"]
    present(
        "transformer ratio range",
        f"{tr['lead_over_observed_median'].min():.3f} to "
        f"{tr['lead_over_observed_median'].max():.3f}",
    )
    present(
        "transformer rho range",
        f"ρ = {tr['spearman_lead_vs_observed'].min():.3f} to "
        f"{tr['spearman_lead_vs_observed'].max():.3f}",
    )
    for family in ("logreg", "xgb"):
        value = observed[
            (observed["family"] == family) & (observed["cohort"] == "vitaldb")
        ]["lead_over_observed_median"].iloc[0]
        present(f"mildest cell {family}", f"({value:.3f})")

    # ---- §3.3: N1 -----------------------------------------------------------------------
    n1 = pd.read_csv(N / "n1_uniform_placement" / "n1_uniform_placement.csv")
    n1_tr = n1[n1["family"] == "transformer"]
    present(
        "N1 transformer excess",
        f"**+{n1_tr['excess_ratio'].min():.3f} to +{n1_tr['excess_ratio'].max():.3f}**",
    )
    below = int((n1["excess_ratio"] < 0).sum())
    present("N1 cells below", f"in **{below} of 15** cells")
    for family in ("xgb", "logreg"):
        value = n1[(n1["family"] == family) & (n1["cohort"] == "vitaldb")]["excess_ratio"].iloc[0]
        present(f"N1 below-null {family}", f"by −{abs(value):.3f}")
    rf = n1[(n1["family"] == "rf") & (n1["cohort"] == "vitaldb")].iloc[0]
    present(
        "N1 rf vitaldb",
        f"(+{rf['excess_ratio']:.3f}, *P* = {rf['p_value']:.3f})",
    )

    # ---- §3.3: N2 -----------------------------------------------------------------------
    n2 = pd.read_csv(N / "n2_score_shuffle" / "n2_score_shuffle.csv")
    hold = n2[n2["variant"] == "hold"]
    longer = n2[n2["variant"] == "longer"]
    present(
        "N2 null ratio range",
        f"**{hold['null_ratio_mean'].min():.2f} to {hold['null_ratio_mean'].max():.2f}**",
    )
    present(
        "N2 null rho range",
        f"**{hold['null_spearman_mean'].min():.2f} to "
        f"{hold['null_spearman_mean'].max():.2f}**",
    )
    at_or_below = int((hold["excess_ratio"] <= 0).sum())
    present("N2 cells at or below", f"in **{at_or_below} of 15** cells")
    not_sig = int((longer["p_spearman"] >= 0.05).sum())
    present(
        "N2 rho indistinguishable",
        f"distinguishable from the reference in {not_sig} of 15 cells",
    )
    null_higher = int((longer["excess_spearman"] < 0).sum())
    check(
        "N2 null higher count",
        f"the reference is the larger in {null_higher} of 15" in PAPER,
        f"'the reference is the larger in {null_higher} of 15'",
    )
    longer_tr = longer[longer["family"] == "transformer"]
    present(
        "N2 transformer null rho",
        f"null spans {longer_tr['null_spearman_mean'].min():.2f} to "
        f"{longer_tr['null_spearman_mean'].max():.2f}",
    )
    present("N2 permutations", "1,000 per cell")

    # ---- §4.1: score profile and thresholds ---------------------------------------------
    profile = pd.read_csv(B / "b1_prevalent_incident" / "b1_score_profile.csv")
    cuts = headline_cuts()
    present("transformer threshold", f"**{float(cuts['transformer']):.3f}**")

    def score(family: str, cohort: str, elapsed: int, label: int) -> float:
        row = profile[
            (profile["family"] == family)
            & (profile["cohort"] == cohort)
            & (profile["elapsed"] == elapsed)
            & (profile["label"] == label)
        ]
        return float(row["score_median"].iloc[0])

    present(
        "EPIC control rise",
        f"from {score('transformer', 'epic_test', 0, 0):.3f} at the first scored minute "
        f"to {score('transformer', 'epic_test', 1, 0):.3f}",
    )
    present(
        "EPIC event rise",
        f"and from {score('transformer', 'epic_test', 0, 1):.3f} to "
        f"{score('transformer', 'epic_test', 1, 1):.3f}",
    )
    present(
        "EPIC minute 5 pair",
        f"at {score('transformer', 'epic_test', 5, 0):.3f} and "
        f"{score('transformer', 'epic_test', 5, 1):.3f}",
    )
    present(
        "VitalDB minute 5 pair",
        f"reaching {score('transformer', 'vitaldb', 5, 0):.3f} and "
        f"{score('transformer', 'vitaldb', 5, 1):.3f}",
    )
    present(
        "SIS minute 2 pair",
        f"at {score('transformer', 'mover', 2, 0):.3f} and "
        f"{score('transformer', 'mover', 2, 1):.3f} by minute two",
    )
    present(
        "SIS minute 5 pair",
        f"and {score('transformer', 'mover', 5, 0):.3f} and "
        f"{score('transformer', 'mover', 5, 1):.3f} by minute five",
    )

    # Non-transformer families: the highest median score reached in the first ten minutes,
    # against that family's own threshold. The paper rounds these to two decimals.
    early = profile[profile["elapsed"] <= 10]
    for family in ("logreg", "xgb", "rf"):
        peak = early[(early["family"] == family) & (early["cohort"] == "epic_test")][
            "score_median"
        ].max()
        present(
            f"{family} peak vs threshold",
            f"{peak:.2f} against a threshold of {float(cuts[family]):.2f}",
        )

    # ---- §4.1: above-threshold share ----------------------------------------------------
    others = observed[observed["family"] != "transformer"]
    present(
        "transformer above-threshold share",
        f"**{tr['median_above_fraction_events'].min() * 100:.1f} to "
        f"{tr['median_above_fraction_events'].max() * 100:.1f}% of the transformer's event "
        f"minutes and {tr['median_above_fraction_controls'].min() * 100:.1f} to "
        f"{tr['median_above_fraction_controls'].max() * 100:.1f}% of its control minutes",
    )
    present(
        "other families above-threshold share",
        f"against {others['median_above_fraction_events'].min() * 100:.0f} to "
        f"{others['median_above_fraction_events'].max() * 100:.1f}% and "
        f"{others['median_above_fraction_controls'].min() * 100:.0f} to "
        f"{others['median_above_fraction_controls'].max() * 100:.1f}%",
    )

    # ---- §4.2 and Table 2: path decomposition -------------------------------------------
    b3 = pd.read_csv(B / "b3_cross_family_path" / "b3_comparison.csv")
    b3 = b3[b3["endpoint_min"] == 5]
    present(
        "directedness range",
        f"**+{b3['directedness_median'].min():.3f} to "
        f"+{b3['directedness_median'].max():.3f} across all fifteen cells**",
    )
    present(
        "path per net range",
        f"is {b3['path_per_net'].min():.1f} to {b3['path_per_net'].max():.1f}",
    )
    for row in b3.itertuples():
        present(
            f"Table 2 {row.family}/{row.cohort}",
            f"| {row.directedness_median:.3f} "
            f"[{row.directedness_median_ci_lo:.3f}, {row.directedness_median_ci_hi:.3f}] "
            f"| {row.path_per_net:.1f} |",
        )
    b3_tr = b3[b3["family"] == "transformer"]
    b3_lr = b3[b3["family"] == "logreg"]
    present(
        "transformer volatile end",
        f"(directedness +{b3_tr['directedness_median'].min():.3f} to "
        f"+{b3_tr['directedness_median'].max():.3f}, path per unit net displacement "
        f"{b3_tr['path_per_net'].min():.1f} to {b3_tr['path_per_net'].max():.1f})",
    )
    present(
        "logreg least volatile",
        f"(+{b3_lr['directedness_median'].min():.3f} to "
        f"+{b3_lr['directedness_median'].max():.3f}, "
        f"{b3_lr['path_per_net'].min():.1f} to {b3_lr['path_per_net'].max():.1f})",
    )
    steps = int(b3["median_n_steps"].iloc[0])
    present("median steps", f"median {steps} steps per episode")
    for cohort in ("epic_test", "vitaldb", "mover"):
        episodes = int(b3[b3["cohort"] == cohort]["n_episodes_spanning"].iloc[0])
        present(f"Table 2 episodes {cohort}", f"| {episodes} |")

    # ---- §5.1: prevalence ---------------------------------------------------------------
    b1 = pd.read_csv(B / "b1_prevalent_incident" / "b1_summary.csv")
    b1 = b1[
        (b1["target_sensitivity"] == HEADLINE_TARGET)
        & (b1["first_minute_definition"] == "window")
    ]
    present(
        "prevalent share range",
        f"**{b1['prop_prevalent'].min() * 100:.1f} to {b1['prop_prevalent'].max() * 100:.1f}%**",
    )
    loss = b1["lead_median_all"] - b1["lead_median_incident"]
    present(
        "prevalence lead cost",
        f"**{loss.min():.0f} to {loss.max():.0f} minutes in all fifteen cells**",
    )
    b1_tr = b1[b1["family"] == "transformer"].set_index("cohort")
    order = ["epic_test", "vitaldb", "mover"]
    present(
        "transformer prevalent shares",
        ", ".join(f"{b1_tr.loc[c, 'prop_prevalent'] * 100:.1f}" for c in order[:2])
        + f" and {b1_tr.loc[order[2], 'prop_prevalent'] * 100:.1f}%",
    )
    present(
        "transformer lead all",
        ", ".join(f"{b1_tr.loc[c, 'lead_median_all']:.0f}" for c in order[:2])
        + f" and {b1_tr.loc[order[2], 'lead_median_all']:.0f} minutes",
    )
    present(
        "transformer lead incident",
        ", ".join(f"{b1_tr.loc[c, 'lead_median_incident']:.0f}" for c in order[:2])
        + f" and {b1_tr.loc[order[2], 'lead_median_incident']:.0f}",
    )

    # ---- §5.2: suppression ----------------------------------------------------------------
    supp = pd.read_csv(B / "b1b_suppression" / "b1b_suppression.csv")
    wide = supp.pivot_table(
        index=["family", "cohort"], columns="suppress_min",
        values=["sensitivity", "specificity", "lead_median"],
    )
    d_sens = (wide[("sensitivity", 0)] - wide[("sensitivity", 5)]) * 100
    d_spec = (wide[("specificity", 5)] - wide[("specificity", 0)]) * 100
    d_lead = wide[("lead_median", 5)] - wide[("lead_median", 0)]
    present(
        "suppression sensitivity cost",
        f"**{d_sens.min():.1f} to {d_sens.max():.1f} percentage points\nof case-level "
        f"sensitivity**".replace("\n", " "),
    )
    present(
        "suppression specificity gain",
        f"**{d_spec.min():.0f} to {d_spec.max():.1f} percentage points of specificity**",
    )
    # The paper sets a typographic minus (U+2212), not a hyphen.
    present(
        "suppression lead change",
        f"**{d_lead.min():+.0f} to {d_lead.max():+.0f} minutes**".replace("-", "\u2212"),
    )
    increased = int((d_lead > 0).sum())
    present(
        "suppression cells increased",
        f"in {WORDS[increased]} of the fifteen cells it *increases*",
    )

    # ---- §6.2: N(t) shrinkage ---------------------------------------------------------------
    a7 = pd.read_csv(
        REPO / "analysis" / "patient_trajectory_2026" / "a7_observability"
        / "a7_auroc_by_sample.csv"
    )
    a7 = a7[a7["sample"] == "all"]
    spans = []
    for cohort in ("epic_test", "vitaldb", "mover"):
        cell = a7[a7["cohort"] == cohort]
        n0 = int(cell[cell["bin_center_min"] == 0]["n_cases"].iloc[0])
        n60 = int(cell[cell["bin_center_min"] == 60]["n_cases"].iloc[0])
        spans.append(f"{n0:,} to {n60:,}")
    present("N(t) shrinkage", ", ".join(spans[:2]) + f" and {spans[2]}")

    # ---- A.6 / §6.2: horizons and crossings on the two denominators ------------------------
    # horizon() and crossing() come from the figure builder, so the numbers asserted here and
    # the curves drawn in Figure A3 cannot drift apart. Not read from
    # lead_time_origin_2026/figures/figure_nt_annotations.json: that file is a build artefact
    # of a different module and asserting the paper against it would only prove the two agree
    # with each other.
    sys.path.insert(0, str(HERE))
    from build_conf_figures import FIXED_SAMPLE, crossing, horizon  # noqa: E402

    a7_full = pd.read_csv(
        REPO / "analysis" / "patient_trajectory_2026" / "a7_observability"
        / "a7_auroc_by_sample.csv"
    )
    horizons_all, horizons_fixed, crossings = [], [], []
    for cohort in ("epic_test", "vitaldb", "mover"):
        cell = a7_full[a7_full["cohort"] == cohort]
        varying = cell[cell["sample"] == "all"]
        fixed = cell[cell["sample"] == FIXED_SAMPLE]
        horizons_all.append(horizon(varying))
        horizons_fixed.append(horizon(fixed))
        crossings.append(crossing(varying, fixed))

    assert len(set(horizons_all)) == 1, (
        f"the varying-denominator horizon is quoted as one number for all three cohorts "
        f"but reads {horizons_all}"
    )
    present(
        "horizon on the varying denominator",
        f"from {horizons_all[0]:.0f} minutes in all three cohorts",
    )
    present(
        "horizon on the fixed cohort",
        "to " + ", ".join(f"{h:.0f}" for h in horizons_fixed[:2])
        + f" and {horizons_fixed[2]:.0f}",
    )
    present(
        "curves cross",
        "cross at " + ", ".join(f"{c:.1f}" for c in crossings[:2])
        + f" and {crossings[2]:.1f} minutes before onset",
    )

    # ---- 4.1: how long the elevated phase lasts ---------------------------------------------
    # Figure 2 stops at ten elapsed minutes and Figure A4 sits far later in the record, so the
    # two look contradictory unless the length of the plateau is stated. Measured here from
    # the cached scores rather than from a summary, because no module reports it.
    cut = float(headline_cuts()["transformer"])
    last_above, at_thirty = {}, []
    for label, group in ((1, "event"), (0, "control")):
        ends = []
        for cohort in ("epic_test", "vitaldb", "mover"):
            frame = load_scored("transformer", cohort).copy()
            frame["elapsed"] = (
                frame.groupby("case_id")["t_to_event"].transform("max") - frame["t_to_event"]
            )
            median = frame[frame["label"] == label].groupby("elapsed")["score"].median()
            median = median[median.index <= 120]
            ends.append(int(median[median >= cut].index.max()))
            at_thirty.append(float(median.loc[30]))
        last_above[group] = ends
    present(
        "elevated phase, event",
        "through elapsed minute " + ", ".join(str(e) for e in last_above["event"][:2])
        + f" and {last_above['event'][2]} in event cases",
    )
    present(
        "elevated phase, control",
        ", ".join(str(e) for e in last_above["control"][:2])
        + f" and {last_above['control'][2]} in controls",
    )
    present(
        "score at elapsed 30",
        f"falls to {min(at_thirty):.2f} to {max(at_thirty):.2f} by minute 30",
    )

    # ---- A.7: event and control mean score on the event-aligned axis -----------------------
    a4 = pd.read_csv(
        REPO / "analysis" / "patient_trajectory_2026" / "a4_event_control_divergence"
        / "a4_event_control_means.csv"
    )
    a4 = a4[(a4["grid"] == "published_13_bin") & a4["mean_score_event"].notna()]

    def _cell(family: str, cohort: str) -> pd.DataFrame:
        part = a4[(a4["family"] == family) & (a4["cohort"] == cohort)]
        return part.sort_values("bin_center_min", ascending=False)

    # The transformer's gap at the far end, interval by interval. The paper quotes all three
    # because "covers zero in all three cohorts" is the claim.
    far_gaps = []
    for cohort in ("epic_test", "vitaldb", "mover"):
        far = _cell("transformer", cohort).iloc[0]
        assert far["gap_ci_lo"] < 0 < far["gap_ci_hi"], (
            f"the paper says the transformer's 60-minute gap covers zero in every cohort, "
            f"but {cohort} reads [{far['gap_ci_lo']:.3f}, {far['gap_ci_hi']:.3f}]"
        )
        far_gaps.append(
            f"{far['gap_event_minus_control']:.3f} [{far['gap_ci_lo']:.3f}, "
            f"{far['gap_ci_hi']:.3f}]".replace("-", "\u2212")
        )
    present("transformer gap at 60 min", ", ".join(far_gaps[:2]) + f" and {far_gaps[2]}")

    # Where it first separates, walking inward.
    separations = []
    for cohort in ("epic_test", "vitaldb", "mover"):
        cell = _cell("transformer", cohort)
        separations.append(int(cell[cell["gap_ci_lo"] > 0]["bin_center_min"].max()))
    present(
        "transformer separation onset",
        "first excludes it at " + ", ".join(str(s) for s in separations[:2])
        + f" and {separations[2]} minutes",
    )

    # The tabular families are already apart at the far end.
    tabular_rows = [
        _cell(family, cohort).iloc[0]
        for family in ("xgb", "rf", "logreg")
        for cohort in ("epic_test", "vitaldb", "mover")
    ]
    # The paper says every one of these nine intervals excludes zero, which is what makes
    # "already apart at 60 minutes" a claim rather than a description of the point estimates.
    apart = [row for row in tabular_rows if row["gap_ci_lo"] <= 0]
    assert not apart, (
        "the paper says the tabular families are already apart at 60 minutes with every "
        f"interval excluding zero, but {len(apart)} of nine cells cover it"
    )
    tabular_far = [row["gap_event_minus_control"] for row in tabular_rows]
    present(
        "tabular gap at 60 min",
        f"running +{min(tabular_far):.3f} to +{max(tabular_far):.3f} with every interval",
    )

    # Event rise and control fall over the hour, transformer.
    rises, falls = [], []
    for cohort in ("epic_test", "vitaldb", "mover"):
        cell = _cell("transformer", cohort)
        far, near = cell.iloc[0], cell.iloc[-1]
        rises.append(near["mean_score_event"] - far["mean_score_event"])
        falls.append(near["mean_score_control"] - far["mean_score_control"])
    present(
        "transformer event rise",
        "event mean rises " + ", ".join(f"{r:+.3f}" for r in rises[:2])
        + f" and {rises[2]:+.3f}",
    )
    present(
        "transformer control fall",
        (
            "control mean falls " + ", ".join(f"{f:+.3f}" for f in falls[:2])
            + f" and {falls[2]:+.3f}"
        ).replace("-", "\u2212"),
    )

    lstm_falls = [
        _cell("lstm", cohort).iloc[-1]["mean_score_control"]
        - _cell("lstm", cohort).iloc[0]["mean_score_control"]
        for cohort in ("epic_test", "vitaldb", "mover")
    ]
    present(
        "lstm control fall",
        f"also falls, by {abs(max(lstm_falls)):.3f} to {abs(min(lstm_falls)):.3f}",
    )

    tabular_moves = [
        _cell(family, cohort).iloc[-1]["mean_score_control"]
        - _cell(family, cohort).iloc[0]["mean_score_control"]
        for family in ("xgb", "rf", "logreg")
        for cohort in ("epic_test", "vitaldb", "mover")
    ]
    present(
        "tabular control movement",
        (
            f"moves between {min(tabular_moves):+.3f} and {max(tabular_moves):+.3f}"
        ).replace("-", "\u2212"),
    )

    # ---- A.8: the transformer's departure bar exceeds its headroom in every cohort ---------
    b2 = pd.read_csv(
        REPO / "analysis" / "lead_time_origin_2026" / "b2_departure_timing" / "b2_summary.csv"
    )
    b2 = b2[b2["rule"] == "primary"]
    tight = b2[b2["family"] == "transformer"]
    over = tight[tight["score_bar_median"] <= tight["score_headroom_median"]]
    assert over.empty, (
        "the appendix says the transformer's headroom is less than the bar its own rule sets "
        f"in all three cohorts, but {len(over)} cohort(s) read the other way"
    )
    present(
        "transformer baseline and headroom",
        f"baseline of {tight['score_baseline_median'].min():.2f} to "
        f"{tight['score_baseline_median'].max():.2f} leaves median headroom of "
        f"{tight['score_headroom_median'].min():.3f} to "
        f"{tight['score_headroom_median'].max():.3f}",
    )

    # The claim that the expected shape is present everywhere.
    present("all fifteen cells show the shape", "**present in all fifteen cells**")

    present("operating point", f"transported {HEADLINE_TARGET:.0%}-sensitivity operating point")

    # ---- report -------------------------------------------------------------------------
    total = PASSED + len(FAILURES)
    if FAILURES:
        print(f"{PASSED}/{total} passed, {len(FAILURES)} FAILED\n")
        for failure in FAILURES:
            print(f"  {failure}")
        return 1
    print(f"{PASSED}/{total} passed, 0 failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
