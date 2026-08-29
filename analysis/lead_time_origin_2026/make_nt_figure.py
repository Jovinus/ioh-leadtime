"""The paired AUROC / N(t) figure: what the changing denominator does to the trajectory.

The published population trajectory scores every case that has a minute in the bin, so its
denominator shrinks and its composition shifts as the bin moves away from onset -- an event
case's observable run-up *is* its time to onset, so the far bins keep only long run-ups.
This figure puts that trajectory beside the same bins recomputed on a cohort fixed to cases
observable back to 60 minutes, with N(t) underneath so a reader can attribute every widening
interval.

The two curves cross, and the crossing is the point of the figure: fixing the cohort raises
the far end and lowers the near end. The useful horizon -- the first bin at which AUROC
reaches 0.70 -- therefore depends on which denominator is used, moving from 15 minutes in all
three cohorts to 20, 35 and 20 minutes. Both series are annotated so the reader does not have
to read the crossing off the curves.

Built at submission quality (300 dpi PNG plus vector PDF) with alt text, and left in this
module rather than written into ``draft/``: which figures ship is an output-configuration
decision, not an analysis one.

Reads ``a7_observability/a7_auroc_by_sample.csv``. Computes nothing.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib_b import COHORT_LABELS, COHORT_ORDER, REPO  # noqa: E402

OUT = Path(__file__).resolve().parent / "figures"
DATA = (
    REPO / "analysis" / "patient_trajectory_2026" / "a7_observability" / "a7_auroc_by_sample.csv"
)

FIXED_SAMPLE = "reaches_60"
CLINICAL = 0.70
#: Okabe-Ito, the palette the submission figures already use.
ALL_COLOUR = "#0072B2"
FIXED_COLOUR = "#D55E00"
RULE_COLOUR = "#A93226"
INK = "#161C22"
MUTE = "#5A6672"
RULE = "#DDE4EA"


def _horizon(cell: pd.DataFrame) -> float:
    """Farthest bin at which AUROC reaches 0.70, walking inward from 60 minutes."""
    reached = cell[cell["auroc"] >= CLINICAL]
    return float(reached["bin_center_min"].max()) if len(reached) else np.nan


def _crossing(all_cases: pd.DataFrame, fixed: pd.DataFrame) -> float:
    """Where the fixed-cohort curve falls back below the all-cases curve, by interpolation.

    Both series are read on the bins they share.  The reported crossing is the innermost
    sign change of ``fixed - all``, linearly interpolated between the two bracketing bin
    centres, because the crossing is the figure's claim and rounding it to a bin centre
    would overstate its precision.
    """
    merged = all_cases.merge(fixed, on="bin_center_min", suffixes=("_all", "_fixed"))
    merged = merged.sort_values("bin_center_min", ascending=False)
    difference = merged["auroc_fixed"].to_numpy() - merged["auroc_all"].to_numpy()
    centres = merged["bin_center_min"].to_numpy(float)
    for index in range(1, len(difference)):
        if difference[index - 1] > 0 >= difference[index]:
            span = difference[index - 1] - difference[index]
            if span == 0:
                return float(centres[index])
            fraction = difference[index - 1] / span
            return float(centres[index - 1] + fraction * (centres[index] - centres[index - 1]))
    return float("nan")


def run() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9.5,
            "axes.titlesize": 11.5,
            "axes.labelsize": 10.0,
            "xtick.labelsize": 8.8,
            "ytick.labelsize": 8.8,
            "legend.frameon": False,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
            "savefig.dpi": 300,
        }
    )
    data = pd.read_csv(DATA)
    annotations: dict[str, dict] = {}

    fig, axes = plt.subplots(
        2,
        len(COHORT_ORDER),
        figsize=(13.0, 7.4),
        constrained_layout=True,
        sharex=True,
        height_ratios=[2.35, 1.0],
    )
    for column, cohort in enumerate(COHORT_ORDER):
        top, bottom = axes[0, column], axes[1, column]
        series = {}
        for sample, colour, marker, style, face in (
            ("all", ALL_COLOUR, "o", "-", ALL_COLOUR),
            (FIXED_SAMPLE, FIXED_COLOUR, "s", (0, (4, 2)), "white"),
        ):
            cell = data[(data["cohort"] == cohort) & (data["sample"] == sample)].sort_values(
                "bin_center_min"
            )
            series[sample] = cell
            x = cell["bin_center_min"].to_numpy()
            top.fill_between(
                x,
                cell["auroc_ci_lo"],
                cell["auroc_ci_hi"],
                color=colour,
                alpha=0.13,
                linewidth=0,
            )
            top.plot(
                x, cell["auroc"], color=colour, marker=marker, linestyle=style,
                markersize=4.8, markerfacecolor=face, markeredgecolor=colour,
                markeredgewidth=1.1, linewidth=1.7,
            )
            bottom.plot(
                x, cell["n_cases"], color=colour, marker=marker, linestyle=style,
                markersize=4.2, markerfacecolor=face, markeredgecolor=colour,
                markeredgewidth=1.1, linewidth=1.5,
            )

        horizon_all = _horizon(series["all"])
        horizon_fixed = _horizon(series[FIXED_SAMPLE])
        crossing = _crossing(series["all"], series[FIXED_SAMPLE])
        annotations[cohort] = {
            "horizon_all_cases_min": horizon_all,
            "horizon_fixed_cohort_min": horizon_fixed,
            "crossing_min": crossing,
            # Sorted ascending by bin centre, so iloc[0] is the 0-minute bin.
            "n_cases_all_at_0": int(series["all"]["n_cases"].iloc[0]),
            "n_cases_all_at_60": int(series["all"]["n_cases"].iloc[-1]),
            "n_cases_fixed": int(series[FIXED_SAMPLE]["n_cases"].max()),
        }

        top.axhline(0.5, color=MUTE, linewidth=0.9, linestyle=(0, (2, 2)))
        top.axhline(CLINICAL, color=RULE_COLOUR, linewidth=1.1)
        top.annotate(
            "AUROC 0.70", xy=(0.015, CLINICAL), xycoords=("axes fraction", "data"),
            xytext=(0, 5), textcoords="offset points", fontsize=8.0, color=RULE_COLOUR,
        )
        # Horizon markers sit at the top of the panel: the 0.70 rule, the curves and the
        # 0.5 reference all occupy the middle and lower band.
        for horizon, colour, label, align, offset in (
            (horizon_fixed, FIXED_COLOUR, "fixed cohort", "right", -4),
            (horizon_all, ALL_COLOUR, "all cases", "left", 4),
        ):
            if not np.isfinite(horizon):
                continue
            top.axvline(horizon, color=colour, linewidth=0.9, linestyle=(0, (1, 2)), alpha=0.85)
            top.annotate(
                f"{label}\nreaches 0.70\nat {horizon:.0f} min", xy=(horizon, 1.005),
                xycoords="data", xytext=(offset, 0), textcoords="offset points",
                fontsize=7.4, color=colour, ha=align, va="top",
            )
        if np.isfinite(crossing):
            top.plot([crossing], [np.interp(
                crossing,
                series["all"]["bin_center_min"],
                series["all"]["auroc"],
            )], marker="X", markersize=9, color=INK, zorder=6, markeredgecolor="white",
                markeredgewidth=1.0)
            top.annotate(
                f"curves cross\nat {crossing:.0f} min", xy=(crossing, np.interp(
                    crossing, series["all"]["bin_center_min"], series["all"]["auroc"])),
                xytext=(-38, -44), textcoords="offset points", fontsize=7.6, color=INK,
                ha="center",
                arrowprops={"arrowstyle": "-", "color": INK, "linewidth": 0.7},
            )

        top.set_ylim(0.45, 1.10)
        letter = "ABC"[column]
        top.set_title(f"{letter}  {COHORT_LABELS[cohort]}", loc="left", fontweight="bold", color=INK)
        bottom.set_xlabel("Minutes before reference time")
        if column == 0:
            top.set_ylabel("Population AUROC (95% CI)")
            bottom.set_ylabel("N(t), cases in the bin")
        for ax in (top, bottom):
            # Time runs toward onset from left to right, matching Figure 1.  Setting the
            # limits rather than calling invert_xaxis() matters here: the axes are shared,
            # so six inversions would cancel out and silently reverse the reading order.
            ax.set_xlim(62, -2)
            ax.set_xticks([60, 45, 30, 15, 0])
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            for side in ("left", "bottom"):
                ax.spines[side].set_color(RULE)
            ax.grid(axis="y", color=RULE, linewidth=0.65, alpha=0.8)
            ax.set_axisbelow(True)
            ax.tick_params(colors=MUTE, length=3)

    handles = [
        Line2D([0], [0], color=ALL_COLOUR, marker="o", linestyle="-",
               label="All cases — denominator varies with the bin (published convention)"),
        Line2D([0], [0], color=FIXED_COLOUR, marker="s", markerfacecolor="white",
               linestyle=(0, (4, 2)), label="Fixed cohort — cases observable back to 60 minutes"),
        Line2D([0], [0], color=RULE_COLOUR, linestyle="-", label="AUROC 0.70"),
        Line2D([0], [0], color=INK, marker="X", linestyle="none", label="Curves cross"),
    ]
    fig.legend(
        handles, [handle.get_label() for handle in handles], ncol=2,
        loc="outside lower center", bbox_to_anchor=(0.5, -0.075), handlelength=2.6,
    )

    png = OUT / "Figure_Nt_fixed_cohort.png"
    pdf = OUT / "Figure_Nt_fixed_cohort.pdf"
    fig.savefig(png, bbox_inches="tight", pad_inches=0.10)
    fig.savefig(pdf, bbox_inches="tight", pad_inches=0.10, metadata={"CreationDate": None})
    plt.close(fig)

    _write_alt_text(annotations)
    (OUT / "figure_nt_annotations.json").write_text(
        json.dumps(annotations, indent=2), encoding="utf-8"
    )
    return annotations


def _write_alt_text(annotations: dict) -> None:
    horizons_fixed = ", ".join(
        f"{annotations[c]['horizon_fixed_cohort_min']:.0f}" for c in COHORT_ORDER
    )
    crossings = ", ".join(f"{annotations[c]['crossing_min']:.0f}" for c in COHORT_ORDER)
    caption = f"""## Figure | Risk-set composition, not only discrimination, shapes the population trajectory

