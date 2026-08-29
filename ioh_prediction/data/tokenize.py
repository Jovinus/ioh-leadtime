"""Minute-matrix to STraTS-style triplet conversion.

A *triplet* is `(value, variable_id, t_offset)`:

  - `value`:        the (normalized) scalar at that (minute, channel)
  - `variable_id`:  integer index into `schema.ALL_CHANNELS`
  - `t_offset`:     `t_min - t_ref` (negative; closer to 0 = more recent)

Missing cells (NaN) produce no token — this is what makes the
representation native to irregular sampling.

This module is *normalization-agnostic*: it returns raw values; the caller
applies `(value - median) / iqr` (or whatever) before passing the tokens to
the model.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .schema import ALL_CHANNELS


@dataclass(frozen=True)
class TripletBatch:
    """Token sequence for a single case."""

    value: np.ndarray       # (N,) float32 — raw value
    variable_id: np.ndarray  # (N,) int32   — index into ALL_CHANNELS
    t_offset: np.ndarray    # (N,) int32   — minutes before t_ref (≤ 0)

    def __len__(self) -> int:
        return int(self.value.shape[0])


def matrix_to_triplets(
    matrix: np.ndarray,
    t_min: np.ndarray,
    channels: tuple[str, ...] = ALL_CHANNELS,
) -> TripletBatch:
    """Convert a `(T, C)` minute matrix into triplet tokens.

    Args:
        matrix:   `(T, C)` float array, NaN where the cell is missing.
        t_min:    `(T,)` int array of minute indices (must align with rows).
        channels: feature names, same order as columns of `matrix`. Used
                  only to assert shape and document the variable_id encoding.

    Returns:
        `TripletBatch` — flat arrays of length N where N is the number of
        non-NaN cells in the matrix. Order is row-major (sorted by minute,
        then by channel index).
    """
    if matrix.ndim != 2:
        raise ValueError(f"matrix must be 2D, got shape {matrix.shape}")
    if matrix.shape[1] != len(channels):
        raise ValueError(
            f"matrix has {matrix.shape[1]} channels but schema has {len(channels)}"
        )
    if t_min.shape[0] != matrix.shape[0]:
        raise ValueError(
            f"t_min length {t_min.shape[0]} != matrix rows {matrix.shape[0]}"
        )

    rows, cols = np.where(~np.isnan(matrix))
    values = matrix[rows, cols].astype(np.float32)
    var_ids = cols.astype(np.int32)
    offsets = t_min[rows].astype(np.int32)
    return TripletBatch(value=values, variable_id=var_ids, t_offset=offsets)


def window_triplets(
    triplets: TripletBatch,
    t_ref: int,
    window_min: int,
    induction_drop: int,
    max_seq_len: int,
) -> TripletBatch:
    """Slice triplets to `[max(induction_drop, t_ref - window_min), t_ref)` and
    cap to `max_seq_len` tokens (keep most recent on overflow).

    Also rewrites `t_offset` to be relative to `t_ref` (≤ 0 for kept tokens).
    """
    lo = max(induction_drop, t_ref - window_min)
    hi = t_ref  # exclusive
    keep = (triplets.t_offset >= lo) & (triplets.t_offset < hi)
    val = triplets.value[keep]
    var = triplets.variable_id[keep]
    off = triplets.t_offset[keep] - np.int32(t_ref)  # now ≤ 0

    if val.shape[0] > max_seq_len:
        # Most-recent truncation: sort by offset (descending = newest first),
        # take the first `max_seq_len`, then restore chronological order.
        order_newest = np.argsort(-off, kind="stable")
        keep_idx = np.sort(order_newest[:max_seq_len])
        val = val[keep_idx]
        var = var[keep_idx]
        off = off[keep_idx]

    return TripletBatch(value=val, variable_id=var, t_offset=off)
