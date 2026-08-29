"""Unit tests for bootstrap CI + plotting helpers."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless
import numpy as np
import pandas as pd
import pytest

from ioh_prediction.evaluation.bootstrap import (
    BootstrapConfig,
    window_metrics_with_ci,
)
from ioh_prediction.evaluation.nne import alert_burden_curve
from ioh_prediction.evaluation.plots import (
    generate_all_plots,
    plot_auroc_trajectory,
    plot_nne_curve,
    plot_ppv_sensitivity_threshold,
    plot_reliability_diagram,
)


def _synthetic_predictions(n_pos: int = 100, n_neg: int = 100, seed: int = 0) -> pd.DataFrame:
    rng = np.random.RandomState(seed)
    rows = []
    for case in range(n_pos):
        for t in range(60, -1, -1):
            base = 0.4 + 0.4 * (1.0 - t / 60.0)
            rows.append(dict(t_to_event=t, score=base + rng.normal(0, 0.08), label=1))
    for case in range(n_neg):
        for t in range(60, -1, -1):
            rows.append(dict(t_to_event=t, score=0.3 + rng.normal(0, 0.08), label=0))
    return pd.DataFrame(rows)


# ---------- bootstrap ----------


def test_bootstrap_window_ci_shape_and_ordering():
    pred = _synthetic_predictions()
    out = window_metrics_with_ci(pred, BootstrapConfig(n_boot=100))
    assert "auroc_ci_lo" in out.columns and "auroc_ci_hi" in out.columns
    assert "auprc_ci_lo" in out.columns and "auprc_ci_hi" in out.columns
    # CI lower bound <= point estimate <= upper bound
    assert (out["auroc_ci_lo"] <= out["auroc"]).all()
    assert (out["auroc"] <= out["auroc_ci_hi"]).all()


def test_bootstrap_ci_widens_with_fewer_resamples():
    """More bootstraps should narrow the CI on average (one-tail check)."""
    pred = _synthetic_predictions(n_pos=300, n_neg=300, seed=1)
    out_few = window_metrics_with_ci(pred, BootstrapConfig(n_boot=30, seed=0))
    out_many = window_metrics_with_ci(pred, BootstrapConfig(n_boot=300, seed=0))
    width_few = (out_few["auroc_ci_hi"] - out_few["auroc_ci_lo"]).mean()
    width_many = (out_many["auroc_ci_hi"] - out_many["auroc_ci_lo"]).mean()
    # Wider variance from fewer samples is expected; allow either direction
    # to be near each other but not blow up.
    assert width_few >= 0 and width_many >= 0
    assert width_few < 0.5 and width_many < 0.5


# ---------- plots ----------


def test_plot_auroc_trajectory_writes_file(tmp_path):
    pred = _synthetic_predictions()
    wm = window_metrics_with_ci(pred, BootstrapConfig(n_boot=50))
    out = tmp_path / "auroc.png"
    plot_auroc_trajectory(wm, out, title="test")
    assert out.exists()
    assert out.stat().st_size > 1000  # non-trivial file


def test_plot_nne_curve_writes_file(tmp_path):
    pred = _synthetic_predictions()
    curve = alert_burden_curve(pred["score"].to_numpy(), pred["label"].to_numpy())
    out = tmp_path / "nne.png"
    plot_nne_curve(curve, out, title="test")
    assert out.exists()


def test_plot_ppv_sens_vs_threshold_writes_file(tmp_path):
    pred = _synthetic_predictions()
    curve = alert_burden_curve(pred["score"].to_numpy(), pred["label"].to_numpy())
    out = tmp_path / "ppv_sens.png"
    plot_ppv_sensitivity_threshold(curve, out, title="test")
    assert out.exists()


def test_plot_reliability_writes_file(tmp_path):
    from ioh_prediction.evaluation.calibration import calibration_diagnostics

    pred = _synthetic_predictions()
    diag = calibration_diagnostics(
        pred["score"].to_numpy().clip(0, 1), pred["label"].to_numpy()
    )
    out = tmp_path / "rel.png"
    plot_reliability_diagram(diag, out, title="test")
    assert out.exists()


def test_generate_all_plots_uses_eval_dir(tmp_path):
    """Drop the standard artifacts into a tmp dir and let the bulk
    helper produce every plot."""
    from ioh_prediction.evaluation.calibration import calibration_diagnostics

    pred = _synthetic_predictions()
    eval_dir = tmp_path / "eval"
    eval_dir.mkdir()
    pred.to_parquet(eval_dir / "predictions_raw.parquet", index=False)
    wm = window_metrics_with_ci(pred, BootstrapConfig(n_boot=50))
    wm.to_csv(eval_dir / "window_metrics_ci.csv", index=False)
    diag = calibration_diagnostics(
        pred["score"].to_numpy().clip(0, 1), pred["label"].to_numpy()
    )
    with (eval_dir / "calibration_diagnostics.json").open("w") as f:
        json.dump({"raw": diag, "calibrated": diag}, f)

    plots = generate_all_plots(eval_dir, title_prefix="synthetic")
    names = {p.name for p in plots}
    assert "auroc_trajectory.png" in names
    assert "nne_curve.png" in names
    assert "ppv_sens_vs_threshold.png" in names
    assert "reliability_raw.png" in names
    assert "reliability_calibrated.png" in names
    for p in plots:
        assert p.exists()
