"""Loss functions for softmax-based classification.

We deliberately use multi-class softmax + CrossEntropy-family losses for
the binary IOH task so the same head can be reused for ordinal or
multi-class extensions without changing probability extraction.

Available:
  - "cross_entropy": plain `nn.CrossEntropyLoss(weight=class_weights)`.
  - "cosine_ce":     `0.1 * CE + (1 - cosine_similarity(logits, one_hot(target)))`.
                     Robust to very small probability differences — useful
                     when most cases sit near the decision boundary.
                     Adapted from the user's AKI repo
                     (`shared/losses/custom_loss.py::Cosine_Loss`).

Usage from the trainer:
    criterion = build_loss(
        loss_type="cosine_ce",
        num_classes=2,
        class_weights=None,        # or torch.tensor([w_neg, w_pos])
    )
"""

from __future__ import annotations

from typing import Optional, Sequence

import torch
from torch import nn
from torch.nn import functional as F


class CosineCELoss(nn.Module):
    """`ce_weight * CE + (1 - cosine_similarity(logits, one_hot(target)))`.

    Mirrors the user's prior AKI implementation:
        loss = cosine_term + 0.1 * cross_entropy

    The cosine-embedding term anchors the *direction* of the logit
    vector to the one-hot target, which is robust to logit magnitudes
    that are tiny near the start of training.
    """

    def __init__(
        self,
        num_classes: int,
        ce_weight: float = 0.1,
        class_weights: Optional[torch.Tensor] = None,
    ) -> None:
        super().__init__()
        self.num_classes = int(num_classes)
        self.ce_weight = float(ce_weight)
        self.cross_entropy = nn.CrossEntropyLoss(weight=class_weights)
        self.cosine = nn.CosineEmbeddingLoss(reduction="mean")
        # The constant +1 target for CosineEmbeddingLoss means "pull the
        # two vectors to face the same direction".
        self.register_buffer("_target_dir", torch.tensor([1.0]))

    def forward(self, logits: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        # logits: (B, C),  labels: (B,) int64
        ce = self.cross_entropy(logits, labels)
        one_hot = F.one_hot(labels, num_classes=self.num_classes).float()
        cosine_term = self.cosine(
            logits,
            one_hot,
            self._target_dir.expand(logits.size(0)).to(logits.dtype),
        )
        return cosine_term + self.ce_weight * ce


def build_loss(
    loss_type: str,
    num_classes: int,
    class_weights: Optional[Sequence[float]] = None,
    cosine_ce_weight: float = 0.1,
) -> nn.Module:
    """Factory used by the trainer.

    Args:
        loss_type: "cross_entropy" or "cosine_ce".
        num_classes: needed by cosine_ce.
        class_weights: per-class scalar weights for handling imbalance.
            Applied to the CE term in both supported losses.
        cosine_ce_weight: scalar in front of CE inside `cosine_ce`.
    """
    weight_tensor = (
        torch.tensor(list(class_weights), dtype=torch.float32)
        if class_weights is not None
        else None
    )
    if loss_type == "cross_entropy":
        return nn.CrossEntropyLoss(weight=weight_tensor)
    if loss_type == "cosine_ce":
        return CosineCELoss(
            num_classes=num_classes,
            ce_weight=cosine_ce_weight,
            class_weights=weight_tensor,
        )
    raise ValueError(
        f"Unknown loss_type={loss_type!r}. Expected 'cross_entropy' or 'cosine_ce'."
    )
