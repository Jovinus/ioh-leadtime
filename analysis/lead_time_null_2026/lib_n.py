"""Shared helpers for N1-N3: is the lead-to-window relationship anything more than arithmetic?

B1b reported that median alert lead time is substantially a measure of observation length:
the ratio ``lead / observed_window`` is 0.455-0.944 and the Spearman correlation between
per-case lead and observed window length is 0.501-0.906 across all fifteen family-by-cohort
cells.  The obvious objection is that lead is *bounded above* by the observed window, so a
positive correlation is partly structural and a ratio below 1 is guaranteed.  N1-N3 answer
that objection before the finding is written up.

* **N1** places a pseudo-crossing uniformly on each case's own window.  Expected median
  ratio 0.5 by construction.  Necessary but weak alone: it only says the observed ratio is
  not what a coin flip would give.
* **N2** permutes whole score sequences across cases inside a cell, preserving each
  recipient's own window length and reference time, and recomputes the crossing against the
  unchanged transported threshold.  This keeps the score's generic temporal profile --
  including the warm-up plateau -- and destroys case-specific information.  It is the one
  that decides how the finding is stated.
* **N3** stratifies by quintile of observed window length and reports median *absolute*
  lead in minutes inside each.  If lead in minutes is flat across quintiles the ratio is
  arithmetic; if it rises with window length the metric tracks observation.

Three things are imported rather than restated:

* ``lib_b`` supplies the validation-fixed thresholds, the published alert window, the case
  manifest with ``observable_min`` attached, and the cluster bootstrap machinery, so N1-N3
  land on exactly the cohorts and operating points B1-B4 used.
* ``lib_pt`` (through ``lib_b``) supplies the cached-score loader and the clustering unit.
* ``per_case_leads`` below reproduces ``b1b_suppression._lead_vs_observation``'s per-case
  construction exactly.  ``step0_repro`` asserts that it reproduces
  ``b1b_lead_vs_observation.csv`` before any N step runs, so a divergence is caught here
  rather than showing up as a null that disagrees with the observed value it is a null for.

N1-N3 are a new multiplicity family.  They are **not** pooled with the 21-trajectory,
15-orientation, A1-A5 or B1-B4 families; ``collect_results`` adjusts within N alone and
records the family size.

Post-hoc on cached per-minute scores.  No model is trained, refitted or re-scored, and no
threshold, split, seed or operating point is reselected.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "analysis" / "lead_time_origin_2026"))

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
    bh_adjust,
    bootstrap_p_two_sided,
    case_manifest,
    cluster_codes,
    df_to_md,
    iqr_text,
    load_scored,
    percentile_ci,
    thresholds,
    weight_matrix,
    weighted_fraction,
    weighted_median,
    weighted_spearman,
    write_manifest,
)

#: Permutation count for N2.  ``N_BOOTSTRAP_OTHER`` in lib_pt, restated here because the
#: number is quoted in the paper and should not move if that constant is retuned for a
#: different purpose.
N_PERMUTATIONS = 1_000

#: Quintiles.  Five bins of observed window length, cut within cell.
N_STRATA = 5

#: Seed offsets on ``BOOTSTRAP_SEED``.  A steps run up to 90,000 and B steps occupy
#: 100,000-130,000, so N takes a block above both.  N4 and N5 were added after the first
#: submission draft and take 180,000 and 190,000, above every block already drawn from, so
#: neither can reuse another step's replicates.
SEED_OFFSETS = {
    "n1": 140_000,
    "n2": 150_000,
    "n3": 160_000,
    "step0": 170_000,
    "n4": 180_000,
    "n5": 190_000,
}


def seed_for(step: str, family: str, cohort: str) -> int:
    return (
        BOOTSTRAP_SEED
        + SEED_OFFSETS[step]
        + FAMILY_ORDER.index(family) * 100
        + COHORT_ORDER.index(cohort)
    )


def headline_cuts() -> pd.Series:
    """The transported raw-score threshold per family at the published 80% target.

    Read through ``lib_b.thresholds``, which asserts the threshold does not vary by cohort
    before returning it.  Never recomputed, never reselected.
    """
    frame = thresholds()
    frame = frame[frame["target_sensitivity"] == HEADLINE_TARGET]
    return frame.set_index("family")["threshold"]


def per_case_all(family: str, cohort: str, cut: float) -> pd.DataFrame:
    """One row per case in the alert window, detected or not, with ``lead`` NaN if it never fires.

    ``per_case_leads`` is this frame filtered to detected event cases.  The two share one
    construction so a denominator computed here can never drift from the numerator computed
    there -- which matters because the detection-rate analysis exists precisely to supply the
    denominator ``per_case_leads`` drops.

    ``lead`` is the *earliest* minute inside the published alert window at which the score is
    at or above the transported cut, expressed as ``t_to_event`` -- so the maximum
    ``t_to_event`` among crossing minutes.  ``observed_min`` is the case's own pre-onset
    observation length capped at the 60-minute alert window, because no crossing can be found
    outside it.
    """
    frame = load_scored(family, cohort)
    frame = frame[(frame["t_to_event"] > 0) & np.isfinite(frame["score"])]
    window = alert_window(frame)
    manifest = case_manifest(cohort).set_index("case_id")

    crossing = window[window["score"] >= cut].groupby("case_id")["t_to_event"].max()
    per_case = window.groupby("case_id").agg(
        label=("label", "first"), cluster_id=("cluster_id", "first")
    )
    per_case["lead"] = crossing
    per_case["observed_min"] = np.minimum(
        manifest["observable_min"].reindex(per_case.index).astype(float),
        float(ALERT_WINDOW_MIN),
    )
    return per_case.reset_index()


def per_case_leads(family: str, cohort: str, cut: float) -> pd.DataFrame:
    """One row per detected event case: its lead, its observed window, its cluster.

    This is ``b1b_suppression._lead_vs_observation``'s per-case construction, lifted so the
    nulls can operate on the same rows the observed statistic is computed from.  Copied
    rather than imported because importing it would mean importing a module whose ``run()``
    rewrites B1b's output directory.  ``step0_repro`` asserts it still reproduces B1b's
    published per-cell values.
    """
    per_case = per_case_all(family, cohort, cut)
    detected = per_case[(per_case["label"] == 1) & per_case["lead"].notna()].copy()
    detected = detected[detected["observed_min"] > 0]
    detected["ratio"] = detected["lead"] / detected["observed_min"]
    return detected.reset_index(drop=True)


def window_matrix(family: str, cohort: str) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    """Every case's alert-window scores on a common elapsed-minute grid.

    Returns ``(scores, valid, cases)`` where ``scores`` and ``valid`` are
    ``(n_cases, ALERT_WINDOW_MIN)`` arrays indexed by **elapsed minutes since the case's own
    first scored minute inside the alert window**, and ``cases`` is the matching one-row-
    per-case frame carrying ``case_id``, ``label``, ``cluster_id`` and ``observed_min``.

    Elapsed alignment, not ``t_to_event`` alignment, is what N2 needs.  A donor sequence
    laid onto a recipient by ``t_to_event`` would carry the donor's distance-to-onset
    structure across and destroy precisely the generic start-of-sequence profile the null is
    meant to preserve.  Laid on by elapsed minute, the plateau survives the permutation and
    only case-specific information is removed.
    """
    frame = load_scored(family, cohort)
    frame = alert_window(frame)
    frame = frame.sort_values(["case_id", "t_to_event"], ascending=[True, False])
    # t_to_event counts down, so descending order is chronological. Elapsed is the rank of
    # the minute within the case's own observed window.
    frame["elapsed"] = frame.groupby("case_id").cumcount()
    frame = frame[frame["elapsed"] < ALERT_WINDOW_MIN]

    cases = (
        frame.groupby("case_id")
        .agg(label=("label", "first"), cluster_id=("cluster_id", "first"))
        .reset_index()
    )
    index = {case_id: i for i, case_id in enumerate(cases["case_id"])}

    scores = np.full((len(cases), ALERT_WINDOW_MIN), np.nan)
    rows = frame["case_id"].map(index).to_numpy()
    scores[rows, frame["elapsed"].to_numpy()] = frame["score"].to_numpy()
    valid = np.isfinite(scores)

    manifest = case_manifest(cohort).set_index("case_id")
    cases["observed_min"] = np.minimum(
        manifest["observable_min"].reindex(cases["case_id"]).astype(float).to_numpy(),
        float(ALERT_WINDOW_MIN),
    )
    cases["n_window_minutes"] = valid.sum(axis=1)
    return scores, valid, cases


def first_crossing_elapsed(scores: np.ndarray, valid: np.ndarray, cut: float) -> np.ndarray:
    """Elapsed index of each row's first at-or-above-``cut`` minute, or -1 if it never is.

    Vectorised over rows: ``argmax`` on a boolean row returns the first ``True``, and a row
    with no ``True`` returns 0, so the ``any`` mask is what separates "crossed at elapsed 0"
    from "never crossed".
    """
    above = valid & (scores >= cut)
    ever = above.any(axis=1)
    first = np.where(ever, above.argmax(axis=1), -1)
    return first


def cluster_bootstrap(case_frame: pd.DataFrame, step: str, family: str, cohort: str,
                      n_replicates: int = N_BOOTSTRAP_PATIENT) -> tuple[np.ndarray, np.ndarray]:
    """``(codes, weights)`` for the paired cluster bootstrap over a one-row-per-case frame.

    The clustering unit is a patient for MOVER (EPIC) and VitalDB and a case for MOVER
    (SIS), whose released ``subject_id`` is a copy of ``case_id``.  ``load_scored`` has
    already attached the right one; this only factorises it.  One weight matrix is drawn per
    cell and reused across every statistic in that cell, which is what makes a difference of
    two statistics a paired difference.
    """
    codes, n_clusters = cluster_codes(case_frame)
    rng = np.random.default_rng(seed_for(step, family, cohort))
    return codes, weight_matrix(n_clusters, rng, n_replicates)


def cells() -> list[tuple[str, str]]:
    """The fifteen family-by-cohort cells, in the published order."""
    return [(family, cohort) for family in FAMILY_ORDER for cohort in COHORT_ORDER]


__all__ = [
    "ALERT_WINDOW_MIN",
    "BOOTSTRAP_SEED",
    "COHORT_LABELS",
    "COHORT_ORDER",
    "FAMILY_LABELS",
    "FAMILY_ORDER",
    "HEADLINE_TARGET",
    "HERE",
    "N_BOOTSTRAP_PATIENT",
    "N_PERMUTATIONS",
    "N_STRATA",
    "REPO",
    "bh_adjust",
    "bootstrap_p_two_sided",
    "cells",
    "cluster_bootstrap",
    "df_to_md",
    "first_crossing_elapsed",
    "headline_cuts",
    "iqr_text",
    "per_case_all",
    "per_case_leads",
    "percentile_ci",
    "seed_for",
    "weighted_fraction",
    "weighted_median",
    "weighted_spearman",
    "window_matrix",
    "write_manifest",
]
