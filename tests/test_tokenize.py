"""Unit tests for triplet tokenization and windowing."""

from __future__ import annotations

import numpy as np
import pytest

from ioh_prediction.data.schema import ALL_CHANNELS
from ioh_prediction.data.tokenize import (
    TripletBatch,
    matrix_to_triplets,
    window_triplets,
)


def _matrix_with_nans() -> tuple[np.ndarray, np.ndarray]:
    # 3 minutes, all 16 channels. Mark a known subset as non-NaN.
    T, C = 3, len(ALL_CHANNELS)
    m = np.full((T, C), np.nan, dtype=np.float32)
    t_min = np.array([10, 11, 12], dtype=np.int64)

    # Place known non-NaN values:
    #   minute 10, channel 0 (MAP) = 70
    #   minute 11, channel 0 (MAP) = 65
    #   minute 11, channel 6 (HR)  = 80
    #   minute 12, channel 7 (SpO2)= 98
    m[0, 0] = 70.0
    m[1, 0] = 65.0
    m[1, 6] = 80.0
    m[2, 7] = 98.0
    return m, t_min


def test_matrix_to_triplets_skips_nans():
    m, t_min = _matrix_with_nans()
    triplets = matrix_to_triplets(m, t_min)

    assert len(triplets) == 4
    # Order is row-major (sorted by minute, then channel within minute).
    np.testing.assert_array_equal(triplets.t_offset, [10, 11, 11, 12])
    np.testing.assert_array_equal(triplets.variable_id, [0, 0, 6, 7])
    np.testing.assert_array_equal(triplets.value, [70.0, 65.0, 80.0, 98.0])


def test_matrix_to_triplets_validates_shape():
    m = np.zeros((3, 4), dtype=np.float32)
    t_min = np.array([0, 1, 2])
    with pytest.raises(ValueError, match=r"channels"):
        matrix_to_triplets(m, t_min)  # 4 != len(ALL_CHANNELS)


def test_matrix_to_triplets_validates_t_min_alignment():
    m = np.zeros((3, len(ALL_CHANNELS)), dtype=np.float32)
    t_min = np.array([0, 1])  # wrong length
    with pytest.raises(ValueError, match=r"t_min length"):
        matrix_to_triplets(m, t_min)


def test_window_triplets_basic_slice_and_offset():
    m, t_min = _matrix_with_nans()
    triplets = matrix_to_triplets(m, t_min)

    # ref_time = 12, window = 2 minutes → keep t in [10, 12) = {10, 11}
    out = window_triplets(triplets, t_ref=12, window_min=2, induction_drop=0, max_seq_len=10)

    assert len(out) == 3  # (10, MAP), (11, MAP), (11, HR)
    # Offsets are minutes-before-ref, so all ≤ 0.
    assert out.t_offset.tolist() == [-2, -1, -1]
    assert out.variable_id.tolist() == [0, 0, 6]
    assert out.value.tolist() == [70.0, 65.0, 80.0]


def test_window_triplets_respects_induction_drop():
    m, t_min = _matrix_with_nans()
    triplets = matrix_to_triplets(m, t_min)

    # induction_drop=11 → only t >= 11 is kept; ref_time=12 means [11,12)
    out = window_triplets(triplets, t_ref=12, window_min=10, induction_drop=11, max_seq_len=10)
    assert len(out) == 2  # (11, MAP), (11, HR)
    assert out.t_offset.tolist() == [-1, -1]
    assert sorted(out.variable_id.tolist()) == [0, 6]


def test_window_triplets_most_recent_truncation():
    # Build a synthetic triplet batch with offsets [-5, -4, -3, -2, -1].
    val = np.arange(5, dtype=np.float32)
    var = np.zeros(5, dtype=np.int32)
    off = np.arange(-5, 0, dtype=np.int32) + 100  # absolute t_min = 95..99
    triplets = TripletBatch(value=val, variable_id=var, t_offset=off)

    # Window=5 from ref=100 picks all 5 → but cap to max_seq_len=3.
    out = window_triplets(triplets, t_ref=100, window_min=5, induction_drop=0, max_seq_len=3)
    assert len(out) == 3
    # Keeps the 3 most recent offsets: [-3, -2, -1] in chronological order.
    assert out.t_offset.tolist() == [-3, -2, -1]
    assert out.value.tolist() == [2.0, 3.0, 4.0]
