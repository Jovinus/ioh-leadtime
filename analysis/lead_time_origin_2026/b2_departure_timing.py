"""B2 - inside an episode, does the score depart from its own baseline before MAP does?

This is a timing question and nothing more. The outcome is defined on MAP and MAP is an
input channel, so a score that moves before MAP does is not evidence that the model
anticipates physiology -- it is evidence about the order of two departures under one stated
rule. That is the only claim the module supports and the only one its report makes.

Pre-specified departure rule, identical for both series:

* the episode's **baseline** is the median over its first 10 eligible pre-onset minutes;
* its **robust scale** is 1.4826 x the median absolute deviation over the same minutes,
  falling back to the MAD over the whole pre-onset record when the baseline MAD is zero
  (a coarse score can be constant for ten minutes), and the episode is dropped if both are
  zero, with the count reported;
* **departure** is the first minute that begins a run of at least 3 consecutive observed
  minutes exceeding the baseline by more than 1.5 robust scale units in the deteriorating
  direction -- score upward, MAP downward.

The reported quantity is ``MAP departure minus score departure`` in minutes, so a positive
value means the score departed first. Episodes in which neither series departs are episodes
in which the model never signalled, and they are counted rather than dropped: the four-way
breakdown (neither / score only / MAP only / both) is part of the result.

Transformer and XGBoost only. This is a mechanism question, so the tiering rule gives it two
families rather than five. Three sensitivity settings are reported beside the primary rule:
a 2.0 robust-scale threshold, a 5-minute run requirement, and a search window capped at the
60 minutes the published alert analysis uses -- the last because "the first 10 eligible
minutes" of a three-hour record is a very early baseline, and that choice is a convention.

Post-hoc on cached per-minute scores and the source per-minute MAP series; no retraining.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib_b import (  # noqa: E402
    COHORT_LABELS,
    COHORT_ORDER,
    FAMILY_LABELS,
    N_BOOTSTRAP_PATIENT,
    REPO,
    bootstrap_p_two_sided,
    case_manifest,
    cluster_codes,
    df_to_md,
    load_scored,
    percentile_ci,
    seed_for,
    weight_matrix,
    weighted_fraction,
    weighted_median,
    write_manifest,
)

OUT = Path(__file__).resolve().parent / "b2_departure_timing"

FAMILIES = ("transformer", "xgb")
MIN_PRE_ONSET_MIN = 30
BASELINE_MIN = 10
MAD_TO_SD = 1.4826
#: The published 80%-sensitivity transformer threshold, used only as a fixed yardstick for
#: "was the baseline already at alerting level".  Nothing is reselected against it.
SATURATION_REFERENCE = 0.893518


@dataclass(frozen=True)
class Rule:
    name: str
    n_scale: float
    run_length: int
    cap_min: float | None


RULES = (
    Rule("primary", 1.5, 3, None),
    Rule("scale_2.0", 2.0, 3, None),
    Rule("run_5", 1.5, 5, None),
    Rule("cap_60", 1.5, 3, 60.0),
)


def _departure(values: np.ndarray, minutes: np.ndarray, rule: Rule, sign: float) -> tuple[float, bool, float, float]:
    """First minute beginning a qualifying run, as ``t_to_event``.

    ``values`` and ``minutes`` run chronologically (``minutes`` = ``t_to_event``, so it
    descends).  ``sign`` is +1 when deterioration is upward (score) and -1 when it is
    downward (MAP), which lets one implementation serve both series and makes the rule
    provably identical for the two.
    """
    oriented = sign * values
    baseline_slice = oriented[:BASELINE_MIN]
    baseline = float(np.median(baseline_slice))
    scale = MAD_TO_SD * float(np.median(np.abs(baseline_slice - baseline)))
    if scale == 0:
        whole = MAD_TO_SD * float(np.median(np.abs(oriented - np.median(oriented))))
        scale = whole
    if scale == 0:
        return np.nan, False, 0.0, sign * baseline
    exceeds = oriented > baseline + rule.n_scale * scale
    # Search starts after the baseline window; the baseline cannot depart from itself.
    for index in range(BASELINE_MIN, len(oriented) - rule.run_length + 1):
        if exceeds[index : index + rule.run_length].all():
            return float(minutes[index]), True, scale, sign * baseline
    return np.nan, True, scale, sign * baseline


def _episode_series(family: str, cohort: str) -> pd.DataFrame:
    """One row per eligible event episode: the two departure minutes under every rule."""
    path = {
        "epic_test": REPO / "outputs/runs/gap0/predictions/test/predictions_raw.parquet",
        "vitaldb": REPO / "outputs/runs/gap0/external_vitaldb/predictions_raw.parquet",
        "mover": REPO / "outputs/runs/gap0/external_mover/predictions_raw.parquet",
    }
    run = {"transformer": "gap0", "xgb": "xgb_gap0"}[family]
    scored = pd.read_parquet(
        str(path[cohort]).replace("gap0", run, 1) if family != "transformer" else path[cohort],
        columns=["case_id", "t_min", "t_to_event", "score", "label"],
    )
    scored["case_id"] = scored["case_id"].astype(str)
    scored = scored[(scored["label"] == 1) & (scored["t_to_event"] > 0) & np.isfinite(scored["score"])]

    clusters = load_scored(family, cohort)[["case_id", "cluster_id", "cluster_level"]].drop_duplicates()
    manifest = case_manifest(cohort).set_index("case_id")

    rows: list[dict] = []
    gaps: list[int] = []
    for case_id, group in scored.groupby("case_id", sort=False):
        ordered = group.sort_values("t_min")
        if len(ordered) < MIN_PRE_ONSET_MIN:
            rows.append({"case_id": case_id, "eligible": False, "n_pre_onset_min": len(ordered)})
            continue
        parquet = manifest.loc[case_id, "parquet_path"]
        series = pd.read_parquet(parquet, columns=["t_min", "MAP"])
        merged = ordered.merge(series, on="t_min", how="left")
        merged = merged[np.isfinite(merged["MAP"])]
        if len(merged) < MIN_PRE_ONSET_MIN:
            rows.append({"case_id": case_id, "eligible": False, "n_pre_onset_min": len(merged),
                         "reason": "too few minutes with both score and MAP"})
            continue
        gaps.extend(np.diff(merged["t_min"].to_numpy()).tolist())
        record = {
            "case_id": case_id,
            "eligible": True,
            "n_pre_onset_min": int(len(merged)),
            "observable_min": float(manifest.loc[case_id, "observable_min"]),
        }
        for rule in RULES:
            frame = merged if rule.cap_min is None else merged[merged["t_to_event"] <= rule.cap_min]
            if len(frame) < BASELINE_MIN + rule.run_length:
                record[f"score_departure_{rule.name}"] = np.nan
                record[f"map_departure_{rule.name}"] = np.nan
                record[f"computable_{rule.name}"] = False
                continue
            minutes = frame["t_to_event"].to_numpy(float)
            score_at, score_ok, score_scale, score_base = _departure(frame["score"].to_numpy(float), minutes, rule, +1.0)
            map_at, map_ok, map_scale, map_base = _departure(frame["MAP"].to_numpy(float), minutes, rule, -1.0)
            record[f"score_departure_{rule.name}"] = score_at
            record[f"map_departure_{rule.name}"] = map_at
            record[f"computable_{rule.name}"] = bool(score_ok and map_ok)
            record[f"score_scale_{rule.name}"] = score_scale
            record[f"map_scale_{rule.name}"] = map_scale
            # The rule normalises each series by its own volatility, so a series that
            # wanders needs a proportionally larger excursion to be called a departure.
            # Recording the bar in the series' own units is what makes "the score never
            # departed" distinguishable from "the bar was higher for the score".
            record[f"score_bar_{rule.name}"] = rule.n_scale * score_scale
            record[f"map_bar_{rule.name}"] = rule.n_scale * map_scale
            record[f"score_baseline_{rule.name}"] = score_base
            record[f"map_baseline_{rule.name}"] = map_base
            # A score whose baseline already sits at the top of its range cannot depart
            # upward at all, however low the bar.  Recording the headroom is what tells a
            # "flat and high" episode apart from a "flat and low" one.
            record[f"score_headroom_{rule.name}"] = float(
                frame["score"].max() - score_base
            )
            record[f"score_baseline_above_thr_{rule.name}"] = bool(score_base >= SATURATION_REFERENCE)
        rows.append(record)

    frame = pd.DataFrame(rows).merge(clusters, on="case_id", how="left")
    frame["family"] = family
    frame["cohort"] = cohort
    if gaps:
        median_gap = float(np.median(gaps))
        if median_gap != 1.0:
            raise AssertionError(
                f"{family}/{cohort}: median inter-sample gap is {median_gap}, so a run of "
                "consecutive observed rows is not a run of consecutive minutes"
            )
    return frame


def _summarise(frame: pd.DataFrame, family: str, cohort: str) -> list[dict]:
    eligible = frame[frame["eligible"].fillna(False)].reset_index(drop=True)
    codes, n_clusters = cluster_codes(eligible)
    rng = np.random.default_rng(seed_for("b2", family, cohort))
    weights = weight_matrix(n_clusters, rng, N_BOOTSTRAP_PATIENT) if n_clusters else None

    out: list[dict] = []
    for rule in RULES:
        score_at = eligible[f"score_departure_{rule.name}"].to_numpy(float)
        map_at = eligible[f"map_departure_{rule.name}"].to_numpy(float)
        computable = eligible[f"computable_{rule.name}"].to_numpy(bool)
        score_dep = np.isfinite(score_at)
        map_dep = np.isfinite(map_at)
        both = score_dep & map_dep
        # t_to_event descends toward onset, so "MAP departure minus score departure" in
        # minutes-before-onset is score_at - map_at: positive when the score departed at a
        # larger t_to_event, i.e. earlier.
        difference = np.where(both, score_at - map_at, np.nan)

        row = {
            "family": family,
            "family_label": FAMILY_LABELS[family],
            "cohort": cohort,
            "cohort_label": COHORT_LABELS[cohort],
            "rule": rule.name,
            "n_scale": rule.n_scale,
            "run_length": rule.run_length,
            "cap_min": rule.cap_min if rule.cap_min is not None else np.nan,
            "score_scale_median": float(np.nanmedian(eligible.get(f"score_scale_{rule.name}", pd.Series([np.nan])))),
            "map_scale_median": float(np.nanmedian(eligible.get(f"map_scale_{rule.name}", pd.Series([np.nan])))),
            "score_bar_median": float(np.nanmedian(eligible.get(f"score_bar_{rule.name}", pd.Series([np.nan])))),
            "map_bar_median": float(np.nanmedian(eligible.get(f"map_bar_{rule.name}", pd.Series([np.nan])))),
            "score_baseline_median": float(np.nanmedian(eligible.get(f"score_baseline_{rule.name}", pd.Series([np.nan])))),
            "score_headroom_median": float(np.nanmedian(eligible.get(f"score_headroom_{rule.name}", pd.Series([np.nan])))),
            "prop_baseline_above_alert_threshold": float(
                pd.Series(eligible.get(f"score_baseline_above_thr_{rule.name}", pd.Series([np.nan]))).mean()
            ),
            "n_event_cases": int(len(frame)),
            "n_eligible": int(len(eligible)),
            "retention": float(len(eligible) / len(frame)) if len(frame) else np.nan,
            "n_computable": int(computable.sum()),
            "n_clusters": int(n_clusters),
            "n_neither": int((~score_dep & ~map_dep).sum()),
            "n_score_only": int((score_dep & ~map_dep).sum()),
            "n_map_only": int((~score_dep & map_dep).sum()),
            "n_both": int(both.sum()),
            "prop_neither": float((~score_dep & ~map_dep).mean()),
            "prop_score_only": float((score_dep & ~map_dep).mean()),
            "prop_map_only": float((~score_dep & map_dep).mean()),
            "prop_both": float(both.mean()),
            "n_difference": int(np.isfinite(difference).sum()),
        }
        finite = difference[np.isfinite(difference)]
        row["difference_median_min"] = float(np.median(finite)) if finite.size else np.nan
        row["difference_q25_min"] = float(np.percentile(finite, 25)) if finite.size else np.nan
        row["difference_q75_min"] = float(np.percentile(finite, 75)) if finite.size else np.nan
        row["prop_score_first"] = float((finite > 0).mean()) if finite.size else np.nan
        row["prop_simultaneous"] = float((finite == 0).mean()) if finite.size else np.nan

        if weights is not None and finite.size:
            positive = np.where(both, difference > 0, False)
            med = np.empty(N_BOOTSTRAP_PATIENT)
            pos = np.empty(N_BOOTSTRAP_PATIENT)
            for replicate in range(N_BOOTSTRAP_PATIENT):
                w = weights[replicate][codes]
                paired = np.where(both, w, 0)
                med[replicate] = weighted_median(difference, paired)
                pos[replicate] = weighted_fraction(positive, paired)
            row["difference_median_ci_lo"], row["difference_median_ci_hi"] = percentile_ci(med)
            row["prop_score_first_ci_lo"], row["prop_score_first_ci_hi"] = percentile_ci(pos)
            row["difference_median_p"] = bootstrap_p_two_sided(med)
            row["prop_score_first_vs_half_p"] = bootstrap_p_two_sided(pos - 0.5)
        out.append(row)
    return out


def run() -> dict[str, pd.DataFrame]:
    OUT.mkdir(parents=True, exist_ok=True)
    summaries: list[dict] = []
    episodes: list[pd.DataFrame] = []
    for family in FAMILIES:
        for cohort in COHORT_ORDER:
            frame = _episode_series(family, cohort)
            episodes.append(frame)
            summaries.extend(_summarise(frame, family, cohort))
            print(f"  b2 {family} / {cohort}: {int(frame['eligible'].fillna(False).sum())} eligible", flush=True)
    tables = {"summary": pd.DataFrame(summaries), "episodes": pd.concat(episodes, ignore_index=True)}
    tables["summary"].to_csv(OUT / "b2_summary.csv", index=False)
    tables["episodes"].to_csv(OUT / "b2_episodes.csv.gz", index=False, compression="gzip")
    _write_report(tables)
    write_manifest(
        OUT,
        "b2_departure_timing",
        [],
        extra={
            "families": list(FAMILIES),
            "tier": "two families; the claim concerns mechanism, not model ranking",
            "min_pre_onset_min": MIN_PRE_ONSET_MIN,
            "baseline_min": BASELINE_MIN,
            "rules": [
                {"name": r.name, "n_robust_scale": r.n_scale, "run_length_min": r.run_length,
                 "cap_min": r.cap_min}
                for r in RULES
            ],
            "robust_scale": "1.4826 x MAD over the baseline minutes, falling back to the whole record",
            "sign_convention": "deterioration is score upward and MAP downward",
            "reported_difference": "score departure minus MAP departure, in minutes before onset; positive means the score departed first",
            "permitted_claim": "temporal precedence under the stated rule; NOT anticipation of physiology",
            "n_bootstrap": N_BOOTSTRAP_PATIENT,
            "seed_base": seed_for("b2", "transformer", "epic_test"),
        },
    )
    return tables


def _write_report(tables: dict[str, pd.DataFrame]) -> None:
    summary = tables["summary"]
    primary = summary[summary["rule"] == "primary"]
    lines = [
        "# B2 - order of score departure and MAP departure inside an episode\n",
        "**What this can and cannot say.** The outcome is defined on MAP and MAP is a model "
        "input, so an earlier score departure is a statement about the order of two "
        "departures under one pre-specified rule. It is not evidence that the model "
        "anticipates physiology, and nothing below is written as if it were.\n",
        "Baseline is the median over an episode's first 10 eligible pre-onset minutes; "
        "departure is the first minute beginning a run of at least 3 consecutive minutes "
        "more than 1.5 robust scale units into the deteriorating direction. Positive "
        "difference means the score departed first.\n",
        "## 1. Retention and the four-way breakdown\n",
        df_to_md(
            primary[["cohort_label", "family_label", "n_event_cases", "n_eligible", "retention",
                     "n_neither", "n_score_only", "n_map_only", "n_both",
                     "prop_neither", "prop_score_only", "prop_map_only", "prop_both"]].round(4)
        ),
        "",
        "Episodes counted under `n_neither` and `n_map_only` are episodes in which the score "
        "never departed from its own baseline at all -- the model did not signal.\n",
        "The rule normalises each series by its own robust scale, so a volatile series has to travel further to be called departed. The median bar each series had to clear, in its own units, is reported here rather than left implicit -- a low `prop_both` for a volatile score is partly a property of the rule.\n",
        df_to_md(
            primary[["cohort_label", "family_label", "score_scale_median", "score_bar_median",
                     "map_scale_median", "map_bar_median", "score_baseline_median",
                     "score_headroom_median", "prop_baseline_above_alert_threshold"]].round(4)
        ),
        "",
        "## 2. MAP departure minus score departure, among episodes where both departed\n",
        df_to_md(
            pd.DataFrame(
                {
                    "Cohort": primary["cohort_label"],
                    "Model": primary["family_label"],
                    "n": primary["n_difference"],
                    "Median (IQR), min": [
                        f"{r.difference_median_min:+.0f} ({r.difference_q25_min:+.0f} to {r.difference_q75_min:+.0f})"
                        for r in primary.itertuples()
                    ],
                    "Median (95% CI)": [
                        f"{r.difference_median_min:+.0f} ({r.difference_median_ci_lo:+.0f} to {r.difference_median_ci_hi:+.0f})"
                        for r in primary.itertuples()
                    ],
                    "Score first (95% CI)": [
                        f"{r.prop_score_first:.1%} ({r.prop_score_first_ci_lo:.1%}–{r.prop_score_first_ci_hi:.1%})"
                        for r in primary.itertuples()
                    ],
                    "Simultaneous": primary["prop_simultaneous"].map("{:.1%}".format),
                    "P, share vs 0.5": primary["prop_score_first_vs_half_p"].map("{:.4f}".format),
                }
            )
        ),
        "",
        "## 3. Sensitivity to the rule\n",
        "`scale_2.0` raises the departure threshold, `run_5` lengthens the run requirement, "
        "and `cap_60` restricts the search to the published 60-minute alert window so the "
        "baseline is taken 60-51 minutes before onset instead of at the start of the record.\n",
        df_to_md(
            summary[["cohort_label", "family_label", "rule", "n_eligible", "n_difference",
                     "difference_median_min", "prop_score_first", "prop_both",
                     "prop_neither"]].round(4)
        ),
        "",
    ]
    (OUT / "b2_departure_timing.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    tables = run()
    primary = tables["summary"][tables["summary"]["rule"] == "primary"]
    print("\nScore-minus-MAP departure (minutes; positive = score first):")
    print(
        primary[["cohort", "family", "n_eligible", "n_difference", "difference_median_min",
                 "prop_score_first", "prop_both", "prop_neither", "prop_map_only"]]
        .round(3).to_string(index=False)
    )


if __name__ == "__main__":
    main()
