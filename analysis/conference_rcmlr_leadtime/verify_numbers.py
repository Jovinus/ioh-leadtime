"""Assert that every number in PAPER.md agrees with the CSV it came from.

Each check reads a value from its source file, formats it the way the paper does, and
asserts that string appears in the paper.  Nothing is transcribed from a REPORT.md: reports
round, and a report that drifts from its own source would take the paper with it.

Exit status is 1 on any mismatch, so this can gate a commit.

Coverage grows with the draft.  Sections 3 and 4 are written; §1, §2, §5, §6, §7 and the
appendix are not, and their checks are added as they land.
"""

from __future__ import annotations

import re
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

    # ---- §3.1 and Table A2: N3 strata -------------------------------------------------
    strata = pd.read_csv(N / "n3_stratified" / "n3_strata.csv")
    summary = pd.read_csv(N / "n3_stratified" / "n3_summary.csv")

    transformer = strata[strata["family"] == "transformer"]
    for row in transformer.itertuples():
        present(
            f"Table A2 lead, {row.cohort} Q{row.stratum}",
            f"| {row.lead_median:.0f} [{row.lead_ci_lo:.0f}, {row.lead_ci_hi:.0f}] "
            f"| {row.ratio_median:.2f} [{row.ratio_ci_lo:.2f}, {row.ratio_ci_hi:.2f}] |",
        )
        present(f"Table A2 n, {row.cohort} Q{row.stratum}", f"| {row.n_cases} |")

    rising = int((summary["lead_gradient_min"] > 0).sum())
    present("N3 cells rising", f"**{rising} of 15**")
    present(
        "N3 gradient range",
        f"cells, by {summary['lead_gradient_min'].min():.0f} to "
        f"{summary['lead_gradient_min'].max():.0f} minutes**",
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
        f"band reports {min(q1):.0f} to {max(q1):.0f} minutes and",
    )
    present("transformer last-quintile span", f"the longest {min(q5):.0f} to {max(q5):.0f};")

    published = pd.read_csv(B / "b1b_suppression" / "b1b_lead_vs_observation.csv")
    published_tr = published[published["family"] == "transformer"]["median_lead_min"]
    present(
        "pooled median lead span",
        f"its pooled median of {published_tr.min():.0f} to {published_tr.max():.0f} minutes",
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
        "all-cell rho range, Section 6.1",
        f"ρ = {observed['spearman_lead_vs_observed'].min():.3f} to "
        f"{observed['spearman_lead_vs_observed'].max():.3f}",
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
        # The caption says the ratio "sits below it by X", so the magnitude is unsigned: a
        # minus here would make it "sits below by −0.054", which states the opposite. The
        # sign is still checked, by the excess_ratio < 0 count asserted just above.
        present(f"N1 below-null {family}", f"by {abs(value):.3f}")
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
        f"not distinguishable from the observed correlation in {not_sig} of 15 cells",
    )
    # Section 3.3 reports this WITHIN the cells the observed correlation is not
    # distinguishable from, not over all fifteen -- "the larger within 6 of those 9".
    undecided = longer[longer["p_spearman"] >= 0.05]
    reference_larger = int((undecided["excess_spearman"] < 0).sum())
    # Camera-ready: the "larger within 6 of those 9" detail left the body (Section 3 now says
    # only that the references bound nothing), so it is no longer asserted.
    _ = reference_larger
    longer_tr = longer[longer["family"] == "transformer"]
    # A.7's closing paragraph is about the observed RATIO, and until 2026-08-30 its last
    # sentence quoted the rank-correlation columns instead.  It now reports the ratio
    # reference, so this is sourced from null_ratio_mean rather than null_spearman_mean.
    present(
        "N2 transformer ratio reference",
        f"ratio reference spans {longer_tr['null_ratio_mean'].min():.2f} to "
        f"{longer_tr['null_ratio_mean'].max():.2f}",
    )

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
        f"rises from {score('transformer', 'epic_test', 0, 0):.3f} "
        f"to {score('transformer', 'epic_test', 1, 0):.3f} in one minute in control cases",
    )
    present(
        "EPIC event rise",
        f"and from {score('transformer', 'epic_test', 0, 1):.3f} to "
        f"{score('transformer', 'epic_test', 1, 1):.3f}",
    )
    # Section 4.1 gives the EPIC score pairs in full and reduces the two external cohorts to
    # the minute each clears in.  So what is asserted for those two is the clearing minute
    # itself: the first elapsed minute at which the median score is at or above the
    # transported threshold in BOTH label groups.
    def clears_at(cohort: str) -> int:
        rows = profile[(profile["family"] == "transformer") & (profile["cohort"] == cohort)]
        cut = float(cuts["transformer"])
        for elapsed in sorted(rows["elapsed"].unique()):
            both = rows[rows["elapsed"] == elapsed]
            if len(both) == 2 and (both["score_median"] >= cut).all():
                return int(elapsed)
        raise SystemExit(f"transformer never clears its threshold in {cohort}")

    slowest = max(clears_at(c) for c in COHORT_ORDER)
    present(
        "transformer clears in every cohort within the stated minutes",
        f"Within {WORDS[slowest]} minutes of its first scored minute",
    )
    check(
        "EPIC clears at elapsed minute one",
        clears_at("epic_test") == 1 and "in one minute in control cases" in PAPER,
        "MOVER (EPIC) to clear at elapsed minute one, as Section 4 says",
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

    # ---- §4.2 and Table A5: path decomposition -------------------------------------------
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
            f"Table A5 {row.family}/{row.cohort}",
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
        present(f"Table A5 episodes {cohort}", f"| {episodes} |")

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
        f"in {WORDS[increased]} cells *increasing* it",
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

    # ---- A.17 / §6.2: horizons and crossings on the two denominators ------------------------
    # horizon() and crossing() come from the figure builder, so the numbers asserted here and
    # the curves drawn in Figure A4 cannot drift apart. Not read from
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
    # Figure 2 stops at ten elapsed minutes and Figure A3 sits far later in the record, so the
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

    # ---- A.9: event and control mean score on the event-aligned axis -----------------------
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
        f"running +{min(tabular_far):.3f} to +{max(tabular_far):.3f} with each pointwise",
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

    # ---- A.13: the transformer's departure bar exceeds its headroom in every cohort ---------
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

    # ---- §4.1 and the Abstract: the operating point behind the reported lead --------------
    # Every value here is read unrounded from the cell-level CSV, then formatted the way the
    # paper prints it.  These are the numbers a reviewer disputed, so each one is asserted
    # against its source rather than against a table cell.
    cells = pd.read_csv(B / "b1b_suppression" / "b1b_suppression.csv")
    cells = cells[cells["suppress_min"] == 0]
    assert len(cells) == 15, f"expected fifteen cells, got {len(cells)}"

    spec = cells.set_index(["family", "cohort"])["specificity"]
    lead = cells.set_index(["family", "cohort"])["lead_median"]

    # The Abstract: 24 minutes is the longest lead of the fifteen, and the specificity it
    # occurs at is 0.406, which is NOT the minimum -- 0.379 is.
    longest = lead.idxmax()
    present(
        "abstract longest lead and its specificity",
        f"the longest median lead, {lead.max():.0f} minutes, was read at a "
        f"specificity of {spec[longest]:.3f}",
    )
    check(
        "0.406 is not the minimum specificity",
        spec.min() < spec[longest],
        f"a specificity below {spec[longest]:.3f}; the paper must not call it the minimum",
    )
    ranked = spec.sort_values()
    check(
        "0.406 is second-lowest of the fifteen",
        ranked.index[1] == longest and ranked.index[0] == ("transformer", "vitaldb"),
        "0.406 second in the sorted specificities, behind the transformer in VitalDB",
    )

    # §4.1: lowest specificity within every cohort, longest lead in two and tied in the third.
    tr_lowest = all(
        spec[("transformer", c)] == spec.xs(c, level="cohort").min() for c in COHORT_ORDER
    )
    check("transformer specificity lowest in every cohort", tr_lowest,
          "the transformer to hold the minimum specificity in all three cohorts")
    strict = sum(
        1 for c in COHORT_ORDER
        if (lead.xs(c, level="cohort") < lead[("transformer", c)]).sum() == 4
    )
    tied = sum(
        1 for c in COHORT_ORDER
        if lead[("transformer", c)] == lead.xs(c, level="cohort").max()
        and (lead.xs(c, level="cohort") == lead[("transformer", c)]).sum() > 1
    )
    check(
        "transformer lead longest in two cohorts, tied in the third",
        (strict, tied) == (2, 1),
        f"two strict and one tied, got {strict} strict and {tied} tied",
    )
    present(
        "transformer leads",
        f"Its median leads, {lead[('transformer', 'epic_test')]:.0f}, "
        f"{lead[('transformer', 'vitaldb')]:.0f} and {lead[('transformer', 'mover')]:.0f} minutes, "
        f"are the longest of the five families in two cohorts and tied for longest in the third",
    )

    # §4.1: the cross-combination rank correlations, from the unrounded per-cell values.
    op = pd.read_csv(B / "b1b_suppression" / "b1b_lead_vs_operating_point.csv")
    pooled = op[op["scope"] == "pooled"].iloc[0]
    # The cell-pairing permutation was withdrawn in the 2026-08-29 revision: its unit is a
    # cell, and cells sharing a cohort or a family are not exchangeable.  Section 4.1 reports
    # the correlation as a point estimate with the untied-pair count and no test, so no P or q
    # is asserted here.  A.20's disclosure that the permutation was computed and is not
    # reported is checked below, which is what keeps the withdrawal honest.
    present(
        "lead vs specificity across combinations",
        f"(Spearman \u2212{abs(pooled.spearman_lead_vs_specificity):.3f}; "
        f"{int(pooled.n_pairs_longer_lead_lower_specificity)} of "
        f"{int(pooled.n_untied_pairs)} untied pairs)",
    )
    present(
        "lead vs PPV lift",
        f"to PPV in excess of prevalence (\u2212"
        f"{abs(pooled.spearman_lead_vs_ppv_lift):.3f})",
    )
    present(
        "realized sensitivity spread",
        f"realized sensitivities from {cells['sensitivity'].min():.3f} to "
        f"{cells['sensitivity'].max():.3f}",
    )

    # ---- Section 1, Table 1: the reader-facing table carries no new evidence -------------
    # Every cell restates a result measured elsewhere, so every numeric cell is asserted here
    # against the same source as the section it points at.  Without this the table would be the
    # one place in the paper where a number is transcribed rather than derived.
    present(
        "Table 1 row 1, the invited reading",
        f"The model warns about {lead.max():.0f} minutes ahead",
    )
    present(
        "Table 1 row 2, the window-band gradient",
        f"median lead rises across window bands by {summary['lead_gradient_min'].min():.0f} to "
        f"{summary['lead_gradient_min'].max():.0f} minutes, in {rising} of 15 cells",
    )
    check(
        "Table 1 row 3, 0.406 is lowest within its own cohort",
        spec[("transformer", "epic_test")] == spec.xs("epic_test", level="cohort").min(),
        "the transformer to hold the minimum specificity within MOVER (EPIC) test",
    )
    present(
        "Table 1 row 3, the operating point read beside the lead",
        f"case-level specificity {spec[('transformer', 'epic_test')]:.3f}, the lowest of the five "
        f"families in that cohort",
    )
    present(
        "Table 1 row 4, lead against specificity",
        f"Spearman \u2212{abs(pooled.spearman_lead_vs_specificity):.3f}",
    )

    # ---- A.14: the two estimands the appendix distinguishes ------------------------------
    # The prevalent share is over DETECTED event cases at elapsed minute 0; Table A7's
    # column is over ALL event cases at elapsed minute 0 or 1.  Both are recomputed here
    # from the same per-case construction the analyses use, so the bridge text cannot drift.
    from lib_n import per_case_all  # noqa: PLC0415

    cut = float(headline_cuts()["transformer"])
    prevalent, detected_n, by_min1, event_n, minute_one = [], [], [], [], []
    for cohort in COHORT_ORDER:
        per_case = per_case_all("transformer", cohort, cut)
        events = per_case[(per_case["label"] == 1) & (per_case["observed_min"] > 0)]
        alerted = events["lead"].notna()
        elapsed = (events["observed_min"] - events["lead"])[alerted]
        prevalent.append(int((elapsed == 0).sum()))
        detected_n.append(int(alerted.sum()))
        by_min1.append(int((elapsed <= 1).sum()))
        event_n.append(len(events))
        minute_one.append(int((elapsed == 1).sum()))
    present(
        "A.13 prevalent numerators",
        f"{prevalent[0]} of {detected_n[0]:,}, {prevalent[1]} of {detected_n[1]:,} and "
        f"{prevalent[2]} of {detected_n[2]:,} for the transformer",
    )
    present(
        "A.13 elapsed-minute-one numerators",
        f"{by_min1[0]} of {event_n[0]:,}, {by_min1[1]} of {event_n[1]:,} and "
        f"{by_min1[2]} of {event_n[2]:,}",
    )
    present(
        "A.13 minute-one contribution",
        f"minute one alone adds {minute_one[0]}, {minute_one[1]} and {minute_one[2]} cases",
    )
    km = pd.read_csv(N / "n5_time_to_alert" / "n5_time_to_alert.csv")
    km = km[km["family"] == "transformer"].set_index("cohort")
    for cohort, numerator, denominator in zip(COHORT_ORDER, by_min1, event_n):
        check(
            f"A.12 KM equals the crude share, {cohort}",
            abs((1 - km.loc[cohort, "km_unalerted_by_min1"]) - numerator / denominator) < 5e-4,
            "one minus the survival at minute 1 to equal the crude cumulative share",
        )

    # ---- A.17: the balance Section 5.3 cites ----------------------------------------------
    balance = pd.read_csv(
        REPO / "analysis" / "patient_trajectory_2026" / "a7_observability"
        / "a7_balance_short_vs_long.csv"
    )
    duration = balance[balance["variable"].str.startswith("surgery_min")].set_index("cohort")
    present(
        "A.16 surgery-duration imbalance",
        "by a standardized mean difference of "
        + ", ".join(f"{duration.loc[c, 'smd']:.3f}" for c in COHORT_ORDER[:2])
        + f" and {duration.loc[COHORT_ORDER[2], 'smd']:.3f}",
    )
    for cohort in COHORT_ORDER:
        rows = balance[balance["cohort"] == cohort].dropna(subset=["smd"])
        check(
            f"A.15 duration is the largest imbalance, {cohort}",
            rows["smd"].abs().idxmax() == duration.loc[cohort].name
            or rows.loc[rows["smd"].abs().idxmax(), "variable"].startswith("surgery_min"),
            "operation length to be the largest standardized mean difference",
        )

    # ---- A.20: the two resampling counts are different and both are stated ---------------
    # A.20 used to state the cell-pairing permutation count.  That test is withdrawn, so what
    # is asserted now is the disclosure itself -- that it was computed, is not reported, and
    # why -- plus the two counts the paper DOES rely on.
    present(
        "A.19 discloses the withdrawn permutation",
        "A permutation of the pairing was computed while this analysis was being developed, "
        "and is not reported",
    )
    present(
        "A.19 states the reported resampling counts",
        "Cluster bootstraps use 2,000 replicates",
    )
    present("A.19 permutations per cell", "draw 1,000 permutations per cell")
    check(
        "no withdrawn permutation count survives anywhere in the paper",
        "10,000" not in PAPER,
        "the paper to name no 10,000-permutation test",
    )

    # ---- report -------------------------------------------------------------------------
    # ---- A.19: the Benjamini-Hochberg family, derived from the collected null results -----
    # Ungated until 2026-08-29: the family size and the significant count were stated in prose
    # with nothing comparing them to the tests they count.
    n_long = pd.read_csv(N / "collect_results" / "n_results_long.csv")
    adjusted = n_long[n_long["q_value"].notna()]
    present(
        "A.18 BH family size",
        f"one Benjamini\u2013Hochberg family of {len(adjusted)} formal tests",
    )
    present(
        "A.18 significant after adjustment",
        f"of which {int((adjusted['q_value'] < 0.05).sum())} are significant at *q* < 0.05",
    )

    # ---- The title, the abstract, and every count the paper states about itself ----------
    # Added 2026-08-29, after two errors reached the built PDF through the same blind spot: a
    # count stated in prose that no gate compared against the thing it counted. "Four more
    # items came close and missed" stood against a five-row Table A10, and audit_references.py
    # compared only the first author's family name, so five wrong co-authors survived. Every
    # count below is derived from what it counts, never transcribed.
    from lib_n import FAMILY_ORDER  # noqa: PLC0415

    # Camera-ready title: "... and runs opposite to specificity". That is the sign of the
    # cross-combination rank correlation, so the sign is what is asserted.
    check(
        "title's 'runs opposite to specificity' matches the sign of the correlation",
        "runs opposite to specificity" in PAPER and pooled.spearman_lead_vs_specificity < 0,
        "a negative lead-vs-specificity correlation behind the title",
    )
    present(
        "abstract cohort and family counts",
        f"Across {WORDS[len(COHORT_ORDER)]} perioperative cohorts and "
        f"{WORDS[len(FAMILY_ORDER)]} model families",
    )
    present(
        "abstract combination count",
        f"in all {WORDS[len(cells)]} model-by-cohort combinations",
    )
    check(
        "the fifteen combinations are the cohorts times the families",
        len(cells) == len(COHORT_ORDER) * len(FAMILY_ORDER),
        f"{len(COHORT_ORDER)} x {len(FAMILY_ORDER)} cells, got {len(cells)}",
    )
    present(
        "abstract gradient range",
        f"rises by {summary['lead_gradient_min'].min():.0f} to "
        f"{summary['lead_gradient_min'].max():.0f} minutes from the shortest",
    )

    # Counts the paper states about its own structure, each against the structure itself.
    section = lambda start, end: _RAW[_RAW.index(start):_RAW.index(end)]  # noqa: E731
    disclosures = len(re.findall(r"^\d+\. \*\*", section("## 6.3", "# 7"), re.M))
    present(
        "abstract disclosure count",
        f"We propose {WORDS[disclosures]} task-specific disclosures",
    )
    check(
        "Section 6.3's heading agrees with its own list",
        f"## 6.3 {WORDS[disclosures].capitalize()} disclosures" in _RAW,
        f"the heading to say {WORDS[disclosures]}, the number of numbered items under it",
    )
    check(
        "the abstract's response count agrees with Section 5's heading",
        (f"{WORDS[2].capitalize()} natural repairs, discounting" in PAPER)
        and (f"# 5 {WORDS[2].capitalize()} natural repairs" in _RAW),
        "the abstract and Section 5's heading to name the same number of responses",
    )

    # Table A10's caption stated its own row count until 2026-08-30, when the count was wrong
    # -- it said "five" over five rows describing six items, because the first row covers two.
    # The caption now names no count, so what is asserted instead is that every item the
    # caption says Section 6.1 discusses is actually discussed there, and that the items the
    # table carries are disjoint from none of them.  A count that cannot be derived from the
    # rows is exactly the blind spot that let "four" stand over five rows.
    a8 = _RAW[_RAW.index("**Table A10 |"):]
    a8_rows = sum(
        1 for line in a8.split("\n\n")[1].splitlines() if line.startswith("| ")
    ) - 1  # minus the header; the alignment rule starts "|-"
    present(
        "Table A10 caption names what Section 6.1 discusses",
        "**Table A10 | The TRIPOD+AI items that came close and missed.** Main text Section 6.1 "
        "discusses items 12e, 15, 23a, 20a, 20b and 14",
    )
    # 6.1 writes both "Item 12e," and "Items 20a and 20b", so the item token is matched
    # after an item/items opener rather than immediately behind it.
    section_61 = " ".join(section("## 6.1", "## 6.2").split())
    for item in ("12e", "15", "23a", "20a", "20b", "14"):
        check(
            f"Section 6.1 discusses item {item}, as Table A10's caption says",
            re.search(rf"\bitems?\b[^.]{{0,40}}\b{item}\b", section_61, re.IGNORECASE)
            is not None,
            f"Section 6.1 to discuss item {item}",
        )
    check(
        "Table A10 carries at least one row per remaining near miss",
        a8_rows >= 5,
        f"Table A10 to carry its rows, got {a8_rows}",
    )

    # ---- Camera-ready additions (2026-11-02): case-level AUROC and the usable-model rows --
    auroc = pd.read_csv(B / "b5_case_auroc" / "b5_case_auroc.csv").set_index(["family", "cohort"])
    assert len(auroc) == 15, f"expected fifteen AUROC cells, got {len(auroc)}"
    # Same case set as Table A6: B5 recounts sensitivity and specificity at the cut.
    check(
        "B5 case set reproduces Table A6's sensitivity and specificity",
        all(
            abs(auroc.loc[k, "specificity_at_cut"] - spec[k]) < 1e-12
            and abs(auroc.loc[k, "sensitivity_at_cut"] - cells.set_index(["family", "cohort"])
                    .loc[k, "sensitivity"]) < 1e-12
            for k in auroc.index
        ),
        "B5's per-cut sensitivity and specificity to equal b1b_suppression's",
    )
    a_tr = [auroc.loc[("transformer", c), "case_auroc"] for c in COHORT_ORDER]
    present("transformer case AUROC",
            f"Its case-level AUROC is {a_tr[0]:.3f}, {a_tr[1]:.3f} and {a_tr[2]:.3f}")
    others = auroc.drop(index="transformer", level="family")["case_auroc"]
    present("other families' case AUROC",
            f"against {others.min():.3f} to {others.max():.3f} for the other four")
    check(
        "transformer has the lowest case AUROC in every cohort",
        all(auroc.loc[("transformer", c), "case_auroc"]
            == auroc.xs(c, level="cohort")["case_auroc"].min() for c in COHORT_ORDER),
        "the transformer to hold the minimum case AUROC in all three cohorts",
    )
    usable = [("xgb", c) for c in COHORT_ORDER] + [("rf", c) for c in COHORT_ORDER]
    sp_u = [spec[k] for k in usable]
    au_u = [auroc.loc[k, "case_auroc"] for k in usable]
    rise = summary.set_index(["family", "cohort"])["lead_gradient_min"]
    ri_u = [rise[k] for k in usable]
    present("XGBoost and RF specificity",
            f"specificity {min(sp_u):.3f} to {max(sp_u):.3f} and case-level AUROC "
            f"{min(au_u):.3f} to {max(au_u):.3f}")
    present("XGBoost and RF rise", f"still rise by {min(ri_u):.0f} to {max(ri_u):.0f} minutes")

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
