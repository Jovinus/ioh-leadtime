"""Bootstrap confidence intervals for AUROC / AUPRC / PPV at a threshold.

Built as a thin add-on to `time_window_metrics.compute_window_metrics`:
re-runs the same metric in each bin with `n_boot` resamples (with
replacement) and reports the percentile-method 95% CI.

Bins with only one class after resampling produce NaN AUROC; those
draws are silently skipped (matches AKI step_a behaviour).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from .time_window_metrics import (
    DEFAULT_PPV_THRESHOLDS,
    DEFAULT_TIME_POINTS_MIN,
    DEFAULT_WINDOW_SIZE_MIN,
)


@dataclass(frozen=True)
class BootstrapConfig:
    n_boot: int = 1000
    seed: int = 1004
    ci_low: float = 2.5
    ci_high: float = 97.5
    time_points_min: tuple[int, ...] = DEFAULT_TIME_POINTS_MIN
    window_size_min: int = DEFAULT_WINDOW_SIZE_MIN
    ppv_thresholds: tuple[float, ...] = DEFAULT_PPV_THRESHOLDS
    min_samples_per_window: int = 30


def _percentile_ci(arr: list[float], lo: float, hi: float) -> tuple[float, float]:
    if not arr:
        return float("nan"), float("nan")
    a = np.asarray(arr, dtype=np.float64)
    return float(np.percentile(a, lo)), float(np.percentile(a, hi))


def _bootstrap_one_window(
    y: np.ndarray,
    p: np.ndarray,
    thresholds: tuple[float, ...],
    cfg: BootstrapConfig,
) -> dict:
    rng = np.random.RandomState(cfg.seed)
    n = y.size
    idx_all = rng.randint(0, n, size=(cfg.n_boot, n))

    aurocs: list[float] = []
    auprcs: list[float] = []
    ppvs: dict[float, list[float]] = {th: [] for th in thresholds}
    senses: dict[float, list[float]] = {th: [] for th in thresholds}

    for b in range(cfg.n_boot):
        idx = idx_all[b]
        yb, pb = y[idx], p[idx]
        if np.unique(yb).size < 2:
            continue
        aurocs.append(roc_auc_score(yb, pb))
        auprcs.append(average_precision_score(yb, pb))
        for th in thresholds:
            pred = pb >= th
            tp = int(((pred) & (yb == 1)).sum())
            fp = int(((pred) & (yb == 0)).sum())
            fn = int(((~pred) & (yb == 1)).sum())
            ppvs[th].append(tp / (tp + fp) if (tp + fp) > 0 else 0.0)
            senses[th].append(tp / (tp + fn) if (tp + fn) > 0 else 0.0)

    out = {
        "auroc_ci": _percentile_ci(aurocs, cfg.ci_low, cfg.ci_high),
        "auprc_ci": _percentile_ci(auprcs, cfg.ci_low, cfg.ci_high),
    }
    for th in thresholds:
        out[f"ppv_ci_{th:.2f}".replace(".", "")] = _percentile_ci(
            ppvs[th], cfg.ci_low, cfg.ci_high
        )
        out[f"sens_ci_{th:.2f}".replace(".", "")] = _percentile_ci(
            senses[th], cfg.ci_low, cfg.ci_high
        )
    return out


def window_metrics_with_ci(
    predictions: pd.DataFrame,
    config: BootstrapConfig = BootstrapConfig(),
) -> pd.DataFrame:
    """Like `compute_window_metrics` but adds bootstrap CI columns.

    Returns a DataFrame with one row per usable time window and columns:
      time_window_min, n_total, n_pos, n_neg,
      auroc, auroc_ci_lo, auroc_ci_hi,
      auprc, auprc_ci_lo, auprc_ci_hi,
      ppv_<TH>, ppv_<TH>_ci_lo, ppv_<TH>_ci_hi, sens_<TH>, ...
      brier
    """
    half = config.window_size_min / 2.0
    rows: list[dict] = []
    for tp in config.time_points_min:
        lo, hi = tp - half, tp + half
        sub = predictions[
            (predictions["t_to_event"] >= lo) & (predictions["t_to_event"] < hi)
        ]
        if len(sub) < config.min_samples_per_window:
            continue
        y = sub["label"].to_numpy(dtype=np.int64)
        if np.unique(y).size < 2:
            continue
        p = np.clip(sub["score"].to_numpy(dtype=np.float64), 0.0, 1.0)

        row: dict = {
            "time_window_min": tp,
            "n_total": len(sub),
            "n_pos": int(y.sum()),
            "n_neg": int((y == 0).sum()),
            "auroc": float(roc_auc_score(y, p)),
            "auprc": float(average_precision_score(y, p)),
        }
        cis = _bootstrap_one_window(y, p, config.ppv_thresholds, config)
        row["auroc_ci_lo"], row["auroc_ci_hi"] = cis["auroc_ci"]
        row["auprc_ci_lo"], row["auprc_ci_hi"] = cis["auprc_ci"]
        for th in config.ppv_thresholds:
            tag = f"{th:.2f}".replace(".", "")
            pred = p >= th
            tp_ = int((pred & (y == 1)).sum())
            fp_ = int((pred & (y == 0)).sum())
            fn_ = int((~pred & (y == 1)).sum())
            row[f"ppv_{tag}"] = tp_ / (tp_ + fp_) if (tp_ + fp_) > 0 else 0.0
            row[f"sens_{tag}"] = tp_ / (tp_ + fn_) if (tp_ + fn_) > 0 else 0.0
            row[f"ppv_{tag}_ci_lo"], row[f"ppv_{tag}_ci_hi"] = cis[f"ppv_ci_{tag}"]
            row[f"sens_{tag}_ci_lo"], row[f"sens_{tag}_ci_hi"] = cis[f"sens_ci_{tag}"]
        rows.append(row)
    return pd.DataFrame(rows)
