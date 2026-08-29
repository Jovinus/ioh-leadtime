"""A4 - do event and control scores actually diverge, or does everything drift up together?

This is the evidence that the rising population trend is not all scores drifting upward in
parallel. The paper already has it -- the time-by-group interaction is positive in all 15
family-by-cohort cells at 0.97 to 4.51 score units per hour, and the control slope is itself
negative in 13 of them -- but it lives in a single supplementary sentence, with no exhibit,
because the stored mixed-model output holds slopes and no per-bin means.

So the slopes are **read, not refitted**, and the only new computation is the per-bin mean
score for event and control episodes with cluster-bootstrap bands. Both are emitted on two
grids, because the two existing exhibits this could join use different ones: Figure 1 and
A1 are on the 13 published lead-time bins from 60 to 0 minutes, while Figure 3's
accumulation-null panels are on the null's five horizons at 20 to 0 minutes with 5-minute
windows. Whichever grid the figure ends up on, it should be one grid, and the supplement
already warns that these two must not be merged in a single display.

Post-hoc on cached scores; no model is fitted here.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib_pt import (  # noqa: E402
    BIN_CENTERS,
    BOOTSTRAP_SEED,
    COHORT_LABELS,
    COHORT_ORDER,
    FAMILY_LABELS,
    FAMILY_ORDER,
    N_BOOTSTRAP_PATIENT,
    REPO,
    cell_rng,
    cluster_weights,
    df_to_md,
    load_scored,
    percentile_ci,
    write_manifest,
)

OUT = Path(__file__).resolve().parent / "a4_event_control_divergence"
MIXED_MODEL = (
    REPO / "analysis" / "plan_additions_2026" / "mixed_model" / "mixed_model_results.csv"
)

# Two grids, named after the exhibits they match.
GRIDS = {
    # Figure 1 and A1: 13 centres 5 minutes apart, 2 minutes wide.
    "published_13_bin": {"centers": tuple(BIN_CENTERS), "half_width": 1.0},
    # Figure 3's accumulation-null panels: 5 horizons, 5-minute windows.
    "null_5_horizon": {"centers": (20, 15, 10, 5, 0), "half_width": 2.5},
}

# The two statements the supplement makes about the stored output.  Checked rather than
# copied, because a summary sentence is the thing most likely to have drifted from its CSV.
EXPECTED_INTERACTION_RANGE = (0.97, 4.51)
EXPECTED_NEGATIVE_CONTROL_SLOPES = 13


def _per_bin_means(family: str, cohort: str, grid: str) -> pd.DataFrame:
    centers = GRIDS[grid]["centers"]
    half = GRIDS[grid]["half_width"]
    frame = load_scored(family, cohort)
    codes, clusters = pd.factorize(frame["cluster_id"], sort=True)
    n_clusters = len(clusters)
    values = frame["t_to_event"].to_numpy(float)
    labels = frame["label"].to_numpy(int)
    scores = frame["score"].to_numpy(float)

    # One replicate must weight both groups and every bin at once, or the event-minus-control
    # difference is not paired and its interval is wrong.
    group = np.full(values.shape, -1, dtype=int)
    for position, centre in enumerate(centers):
        inside = (values >= centre - half) & (values < centre + half) & (values > 0)
        group[inside] = position * 2 + (labels[inside] == 1)
    keep = group >= 0
    group, weights_index, scores_kept = group[keep], codes[keep], scores[keep]
    n_groups = 2 * len(centers)

    rng = cell_rng(BOOTSTRAP_SEED + 70_000, family, cohort)
    draws = np.full((N_BOOTSTRAP_PATIENT, n_groups), np.nan)
    for replicate in range(N_BOOTSTRAP_PATIENT):
        row_weights = cluster_weights(weights_index, n_clusters, rng).astype(float)
        numerator = np.bincount(group, weights=scores_kept * row_weights, minlength=n_groups)
        denominator = np.bincount(group, weights=row_weights, minlength=n_groups)
        with np.errstate(invalid="ignore", divide="ignore"):
            draws[replicate] = np.where(denominator > 0, numerator / denominator, np.nan)

    rows: list[dict] = []
    for position, centre in enumerate(centers):
        control_rows = group == position * 2
        event_rows = group == position * 2 + 1
        control_lo, control_hi = percentile_ci(draws[:, position * 2])
        event_lo, event_hi = percentile_ci(draws[:, position * 2 + 1])
        gap_lo, gap_hi = percentile_ci(draws[:, position * 2 + 1] - draws[:, position * 2])
        rows.append(
            {
                "family": family,
                "family_label": FAMILY_LABELS[family],
                "cohort": cohort,
                "cohort_label": COHORT_LABELS[cohort],
                "grid": grid,
                "bin_center_min": int(centre),
                "bin_half_width_min": half,
                "n_rows_event": int(event_rows.sum()),
                "n_rows_control": int(control_rows.sum()),
                "n_clusters": int(pd.unique(weights_index).size),
                "cluster_level": frame["cluster_level"].iloc[0],
                "mean_score_event": float(scores_kept[event_rows].mean()),
                "mean_score_event_ci_lo": event_lo,
                "mean_score_event_ci_hi": event_hi,
                "mean_score_control": float(scores_kept[control_rows].mean()),
                "mean_score_control_ci_lo": control_lo,
                "mean_score_control_ci_hi": control_hi,
                "gap_event_minus_control": float(
                    scores_kept[event_rows].mean() - scores_kept[control_rows].mean()
                ),
                "gap_ci_lo": gap_lo,
                "gap_ci_hi": gap_hi,
                "n_bootstrap": N_BOOTSTRAP_PATIENT,
            }
        )
    return pd.DataFrame(rows)


def _slopes() -> pd.DataFrame:
    """Read the published interaction estimates and check the sentences that describe them."""
    stored = pd.read_csv(MIXED_MODEL)
    slopes = stored[
        stored["family"].isin(FAMILY_ORDER) & stored["cohort"].isin(COHORT_ORDER)
    ].copy()
    if len(slopes) != 15:
        raise AssertionError(f"expected 15 mixed-model cells, found {len(slopes)}")
    low, high = slopes["interaction"].min(), slopes["interaction"].max()
    if not (
        np.isclose(round(low, 2), EXPECTED_INTERACTION_RANGE[0], atol=5e-3)
        and np.isclose(round(high, 2), EXPECTED_INTERACTION_RANGE[1], atol=5e-3)
    ):
        raise AssertionError(
            f"interaction range {low:.4f} to {high:.4f} does not match the published "
            f"{EXPECTED_INTERACTION_RANGE[0]} to {EXPECTED_INTERACTION_RANGE[1]}"
        )
    negative = int((slopes["control_slope"] < 0).sum())
    if negative != EXPECTED_NEGATIVE_CONTROL_SLOPES:
        raise AssertionError(
            f"{negative} of 15 control slopes are negative; the supplement says "
            f"{EXPECTED_NEGATIVE_CONTROL_SLOPES}"
        )
    slopes["family_label"] = slopes["family"].map(FAMILY_LABELS)
    slopes["cohort_label"] = slopes["cohort"].map(COHORT_LABELS)
    slopes["interaction_excludes_zero"] = (slopes["interaction_lo"] > 0) | (
        slopes["interaction_hi"] < 0
    )
    slopes["control_slope_negative"] = slopes["control_slope"] < 0
    slopes["source"] = "read unchanged from plan_additions_2026/mixed_model"
    return slopes


def run() -> tuple[pd.DataFrame, pd.DataFrame]:
    OUT.mkdir(parents=True, exist_ok=True)
    frames = [
        _per_bin_means(family, cohort, grid)
        for grid in GRIDS
        for family in FAMILY_ORDER
        for cohort in COHORT_ORDER
    ]
    means = pd.concat(frames, ignore_index=True)
    means.to_csv(OUT / "a4_event_control_means.csv", index=False)

    slopes = _slopes()
    slopes.to_csv(OUT / "a4_event_control_slopes.csv", index=False)

    transformer = means[(means["family"] == "transformer") & (means["grid"] == "published_13_bin")]
    lines = [
        "# A4 - event versus control score divergence",
        "",
        "Per-bin mean score with cluster-bootstrap bands, "
        f"{N_BOOTSTRAP_PATIENT} replicates, event and control weighted by the same replicate "
        "so the gap is paired. Slopes are read from the published mixed-model output; no "
        "model is fitted here.",
        "",
        "Published statements re-derived from the stored output: interaction range "
        f"{slopes['interaction'].min():.4f} to {slopes['interaction'].max():.4f} score units "
        f"per hour, control slope negative in "
        f"{int(slopes['control_slope_negative'].sum())} of {len(slopes)} cells, interaction "
        f"interval excluding zero in {int(slopes['interaction_excludes_zero'].sum())} of "
        f"{len(slopes)}.",
        "",
        "## Transformer, published 13-bin grid",
        "",
        df_to_md(
            transformer[
                [
                    "cohort_label",
                    "bin_center_min",
                    "mean_score_event",
                    "mean_score_control",
                    "gap_event_minus_control",
                    "gap_ci_lo",
                    "gap_ci_hi",
                ]
            ].round(4)
        ),
        "",
        "## Paired event-minus-control slope, all cells",
        "",
        df_to_md(
            slopes[
                [
                    "family_label",
                    "cohort_label",
                    "control_slope",
                    "event_slope",
                    "interaction",
                    "interaction_lo",
                    "interaction_hi",
                ]
            ].round(4)
        ),
    ]
    (OUT / "a4_event_control_divergence.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_manifest(
        OUT,
        "a4_event_control_divergence",
        [],
        extra={
            "seed": BOOTSTRAP_SEED + 70_000,
            "n_bootstrap": N_BOOTSTRAP_PATIENT,
            "grids": {name: list(spec["centers"]) for name, spec in GRIDS.items()},
            "slopes": "read unchanged; no model fitted",
        },
    )
    return means, slopes


def main() -> None:
    means, slopes = run()
    print("a4_event_control_divergence done ->", OUT)
    for grid in GRIDS:
        cell = means[
            (means["family"] == "transformer") & (means["grid"] == grid)
        ]
        print(f"\n-- transformer, {grid}")
        print(
            cell[
                [
                    "cohort",
                    "bin_center_min",
                    "mean_score_event",
                    "mean_score_control",
                    "gap_event_minus_control",
                    "gap_ci_lo",
                    "gap_ci_hi",
                ]
            ]
            .round(3)
            .to_string(index=False)
        )
    print(
        f"\ninteraction {slopes['interaction'].min():.3f} to {slopes['interaction'].max():.3f}; "
        f"control slope negative in {int(slopes['control_slope_negative'].sum())}/15"
    )


if __name__ == "__main__":
    main()
