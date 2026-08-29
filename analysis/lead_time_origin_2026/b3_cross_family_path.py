"""B3 - does the late-jump path shape belong to the transformer, or to the task?

A6 measured, for each episode, how far the score moved over a window and how it got there:
the gross upward path, the gross downward path, the net displacement, the ratio of net to
path (``directedness``: +1 a monotone rise, 0 a pure wobble, -1 a monotone fall), and the
largest single step as a share of the gross rise. Those numbers are already computed for
all five families and all three cohorts with cluster-bootstrap intervals, so B3 verifies
and assembles rather than recomputes -- and says explicitly whether the intervals separate.

The reason this matters is not a model comparison. If every family lands in the same place,
the shape is a property of the prediction task under these inputs rather than of any
architecture, which is a substantially stronger and more portable claim than "the
transformer's trajectory jumps late". If the families separate, the ordering is the finding,
and it is worth knowing whether it contradicts the AUROC ordering.

Two windows are reported. 60-to-5 is the widest published window. 60-to-10 stops short of
the final 5 minutes, so comparing the two isolates how much of the movement is confined to
those minutes, and whether that confinement is itself family-invariant.

Windows whose median step count is at or below 2 are excluded: with a single step the
directedness is pinned at +/-1 and the largest-step share at 1 by arithmetic, not by
behaviour. The filter is applied on ``median_n_steps`` and stated in the output.

Reads ``a6_window_trend.csv``. Computes no new estimate.
"""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib_b import (  # noqa: E402
    COHORT_LABELS,
    COHORT_ORDER,
    FAMILY_ORDER,
    REPO,
    df_to_md,
    write_manifest,
)

OUT = Path(__file__).resolve().parent / "b3_cross_family_path"
A6_CSV = (
    REPO / "analysis" / "patient_trajectory_2026" / "a6_window_trend" / "a6_window_trend.csv"
)

WINDOW_START_MIN = 60
ENDPOINTS = (5, 10)
#: Both directedness and the largest-step share are arithmetically pinned when a window
#: holds one step, so a window at or below this many median steps is not reported.
MIN_MEDIAN_STEPS = 3

MEASURES = (
    ("gross_up", "Total upward path"),
    ("gross_down", "Total downward path"),
    ("delta", "Net change"),
    ("directedness", "Directedness"),
    ("max_up_share", "Largest single step / gross rise"),
)


def _load() -> pd.DataFrame:
    frame = pd.read_csv(A6_CSV)
    needed = {f"{m}_median" for m, _ in MEASURES}
    needed |= {f"{m}_median_ci_lo" for m, _ in MEASURES}
    needed |= {f"{m}_median_ci_hi" for m, _ in MEASURES}
    needed |= {"median_n_steps", "n_episodes_spanning", "n_clusters", "cluster_level"}
    missing = needed - set(frame.columns)
    if missing:
        raise AssertionError(f"a6_window_trend.csv is missing {sorted(missing)}")
    return frame


