"""IOH event prevalence and onset-ratio distribution.

Mirrors the analysis the user's previous AKI repo used to set up
reference-time matching for negative cases:
  - For each case, does any `in_event_d3==1` exist?
  - If yes, what is `first_onset_minute / case_total_minutes`? (onset ratio)
  - What is `first_onset_minute` distribution in absolute minutes?
"""

from __future__ import annotations

from pathlib import Path

import duckdb

DATA_ROOT = Path(__file__).resolve().parents[1] / "data"
TS_GLOB = str(DATA_ROOT / "timeseries" / "source=*" / "case_id=*" / "data.parquet")


def main() -> None:
    con = duckdb.connect()
    sql = f"""
    WITH per_minute AS (
        SELECT source, case_id, t_min, in_event_d3
        FROM read_parquet('{TS_GLOB}', hive_partitioning=true)
    ),
    per_case AS (
        SELECT
            source,
            case_id,
            MAX(t_min) + 1                                     AS case_length_min,
            SUM(in_event_d3)                                   AS event_minutes,
            MIN(CASE WHEN in_event_d3 = 1 THEN t_min END)      AS first_onset_min
        FROM per_minute
        GROUP BY source, case_id
    )
    SELECT
        source,
        COUNT(*)                                               AS n_cases,
        SUM(CASE WHEN first_onset_min IS NOT NULL THEN 1 ELSE 0 END) AS n_positive,
        AVG(CASE WHEN first_onset_min IS NOT NULL THEN 1.0 ELSE 0 END) AS pos_rate,
        MEDIAN(case_length_min)                                AS case_p50,
        QUANTILE_CONT(case_length_min, 0.95)                   AS case_p95,
        MEDIAN(first_onset_min)                                AS onset_p50,
        QUANTILE_CONT(first_onset_min, 0.25)                   AS onset_p25,
        QUANTILE_CONT(first_onset_min, 0.75)                   AS onset_p75,
        MEDIAN(first_onset_min * 1.0 / case_length_min)        AS ratio_p50,
        QUANTILE_CONT(first_onset_min * 1.0 / case_length_min, 0.25) AS ratio_p25,
        QUANTILE_CONT(first_onset_min * 1.0 / case_length_min, 0.75) AS ratio_p75
    FROM per_case
    GROUP BY source
    ORDER BY source
    """
    df = con.sql(sql).df()
    print(df.round(3).to_string(index=False))
    print()

    # Also: how many positive cases have onset before induction_drop window
    # ends (i.e., the model would have <W=120 min of usable input)?
    early_onset_sql = f"""
    WITH per_minute AS (
        SELECT source, case_id, t_min, in_event_d3
        FROM read_parquet('{TS_GLOB}', hive_partitioning=true)
    ),
    per_case AS (
        SELECT source, case_id,
               MIN(CASE WHEN in_event_d3 = 1 THEN t_min END) AS first_onset_min
        FROM per_minute
        GROUP BY source, case_id
    )
    SELECT
        source,
        SUM(CASE WHEN first_onset_min IS NOT NULL THEN 1 ELSE 0 END) AS n_positive,
        SUM(CASE WHEN first_onset_min IS NOT NULL AND first_onset_min < 30  THEN 1 ELSE 0 END) AS n_lt_30,
        SUM(CASE WHEN first_onset_min IS NOT NULL AND first_onset_min < 60  THEN 1 ELSE 0 END) AS n_lt_60,
        SUM(CASE WHEN first_onset_min IS NOT NULL AND first_onset_min < 90  THEN 1 ELSE 0 END) AS n_lt_90,
        SUM(CASE WHEN first_onset_min IS NOT NULL AND first_onset_min < 120 THEN 1 ELSE 0 END) AS n_lt_120
    FROM per_case
    GROUP BY source
    ORDER BY source
    """
    print("Positive cases with early onset (would have < W minutes of pre-onset context):")
    print(con.sql(early_onset_sql).df().to_string(index=False))


if __name__ == "__main__":
    main()
