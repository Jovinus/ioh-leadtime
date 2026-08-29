"""Classification metrics powered by torchmetrics.

We switched off sklearn (`roc_auc_score`, etc.) for the trainer hot path
because:

  - torchmetrics' functional API accepts tensors directly, so it works
    without forcing CPU/numpy round-trips during validation.
  - It handles edge cases (single-class batches, label dtype quirks)
    without raising opaque "multi_class must be in (...)" errors.
  - The same module exposes binary and multi-class variants, so the
    code path stays uniform when we extend to multi-class IOH severity.

Two entrypoints:

  - `binary_metrics(probs_positive, labels)` returns AUROC, AUPRC,
    Accuracy, PPV, Sensitivity, F1, Brier at the default threshold 0.5.
  - `multiclass_metrics(probs, labels, num_classes)` returns macro-
    averaged equivalents.

Both accept torch Tensors or numpy arrays / Python lists; they coerce
internally. NaNs are returned for AUROC/AUPRC when only one class is
present in a validation batch (torchmetrics' default behaviour).
"""

from __future__ import annotations

from typing import Union

import numpy as np
import torch
from torchmetrics.functional.classification import (
    binary_accuracy,
    binary_auroc,
    binary_average_precision,
    binary_f1_score,
    binary_precision,
    binary_recall,
    multiclass_accuracy,
    multiclass_auroc,
    multiclass_average_precision,
    multiclass_f1_score,
    multiclass_precision,
    multiclass_recall,
)

ArrayLike = Union[torch.Tensor, np.ndarray, list, tuple]


def _as_tensor(x: ArrayLike, dtype: torch.dtype) -> torch.Tensor:
    if isinstance(x, torch.Tensor):
        return x.detach().to(dtype=dtype).flatten()
    return torch.as_tensor(np.asarray(x), dtype=dtype).flatten()


def _brier(probs: torch.Tensor, labels: torch.Tensor) -> float:
    return float(((probs.float() - labels.float()) ** 2).mean().item())


def _safe(metric_fn, *args, **kwargs) -> float:
    """Call a torchmetrics function and return float; emit a one-line
    warning on failure (rather than swallowing the exception silently).
    """
    try:
        v = metric_fn(*args, **kwargs)
    except Exception as exc:  # pragma: no cover - diagnostic
        import warnings

        warnings.warn(
            f"metric {getattr(metric_fn, '__name__', metric_fn)} failed: {exc}",
            RuntimeWarning,
            stacklevel=2,
        )
        return float("nan")
    return float(v.item()) if torch.is_tensor(v) else float(v)


def binary_metrics(
    probs_positive: ArrayLike,
    labels: ArrayLike,
    threshold: float = 0.5,
) -> dict[str, float]:
    """AUROC / AUPRC / Accuracy / PPV / Sensitivity / F1 / Brier."""
    p = _as_tensor(probs_positive, torch.float32).clamp(0.0, 1.0)
    y = _as_tensor(labels, torch.long)
    if p.shape != y.shape:
        raise ValueError(f"shape mismatch: probs={p.shape} labels={y.shape}")

    if torch.unique(y).numel() < 2:
        auroc = float("nan")
        auprc = float("nan")
    else:
        auroc = _safe(binary_auroc, p, y)
        auprc = _safe(binary_average_precision, p, y)

    return {
        "auroc": auroc,
        "auprc": auprc,
        "accuracy": _safe(binary_accuracy, p, y, threshold=threshold),
        "ppv": _safe(binary_precision, p, y, threshold=threshold),
        "sensitivity": _safe(binary_recall, p, y, threshold=threshold),
        "f1": _safe(binary_f1_score, p, y, threshold=threshold),
        "brier": _brier(p, y),
    }


def multiclass_metrics(
    probs: ArrayLike, labels: ArrayLike, num_classes: int
) -> dict[str, float]:
    """Macro-averaged AUROC / AUPRC / accuracy / PPV / sensitivity / F1."""
    if isinstance(probs, torch.Tensor):
        p = probs.detach().to(torch.float32)
    else:
        p = torch.as_tensor(np.asarray(probs), dtype=torch.float32)
    y = _as_tensor(labels, torch.long)
    if p.dim() != 2 or p.size(0) != y.size(0):
        raise ValueError(
            f"shape mismatch: probs={p.shape} labels={y.shape} (expected (N, num_classes) and (N,))"
        )

    return {
        "auroc": _safe(multiclass_auroc, p, y, num_classes=num_classes, average="macro"),
        "auprc": _safe(multiclass_average_precision, p, y, num_classes=num_classes, average="macro"),
        "accuracy": _safe(multiclass_accuracy, p, y, num_classes=num_classes, average="macro"),
        "ppv": _safe(multiclass_precision, p, y, num_classes=num_classes, average="macro"),
        "sensitivity": _safe(multiclass_recall, p, y, num_classes=num_classes, average="macro"),
        "f1": _safe(multiclass_f1_score, p, y, num_classes=num_classes, average="macro"),
    }
