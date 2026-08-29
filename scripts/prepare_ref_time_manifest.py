"""Build a reference-time-matched training manifest for one or more cohorts.

For each source independently:
  - Compute onset_ratio distribution from positives
  - Sample pseudo-onset for negatives
  - Apply exclusion rules (HANDOFF + design v1)
  - Attach parquet paths
  - Emit a manifest CSV + a QC report

Usage:
    conda run -n torch python scripts/prepare_ref_time_manifest.py \
        --source mover_epic \
        --out outputs/manifests/epic_train_v1.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from ioh_prediction.data.reference_time import (
    RefTimeConfig,
    build_ref_time_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TS_GLOB = (
    REPO_ROOT / "data" / "timeseries" / "source=*" / "case_id=*" / "data.parquet"
)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--source",
        action="append",
        required=True,
        choices=["mover_epic", "vitaldb", "mover"],
        help="Cohort source(s). Repeat for multiple. Matching is per-source.",
    )
    p.add_argument("--pos-min-pre-onset-min", type=int, default=5)
    p.add_argument("--neg-min-pre-onset-min", type=int, default=30)
    p.add_argument("--seed", type=int, default=1004)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    config = RefTimeConfig(
        pos_min_pre_onset_min=args.pos_min_pre_onset_min,
        neg_min_pre_onset_min=args.neg_min_pre_onset_min,
        seed=args.seed,
    )
    manifest, qc = build_ref_time_manifest(
        ts_glob=DEFAULT_TS_GLOB,
        sources=tuple(args.source),
        config=config,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    manifest.to_csv(args.out, index=False)

    print(f"Wrote {len(manifest):,} rows to {args.out}")
    print(manifest.groupby(["source", "label"]).size().to_string())
    print()
    print("Reference-time QC (KS test, positive vs pseudo-negative ratio):")
    print(qc.to_string(index=False))

    # Save the QC report next to the manifest for traceability.
    qc_path = args.out.with_suffix(".qc.csv")
    qc.to_csv(qc_path, index=False)
    print(f"\nQC report written to {qc_path}")


if __name__ == "__main__":
    main()
