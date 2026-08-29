"""Figures for A7: what the changing denominator does to the trajectory.

One figure, because the whole point is a comparison that has to be seen on one axis. The
published AUROC(t) uses every case that has a minute in the bin, so its denominator shrinks
and its composition shifts as the bin moves away from onset. The fixed-cohort curve holds the
denominator constant by keeping only cases observable back to 60 minutes. N(t) is drawn on a
twin axis underneath, because a reader cannot judge a widening interval without it.

The two curves crossing is the finding, so they are drawn in one panel per cohort rather than
side by side.

Review figure, not a submission figure.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib_pt import COHORT_LABELS, COHORT_ORDER  # noqa: E402

HERE = Path(__file__).resolve().parent
DATA = HERE / "a7_observability" / "a7_auroc_by_sample.csv"
OUT = HERE / "review_figures"

ALL = "#0072B2"
FIXED = "#C24E00"
INK = "#161C22"
MUTE = "#5A6672"
RULE = "#DDE4EA"
CLINICAL = 0.70


def run() -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9.5,
            "axes.titlesize": 10.5,
            "axes.labelsize": 9.5,
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 8.5,
            "legend.frameon": False,
            "figure.facecolor": "white",
            "savefig.dpi": 200,
        }
    )
    data = pd.read_csv(DATA)
    fig, axes = plt.subplots(
        2,
        len(COHORT_ORDER),
        figsize=(12.6, 7.0),
        constrained_layout=True,
        sharex=True,
        height_ratios=[2.4, 1.0],
    )
    for column, cohort in enumerate(COHORT_ORDER):
        top, bottom = axes[0, column], axes[1, column]
        for sample, colour, marker, style, label in (
            ("all", ALL, "o", "-", "All cases, denominator varies"),
            ("reaches_60", FIXED, "s", (0, (4, 2)), "Fixed cohort, observable to 60 min"),
        ):
            cell = data[(data["cohort"] == cohort) & (data["sample"] == sample)].sort_values(
                "bin_center_min"
            )
            x = cell["bin_center_min"].to_numpy()
            top.fill_between(
                x, cell["auroc_ci_lo"], cell["auroc_ci_hi"], color=colour, alpha=0.13, linewidth=0
            )
            top.plot(
                x,
                cell["auroc"],
                color=colour,
                marker=marker,
                linestyle=style,
                markersize=4.6,
                markerfacecolor=colour if sample == "all" else "white",
                markeredgewidth=1.0,
                linewidth=1.6,
                label=label,
            )
            bottom.plot(
                x,
                cell["n_cases"],
                color=colour,
                marker=marker,
                linestyle=style,
                markersize=4.0,
                markerfacecolor=colour if sample == "all" else "white",
                markeredgewidth=1.0,
                linewidth=1.4,
            )
        top.axhline(0.5, color=MUTE, linewidth=0.9, linestyle=(0, (2, 2)))
        top.axhline(CLINICAL, color="#A93226", linewidth=1.0, linestyle="-")
        top.annotate(
            "AUROC 0.70",
            xy=(0.02, CLINICAL),
            xycoords=("axes fraction", "data"),
            xytext=(0, 4),
            textcoords="offset points",
            fontsize=7.8,
            color="#A93226",
        )
        top.set_ylim(0.45, 1.02)
        top.set_title(COHORT_LABELS[cohort], loc="left", fontweight="bold", color=INK)
        bottom.set_xlabel("Minutes before reference time")
        if column == 0:
            top.set_ylabel("Population AUROC (95% CI)")
            bottom.set_ylabel("N cases in the bin")
        for ax in (top, bottom):
            ax.invert_xaxis()
            ax.set_xticks([60, 45, 30, 15, 0])
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            for side in ("left", "bottom"):
                ax.spines[side].set_color(RULE)
            ax.grid(axis="y", color=RULE, linewidth=0.65, alpha=0.8)
            ax.set_axisbelow(True)
            ax.tick_params(colors=MUTE, length=3)

    handles = [
        Line2D([0], [0], color=ALL, marker="o", linestyle="-", label="All cases, denominator varies with the bin"),
        Line2D(
            [0], [0], color=FIXED, marker="s", markerfacecolor="white", linestyle=(0, (4, 2)),
            label="Fixed cohort, cases observable back to 60 min",
        ),
        Line2D([0], [0], color="#A93226", linestyle="-", label="AUROC 0.70"),
    ]
    fig.legend(
        handles,
        [handle.get_label() for handle in handles],
        ncol=3,
        loc="outside lower center",
        bbox_to_anchor=(0.5, -0.055),
        handlelength=2.6,
    )
    fig.text(
        0.5,
        -0.10,
        "The two curves cross. Holding the cohort fixed raises the far end and lowers the near "
        "end, so part of the published trajectory's shape is the sample changing with the bin.",
        ha="center",
        fontsize=8.6,
        color=MUTE,
        style="italic",
    )
    path = OUT / "review_A7_denominator.png"
    fig.savefig(path, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    return path


def main() -> None:
    print("wrote", run())


if __name__ == "__main__":
    main()
