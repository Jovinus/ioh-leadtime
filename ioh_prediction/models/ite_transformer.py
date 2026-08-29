"""ITE Transformer for irregular-time-series IOH prediction.

Mirrors a STraTS-style irregular-time-series encoder previously validated on an
acute kidney injury prediction task, adapted here to binary IOH classification.

Input contract (single 3-D tensor):
  data:  (B, M, 3) float32, columns = [type_id, time, value]
  mask:  (B, M)    bool,    True at real tokens (PAD elsewhere)

`type_id` indexes into the shared embedding table built from
`ioh_prediction/data/schema.py:TYPE_DICT`. Demographics and time-series
channels are *both* tokens — the model has no separate static-feature
path. `time` is in minutes; demographics use `time = 0`, time-series use
`t_offset = t_min - ref_time_min` (≤ 0). `value` is z-score-style
normalized via the train cohort `NormalizerStats`.

Returns: `(B, num_classes)` logits. For binary (num_classes=2), apply
softmax along dim=-1 and take index [1] for P(positive). The
non-squeezed shape is intentional — it lets the same model serve
multi-class (severity, ordinal) without rewriting probability
extraction or the loss.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import torch
from torch import nn

from ..data.schema import N_TYPES


@dataclass(frozen=True)
class ITEConfig:
    n_types: int = N_TYPES
    d_model: int = 128
    num_layers: int = 2
    num_heads: int = 4
    dim_feedforward: int | None = None  # defaults to 4*d_model (AKI)
    dropout: float = 0.1
    # Always uses softmax + CrossEntropy-family losses so the same model
    # extends from binary (num_classes=2) to multi-class without
    # rewriting prob extraction. Set to >2 for, e.g., ordinal severity.
    num_classes: int = 2
    activation: str = "gelu"

    def ffn_dim(self) -> int:
        return self.dim_feedforward if self.dim_feedforward is not None else 4 * self.d_model


class ITE(nn.Module):
    """Triplet embedding: `type_emb + time_emb + value_emb`."""

    def __init__(self, config: ITEConfig):
        super().__init__()
        d = config.d_model
        self.type_emb = nn.Embedding(config.n_types, d)
        self.value_emb = nn.Sequential(
            nn.Linear(1, d), nn.Tanh(), nn.Linear(d, d, bias=False)
        )
        self.time_emb = nn.Sequential(
            nn.Linear(1, d), nn.Tanh(), nn.Linear(d, d, bias=False)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, M, 3) -> [type, time, value]
        type_emb = self.type_emb(x[..., 0].long())
        time_emb = self.time_emb(x[..., 1:2])
        value_emb = self.value_emb(x[..., 2:3])
        return type_emb + time_emb + value_emb


class ITETransformer(nn.Module):
    """STraTS-style encoder + CLS head — binary or multi-class output."""

    def __init__(self, config: ITEConfig = ITEConfig()):
        super().__init__()
        if config.d_model % config.num_heads != 0:
            raise ValueError(
                f"d_model {config.d_model} not divisible by num_heads {config.num_heads}"
            )
        self.config = config
        d = config.d_model

        self.embedding = ITE(config)
        self.cls_token = nn.Parameter(torch.empty(1, 1, d))
        nn.init.normal_(self.cls_token, std=0.02)
        self.dropout = nn.Dropout(config.dropout)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d,
            nhead=config.num_heads,
            dim_feedforward=config.ffn_dim(),
            dropout=config.dropout,
            activation=config.activation,
            batch_first=True,
        )
        # `enable_nested_tensor=False`: PyTorch's TransformerEncoder fast
        # path converts padded inputs to nested tensors during eval, but
        # the required op (`_nested_tensor_from_mask_left_aligned`) is
        # not implemented on MPS. Disabling keeps eval portable across
        # CUDA / MPS / CPU at a negligible CUDA-eval cost.
        self.encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=config.num_layers,
            enable_nested_tensor=False,
        )

        self.classifier = nn.Sequential(
            nn.Linear(d, d),
            nn.Tanh(),
            nn.Dropout(config.dropout),
            nn.Linear(d, config.num_classes),
        )

    def forward(
        self,
        x: torch.Tensor,
        mask: torch.Tensor | None = None,
        return_features: bool = False,
    ) -> torch.Tensor | tuple[torch.Tensor, torch.Tensor]:
        """Forward.

        Args:
            x:    `(B, M, 3)` float, columns = `[type, time, value]`.
            mask: `(B, M)` bool, True at real tokens. Optional; if None,
                  no key-padding mask is applied.
            return_features: also return the CLS feature vector.

        Returns:
            `(B, num_classes)` logits. When `return_features`, additionally
            returns `(B, d_model)`.
        """
        batch_size = x.size(0)

        x = self.dropout(self.embedding(x))             # (B, M, d)
        cls = self.cls_token.expand(batch_size, -1, -1)  # (B, 1, d)
        x = torch.cat([cls, x], dim=1)                   # (B, M+1, d)

        if mask is not None:
            cls_mask = torch.ones(batch_size, 1, dtype=torch.bool, device=mask.device)
            full_mask = torch.cat([cls_mask, mask], dim=1)
            x = self.encoder(x, src_key_padding_mask=~full_mask)
        else:
            x = self.encoder(x)

        cls_features = x[:, 0]                           # (B, d)
        logits = self.classifier(cls_features)           # (B, num_classes)

        return (logits, cls_features) if return_features else logits
