"""Verify that the cohort-AUROC dip at t≈30 min is a clipping artefact.

`reference_time.py` clips negative `pseudo_onset_min` to
`[induction_drop + neg_min_pre_onset_min, case_length]`. Any negative
whose sampled `ratio × case_length` falls below the lower clip is
piled at the boundary. Bin t = neg_min_pre_onset_min (≡ 30 with
defaults) is the first bin where these piled-up cases gain a score
column — which is exactly where the AUROC drops.

This script:
  1) Reads each cohort's manifest CSV.
  2) Plots first_onset (positive) and pseudo_onset (negative) histograms.
  3) Reports the fraction of negatives clipped at the lower boundary.
  4) Saves a PNG to reports/pseudo_onset_distribution.png.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ioh_prediction.data.eligibility import INDUCTION_DROP_MIN
from ioh_prediction.data.reference_time import RefTimeConfig


def _classify(name: str) -> str | None:
    """Map cohort display name → HANDOFF source key for INDUCTION_DROP_MIN."""
    n = name.lower()
    if "epic" in n or "mover_epic" in n:
        return "mover_epic"
    if "vitaldb" in n:
        return "vitaldb"
    if "mover" in n or "sis" in n:
        return "mover"
    return None


def analyze(name: str, manifest_path: Path, neg_min_pre_onset_min: int) -> dict:
    df = pd.read_csv(manifest_path)
    src = _classify(name)
    induction_drop = INDUCTION_DROP_MIN.get(src, 10) if src else 10
    clip_min = induction_drop + neg_min_pre_onset_min

    pos = pd.to_numeric(df.loc[df["label"] == 1, "first_onset_min"], errors="coerce").dropna()
    neg = pd.to_numeric(df.loc[df["label"] == 0, "ref_time_min"], errors="coerce").dropna()

    n_neg_at_clip = int(((neg >= clip_min - 0.5) & (neg <= clip_min + 0.5)).sum())
    pct_at_clip = 100.0 * n_neg_at_clip / max(1, len(neg))

    return {
        "name": name,
        "induction_drop": induction_drop,
        "clip_min": clip_min,
        "pos_onset": pos,
        "neg_pseudo_onset": neg,
        "n_pos": len(pos),
        "n_neg": len(neg),
        "n_neg_at_clip": n_neg_at_clip,
        "pct_neg_at_clip": pct_at_clip,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--run-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, default=Path("reports/pseudo_onset_distribution.png"))
    p.add_argument(
        "--neg-min-pre-onset-min",
        type=int,
        default=RefTimeConfig().neg_min_pre_onset_min,
        help="neg_min_pre_onset_min used when manifests were built (default 30)",
    )
    args = p.parse_args()

    sources: list[tuple[str, Path]] = []
    epic_manifest = args.run_dir / "manifest.csv"
    if epic_manifest.exists():
        sources.append(("EPIC", epic_manifest))
    for ext, label in [("vitaldb", "VitalDB"), ("mover", "MOVER SIS")]:
        p2 = args.run_dir / f"external_{ext}" / "manifest.csv"
        if p2.exists():
            sources.append((label, p2))

    fig, axes = plt.subplots(
        len(sources), 1, figsize=(8.5, 4 * len(sources)), squeeze=False
    )
    print(f"{'Cohort':<14s} {'induction_drop':>14s} {'clip_min':>9s} {'n_neg':>8s} "
          f"{'n@clip':>8s} {'%@clip':>7s}")
    for i, (name, mp) in enumerate(sources):
        res = analyze(name, mp, args.neg_min_pre_onset_min)
        ax = axes[i][0]
        bins = np.arange(0, max(res["pos_onset"].max(), res["neg_pseudo_onset"].max()) + 5, 5)
        ax.hist(
            res["pos_onset"], bins=bins, alpha=0.5, color="C3",
            label=f"positive first_onset (n={res['n_pos']})",
        )
        ax.hist(
            res["neg_pseudo_onset"], bins=bins, alpha=0.5, color="C0",
            label=f"negative pseudo_onset (n={res['n_neg']})",
        )
        ax.axvline(
            res["clip_min"], color="black", linestyle="--", linewidth=1.0,
            label=f"clip_min = induction_drop + neg_min_pre_onset = {res['clip_min']}",
        )
        ax.set_title(
            f"{name}: pseudo_onset clipped at {res['clip_min']} — "
            f"{res['pct_neg_at_clip']:.1f}% of negatives pile at the boundary"
        )
        ax.set_xlabel("minute index from anchor")
        ax.set_ylabel("count")
        ax.set_xlim(0, min(bins[-1], 500))
        ax.legend(loc="upper right", fontsize=8)
        print(f"{name:<14s} {res['induction_drop']:>14d} {res['clip_min']:>9d} "
              f"{res['n_neg']:>8d} {res['n_neg_at_clip']:>8d} {res['pct_neg_at_clip']:>6.1f}%")

    fig.suptitle("Reference-time distribution: positive vs negative",
                 fontsize=14, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=150, bbox_inches="tight")
    print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
