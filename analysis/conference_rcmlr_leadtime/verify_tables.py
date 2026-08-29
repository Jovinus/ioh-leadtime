#!/usr/bin/env python3
"""Recompute every cell of the paper's four tables from its source CSV.

``verify_numbers.py`` asserts the headline numbers in the prose, and it reaches a handful of
Table 1 cells, but the four tables carry roughly 340 numbers between them and most were not
checked by anything. A wrong cell in an appendix table is exactly the kind of error that
survives proofreading, so this walks the tables instead of the prose: it parses each
markdown table out of ``PAPER.md``, looks the row up in the CSV its caption names, and
compares every printed value against the source at the precision the table prints.

The two gates are deliberately separate. This one would pass on a paper whose prose
contradicted its tables; that one would pass on a paper whose tables were wrong.

Run:
    conda run -n torch python verify_tables.py

Exit status is non-zero if any cell disagrees.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
NULL = REPO / "analysis" / "lead_time_null_2026"
ORIGIN = REPO / "analysis" / "lead_time_origin_2026"
PAPER = (HERE / "PAPER.md").read_text()

#: Table label -> the family key the source CSVs use. The tables print display names.
FAMILY = {
    "ITE Transformer": "transformer",
    "Transformer": "transformer",
    "LSTM": "lstm",
    "XGBoost": "xgb",
    "Random forest": "rf",
    "Logistic regression": "logreg",
    "Logistic reg.": "logreg",
}
COHORT = {
    "MOVER (EPIC) test": "epic_test",
    "MOVER (EPIC)": "epic_test",
    "VitalDB": "vitaldb",
    "MOVER (SIS)": "mover",
    "MOVER SIS": "mover",
}

MISMATCHES: list[str] = []
CHECKED = 0


def cell(tag: str, printed: str, expected, tol: float = 1e-9) -> None:
    """Compare one printed cell against the source value."""
    global CHECKED
    CHECKED += 1
    try:
        ok = abs(float(printed.replace(",", "")) - float(expected)) <= tol + 1e-9
    except ValueError:
        ok = printed == str(expected)
    if not ok:
        MISMATCHES.append(f"{tag}: table {printed!r} vs source {expected!r}")


def parse(label: str) -> list[list[str]]:
    """The data rows of the markdown table that follows a ``**Label | ...**`` caption."""
    start = PAPER.index(f"**{label} |")
    rows: list[list[str]] = []
    for line in PAPER[PAPER.index("\n|", start):].splitlines():
        if not line.startswith("|"):
            if rows:
                break
            continue
        rows.append([c.strip() for c in line.strip().strip("|").split("|")])
    if len(rows) < 3:
        raise SystemExit(f"no table found after the caption for {label}")
    return rows[2:]  # rows[0] is the header, rows[1] the alignment rule


def family_of(text: str) -> str:
    return FAMILY[re.sub(r"\s+", " ", text).strip()]


def numbers(text: str) -> list[str]:
    return re.findall(r"-?\d+\.?\d*", text)


def table_a9() -> None:
    """Table A9: transformer quintiles, three cohorts, from n3_strata.csv.

    This was main text Table 1 until the operating-point table took that number, and Table 1 is
    now the Section 1 reader-facing table; the checks are
    unchanged apart from the label.
    """
    strata = pd.read_csv(NULL / "n3_stratified" / "n3_strata.csv")
    cohort = None
    for row in parse("Table A9"):
        if row[0]:
            cohort = COHORT[row[0]]
        stratum = int(row[1])
        src = strata[
            (strata.family == "transformer")
            & (strata.cohort == cohort)
            & (strata.stratum == stratum)
        ]
        if len(src) != 1:
            raise SystemExit(f"n3_strata has {len(src)} rows for {cohort} Q{stratum}")
        s = src.iloc[0]
        tag = f"Table A9 {cohort} Q{stratum}"
        cell(f"{tag} n", row[2], s.n_cases)
        cell(f"{tag} window", row[3], round(s.window_median))
        lead, interval = row[4].split("[")
        cell(f"{tag} lead", lead.strip(), round(s.lead_median))
        lo, hi = numbers(interval)
        cell(f"{tag} lead lo", lo, round(s.lead_ci_lo))
        cell(f"{tag} lead hi", hi, round(s.lead_ci_hi))
        cell(f"{tag} ratio", row[5].split("[")[0].strip(), round(s.ratio_median, 2), 0.005)


def table_a1() -> None:
    """Table A1: all fifteen cells, from n3_summary.csv."""
    summary = pd.read_csv(NULL / "n3_stratified" / "n3_summary.csv")
    family = cohort = None
    for row in parse("Table A1"):
        if row[0]:
            family = family_of(row[0])
        if row[1]:
            cohort = COHORT[row[1]]
        src = summary[(summary.family == family) & (summary.cohort == cohort)]
        if len(src) != 1:
            raise SystemExit(f"n3_summary has {len(src)} rows for {family}/{cohort}")
        s = src.iloc[0]
        tag = f"Table A1 {family}/{cohort}"
        cell(f"{tag} bands", row[2], s.n_bands)
        window, lead = numbers(row[3]), numbers(row[4])
        cell(f"{tag} window Q1", window[0], round(s.window_median_lowest_band))
        cell(f"{tag} window Qlast", window[1], round(s.window_median_highest_band))
        cell(f"{tag} lead Q1", lead[0], round(s.lead_median_lowest_band))
        cell(f"{tag} lead Qlast", lead[1], round(s.lead_median_highest_band))
        gradient = numbers(row[5])
        cell(f"{tag} gradient", gradient[0], round(s.lead_gradient_min))
        cell(f"{tag} gradient lo", gradient[1], round(s.lead_gradient_ci_lo))
        cell(f"{tag} gradient hi", gradient[2], round(s.lead_gradient_ci_hi))
        per = numbers(row[6])
        cell(f"{tag} per minute", per[0], round(s.lead_per_window_minute, 2), 0.005)
        cell(f"{tag} per minute lo", per[1], round(s.lead_per_window_ci_lo, 2), 0.005)
        cell(f"{tag} per minute hi", per[2], round(s.lead_per_window_ci_hi, 2), 0.005)


def table_a2() -> None:
    """Table A2: both nulls, all fifteen cells, from the N1 and N2 CSVs."""
    n1 = pd.read_csv(NULL / "n1_uniform_placement" / "n1_uniform_placement.csv")
    n2 = pd.read_csv(NULL / "n2_score_shuffle" / "n2_score_shuffle.csv")
    for row in parse("Table A2"):
        family, cohort = family_of(row[0]), COHORT[row[1]]
        uniform = n1[(n1.family == family) & (n1.cohort == cohort)].iloc[0]
        pair = n2[(n2.family == family) & (n2.cohort == cohort)]
        hold = pair[pair.variant == "hold"].iloc[0]
        matched = pair[pair.variant != "hold"].iloc[0]
        tag = f"Table A2 {family}/{cohort}"
        cell(f"{tag} observed ratio", row[2], round(uniform.observed_ratio_median, 3), 5e-4)
        cell(f"{tag} observed rho", row[6], round(hold.observed_spearman, 3), 5e-4)
        for column, source, mean, lo, hi in (
            (3, uniform, "null_ratio_mean", "null_ratio_ci_lo", "null_ratio_ci_hi"),
            (4, hold, "null_ratio_mean", "null_ratio_ci_lo", "null_ratio_ci_hi"),
            (5, matched, "null_ratio_mean", "null_ratio_ci_lo", "null_ratio_ci_hi"),
            (7, hold, "null_spearman_mean", "null_spearman_ci_lo", "null_spearman_ci_hi"),
            (8, matched, "null_spearman_mean", "null_spearman_ci_lo", "null_spearman_ci_hi"),
        ):
            printed = numbers(row[column])
            cell(f"{tag} c{column} mean", printed[0], round(source[mean], 3), 5e-4)
            cell(f"{tag} c{column} lo", printed[1], round(source[lo], 3), 5e-4)
            cell(f"{tag} c{column} hi", printed[2], round(source[hi], 3), 5e-4)


def table_a3() -> None:
    """Table A3: path decomposition over 60 to 5 minutes, from b3_comparison.csv."""
    b3 = pd.read_csv(ORIGIN / "b3_cross_family_path" / "b3_comparison.csv")
    b3 = b3[b3.endpoint_min == 5]
    cohort = None
    for row in parse("Table A3"):
        if row[0]:
            cohort = COHORT[row[0]]
        family = family_of(row[1])
        src = b3[(b3.family == family) & (b3.cohort == cohort)]
        if len(src) != 1:
            raise SystemExit(f"b3_comparison has {len(src)} rows for {family}/{cohort}")
        s = src.iloc[0]
        tag = f"Table A3 {family}/{cohort}"
        cell(f"{tag} episodes", row[2], s.n_episodes_spanning)
        printed = numbers(row[3])
        cell(f"{tag} directedness", printed[0], round(s.directedness_median, 3), 5e-4)
        cell(f"{tag} lo", printed[1], round(s.directedness_median_ci_lo, 3), 5e-4)
        cell(f"{tag} hi", printed[2], round(s.directedness_median_ci_hi, 3), 5e-4)
        cell(f"{tag} path per net", row[4], round(s.path_per_net, 1), 0.05)


def _operating() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """The three CSVs behind the operating-point tables, at the transported operating point."""
    sup = pd.read_csv(ORIGIN / "b1b_suppression" / "b1b_suppression.csv")
    sup = sup[sup.suppress_min == 0]
    mech = pd.read_csv(ORIGIN / "b1b_suppression" / "b1b_lead_vs_observation.csv")
    n5 = pd.read_csv(NULL / "n5_time_to_alert" / "n5_time_to_alert.csv")
    return sup, mech, n5


def _row_of(frame: pd.DataFrame, family: str, cohort: str, name: str) -> pd.Series:
    src = frame[(frame.family == family) & (frame.cohort == cohort)]
    if len(src) != 1:
        raise SystemExit(f"{name} has {len(src)} rows for {family}/{cohort}")
    return src.iloc[0]


def table_a4() -> None:
    """Table A4: the same operating point for all fifteen cells, with intervals."""
    sup, mech, _ = _operating()
    for row in parse("Table A4"):
        family, cohort = family_of(row[0]), COHORT[row[1]]
        r = _row_of(sup, family, cohort, "b1b_suppression")
        q = _row_of(mech, family, cohort, "b1b_lead_vs_observation")
        tag = f"Table A4 {family}/{cohort}"
        for column, value, lo, hi, digits in (
            (2, r.sensitivity, r.sensitivity_ci_lo, r.sensitivity_ci_hi, 3),
            (3, r.specificity, r.specificity_ci_lo, r.specificity_ci_hi, 3),
            (4, r.ppv, r.ppv_ci_lo, r.ppv_ci_hi, 3),
            (5, r.nne, r.nne_ci_lo, r.nne_ci_hi, 2),
            (6, q.median_above_fraction_events, q.median_above_fraction_events_ci_lo,
             q.median_above_fraction_events_ci_hi, 3),
        ):
            printed = numbers(row[column])
            tolerance = 0.5 * 10 ** -digits
            cell(f"{tag} c{column}", printed[0], round(value, digits), tolerance)
            cell(f"{tag} c{column} lo", printed[1], round(lo, digits), tolerance)
            cell(f"{tag} c{column} hi", printed[2], round(hi, digits), tolerance)
        printed = numbers(row[7])
        cell(f"{tag} lead", printed[0], round(r.lead_median))
        cell(f"{tag} lead lo", printed[1], round(r.lead_median_ci_lo))
        cell(f"{tag} lead hi", printed[2], round(r.lead_median_ci_hi))


def table_a5() -> None:
    """Table A5: detection rate by band, from n4_band_detection.csv."""
    bands = pd.read_csv(NULL / "n4_band_detection" / "n4_band_detection.csv")
    family = cohort = None
    for row in parse("Table A5"):
        if row[0]:
            family = family_of(row[0])
        if row[1]:
            cohort = COHORT[row[1]]
        stratum = int(row[2])
        src = bands[(bands.family == family) & (bands.cohort == cohort)
                    & (bands.stratum == stratum)]
        if len(src) != 1:
            raise SystemExit(f"n4_band_detection has {len(src)} rows for {family}/{cohort} b{stratum}")
        s = src.iloc[0]
        tag = f"Table A5 {family}/{cohort} b{stratum}"
        cell(f"{tag} events", row[3], s.n_event_cases)
        cell(f"{tag} detected", row[4], s.n_detected)
        cell(f"{tag} window", row[5], round(s.window_median))
        printed = numbers(row[6])
        cell(f"{tag} rate", printed[0], round(s.detection_rate, 3), 5e-4)
        cell(f"{tag} rate lo", printed[1], round(s.detection_ci_lo, 3), 5e-4)
        cell(f"{tag} rate hi", printed[2], round(s.detection_ci_hi, 3), 5e-4)
        printed = numbers(row[7])
        cell(f"{tag} lead", printed[0], round(s.lead_median))


def table_a6() -> None:
    """Table A6: fixed-horizon detection at all seven horizons, from n5_fixed_horizon.csv."""
    horizons = pd.read_csv(NULL / "n5_time_to_alert" / "n5_fixed_horizon.csv")
    for row in parse("Table A6"):
        family, cohort = family_of(row[0]), COHORT[row[1]]
        cellrows = horizons[(horizons.family == family) & (horizons.cohort == cohort)]
        tag = f"Table A6 {family}/{cohort}"
        for offset, horizon in enumerate((5, 10, 15, 20, 30, 45, 60)):
            src = cellrows[cellrows.horizon_min == horizon]
            if len(src) != 1:
                raise SystemExit(f"n5_fixed_horizon missing {family}/{cohort} at {horizon}")
            cell(f"{tag} {horizon}min", row[2 + offset],
                 round(src.iloc[0].fixed_horizon_detection, 3), 5e-4)
        printed = numbers(row[9])
        first = cellrows[cellrows.horizon_min == 5].iloc[0]
        last = cellrows[cellrows.horizon_min == 60].iloc[0]
        cell(f"{tag} n first", printed[0], first.n_observed_at_least_horizon)
        cell(f"{tag} n last", printed[1], last.n_observed_at_least_horizon)


def table_a7() -> None:
    """Table A7: the full alert window as a constant, from n5_time_to_alert.csv."""
    _, _, n5 = _operating()
    for row in parse("Table A7"):
        family, cohort = family_of(row[0]), COHORT[row[1]]
        s = _row_of(n5, family, cohort, "n5_time_to_alert")
        tag = f"Table A7 {family}/{cohort}"
        cell(f"{tag} n", row[2], s.n_fully_observed)
        cell(f"{tag} detected", row[3], round(s.detection_fully_observed, 3), 5e-4)
        printed = numbers(row[4])
        cell(f"{tag} lead", printed[0], round(s.lead_median_fully_observed))
        cell(f"{tag} lead lo", printed[1], round(s.lead_median_fully_observed_ci_lo))
        cell(f"{tag} lead hi", printed[2], round(s.lead_median_fully_observed_ci_hi))
        printed = numbers(row[5])
        # the table prints the alerted share, which is one minus the KM survival, so the
        # interval bounds swap
        cell(f"{tag} alerted", printed[0], round(1 - s.km_unalerted_by_min1, 3), 5e-4)
        cell(f"{tag} alerted lo", printed[1], round(1 - s.km_unalerted_by_min1_ci_hi, 3), 5e-4)
        cell(f"{tag} alerted hi", printed[2], round(1 - s.km_unalerted_by_min1_ci_lo, 3), 5e-4)


def table_a10() -> None:
    """Table A10: cohort composition and the control side."""
    sup, mech, n5 = _operating()
    for row in parse("Table A10"):
        family, cohort = family_of(row[0]), COHORT[row[1]]
        r = _row_of(sup, family, cohort, "b1b_suppression")
        q = _row_of(mech, family, cohort, "b1b_lead_vs_observation")
        k = _row_of(n5, family, cohort, "n5_time_to_alert")
        prevalence = r.n_event / (r.n_event + r.n_control)
        tag = f"Table A10 {family}/{cohort}"
        cell(f"{tag} events", row[2], r.n_event)
        cell(f"{tag} controls", row[3], r.n_control)
        cell(f"{tag} prevalence", row[4], round(prevalence, 3), 5e-4)
        cell(f"{tag} lift", row[5], round(r.ppv - prevalence, 3), 5e-4)
        printed = numbers(row[6])
        cell(f"{tag} burden", printed[0], round(q.median_above_fraction_controls, 3), 5e-4)
        cell(f"{tag} burden lo", printed[1],
             round(q.median_above_fraction_controls_ci_lo, 3), 5e-4)
        cell(f"{tag} burden hi", printed[2],
             round(q.median_above_fraction_controls_ci_hi, 3), 5e-4)
        printed = numbers(row[7])
        cell(f"{tag} alerted", printed[0], round(1 - k.km_unalerted_by_min1, 3), 5e-4)


def main() -> int:
    table_a1()
    table_a2()
    table_a3()
    table_a4()
    table_a5()
    table_a6()
    table_a7()
    table_a9()
    table_a10()
    if MISMATCHES:
        print(f"{CHECKED - len(MISMATCHES)}/{CHECKED} cells agree, {len(MISMATCHES)} FAILED\n")
        for line in MISMATCHES:
            print(f"  {line}")
        return 1
    print(f"{CHECKED}/{CHECKED} table cells agree with their source CSVs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