def run() -> dict[str, pd.DataFrame]:
    OUT.mkdir(parents=True, exist_ok=True)
    a6 = _load()
    selected = a6[
        (a6["window_start_min"] == WINDOW_START_MIN)
        & (a6["endpoint_min"].isin(ENDPOINTS))
        & (a6["group"] == "event")
    ].copy()

    dropped = selected[selected["median_n_steps"] < MIN_MEDIAN_STEPS]
    kept = selected[selected["median_n_steps"] >= MIN_MEDIAN_STEPS].copy()

    # Derived, not estimated: how many score units the path travelled per unit of net
    # displacement.  This is the quantity that reconciles a near-zero net change with an
    # early threshold crossing -- a long path can touch a high threshold without trending.
    kept["path_per_net"] = kept["path_length_median"] / kept["delta_median"].abs()

    columns = ["family", "family_label", "cohort", "cohort_label", "endpoint_min", "window",
               "n_episodes_spanning", "n_clusters", "cluster_level", "median_n_steps",
               "path_length_median", "path_per_net"]
    for measure, _ in MEASURES:
        columns += [f"{measure}_median", f"{measure}_median_ci_lo", f"{measure}_median_ci_hi"]
    comparison = kept[columns].sort_values(
        ["endpoint_min", "cohort", "family"],
        key=lambda s: s.map({f: i for i, f in enumerate(FAMILY_ORDER)}) if s.name == "family" else
                      (s.map({c: i for i, c in enumerate(COHORT_ORDER)}) if s.name == "cohort" else s),
    ).reset_index(drop=True)

    overlap = _overlap(kept)
    last5 = _last_five(kept)

    tables = {
        "comparison": comparison,
        "directedness_overlap": overlap,
        "last5_concentration": last5,
        "excluded_windows": dropped[["family", "cohort", "window", "median_n_steps"]],
    }
    for name, frame in tables.items():
        frame.to_csv(OUT / f"b3_{name}.csv", index=False)
    _write_report(tables)
    write_manifest(
        OUT,
        "b3_cross_family_path",
        [],
        extra={
            "source": str(A6_CSV.relative_to(REPO)),
            "window_start_min": WINDOW_START_MIN,
            "endpoints_min": list(ENDPOINTS),
            "group": "event",
            "sample": "spanning (an observed bin at both window edges)",
            "min_median_steps": MIN_MEDIAN_STEPS,
            "n_windows_excluded_for_step_count": int(len(dropped)),
            "recomputed": "nothing; A6 medians and cluster-bootstrap intervals are read",
        },
    )
    return tables


def _overlap(kept: pd.DataFrame) -> pd.DataFrame:
    """Pairwise interval overlap for directedness, within cohort and endpoint."""
    rows: list[dict] = []
    for endpoint in ENDPOINTS:
        for cohort in COHORT_ORDER:
            cell = kept[(kept["endpoint_min"] == endpoint) & (kept["cohort"] == cohort)]
            indexed = cell.set_index("family")
            pairs_overlapping = 0
            pairs_total = 0
            for left, right in itertools.combinations(FAMILY_ORDER, 2):
                if left not in indexed.index or right not in indexed.index:
                    continue
                a, b = indexed.loc[left], indexed.loc[right]
                overlaps = (
                    a["directedness_median_ci_lo"] <= b["directedness_median_ci_hi"]
                    and b["directedness_median_ci_lo"] <= a["directedness_median_ci_hi"]
                )
                pairs_total += 1
                pairs_overlapping += int(overlaps)
                rows.append(
                    {
                        "endpoint_min": endpoint,
                        "cohort": cohort,
                        "cohort_label": COHORT_LABELS[cohort],
                        "family_a": left,
                        "family_b": right,
                        "directedness_a": a["directedness_median"],
                        "directedness_b": b["directedness_median"],
                        "ci_a": f"{a['directedness_median_ci_lo']:.3f}–{a['directedness_median_ci_hi']:.3f}",
                        "ci_b": f"{b['directedness_median_ci_lo']:.3f}–{b['directedness_median_ci_hi']:.3f}",
                        "intervals_overlap": overlaps,
                    }
                )
            rows.append(
                {
                    "endpoint_min": endpoint,
                    "cohort": cohort,
                    "cohort_label": COHORT_LABELS[cohort],
                    "family_a": "ALL PAIRS",
                    "family_b": "",
                    "directedness_a": np.nan,
                    "directedness_b": np.nan,
                    "ci_a": "",
                    "ci_b": "",
                    "intervals_overlap": pairs_overlapping == pairs_total and pairs_total > 0,
                }
            )
    return pd.DataFrame(rows)


