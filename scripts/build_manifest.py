"""Build a manifest CSV from the on-disk dataset.

Usage:
    python scripts/build_manifest.py --source mover_epic --out outputs/manifest_epic.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ioh_prediction.data.manifest import ManifestQuery, build_manifest


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--source", action="append", required=True,
                   choices=["mover_epic", "vitaldb", "mover"],
                   help="Cohort source(s). Repeat for multiple.")
    p.add_argument("--min-surgery-min", type=float, default=30.0)
    p.add_argument("--max-surgery-min", type=float, default=1440.0)
    p.add_argument("--max-asa", type=int, default=None)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    query = ManifestQuery(
        sources=tuple(args.source),
        min_surgery_min=args.min_surgery_min,
        max_surgery_min=args.max_surgery_min,
        max_asa=args.max_asa,
    )
    df = build_manifest(query)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"Wrote {len(df):,} cases to {args.out}")
    print(df.groupby("source").size())


if __name__ == "__main__":
    main()
