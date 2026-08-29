"""A7 - is the observable run-up long enough, and is its length informative?

A6 reports a 60-to-5 window, and the observable time from monitoring start to onset has a
median of 43, 44 and 52 minutes. So the widest windows are computed on a minority of episodes,
selected on how long the run-up was. That is the first thing a reviewer will ask about, and it
has two distinct answers.

**Does the sample change the trajectory?** Reported two ways side by side, which is the
standard early-warning-score treatment of a varying denominator. (a) All cases with the
per-timepoint denominator the paper already uses, with N(t) printed beside AUROC(t) so a
reader can see where the interval widens. (b) The same bins recomputed on only the cases whose
observation reaches a common start L, which is the fair-comparison view at a fixed N. If the
two agree over the shared bins, the change in discrimination is not an artefact of sample
composition. If they disagree, that disagreement is the finding.

**Is the length informative?** For an event case the observable run-up *is* the time to onset,
so a short run-up is not missing data -- it is an early-onset event, which is a clinically
different thing from a late-onset one. This part measures that rather than assuming it:
standardized mean differences between short and long run-ups, and a logistic model for
P(run-up >= 40 min) fitted twice, once on patient and event characteristics alone and once
adding operation length, so "the long subset is just longer operations" can be told apart from
"the long subset is different patients".

``procedure_group`` appears here as a covariate. It is barred from being a *model input* for
the IOH task because it identifies the cohort; used descriptively within one cohort to
characterise who is in a subset, it is the subgroup reporting the rule allows for.

Post-hoc on cached scores and the source series; no retraining.
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib_pt import (  # noqa: E402
    BIN_CENTERS,
    BOOTSTRAP_SEED,
    COHORT_LABELS,
    COHORT_ORDER,
    N_BOOTSTRAP_OTHER,
    REPO,
    assign_bin,
    df_to_md,
    load_scored,
    percentile_ci,
    write_manifest,
)

sys.path.insert(0, str(REPO))

from ioh_prediction.data.eligibility import INDUCTION_DROP_MIN  # noqa: E402
from ioh_prediction.data.splits import stratified_subject_split_3way  # noqa: E402

OUT = Path(__file__).resolve().parent / "a7_observability"
TIMESERIES = str(REPO / "data" / "timeseries" / "source=*" / "case_id=*" / "data.parquet")

#: Common window starts to re-anchor on.  Each is a published bin centre.
COMMON_STARTS = (20, 30, 40, 60)
#: Split point for the informative-length diagnostic.
LONG_RUNUP_MIN = 40
#: |SMD| above this is conventionally called a meaningful imbalance.
SMD_FLAG = 0.1

COHORT_SOURCE = {"epic_test": "mover_epic", "vitaldb": "vitaldb", "mover": "mover"}
CONTINUOUS = ("age", "bmi", "surgery_min", "episode_nadir_map", "episode_duration_min")
BINARY = ("female",)


def _manifest(cohort: str) -> pd.DataFrame:
    if cohort == "epic_test":
        epic = pd.read_csv(REPO / "outputs" / "runs" / "gap0" / "manifest.csv")
        epic = epic[(epic["source"] == "mover_epic") & epic["subject_id"].notna()]
        _, _, test = stratified_subject_split_3way(epic, seed=1004)
        frame = test
    else:
        frame = pd.read_csv(
            REPO / "outputs" / "runs" / "gap0" / f"external_{cohort}" / "manifest.csv"
        )
    frame = frame.copy()
    frame["case_id"] = frame["case_id"].astype(str)
    drop = INDUCTION_DROP_MIN[COHORT_SOURCE[cohort]]
    # For an event case the observable run-up is the time to onset; for a control it is the
    # time to the sampled pseudo-onset.
    frame["observable_min"] = np.where(
        frame["label"] == 1,
        frame["first_onset_min"] - drop,
        frame["ref_time_min"] - drop,
    )
    frame["female"] = (frame["sex"].astype(str).str.upper().str[0] == "F").astype(float)
    frame.loc[frame["sex"].isna(), "female"] = np.nan
    return frame


def _episode_severity() -> pd.DataFrame:
    """Nadir MAP and duration of each case's first sustained episode.

    Severity has to come from the source series: the manifest records when the first episode
    started, not how deep or how long it went, and "were the short run-ups the more severe
    events" is exactly the question the informative-length check needs answered.
    """
    return duckdb.sql(f"""
      WITH minutes AS (
        SELECT source, case_id, t_min, MAP, event_id_d3
        FROM read_parquet('{TIMESERIES}', hive_partitioning=true)
        WHERE event_id_d3 IS NOT NULL
      ), first_episode AS (
        SELECT source, case_id, MIN(event_id_d3) AS event_id
        FROM (
          SELECT source, case_id, event_id_d3, MIN(t_min) AS onset
          FROM minutes GROUP BY source, case_id, event_id_d3
        ) GROUP BY source, case_id
      )
      SELECT m.source, m.case_id,
             MIN(m.MAP)   AS episode_nadir_map,
             COUNT(*)     AS episode_duration_min
      FROM minutes m
      JOIN first_episode f
        ON f.source = m.source AND f.case_id = m.case_id AND f.event_id = m.event_id_d3
      GROUP BY m.source, m.case_id
    """).df()


def _bin_membership(cohort: str) -> pd.DataFrame:
    """Which published bins each case has an observed minute in, from the cached scores."""
    frame = load_scored("transformer", cohort)
    frame = frame[(frame["t_to_event"] > 0) & np.isfinite(frame["score"])]
    frame = frame.assign(bin_center=assign_bin(frame["t_to_event"]))
    frame = frame[frame["bin_center"].notna()]
    return (
        frame.groupby(["case_id", "bin_center"], sort=False)
        .size()
        .reset_index(name="n_minutes")
    )


def _auroc_curves(cohort: str) -> pd.DataFrame:
    """AUROC(t) and N(t) on all cases, and on each common-start subset, with paired intervals."""
    frame = load_scored("transformer", cohort)
    frame = frame[np.isfinite(frame["score"])]
    values = frame["t_to_event"].to_numpy(float)
    labels = frame["label"].to_numpy(int)
    scores = np.clip(frame["score"].to_numpy(float), 0, 1)
    codes, clusters = pd.factorize(frame["cluster_id"], sort=True)
    n_clusters = len(clusters)

    membership = _bin_membership(cohort)
    reaches = {
        start: set(membership.loc[membership["bin_center"] == start, "case_id"])
        for start in COMMON_STARTS
    }
    case_ids = frame["case_id"].to_numpy()

    rng = np.random.default_rng(BOOTSTRAP_SEED + 90_000 + COHORT_ORDER.index(cohort))
    weights = np.zeros((N_BOOTSTRAP_OTHER, n_clusters), dtype=np.float32)
    for replicate in range(N_BOOTSTRAP_OTHER):
        weights[replicate] = np.bincount(
            rng.integers(0, n_clusters, n_clusters), minlength=n_clusters
        )

    rows: list[dict] = []
    for centre in BIN_CENTERS:
        # No lower bound on t_to_event: this reproduces effective_horizon's bin definition,
        # which the published AUROC uses.
        in_bin = (values >= centre - 1) & (values < centre + 1)
        for sample in ("all", *(f"reaches_{start}" for start in COMMON_STARTS)):
            if sample == "all":
                keep = in_bin
            else:
                start = int(sample.split("_")[1])
                if centre > start:
                    continue
                keep = in_bin & np.isin(case_ids, list(reaches[start]))
            if keep.sum() < 30 or np.unique(labels[keep]).size < 2:
                continue
            point = float(roc_auc_score(labels[keep], scores[keep]))
            row_weights = weights[:, codes[keep]]
            draws = np.full(N_BOOTSTRAP_OTHER, np.nan)
            y, p = labels[keep], scores[keep]
            for replicate in range(N_BOOTSTRAP_OTHER):
                w = row_weights[replicate]
                if w.sum() == 0 or np.unique(y[w > 0]).size < 2:
                    continue
                draws[replicate] = roc_auc_score(y, p, sample_weight=w)
            lo, hi = percentile_ci(draws)
            rows.append(
                {
                    "cohort": cohort,
                    "cohort_label": COHORT_LABELS[cohort],
                    "sample": sample,
                    "bin_center_min": int(centre),
                    "n_rows": int(keep.sum()),
                    "n_cases": int(pd.unique(case_ids[keep]).size),
                    "n_event_cases": int(pd.unique(case_ids[keep & (labels == 1)]).size),
                    "n_clusters": int(pd.unique(codes[keep]).size),
                    "auroc": point,
                    "auroc_ci_lo": lo,
                    "auroc_ci_hi": hi,
                    "n_bootstrap": N_BOOTSTRAP_OTHER,
                }
            )
    return pd.DataFrame(rows)


def _smd_continuous(a: pd.Series, b: pd.Series) -> float:
    a, b = a.dropna(), b.dropna()
    if len(a) < 2 or len(b) < 2:
        return np.nan
    pooled = np.sqrt((a.var() + b.var()) / 2)
    return float((a.mean() - b.mean()) / pooled) if pooled > 0 else np.nan


def _smd_binary(a: pd.Series, b: pd.Series) -> float:
    a, b = a.dropna(), b.dropna()
    if not len(a) or not len(b):
        return np.nan
    p1, p2 = a.mean(), b.mean()
    bar = (p1 + p2) / 2
    spread = np.sqrt(bar * (1 - bar))
    return float((p1 - p2) / spread) if spread > 0 else np.nan


def _balance(events: pd.DataFrame, cohort: str) -> pd.DataFrame:
    long = events[events["observable_min"] >= LONG_RUNUP_MIN]
    short = events[events["observable_min"] < LONG_RUNUP_MIN]
    rows: list[dict] = []

    def record(variable, long_value, short_value, smd):
        rows.append(
            {
                "cohort": cohort,
                "cohort_label": COHORT_LABELS[cohort],
                "variable": variable,
                "n_long": int(len(long)),
                "n_short": int(len(short)),
                "long": long_value,
                "short": short_value,
                "smd": smd,
                "flagged": bool(np.isfinite(smd) and abs(smd) > SMD_FLAG),
            }
        )

    for column in CONTINUOUS:
        if column not in events or events[column].notna().sum() < 20:
            continue
        record(
            f"{column}, mean",
            float(long[column].mean()),
            float(short[column].mean()),
            _smd_continuous(long[column], short[column]),
        )
    for column in BINARY:
        if column not in events or events[column].notna().sum() < 20:
            continue
        record(
            f"{column}, proportion",
            float(long[column].mean()),
            float(short[column].mean()),
            _smd_binary(long[column], short[column]),
        )
    for column in ("asa", "ane_type", "procedure_group"):
        if column not in events or events[column].notna().sum() < 20:
            continue
        for level in sorted(events[column].dropna().astype(str).unique()):
            indicator_long = (long[column].astype(str) == level).astype(float)
            indicator_short = (short[column].astype(str) == level).astype(float)
            record(
                f"{column} = {level}, proportion",
                float(indicator_long.mean()),
                float(indicator_short.mean()),
                _smd_binary(indicator_long, indicator_short),
            )
    return pd.DataFrame(rows)


def _logistic(events: pd.DataFrame, cohort: str) -> pd.DataFrame:
    """P(run-up >= 40 min), with and without operation length."""
    import statsmodels.api as sm

    base = ["age", "female", "bmi", "episode_nadir_map", "episode_duration_min"]
    categorical = [
        column
        for column in ("asa", "ane_type", "procedure_group")
        if column in events and events[column].notna().sum() >= 20 and events[column].nunique() > 1
    ]
    rows: list[dict] = []
    for name, columns in (
        ("patient and event characteristics", base),
        ("plus operation length", [*base, "surgery_min"]),
    ):
        usable = [column for column in columns if column in events and events[column].notna().sum() >= 20]
        design = events[[*usable, *categorical, "observable_min"]].dropna()
        if len(design) < 60:
            continue
        y = (design.pop("observable_min") >= LONG_RUNUP_MIN).astype(int)
        X = pd.get_dummies(design, columns=categorical, drop_first=True, dtype=float)
        X = X.loc[:, X.std() > 0]
        X = sm.add_constant(X)
        try:
            fit = sm.Logit(y, X).fit(disp=0, maxiter=200)
        except Exception as error:  # pragma: no cover - separation or singularity
            rows.append(
                {
                    "cohort": cohort,
                    "model": name,
                    "term": "FIT FAILED",
                    "note": str(error)[:200],
                }
            )
            continue
        intervals = fit.conf_int()
        for term in fit.params.index:
            if term == "const":
                continue
            rows.append(
                {
                    "cohort": cohort,
                    "cohort_label": COHORT_LABELS[cohort],
                    "model": name,
                    "n": int(len(design)),
                    "n_long": int(y.sum()),
                    "term": term,
                    "odds_ratio": float(np.exp(fit.params[term])),
                    "or_ci_lo": float(np.exp(intervals.loc[term, 0])),
                    "or_ci_hi": float(np.exp(intervals.loc[term, 1])),
                    "p_value": float(fit.pvalues[term]),
                    "significant": bool(fit.pvalues[term] < 0.05),
                    "pseudo_r2": float(fit.prsquared),
                }
            )
    return pd.DataFrame(rows)


def run() -> dict[str, pd.DataFrame]:
    OUT.mkdir(parents=True, exist_ok=True)
    severity = _episode_severity()
    severity["case_id"] = severity["case_id"].astype(str)

    lengths, curves, balances, models = [], [], [], []
    for cohort in COHORT_ORDER:
        manifest = _manifest(cohort)
        source = COHORT_SOURCE[cohort]
        manifest = manifest.merge(
            severity[severity["source"] == source].drop(columns=["source"]),
            on="case_id",
            how="left",
        )
        for label, group in (("event", 1), ("control", 0)):
            selected = manifest[manifest["label"] == group]
            observable = selected["observable_min"]
            lengths.append(
                {
                    "cohort": cohort,
                    "cohort_label": COHORT_LABELS[cohort],
                    "group": label,
                    "induction_drop_min": INDUCTION_DROP_MIN[source],
                    "n": int(len(selected)),
                    "observable_median": float(observable.median()),
                    "observable_q25": float(observable.quantile(0.25)),
                    "observable_q75": float(observable.quantile(0.75)),
                    **{
                        f"frac_ge_{threshold}": float((observable >= threshold).mean())
                        for threshold in (10, 20, 30, 40, 60)
                    },
                    "case_length_median": float(selected["case_length_min"].median()),
                }
            )
        events = manifest[manifest["label"] == 1]
        balances.append(_balance(events, cohort))
        models.append(_logistic(events, cohort))
        curves.append(_auroc_curves(cohort))

    tables = {
        "observable_length": pd.DataFrame(lengths),
        "auroc_by_sample": pd.concat(curves, ignore_index=True),
        "balance_short_vs_long": pd.concat(balances, ignore_index=True),
        "logistic_long_runup": pd.concat(models, ignore_index=True),
    }
    for name, frame in tables.items():
        frame.to_csv(OUT / f"a7_{name}.csv", index=False)
    _write_report(tables)
    write_manifest(
        OUT,
        "a7_observability",
        [],
        extra={
            "common_starts_min": list(COMMON_STARTS),
            "long_runup_min": LONG_RUNUP_MIN,
            "smd_flag": SMD_FLAG,
            "n_bootstrap": N_BOOTSTRAP_OTHER,
            "seed": BOOTSTRAP_SEED + 90_000,
            "observable_definition": (
                "first sustained onset minus the induction exclusion for events; sampled "
                "pseudo-onset minus the induction exclusion for controls"
            ),
        },
    )
    return tables


def _write_report(tables: dict[str, pd.DataFrame]) -> None:
    lengths = tables["observable_length"]
    curves = tables["auroc_by_sample"]
    balance = tables["balance_short_vs_long"]
    models = tables["logistic_long_runup"]

    lines = [
        "# A7 - observable run-up, and whether its length is informative",
        "",
        "## 1. How long the run-up actually is",
        "",
        df_to_md(
            pd.DataFrame(
                {
                    "Cohort": lengths["cohort_label"],
                    "Group": lengths["group"],
                    "n": lengths["n"],
                    "Observable min, median (IQR)": [
                        f"{row.observable_median:.0f} ({row.observable_q25:.0f}"
                        f"-{row.observable_q75:.0f})"
                        for row in lengths.itertuples()
                    ],
                    ">=20 min": lengths["frac_ge_20"].map("{:.0%}".format),
                    ">=40 min": lengths["frac_ge_40"].map("{:.0%}".format),
                    ">=60 min": lengths["frac_ge_60"].map("{:.0%}".format),
                }
            )
        ),
        "",
        "## 2. AUROC(t) with a varying denominator, against the common-start subsets",
        "",
        "The `all` rows are the paper's convention: every case that has a minute in the bin. "
        "The `reaches_L` rows keep only cases whose observation reaches bin L, which fixes the "
        "denominator across the bins at or inside L. N(t) is printed beside AUROC(t) so the "
        "widening interval is attributable.",
        "",
    ]
    for cohort in COHORT_ORDER:
        cell = curves[curves["cohort"] == cohort]
        table = pd.DataFrame(
            {
                "Sample": cell["sample"],
                "Bin, min": cell["bin_center_min"],
                "N cases": cell["n_cases"],
                "N event cases": cell["n_event_cases"],
                "AUROC (95% CI)": [
                    f"{row.auroc:.3f} ({row.auroc_ci_lo:.3f}-{row.auroc_ci_hi:.3f})"
                    for row in cell.itertuples()
                ],
            }
        )
        lines += [
            f"### {COHORT_LABELS[cohort]}",
            "",
            df_to_md(table.sort_values(["Sample", "Bin, min"], ascending=[True, False])),
            "",
        ]

    lines += [
        "## 3. Are short and long run-ups the same cases?",
        "",
        f"Short is under {LONG_RUNUP_MIN} minutes of observable run-up, long is at or above it. "
        f"|SMD| above {SMD_FLAG} is flagged. For an event case the run-up *is* the time to "
        "onset, so a short run-up means an early-onset event; this table says whether those "
        "events are otherwise different.",
        "",
        df_to_md(
            balance.loc[
                balance["flagged"],
                ["cohort_label", "variable", "n_long", "n_short", "long", "short", "smd"],
            ].round(3)
        ),
        "",
        "Unflagged variables are in `a7_balance_short_vs_long.csv`.",
        "",
        "## 4. A model for the long run-up",
        "",
        f"Logistic regression for P(run-up >= {LONG_RUNUP_MIN} min) among event cases, fitted "
        "twice: on patient and event characteristics alone, and again adding operation length. "
        "Significant terms in the first model mean the long subset is a different set of "
        "patients, not only a set of longer operations.",
        "",
    ]
    significant = models[models.get("significant", pd.Series(dtype=bool)).fillna(False)]
    if len(significant):
        lines += [
            df_to_md(
                significant[
                    ["cohort_label", "model", "n", "n_long", "term", "odds_ratio", "or_ci_lo", "or_ci_hi", "p_value", "pseudo_r2"]
                ].round(4)
            ),
            "",
        ]
    else:
        lines += ["No term reached p<0.05 in any cohort.", ""]
    lines += ["Every term, significant or not, is in `a7_logistic_long_runup.csv`.", ""]
    (OUT / "a7_observability.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    tables = run()
    print("a7_observability done ->", OUT)
    print(tables["observable_length"][
        ["cohort", "group", "n", "observable_median", "frac_ge_40", "frac_ge_60"]
    ].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
