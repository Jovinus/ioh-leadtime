"""Online-simulation evaluation framework for IOH prediction."""

from .bootstrap import BootstrapConfig, window_metrics_with_ci
from .calibration import CalibrationModel, calibration_diagnostics, fit_isotonic
from .mann_kendall import mk_for_metrics, run_mk_test
from .nne import alert_burden_curve, nne_at_target_sensitivity
from .online_inference import (
    OnlineInferenceConfig,
    save_predictions,
    score_case,
    score_manifest,
)
from .plots import (
    generate_all_plots,
    plot_auroc_trajectory,
    plot_nne_curve,
    plot_ppv_sensitivity_threshold,
    plot_reliability_diagram,
)
from .time_window_metrics import WindowConfig, compute_window_metrics

__all__ = [
    "OnlineInferenceConfig",
    "score_case",
    "score_manifest",
    "save_predictions",
    "WindowConfig",
    "compute_window_metrics",
    "BootstrapConfig",
    "window_metrics_with_ci",
    "run_mk_test",
    "mk_for_metrics",
    "alert_burden_curve",
    "nne_at_target_sensitivity",
    "CalibrationModel",
    "fit_isotonic",
    "calibration_diagnostics",
    "generate_all_plots",
    "plot_auroc_trajectory",
    "plot_nne_curve",
    "plot_ppv_sensitivity_threshold",
    "plot_reliability_diagram",
]