**Risk-set composition changes the trajectory and the useful horizon.** Upper
panels: population area under the receiver operating characteristic curve (AUROC) of the
continuously read transformer by minutes before the reference time in **A,** held-out
MOVER (EPIC), **B,** VitalDB, and **C,** MOVER (SIS), computed two ways on the same
bins — over all cases with an observed minute in the bin, which is the published
convention and whose denominator varies with the bin, and over a cohort fixed to cases
observable back to 60 minutes. Lower panels: N(t), the number of cases contributing to
each bin, on the same lead-time axis. For an event case the observable run-up is its own
time to onset, so the far bins of the all-cases series retain only long run-ups. Shading
is the pointwise 95% cluster-bootstrap confidence interval. The horizontal line marks
AUROC 0.70; dotted vertical lines mark the farthest bin at which each series reaches it —
15 minutes for all cases in every cohort, against {horizons_fixed} minutes for the fixed
cohort. The cross marks where the two series meet, at {crossings} minutes. Colour, marker
and line style redundantly identify the two series.

Alt text: Three columns of paired charts, one column per cohort. Each upper chart plots two
population AUROC curves from 60 to 0 minutes before the reference time: an all-cases
series drawn as a solid blue line with filled circles, and a fixed-cohort series drawn as
a dashed orange line with open squares. In every cohort the fixed-cohort curve sits above
the all-cases curve at the far end and below it near the reference time, so the two cross
— at {crossings} minutes in MOVER (EPIC) test, VitalDB and MOVER (SIS) respectively. A
horizontal red line marks AUROC 0.70; the all-cases series first reaches it at 15 minutes
in all three cohorts, whereas the fixed-cohort series reaches it at {horizons_fixed}
minutes. Shaded bands are pointwise 95% cluster-bootstrap confidence intervals. Each lower
chart plots the number of cases in each bin for the same two series on the same horizontal
axis: the all-cases count rises steeply toward the reference time while the fixed-cohort
count is flat by construction, which is why the all-cases interval is widest exactly where
that curve is lowest.
"""
    (OUT / "ALT_TEXT_Nt.md").write_text(caption, encoding="utf-8")


def main() -> None:
    annotations = run()
    print(json.dumps(annotations, indent=2))
    print("wrote", OUT / "Figure_Nt_fixed_cohort.png")


if __name__ == "__main__":
    main()
