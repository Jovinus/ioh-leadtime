"""B4 - which side of the event-control gap is actually moving?

Figure 3C shows event and control mean scores diverging rather than drifting upward
together, and the manuscript reads that divergence as evidence against an accumulation-only
explanation. A6 reports the two sides separately, and in MOVER (EPIC) the transformer's
control median falls by 0.073 over 60-to-5 while its event median rises by 0.046: more than
half the widening is the controls going down, not the events going up. That is currently
unreported, and it bears on what the divergence claim can support. A gap that widens because
controls fall is still a real gap -- discrimination is a between-group statement -- but it is
not evidence that the model is picking up an approaching event.

So the gap at each lead-time bin is decomposed against each side's own 60-minute baseline:

    gap(t) - gap(60) = [E(t) - E(60)] - [C(t) - C(60)]
                     =    event side    -  control side

and each side is reported as a share of that widening. The shares sum to 1 by construction.
A share outside [0, 1] is meaningful rather than an error: it means that side moved *against*
the widening while the other side more than compensated.

The sample is fixed. Only episodes with an observed bin at every centre from 60 to 5 enter,
so the decomposition is not reading a change of denominator as a change of score -- which is
the confound A7 exists to measure. Retention against the A6 spanning sample is reported.

All five families: the claim is about what the divergence in the published figure consists
of, which is a statement about the task rather than about one architecture.

Post-hoc on cached per-minute scores; no retraining.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib_b import (  # noqa: E402
    COHORT_LABELS,
    COHORT_ORDER,
    FAMILY_LABELS,
    FAMILY_ORDER,
    N_BOOTSTRAP_PATIENT,
    assign_bin,
    bootstrap_p_two_sided,
    df_to_md,
    load_scored,
    percentile_ci,
    seed_for,
    weight_matrix,
    write_manifest,
)

OUT = Path(__file__).resolve().parent / "b4_divergence_asymmetry"

BASELINE_MIN = 60
ENDPOINT_MIN = 5
#: The published bin centres inside the window, far-from-onset first.
BINS = tuple(range(BASELINE_MIN, ENDPOINT_MIN - 1, -5))


def _episode_bin_matrix(family: str, cohort: str) -> tuple[pd.DataFrame, int]:
    """Episodes observed in every bin from 60 to 5, one column per bin.

    Returns the fixed-cohort matrix and the count of episodes that merely span the two
    edges, so the retention cost of fixing the sample is visible.
    """
    frame = load_scored(family, cohort)
    frame = frame[(frame["t_to_event"] > 0) & np.isfinite(frame["score"])]
    frame = frame.assign(bin_center=assign_bin(frame["t_to_event"]))
    frame = frame[frame["bin_center"].notna() & frame["bin_center"].isin(BINS)]
    per_bin = (
        frame.groupby(["case_id", "cluster_id", "label", "bin_center"], sort=False)["score"]
        .mean()
        .unstack("bin_center")
    )
    spanning = int(per_bin[[BASELINE_MIN, ENDPOINT_MIN]].notna().all(axis=1).sum())
    complete = per_bin.dropna(axis=0, how="any").reset_index()
    return complete, spanning


def _decompose(matrix: pd.DataFrame, family: str, cohort: str) -> pd.DataFrame:
    """Per-bin event-side and control-side shares of the widening, with paired intervals."""
    codes, clusters = pd.factorize(matrix["cluster_id"], sort=True)
    rng = np.random.default_rng(seed_for("b4", family, cohort))
    weights = weight_matrix(len(clusters), rng, N_BOOTSTRAP_PATIENT)
    is_event = (matrix["label"] == 1).to_numpy()

    def _means(w: np.ndarray, column: float) -> tuple[float, float]:
        values = matrix[column].to_numpy(float)
        we, wc = w * is_event, w * (~is_event)
        return (
            float(np.dot(values, we) / we.sum()) if we.sum() else np.nan,
            float(np.dot(values, wc) / wc.sum()) if wc.sum() else np.nan,
        )

    unit = np.ones(len(matrix), dtype=np.int32)
    base_event, base_control = _means(unit, BASELINE_MIN)

    rows: list[dict] = []
    for centre in BINS:
        if centre == BASELINE_MIN:
            continue
        event, control = _means(unit, centre)
        d_event = event - base_event
        d_control = control - base_control
        widening = d_event - d_control

        draws = np.empty((N_BOOTSTRAP_PATIENT, 4))
        for replicate in range(N_BOOTSTRAP_PATIENT):
            w = weights[replicate][codes]
            be, bc = _means(w, BASELINE_MIN)
            e, c = _means(w, centre)
            de, dc = e - be, c - bc
            width = de - dc
            draws[replicate] = (
                de,
                dc,
                de / width if width != 0 else np.nan,
                -dc / width if width != 0 else np.nan,
            )

        row = {
            "family": family,
            "family_label": FAMILY_LABELS[family],
            "cohort": cohort,
            "cohort_label": COHORT_LABELS[cohort],
            "bin_center_min": centre,
            "n_event": int(is_event.sum()),
            "n_control": int((~is_event).sum()),
            "n_clusters": int(len(clusters)),
            "event_mean_baseline": base_event,
            "control_mean_baseline": base_control,
            "event_mean": event,
            "control_mean": control,
            "gap_baseline": base_event - base_control,
            "gap": event - control,
            "event_side_change": d_event,
            "control_side_change": d_control,
            "gap_widening": widening,
            "event_side_share": d_event / widening if widening else np.nan,
            "control_side_share": -d_control / widening if widening else np.nan,
        }
        for index, name in enumerate(
            ("event_side_change", "control_side_change", "event_side_share", "control_side_share")
        ):
            lo, hi = percentile_ci(draws[:, index])
            row[f"{name}_ci_lo"], row[f"{name}_ci_hi"] = lo, hi
        # Is the widening split evenly?  Tested on the event share against 0.5.
        row["event_share_vs_half_p"] = bootstrap_p_two_sided(draws[:, 2] - 0.5)
        rows.append(row)
    return pd.DataFrame(rows)


def run() -> dict[str, pd.DataFrame]:
    OUT.mkdir(parents=True, exist_ok=True)
    parts: list[pd.DataFrame] = []
    retention: list[dict] = []
    for family in FAMILY_ORDER:
        for cohort in COHORT_ORDER:
            matrix, spanning = _episode_bin_matrix(family, cohort)
            retention.append(
                {
                    "family": family,
                    "cohort": cohort,
                    "n_spanning_edges_only": spanning,
                    "n_complete_all_bins": int(len(matrix)),
                    "retention": float(len(matrix) / spanning) if spanning else np.nan,
                    "n_event_complete": int((matrix["label"] == 1).sum()),
                    "n_control_complete": int((matrix["label"] == 0).sum()),
                }
            )
            parts.append(_decompose(matrix, family, cohort))
            print(f"  b4 {family} / {cohort}", flush=True)
    tables = {
        "decomposition": pd.concat(parts, ignore_index=True),
        "retention": pd.DataFrame(retention),
    }
    for name, frame in tables.items():
        frame.to_csv(OUT / f"b4_{name}.csv", index=False)
    _write_report(tables)
    write_manifest(
        OUT,
        "b4_divergence_asymmetry",
        [],
        extra={
            "baseline_min": BASELINE_MIN,
            "endpoint_min": ENDPOINT_MIN,
            "bins_min": list(BINS),
            "sample": "episodes with an observed bin at every centre from 60 to 5",
            "decomposition": "gap(t) - gap(60) = [E(t) - E(60)] - [C(t) - C(60)]",
            "shares": "each side divided by the widening; they sum to 1 by construction",
            "n_bootstrap": N_BOOTSTRAP_PATIENT,
            "seed_base": seed_for("b4", "transformer", "epic_test"),
        },
    )
    return tables


def _write_report(tables: dict[str, pd.DataFrame]) -> None:
    frame = tables["decomposition"]
    lines = [
        "# B4 - which side of the event-control gap is moving?\n",
        "The gap at each lead-time bin is measured against each side's own 60-minute "
        "baseline, so `gap(t) - gap(60)` splits exactly into an event-side change and a "
        "control-side change. Shares sum to 1; a share outside [0, 1] means that side moved "
        "against the widening. Fixed sample: only episodes observed in every bin from 60 to "
        "5 minutes.\n",
        "## Sample retention when the denominator is fixed\n",
        df_to_md(tables["retention"]),
        "",
        f"## The endpoint bin, {ENDPOINT_MIN} minutes before the reference time\n",
    ]
    end = frame[frame["bin_center_min"] == ENDPOINT_MIN]
    for cohort in COHORT_ORDER:
        cell = end[end["cohort"] == cohort]
        table = pd.DataFrame(
            {
                "Model": cell["family_label"],
                "Event side (95% CI)": [
                    f"{r.event_side_change:+.3f} ({r.event_side_change_ci_lo:+.3f} to "
                    f"{r.event_side_change_ci_hi:+.3f})" for r in cell.itertuples()
                ],
                "Control side (95% CI)": [
                    f"{r.control_side_change:+.3f} ({r.control_side_change_ci_lo:+.3f} to "
                    f"{r.control_side_change_ci_hi:+.3f})" for r in cell.itertuples()
                ],
                "Widening": cell["gap_widening"].map("{:+.3f}".format),
                "Event share (95% CI)": [
                    f"{r.event_side_share:.2f} ({r.event_side_share_ci_lo:.2f}–"
                    f"{r.event_side_share_ci_hi:.2f})" for r in cell.itertuples()
                ],
                "Control share (95% CI)": [
                    f"{r.control_side_share:.2f} ({r.control_side_share_ci_lo:.2f}–"
                    f"{r.control_side_share_ci_hi:.2f})" for r in cell.itertuples()
                ],
                "P, event share vs 0.5": cell["event_share_vs_half_p"].map("{:.4f}".format),
            }
        )
        lines += [f"### {COHORT_LABELS[cohort]}\n", df_to_md(table), ""]

    lines += [
        "## Every bin\n",
        df_to_md(
            frame[["cohort_label", "family_label", "bin_center_min", "event_side_change",
                   "control_side_change", "gap_widening", "event_side_share",
                   "control_side_share"]].round(4)
        ),
        "",
    ]
    (OUT / "b4_divergence_asymmetry.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    tables = run()
    end = tables["decomposition"]
    end = end[end["bin_center_min"] == ENDPOINT_MIN]
    print("\nEvent-side and control-side contributions to the widening at 5 minutes:")
    print(
        end[["cohort", "family", "event_side_change", "control_side_change", "gap_widening",
             "event_side_share", "control_side_share"]].round(3).to_string(index=False)
    )


if __name__ == "__main__":
    main()
