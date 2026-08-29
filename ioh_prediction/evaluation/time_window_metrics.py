"""Time-window metric computation over an online-inference trajectory.

Mirrors `experiments/clinical_faithfulness/step_a_compute_metrics.py` in
the AKI repo, simplified for the IOH (minute-scale) timescale:

  - Bin per-minute predictions by `t_to_event` (minutes before the case's
    reference time — true onset for positives, sampled pseudo-onset for
    negatives).
  - In each bin, compute AUROC, AUPRC, PPV / Sensitivity at fixed
    thresholds, and the Brier score.

Bootstrap CIs are intentionally omitted in v1 to keep the module fast —
add them when needed for publication tables.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    roc_auc_score,
)

# Minute-scale binning. Center of each bin is the value listed here;
# half-width is `WINDOW_SIZE_MIN / 2`. The default sweeps from 60 min
# before onset down to onset in 5-minute steps -- 13 contiguous bins
# that fit naturally onto a single trajectory plot or a landscape
# table page.
DEFAULT_TIME_POINTS_MIN: tuple[int, ...] = (
    60, 55, 50, 45, 40, 35, 30, 25, 20, 15, 10, 5, 0,
)
DEFAULT_WINDOW_SIZE_MIN: int = 2
DEFAULT_PPV_THRESHOLDS: tuple[float, ...] = (0.3, 0.4, 0.5)


@dataclass(frozen=True)
class WindowConfig:
    time_points_min: tuple[int, ...] = DEFAULT_TIME_POINTS_MIN
    window_size_min: int = DEFAULT_WINDOW_SIZE_MIN
    ppv_thresholds: tuple[float, ...] = DEFAULT_PPV_THRESHOLDS
    min_samples_per_window: int = 30


def _metrics_at_threshold(
    y_true: np.ndarray, y_prob: np.ndarray, th: float
) -> tuple[float, float]:
    pred = (y_prob >= th).astype(np.int8)
    tp = int(((pred == 1) & (y_true == 1)).sum())
    fp = int(((pred == 1) & (y_true == 0)).sum())
    fn = int(((pred == 0) & (y_true == 1)).sum())
    ppv = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    sens = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    return ppv, sens


def compute_window_metrics(
    predictions: pd.DataFrame,
    config: WindowConfig = WindowConfig(),
) -> pd.DataFrame:
    """One-row-per-time-window summary.

    `predictions` must have columns `t_to_event`, `score`, `label`.

    Returns rows with: time_window, n_total, n_pos, auroc, auprc, brier,
    and PPV / sensitivity at each configured threshold.
    """
    required = {"t_to_event", "score", "label"}
    missing = required - set(predictions.columns)
    if missing:
        raise ValueError(f"predictions DataFrame missing columns: {missing}")

    half = config.window_size_min / 2.0
    rows: list[dict] = []
    for tp in config.time_points_min:
        lo, hi = tp - half, tp + half
        sub = predictions[
            (predictions["t_to_event"] >= lo) & (predictions["t_to_event"] < hi)
        ]
        n_total = len(sub)
        if n_total < config.min_samples_per_window:
            continue
        y = sub["label"].to_numpy(dtype=np.int64)
        if np.unique(y).size < 2:
            continue
        # Defensive clip — brier_score_loss rejects values outside [0,1].
        p = np.clip(sub["score"].to_numpy(dtype=np.float32), 0.0, 1.0)

        row: dict = {
            "time_window_min": tp,
            "n_total": n_total,
            "n_pos": int(y.sum()),
            "n_neg": int((y == 0).sum()),
            "auroc": float(roc_auc_score(y, p)),
            "auprc": float(average_precision_score(y, p)),
            "brier": float(brier_score_loss(y, p)),
        }
        for th in config.ppv_thresholds:
            ppv, sens = _metrics_at_threshold(y, p, th)
            tag = f"{th:.2f}".replace(".", "")
            row[f"ppv_{tag}"] = ppv
            row[f"sens_{tag}"] = sens
        rows.append(row)

    return pd.DataFrame(rows)