def _last_five(kept: pd.DataFrame) -> pd.DataFrame:
    """How much of the 60-to-5 movement is absent from 60-to-10, family by family."""
    wide = kept.pivot_table(
        index=["family", "family_label", "cohort", "cohort_label"],
        columns="endpoint_min",
        values=["delta_median", "directedness_median", "gross_up_median", "max_up_share_median"],
    )
    wide.columns = [f"{a}_ep{b}" for a, b in wide.columns.to_flat_index()]
    wide = wide.reset_index()
    wide["delta_last5"] = wide["delta_median_ep5"] - wide["delta_median_ep10"]
    wide["delta_last5_share_of_60_5"] = wide["delta_last5"] / wide["delta_median_ep5"]
    wide["directedness_drop_without_last5"] = (
        wide["directedness_median_ep5"] - wide["directedness_median_ep10"]
    )
    return wide


def _write_report(tables: dict[str, pd.DataFrame]) -> None:
    comparison = tables["comparison"]
    lines = [
        "# B3 - is the path shape a property of the transformer or of the task?\n",
        "Event episodes, spanning sample, window start 60 minutes before the reference time. "
        "`directedness` is net change divided by total path length: +1 a monotone rise, 0 a "
        "pure wobble, -1 a monotone fall. `path_per_net` is total path length divided by the "
        "absolute net change -- how much travelling bought one unit of displacement. All "
        "values are medians over episodes with cluster-bootstrap 95% intervals, read from "
        f"A6; nothing is recomputed. Windows with median step count below {MIN_MEDIAN_STEPS} "
        "are excluded because directedness and the largest-step share are then pinned by "
        "arithmetic.\n",
    ]
    for endpoint in ENDPOINTS:
        lines.append(f"## The 60-to-{endpoint} window\n")
        for cohort in COHORT_ORDER:
            cell = comparison[
                (comparison["endpoint_min"] == endpoint) & (comparison["cohort"] == cohort)
            ]
            table = pd.DataFrame(
                {
                    "Model": cell["family_label"],
                    "n": cell["n_episodes_spanning"],
                    "Up path": cell["gross_up_median"].map("{:.3f}".format),
                    "Down path": cell["gross_down_median"].map("{:.3f}".format),
                    "Net": cell["delta_median"].map("{:+.3f}".format),
                    "Directedness (95% CI)": [
                        f"{r.directedness_median:+.3f} ({r.directedness_median_ci_lo:+.3f} to "
                        f"{r.directedness_median_ci_hi:+.3f})"
                        for r in cell.itertuples()
                    ],
                    "Largest step / gross rise": cell["max_up_share_median"].map("{:.3f}".format),
                    "Path per unit net": cell["path_per_net"].map("{:.0f}".format),
                }
            )
            lines += [f"### {COHORT_LABELS[cohort]}\n", df_to_md(table), ""]

    lines += [
        "## Do the directedness intervals separate?\n",
        "Every pair of families within a cohort and window. `ALL PAIRS` is true only if "
        "every pairwise interval overlaps in that cell.\n",
        df_to_md(tables["directedness_overlap"]),
        "",
        "## What the final 5 minutes carry\n",
        "`delta_last5` is the 60-to-5 net change minus the 60-to-10 net change: the "
        "displacement that exists only when the last 5 minutes are included.\n",
        df_to_md(
            tables["last5_concentration"][
                ["family_label", "cohort_label", "delta_median_ep5", "delta_median_ep10",
                 "delta_last5", "delta_last5_share_of_60_5",
                 "directedness_median_ep5", "directedness_median_ep10"]
            ]
        ),
        "",
    ]
    if len(tables["excluded_windows"]):
        lines += ["## Windows excluded on step count\n",
                  df_to_md(tables["excluded_windows"]), ""]
    (OUT / "b3_cross_family_path.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    tables = run()
    verdict = tables["directedness_overlap"]
    verdict = verdict[verdict["family_a"] == "ALL PAIRS"]
    print("Directedness intervals overlap across all five families?")
    print(verdict[["endpoint_min", "cohort", "intervals_overlap"]].to_string(index=False))
    print()
    print(
        tables["comparison"][
            ["endpoint_min", "cohort", "family", "delta_median", "directedness_median",
             "directedness_median_ci_lo", "directedness_median_ci_hi", "path_per_net"]
        ].round(3).to_string(index=False)
    )


if __name__ == "__main__":
    main()
