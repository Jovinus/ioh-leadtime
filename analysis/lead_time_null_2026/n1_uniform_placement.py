"""N1 — is the observed lead-to-window ratio different from a crossing placed at random?

The weakest form of the objection to B1b's finding is that ``lead / observed_window`` is a
ratio of a quantity to its own upper bound, so it is bounded in [0, 1] and some positive
value is guaranteed.  N1 fixes the reference point: place the crossing uniformly at random
inside each case's own window and the median ratio is 0.5 by construction.  Anything the
observed ratio does relative to 0.5 is therefore not an artefact of the bound.

This is necessary but weak alone, and the report says so.  It rules out only the crudest
reading.  It does **not** rule out the possibility that the ratio is a property of the
scoring policy rather than of the individual patient; that is N2's job.

Per case the null draws a crossing minute uniformly from the integers 1..L, where L is the
case's own observed pre-onset window capped at the published 60-minute alert window -- the
same L the observed ratio is divided by.  The null is redrawn ``N_PERMUTATIONS`` times to
give it a distribution rather than a point, and the observed side carries a
``N_BOOTSTRAP_PATIENT``-replicate cluster bootstrap.

Post-hoc on cached scores.  Nothing is retrained, refitted or re-scored.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib_n import (  # noqa: E402
    COHORT_LABELS,
    FAMILY_LABELS,
    N_BOOTSTRAP_PATIENT,
    N_PERMUTATIONS,
    cells,
    cluster_bootstrap,
    df_to_md,
    headline_cuts,
    per_case_leads,
    percentile_ci,
    seed_for,
    weighted_median,
    write_manifest,
)

OUT = Path(__file__).resolve().parent / "n1_uniform_placement"

#: The null's median ratio, by construction.  Stated rather than estimated so the report can
#: show the simulated value landing on it.
ANALYTIC_NULL_RATIO = 0.5


def _cell(family: str, cohort: str, cut: float) -> dict:
    detected = per_case_leads(family, cohort, cut)
    lead = detected["lead"].to_numpy(float)
    observed = detected["observed_min"].to_numpy(float)
    ratio = detected["ratio"].to_numpy(float)
    n = len(detected)

    observed_ratio = float(np.median(ratio))
    observed_lead = float(np.median(lead))

    codes, weights = cluster_bootstrap(detected, "n1", family, cohort)
    ratio_draws = np.empty(N_BOOTSTRAP_PATIENT)
    lead_draws = np.empty(N_BOOTSTRAP_PATIENT)
    for replicate in range(N_BOOTSTRAP_PATIENT):
        w = weights[replicate][codes]
        ratio_draws[replicate] = weighted_median(ratio, w)
        lead_draws[replicate] = weighted_median(lead, w)

    # The null. A crossing uniform on the integers 1..L, redrawn N_PERMUTATIONS times.
    rng = np.random.default_rng(seed_for("n1", family, cohort))
    null_ratio = np.empty(N_PERMUTATIONS)
    null_lead = np.empty(N_PERMUTATIONS)
    for draw in range(N_PERMUTATIONS):
        pseudo = rng.integers(1, np.maximum(observed.astype(int), 1) + 1)
        null_lead[draw] = float(np.median(pseudo))
        null_ratio[draw] = float(np.median(pseudo / observed))

    # Two-sided permutation p for observed != null, by interval inversion on the null draws.
    below = float((null_ratio >= observed_ratio).mean())
    above = float((null_ratio <= observed_ratio).mean())
    p_ratio = float(min(1.0, max(2.0 * min(below, above), 2.0 / N_PERMUTATIONS)))

    row = {
        "family": family,
        "family_label": FAMILY_LABELS[family],
        "cohort": cohort,
        "cohort_label": COHORT_LABELS[cohort],
        "n_detected": n,
        "n_clusters": int(pd.factorize(detected["cluster_id"])[1].size),
        "median_observed_min": float(np.median(observed)),
        "observed_ratio_median": observed_ratio,
        "observed_lead_median": observed_lead,
        "analytic_null_ratio": ANALYTIC_NULL_RATIO,
        "null_ratio_mean": float(null_ratio.mean()),
        "null_lead_mean": float(null_lead.mean()),
        "excess_ratio": observed_ratio - float(null_ratio.mean()),
        "excess_lead_min": observed_lead - float(null_lead.mean()),
        "p_value": p_ratio,
    }
    row["observed_ratio_ci_lo"], row["observed_ratio_ci_hi"] = percentile_ci(ratio_draws)
    row["observed_lead_ci_lo"], row["observed_lead_ci_hi"] = percentile_ci(lead_draws)
    row["null_ratio_ci_lo"], row["null_ratio_ci_hi"] = percentile_ci(null_ratio)
    row["null_lead_ci_lo"], row["null_lead_ci_hi"] = percentile_ci(null_lead)
    return row


def run() -> pd.DataFrame:
    OUT.mkdir(parents=True, exist_ok=True)
    cuts = headline_cuts()
    rows = [_cell(family, cohort, float(cuts[family])) for family, cohort in cells()]
    frame = pd.DataFrame(rows)
    frame.to_csv(OUT / "n1_uniform_placement.csv", index=False)
    return frame


def _write_report(frame: pd.DataFrame) -> None:
    display = pd.DataFrame(
        {
            "Model": frame["family_label"],
            "Cohort": frame["cohort_label"],
            "n": frame["n_detected"],
            "Observed ratio (95% CI)": [
                f"{r.observed_ratio_median:.3f} "
                f"({r.observed_ratio_ci_lo:.3f}–{r.observed_ratio_ci_hi:.3f})"
                for r in frame.itertuples()
            ],
            "Uniform-null ratio (95% CI)": [
                f"{r.null_ratio_mean:.3f} ({r.null_ratio_ci_lo:.3f}–{r.null_ratio_ci_hi:.3f})"
                for r in frame.itertuples()
            ],
            "Excess": frame["excess_ratio"].map("{:+.3f}".format),
            "Observed lead, min": frame["observed_lead_median"].map("{:.0f}".format),
            "Uniform-null lead, min": frame["null_lead_mean"].map("{:.1f}".format),
            "p": frame["p_value"].map("{:.3g}".format),
        }
    )
    lo, hi = frame["excess_ratio"].min(), frame["excess_ratio"].max()
    lines = [
        "# N1 — uniform-placement null",
        "",
        "A crossing placed uniformly at random inside each case's own observed window gives "
        "a median ratio of 0.5 by construction. This fixes the reference point so that the "
        "observed ratio cannot be dismissed as an artefact of the bound.",
        "",
        f"Excess over the uniform null ranges **{lo:+.3f} to {hi:+.3f}** across the fifteen "
        "cells.",
        "",
        "**This is necessary but weak alone.** It rules out only the crudest reading of the "
        "objection. It does not distinguish a ratio that reflects case-specific timing from "
        "one that is a property of the scoring policy; that is N2's question.",
        "",
        df_to_md(display),
        "",
        "## Method",
        "",
        f"Per case the null draws a crossing minute uniformly from the integers 1..L, where "
        f"L is the case's own pre-onset observation length capped at the published "
        f"60-minute alert window -- the same L the observed ratio is divided by. The null "
        f"is redrawn {N_PERMUTATIONS:,} times. The observed side carries a "
        f"{N_BOOTSTRAP_PATIENT:,}-replicate cluster bootstrap, clustering on patient for "
        "MOVER (EPIC) and VitalDB and on case for MOVER (SIS). `p` is two-sided by interval "
        f"inversion on the null draws, floored at 2/{N_PERMUTATIONS:,}.",
        "",
    ]
    (OUT / "n1_uniform_placement.md").write_text("\n".join(lines))


def main() -> None:
    frame = run()
    _write_report(frame)
    write_manifest(
        OUT,
        "n1_uniform_placement",
        [],
        extra={
            "n_cells": int(len(frame)),
            "n_permutations": N_PERMUTATIONS,
            "n_bootstrap": N_BOOTSTRAP_PATIENT,
            "analytic_null_ratio": ANALYTIC_NULL_RATIO,
        },
        hash_inputs=False,
    )
    print(
        f"N1: {len(frame)} cells, excess over uniform null "
        f"{frame['excess_ratio'].min():+.3f} to {frame['excess_ratio'].max():+.3f}"
    )


if __name__ == "__main__":
    main()
