"""Channel-level normalization stats (median / IQR), fit on a train cohort
and serialized to a small parquet so val/test can reuse them without refit.

Mirrors the user's prior AKI repo `shared/data` / `scaling_info` pattern.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from .schema import ALL_CHANNELS, STATIC_FEATURES


@dataclass(frozen=True)
class NormalizerStats:
    """One row per channel: `median`, `iqr`, plus `feature` name."""

    table: pd.DataFrame  # columns: feature, median, iqr

    def lookup(
        self, features: tuple[str, ...] = ALL_CHANNELS
    ) -> tuple[np.ndarray, np.ndarray]:
        """Return aligned `(median, iqr)` arrays in the order of `features`.

        Works for both time-series channels and static demographics — both
        are stored in the same `table` keyed by feature name.
        """
        t = self.table.set_index("feature")
        missing = [f for f in features if f not in t.index]
        if missing:
            raise KeyError(
                f"NormalizerStats missing entries for: {missing}. "
                f"Did you fit with cases_parquet=...?"
            )
        med = np.array([float(t.loc[c, "median"]) for c in features], dtype=np.float32)
        iqr = np.array([float(t.loc[c, "iqr"]) for c in features], dtype=np.float32)
        iqr = np.where(iqr <= 0, 1.0, iqr).astype(np.float32)
        return med, iqr

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.table.to_parquet(path, index=False)

    @classmethod
    def load(cls, path: str | Path) -> "NormalizerStats":
        return cls(table=pd.read_parquet(path))


def fit_normalizer(
    ts_glob: str,
    case_ids: list[str] | None = None,
    sources: list[str] | None = None,
    channels: tuple[str, ...] = ALL_CHANNELS,
    cases_parquet: str | None = None,
    static_features: tuple[str, ...] = STATIC_FEATURES,
) -> NormalizerStats:
    """Compute median + IQR over the given case set for:
      - every channel in `channels` (from the per-minute timeseries), and
      - every demographic in `static_features` (from `cases.parquet`).

    Either pass `case_ids` (preferred — train cases) OR `sources`
    (e.g., `['mover_epic']`). Passing neither uses all data, which is
    almost certainly wrong for training-time normalization.

    `cases_parquet` may be left None when callers only need channel
    stats; in that case static-feature stats are skipped.
    """
    where_clauses: list[str] = []
    if sources:
        src_list = ",".join(f"'{s}'" for s in sources)
        where_clauses.append(f"source IN ({src_list})")
    if case_ids:
        ids = ",".join(f"'{c}'" for c in case_ids)
        where_clauses.append(f"case_id IN ({ids})")
    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    # --- Time-series channel stats ---
    cols_sql = ", ".join(
        f"QUANTILE_CONT({c}, 0.5) AS {c}__median, "
        f"QUANTILE_CONT({c}, 0.75) - QUANTILE_CONT({c}, 0.25) AS {c}__iqr"
        for c in channels
    )
    sql = f"""
    SELECT {cols_sql}
    FROM read_parquet('{ts_glob}', hive_partitioning=true)
    {where_sql}
    """
    row = duckdb.sql(sql).df().iloc[0]
    rows = [
        dict(
            feature=c,
            median=float(row[f"{c}__median"]),
            iqr=float(row[f"{c}__iqr"]),
        )
        for c in channels
    ]

    # --- Static demographic stats ---
    if cases_parquet is not None and static_features:
        scols_sql = ", ".join(
            f"QUANTILE_CONT({c}, 0.5) AS {c}__median, "
            f"QUANTILE_CONT({c}, 0.75) - QUANTILE_CONT({c}, 0.25) AS {c}__iqr"
            for c in static_features
        )
        ssql = f"""
        SELECT {scols_sql}
        FROM read_parquet('{cases_parquet}')
        {where_sql}
        """
        srow = duckdb.sql(ssql).df().iloc[0]
        for c in static_features:
            iqr = float(srow[f"{c}__iqr"])
            # `sex` is binary 0/1 — leave it un-normalized so the embedding
            # / value-emb sees the raw indicator.
            if c == "sex":
                rows.append(dict(feature=c, median=0.0, iqr=1.0))
            else:
                rows.append(
                    dict(
                        feature=c,
                        median=float(srow[f"{c}__median"]),
                        iqr=iqr,
                    )
                )

    return NormalizerStats(table=pd.DataFrame(rows))
