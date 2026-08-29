"""A6 - nested windows ending near onset: within-episode trend, ascent, and actual rise.

A1 asked whether a single five-minute step went up. A2 asked whether one truncated window
rescued the published tau. Neither answers the question a reader actually has: over the run
up to onset, **how much did the score move, and did the movement have a direction** -- and
does the answer depend on how far back you start looking.

So this sweeps the window start from 60 minutes down to 10 while holding the near end fixed,
and reports three things side by side for each window:

* **Kendall tau** median and IQR, the ordering question. Whether the score kept climbing.
* **Ascent fraction**, the same question reduced to its endpoints: did the near end sit above
  the far end at all.
* **Change in score**, the displacement question. How far it actually moved. Ordering and
  displacement come apart -- a previously published patient-level summary already shows the
  transformer ranking 5/5 on three ordering summaries and 2/5 on net change -- so reporting
  one without the other is how a trajectory gets described as flat when it moved, or as
  moving when it only wobbled upward.
* **How the movement was delivered.** The ascent fraction is closer to a volatility measure
  than a level measure: a window whose score rose a long way while only two of ten steps went
  up did not climb, it jumped. So the step decomposition is reported beside them -- the gross
  rise and gross fall separately, their sum as the path the score actually travelled, the net
  over that path as a directedness ratio, and the largest single step as a share of the gross
  rise. A high net with a low ascent fraction and a large single-step share is one or two
  jumps; the same net with a high ascent fraction is a climb. Those are different clinical
  objects and no one of these numbers separates them alone.

The last five minutes get their own quantity. A2 found that removing them lowers tau in all
15 cells, so they carry the rise; ``last5_share`` puts a number on it per episode -- the part
of the 60-to-5 change delivered between minute 10 and minute 5.

Three groups: all episodes, event episodes, and control episodes. Controls are anchored on
the sampled pseudo-onset already used throughout the paper, so "60 minutes before onset"
means "before the pseudo-onset" for them.

Two near ends, 5 and 10 minutes, because the last five minutes are exactly what A2 showed
carries the within-episode rise; ending at 10 shows what is left without them.

The window convention is A2's, ``endpoint < t_to_event <= start``, so the 30-to-5 window here
is numerically the same object as A2's truncated window. That is asserted rather than
assumed.

Post-hoc on cached scores; no retraining.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kendalltau

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib_pt import (  # noqa: E402
    COHORT_LABELS,
    COHORT_ORDER,
    FAMILY_LABELS,
    FAMILY_ORDER,
    MIN_POINTS,
    N_BOOTSTRAP_PATIENT,
    assign_bin,
    df_to_md,
    load_scored,
    percentile_ci,
    write_manifest,
)

OUT = Path(__file__).resolve().parent / "a6_window_trend"

# Near ends and window starts.  Starts are the published bin centres, so every window edge is
# a point at which the paper already reports a population AUROC.
BIN_STEP_MIN = 5
ENDPOINTS = (5, 10)
STARTS = (60, 55, 50, 45, 40, 35, 30, 25, 20, 15, 10)
GROUPS = ("all", "event", "control")
GROUP_LABELS = {"all": "All episodes", "event": "Event", "control": "Control"}

SEED_BASE = 20260706 + 80_000


def _decompose(values: np.ndarray) -> dict:
    """Split a window's movement into how far it went and how it got there.

    ``values`` runs far-from-onset to near, one entry per observed bin.  Net change alone
    cannot tell a steady climb from a single jump, and the ascent fraction alone cannot tell a
    small wobble upward from a large one, so both come out of here together with the largest
    single step.
    """
    steps = np.diff(values)
    up = steps[steps > 0]
    down = steps[steps < 0]
    gross_up = float(up.sum()) if up.size else 0.0
    gross_down = float(-down.sum()) if down.size else 0.0
    path = gross_up + gross_down
    net = float(values[-1] - values[0])
    return {
        "delta": net,
        "n_steps": int(steps.size),
        "n_up": int((steps > 0).sum()),
        "n_down": int((steps < 0).sum()),
        "step_ascent_fraction": float((steps > 0).mean()) if steps.size else np.nan,
        "gross_up": gross_up,
        "gross_down": gross_down,
        "path_length": path,
        # +1 monotone rise, 0 pure wobble, -1 monotone fall.  This is the volatility-versus-
        # trend split the net change hides.
        "directedness": float(net / path) if path > 0 else np.nan,
        "max_up_step": float(up.max()) if up.size else 0.0,
        # Near 1 means the whole rise arrived in one step.
        "max_up_share": float(up.max() / gross_up) if gross_up > 0 else np.nan,
    }


def _episode_windows(family: str, cohort: str) -> pd.DataFrame:
    """One row per episode per window: tau, displacement, and the step decomposition."""
    frame = load_scored(family, cohort)
    frame = frame[(frame["t_to_event"] > 0) & np.isfinite(frame["score"])]
    frame = frame.assign(bin_center=assign_bin(frame["t_to_event"]))

    rows: list[dict] = []
    for case_id, group in frame.groupby("case_id", sort=False):
        ordered = group.sort_values("t_to_event")
        minutes = ordered["t_to_event"].to_numpy(float)
        score = ordered["score"].to_numpy(float)
        identity = {
            "case_id": case_id,
            "cluster_id": str(ordered["cluster_id"].iloc[0]),
            "cluster_level": str(ordered["cluster_level"].iloc[0]),
            "label": int(ordered["label"].iloc[0]),
        }
        # An episode's value for a 2-minute bin is the mean of the minutes inside it, exactly
        # as A1 defines it.
        binned = ordered[ordered["bin_center"].notna()]
        bin_score = binned.groupby("bin_center", sort=True)["score"].mean().to_dict()

        for endpoint in ENDPOINTS:
            # Minutes ascend, so one searchsorted per endpoint fixes the lower cut and every
            # window start is a contiguous slice above it.
            low = np.searchsorted(minutes, endpoint, side="right")
            for start in STARTS:
                if start <= endpoint:
                    continue
                record = dict(identity, endpoint_min=endpoint, window_start_min=start)

                high = np.searchsorted(minutes, start, side="right")
                window_minutes = minutes[low:high]
                if len(window_minutes) >= MIN_POINTS:
                    statistic = kendalltau(-window_minutes, score[low:high]).statistic
                    record["tau"] = float(statistic) if np.isfinite(statistic) else np.nan
                    record["n_points"] = int(len(window_minutes))
                    # The window is a cap on tau, not the span it is measured over: an episode
                    # observed only from minute 20 gives the same tau at "60-5" as at "30-5".
                    # Record what was actually spanned so the distinction is checkable.
                    record["realised_span_min"] = float(
                        window_minutes.max() - window_minutes.min()
                    )
                else:
                    record["tau"] = np.nan
                    record["n_points"] = int(len(window_minutes))
                    record["realised_span_min"] = np.nan

                # Displacement needs both edges; the bins between them are used where observed.
                edges = [
                    bin_score[centre]
                    for centre in range(start, endpoint - 1, -BIN_STEP_MIN)
                    if centre in bin_score
                ]
                has_edges = (start in bin_score) and (endpoint in bin_score)
                if has_edges and len(edges) >= 2:
                    record.update(_decompose(np.asarray(edges, float)))
                    record["score_at_start"] = bin_score[start]
                    record["score_at_endpoint"] = bin_score[endpoint]
                    # tau on the episodes that actually reach the window start, so that every
                    # column of a table row is on one sample.  `tau` keeps the capped
                    # convention because that is the object A2 published.
                    record["tau_spanning"] = record["tau"]
                rows.append(record)
    return pd.DataFrame(rows)


def _cluster_weight_matrix(n_clusters: int, rng: np.random.Generator) -> np.ndarray:
    """(B, n_clusters) integer multiplicities, one row per bootstrap replicate.

    Drawn once per family-by-cohort cell and reused across every window and group, so the
    same resampled patients carry through the whole sweep and the windows are comparable to
    each other rather than each carrying its own resampling noise.
    """
    draws = rng.integers(0, n_clusters, size=(N_BOOTSTRAP_PATIENT, n_clusters))
    weights = np.zeros((N_BOOTSTRAP_PATIENT, n_clusters), dtype=np.float32)
    for replicate in range(N_BOOTSTRAP_PATIENT):
        weights[replicate] = np.bincount(draws[replicate], minlength=n_clusters)
    return weights


def _weighted_median_draws(values: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Median of ``values`` under each row of ``weights``, vectorised over replicates.

    Sorting once and taking a cumulative sum per replicate is what makes 2,000 replicates
    across ~950 cells finish in minutes rather than hours; the obvious loop over replicates
    does not.
    """
    order = np.argsort(values, kind="mergesort")
    sorted_values = values[order]
    sorted_weights = weights[:, order]
    cumulative = np.cumsum(sorted_weights, axis=1)
    total = cumulative[:, -1:]
    with np.errstate(invalid="ignore"):
        index = (cumulative >= total / 2.0).argmax(axis=1)
    out = sorted_values[index]
    return np.where(total[:, 0] > 0, out, np.nan)


