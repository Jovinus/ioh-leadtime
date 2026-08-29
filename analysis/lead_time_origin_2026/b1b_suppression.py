"""B1b - what suppression recovers, and what the reported lead time is actually measuring.

B1's ``settled`` fraction is *not* the answer to "suppress the first N minutes and rerun".
It classifies each case by its **first** crossing, so a case that crossed at minute 2 and
again at minute 40 counts as warm-up and contributes its minute-2 lead. Under a real
suppression rule that case would still alert, at minute 40. ``prop_settled`` is therefore a
lower bound on post-suppression sensitivity, and quoting it as the answer would understate
what suppression recovers.

This runs the actual rule: discard every minute at or before ``suppress`` minutes of elapsed
monitoring, then apply the same threshold and the same first-crossing definition to what is
left. Sensitivity, specificity, median lead and NNE come back on the same footing as
Table 2, so the two are directly comparable.

The point is not to propose a fix. It is that the fix is the first thing a reader will ask
for, the answer is computable from the cached scores without retraining, and it should be in
the paper rather than left for a reviewer to request.

**And the answer is that it is not a fix.** Across all five families a 5-minute suppression
window costs 4 to 7 points of case-level sensitivity, gains 0 to 2 points of specificity and
shortens the median lead by 0 to 3 minutes. The elevation is not confined to the warm-up
window; suppressing it only trades sensitivity away.

Which raises the sharper question, measured in the second half of this module: if the lead
survives both the removal of prevalent alerts and the removal of the first minutes, what is
it measuring? For each detected event case we compare its lead with the length of its own
observed pre-onset window, capped at the 60-minute alert window. If a model alerts as soon
as it is switched on, the lead is that length, and "median lead time" is a statement about
how long the patient was watched rather than about how early the event was seen coming.

Thresholds are the published validation-fixed values, transported unchanged and not
reselected.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib_b import (  # noqa: E402
    ALERT_WINDOW_MIN,
    BOOTSTRAP_SEED,
    COHORT_LABELS,
    COHORT_ORDER,
    FAMILY_LABELS,
    FAMILY_ORDER,
    HEADLINE_TARGET,
    N_BOOTSTRAP_PATIENT,
    alert_window,
    case_manifest,
    cluster_codes,
    df_to_md,
    load_scored,
    percentile_ci,
    seed_for,
    thresholds,
    weight_matrix,
    weighted_fraction,
    weighted_median,
    weighted_spearman,
    write_manifest,
)

OUT = Path(__file__).resolve().parent / "b1b_suppression"

#: Suppression windows in minutes of elapsed monitoring.  0 reproduces Table 2 exactly, which
#: is the check that the rest of the column is comparable to it.
SUPPRESS_MIN = (0, 3, 5, 10, 15)


def _evaluate(family: str, cohort: str, cut: float, suppress: float) -> dict:
    frame = load_scored(family, cohort)
    frame = frame[(frame["t_to_event"] > 0) & np.isfinite(frame["score"])]
    start = frame.groupby("case_id")["t_to_event"].max()

    window = alert_window(frame).copy()
    window["elapsed"] = window["case_id"].map(start) - window["t_to_event"]
    eligible = window[window["elapsed"] > suppress]

    # Every case keeps its label and cluster even if suppression leaves it no eligible minute:
    # a case that can no longer alert is a missed case, not a dropped one.
    cases = window.groupby("case_id").agg(
        label=("label", "first"), cluster_id=("cluster_id", "first")
    )
    crossings = eligible[eligible["score"] >= cut]
    cases["lead"] = crossings.groupby("case_id")["t_to_event"].max()
    cases["alerted"] = cases["lead"].notna()
    cases = cases.reset_index()

    codes, n_clusters = cluster_codes(cases)
    rng = np.random.default_rng(seed_for("b1", family, cohort) + 7_000 + int(suppress))
    weights = weight_matrix(n_clusters, rng, N_BOOTSTRAP_PATIENT)

    is_event = (cases["label"] == 1).to_numpy()
    alerted = cases["alerted"].to_numpy(bool)
    lead = cases["lead"].to_numpy(float)

    sensitivity = float(alerted[is_event].mean())
    specificity = float(1 - alerted[~is_event].mean())
    tp = int((alerted & is_event).sum())
    fp = int((alerted & ~is_event).sum())

    sens_draws = np.empty(N_BOOTSTRAP_PATIENT)
    spec_draws = np.empty(N_BOOTSTRAP_PATIENT)
    lead_draws = np.empty(N_BOOTSTRAP_PATIENT)
    # PPV and NNE are ratios of two weighted counts rather than means of an indicator, so they
    # cannot go through ``weighted_fraction``. Both are resampled on the *same* weight matrix as
    # sensitivity and specificity, which is what keeps every column of the row a paired draw.
    ppv_draws = np.empty(N_BOOTSTRAP_PATIENT)
    nne_draws = np.empty(N_BOOTSTRAP_PATIENT)
    true_positive = alerted & is_event
    false_positive = alerted & ~is_event
    for replicate in range(N_BOOTSTRAP_PATIENT):
        w = weights[replicate][codes]
        sens_draws[replicate] = weighted_fraction(alerted, np.where(is_event, w, 0))
        spec_draws[replicate] = 1 - weighted_fraction(alerted, np.where(is_event, 0, w))
        lead_draws[replicate] = weighted_median(lead, np.where(is_event & alerted, w, 0))
        tp_w = float(np.dot(true_positive, w))
        fp_w = float(np.dot(false_positive, w))
        alerting_w = tp_w + fp_w
        # A replicate that draws no alerting case at all has no PPV to report; nan propagates
        # into percentile_ci, which is nan-safe.
        ppv_draws[replicate] = tp_w / alerting_w if alerting_w else np.nan
        nne_draws[replicate] = alerting_w / tp_w if tp_w else np.nan

    detected_lead = lead[is_event & alerted]
    row = {
        "family": family,
        "family_label": FAMILY_LABELS[family],
        "cohort": cohort,
        "cohort_label": COHORT_LABELS[cohort],
        "suppress_min": suppress,
        "threshold": cut,
        "n_event": int(is_event.sum()),
        "n_control": int((~is_event).sum()),
        "n_detected": tp,
        "sensitivity": sensitivity,
        "specificity": specificity,
        "ppv": tp / (tp + fp) if tp + fp else np.nan,
        "nne": (tp + fp) / tp if tp else np.inf,
        "lead_median": float(np.median(detected_lead)) if detected_lead.size else np.nan,
        "lead_q25": float(np.percentile(detected_lead, 25)) if detected_lead.size else np.nan,
        "lead_q75": float(np.percentile(detected_lead, 75)) if detected_lead.size else np.nan,
    }
    row["sensitivity_ci_lo"], row["sensitivity_ci_hi"] = percentile_ci(sens_draws)
    row["specificity_ci_lo"], row["specificity_ci_hi"] = percentile_ci(spec_draws)
    row["lead_median_ci_lo"], row["lead_median_ci_hi"] = percentile_ci(lead_draws)
    row["ppv_ci_lo"], row["ppv_ci_hi"] = percentile_ci(ppv_draws)
    row["nne_ci_lo"], row["nne_ci_hi"] = percentile_ci(nne_draws)
    return row


def _lead_vs_observation(family: str, cohort: str, cut: float) -> dict:
    """Is the lead the model's warning, or the length of the window it was given?

    ``observed_min`` is each case's own pre-onset observation length, capped at the 60-minute
    alert window because no crossing can be found outside it -- without the cap the
    correlation would be diluted by minutes the rule never looked at. A ratio near 1 means
    the alert fired at the first opportunity, so the lead is the window length.
    """
    frame = load_scored(family, cohort)
    frame = frame[(frame["t_to_event"] > 0) & np.isfinite(frame["score"])]
    window = alert_window(frame)
    manifest = case_manifest(cohort).set_index("case_id")

    crossing = window[window["score"] >= cut].groupby("case_id")["t_to_event"].max()
    per_case = window.groupby("case_id").agg(
        label=("label", "first"), cluster_id=("cluster_id", "first")
    )
    per_case["above_fraction"] = (
        window.assign(above=window["score"] >= cut).groupby("case_id")["above"].mean()
    )
    per_case["lead"] = crossing
    per_case["observed_min"] = np.minimum(
        manifest["observable_min"].reindex(per_case.index).astype(float), float(ALERT_WINDOW_MIN)
    )
    per_case = per_case.reset_index()

    detected = per_case[(per_case["label"] == 1) & per_case["lead"].notna()].copy()
    detected = detected[detected["observed_min"] > 0]
    ratio = (detected["lead"] / detected["observed_min"]).to_numpy(float)
    codes, n_clusters = cluster_codes(detected)
    rng = np.random.default_rng(seed_for("b1", family, cohort) + 8_000)
    weights = weight_matrix(n_clusters, rng, N_BOOTSTRAP_PATIENT)

    lead = detected["lead"].to_numpy(float)
    observed = detected["observed_min"].to_numpy(float)
    rho_draws = np.empty(N_BOOTSTRAP_PATIENT)
    ratio_draws = np.empty(N_BOOTSTRAP_PATIENT)
    for replicate in range(N_BOOTSTRAP_PATIENT):
        w = weights[replicate][codes]
        rho_draws[replicate] = weighted_spearman(observed, lead, w)
        ratio_draws[replicate] = weighted_median(ratio, w)

    # The two above-fraction medians are taken over *all* event and *all* control cases, not
    # over the detected subset the weights above are drawn on, so they need their own weight
    # matrix over ``per_case``. Sub-offset 9,000 keeps it clear of the 7,000 block ``_evaluate``
    # uses per suppression level and the 8,000 block the ratio draws above use.
    burden_codes, burden_clusters = cluster_codes(per_case)
    burden_rng = np.random.default_rng(seed_for("b1", family, cohort) + 9_000)
    burden_weights = weight_matrix(burden_clusters, burden_rng, N_BOOTSTRAP_PATIENT)
    above = per_case["above_fraction"].to_numpy(float)
    burden_is_event = (per_case["label"] == 1).to_numpy()
    burden_event_draws = np.empty(N_BOOTSTRAP_PATIENT)
    burden_control_draws = np.empty(N_BOOTSTRAP_PATIENT)
    for replicate in range(N_BOOTSTRAP_PATIENT):
        w = burden_weights[replicate][burden_codes]
        burden_event_draws[replicate] = weighted_median(above, np.where(burden_is_event, w, 0))
        burden_control_draws[replicate] = weighted_median(above, np.where(burden_is_event, 0, w))

    row = {
        "family": family,
        "family_label": FAMILY_LABELS[family],
        "cohort": cohort,
        "cohort_label": COHORT_LABELS[cohort],
        "n_detected": int(len(detected)),
        "median_lead_min": float(np.median(lead)),
        "median_observed_min": float(np.median(observed)),
        "lead_over_observed_median": float(np.median(ratio)),
        "spearman_lead_vs_observed": float(weighted_spearman(observed, lead, np.ones(len(detected), int))),
        "median_above_fraction_events": float(
            per_case.loc[per_case["label"] == 1, "above_fraction"].median()
        ),
        "median_above_fraction_controls": float(
            per_case.loc[per_case["label"] == 0, "above_fraction"].median()
        ),
    }
    row["lead_over_observed_ci_lo"], row["lead_over_observed_ci_hi"] = percentile_ci(ratio_draws)
    row["spearman_ci_lo"], row["spearman_ci_hi"] = percentile_ci(rho_draws)
    (
        row["median_above_fraction_events_ci_lo"],
        row["median_above_fraction_events_ci_hi"],
    ) = percentile_ci(burden_event_draws)
    (
        row["median_above_fraction_controls_ci_lo"],
        row["median_above_fraction_controls_ci_hi"],
    ) = percentile_ci(burden_control_draws)
    return row


#: Permutation replicates for the cross-cell rank correlations of
#: ``_lead_vs_operating_point``. This is a permutation over the fifteen cells, not a resample
#: over patients, so it is a different quantity from every other interval in this module and is
#: deliberately not drawn from ``BOOTSTRAP_SEED``'s cluster-bootstrap blocks.
N_CELL_PERMUTATIONS = 10_000


def _rank(values: np.ndarray) -> np.ndarray:
    """Average ranks, so ties do not bias the correlation."""
    return pd.Series(values).rank().to_numpy(float)


def _spearman(x: np.ndarray, y: np.ndarray) -> float:
    rx, ry = _rank(x), _rank(y)
    rx = rx - rx.mean()
    ry = ry - ry.mean()
    denominator = float(np.sqrt(np.dot(rx, rx) * np.dot(ry, ry)))
    return float(np.dot(rx, ry) / denominator) if denominator else np.nan


def _permutation_p(x: np.ndarray, y: np.ndarray, rng: np.random.Generator) -> float:
    """Two-sided P for a cross-cell Spearman, by permuting which y goes with which x.

    Floored at ``1 / (N + 1)`` rather than reported as 0: with fifteen cells the permutation
    distribution is discrete and a zero count means "smaller than the resolution of this test",
    not "zero".
    """
    observed = abs(_spearman(x, y))
    if not np.isfinite(observed):
        return np.nan
    count = 0
    for _ in range(N_CELL_PERMUTATIONS):
        if abs(_spearman(x, rng.permutation(y))) >= observed:
            count += 1
    return max((count + 1) / (N_CELL_PERMUTATIONS + 1), 1.0 / (N_CELL_PERMUTATIONS + 1))


def _lead_vs_operating_point(frame: pd.DataFrame) -> pd.DataFrame:
    """Does a longer reported lead time go with a *better* operating point, or a worse one?

    Every other analysis in this paper holds the model fixed and asks what the reported lead
    responds to. This one holds nothing fixed and asks the reader's question: if you ranked
    these fifteen systems by the number they publish, what would you be ranking them by?

    The answer is that you would be ranking them close to the reverse of their case-level
    specificity. Two caveats belong beside it and are carried in the output. First, the unit
    here is a **cell, not a patient**, so there is no cluster bootstrap to run and the
    permutation P below is over the pairing of cells, not over subjects. Second, cohort is a
    confounder in the pooled figure -- VitalDB has both the lowest prevalence and the shortest
    leads -- which is why the per-cohort rows are reported alongside it. The within-cohort
    rows are the claim that does not depend on pooling.

    ``ppv_lift`` is PPV minus prevalence. Raw PPV is not comparable across these cohorts:
    prevalence runs from 0.359 in VitalDB to 0.560 in MOVER (EPIC), so a PPV of 0.38 is
    near-worthless there and a PPV of 0.60 is good here.
    """
    cells = frame[frame["suppress_min"] == 0].copy()
    cells["prevalence"] = cells["n_event"] / (cells["n_event"] + cells["n_control"])
    cells["ppv_lift"] = cells["ppv"] - cells["prevalence"]
    rng = np.random.default_rng(BOOTSTRAP_SEED + 200_000)

    rows: list[dict] = []
    for scope, subset in [("pooled", cells)] + [
        (cohort, cells[cells["cohort"] == cohort]) for cohort in COHORT_ORDER
    ]:
        lead = subset["lead_median"].to_numpy(float)
        specificity = subset["specificity"].to_numpy(float)
        lift = subset["ppv_lift"].to_numpy(float)
        # Concordance is the assumption-free version of the same statement: of all cell pairs,
        # how many have the longer lead paired with the lower specificity?
        pairs = discordant = 0
        for i in range(len(subset)):
            for j in range(i + 1, len(subset)):
                if lead[i] == lead[j] or specificity[i] == specificity[j]:
                    continue
                pairs += 1
                if (lead[i] > lead[j]) == (specificity[i] < specificity[j]):
                    discordant += 1
        rows.append(
            {
                "scope": scope,
                "scope_label": "All cells" if scope == "pooled" else COHORT_LABELS[scope],
                "n_cells": int(len(subset)),
                "lead_median_min": float(np.min(lead)),
                "lead_median_max": float(np.max(lead)),
                "specificity_min": float(np.min(specificity)),
                "specificity_max": float(np.max(specificity)),
                "ppv_lift_min": float(np.min(lift)),
                "ppv_lift_max": float(np.max(lift)),
                "spearman_lead_vs_specificity": _spearman(lead, specificity),
                "p_permutation_specificity": _permutation_p(lead, specificity, rng),
                "spearman_lead_vs_ppv_lift": _spearman(lead, lift),
                "p_permutation_ppv_lift": _permutation_p(lead, lift, rng),
                "n_untied_pairs": pairs,
                "n_pairs_longer_lead_lower_specificity": discordant,
            }
        )
    return pd.DataFrame(rows)


def run() -> pd.DataFrame:
    OUT.mkdir(parents=True, exist_ok=True)
    cuts = thresholds().set_index(["family", "target_sensitivity"])["threshold"]
    rows: list[dict] = []
    mechanism: list[dict] = []
    for family in FAMILY_ORDER:
        for cohort in COHORT_ORDER:
            cut = float(cuts.loc[(family, HEADLINE_TARGET)])
            for suppress in SUPPRESS_MIN:
                rows.append(_evaluate(family, cohort, cut, suppress))
            mechanism.append(_lead_vs_observation(family, cohort, cut))
            print(f"  b1b {family} / {cohort}", flush=True)
    frame = pd.DataFrame(rows)
    mech = pd.DataFrame(mechanism)
    operating = _lead_vs_operating_point(frame)
    frame.to_csv(OUT / "b1b_suppression.csv", index=False)
    mech.to_csv(OUT / "b1b_lead_vs_observation.csv", index=False)
    operating.to_csv(OUT / "b1b_lead_vs_operating_point.csv", index=False)
    _write_report(frame, mech, operating)
    write_manifest(
        OUT,
        "b1b_suppression",
        [],
        extra={
            "suppress_min": list(SUPPRESS_MIN),
            "rule": (
                "discard every minute at or before `suppress` minutes of elapsed monitoring, "
                "then apply the unchanged transported threshold and the same first-crossing "
                "definition to the remainder"
            ),
            "alert_window_min": ALERT_WINDOW_MIN,
            "target_sensitivity": HEADLINE_TARGET,
            "note": (
                "suppress_min=0 must reproduce Table 2; that is the check that the rest of "
                "the column is comparable to it"
            ),
            "why_not_prop_settled": (
                "B1's settled fraction classifies a case by its first crossing only, so it is "
                "a lower bound on post-suppression sensitivity, not the answer"
            ),
            "n_bootstrap": N_BOOTSTRAP_PATIENT,
            "n_cell_permutations": N_CELL_PERMUTATIONS,
            "cross_cell_note": (
                "b1b_lead_vs_operating_point.csv correlates the reported median lead with "
                "the operating point across the fifteen cells; the unit there is a cell, "
                "not a patient, so its P values are cell permutations and not bootstraps"
            ),
        },
    )
    return frame


def _write_report(frame: pd.DataFrame, mech: pd.DataFrame, operating: pd.DataFrame) -> None:
    lines = [
        "# B1b - what suppressing the warm-up window recovers\n",
        "Same threshold, same alert window, same first-crossing rule; the only change is that "
        "minutes at or before `suppress` minutes of elapsed monitoring are discarded before the "
        "rule is applied. `suppress = 0` reproduces Table 2, which is what makes the rest of "
        "each column comparable to it.\n",
        "A case that can no longer alert is counted as a miss, not dropped.\n",
        "## Suppression, family by family\n",
    ]
    for cohort in COHORT_ORDER:
        cell = frame[frame["cohort"] == cohort]
        table = pd.DataFrame(
            {
                "Model": cell["family_label"],
                "Suppress, min": cell["suppress_min"],
                "Sensitivity (95% CI)": [
                    f"{r.sensitivity:.3f} ({r.sensitivity_ci_lo:.3f}–{r.sensitivity_ci_hi:.3f})"
                    for r in cell.itertuples()
                ],
                "Specificity (95% CI)": [
                    f"{r.specificity:.3f} ({r.specificity_ci_lo:.3f}–{r.specificity_ci_hi:.3f})"
                    for r in cell.itertuples()
                ],
                "Median lead (95% CI)": [
                    f"{r.lead_median:.0f} ({r.lead_median_ci_lo:.0f}–{r.lead_median_ci_hi:.0f})"
                    for r in cell.itertuples()
                ],
                "PPV": cell["ppv"].map("{:.3f}".format),
                "NNE": cell["nne"].map("{:.2f}".format),
            }
        )
        lines += [f"### {COHORT_LABELS[cohort]}\n", df_to_md(table), ""]

    lines += [
        "## What the lead is measuring\n",
        "For each detected event case, its lead against the length of its own observed "
        "pre-onset window, capped at the 60-minute alert window. A ratio near 1 means the "
        "alert fired at the first opportunity, so the reported lead is the window length "
        "rather than a warning. `above_fraction` is the median share of a case's monitored "
        "minutes spent at or above the threshold.\n",
        df_to_md(
            pd.DataFrame(
                {
                    "Cohort": mech["cohort_label"],
                    "Model": mech["family_label"],
                    "n": mech["n_detected"],
                    "Median lead, min": mech["median_lead_min"].map("{:.0f}".format),
                    "Median observed window, min": mech["median_observed_min"].map("{:.0f}".format),
                    "Lead / window (95% CI)": [
                        f"{r.lead_over_observed_median:.2f} "
                        f"({r.lead_over_observed_ci_lo:.2f}–{r.lead_over_observed_ci_hi:.2f})"
                        for r in mech.itertuples()
                    ],
                    "Spearman (95% CI)": [
                        f"{r.spearman_lead_vs_observed:.2f} "
                        f"({r.spearman_ci_lo:.2f}–{r.spearman_ci_hi:.2f})"
                        for r in mech.itertuples()
                    ],
                    "Above thr, events": mech["median_above_fraction_events"].map("{:.3f}".format),
                    "Above thr, controls": mech["median_above_fraction_controls"].map("{:.3f}".format),
                }
            )
        ),
        "",
        "## What a reader ranking by the published number would be ranking by\n",
        "The unit here is a cell, not a patient, so the P values are permutations of which "
        "operating point is paired with which reported lead, not cluster bootstraps. Cohort "
        "confounds the pooled row -- VitalDB has both the lowest prevalence and the shortest "
        "leads -- so the per-cohort rows are the claim that does not depend on pooling. "
        "`PPV lift` is PPV minus prevalence, because raw PPV is not comparable across cohorts "
        "whose prevalence runs from 0.359 to 0.560.\n",
        df_to_md(
            pd.DataFrame(
                {
                    "Scope": operating["scope_label"],
                    "Cells": operating["n_cells"],
                    "Median lead, min": [
                        f"{r.lead_median_min:.0f}–{r.lead_median_max:.0f}"
                        for r in operating.itertuples()
                    ],
                    "Specificity": [
                        f"{r.specificity_min:.3f}–{r.specificity_max:.3f}"
                        for r in operating.itertuples()
                    ],
                    "Spearman lead vs specificity": [
                        f"{r.spearman_lead_vs_specificity:+.3f} "
                        f"(P = {r.p_permutation_specificity:.4f})"
                        for r in operating.itertuples()
                    ],
                    "Spearman lead vs PPV lift": [
                        f"{r.spearman_lead_vs_ppv_lift:+.3f} "
                        f"(P = {r.p_permutation_ppv_lift:.4f})"
                        for r in operating.itertuples()
                    ],
                    "Longer lead / lower specificity": [
                        f"{r.n_pairs_longer_lead_lower_specificity} of {r.n_untied_pairs} pairs"
                        for r in operating.itertuples()
                    ],
                }
            )
        ),
        "",
    ]
    (OUT / "b1b_suppression.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    frame = run()
    mech = pd.read_csv(OUT / "b1b_lead_vs_observation.csv")
    print("\nIs the lead the warning, or the window length?")
    print(
        mech[["cohort", "family", "n_detected", "median_lead_min", "median_observed_min",
              "lead_over_observed_median", "spearman_lead_vs_observed",
              "median_above_fraction_events", "median_above_fraction_controls"]]
        .round(3).to_string(index=False)
    )
    print("\nTransformer, 80% target, by suppression window:")
    print(
        frame[frame["family"] == "transformer"][
            ["cohort", "suppress_min", "sensitivity", "specificity", "lead_median", "nne"]
        ].round(3).to_string(index=False)
    )


if __name__ == "__main__":
    main()
