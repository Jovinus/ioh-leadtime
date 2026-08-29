"""Matplotlib plotting helpers for IOH evaluation artifacts.

Each function takes a path-or-DataFrame input and a `save_path`; it returns
the matplotlib Figure so callers can compose into a multi-panel layout if
they want. Plots use the repo defaults (no styling kwargs beyond what's
needed for legibility).
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _save(fig: plt.Figure, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(p, dpi=150, bbox_inches="tight")


def plot_auroc_trajectory(
    window_metrics: pd.DataFrame,
    save_path: str | Path,
    title: str | None = None,
) -> plt.Figure:
    """Line chart of AUROC vs time-to-event. Shows CI band when the
    `auroc_ci_lo` / `auroc_ci_hi` columns are present (i.e., result came
    from `window_metrics_with_ci`)."""
    df = window_metrics.sort_values("time_window_min", ascending=False).reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(df["time_window_min"], df["auroc"], marker="o", color="C0", label="AUROC")
    if "auroc_ci_lo" in df.columns and "auroc_ci_hi" in df.columns:
        ax.fill_between(
            df["time_window_min"],
            df["auroc_ci_lo"],
            df["auroc_ci_hi"],
            alpha=0.2,
            color="C0",
            label="95% CI",
        )
    ax.axhline(0.5, color="grey", linestyle="--", linewidth=0.8, label="chance")
    ax.invert_xaxis()  # 60 -> 0 reads "approaching onset"
    ax.set_xlabel("Minutes before event onset")
    ax.set_ylabel("AUROC")
    ax.set_ylim(0.4, 1.0)
    if title:
        ax.set_title(title)
    ax.legend(loc="lower right")
    _save(fig, save_path)
    return fig


def plot_nne_curve(
    alert_curve: pd.DataFrame,
    save_path: str | Path,
    title: str | None = None,
) -> plt.Figure:
    """NNE vs sensitivity (and the PPV/threshold axes for context)."""
    df = alert_curve.sort_values("sensitivity").reset_index(drop=True)
    # Drop infs/nans for plotting, but keep the operating curve sensible.
    plot_df = df[np.isfinite(df["nne"])]

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(plot_df["sensitivity"], plot_df["nne"], color="C2", label="NNE")
    ax.set_xlabel("Sensitivity (recall)")
    ax.set_ylabel("NNE (alerts per detected event)")
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(bottom=1.0)
    ax.axhline(1.0, color="grey", linestyle=":", linewidth=0.8)
    if title:
        ax.set_title(title)
    ax.legend(loc="upper left")
    _save(fig, save_path)
    return fig


def plot_reliability_diagram(
    diag: dict,
    save_path: str | Path,
    title: str | None = None,
) -> plt.Figure:
    """Reliability diagram from a `calibration_diagnostics` result dict."""
    edges = np.asarray(diag["bin_edges"])
    mid = 0.5 * (edges[:-1] + edges[1:])
    pred = np.asarray(diag["bin_mean_pred"], dtype=float)
    obs = np.asarray(diag["bin_mean_obs"], dtype=float)
    counts = np.asarray(diag["bin_counts"], dtype=int)

    fig, (ax_main, ax_hist) = plt.subplots(
        2, 1, figsize=(6, 6), gridspec_kw={"height_ratios": [4, 1], "hspace": 0.08},
        sharex=True,
    )
    ax_main.plot([0, 1], [0, 1], color="grey", linestyle="--", linewidth=0.8, label="perfect calibration")
    valid = counts > 0
    ax_main.plot(pred[valid], obs[valid], marker="o", color="C3", label="observed")
    ax_main.set_ylabel("Observed event rate")
    ax_main.set_xlim(0.0, 1.0)
    ax_main.set_ylim(0.0, 1.0)
    ax_main.set_title(title or "Reliability diagram")
    ax_main.text(
        0.02, 0.95,
        f"Brier = {diag['brier']:.3f}\nECE   = {diag['ece']:.3f}",
        transform=ax_main.transAxes,
        verticalalignment="top",
        fontfamily="monospace",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
    )
    ax_main.legend(loc="lower right")

    ax_hist.bar(mid, counts, width=(edges[1] - edges[0]) * 0.95, color="C0")
    ax_hist.set_yscale("log")
    ax_hist.set_xlabel("Predicted probability")
    ax_hist.set_ylabel("count")

    _save(fig, save_path)
    return fig


def plot_ppv_sensitivity_threshold(
    alert_curve: pd.DataFrame,
    save_path: str | Path,
    title: str | None = None,
) -> plt.Figure:
    """PPV and Sensitivity vs threshold (alert burden curve view)."""
    df = alert_curve.sort_values("threshold").reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(df["threshold"], df["ppv"], color="C0", label="PPV")
    ax.plot(df["threshold"], df["sensitivity"], color="C1", label="Sensitivity")
    ax.set_xlabel("Threshold")
    ax.set_ylabel("Value")
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    if title:
        ax.set_title(title)
    ax.legend(loc="upper right")
    _save(fig, save_path)
    return fig


def generate_all_plots(
    eval_dir: str | Path,
    title_prefix: str | None = None,
) -> list[Path]:
    """Read the artifacts under `eval_dir` (output of `train.py` post-eval
    OR `evaluate_external.py`) and emit the four standard plots.

    Looks for:
      window_metrics.csv  (or window_metrics_ci.csv if present)
      predictions_raw.parquet (preferred) or val_predictions.parquet
      calibration_diagnostics.json (optional, raw + calibrated)
    """
    from ..evaluation.nne import alert_burden_curve

    eval_dir = Path(eval_dir)
    if not eval_dir.exists():
        raise FileNotFoundError(f"eval dir not found: {eval_dir}")
    out_dir = eval_dir / "plots"

    ci_path = eval_dir / "window_metrics_ci.csv"
    wm_path = eval_dir / "window_metrics.csv"
    if ci_path.exists():
        window = pd.read_csv(ci_path)
    elif wm_path.exists():
        window = pd.read_csv(wm_path)
    else:
        raise FileNotFoundError("Missing window_metrics.csv or window_metrics_ci.csv")

    pred_path = (
        eval_dir / "predictions_raw.parquet"
        if (eval_dir / "predictions_raw.parquet").exists()
        else eval_dir / "val_predictions.parquet"
    )
    predictions = pd.read_parquet(pred_path)
    alert = alert_burden_curve(
        predictions["score"].to_numpy(),
        predictions["label"].to_numpy(),
        n_points=201,
    )

    saved: list[Path] = []
    p = out_dir / "auroc_trajectory.png"
    plot_auroc_trajectory(window, p, title=f"{title_prefix} AUROC over time" if title_prefix else None)
    saved.append(p)
    plt.close("all")

    p = out_dir / "nne_curve.png"
    plot_nne_curve(alert, p, title=f"{title_prefix} NNE curve" if title_prefix else None)
    saved.append(p)
    plt.close("all")

    p = out_dir / "ppv_sens_vs_threshold.png"
    plot_ppv_sensitivity_threshold(alert, p, title=f"{title_prefix} PPV / sensitivity vs threshold" if title_prefix else None)
    saved.append(p)
    plt.close("all")

    diag_path = eval_dir / "calibration_diagnostics.json"
    if diag_path.exists():
        import json
        with diag_path.open() as f:
            diag_pair = json.load(f)
        if "raw" in diag_pair:
            p = out_dir / "reliability_raw.png"
            plot_reliability_diagram(diag_pair["raw"], p, title=f"{title_prefix} reliability (raw)" if title_prefix else None)
            saved.append(p)
            plt.close("all")
        if "calibrated" in diag_pair:
            p = out_dir / "reliability_calibrated.png"
            plot_reliability_diagram(diag_pair["calibrated"], p, title=f"{title_prefix} reliability (isotonic)" if title_prefix else None)
            saved.append(p)
            plt.close("all")
    return saved
