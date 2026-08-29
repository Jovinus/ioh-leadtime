"""Figures for A6: the nested-window sweep, and how the movement was delivered.

Two figures because there are two questions and one axis cannot carry both.

The first sweeps the window start and puts the ordering question (Kendall tau), the
endpoint question (ascent fraction) and the displacement question (change in score) in three
rows on one x axis, for both near ends. Read down a column and the disagreement between the
three is the point.

The second answers "how did it move" rather than "how far". The score's gross rise and gross
fall are drawn against each other, so the distance travelled is visible beside the net
displacement; a bar pair that is nearly symmetric with a small net is a wobble, not a climb.
The largest single step's share of the gross rise is annotated, because a rise delivered in
one step and a rise delivered in ten are different clinical objects that every summary
statistic here reports identically.

Review figures, not submission figures: written to this module's own output directory,
never into draft/.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib_pt import COHORT_LABELS, COHORT_ORDER  # noqa: E402

HERE = Path(__file__).resolve().parent
DATA = HERE / "a6_window_trend" / "a6_window_trend.csv"
OUT = HERE / "review_figures"

EVENT = "#0072B2"
CONTROL = "#9AA6B1"
UP = "#00795A"
DOWN = "#A93226"
INK = "#161C22"
MUTE = "#5A6672"
RULE = "#DDE4EA"

GROUP_STYLE = {"event": (EVENT, "o"), "control": (CONTROL, "s")}
GROUP_LABEL = {"event": "Event", "control": "Control"}
ENDPOINT_LINE = {5: "-", 10: (0, (4, 2))}


def _style() -> None:
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


def _clean(ax, grid_axis: str = "y") -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(RULE)
    ax.grid(axis=grid_axis, color=RULE, linewidth=0.65, alpha=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=MUTE, length=3)


def concept_figure() -> Path:
    """Two trajectories with the same net change, delivered completely differently.

    This is the reading rule for the A6 tables, and it is faster to draw than to argue. Net
    change alone calls these two identical. The ascent fraction, the directedness and the
    largest step separate them, and none of the three does it alone.

    Schematic, not data. The annotated numbers are computed from the drawn series so they
    cannot drift from the picture.
    """
    steady = np.array([0.30, 0.325, 0.35, 0.372, 0.365, 0.39, 0.415, 0.44, 0.462, 0.485, 0.50])
    jump = np.array([0.30, 0.29, 0.28, 0.27, 0.72, 0.68, 0.645, 0.61, 0.575, 0.54, 0.50])
    minutes = np.arange(60, 4, -5)[: len(steady)]

    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.3), constrained_layout=True, sharey=True)
    for ax, values, title, colour in (
        (axes[0], steady, "A   A climb", UP),
        (axes[1], jump, "B   A single jump", DOWN),
    ):
        steps = np.diff(values)
        up = steps[steps > 0]
        gross_up = float(up.sum())
        gross_down = float(-steps[steps < 0].sum())
        net = float(values[-1] - values[0])
        for index in range(len(minutes) - 1):
            rising = steps[index] > 0
            ax.annotate(
                "",
                xy=(minutes[index + 1], values[index + 1]),
                xytext=(minutes[index], values[index]),
                arrowprops=dict(
                    arrowstyle="-|>",
                    color=UP if rising else DOWN,
                    linewidth=1.8,
                    shrinkA=3,
                    shrinkB=3,
                ),
            )
        ax.plot(minutes, values, "o", color="white", markeredgecolor=MUTE, markersize=5, zorder=3)
        ax.axhline(values[0], color=MUTE, linewidth=0.8, linestyle=(0, (2, 2)))
        ax.axhline(values[-1], color=MUTE, linewidth=0.8, linestyle=(0, (2, 2)))
        ax.annotate(
            "",
            xy=(2.0, values[-1]),
            xytext=(2.0, values[0]),
            arrowprops=dict(arrowstyle="<->", color=INK, linewidth=1.2),
        )
        ax.text(
            0.5,
            (values[0] + values[-1]) / 2,
            f"net\n{net:+.2f}",
            fontsize=8.6,
            fontweight="bold",
            color=INK,
            ha="center",
            va="center",
            linespacing=1.4,
        )
        ax.set_title(title, loc="left", fontweight="bold", color=colour)
        ax.set_xlabel("Minutes before onset")
        ax.invert_xaxis()
        ax.set_xlim(64, -6)
        ax.set_ylim(0.20, 0.82)
        # Top left in both panels: the bottom right is where the net-change arrow sits, and
        # the two collided.
        ax.text(
            0.02,
            0.97,
            f"ascent fraction  {int((steps > 0).sum())}/{len(steps)} = {(steps > 0).mean():.1f}\n"
            f"distance travelled  {gross_up + gross_down:.2f}\n"
            f"directedness  {net / (gross_up + gross_down):+.2f}\n"
            f"largest step  {up.max() / gross_up:.0%} of the rise",
            transform=ax.transAxes,
            fontsize=8.6,
            color=INK,
            ha="left",
            va="top",
            linespacing=1.7,
            family="monospace",
        )
        _clean(ax)
    axes[0].set_ylabel("Model score")
    fig.text(
        0.5,
        -0.06,
        "Both trajectories start and end at the same score, so the net change cannot tell them "
        "apart. Schematic, not data.",
        ha="center",
        fontsize=8.6,
        color=MUTE,
        style="italic",
    )
    path = OUT / "review_A6_concept.png"
    fig.savefig(path, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    return path


def sweep_figure(data: pd.DataFrame) -> Path:
    rows = [
        # tau_spanning, not tau: the capped tau measures a different actual span in every row
        # while carrying the same window label, so plotting it against window start plots an
        # artefact of the labelling.
        (
            "tau_spanning_median",
            "tau_spanning_q25",
            "tau_spanning_q75",
            "Kendall tau, median (IQR)",
            0.0,
            (-0.85, 0.65),
        ),
        ("ascent_fraction", "ascent_ci_lo", "ascent_ci_hi", "Ascent fraction (95% CI)", 0.5, (0.24, 0.72)),
        ("delta_median", "delta_q25", "delta_q75", "Change in score, median (IQR)", 0.0, (-0.72, 0.52)),
    ]
    fig, axes = plt.subplots(
        len(rows), len(COHORT_ORDER), figsize=(12.6, 10.0), constrained_layout=True, sharex=True
    )
    for row, (value_col, lo_col, hi_col, ylabel, null, ylim) in enumerate(rows):
        for column, cohort in enumerate(COHORT_ORDER):
            ax = axes[row, column]
            ax.axhline(null, color=MUTE, linewidth=0.9, linestyle=(0, (2, 2)))
            for group in ("event", "control"):
                colour, marker = GROUP_STYLE[group]
                for endpoint in (5, 10):
                    cell = data[
                        (data["cohort"] == cohort)
                        & (data["group"] == group)
                        & (data["endpoint_min"] == endpoint)
                    ].sort_values("window_start_min")
                    if not len(cell):
                        continue
                    x = cell["window_start_min"].to_numpy()
                    if endpoint == 5:
                        ax.fill_between(
                            x, cell[lo_col], cell[hi_col], color=colour, alpha=0.09, linewidth=0
                        )
                    ax.plot(
                        x,
                        cell[value_col],
                        color=colour,
                        marker=marker,
                        linestyle=ENDPOINT_LINE[endpoint],
                        markersize=4.4,
                        markerfacecolor=colour if endpoint == 5 else "white",
                        markeredgewidth=1.0,
                        linewidth=1.5,
                    )
            ax.invert_xaxis()
            ax.set_ylim(*ylim)
            ax.set_xticks([60, 45, 30, 15, 10])
            if row == 0:
                ax.set_title(COHORT_LABELS[cohort], loc="left", fontweight="bold", color=INK)
            if row == len(rows) - 1:
                ax.set_xlabel("Window start, minutes before onset")
            if column == 0:
                ax.set_ylabel(ylabel)
            _clean(ax)

    handles = [
        Line2D([0], [0], color=EVENT, marker="o", linestyle="-", label="Event · near end 5 min"),
        Line2D(
            [0], [0], color=EVENT, marker="o", markerfacecolor="white",
            linestyle=(0, (4, 2)), label="Event · near end 10 min",
        ),
        Line2D([0], [0], color=CONTROL, marker="s", linestyle="-", label="Control · near end 5 min"),
        Line2D(
            [0], [0], color=CONTROL, marker="s", markerfacecolor="white",
            linestyle=(0, (4, 2)), label="Control · near end 10 min",
        ),
        Line2D([0], [0], color=MUTE, linestyle=(0, (2, 2)), label="Null (0, or 0.5 for the fraction)"),
    ]
    fig.legend(
        handles,
        [handle.get_label() for handle in handles],
        ncol=3,
        loc="outside lower center",
        bbox_to_anchor=(0.5, -0.065),
        handlelength=2.6,
    )
    fig.text(
        0.5,
        -0.105,
        "Every panel is on the spanning sample: episodes whose observation actually reaches the "
        "window start. That sample halves at the widest starts, and is selected on operation "
        "length.",
        ha="center",
        fontsize=8.6,
        color=MUTE,
        style="italic",
    )
    path = OUT / "review_A6_window_sweep.png"
    fig.savefig(path, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    return path


def delivery_figure(data: pd.DataFrame) -> Path:
    """Distance travelled against displacement, for the 60-to-5 window."""
    window = data[(data["endpoint_min"] == 5) & (data["window_start_min"] == 60)]
    fig, axes = plt.subplots(1, len(COHORT_ORDER), figsize=(12.6, 4.6), constrained_layout=True, sharey=True)
    for column, cohort in enumerate(COHORT_ORDER):
        ax = axes[column]
        cell = window[window["cohort"] == cohort]
        positions = []
        labels = []
        for index, group in enumerate(("event", "control")):
            row = cell[cell["group"] == group]
            if row.empty:
                continue
            row = row.iloc[0]
            base = index * 1.5
            positions.append(base)
            labels.append(GROUP_LABEL[group])
            ax.bar(base - 0.22, row["gross_up_median"], 0.4, color=UP, alpha=0.85, label="_")
            ax.bar(base + 0.22, -row["gross_down_median"], 0.4, color=DOWN, alpha=0.85, label="_")
            ax.plot(
                [base], [row["delta_median"]], marker="D", markersize=9,
                markerfacecolor=INK, markeredgecolor="white", markeredgewidth=1.4, zorder=5,
            )
            # Above the diamond rather than beside it: at the right-hand group the sideways
            # label ran past the axes and into the next panel.
            ax.annotate(
                f"net {row['delta_median']:+.3f}",
                xy=(base, row["delta_median"]),
                xytext=(0, 13),
                textcoords="offset points",
                fontsize=8.6,
                fontweight="bold",
                color=INK,
                ha="center",
            )
            ax.annotate(
                f"directedness {row['directedness_median']:+.3f}\nlargest step = "
                f"{row['max_up_share_median']:.0%} of the rise",
                xy=(base, -1.02),
                fontsize=7.8,
                color=MUTE,
                ha="center",
                va="top",
                linespacing=1.45,
            )
        ax.axhline(0.0, color=INK, linewidth=1.1)
        ax.set_xticks(positions)
        ax.set_xticklabels(labels)
        ax.set_xlim(-0.75, 2.25)
        ax.set_ylim(-1.28, 1.15)
        ax.set_title(COHORT_LABELS[cohort], loc="left", fontweight="bold", color=INK)
        if column == 0:
            ax.set_ylabel("Distance travelled by the score, 60 to 5 min")
        _clean(ax)

    handles = [
        Patch(facecolor=UP, alpha=0.85, label="Gross rise, sum of up-steps (median)"),
        Patch(facecolor=DOWN, alpha=0.85, label="Gross fall, sum of down-steps (median)"),
        Line2D(
            [0], [0], marker="D", color="none", markerfacecolor=INK, markeredgecolor="white",
            markersize=9, label="Net change (median)",
        ),
    ]
    fig.legend(
        handles,
        [handle.get_label() for handle in handles],
        ncol=3,
        loc="outside lower center",
        bbox_to_anchor=(0.5, -0.09),
        handlelength=1.8,
    )
    path = OUT / "review_A6_delivery.png"
    fig.savefig(path, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    return path


def run() -> list[Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    _style()
    data = pd.read_csv(DATA)
    data = data[data["family"] == "transformer"]
    return [concept_figure(), sweep_figure(data), delivery_figure(data)]


def main() -> None:
    for path in run():
        print("wrote", path)


if __name__ == "__main__":
    main()
