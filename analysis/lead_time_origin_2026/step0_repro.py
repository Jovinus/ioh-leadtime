"""Reproduction gate for B1-B4.  Halts the pipeline before any B step runs.

Three things have to still be true, or a B result is describing a cohort that has silently
moved:

1. **Table 2 comes back out of the source file.** Achieved sensitivity, specificity, PPV,
   NNE and the median lead for all five families at the 80% validation target, against the
   values printed in the manuscript. B1 re-derives the alert decomposition from the same
   thresholds, so if Table 2 does not reproduce, B1's denominator is not Table 2's.

2. **The alert rule reproduces from the cached scores.** Table 2's numbers are recomputed
   here from ``predictions_raw.parquet`` with the window and alarm convention B1 uses,
   and compared with the source file.  This is the check that B1's reimplementation of
   "first crossing" agrees with the published one, rather than assuming it.

3. **A6's transformer path numbers are unchanged.** The motivating contradiction B1-B4
   exist to resolve is stated in terms of specific A6 values; if those have moved, the
   question has changed.

Nothing here writes a result.  It writes a pass/fail table and exits nonzero on any
disagreement.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib_b import (  # noqa: E402
    ALERT_WINDOW_MIN,
    FAMILY_ORDER,
    HEADLINE_TARGET,
    REPO,
    THRESHOLD_CSV,
    alert_window,
    df_to_md,
    load_scored,
    thresholds,
    write_manifest,
)

OUT = Path(__file__).resolve().parent / "step0_repro"

#: Table 2 of the manuscript, held-out MOVER (EPIC), 80% validation sensitivity target.
#: Transcribed from the companion manuscript, not from a summary.
PUBLISHED_TABLE_2 = {
    "transformer": {"sensitivity": 0.78, "specificity": 0.41, "lead": 24.0, "ppv": 0.625, "nne": 1.60},
    "xgb": {"sensitivity": 0.81, "specificity": 0.61, "lead": 21.0, "ppv": 0.725, "nne": 1.38},
    "rf": {"sensitivity": 0.83, "specificity": 0.56, "lead": 22.0, "ppv": 0.703, "nne": 1.42},
    "lstm": {"sensitivity": 0.81, "specificity": 0.47, "lead": 23.0, "ppv": 0.661, "nne": 1.51},
    "logreg": {"sensitivity": 0.84, "specificity": 0.52, "lead": 23.0, "ppv": 0.688, "nne": 1.45},
}

#: A6, transformer, event group, spanning sample.  ``a6_window_trend.csv``.
PUBLISHED_A6 = {
    ("epic_test", 5): {"delta": 0.046470, "directedness": 0.025202, "max_up_share": 0.487877},
    ("epic_test", 10): {"delta": -0.000030, "directedness": -0.000052, "max_up_share": 0.510001},
    ("vitaldb", 5): {"delta": 0.012713, "directedness": 0.020802, "max_up_share": 0.489521},
    ("vitaldb", 10): {"delta": -0.000018, "directedness": -0.000018, "max_up_share": 0.525051},
}


def _check(rows: list[dict], name: str, observed: float, expected: float, tol: float) -> None:
    ok = np.isfinite(observed) and abs(observed - expected) <= tol
    rows.append(
        {
            "check": name,
            "expected": expected,
            "observed": observed,
            "tolerance": tol,
            "status": "pass" if ok else "FAIL",
        }
    )


def _source_table_2(rows: list[dict]) -> None:
    frame = pd.read_csv(THRESHOLD_CSV)
    op = frame[
        (frame["record"] == "operating_point")
        & (frame["cohort"] == "epic_test")
        & (frame["target_sensitivity"] == HEADLINE_TARGET)
    ].set_index("family")
    for family, want in PUBLISHED_TABLE_2.items():
        got = op.loc[family]
        # Table 2 prints sensitivity/specificity to 2 dp and PPV/NNE to 3/2 dp.
        _check(rows, f"table2/{family}/sensitivity", float(got["sensitivity"]), want["sensitivity"], 0.005)
        _check(rows, f"table2/{family}/specificity", float(got["specificity"]), want["specificity"], 0.005)
        _check(rows, f"table2/{family}/ppv", float(got["ppv"]), want["ppv"], 0.0005)
        _check(rows, f"table2/{family}/nne", float(got["nne"]), want["nne"], 0.005)
        _check(
            rows,
            f"table2/{family}/median_lead_min",
            float(got["median_first_alarm_lead_min"]),
            want["lead"],
            0.0,
        )


def _recomputed_alert_rule(rows: list[dict]) -> None:
    """B1's own implementation of the alarm rule, against the published operating point."""
    threshold = thresholds().set_index(["family", "target_sensitivity"])["threshold"]
    source = pd.read_csv(THRESHOLD_CSV)
    source = source[
        (source["record"] == "operating_point")
        & (source["cohort"] == "epic_test")
        & (source["target_sensitivity"] == HEADLINE_TARGET)
    ].set_index("family")
    for family in FAMILY_ORDER:
        cut = float(threshold.loc[(family, HEADLINE_TARGET)])
        window = alert_window(load_scored(family, "epic_test"))
        peak = window.groupby("case_id").agg(label=("label", "first"), peak=("score", "max"))
        alarm = peak["peak"] >= cut
        n_pos = int((peak["label"] == 1).sum())
        n_neg = int((peak["label"] == 0).sum())
        tp = int((alarm & (peak["label"] == 1)).sum())
        fp = int((alarm & (peak["label"] == 0)).sum())
        crossings = window[(window["label"] == 1) & (window["score"] >= cut)]
        # Chronological first crossing == largest t_to_event among crossings.
        lead = crossings.groupby("case_id")["t_to_event"].max()
        _check(rows, f"recompute/{family}/sensitivity", tp / n_pos, float(source.loc[family, "sensitivity"]), 1e-9)
        _check(rows, f"recompute/{family}/specificity", 1 - fp / n_neg, float(source.loc[family, "specificity"]), 1e-9)
        _check(
            rows,
            f"recompute/{family}/median_lead_min",
            float(lead.median()),
            float(source.loc[family, "median_first_alarm_lead_min"]),
            0.0,
        )


