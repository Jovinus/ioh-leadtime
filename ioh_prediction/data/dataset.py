"""PyTorch datasets for per-minute IOH timeseries.

Two flavors:

  - `IOHCaseDataset` — one *full case* per item (per-minute matrix).
    Used for online-simulation evaluation, where the trainer iterates
    every minute.

  - `IOHRefTimeDataset` — one *training sample per case*, ending at the
    case's `ref_time_min` (event onset for positives, sampled pseudo-onset
    for negatives). Manifests for this are built by
    `ioh_prediction.data.reference_time.build_ref_time_manifest`.

Items returned are raw dicts; tokenization and normalization happen in the
collate function so the same Dataset can serve different model families.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset

from .eligibility import induction_drop_for, training_mask
from .schema import ALL_CHANNELS, PRIMARY_LABEL, STATIC_FEATURES


class IOHCaseDataset(Dataset):
    """One *full case* per item — full per-minute matrix and labels."""

    def __init__(
        self,
        manifest: pd.DataFrame,
        label_column: str = PRIMARY_LABEL,
        channels: tuple[str, ...] = ALL_CHANNELS,
        static_features: tuple[str, ...] = STATIC_FEATURES,
    ):
        required = {"case_id", "source", "parquet_path"}
        missing = required - set(manifest.columns)
        if missing:
            raise ValueError(f"manifest is missing columns: {missing}")

        self.manifest = manifest.reset_index(drop=True)
        self.label_column = label_column
        self.channels = tuple(channels)
        self.static_features = tuple(static_features)

    def __len__(self) -> int:
        return len(self.manifest)

    def __getitem__(self, idx: int) -> dict:
        row = self.manifest.iloc[idx]
        df = pd.read_parquet(row["parquet_path"])
        df = df.sort_values("t_min").reset_index(drop=True)

        vitals = df[list(self.channels)].to_numpy(dtype=np.float32)
        label = df[self.label_column].to_numpy(dtype=np.float32)
        mask = training_mask(df).to_numpy()
        t_min = df["t_min"].to_numpy(dtype=np.int64)

        static = np.array(
            [row[f] for f in self.static_features], dtype=np.float32
        )

        return {
            "case_id": str(row["case_id"]),
            "source": str(row["source"]),
            "vitals": torch.from_numpy(vitals),
            "static": torch.from_numpy(static),
            "label": torch.from_numpy(label),
            "mask": torch.from_numpy(mask),
            "t_min": torch.from_numpy(t_min),
        }


class IOHRefTimeDataset(Dataset):
    """One sample per case, anchored at `ref_time_min`.

    The Dataset loads the *full* case from disk and trims it to
    `[max(induction_drop, ref_time_min - max_lookback_min), ref_time_min)`.
    Triplet conversion and max_seq_len truncation happen in the collate.
    """

    def __init__(
        self,
        manifest: pd.DataFrame,
        window_min: int = 120,
        max_lookback_min: int | None = None,
        channels: tuple[str, ...] = ALL_CHANNELS,
        static_features: tuple[str, ...] = STATIC_FEATURES,
    ):
        required = {"case_id", "source", "parquet_path", "ref_time_min", "label"}
        missing = required - set(manifest.columns)
        if missing:
            raise ValueError(f"manifest is missing columns: {missing}")

        self.manifest = manifest.reset_index(drop=True)
        self.window_min = int(window_min)
        # Optional disk-side trim: load only the rows we'll use. Defaults
        # to window_min (same as the model's lookback).
        self.max_lookback_min = int(max_lookback_min or window_min)
        self.channels = tuple(channels)
        self.static_features = tuple(static_features)

    def __len__(self) -> int:
        return len(self.manifest)

    def __getitem__(self, idx: int) -> dict:
        row = self.manifest.iloc[idx]
        src = str(row["source"])
        ref_t = int(row["ref_time_min"])
        drop = induction_drop_for(src)
        lo = max(drop, ref_t - self.max_lookback_min)

        df = pd.read_parquet(row["parquet_path"])
        df = df[(df["t_min"] >= lo) & (df["t_min"] < ref_t)]
        df = df.sort_values("t_min").reset_index(drop=True)

        vitals = df[list(self.channels)].to_numpy(dtype=np.float32)
        t_min = df["t_min"].to_numpy(dtype=np.int32)
        # `sex` and other categorical-ish columns in cases.parquet use
        # pandas nullable dtypes (Int8/Int64). A direct `np.array(...,
        # dtype=np.float32)` on a list containing `pd.NA` raises
        # TypeError. Cast through `pd.to_numeric(..., errors="coerce")`
        # so missing values become NaN cleanly.
        static = pd.to_numeric(
            pd.Series([row[f] for f in self.static_features]),
            errors="coerce",
        ).to_numpy(dtype=np.float32)

        return {
            "case_id": str(row["case_id"]),
            "source": src,
            "ref_time_min": ref_t,
            "label": float(row["label"]),
            "vitals": vitals,         # (T, C) float32 with NaNs
            "t_min": t_min,           # (T,) int32
            "static": static,         # (S,) float32
        }
