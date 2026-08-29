"""Mann-Kendall trend test on a time-window metric trajectory.

Tests whether AUROC / PPV / etc. shows a monotonic trend as the time
window approaches the event onset.

Convention: input `values` are ordered **from farthest to closest** to the
onset (e.g., at time_points = 60, 45, 30, ..., 1, 0 minutes-before-onset,
the array index 0 is "60 min before"). Then a positive tau means
"improving as we approach onset" — i.e., the model becomes more confident
just before the event.

The AKI repo's `experiments/clinical_faithfulness/step_b_mann_kendall.py`
follows the same convention; matching it here keeps results comparable.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pymannkendall as mk


def run_mk_test(values: np.ndarray) -> dict:
    """Run the Mann-Kendall test on a time-ordered series.

    Returns a dict with `tau`, `p_value`, `trend_direction`,
    `significant`, `sens_slope`, and the raw `z_score` / `s_statistic`.
    NaN-fills the result when the input is too short or all-NaN.
    """
    values = np.asarray(values, dtype=np.float64)
    if values.size < 4 or np.all(np.isnan(values)):
        return {
            "tau": float("nan"),
            "p_value": float("nan"),
            "trend_direction": "insufficient_data",
            "significant": False,
            "z_score": float("nan"),
            "s_statistic": float("nan"),
            "var_s": float("nan"),
            "sens_slope": float("nan"),
            "sens_intercept": float("nan"),
        }
    result = mk.original_test(values[~np.isnan(values)])
    return {
        "tau": float(result.Tau),
        "p_value": float(result.p),
        "trend_direction": str(result.trend),
        "significant": bool(result.p < 0.05),
        "z_score": float(result.z),
        "s_statistic": float(result.s),
        "var_s": float(result.var_s),
        "sens_slope": float(result.slope),
        "sens_intercept": float(result.intercept),
    }


def mk_for_metrics(
    window_metrics: pd.DataFrame,
    metric_cols: tuple[str, ...] = ("auroc", "auprc", "ppv_030", "ppv_050"),
) -> pd.DataFrame:
    """Run MK on every column in `metric_cols` of `window_metrics`.

    `window_metrics` is the output of `compute_window_metrics` (one row
    per time_window_min). We sort so that **farthest-from-onset comes
    first** (descending t_to_event = descending time_window_min).
    """
    df = window_metrics.sort_values("time_window_min", ascending=False).reset_index(drop=True)
    rows = []
    for col in metric_cols:
        if col not in df.columns:
            continue
        res = run_mk_test(df[col].to_numpy())
        res["metric"] = col
        rows.append(res)
    return pd.DataFrame(rows)