def _weighted_mean_draws(values: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Weighted mean of ``values`` under each row of ``weights``.

    Used for the fractions as well: a 0/1 indicator's weighted mean is its weighted fraction,
    and the step-ascent fraction is already a per-episode proportion.
    """
    total = weights.sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(total > 0, weights @ values.astype(np.float32) / total, np.nan)


def _summarise(
    values: np.ndarray, weights: np.ndarray, prefix: str
) -> dict:
    """Point median and IQR, plus a cluster-bootstrap interval on the median."""
    if not len(values):
        return {
            f"{prefix}_median": np.nan,
            f"{prefix}_q25": np.nan,
            f"{prefix}_q75": np.nan,
            f"{prefix}_median_ci_lo": np.nan,
            f"{prefix}_median_ci_hi": np.nan,
        }
    lo, hi = percentile_ci(_weighted_median_draws(values, weights))
    return {
        f"{prefix}_median": float(np.median(values)),
        f"{prefix}_q25": float(np.percentile(values, 25)),
        f"{prefix}_q75": float(np.percentile(values, 75)),
        f"{prefix}_median_ci_lo": lo,
        f"{prefix}_median_ci_hi": hi,
    }


#: Quantities summarised as median (IQR) with a bootstrap interval on the median.
MEDIAN_STATS = (
    "tau",
    "tau_spanning",
    "realised_span_min",
    "delta",
    "gross_up",
    "gross_down",
    "path_length",
    "directedness",
    "max_up_step",
    "max_up_share",
    "last5_share",
)
#: Quantities summarised as a fraction with a bootstrap interval.
FRACTION_STATS = ("tau_positive", "tau_spanning_positive", "ascent", "step_ascent")


def _last5_share(episodes: pd.DataFrame) -> pd.DataFrame:
    """Per episode, the part of the 60-to-5 change that arrived between minute 10 and 5.

    A2 showed that removing the last five minutes lowers tau in all 15 cells, so those minutes
    carry the rise.  This says how much of it.  Undefined when the 60-to-5 change is not
    positive -- a share of a fall is not interpretable -- so those episodes are dropped from
    this column rather than given a signed ratio.
    """
    wide = episodes.pivot_table(
        index=["case_id", "endpoint_min"], columns="window_start_min", values="score_at_endpoint"
    )
    del wide
    near = episodes[(episodes["endpoint_min"] == 5) & (episodes["window_start_min"] == 60)][
        ["case_id", "delta", "score_at_endpoint", "score_at_start"]
    ].rename(columns={"delta": "delta_60_5", "score_at_endpoint": "score_5"})
    far = episodes[(episodes["endpoint_min"] == 10) & (episodes["window_start_min"] == 60)][
        ["case_id", "delta", "score_at_endpoint"]
    ].rename(columns={"delta": "delta_60_10", "score_at_endpoint": "score_10"})
    joined = near.merge(far, on="case_id", how="inner")
    joined = joined[joined["delta_60_5"] > 0]
    joined["last5_share"] = (joined["score_5"] - joined["score_10"]) / joined["delta_60_5"]
    return joined[["case_id", "last5_share"]]


def run() -> pd.DataFrame:
    OUT.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    shares: list[pd.DataFrame] = []

    for family in FAMILY_ORDER:
        for cohort in COHORT_ORDER:
            episodes = _episode_windows(family, cohort)
            share = _last5_share(episodes)
            episodes = episodes.merge(share, on="case_id", how="left")
            share = share.assign(family=family, cohort=cohort)
            shares.append(share)

            index = episodes[["case_id", "cluster_id"]].drop_duplicates("case_id")
            codes_by_case = dict(
                zip(
                    index["case_id"],
                    pd.factorize(index["cluster_id"], sort=True)[0],
                    strict=True,
                )
            )
            n_clusters = index["cluster_id"].nunique()
            rng = np.random.default_rng(
                SEED_BASE + FAMILY_ORDER.index(family) * 100 + COHORT_ORDER.index(cohort)
            )
            cluster_weights = _cluster_weight_matrix(n_clusters, rng)
            episodes["cluster_code"] = episodes["case_id"].map(codes_by_case)
            episodes["tau_positive"] = np.where(
                episodes["tau"].notna(), episodes["tau"] > 0, np.nan
            )
            episodes["tau_spanning_positive"] = np.where(
                episodes["tau_spanning"].notna(), episodes["tau_spanning"] > 0, np.nan
            )
            episodes["ascent"] = np.where(
                episodes["delta"].notna(), episodes["delta"] > 0, np.nan
            )
            episodes["step_ascent"] = episodes["step_ascent_fraction"]

            for (endpoint, start), window_rows in episodes.groupby(
                ["endpoint_min", "window_start_min"], sort=False
            ):
                for group in GROUPS:
                    if group == "event":
                        selected = window_rows[window_rows["label"] == 1]
                    elif group == "control":
                        selected = window_rows[window_rows["label"] == 0]
                    else:
                        selected = window_rows

                    record = {
                        "family": family,
                        "family_label": FAMILY_LABELS[family],
                        "cohort": cohort,
                        "cohort_label": COHORT_LABELS[cohort],
                        "group": group,
                        "group_label": GROUP_LABELS[group],
                        "endpoint_min": int(endpoint),
                        "window_start_min": int(start),
                        "window": f"{int(start)}\u2013{int(endpoint)}",
                        "n_episodes_tau_capped": int(selected["tau"].notna().sum()),
                        "n_episodes_spanning": int(selected["delta"].notna().sum()),
                        "n_clusters": int(selected["cluster_id"].nunique()),
                        "cluster_level": (
                            selected["cluster_level"].iloc[0] if len(selected) else ""
                        ),
                        "median_n_steps": (
                            float(selected["n_steps"].median())
                            if selected["n_steps"].notna().any()
                            else np.nan
                        ),
                    }
                    for name in MEDIAN_STATS:
                        available = selected[selected[name].notna()]
                        weights = cluster_weights[:, available["cluster_code"].to_numpy()]
                        record.update(
                            _summarise(available[name].to_numpy(float), weights, name)
                        )
                        record[f"{name}_n"] = int(len(available))
                    for name in FRACTION_STATS:
                        available = selected[selected[name].notna()]
                        weights = cluster_weights[:, available["cluster_code"].to_numpy()]
                        if len(available):
                            values = available[name].to_numpy(float)
                            lo, hi = percentile_ci(_weighted_mean_draws(values, weights))
                            record[f"{name}_fraction"] = float(values.mean())
                            record[f"{name}_ci_lo"] = lo
                            record[f"{name}_ci_hi"] = hi
                        else:
                            record[f"{name}_fraction"] = np.nan
                            record[f"{name}_ci_lo"] = np.nan
                            record[f"{name}_ci_hi"] = np.nan
                    rows.append(record)

    result = pd.DataFrame(rows).sort_values(
        ["family", "cohort", "endpoint_min", "window_start_min", "group"]
    )
    result.to_csv(OUT / "a6_window_trend.csv", index=False)
    pd.concat(shares, ignore_index=True).to_csv(
        OUT / "a6_last5_share_episodes.csv.gz", index=False, compression="gzip"
    )
    _audit_against_a2(result)
    _write_report(result)
    write_manifest(
        OUT,
        "a6_window_trend",
        [],
        extra={
            "endpoints_min": list(ENDPOINTS),
            "window_starts_min": list(STARTS),
            "groups": list(GROUPS),
            "window_convention": "endpoint < t_to_event <= start, same as A2",
            "bin_step_min": BIN_STEP_MIN,
            "min_points": MIN_POINTS,
            "n_bootstrap": N_BOOTSTRAP_PATIENT,
            "seed_base": SEED_BASE,
            "median_stats": list(MEDIAN_STATS),
            "fraction_stats": list(FRACTION_STATS),
        },
    )
    return result


def _audit_against_a2(result: pd.DataFrame) -> None:
    """The 30-to-5 window is A2's truncated window; the two must agree exactly."""
    a2_path = Path(__file__).resolve().parent / "a2_truncated_tau" / "a2_truncated_tau.csv"
    if not a2_path.is_file():
        return
    a2 = pd.read_csv(a2_path)
    mine = result[
        (result["group"] == "event")
        & (result["endpoint_min"] == 5)
        & (result["window_start_min"] == 30)
    ]
    failures: list[str] = []
    for _, row in mine.iterrows():
        want = a2[(a2["family"] == row["family"]) & (a2["cohort"] == row["cohort"])]
        if want.empty:
            continue
        want = want.iloc[0]
        if int(row["n_episodes_tau_capped"]) != int(want["n_episodes_truncated"]):
            failures.append(
                f"{row['family']}/{row['cohort']}: n {row['n_episodes_tau_capped']} vs "
                f"{want['n_episodes_truncated']}"
            )
        if abs(float(row["tau_median"]) - float(want["median_tau_truncated"])) > 1e-12:
            failures.append(
                f"{row['family']}/{row['cohort']}: median tau {row['tau_median']} vs "
                f"{want['median_tau_truncated']}"
            )
    if failures:
        raise AssertionError(
            "the 30-to-5 window disagrees with A2's truncated window:\n" + "\n".join(failures)
        )


def _iqr(row: pd.Series, prefix: str, digits: int = 3) -> str:
    if not np.isfinite(row.get(f"{prefix}_median", np.nan)):
        return "-"
    return (
        f"{row[f'{prefix}_median']:.{digits}f} "
        f"({row[f'{prefix}_q25']:.{digits}f} to {row[f'{prefix}_q75']:.{digits}f})"
    )


def _fraction(row: pd.Series, prefix: str) -> str:
    if not np.isfinite(row.get(f"{prefix}_fraction", np.nan)):
        return "-"
    return (
        f"{row[f'{prefix}_fraction']:.3f} "
        f"({row[f'{prefix}_ci_lo']:.3f} to {row[f'{prefix}_ci_hi']:.3f})"
    )


def _window_table(cell: pd.DataFrame) -> pd.DataFrame:
    """Every column on the spanning sample, so one row is one sample.

    The capped tau is carried alongside with its own n, because it is the object A2 published
    and dropping it would break the comparison -- but it is a different sample and is labelled
    as one.
    """
    return pd.DataFrame(
        {
            "Window": cell["window"],
            "Group": cell["group_label"],
            "n spanning": cell["n_episodes_spanning"],
            "Kendall tau, median (IQR)": [
                _iqr(row, "tau_spanning") for _, row in cell.iterrows()
            ],
            "tau > 0": [_fraction(row, "tau_spanning_positive") for _, row in cell.iterrows()],
            "Ascent fraction": [_fraction(row, "ascent") for _, row in cell.iterrows()],
            "Change in score, median (IQR)": [_iqr(row, "delta") for _, row in cell.iterrows()],
            "Directedness, median (IQR)": [
                _iqr(row, "directedness") for _, row in cell.iterrows()
            ],
            "Largest step / gross rise": [_iqr(row, "max_up_share") for _, row in cell.iterrows()],
            "n capped": cell["n_episodes_tau_capped"],
            "Capped tau, median (IQR)": [_iqr(row, "tau") for _, row in cell.iterrows()],
            "Median span actually covered, min": cell["realised_span_min_median"].round(0),
        }
    )


def _write_report(result: pd.DataFrame) -> None:
    transformer = result[result["family"] == "transformer"]
    lines = [
        "# A6 - nested windows: trend, ascent, and how far the score actually moved",
        "",
        "Window convention `endpoint < t_to_event <= start`, the same as A2, so the 30-5 "
        "window is A2's truncated window (asserted against it). Kendall tau uses every "
        "observed minute in the window. The ascent fraction, the change in score and the step "
        "decomposition use the 5-minute bin grid, each bin the mean of its observed minutes. "
        f"Intervals are {N_BOOTSTRAP_PATIENT}-replicate cluster bootstraps, drawn once per "
        "family-by-cohort cell and reused across windows so the windows are comparable to each "
        "other.",
        "",
        "**Two samples, and they are not the same one.** A window is a *cap* on the capped "
        "tau, not the span it is measured over: an episode observed only from minute 20 gives "
        "the same capped tau at 60-5 as at 30-5, which is why that column barely moves across "
        "the sweep. Every other column, and the tau reported first, is on the **spanning** "
        "sample -- the episodes whose observation actually reaches the window start. That "
        "sample is much smaller at wide starts and is selected on operation length, because "
        "the median observable time from monitoring start to onset is only 43, 44 and "
        "52 minutes and just 40%, 43% and 47% of event episodes reach 60 minutes. Read the "
        "60-start rows as a statement about long operations.",
        "",
        "**Reading the three together.** The ascent fraction is closer to a volatility measure "
        "than a level measure. A window with a large change in score but a low ascent fraction "
        "and a large largest-step share did not climb, it jumped once or twice; the same change "
        "with a high ascent fraction is a climb. Directedness is the net change over the total "
        "distance travelled: +1 is a monotone rise, 0 a pure wobble, -1 a monotone fall.",
        "",
        "**Do not read the narrow windows' decomposition.** Directedness and the largest-step "
        "share are defined on the steps inside a window, and the 10-5 window has one step, the "
        "15-5 window two. Their directedness is therefore forced to +/-1 and their largest-step "
        "share to 1.000 by arithmetic, not by anything the model did. The median number of steps "
        "is in the CSV as `median_n_steps`; treat the decomposition as informative only where it "
        "is comfortably above two.",
        "",
    ]
    for endpoint in ENDPOINTS:
        lines += [f"## Transformer, near end {endpoint} minutes before onset", ""]
        for cohort in COHORT_ORDER:
            cell = transformer[
                (transformer["cohort"] == cohort) & (transformer["endpoint_min"] == endpoint)
            ].sort_values(["window_start_min", "group"], ascending=[False, True])
            lines += [f"### {COHORT_LABELS[cohort]}", "", df_to_md(_window_table(cell)), ""]

    lines += ["## How much of the rise arrives in the last five minutes", ""]
    share = result[
        (result["endpoint_min"] == 5) & (result["window_start_min"] == 60)
    ]
    share_table = pd.DataFrame(
        {
            "Model": share["family_label"],
            "Cohort": share["cohort_label"],
            "Group": share["group_label"],
            "n": share["last5_share_n"],
            "Share of the 60-5 rise delivered between 10 and 5 min, median (IQR)": [
                _iqr(row, "last5_share") for _, row in share.iterrows()
            ],
            "Change 60-5, median (IQR)": [_iqr(row, "delta") for _, row in share.iterrows()],
        }
    )
    lines += [
        "Computed on episodes whose 60-to-5 change is positive; a share of a fall is not "
        "interpretable.",
        "",
        df_to_md(share_table),
        "",
    ]
    (OUT / "a6_window_trend.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    result = run()
    print("a6_window_trend done ->", OUT)
    view = result[
        (result["family"] == "transformer")
        & (result["endpoint_min"] == 5)
        & (result["window_start_min"].isin([60, 30, 10]))
    ]
    print(
        view[
            [
                "cohort",
                "group",
                "window",
                "n_episodes_tau_capped",
                "n_episodes_spanning",
                "tau_median",
                "tau_q25",
                "tau_q75",
                "ascent_fraction",
                "delta_median",
            ]
        ]
        .round(3)
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
