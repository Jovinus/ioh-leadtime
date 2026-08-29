"""Visualize per-minute model scores for individual cases.

For each cohort we randomly sample a handful of positives (and the
same number of negatives for comparison) and plot the score as a
function of minutes-before-event. If the cohort-level AUROC dip at
25–30 min reflects a real BP-rebound pattern, individual case curves
should also show a dip; if the dip is purely a sampling artefact, the
case-level curves should look smoothly monotonic.

Usage:
    conda run -n torch python scripts/case_score_trajectories.py \
        --run-dir outputs/runs/baseline_epic \
        --n-cases 9 \
        --out reports/case_trajectories.png
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _plot_panel(ax, sub: pd.DataFrame, color: str, alpha: float = 0.5) -> None:
    sub = sub.sort_values("t_to_event", ascending=False)
    ax.plot(sub["t_to_event"], sub["score"], color=color, alpha=alpha, linewidth=1.2)


def plot_cohort_trajectories(
    name: str,
    pred_path: Path,
    n_cases: int,
    seed: int,
    ax_pos,
    ax_neg,
    ax_avg,
) -> None:
    preds = pd.read_parquet(pred_path)
    # Restrict the x-range so the per-case curves use the same x extent
    # as the cohort-level AUROC trajectory plot.
    preds = preds[(preds["t_to_event"] >= 0) & (preds["t_to_event"] <= 60)]
    rng = np.random.RandomState(seed)

    pos_ids = preds.loc[preds["label"] == 1, "case_id"].unique()
    neg_ids = preds.loc[preds["label"] == 0, "case_id"].unique()
    pos_sample = rng.choice(pos_ids, size=min(n_cases, len(pos_ids)), replace=False)
    neg_sample = rng.choice(neg_ids, size=min(n_cases, len(neg_ids)), replace=False)

    for cid in pos_sample:
        _plot_panel(ax_pos, preds[preds["case_id"] == cid], color="C3")
    for cid in neg_sample:
        _plot_panel(ax_neg, preds[preds["case_id"] == cid], color="C0")

    # Cohort-level mean score per bin, separately for positive and negative.
    pos_mean = (
        preds[preds["label"] == 1]
        .groupby("t_to_event")["score"]
        .mean()
        .sort_index(ascending=False)
    )
    neg_mean = (
        preds[preds["label"] == 0]
        .groupby("t_to_event")["score"]
        .mean()
        .sort_index(ascending=False)
    )
    ax_avg.plot(pos_mean.index, pos_mean.values, color="C3", linewidth=2.0, label="positive (cohort mean)")
    ax_avg.plot(neg_mean.index, neg_mean.values, color="C0", linewidth=2.0, label="negative (cohort mean)")

    for ax, title in (
        (ax_pos, f"{name} — positives ({len(pos_sample)} sampled)"),
        (ax_neg, f"{name} — negatives ({len(neg_sample)} sampled)"),
        (ax_avg, f"{name} — cohort-mean score by t_to_event"),
    ):
        ax.set_xlabel("minutes before event")
        ax.set_ylabel("model score (P(positive))")
        ax.set_xlim(60, 0)  # right-to-left so onset is on the right
        ax.set_ylim(0, 1)
        ax.set_title(title, fontsize=10)
        ax.axhline(0.5, color="grey", linestyle="--", linewidth=0.6)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--run-dir", type=Path, required=True)
    p.add_argument("--n-cases", type=int, default=9)
    p.add_argument("--seed", type=int, default=1004)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    sources: list[tuple[str, Path]] = []
    legacy_val = args.run_dir / "predictions" / "predictions_raw.parquet"
    if legacy_val.exists():
        sources.append(("EPIC val", legacy_val))
    for ext, label in [("vitaldb", "VitalDB"), ("mover", "MOVER SIS")]:
        p2 = args.run_dir / f"external_{ext}" / "predictions_raw.parquet"
        if p2.exists():
            sources.append((label, p2))

    n_rows = len(sources)
    fig, axes = plt.subplots(n_rows, 3, figsize=(14, 4 * n_rows), squeeze=False)
    for r, (name, pp) in enumerate(sources):
        plot_cohort_trajectories(
            name=name, pred_path=pp, n_cases=args.n_cases, seed=args.seed,
            ax_pos=axes[r][0], ax_neg=axes[r][1], ax_avg=axes[r][2],
        )
    # Legend only once.
    axes[0][2].legend(loc="upper left", fontsize=8)
    fig.suptitle("Case-level score trajectories (60 min → onset)", fontsize=14, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=150, bbox_inches="tight")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
