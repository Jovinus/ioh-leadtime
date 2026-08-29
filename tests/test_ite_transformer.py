"""Unit + smoke tests for the ITE Transformer model."""

from __future__ import annotations

import torch

from ioh_prediction.data.schema import N_TYPES
from ioh_prediction.models import ITEConfig, ITETransformer


def _toy_batch(B: int = 4, M: int = 32) -> tuple[torch.Tensor, torch.Tensor]:
    # (type, time, value) — types in [0, N_TYPES), times in [-120, 0], values ~ N(0,1)
    type_ids = torch.randint(0, N_TYPES, (B, M, 1)).float()
    times = torch.randint(-120, 1, (B, M, 1)).float()
    values = torch.randn(B, M, 1)
    x = torch.cat([type_ids, times, values], dim=-1)
    # Variable real-token lengths per sample, all >= 1
    mask = torch.zeros(B, M, dtype=torch.bool)
    for b in range(B):
        n = torch.randint(1, M + 1, (1,)).item()
        mask[b, :n] = True
    return x, mask


def test_forward_returns_2d_for_binary():
    """num_classes=2 must return `(B, 2)` so softmax/CE work naturally."""
    model = ITETransformer(ITEConfig(num_classes=2, d_model=64, num_layers=2))
    x, mask = _toy_batch(B=4, M=32)
    out = model(x, mask)
    assert out.shape == (4, 2), f"expected (4, 2), got {tuple(out.shape)}"
    assert torch.isfinite(out).all()


def test_forward_returns_2d_for_multiclass():
    model = ITETransformer(ITEConfig(num_classes=3, d_model=64, num_layers=2))
    x, mask = _toy_batch(B=4, M=32)
    out = model(x, mask)
    assert out.shape == (4, 3)


def test_return_features():
    model = ITETransformer(ITEConfig(num_classes=2, d_model=64, num_layers=2))
    x, mask = _toy_batch(B=4, M=32)
    logits, feats = model(x, mask, return_features=True)
    assert logits.shape == (4, 2)
    assert feats.shape == (4, 64)


def test_gradient_flows():
    model = ITETransformer(ITEConfig(num_classes=2, d_model=64, num_layers=2))
    x, mask = _toy_batch(B=4, M=32)
    target = torch.randint(0, 2, (4,)).long()
    logits = model(x, mask)
    loss = torch.nn.functional.cross_entropy(logits, target)
    loss.backward()
    # At least the embedding tables should have grads.
    assert model.embedding.type_emb.weight.grad is not None
    assert (model.embedding.type_emb.weight.grad.abs().sum() > 0).item()


def test_mask_affects_output():
    """All-real mask vs all-PAD-after-first should produce different logits."""
    torch.manual_seed(0)
    model = ITETransformer(ITEConfig(num_classes=2, d_model=64, num_layers=2, dropout=0.0))
    model.eval()
    x, _ = _toy_batch(B=2, M=16)
    full_mask = torch.ones(2, 16, dtype=torch.bool)
    sparse_mask = torch.zeros(2, 16, dtype=torch.bool)
    sparse_mask[:, 0] = True
    out_full = model(x, full_mask)
    out_sparse = model(x, sparse_mask)
    assert not torch.allclose(out_full, out_sparse, atol=1e-5)


def test_forward_without_mask():
    """No-mask path should still work (uses CLS attention over everything)."""
    model = ITETransformer(ITEConfig(num_classes=2, d_model=64, num_layers=2))
    x, _ = _toy_batch(B=2, M=16)
    out = model(x)
    assert out.shape == (2, 2)


def test_softmax_index_1_is_positive_probability():
    """softmax(logits)[:, 1] should be in [0, 1] and complement to softmax[:, 0]."""
    model = ITETransformer(ITEConfig(num_classes=2, d_model=64, num_layers=2))
    model.eval()
    x, mask = _toy_batch(B=8, M=32)
    with torch.no_grad():
        logits = model(x, mask)
    probs = torch.softmax(logits, dim=-1)
    assert torch.allclose(probs.sum(dim=-1), torch.ones(8), atol=1e-5)
    assert (probs >= 0).all() and (probs <= 1).all()
