"""Number-Needed-to-Evaluate (NNE) / alert-burden curve.

For a per-minute trajectory, NNE at threshold `θ` =
  (positive alerts) / (true positives caught)
= 1 / PPV at that threshold.

Equivalently it's "for every detected upcoming event, how many alerts
does the clinician have to triage?" Lower = better. NNE = ∞ means the
threshold caught nothing.

In the AKI eval, NNE is reported per time window and per threshold. Here
we expose two helpers:

  - `alert_burden_curve`: NNE vs threshold (one trajectory, one curve).
  - `nne_at_target_sensitivity`: pick the threshold that hits a target
    sensitivity, and return the corresponding NNE. Useful for headline
    numbers like "NNE = 4.2 at 80% sensitivity".

Both work on a flat `(scores, labels)` pair. For per-window NNE just
filter the predictions first and call again.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def alert_burden_curve(
    scores: np.ndarray,
    labels: np.ndarray,
    n_points: int = 101,
) -> pd.DataFrame:
    """NNE, PPV, sensitivity at evenly spaced thresholds in [0, 1].

    Returns columns: threshold, n_alerts, tp, fp, fn, ppv, sensitivity, nne.
    """
    scores = np.asarray(scores, dtype=np.float64)
    labels = np.asarray(labels, dtype=np.int64)
    if scores.size != labels.size:
        raise ValueError(f"size mismatch: scores={scores.size} labels={labels.size}")

    thresholds = np.linspace(0.0, 1.0, n_points)
    rows = []
    pos_total = int(labels.sum())
    for th in thresholds:
        pred = scores >= th
        tp = int(((pred) & (labels == 1)).sum())
        fp = int(((pred) & (labels == 0)).sum())
        fn = pos_total - tp
        ppv = tp / (tp + fp) if (tp + fp) > 0 else float("nan")
        sens = tp / pos_total if pos_total > 0 else float("nan")
        nne = (tp + fp) / tp if tp > 0 else float("inf")
        rows.append(
            dict(
                threshold=float(th),
                n_alerts=tp + fp,
                tp=tp,
                fp=fp,
                fn=fn,
                ppv=ppv,
                sensitivity=sens,
                nne=nne,
            )
        )
    return pd.DataFrame(rows)


def nne_at_target_sensitivity(
    scores: np.ndarray,
    labels: np.ndarray,
    target_sensitivity: float = 0.80,
    n_points: int = 1001,
) -> dict:
    """Find the highest-threshold operating point whose sensitivity is
    at least `target_sensitivity`. Returns threshold, sensitivity,
    PPV, and NNE at that point.
    """
    curve = alert_burden_curve(scores, labels, n_points=n_points)
    qualifying = curve[curve["sensitivity"] >= target_sensitivity]
    if qualifying.empty:
        return dict(
            threshold=float("nan"),
            sensitivity=float("nan"),
            ppv=float("nan"),
            nne=float("inf"),
            note=f"no threshold achieves sensitivity >= {target_sensitivity}",
        )
    # Highest threshold (most conservative) that still meets target.
    pick = qualifying.loc[qualifying["threshold"].idxmax()]
    return dict(
        threshold=float(pick["threshold"]),
        sensitivity=float(pick["sensitivity"]),
        ppv=float(pick["ppv"]),
        nne=float(pick["nne"]),
        note=None,
    )
