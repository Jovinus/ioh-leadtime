"""Shared helpers for B1-B4: where the reported alert lead time actually comes from.

The four analyses answer one question from four sides. Table 2 reports a 21-24 minute
median alert lead at the 80% validation sensitivity target, while A6 reports that the
whole median net score rise sits in the final 5 minutes. A score whose net rise is
confined to the last 5 minutes cannot generate a 21-minute median lead *by rising across
a threshold*, so something else is producing it. B1 tests the obvious candidate (the case
was already above threshold when monitoring started), B2 asks whether score departure
precedes MAP departure inside an episode, B3 asks whether the late-jump path shape belongs
to the transformer or to the task, and B4 asks which side of the event-control gap is
actually moving.

Three things are deliberately imported rather than restated:

* ``lib_pt`` supplies the cached-score loader, the clustering unit, the published
  lead-time bin grid and the bootstrap seed, so B1-B4 land on the same cohorts and the
  same resampling scheme as A1-A7.
* The alert thresholds are read from
  ``analysis/pre_submission_revision_2026/results/validation_calibration_and_thresholds.csv``
  and are **not** reselected. That file is the source of published Table 2; ``step0_repro``
  asserts Table 2 comes back out of it before any B step runs.
* The alert window and the alarm convention come from that same analysis: the monitored
  window is ``0 < t_to_event <= 60`` and a case alarms iff ``score >= threshold`` at some
  minute inside it, with lead time the first such minute's ``t_to_event``.

B1-B4 are a new multiplicity family. They are **not** pooled with the 21-trajectory,
15-orientation, or A1-A5 families; ``collect_results`` adjusts within B alone and records
the family size.

Post-hoc on cached per-minute scores and, for B2, on the source per-minute MAP series.
No model is trained, refitted or re-scored.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "analysis" / "patient_trajectory_2026"))

from lib_pt import (  # noqa: E402
    BIN_CENTERS,
    BOOTSTRAP_SEED,
    COHORT_LABELS,
    COHORT_ORDER,
    FAMILY_LABELS,
    FAMILY_ORDER,
    N_BOOTSTRAP_PATIENT,
    assign_bin,
    bh_adjust,
    df_to_md,
    load_scored,
    percentile_ci,
    weighted_fraction,
    weighted_median,
    weighted_spearman,
    write_manifest,
)

sys.path.insert(0, str(REPO))

from ioh_prediction.data.eligibility import INDUCTION_DROP_MIN  # noqa: E402
from ioh_prediction.data.splits import stratified_subject_split_3way  # noqa: E402

#: Published alert window.  Not a free parameter: it is the window Table 2 is computed on.
ALERT_WINDOW_MIN = 60
#: Published sensitivity targets, transported unchanged from MOVER (EPIC) validation.
TARGET_SENSITIVITIES = (0.70, 0.80, 0.90)
#: The one the manuscript reports in Table 2.
HEADLINE_TARGET = 0.80

THRESHOLD_CSV = (
    REPO
    / "analysis"
    / "pre_submission_revision_2026"
    / "results"
    / "validation_calibration_and_thresholds.csv"
)

COHORT_SOURCE = {"epic_test": "mover_epic", "vitaldb": "vitaldb", "mover": "mover"}

#: Offsets on ``BOOTSTRAP_SEED`` so no B step reuses another step's draws, and none
#: collides with the A1-A7 offsets (which run up to 90,000).
SEED_OFFSETS = {"b1": 100_000, "b2": 110_000, "b3": 120_000, "b4": 130_000}


def seed_for(step: str, family: str, cohort: str) -> int:
    return (
        BOOTSTRAP_SEED
        + SEED_OFFSETS[step]
        + FAMILY_ORDER.index(family) * 100
        + COHORT_ORDER.index(cohort)
    )


def thresholds() -> pd.DataFrame:
    """The validation-fixed raw-score thresholds, one row per family and target.

    Read, never recomputed.  The threshold is a property of the MOVER (EPIC) validation
    split alone, so it is identical across the four cohorts the source file reports it
    against; that invariance is asserted rather than assumed.
    """
    frame = pd.read_csv(THRESHOLD_CSV)
    frame = frame[frame["record"] == "operating_point"]
    grouped = frame.groupby(["family", "target_sensitivity"])["threshold"].nunique()
    if (grouped != 1).any():
        raise AssertionError("a threshold varies by cohort; it should be validation-fixed")
    out = (
        frame.groupby(["family", "target_sensitivity"])["threshold"]
        .first()
        .reset_index()
        .sort_values(["family", "target_sensitivity"])
    )
    return out[out["target_sensitivity"].isin(TARGET_SENSITIVITIES)].reset_index(drop=True)


def alert_window(frame: pd.DataFrame) -> pd.DataFrame:
    """Rows inside the published monitored window, with a finite score."""
    return frame[
        (frame["t_to_event"] > 0)
        & (frame["t_to_event"] <= ALERT_WINDOW_MIN)
        & np.isfinite(frame["score"])
    ]


def case_manifest(cohort: str) -> pd.DataFrame:
    """The cohort's manifest with the observable run-up length attached.

    Same construction as A7: for an event case the observable run-up *is* the time from
    the end of the induction exclusion to onset; for a control it runs to the sampled
    pseudo-onset.
    """
    if cohort == "epic_test":
        epic = pd.read_csv(REPO / "outputs" / "runs" / "gap0" / "manifest.csv")
        epic = epic[(epic["source"] == "mover_epic") & epic["subject_id"].notna()]
        _, _, frame = stratified_subject_split_3way(epic, seed=1004)
    else:
        frame = pd.read_csv(
            REPO / "outputs" / "runs" / "gap0" / f"external_{cohort}" / "manifest.csv"
        )
    frame = frame.copy()
    frame["case_id"] = frame["case_id"].astype(str)
    drop = INDUCTION_DROP_MIN[COHORT_SOURCE[cohort]]
    frame["observable_min"] = np.where(
        frame["label"] == 1,
        frame["first_onset_min"] - drop,
        frame["ref_time_min"] - drop,
    )
    return frame


def cluster_codes(case_frame: pd.DataFrame) -> tuple[np.ndarray, int]:
    """Integer cluster codes for a one-row-per-case frame, and the cluster count."""
    codes, clusters = pd.factorize(case_frame["cluster_id"], sort=True)
    return codes, len(clusters)


def weight_matrix(n_clusters: int, rng: np.random.Generator, n_replicates: int) -> np.ndarray:
    """(B, n_clusters) integer multiplicities, one row per cluster-bootstrap replicate.

    Drawn once per cell and reused across every statistic in that cell, which is what
    makes a difference of two statistics a paired difference.
    """
    draws = rng.integers(0, n_clusters, size=(n_replicates, n_clusters))
    weights = np.zeros((n_replicates, n_clusters), dtype=np.int32)
    for replicate in range(n_replicates):
        weights[replicate] = np.bincount(draws[replicate], minlength=n_clusters)
    return weights


def bootstrap_p_two_sided(draws: np.ndarray, null: float = 0.0) -> float:
    """Two-sided bootstrap p for ``statistic != null``, by interval inversion.

    ``2 * min(P(draw <= null), P(draw >= null))`` capped at 1.  With B replicates the
    smallest reportable value is ``2 / B``; it is reported as such rather than as 0, so a
    Benjamini-Hochberg step never divides by a p-value the resampling could not produce.
    """
    finite = np.asarray(draws, float)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return float("nan")
    below = float((finite <= null).mean())
    above = float((finite >= null).mean())
    p = 2.0 * min(below, above)
    return float(min(1.0, max(p, 2.0 / finite.size)))


def iqr_text(lo: float, mid: float, hi: float, digits: int = 1) -> str:
    if not np.isfinite(mid):
        return "—"
    return f"{mid:.{digits}f} ({lo:.{digits}f}–{hi:.{digits}f})"


__all__ = [
    "ALERT_WINDOW_MIN",
    "BIN_CENTERS",
    "BOOTSTRAP_SEED",
    "COHORT_LABELS",
    "COHORT_ORDER",
    "COHORT_SOURCE",
    "FAMILY_LABELS",
    "FAMILY_ORDER",
    "HEADLINE_TARGET",
    "HERE",
    "INDUCTION_DROP_MIN",
    "N_BOOTSTRAP_PATIENT",
    "REPO",
    "TARGET_SENSITIVITIES",
    "THRESHOLD_CSV",
    "alert_window",
    "assign_bin",
    "bh_adjust",
    "bootstrap_p_two_sided",
    "case_manifest",
    "cluster_codes",
    "df_to_md",
    "iqr_text",
    "load_scored",
    "percentile_ci",
    "seed_for",
    "thresholds",
    "weight_matrix",
    "weighted_fraction",
    "weighted_median",
    "weighted_spearman",
    "write_manifest",
]
