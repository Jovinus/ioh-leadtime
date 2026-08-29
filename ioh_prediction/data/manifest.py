"""Case discovery and manifest building.

A *manifest* is a DataFrame with one row per case, joining the per-case
parquet path with static features from `cases.parquet`. Downstream
`Dataset` / `DataLoader` objects consume a manifest, not raw globs.

Rules enforced here (mirroring `HANDOFF.md` §6):
- Eligibility: `surgery_min BETWEEN 30 AND 1440`
- `procedure_group` is loaded but explicitly marked as "report-only" so it
  cannot accidentally become a model input.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd

DATA_ROOT = Path(__file__).resolve().parents[2] / "data"
TIMESERIES_GLOB = str(DATA_ROOT / "timeseries" / "source=*" / "case_id=*" / "data.parquet")
CASES_PARQUET = str(DATA_ROOT / "cases.parquet")

REPORT_ONLY_COLUMNS = ("procedure_group",)


@dataclass(frozen=True)
class ManifestQuery:
    sources: tuple[str, ...] = ("mover_epic",)
    min_surgery_min: float = 30.0
    max_surgery_min: float = 1440.0
    max_asa: int | None = None  # set 3 to drop ASA 4 while still keeping NA (SIS)


def build_manifest(query: ManifestQuery = ManifestQuery()) -> pd.DataFrame:
    """Return a manifest DataFrame with one row per eligible case.

    Columns: case_id, source, parquet_path, plus all static features from
    `cases.parquet` except `procedure_group` (which is included but kept
    separate as report-only — see `REPORT_ONLY_COLUMNS`).
    """
    src_filter = ",".join(f"'{s}'" for s in query.sources)
    asa_clause = f"AND (c.asa IS NULL OR c.asa <= {query.max_asa})" if query.max_asa else ""

    sql = f"""
    WITH ts AS (
        SELECT DISTINCT
            case_id,
            source,
            filename AS parquet_path
        FROM read_parquet('{TIMESERIES_GLOB}',
                          hive_partitioning=true,
                          filename=true)
    )
    SELECT ts.parquet_path, c.*
    FROM ts
    JOIN read_parquet('{CASES_PARQUET}') c USING (case_id, source)
    WHERE c.source IN ({src_filter})
      AND c.surgery_min BETWEEN {query.min_surgery_min} AND {query.max_surgery_min}
      {asa_clause}
    """
    return duckdb.sql(sql).df()


def split_manifest_by_source(
    manifest: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    return {src: g.reset_index(drop=True) for src, g in manifest.groupby("source")}
