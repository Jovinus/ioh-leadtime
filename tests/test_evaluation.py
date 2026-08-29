"""Unit tests for the online-sim evaluation framework."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ioh_prediction.evaluation.calibration import (
    calibration_diagnostics,
    fit_isotonic,
)
from ioh_prediction.evaluation.mann_kendall import mk_for_metrics, run_mk_test
from ioh_prediction.evaluation.nne import (
    alert_burden_curve,
    nne_at_target_sensitivity,
)
from ioh_prediction.evaluation.time_window_metrics import (
    WindowConfig,
    compute_window_metrics,
)


# ---------- time_window_metrics ----------


def _synthetic_predictions(n_pos: int = 200, n_neg: int = 200, seed: int = 0):
    rng = np.random.RandomState(seed)
    rows = []
    # Positive cases: score increases as t_to_event -> 0.
    for case in range(n_pos):
        for t in range(60, -1, -1):
            # Baseline 0.4 far from event, 0.8 near event.
            base = 0.4 + 0.4 * (1.0 - t / 60.0)
            noise = rng.normal(0, 0.08)
            rows.append(
                dict(case_id=f"p{case}", t_to_event=t, score=base + noise, label=1)
            )
    # Negative cases: flat noise around 0.3.
    for case in range(n_neg):
        for t in range(60, -1, -1):
            rows.append(
                dict(
                    case_id=f"n{case}",
                    t_to_event=t,
                    score=0.3 + rng.normal(0, 0.08),
                    label=0,
                )
            )
    return pd.DataFrame(rows)


def test_compute_window_metrics_has_one_row_per_time_point():
    df = _synthetic_predictions()
    out = compute_window_metrics(df, WindowConfig(window_size_min=2, min_samples_per_window=10))
    assert len(out) > 0
    assert set(out.columns) >= {"time_window_min", "auroc", "auprc", "brier", "ppv_030", "sens_030"}
    # All time points produced should be subset of DEFAULT_TIME_POINTS_MIN.
    from ioh_prediction.evaluation.time_window_metrics import DEFAULT_TIME_POINTS_MIN

    assert set(out["time_window_min"]).issubset(set(DEFAULT_TIME_POINTS_MIN))


def test_compute_window_metrics_auroc_rises_near_event():
    df = _synthetic_predictions()
    out = compute_window_metrics(df, WindowConfig(window_size_min=2, min_samples_per_window=10))
    out = out.sort_values("time_window_min", ascending=False).reset_index(drop=True)
    # Synthetic generator makes AUROC at t=60 lower than at t=0.
    assert out["auroc"].iloc[0] < out["auroc"].iloc[-1]


def test_compute_window_metrics_validates_columns():
    bad = pd.DataFrame({"score": [0.5], "label": [1]})  # no t_to_event
    with pytest.raises(ValueError, match=r"t_to_event"):
        compute_window_metrics(bad)


# ---------- mann_kendall ----------


def test_mk_increasing_series_is_positive_and_significant():
    res = run_mk_test(np.linspace(0.5, 0.9, 10))
    assert res["tau"] > 0
    assert res["significant"]
    assert res["trend_direction"] == "increasing"


def test_mk_short_series_returns_insufficient_data():
    res = run_mk_test(np.array([0.5, 0.6, 0.7]))
    assert res["trend_direction"] == "insufficient_data"
    assert not res["significant"]


def test_mk_for_metrics_runs_on_each_column():
    df = pd.DataFrame(
        {
            "time_window_min": [60, 45, 30, 20, 15, 10, 5, 3, 1, 0],
            "auroc": np.linspace(0.6, 0.9, 10),
            "auprc": np.linspace(0.5, 0.85, 10),
            "ppv_030": np.linspace(0.3, 0.7, 10),
            "ppv_050": np.linspace(0.4, 0.8, 10),
        }
    )
    out = mk_for_metrics(df)
    assert set(out["metric"]) == {"auroc", "auprc", "ppv_030", "ppv_050"}
    # All four should detect the increasing trend.
    assert (out["significant"]).all()
    assert (out["tau"] > 0).all()


# ---------- NNE / alert burden ----------


def test_alert_burden_curve_endpoints():
    rng = np.random.RandomState(0)
    scores = np.concatenate([rng.uniform(0.7, 1.0, 100), rng.uniform(0.0, 0.3, 100)])
    labels = np.concatenate([np.ones(100), np.zeros(100)]).astype(int)
    curve = alert_burden_curve(scores, labels, n_points=11)
    # At threshold 0 everything fires: sensitivity=1, ppv=prevalence=0.5, NNE=2
    bottom = curve.iloc[0]
    assert bottom["sensitivity"] == pytest.approx(1.0)
    assert bottom["nne"] == pytest.approx(2.0)
    # At threshold 1 nothing fires: NNE = inf
    top = curve.iloc[-1]
    assert np.isinf(top["nne"])


def test_nne_at_target_sensitivity_picks_qualifying_threshold():
    rng = np.random.RandomState(0)
    scores = np.concatenate([rng.uniform(0.7, 1.0, 100), rng.uniform(0.0, 0.3, 100)])
    labels = np.concatenate([np.ones(100), np.zeros(100)]).astype(int)
    out = nne_at_target_sensitivity(scores, labels, target_sensitivity=0.80)
    assert out["sensitivity"] >= 0.80
    assert np.isfinite(out["nne"])
    # Well-separated -> NNE close to 1.
    assert out["nne"] < 1.5


def test_nne_at_target_sensitivity_handles_infeasible_target():
    scores = np.array([0.1, 0.2, 0.3, 0.4])
    labels = np.array([0, 0, 0, 1])
    out = nne_at_target_sensitivity(scores, labels, target_sensitivity=1.5)
    assert np.isnan(out["sensitivity"])
    assert np.isinf(out["nne"])
    assert out["note"] is not None


# ---------- calibration ----------


def test_isotonic_fit_then_apply_preserves_monotonicity():
    rng = np.random.RandomState(0)
    n = 1000
    raw = rng.uniform(0, 1, n)
    # Miscalibrated true probabilities are raw**2.
    labels = (rng.uniform(0, 1, n) < raw**2).astype(int)
    model = fit_isotonic(raw, labels)
    # Apply: monotone in input.
    grid = np.linspace(0, 1, 50)
    out = model.apply(grid)
    assert np.all(np.diff(out) >= -1e-9)
    assert (out >= 0).all() and (out <= 1).all()


def test_calibration_diagnostics_basic_keys():
    rng = np.random.RandomState(0)
    scores = rng.uniform(0, 1, 500)
    labels = (rng.uniform(0, 1, 500) < scores).astype(int)
    diag = calibration_diagnostics(scores, labels, n_bins=10)
    assert set(diag.keys()) >= {
        "brier",
        "ece",
        "bin_edges",
        "bin_counts",
        "bin_mean_pred",
        "bin_mean_obs",
    }
    assert 0.0 <= diag["brier"] <= 1.0
    assert 0.0 <= diag["ece"] <= 1.0
    assert len(diag["bin_counts"]) == 10
