"""Reproduction gate for N1-N3.  Halts the pipeline before any N step runs.

Two things have to still be true, or an N result is a null for a statistic other than the
one it claims to be a null for:

1. **``per_case_leads`` reproduces B1b.**  ``lib_n.per_case_leads`` is a lift of
   ``b1b_suppression._lead_vs_observation``'s per-case construction.  Aggregating it must
   return ``n_detected``, ``median_lead_min``, ``median_observed_min``,
   ``lead_over_observed_median`` and ``spearman_lead_vs_observed`` identical to
   ``b1b_lead_vs_observation.csv`` in all fifteen cells.  Tolerance 1e-12 on the
   continuous columns and exact on the count.

2. **``window_matrix`` + ``first_crossing_elapsed`` reproduce the same leads.**  N2 does not
   use ``per_case_leads``; it needs every case's scores on a dense elapsed grid, and it
   recomputes the crossing with ``argmax`` over a boolean matrix rather than with a groupby.
   That is a second implementation of the alert rule, so it is checked against the first.
   A silent disagreement here would make the N2 null incomparable with the observed value
   it is placed beside.  Tolerance 0 -- these are the same integers or they are not.

Nothing here writes a result.  It writes a pass/fail table and exits nonzero on any
disagreement.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib_n import (  # noqa: E402
    ALERT_WINDOW_MIN,
    REPO,
    cells,
    df_to_md,
    first_crossing_elapsed,
    headline_cuts,
    per_case_leads,
    weighted_spearman,
    window_matrix,
    write_manifest,
)

OUT = Path(__file__).resolve().parent / "step0_repro"

B1B_CSV = (
    REPO
    / "analysis"
    / "lead_time_origin_2026"
    / "b1b_suppression"
    / "b1b_lead_vs_observation.csv"
)

#: Columns compared against B1b, and the tolerance each is compared at.
COMPARED = {
    "n_detected": 0.0,
    "median_lead_min": 1e-12,
    "median_observed_min": 1e-12,
    "lead_over_observed_median": 1e-12,
    "spearman_lead_vs_observed": 1e-12,
}


def _observed_row(family: str, cohort: str, cut: float) -> dict:
    detected = per_case_leads(family, cohort, cut)
    lead = detected["lead"].to_numpy(float)
    observed = detected["observed_min"].to_numpy(float)
    return {
        "family": family,
        "cohort": cohort,
        "n_detected": float(len(detected)),
        "median_lead_min": float(np.median(lead)),
        "median_observed_min": float(np.median(observed)),
        "lead_over_observed_median": float(np.median(detected["ratio"].to_numpy(float))),
        "spearman_lead_vs_observed": float(
            weighted_spearman(observed, lead, np.ones(len(detected), int))
        ),
    }


def _matrix_leads(family: str, cohort: str, cut: float) -> pd.DataFrame:
    """Per-case lead recomputed the way N2 recomputes it, for comparison with B1b's rule.

    The matrix is indexed by elapsed minutes from the start of the case's own alert window,
    so ``lead = observed_min - elapsed`` recovers ``t_to_event`` at the crossing whenever the
    window is not truncated by the 60-minute cap.  For a case at the cap the window starts at
    ``t_to_event = 60`` and the same arithmetic holds with ``observed_min = 60``.
    """
    scores, valid, cases = window_matrix(family, cohort)
    first = first_crossing_elapsed(scores, valid, cut)
    cases = cases.copy()
    cases["elapsed_at_crossing"] = first
    cases["lead"] = np.where(first >= 0, cases["observed_min"].to_numpy() - first, np.nan)
    detected = cases[(cases["label"] == 1) & (first >= 0) & (cases["observed_min"] > 0)]
    return detected[["case_id", "lead", "observed_min"]].reset_index(drop=True)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    published = pd.read_csv(B1B_CSV).set_index(["family", "cohort"])
    cuts = headline_cuts()

    rows: list[dict] = []
    for family, cohort in cells():
        cut = float(cuts[family])
        observed = _observed_row(family, cohort, cut)
        reference = published.loc[(family, cohort)]
        for column, tolerance in COMPARED.items():
            expected = float(reference[column])
            got = float(observed[column])
            rows.append(
                {
                    "check": f"b1b/{family}/{cohort}/{column}",
                    "expected": expected,
                    "observed": got,
                    "tolerance": tolerance,
                    "status": "pass" if abs(got - expected) <= tolerance else "FAIL",
                }
            )

        # The second implementation of the alert rule.
        by_groupby = (
            per_case_leads(family, cohort, cut)
            .set_index("case_id")["lead"]
            .sort_index()
        )
        by_matrix = _matrix_leads(family, cohort, cut).set_index("case_id")["lead"].sort_index()
        same_cases = by_groupby.index.equals(by_matrix.index)
        max_diff = (
            float(np.nanmax(np.abs(by_groupby.to_numpy() - by_matrix.to_numpy())))
            if same_cases and len(by_groupby)
            else float("inf")
        )
        rows.append(
            {
                "check": f"matrix/{family}/{cohort}/detected_case_set",
                "expected": float(len(by_groupby)),
                "observed": float(len(by_matrix)),
                "tolerance": 0.0,
                "status": "pass" if same_cases else "FAIL",
            }
        )
        rows.append(
            {
                "check": f"matrix/{family}/{cohort}/lead",
                "expected": 0.0,
                "observed": max_diff,
                "tolerance": 0.0,
                "status": "pass" if max_diff == 0.0 else "FAIL",
            }
        )

    frame = pd.DataFrame(rows)
    frame.to_csv(OUT / "step0_repro.csv", index=False)

    failed = frame[frame["status"] == "FAIL"]
    lines = [
        "# N step 0 — reproduction gate",
        "",
        f"`per_case_leads` and the N2 crossing matrix against "
        f"`{B1B_CSV.relative_to(REPO)}`, alert window "
        f"`0 < t_to_event <= {ALERT_WINDOW_MIN}`, transported 80% thresholds.",
        "",
        f"**{len(frame) - len(failed)}/{len(frame)} checks passed.**",
        "",
    ]
    if len(failed):
        lines += ["## Failures", "", df_to_md(failed, float_fmt="{:.12g}"), ""]
    lines += ["## All checks", "", df_to_md(frame, float_fmt="{:.12g}"), ""]
    (OUT / "step0_repro.md").write_text("\n".join(lines))

    write_manifest(
        OUT,
        "n_step0_repro",
        [],
        extra={
            "source": str(B1B_CSV.relative_to(REPO)),
            "n_checks": int(len(frame)),
            "n_failed": int(len(failed)),
        },
        hash_inputs=False,
    )

    print(f"{len(frame) - len(failed)}/{len(frame)} checks passed")
    if len(failed):
        print(failed.to_string(index=False))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
