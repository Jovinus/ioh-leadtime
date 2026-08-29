"""Figure 2 — lead against observed window length, with the N2 shuffle band and N3 medians.

One panel per cohort for the transformer, the limiting case, plus a five-family small-
multiple row underneath so the figure cannot be read as a claim about one architecture.

Three things are drawn on top of each other, and the order matters:

1. the per-case scatter of ``lead`` against ``observed_min``, which is the raw material;
2. the N2 cross-case shuffle band, drawn as the 2.5-97.5 percentile envelope of the null's
   median ratio times the window -- what the metric would report if the score carried no
   case-specific information at all;
3. the N3 quintile medians, which are the number the Results table reports.

The ``y = x`` diagonal is the ceiling: no crossing can be found outside the case's own
observed window, so every point lies on or below it.  Drawing it explicitly is the honest
way to state the objection the nulls exist to answer.

Fonts are pinned to Times because the NeurIPS style uses ``ptm``; matplotlib's default
DejaVu Serif is about 9% wider and silently inflates every layout estimate made from the
figure.  ``mathtext.fontset`` has to be set as well -- setting ``font.family`` alone leaves
maths in DejaVu Sans Oblique and embeds a second face, which is a fix that looks like it
worked.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib_n import (  # noqa: E402
    ALERT_WINDOW_MIN,
    COHORT_LABELS,
    COHORT_ORDER,
    FAMILY_LABELS,
    FAMILY_ORDER,
    HERE,
    headline_cuts,
    per_case_leads,
    write_manifest,
)

OUT = HERE / "figures"

#: PNG raster density. The LaTeX build includes the PNG, not the PDF, so this is the
#: resolution the submitted paper actually carries.
PNG_DPI = 500

#: ``latex/body.tex`` includes every figure at ``width=\linewidth``, and the NeurIPS text
#: block is 5.5 in. A figure built 7.0 in wide is therefore scaled to 79% on the page, which
#: shrinks every glyph with it: a 5.4 pt legend lands at 4.3 pt, well under the 6 pt floor
#: this style's captions set. Font sizes below are written at their *rendered* size and
#: multiplied by ``width / TARGET_WIDTH_IN`` when the figure is built wider than the column,
#: so what is specified is what a reader sees. Panel geometry is untouched.
TARGET_WIDTH_IN = 5.5

FIGURE_FONT = "Times New Roman"
plt.rcParams.update(
    {
        "font.family": FIGURE_FONT,
        "mathtext.fontset": "custom",
        "mathtext.rm": FIGURE_FONT,
        "mathtext.it": f"{FIGURE_FONT}:italic",
        "mathtext.bf": f"{FIGURE_FONT}:bold",
        "font.size": 7,
        "axes.linewidth": 0.6,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
    }
)

SCATTER = "#4C72B0"
BAND = "#DD8452"
MEDIAN = "#C44E52"
DIAGONAL = "#555555"


def _panel(ax, family: str, cohort: str, cut: float, strata: pd.DataFrame,
           shuffle: pd.DataFrame, show_legend: bool = False, k: float = 1.0) -> None:
    detected = per_case_leads(family, cohort, cut)
    window = detected["observed_min"].to_numpy(float)
    lead = detected["lead"].to_numpy(float)

    # Jitter only along x, and only within a minute, so overplotting at the integer grid does
    # not hide density. The y values are the reported quantity and are left exact.
    rng = np.random.default_rng(0)
    jitter = rng.uniform(-0.35, 0.35, size=window.size)

    ax.plot([0, ALERT_WINDOW_MIN], [0, ALERT_WINDOW_MIN], color=DIAGONAL, lw=0.7, ls="--",
            zorder=1, label="ceiling: lead = window")
    ax.scatter(window + jitter, lead, s=2.0, alpha=0.18, color=SCATTER, linewidths=0,
               zorder=2, label="one case")

    cell_shuffle = shuffle[
        (shuffle["family"] == family)
        & (shuffle["cohort"] == cohort)
        & (shuffle["variant"] == "hold")
    ]
    if len(cell_shuffle):
        row = cell_shuffle.iloc[0]
        grid = np.linspace(0, ALERT_WINDOW_MIN, 200)
        ax.fill_between(
            grid,
            grid * float(row["null_ratio_ci_lo"]),
            grid * float(row["null_ratio_ci_hi"]),
            color=BAND, alpha=0.30, lw=0, zorder=3,
            label="cross-case shuffle null",
        )

    cell_strata = strata[(strata["family"] == family) & (strata["cohort"] == cohort)]
    if len(cell_strata):
        ax.plot(
            cell_strata["window_median"], cell_strata["lead_median"],
            marker="o", ms=3.0, lw=1.2, color=MEDIAN, zorder=4,
            label="quintile median",
        )
        ax.errorbar(
            cell_strata["window_median"], cell_strata["lead_median"],
            yerr=[
                cell_strata["lead_median"] - cell_strata["lead_ci_lo"],
                cell_strata["lead_ci_hi"] - cell_strata["lead_median"],
            ],
            fmt="none", ecolor=MEDIAN, elinewidth=0.8, capsize=1.5, zorder=4,
        )

    ax.set_xlim(0, ALERT_WINDOW_MIN + 1)
    ax.set_ylim(0, ALERT_WINDOW_MIN + 1)
    ax.set_aspect("equal")
    ax.set_xticks([0, 20, 40, 60])
    ax.set_yticks([0, 20, 40, 60])
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    if show_legend:
        ax.legend(loc="upper left", frameon=False, fontsize=5.0 * k, handlelength=1.2,
                  borderpad=0.1, labelspacing=0.25)


def build_cohorts(width: float, height: float, suffix: str) -> Path:
    """The transformer across three cohorts. The body figure."""
    k = width / TARGET_WIDTH_IN
    OUT.mkdir(parents=True, exist_ok=True)
    strata = pd.read_csv(HERE / "n3_stratified" / "n3_strata.csv")
    shuffle = pd.read_csv(HERE / "n2_score_shuffle" / "n2_score_shuffle.csv")
    cuts = headline_cuts()

    fig, axes = plt.subplots(1, len(COHORT_ORDER), figsize=(width, height))
    for column, cohort in enumerate(COHORT_ORDER):
        ax = axes[column]
        _panel(ax, "transformer", cohort, float(cuts["transformer"]), strata, shuffle,
               show_legend=(column == 0), k=k)
        ax.set_title(COHORT_LABELS[cohort], fontsize=7 * k, pad=3)
        ax.tick_params(labelsize=6.0 * k)
        if column == 0:
            ax.set_ylabel("Alert lead time, min", fontsize=6.8 * k)
        ax.set_xlabel("Observed window, min", fontsize=6.8 * k)
    fig.subplots_adjust(left=0.075, right=0.995, top=0.92, bottom=0.20, wspace=0.26)

    path = OUT / f"Figure_lead_vs_window_{suffix}.pdf"
    fig.savefig(path)
    fig.savefig(OUT / f"Figure_lead_vs_window_{suffix}.png", dpi=PNG_DPI)
    plt.close(fig)
    return path


def build_families(width: float, height: float, suffix: str) -> Path:
    """All five families on one cohort. The appendix figure.

    Split out of the body figure for page budget: the body keeps the three cohort panels,
    and this carries the claim that the relationship is not one architecture's.
    """
    k = width / TARGET_WIDTH_IN
    OUT.mkdir(parents=True, exist_ok=True)
    strata = pd.read_csv(HERE / "n3_stratified" / "n3_strata.csv")
    shuffle = pd.read_csv(HERE / "n2_score_shuffle" / "n2_score_shuffle.csv")
    cuts = headline_cuts()

    fig, axes = plt.subplots(1, len(FAMILY_ORDER), figsize=(width, height))
    for column, family in enumerate(FAMILY_ORDER):
        ax = axes[column]
        _panel(ax, family, "epic_test", float(cuts[family]), strata, shuffle,
               show_legend=False, k=k)
        ax.set_title(FAMILY_LABELS[family], fontsize=6.5 * k, pad=2)
        ax.tick_params(labelsize=5.5 * k)
        if column == 0:
            ax.set_ylabel("Alert lead time, min", fontsize=6.5 * k)
        ax.set_xlabel("Observed window, min", fontsize=6.5 * k)
    fig.subplots_adjust(left=0.055, right=0.995, top=0.90, bottom=0.22, wspace=0.26)

    # Shared legend below the row. In-axes it landed on the shuffle band and the ceiling
    # line in the transformer panel, where the points hug the diagonal and leave no empty
    # corner; these panels are 1.9 in tall, so there is no interior room at any location.
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, -0.045),
               ncol=4, frameon=False, fontsize=5.8 * k, handlelength=1.4,
               columnspacing=1.8, borderpad=0.1, handletextpad=0.5)

    path = OUT / f"Figure_lead_vs_window_families_{suffix}.pdf"
    fig.savefig(path)
    fig.savefig(OUT / f"Figure_lead_vs_window_families_{suffix}.png", dpi=PNG_DPI)
    plt.close(fig)
    return path


def main() -> None:
    # Both widths, as the conference module does: the narrow one for a single column and the
    # wide one for the full text block. Regenerate rather than scale with \includegraphics.
    wide = build_cohorts(7.0, 2.5, "wide")
    narrow = build_cohorts(5.5, 2.1, "narrow")
    families = build_families(7.0, 1.9, "wide")
    write_manifest(
        OUT,
        "figure_lead_vs_window",
        [],
        extra={
            "matplotlib_version": matplotlib.__version__,
            "font": FIGURE_FONT,
            "outputs": [wide.name, narrow.name, families.name],
        },
        hash_inputs=False,
    )
    print(f"figures: {wide.name}, {narrow.name}, {families.name} "
          f"(matplotlib {matplotlib.__version__})")


if __name__ == "__main__":
    main()
