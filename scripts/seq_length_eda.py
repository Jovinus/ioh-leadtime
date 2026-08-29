"""Seq-length distribution diagnostics for max_seq_len decision.

Reports per-cohort:
  - Raw case duration (number of minutes in the parquet) — equivalent to a
    dense per-minute Transformer input.
  - "Trainable minutes": minutes that pass `label_mask == 0` AND the
    source-specific induction drop. This is what a per-minute model would
    actually attend to.
  - "Observation tokens": count of non-NaN cells across the model's input
    channels. Equivalent to the token count for an irregular-time-series /
    triplet-based Transformer (e.g. STraTS-style).

Run with:
    /opt/anaconda3/bin/python scripts/seq_length_eda.py
"""

from __future__ import annotations

from pathlib import Path

import duckdb

DATA_ROOT = Path(__file__).resolve().parents[1] / "data"
TS_GLOB = str(DATA_ROOT / "timeseries" / "source=*" / "case_id=*" / "data.parquet")

# Channels we'd feed to the model (mirrors ioh_prediction.data.schema.ALL_CHANNELS).
CHANNELS = [
    "MAP", "SBP", "DBP",
    "NIBP_MAP", "NIBP_SBP", "NIBP_DBP",
    "HR", "SpO2", "ETCO2", "Temp",
    "FiO2", "MAC", "TV", "RR", "PEEP", "PIP",
]

# Induction drop per source (HANDOFF §6.1).
INDUCTION_DROP = {"mover_epic": 25, "vitaldb": 10, "mover": 10}


def main() -> None:
    con = duckdb.connect()

    print("=" * 78)
    print("Per-case seq length diagnostics")
    print("=" * 78)
    print(f"Source glob: {TS_GLOB}")
    print()

    # Build a single big aggregation that returns per-case stats.
    # We use CASE expressions to apply the source-specific induction drop.
    nonnull_expr = " + ".join(
        f"(CASE WHEN {c} IS NOT NULL THEN 1 ELSE 0 END)" for c in CHANNELS
    )

    per_case_sql = f"""
    WITH raw AS (
        SELECT
            source,
            case_id,
            t_min,
            label_mask,
            {nonnull_expr} AS nonnull_channels
        FROM read_parquet('{TS_GLOB}', hive_partitioning=true)
    ),
    annotated AS (
        SELECT
            *,
            CASE source
                WHEN 'mover_epic' THEN 25
                WHEN 'vitaldb'    THEN 10
                WHEN 'mover'      THEN 10
                ELSE 10
            END AS induction_drop
        FROM raw
    )
    SELECT
        source,
        case_id,
        COUNT(*)                                   AS raw_minutes,
        SUM(CASE WHEN label_mask = 0 AND t_min >= induction_drop THEN 1 ELSE 0 END)
                                                   AS trainable_minutes,
        SUM(nonnull_channels)                      AS obs_tokens_raw,
        SUM(CASE WHEN label_mask = 0 AND t_min >= induction_drop
                 THEN nonnull_channels ELSE 0 END) AS obs_tokens_trainable
    FROM annotated
    GROUP BY source, case_id
    """
    con.sql(f"CREATE TEMP TABLE per_case AS {per_case_sql}")

    summary_sql = """
    SELECT
        source,
        COUNT(*)                                       AS n_cases,
        ROUND(AVG(raw_minutes))                        AS mean_min,
        MEDIAN(raw_minutes)                            AS p50_min,
        QUANTILE_CONT(raw_minutes, 0.75)               AS p75_min,
        QUANTILE_CONT(raw_minutes, 0.90)               AS p90_min,
        QUANTILE_CONT(raw_minutes, 0.95)               AS p95_min,
        QUANTILE_CONT(raw_minutes, 0.99)               AS p99_min,
        MAX(raw_minutes)                               AS max_min,
        MEDIAN(trainable_minutes)                      AS p50_train,
        QUANTILE_CONT(trainable_minutes, 0.95)         AS p95_train,
        MEDIAN(obs_tokens_raw)                         AS p50_tok_raw,
        QUANTILE_CONT(obs_tokens_raw, 0.95)            AS p95_tok_raw,
        MEDIAN(obs_tokens_trainable)                   AS p50_tok_train,
        QUANTILE_CONT(obs_tokens_trainable, 0.95)      AS p95_tok_train
    FROM per_case
    GROUP BY source
    ORDER BY source
    """
    df = con.sql(summary_sql).df()
    print("Distribution summary (rounded):")
    with_int = df.copy()
    for c in with_int.columns:
        if c != "source":
            with_int[c] = with_int[c].astype(float).round().astype("Int64")
    print(with_int.to_string(index=False))
    print()

    # Buckets to inform max_seq_len choice.
    print("Coverage @ candidate M (fraction of cases fully untruncated, raw_minutes):")
    coverage_sql = """
    SELECT
        source,
        AVG(CASE WHEN raw_minutes <=  256 THEN 1.0 ELSE 0 END) AS cov_256,
        AVG(CASE WHEN raw_minutes <=  384 THEN 1.0 ELSE 0 END) AS cov_384,
        AVG(CASE WHEN raw_minutes <=  480 THEN 1.0 ELSE 0 END) AS cov_480,
        AVG(CASE WHEN raw_minutes <=  720 THEN 1.0 ELSE 0 END) AS cov_720,
        AVG(CASE WHEN raw_minutes <= 1024 THEN 1.0 ELSE 0 END) AS cov_1024
    FROM per_case
    GROUP BY source
    ORDER BY source
    """
    cov = con.sql(coverage_sql).df()
    print(cov.round(3).to_string(index=False))
    print()

    print("Coverage @ candidate M (fraction of cases fully untruncated, obs_tokens_raw):")
    tok_cov_sql = """
    SELECT
        source,
        AVG(CASE WHEN obs_tokens_raw <= 1024 THEN 1.0 ELSE 0 END) AS tcov_1k,
        AVG(CASE WHEN obs_tokens_raw <= 2048 THEN 1.0 ELSE 0 END) AS tcov_2k,
        AVG(CASE WHEN obs_tokens_raw <= 4096 THEN 1.0 ELSE 0 END) AS tcov_4k,
        AVG(CASE WHEN obs_tokens_raw <= 8192 THEN 1.0 ELSE 0 END) AS tcov_8k,
        AVG(CASE WHEN obs_tokens_raw <= 16384 THEN 1.0 ELSE 0 END) AS tcov_16k
    FROM per_case
    GROUP BY source
    ORDER BY source
    """
    print(con.sql(tok_cov_sql).df().round(3).to_string(index=False))


if __name__ == "__main__":
    main()
