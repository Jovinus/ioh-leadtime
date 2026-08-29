"""Isotonic calibration for the per-minute IOH score.

Fits a monotonic mapping `raw_score -> calibrated_probability` on the
held-out **test** split of the training cohort, reports pre/post
calibration diagnostics on the same test split (so callers can confirm
the isotonic actually helps), then applies the *same fitted calibrator*
to the external cohorts (VitalDB, MOVER) — never re-fit on the externals.

The test split never participates in model training or early-stopping,
so using it as the calibration anchor does not leak into model
selection.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss


@dataclass
class CalibrationModel:
    iso: IsotonicRegression
    fit_n: int

    def apply(self, scores: np.ndarray) -> np.ndarray:
        scores = np.asarray(scores, dtype=np.float64)
        return self.iso.transform(scores)

    def save(self, path: str | Path) -> None:
        import joblib

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @classmethod
    def load(cls, path: str | Path) -> "CalibrationModel":
        import joblib

        return joblib.load(path)


def fit_isotonic(scores: np.ndarray, labels: np.ndarray) -> CalibrationModel:
    """Fit `IsotonicRegression(out_of_bounds='clip')` on a flat set of
    (score, label) pairs. Returns the wrapped model so callers persist a
    single object."""
    scores = np.asarray(scores, dtype=np.float64)
    labels = np.asarray(labels, dtype=np.int64)
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    iso.fit(scores, labels)
    return CalibrationModel(iso=iso, fit_n=int(scores.size))


def calibration_diagnostics(
    scores: np.ndarray, labels: np.ndarray, n_bins: int = 10
) -> dict:
    """Reliability-diagram summary statistics + Brier score.

    Returns: dict with `brier`, `ece` (expected calibration error,
    weighted), `bin_edges`, `bin_counts`, `bin_mean_pred`, `bin_mean_obs`.
    """
    scores = np.asarray(scores, dtype=np.float64)
    labels = np.asarray(labels, dtype=np.int64)
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    bin_idx = np.digitize(scores, bin_edges, right=False) - 1
    bin_idx = np.clip(bin_idx, 0, n_bins - 1)

    counts = np.zeros(n_bins, dtype=np.int64)
    mean_pred = np.zeros(n_bins, dtype=np.float64)
    mean_obs = np.zeros(n_bins, dtype=np.float64)
    for b in range(n_bins):
        m = bin_idx == b
        counts[b] = int(m.sum())
        if counts[b] > 0:
            mean_pred[b] = float(scores[m].mean())
            mean_obs[b] = float(labels[m].mean())
        else:
            mean_pred[b] = float("nan")
            mean_obs[b] = float("nan")

    valid = counts > 0
    if valid.any():
        weights = counts[valid] / counts[valid].sum()
        ece = float(np.sum(weights * np.abs(mean_pred[valid] - mean_obs[valid])))
    else:
        ece = float("nan")

    return dict(
        brier=float(brier_score_loss(labels, scores)),
        ece=ece,
        bin_edges=bin_edges.tolist(),
        bin_counts=counts.tolist(),
        bin_mean_pred=mean_pred.tolist(),
        bin_mean_obs=mean_obs.tolist(),
    )
