"""Collate function for the ITE Transformer.

The model expects a single 3-D input tensor `(B, M, 3)` whose last axis is
`[type_id, time, value]` for each token. This collate:

  1. Builds per-case demographic triplets (one token per static feature,
     all with `time = 0`) — these go FIRST in the sequence so they are
     consistently positioned.
  2. Builds per-case time-series triplets from each non-NaN cell in the
     `[max(induction_drop, ref_time - W), ref_time)` window using
     `matrix_to_triplets`. Time encoded as `t_min - ref_time_min` (≤ 0).
  3. Concatenates statics + time-series tokens, normalizes the value
     column with the train-cohort `NormalizerStats`, and caps to
     `max_seq_len` (keep most recent on overflow, but always keep the
     demographic prefix).
  4. Right-pads to `max_seq_len`, producing:
       data: (B, M, 3) float32  — pad rows are zeros
       mask: (B, M)    bool     — True at real tokens (matches AKI repo)
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch

from .normalize import NormalizerStats
from .schema import ALL_CHANNELS, STATIC_FEATURES, TYPE_DICT
from .tokenize import matrix_to_triplets


@dataclass(frozen=True)
class CollateConfig:
    max_seq_len: int = 2048
    pad_value: float = 0.0       # data row for PAD positions (all 3 cols)


class RefTimeCollate:
    """Stateful collate (holds the normalizer)."""

    def __init__(
        self,
        normalizer: NormalizerStats,
        config: CollateConfig = CollateConfig(),
        channels: tuple[str, ...] = ALL_CHANNELS,
        static_features: tuple[str, ...] = STATIC_FEATURES,
        type_dict: dict[str, int] = TYPE_DICT,
    ):
        self.config = config
        self.channels = tuple(channels)
        self.static_features = tuple(static_features)
        self.type_dict = dict(type_dict)

        # Pre-aligned normalization vectors so we don't look up by name in
        # the hot path.
        self.channel_median, self.channel_iqr = normalizer.lookup(self.channels)
        self.static_median, self.static_iqr = normalizer.lookup(self.static_features)

        # Pre-aligned type ids.
        self.channel_type_ids = np.array(
            [self.type_dict[c] for c in self.channels], dtype=np.int32
        )
        self.static_type_ids = np.array(
            [self.type_dict[c] for c in self.static_features], dtype=np.int32
        )

    def __call__(self, batch: list[dict]) -> dict[str, torch.Tensor]:
        cfg = self.config
        M = cfg.max_seq_len
        B = len(batch)
        S = len(self.static_features)

        data = np.full((B, M, 3), cfg.pad_value, dtype=np.float32)
        mask = np.zeros((B, M), dtype=bool)
        labels = np.zeros((B,), dtype=np.float32)
        case_ids: list[str] = []
        sources: list[str] = []
        ref_times: list[int] = []

        for i, item in enumerate(batch):
            ref_t = int(item["ref_time_min"])

            # --- Demographics: one triplet per static feature, time=0 ---
            stat_raw = item["static"]  # (S,) float32, may contain NaN
            stat_norm = (stat_raw - self.static_median) / self.static_iqr
            # Replace NaN demographics with 0 (already normalized).
            stat_norm = np.nan_to_num(stat_norm, nan=0.0).astype(np.float32)
            # rows: [type_id, time=0, value]
            stat_rows = np.stack(
                [
                    self.static_type_ids.astype(np.float32),
                    np.zeros(S, dtype=np.float32),
                    stat_norm,
                ],
                axis=-1,
            )

            # --- Time-series: triplets from non-NaN cells in the window ---
            vitals = item["vitals"]                       # (T, C) raw
            tmin = item["t_min"].astype(np.int32)
            normed = (vitals - self.channel_median) / self.channel_iqr
            triplets = matrix_to_triplets(normed, tmin, channels=self.channels)
            ts_type_ids = self.channel_type_ids[triplets.variable_id].astype(np.float32)
            ts_time = (triplets.t_offset - np.int32(ref_t)).astype(np.float32)  # ≤ 0
            ts_value = triplets.value.astype(np.float32)
            ts_rows = np.stack([ts_type_ids, ts_time, ts_value], axis=-1)

            # --- Compose: demographics (fixed prefix) + ts ---
            # Always keep the demographic prefix; truncate the TS tail if
            # the total would exceed M.
            ts_budget = M - S
            if ts_rows.shape[0] > ts_budget:
                # Keep most recent ts_budget tokens (largest t_offset).
                order_newest = np.argsort(-ts_rows[:, 1], kind="stable")
                keep_idx = np.sort(order_newest[:ts_budget])
                ts_rows = ts_rows[keep_idx]

            n_ts = ts_rows.shape[0]
            n_total = S + n_ts
            data[i, :S] = stat_rows
            data[i, S : S + n_ts] = ts_rows
            mask[i, :n_total] = True

            labels[i] = item["label"]
            case_ids.append(item["case_id"])
            sources.append(item["source"])
            ref_times.append(ref_t)

        return {
            "data": torch.from_numpy(data),         # (B, M, 3) float32
            "mask": torch.from_numpy(mask),         # (B, M) bool
            "label": torch.from_numpy(labels),      # (B,) float32
            "case_id": case_ids,
            "source": sources,
            "ref_time_min": torch.tensor(ref_times, dtype=torch.long),
        }