def _a6_unchanged(rows: list[dict]) -> None:
    path = (
        REPO
        / "analysis"
        / "patient_trajectory_2026"
        / "a6_window_trend"
        / "a6_window_trend.csv"
    )
    a6 = pd.read_csv(path)
    a6 = a6[
        (a6["family"] == "transformer")
        & (a6["group"] == "event")
        & (a6["window_start_min"] == 60)
    ]
    for (cohort, endpoint), want in PUBLISHED_A6.items():
        cell = a6[(a6["cohort"] == cohort) & (a6["endpoint_min"] == endpoint)]
        if len(cell) != 1:
            rows.append(
                {
                    "check": f"a6/{cohort}/60-{endpoint}",
                    "expected": np.nan,
                    "observed": np.nan,
                    "tolerance": np.nan,
                    "status": "FAIL",
                }
            )
            continue
        row = cell.iloc[0]
        for key, column in (
            ("delta", "delta_median"),
            ("directedness", "directedness_median"),
            ("max_up_share", "max_up_share_median"),
        ):
            _check(rows, f"a6/{cohort}/60-{endpoint}/{key}", float(row[column]), want[key], 1e-6)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    _source_table_2(rows)
    _recomputed_alert_rule(rows)
    _a6_unchanged(rows)
    result = pd.DataFrame(rows)
    result.to_csv(OUT / "step0_repro.csv", index=False)
    (OUT / "step0_repro.md").write_text(
        "# B step 0 - reproduction gate\n\n"
        f"Alert window `0 < t_to_event <= {ALERT_WINDOW_MIN}`, alarm rule `score >= threshold`, "
        "thresholds read from `validation_calibration_and_thresholds.csv` and not reselected.\n\n"
        + df_to_md(result)
        + "\n",
        encoding="utf-8",
    )
    write_manifest(
        OUT,
        "step0_repro",
        [],
        extra={
            "alert_window_min": ALERT_WINDOW_MIN,
            "headline_target_sensitivity": HEADLINE_TARGET,
            "threshold_source": str(THRESHOLD_CSV.relative_to(REPO)),
            "n_checks": int(len(result)),
        },
    )
    failures = result[result["status"] != "pass"]
    print(f"{len(result) - len(failures)}/{len(result)} checks passed")
    if len(failures):
        print(failures.to_string(index=False))
        sys.exit("reproduction gate failed; B1-B4 not run")


if __name__ == "__main__":
    main()
