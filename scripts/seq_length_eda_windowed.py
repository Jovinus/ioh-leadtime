"""Per-window observation-token counts for STraTS/mTAN-style ITE Transformer.

For each candidate temporal window W (minutes), report the distribution of
observation-token counts produced by that window across the training cohort.

Token = a single non-NaN cell across the 16 input channels at a single
minute. With ITE / STraTS / mTAN tokenization, each non-NaN cell becomes a
(value, variable, time) triplet.

We report:
  - Full-case token count (already computed previously, included as
    baseline)
  - Per-window peak: for each case, the max token count across all sliding
    W-minute windows in that case.
  - Per-window typical: median token count across all sliding W-minute
    windows in that case.

The "peak" stat tells us the worst-case M we'd see at training time if we
randomly anchor `t_now`. The "typical" stat tells us the average M.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

DATA_ROOT = Path(__file__).resolve().parents[1] / "data"
TS_GLOB = str(DATA_ROOT / "timeseries" / "source=*" / "case_id=*" / "data.parquet")

CHANNELS = [
    "MAP", "SBP", "DBP",
    "NIBP_MAP", "NIBP_SBP", "NIBP_DBP",
    "HR", "SpO2", "ETCO2", "Temp",
    "FiO2", "MAC", "TV", "RR", "PEEP", "PIP",
]

WINDOWS = [30, 60, 90, 120, 180, 240]


def main() -> None:
    con = duckdb.connect()
    nonnull_expr = " + ".join(
        f"(CASE WHEN {c} IS NOT NULL THEN 1 ELSE 0 END)" for c in CHANNELS
    )

    # Per-minute table: tokens_at_t = non-null channel count at that minute.
    base_sql = f"""
    CREATE TEMP TABLE per_minute AS
    SELECT
        source,
        case_id,
        t_min,
        ({nonnull_expr}) AS tokens_at_t
    FROM read_parquet('{TS_GLOB}', hive_partitioning=true)
    """
    con.sql(base_sql)
    print("Loaded per-minute token counts.")

    for W in WINDOWS:
        # For each case, compute the sliding-window sum over the last W
        # minutes (causal window). Window function on (case_id) ordered by
        # t_min.
        per_window_sql = f"""
        WITH windowed AS (
            SELECT
                source,
                case_id,
                t_min,
                SUM(tokens_at_t) OVER (
                    PARTITION BY source, case_id
                    ORDER BY t_min
                    ROWS BETWEEN {W - 1} PRECEDING AND CURRENT ROW
                ) AS tokens_in_window
            FROM per_minute
        ),
        per_case AS (
            SELECT
                source,
                case_id,
                MAX(tokens_in_window)    AS peak_tokens,
                MEDIAN(tokens_in_window) AS median_tokens
            FROM windowed
            GROUP BY source, case_id
        )
        SELECT
            source,
            COUNT(*)                          AS n_cases,
            MEDIAN(peak_tokens)               AS p50_peak,
            QUANTILE_CONT(peak_tokens, 0.95)  AS p95_peak,
            MAX(peak_tokens)                  AS max_peak,
            MEDIAN(median_tokens)             AS p50_typical,
            QUANTILE_CONT(median_tokens, 0.95) AS p95_typical
        FROM per_case
        GROUP BY source
        ORDER BY source
        """
        df = con.sql(per_window_sql).df()
        print(f"\nWindow W = {W} minutes:")
        with_int = df.copy()
        for c in with_int.columns:
            if c != "source":
                with_int[c] = with_int[c].astype(float).round().astype("Int64")
        print(with_int.to_string(index=False))


if __name__ == "__main__":
    main()
