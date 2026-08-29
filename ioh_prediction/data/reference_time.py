"""AKI-style reference-time matching for IOH cases.

For each *source cohort* independently:

  1. Compute `onset_ratio = first_onset_min / case_length_min` for every
     positive case (one with `in_event_d3 == 1` anywhere).
  2. For every negative case in that cohort, sample `onset_ratio` (with
     replacement) from the positive distribution above.
  3. Compute `pseudo_onset_min = ratio × case_length_min` and clip to
     `[induction_drop + min_pre_onset_min, case_length_min]`.

Cohort exclusion rules (kept here so manifests are consistent):

  - Positives are dropped if `first_onset_min < induction_drop + pos_min_pre_onset_min`.
    Default `pos_min_pre_onset_min = 5` (event during induction).
  - Negatives are dropped if `case_length_min < induction_drop + neg_min_pre_onset_min`.
    Default `neg_min_pre_onset_min = 30` (insufficient room for the
    pseudo_onset to have a meaningful lookback window).

This mirrors `experiments/step1_reference_time_matching.py` in the user's
prior AKI repo, adapted to per-minute IOH timescales.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import duckdb
import numpy as np
import pandas as pd

from .eligibility import INDUCTION_DROP_MIN


@dataclass(frozen=True)
class RefTimeConfig:
    pos_min_pre_onset_min: int = 5
    neg_min_pre_onset_min: int = 30
    # Lead-time gap: shift `ref_time_min` to `onset - pos_gap_min` so
    # the model is supervised to predict an event `pos_gap_min` minutes
    # in the future. Default 0 reproduces the original "predict at
    # onset" framing. The pseudo_onset distribution for negatives is
    # unchanged; the same shift is applied so the ref_time distribution
    # still matches positives.
    pos_gap_min: int = 0
    seed: int = 1004
    # When the sampled `ratio × case_length` falls outside the valid
    # range we resample the ratio instead of clipping (previous
    # behaviour piled ~half of negatives at the lower boundary and
    # caused a cohort-AUROC dip at t = neg_min_pre_onset_min before
    # onset). `max_resample_tries` caps the per-case retry loop; cases
    # that never produce a valid pseudo_onset (typically very short
    # case_length) are dropped from the manifest.
    max_resample_tries: int = 100


def _case_summary_sql(ts_glob: str, sources: Iterable[str]) -> str:
    src_filter = ",".join(f"'{s}'" for s in sources)
    return f"""
    WITH per_minute AS (
        SELECT source, case_id, t_min, in_event_d3
        FROM read_parquet('{ts_glob}', hive_partitioning=true)
        WHERE source IN ({src_filter})
    )
    SELECT
        source,
        case_id,
        MAX(t_min) + 1                                  AS case_length_min,
        MIN(CASE WHEN in_event_d3 = 1 THEN t_min END)   AS first_onset_min
    FROM per_minute
    GROUP BY source, case_id
    """


def load_case_summary(
    ts_glob: str,
    sources: Iterable[str],
) -> pd.DataFrame:
    """One row per case with `case_length_min`, `first_onset_min` (NaN if negative)."""
    return duckdb.sql(_case_summary_sql(ts_glob, sources)).df()


def assign_reference_times(
    case_summary: pd.DataFrame,
    config: RefTimeConfig = RefTimeConfig(),
) -> pd.DataFrame:
    """Add `ref_time_min`, `label`, `is_pseudo`, `onset_ratio_source` columns.

    Operates per source cohort. Drops cases failing the exclusion rules.
    """
    rng = np.random.RandomState(config.seed)
    out_frames: list[pd.DataFrame] = []

    gap = int(config.pos_gap_min)
    if gap < 0:
        raise ValueError(f"pos_gap_min must be >= 0, got {gap}")

    for source, group in case_summary.groupby("source", observed=True):
        drop = INDUCTION_DROP_MIN.get(str(source), 10)
        g = group.copy()
        g["is_positive"] = g["first_onset_min"].notna()

        # Exclude positives with onset during induction. With a lead-time
        # gap we additionally require room for the shifted ref_time to
        # land at or after `drop + pos_min_pre_onset_min`.
        pos_keep = g["is_positive"] & (
            g["first_onset_min"] >= drop + config.pos_min_pre_onset_min + gap
        )
        # Exclude negatives that are too short to host a pseudo_onset
        # (also bumped by the gap so `ref_time = pseudo_onset - gap`
        # still respects the same lower bound).
        neg_keep = (~g["is_positive"]) & (
            g["case_length_min"] >= drop + config.neg_min_pre_onset_min + gap
        )
        keep = pos_keep | neg_keep
        g = g.loc[keep].reset_index(drop=True)

        # Positive ref time = first onset - gap
        g["ref_time_min"] = np.where(
            g["is_positive"], g["first_onset_min"] - gap, np.nan
        )
        g["label"] = g["is_positive"].astype("int8")
        g["is_pseudo"] = (~g["is_positive"]).astype("int8")

        # Sample onset_ratio for negatives from this source's positives
        pos_ratios = (
            g.loc[g["is_positive"], "first_onset_min"]
            / g.loc[g["is_positive"], "case_length_min"]
        ).clip(0.0, 1.0).dropna().to_numpy()

        if len(pos_ratios) == 0:
            raise ValueError(
                f"No positive cases in source={source} after exclusion; "
                f"cannot reference-time-match negatives."
            )

        neg_mask = ~g["is_positive"]
        n_neg = int(neg_mask.sum())
        drop_idx: list[int] = []
        if n_neg:
            lengths = g.loc[neg_mask, "case_length_min"].to_numpy()
            # Bump the minimum pseudo_onset by `gap` so the shifted
            # ref_time still leaves `neg_min_pre_onset_min` of headroom.
            lo = drop + config.neg_min_pre_onset_min + gap
            neg_indices = np.flatnonzero(neg_mask.to_numpy())
            for k, case_len in zip(neg_indices, lengths, strict=True):
                hi = int(case_len) - 1
                if hi < lo:
                    drop_idx.append(int(k))  # case too short to host a pseudo_onset
                    continue
                # Rejection sampling: keep drawing ratios until the
                # implied pseudo_onset lands inside [lo, hi]. This
                # matches positive `onset_ratio` distribution without
                # piling up on the lower clip boundary.
                accepted: int | None = None
                for _ in range(config.max_resample_tries):
                    r = float(rng.choice(pos_ratios))
                    candidate = int(round(r * case_len))
                    if lo <= candidate <= hi:
                        accepted = candidate
                        break
                if accepted is None:
                    drop_idx.append(int(k))
                else:
                    # Negative ref_time = pseudo_onset - gap.
                    g.at[g.index[k], "ref_time_min"] = accepted - gap

        # Drop negatives that couldn't be matched (case_length too short
        # to host any sampled ratio).
        if drop_idx:
            g = g.drop(index=[g.index[k] for k in drop_idx])

        g = g.reset_index(drop=True)
        g["ref_time_min"] = g["ref_time_min"].astype("int32")
        g["onset_ratio_source"] = source
        out_frames.append(g)

    return pd.concat(out_frames, ignore_index=True)


def ks_test_by_source(case_assignments: pd.DataFrame) -> pd.DataFrame:
    """QC: KS-test between positive onset_ratio and negative pseudo onset_ratio per source."""
    from scipy import stats

    rows = []
    for source, g in case_assignments.groupby("source", observed=True):
        pos = g.loc[g["label"] == 1]
        neg = g.loc[g["label"] == 0]
        pos_r = (pos["ref_time_min"] / pos["case_length_min"]).to_numpy()
        neg_r = (neg["ref_time_min"] / neg["case_length_min"]).to_numpy()
        if len(pos_r) and len(neg_r):
            stat, p = stats.ks_2samp(pos_r, neg_r)
        else:
            stat, p = float("nan"), float("nan")
        rows.append(
            dict(
                source=source,
                n_positive=int(len(pos_r)),
                n_negative=int(len(neg_r)),
                pos_ratio_mean=float(pos_r.mean()) if len(pos_r) else float("nan"),
                neg_ratio_mean=float(neg_r.mean()) if len(neg_r) else float("nan"),
                ks_stat=float(stat),
                ks_pval=float(p),
            )
        )
    return pd.DataFrame(rows)


def attach_parquet_paths_and_statics(
    assignments: pd.DataFrame,
    ts_glob: str,
    cases_parquet: str,
) -> pd.DataFrame:
    """Join `(source, case_id)` rows back to (a) their per-case parquet path
    and (b) the static features in `cases.parquet`.
    """
    paths_df = duckdb.sql(
        f"""
        SELECT DISTINCT case_id, source, filename AS parquet_path
        FROM read_parquet('{ts_glob}',
                          hive_partitioning=true,
                          filename=true)
        """
    ).df()
    # cases.parquet currently contains exact-duplicate rows for some
    # (case_id, source) pairs (~1.5% — a preprocessing-side bug);
    # collapse them so the merge stays many-to-one.
    cases_df = duckdb.sql(f"SELECT * FROM read_parquet('{cases_parquet}')").df()
    cases_df = cases_df.drop_duplicates(subset=["case_id", "source"])
    out = assignments.merge(paths_df, on=["case_id", "source"], how="left", validate="m:1")
    out = out.merge(cases_df, on=["case_id", "source"], how="left", validate="m:1")
    return out


def build_ref_time_manifest(
    ts_glob: str | Path,
    sources: Iterable[str],
    config: RefTimeConfig = RefTimeConfig(),
    cases_parquet: str | Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """End-to-end: load case summaries, assign ref times, attach parquet
    paths AND static features from `cases.parquet`.
    """
    cs = load_case_summary(str(ts_glob), sources)
    assigned = assign_reference_times(cs, config)
    if cases_parquet is None:
        # Default: sibling of the `timeseries/` glob root.
        cases_parquet = Path(str(ts_glob)).parts
        cases_root = Path(str(ts_glob)).parent
        while cases_root.name != "timeseries" and cases_root != cases_root.parent:
            cases_root = cases_root.parent
        cases_parquet = cases_root.parent / "cases.parquet"
    manifest = attach_parquet_paths_and_statics(
        assigned, str(ts_glob), str(cases_parquet)
    )
    qc = ks_test_by_source(assigned)
    return manifest, qc
