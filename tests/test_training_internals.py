"""Unit tests for loss factory and metrics module."""

from __future__ import annotations

import numpy as np
import pytest
import torch

from ioh_prediction.training import CosineCELoss, binary_metrics, build_loss
from ioh_prediction.training.metrics import multiclass_metrics


# ---------- losses ----------


def test_build_loss_cross_entropy_returns_module():
    crit = build_loss("cross_entropy", num_classes=2)
    assert isinstance(crit, torch.nn.CrossEntropyLoss)


def test_build_loss_cosine_ce_returns_cosine_module():
    crit = build_loss("cosine_ce", num_classes=2)
    assert isinstance(crit, CosineCELoss)


def test_build_loss_rejects_unknown():
    with pytest.raises(ValueError, match="Unknown loss_type"):
        build_loss("triplet", num_classes=2)


def test_cosine_ce_loss_runs_backward():
    crit = CosineCELoss(num_classes=2)
    logits = torch.randn(4, 2, requires_grad=True)
    labels = torch.tensor([0, 1, 0, 1])
    loss = crit(logits, labels)
    loss.backward()
    assert torch.isfinite(loss).item()
    assert logits.grad is not None and torch.isfinite(logits.grad).all()


def test_cross_entropy_with_class_weights():
    crit = build_loss("cross_entropy", num_classes=2, class_weights=[1.0, 5.0])
    logits = torch.randn(8, 2)
    labels = torch.randint(0, 2, (8,))
    loss = crit(logits, labels)
    assert torch.isfinite(loss).item()


# ---------- metrics ----------


def test_binary_metrics_keys():
    rng = np.random.RandomState(0)
    probs = rng.uniform(0, 1, 200)
    labels = (probs + rng.normal(0, 0.1, 200) > 0.5).astype(int)
    m = binary_metrics(probs, labels)
    assert set(m.keys()) >= {
        "auroc",
        "auprc",
        "accuracy",
        "ppv",
        "sensitivity",
        "f1",
        "brier",
    }
    for v in m.values():
        assert 0.0 <= v <= 1.0 or v != v  # NaN allowed for edge cases


def test_binary_metrics_perfect_separation():
    probs = np.array([0.05, 0.1, 0.9, 0.95])
    labels = np.array([0, 0, 1, 1])
    m = binary_metrics(probs, labels)
    assert m["auroc"] == 1.0
    assert m["auprc"] == 1.0
    assert m["accuracy"] == 1.0
    assert m["ppv"] == 1.0
    assert m["sensitivity"] == 1.0
    assert m["f1"] == 1.0


def test_binary_metrics_single_class_returns_nan_auroc():
    probs = np.array([0.1, 0.4, 0.2])
    labels = np.array([0, 0, 0])  # only negatives
    m = binary_metrics(probs, labels)
    assert m["auroc"] != m["auroc"]  # NaN
    assert m["accuracy"] == 1.0


def test_multiclass_metrics_keys_and_shape():
    rng = np.random.RandomState(0)
    probs = rng.dirichlet(np.ones(3), size=200)
    labels = rng.randint(0, 3, 200)
    m = multiclass_metrics(probs, labels, num_classes=3)
    assert set(m.keys()) >= {"auroc", "auprc", "accuracy", "ppv", "sensitivity", "f1"}
