"""Shared helpers for the A1-A5 patient-level trajectory analyses.

Everything here reads cached per-minute scores. No model is trained, refitted or
re-scored; see ``PREREGISTRATION.md`` for what each analysis estimates and for the
decision rule A2 is committed to.

Two things are deliberately imported rather than restated. The lead-time bins come from
``ioh_prediction.evaluation.time_window_metrics``, so the ascent fractions land on exactly
the grid the published population AUROC uses. The episode extraction is checked against
the previously published episode-metric routine at the published window, so a
truncated-window tau cannot silently differ from the published one for any reason other
than the truncation.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kendalltau

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "analysis" / "ioh_faithfulness_2026"))

from lib import attach_highest_cluster, df_to_md, write_manifest  # noqa: E402

from ioh_prediction.evaluation.time_window_metrics import (  # noqa: E402
    DEFAULT_TIME_POINTS_MIN,
    DEFAULT_WINDOW_SIZE_MIN,
)

RUNS = REPO / "outputs" / "runs"

FAMILY_RUNS = {
    "transformer": "gap0",
    "lstm": "lstm_gap0",
    "xgb": "xgb_gap0",
    "rf": "rf_gap0",
    "logreg": "logreg_gap0",
}
# The family order used throughout.
FAMILY_ORDER = ["transformer", "lstm", "xgb", "rf", "logreg"]
FAMILY_LABELS = {
    "transformer": "ITE Transformer",
    "lstm": "LSTM",
    "xgb": "XGBoost",
    "rf": "Random forest",
    "logreg": "Logistic regression",
}
COHORT_PATHS = {
    "epic_test": "predictions/test",
    "vitaldb": "external_vitaldb",
    "mover": "external_mover",
}
COHORT_ORDER = ["epic_test", "vitaldb", "mover"]
COHORT_LABELS = {
    "epic_test": "MOVER (EPIC) test",
    "vitaldb": "VitalDB",
    "mover": "MOVER (SIS)",
}

# The published patient-level window, and the pre-specified truncation.  TRUNCATION_MIN is
# 5 because that is the largest of the three published median peak times (5 / 4 / 4 minutes
# before onset); it is not anchored on each episode's own maximum, which would be upward
# selection bias.  See PREREGISTRATION.md.
WINDOW_MIN = 30
TRUNCATION_MIN = 5
MIN_POINTS = 5

# Lead-time bins: 13 centres 5 minutes apart, each 2 minutes wide.  Imported, not restated,
# so the ascent fractions cannot drift off the grid the population AUROC is reported on.
BIN_CENTERS = tuple(sorted(DEFAULT_TIME_POINTS_MIN, reverse=True))
BIN_HALF_WIDTH = DEFAULT_WINDOW_SIZE_MIN / 2
BIN_STEP = BIN_CENTERS[0] - BIN_CENTERS[1]

BOOTSTRAP_SEED = 20260706
N_BOOTSTRAP_PATIENT = 2_000
N_BOOTSTRAP_OTHER = 1_000


def prediction_path(family: str, cohort: str) -> Path:
    return RUNS / FAMILY_RUNS[family] / COHORT_PATHS[cohort] / "predictions_raw.parquet"


def load_scored(family: str, cohort: str) -> pd.DataFrame:
    """Cached per-minute scores for one family-by-cohort cell, with the clustering unit.

    ``attach_highest_cluster`` is what makes the unit a patient for MOVER (EPIC) and
    VitalDB and a case for MOVER (SIS), whose released ``subject_id`` is a copy of
    ``case_id`` and is not a patient key.  Going around it is how a bootstrap ends up
    treating one patient's several operations as independent.
    """
    path = prediction_path(family, cohort)
    frame = pd.read_parquet(path, columns=["case_id", "label", "t_to_event", "score"])
    frame = attach_highest_cluster(frame, path, cohort)
    frame["case_id"] = frame["case_id"].astype(str)
    frame["cluster_id"] = frame["cluster_id"].astype(str)
    return frame


def episode_window(frame: pd.DataFrame, lo: float = 0.0, hi: float = WINDOW_MIN) -> pd.DataFrame:
    """Rows inside ``lo < t_to_event <= hi`` with a finite score.

    ``t_to_event`` is negative after the reference time rather than missing, so the lower
    bound is not optional: without it post-onset minutes enter every episode statistic.
    """
    return frame[
        (frame["t_to_event"] > lo)
        & (frame["t_to_event"] <= hi)
        & np.isfinite(frame["score"])
    ]


def episode_tau(group: pd.DataFrame, lo: float = 0.0, hi: float = WINDOW_MIN) -> dict | None:
    """Within-episode Kendall tau over ``lo < t_to_event <= hi``.

    Time is oriented toward onset, so a positive tau means the score rises as onset
    approaches.  The reversal identity is asserted because it is what the orientation
    randomization null in A2 rests on: reversing time preserves the whole score sequence,
    its ties, its duration and its serial dependence, and changes only the sign of tau.
    """
    window = group.pipe(episode_window, lo=lo, hi=hi).sort_values(
        "t_to_event", ascending=False
    )
    if len(window) < MIN_POINTS:
        return None
    time_to_event = window["t_to_event"].to_numpy(float)
    toward_onset = -time_to_event
    score = window["score"].to_numpy(float)
    tau = float(kendalltau(toward_onset, score).statistic)
    if not np.isfinite(tau):
        return None
    reversal = float(kendalltau(-toward_onset, score).statistic)
    if not np.isclose(reversal, -tau, atol=1e-12, rtol=0):
        raise AssertionError("trajectory reversal did not negate Kendall tau")
    running_max = np.maximum.accumulate(score)
    return {
        "n_points": int(len(window)),
        "tau": tau,
        "reversal_tau": reversal,
        "peak_time_min_before_onset": float(time_to_event[int(np.argmax(score))]),
        "max_drawdown": float(np.max(running_max - score)),
        # The score at the earliest observed minute of the window: the same minute that
        # anchors tau, which is what makes A3's correlation a statement about tau.
        "start_score": float(score[0]),
        "start_time_min_before_onset": float(time_to_event[0]),
        "end_score": float(score[-1]),
    }


def episode_table(
    lo: float = 0.0,
    hi: float = WINDOW_MIN,
    labels: tuple[int, ...] = (1,),
) -> pd.DataFrame:
    """One row per episode per family-by-cohort cell.

    ``labels=(1,)`` reproduces the published unit, one positive case.  ``labels=(0, 1)``
    adds control cases anchored on their sampled pseudo-onset, which A1 and A3 need and
    which no published table contains.
    """
    rows: list[dict] = []
    for family in FAMILY_ORDER:
        for cohort in COHORT_ORDER:
            frame = load_scored(family, cohort)
            frame = frame[frame["label"].isin(labels)]
            for case_id, group in frame.groupby("case_id", sort=False):
                metric = episode_tau(group, lo=lo, hi=hi)
                if metric is None:
                    continue
                cluster_ids = group["cluster_id"].unique()
                cluster_levels = group["cluster_level"].astype(str).unique()
                if len(cluster_ids) != 1 or len(cluster_levels) != 1:
                    raise AssertionError(f"nonunique cluster mapping for {case_id}")
                rows.append(
                    {
                        "family": family,
                        "cohort": cohort,
                        "case_id": case_id,
                        "cluster_id": cluster_ids[0],
                        "cluster_level": cluster_levels[0],
                        "label": int(group["label"].iloc[0]),
                        **metric,
                    }
                )
    return pd.DataFrame(rows)


def assign_bin(t_to_event: pd.Series) -> pd.Series:
    """Map minutes to the published lead-time bin centre, or NaN outside every bin.

    The bins are 2 minutes wide and 5 apart, so most minutes fall in no bin at all.  That
    is a property of the published grid, not a bug to be smoothed over.
    """
    values = t_to_event.to_numpy(float)
    out = np.full(values.shape, np.nan)
    for centre in BIN_CENTERS:
        inside = (values >= centre - BIN_HALF_WIDTH) & (values < centre + BIN_HALF_WIDTH)
        out[inside] = centre
    return pd.Series(out, index=t_to_event.index, name="bin_center")


def episode_bin_scores(frame: pd.DataFrame) -> pd.DataFrame:
    """Mean score per episode per lead-time bin.

    A 2-minute bin can hold two observed minutes; their mean is the episode's value for
    that bin.  Returned long, one row per (case_id, bin_center).
    """
    inside = frame.assign(bin_center=assign_bin(frame["t_to_event"]))
    inside = inside[inside["bin_center"].notna() & (inside["t_to_event"] > 0)]
    return (
        inside.groupby(["case_id", "cluster_id", "cluster_level", "label", "bin_center"], sort=False)[
            "score"
        ]
        .mean()
        .reset_index()
    )


def cluster_weights(codes: np.ndarray, n_clusters: int, rng: np.random.Generator) -> np.ndarray:
    """One cluster-bootstrap replicate, as integer multiplicities per row.

    Weights rather than row duplication: the same replicate can then be applied to two
    estimands at once, which is what makes a paired contrast paired.
    """
    drawn = np.bincount(rng.integers(0, n_clusters, n_clusters), minlength=n_clusters)
    return drawn[codes]


def weighted_fraction(indicator: np.ndarray, weights: np.ndarray) -> float:
    total = weights.sum()
    if total == 0:
        return float("nan")
    return float(np.dot(indicator.astype(float), weights) / total)


def weighted_mean(values: np.ndarray, weights: np.ndarray) -> float:
    keep = np.isfinite(values) & (weights > 0)
    if not keep.any():
        return float("nan")
    return float(np.average(values[keep], weights=weights[keep]))


def weighted_median(values: np.ndarray, weights: np.ndarray) -> float:
    """Median of a sample replicated by nonnegative integer weights."""
    values = np.asarray(values, float)
    weights = np.asarray(weights, np.int64)
    keep = np.isfinite(values) & (weights > 0)
    if not keep.any():
        return float("nan")
    values, weights = values[keep], weights[keep]
    order = np.argsort(values, kind="mergesort")
    values, weights = values[order], weights[order]
    cumulative = np.cumsum(weights)
    total = int(cumulative[-1])
    left = values[np.searchsorted(cumulative, (total - 1) // 2, side="right")]
    right = values[np.searchsorted(cumulative, total // 2, side="right")]
    return float((left + right) / 2)


def weighted_spearman(x: np.ndarray, y: np.ndarray, weights: np.ndarray) -> float:
    """Spearman rho under integer resampling weights.

    Ranks are recomputed on the resampled sample, which is the point: ranking the original
    sample and then reweighting would hold the ranks fixed across replicates and understate
    the interval.
    """
    keep = np.isfinite(x) & np.isfinite(y) & (weights > 0)
    if keep.sum() < 3:
        return float("nan")
    xs = np.repeat(x[keep], weights[keep])
    ys = np.repeat(y[keep], weights[keep])
    if xs.size < 3:
        return float("nan")
    rx = pd.Series(xs).rank().to_numpy()
    ry = pd.Series(ys).rank().to_numpy()
    if rx.std() == 0 or ry.std() == 0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


def percentile_ci(draws: np.ndarray) -> tuple[float, float]:
    finite = np.asarray(draws, float)
    if not np.isfinite(finite).any():
        return float("nan"), float("nan")
    return float(np.nanpercentile(finite, 2.5)), float(np.nanpercentile(finite, 97.5))


def bh_adjust(p_values: pd.Series) -> np.ndarray:
    """Benjamini-Hochberg adjusted p-values, preserving NaNs."""
    p = p_values.to_numpy(float)
    out = np.full(p.shape, np.nan)
    valid = np.flatnonzero(np.isfinite(p))
    if not len(valid):
        return out
    order = valid[np.argsort(p[valid])]
    ranked = p[order]
    m = len(ranked)
    adjusted = ranked * m / np.arange(1, m + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    out[order] = np.minimum(adjusted, 1.0)
    return out


def cell_rng(base: int, family: str, cohort: str) -> np.random.Generator:
    """Per-cell generator, offset the way the published analysis offsets its cells."""
    return np.random.default_rng(
        base + FAMILY_ORDER.index(family) * 100 + COHORT_ORDER.index(cohort)
    )


__all__ = [
    "BIN_CENTERS",
    "BIN_HALF_WIDTH",
    "BIN_STEP",
    "BOOTSTRAP_SEED",
    "COHORT_LABELS",
    "COHORT_ORDER",
    "COHORT_PATHS",
    "FAMILY_LABELS",
    "FAMILY_ORDER",
    "FAMILY_RUNS",
    "MIN_POINTS",
    "N_BOOTSTRAP_OTHER",
    "N_BOOTSTRAP_PATIENT",
    "REPO",
    "RUNS",
    "TRUNCATION_MIN",
    "WINDOW_MIN",
    "assign_bin",
    "attach_highest_cluster",
    "bh_adjust",
    "cell_rng",
    "cluster_weights",
    "df_to_md",
    "episode_bin_scores",
    "episode_table",
    "episode_tau",
    "episode_window",
    "load_scored",
    "percentile_ci",
    "prediction_path",
    "weighted_fraction",
    "weighted_mean",
    "weighted_median",
    "weighted_spearman",
    "write_manifest",
]
