"""B5 -- case-level discrimination per cell, from the cached scores.

Added for the RCMLR camera-ready (reviewer Aygs, W4): Table A7 gives sensitivity,
specificity, PPV and NNE at one transported threshold, and no case-level discrimination
metric. Without one a reader cannot tell whether a specificity of 0.406 reflects a poor
threshold or a poor fit.

The case score is the **maximum score inside the alert window** -- the statistic the alert
rule itself thresholds: a case alerts at cut ``c`` iff its window maximum is >= ``c``. So
this AUROC is the threshold-free summary of exactly the case-level operating points Table A7
reports one of. The case set is ``lib_n.per_case_all``'s, the same rows Table A7's
sensitivity and specificity are counted on, and that is asserted below by recomputing both
at the transported cut.

No model is retrained or re-scored. Interval: 95% cluster bootstrap on the paper's
clustering unit (patient for MOVER (EPIC) and VitalDB, case for MOVER (SIS)).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "analysis" / "lead_time_null_2026"))

from lib_n import (  # noqa: E402
    alert_window,
    cells,
    cluster_codes,
    headline_cuts,
    load_scored,
    per_case_all,
)

OUT = HERE / "b5_case_auroc"
N_BOOT = 1000
SEED = 20261102


def _auc_weighted(y: np.ndarray, s: np.ndarray, w: np.ndarray) -> float:
    keep = w > 0
    return roc_auc_score(y[keep], s[keep], sample_weight=w[keep])


def run() -> pd.DataFrame:
    cuts = headline_cuts()
    rows = []
    for i, (family, cohort) in enumerate(cells()):
        frame = load_scored(family, cohort)
        frame = frame[(frame["t_to_event"] > 0) & np.isfinite(frame["score"])]
        case_max = alert_window(frame).groupby("case_id")["score"].max()

        per_case = per_case_all(family, cohort, float(cuts[family]))
        per_case["case_max"] = per_case["case_id"].map(case_max)
        assert per_case["case_max"].notna().all(), (family, cohort)

        y = per_case["label"].to_numpy().astype(int)
        s = per_case["case_max"].to_numpy()
        # Consistency with Table A7: alerting at the cut <=> window max >= cut.
        alerted = per_case["lead"].notna().to_numpy()
        assert np.array_equal(alerted, s >= float(cuts[family])), (family, cohort)
        sens = alerted[y == 1].mean()
        spec = 1 - alerted[y == 0].mean()

        auc = roc_auc_score(y, s)
        codes, n_clusters = cluster_codes(per_case)
        rng = np.random.default_rng(SEED + i)
        boots = np.empty(N_BOOT)
        for b in range(N_BOOT):
            draw = np.bincount(rng.integers(0, n_clusters, n_clusters), minlength=n_clusters)
            boots[b] = _auc_weighted(y, s, draw[codes].astype(float))
        lo, hi = np.percentile(boots, [2.5, 97.5])
        rows.append(dict(
            family=family, cohort=cohort, n_cases=len(per_case), n_event=int(y.sum()),
            case_auroc=auc, ci_low=lo, ci_high=hi,
            sensitivity_at_cut=sens, specificity_at_cut=spec,
        ))
    out = pd.DataFrame(rows)

    OUT.mkdir(exist_ok=True)
    out.to_csv(OUT / "b5_case_auroc.csv", index=False)
    return out


if __name__ == "__main__":
    print(run().round(3).to_string(index=False))
