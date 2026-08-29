"""Shared library for the IOH clinical-faithfulness trend-robustness analysis.

This is a POST-HOC analysis of cached per-minute prediction scores. No model is
ever (re)trained here — every function below reads the cached
`predictions_raw.parquet` / `window_metrics.csv` / `mann_kendall.csv` artefacts
produced by the completed gap-sweep runs and re-derives statistics from them.

Reused, NOT reimplemented (project hard rule): the AUROC/AUPRC trajectory
is recomputed with the pipeline's own `compute_window_metrics`, and the classical
MK reproduction uses the pipeline's own `mk_for_metrics`.

Sign convention (fixed once, used everywhere):
    The trajectory is ordered by `time_window_min` DESCENDING, i.e. the farthest
    lead-time-before-onset bin comes first (index 0) and the onset bin (0 min)
    comes last. A POSITIVE Kendall tau / Sen's slope therefore means
    "AUROC rises as the evaluation point approaches onset" == clinical
    faithfulness. This matches `ioh_prediction.evaluation.mann_kendall`.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import pymannkendall as mk
from scipy.stats import kendalltau
from sklearn.metrics import roc_auc_score

from ioh_prediction.evaluation.time_window_metrics import (
    DEFAULT_TIME_POINTS_MIN,
    WindowConfig,
    compute_window_metrics,
)

# ----------------------------------------------------------------------------
# Paths & constants
# ----------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = REPO_ROOT / "analysis" / "ioh_faithfulness_2026"
RUNS_ROOT = REPO_ROOT / "outputs" / "runs"

# Gaps present in the sweep (auto-verified against disk in discover_grid()).
GAPS = (0, 5, 10, 15, 20, 25, 30)

# cohort key -> (subdir under the gap run, human label)
COHORTS = {
    "epic_test": ("predictions/test", "EPIC test"),
    "vitaldb": ("external_vitaldb", "VitalDB (external, primary)"),
    "mover": ("external_mover", "MOVER/SIS (external, secondary)"),
}

MODEL_NAME = "ITETransformer"  # single architecture; the gap is the setting.

# New-randomness seed (bootstrap only). Existing experiment seeds are untouched.
BOOTSTRAP_SEED = 20260706
N_BOOTSTRAP = 1000

# Primary faithfulness metric for the robustness family; MK also reported for the
# other trajectory metrics for completeness.
PRIMARY_METRIC = "auroc"
MK_METRICS = ("auroc", "auprc", "ppv_030", "ppv_050")

SIGN_CONVENTION = (
    "trajectory ordered by time_window_min DESCENDING (farthest-from-onset first); "
    "positive tau / Sen's slope == AUROC rises toward onset == clinical faithfulness"
)


# ----------------------------------------------------------------------------
# Grid discovery
# ----------------------------------------------------------------------------
@dataclass(frozen=True)
class Cell:
    model: str
    setting: str  # e.g. "gap5"  (lead-time offset the model trained at)
    gap: int
    cohort: str  # cohort key
    cohort_label: str
    pred_path: Path
    wm_path: Path
    mk_path: Path

    @property
    def key(self) -> str:
        return f"{self.model}|{self.setting}|{self.cohort}"


def discover_grid() -> list[Cell]:
    """Auto-detect every (model x setting x cohort) trajectory that has both a
    cached score file and an existing MK file. Nothing is hardcoded beyond the
    directory naming convention; missing cells are skipped (and reported)."""
    cells: list[Cell] = []
    for g in GAPS:
        run = RUNS_ROOT / f"gap{g}"
        if not run.is_dir():
            continue
        for ck, (sub, label) in COHORTS.items():
            base = run / sub
            pred = base / "predictions_raw.parquet"
            wm = base / "window_metrics.csv"
            mk_ = base / "mann_kendall.csv"
            if pred.exists() and wm.exists() and mk_.exists():
                cells.append(
                    Cell(
                        model=MODEL_NAME,
                        setting=f"gap{g}",
                        gap=g,
                        cohort=ck,
                        cohort_label=label,
                        pred_path=pred,
                        wm_path=wm,
                        mk_path=mk_,
                    )
                )
    return cells


# ----------------------------------------------------------------------------
# Trajectory & MK helpers
# ----------------------------------------------------------------------------
def load_predictions(cell: Cell) -> pd.DataFrame:
    df = pd.read_parquet(cell.pred_path)
    return attach_highest_cluster(df, cell.pred_path, cell.cohort)


def manifest_for_predictions(pred_path: Path, cohort: str) -> Path:
    """Return the case manifest paired with a cached prediction file."""
    if cohort == "epic_test":
        # .../<run>/predictions/test/predictions_raw.parquet
        candidate = pred_path.parents[2] / "test_manifest.csv"
        fallback = RUNS_ROOT / "gap0" / "test_manifest.csv"
    else:
        # .../<run>/external_{cohort}/predictions_raw.parquet
        candidate = pred_path.parent / "manifest.csv"
        fallback = RUNS_ROOT / "gap0" / f"external_{cohort}" / "manifest.csv"
    return candidate if candidate.exists() else fallback


def attach_highest_cluster(
    pred: pd.DataFrame, pred_path: Path, cohort: str
) -> pd.DataFrame:
    """Attach the highest reliably identifiable resampling unit.

    EPIC and VitalDB expose patient identifiers. MOVER/SIS does not: its
    ``subject_id`` is a case surrogate, so the surgical case remains the highest
    identifiable unit there.
    """
    out = pred.copy()
    out["case_id"] = out["case_id"].astype(str)
    if cohort == "mover":
        out["cluster_id"] = out["case_id"]
        out["cluster_level"] = "case"
        return out
    manifest = pd.read_csv(
        manifest_for_predictions(Path(pred_path), cohort),
        usecols=["case_id", "subject_id"],
    )
    manifest["case_id"] = manifest["case_id"].astype(str)
    if manifest["case_id"].duplicated().any() or manifest["subject_id"].isna().any():
        raise ValueError(f"invalid patient mapping in {manifest_for_predictions(Path(pred_path), cohort)}")
    out = out.merge(manifest, on="case_id", how="left", validate="m:1")
    if out["subject_id"].isna().any():
        raise ValueError(f"prediction cases missing from patient manifest for {cohort}")
    out["cluster_id"] = out["subject_id"].astype(str)
    out["cluster_level"] = "patient"
    return out


def recompute_trajectory(pred: pd.DataFrame, config: WindowConfig | None = None) -> pd.DataFrame:
    """Recompute the lead-time-bin AUROC/AUPRC/... trajectory with the pipeline's
    own function (guarantees Step-0 reproduction)."""
    config = config or WindowConfig()
    return compute_window_metrics(pred[["t_to_event", "score", "label"]], config)


def sens_slope_on_series(values: np.ndarray, positions: np.ndarray | None = None) -> float:
    """Theil-Sen (Sen's) slope of `values` against ordinal `positions`.

    `positions` defaults to 0..n-1 (the farthest-first ordering). Passing
    explicit positions lets bootstrap replicates keep the ORIGINAL bin ordinals
    even when some bins drop out, so a dropped middle bin doesn't distort slopes.
    """
    values = np.asarray(values, dtype=np.float64)
    ok = ~np.isnan(values)
    v = values[ok]
    if v.size < 2:
        return float("nan")
    pos = (np.arange(values.size) if positions is None else np.asarray(positions, float))[ok]
    slopes = []
    for i in range(v.size):
        for j in range(i + 1, v.size):
            dp = pos[j] - pos[i]
            if dp != 0:
                slopes.append((v[j] - v[i]) / dp)
    return float(np.median(slopes)) if slopes else float("nan")


def mk_classical_and_exact(traj: pd.DataFrame, metric: str) -> dict:
    """Classical MK (pymannkendall normal-approx, matches the saved files) PLUS
    the exact discrete p-value (scipy kendalltau, exact for the no-tie MK
    statistic). tau and Sen's slope are identical between the two; only the
    p-value differs, which matters most at small n."""
    srt = traj.sort_values("time_window_min", ascending=False).reset_index(drop=True)
    y = srt[metric].to_numpy(dtype=np.float64)
    y = y[~np.isnan(y)]
    n = int(y.size)
    out = {
        "metric": metric,
        "n_bins": n,
        "tau": float("nan"),
        "p_classical_normal": float("nan"),  # pymannkendall original_test (reproduces saved)
        "p_classical_exact": float("nan"),  # scipy exact
        "sens_slope": float("nan"),
        "trend_direction": "insufficient_data",
    }
    if n < 4:
        return out
    res = mk.original_test(y)
    x = np.arange(n)
    exact_ok = True
    try:
        # Exact discrete p for the no-tie MK statistic.
        _, p_ex = kendalltau(x, y, method="exact")
    except ValueError:
        # Ties (e.g. in the degenerate info-accum null): exact test undefined;
        # fall back to the asymptotic p with a flag. Real metric trajectories
        # have no ties (verified in Step 0), so this path is null-only.
        _, p_ex = kendalltau(x, y, method="asymptotic")
        exact_ok = False
    out.update(
        tau=float(res.Tau),
        p_classical_normal=float(res.p),
        p_classical_exact=float(p_ex),
        exact_p_available=exact_ok,
        sens_slope=float(res.slope),
        trend_direction=str(res.trend),
    )
    return out


def mk_robust(traj: pd.DataFrame, metric: str) -> dict:
    """Autocorrelation-aware MK variants on the same descending-ordered series:
    Hamed-Rao (variance correction for lag-k autocorrelation) and Yue-Pilon
    trend-free pre-whitening."""
    srt = traj.sort_values("time_window_min", ascending=False).reset_index(drop=True)
    y = srt[metric].to_numpy(dtype=np.float64)
    y = y[~np.isnan(y)]
    n = int(y.size)
    out = {"metric": metric, "n_bins": n, "p_hamedrao": float("nan"), "p_yuepilon": float("nan"),
           "tau_hamedrao": float("nan"), "tau_yuepilon": float("nan")}
    if n < 4:
        return out
    hr = mk.hamed_rao_modification_test(y)
    yp = mk.trend_free_pre_whitening_modification_test(y)
    out.update(
        p_hamedrao=float(hr.p),
        tau_hamedrao=float(hr.Tau),
        p_yuepilon=float(yp.p),
        tau_yuepilon=float(yp.Tau),
    )
    return out


# ----------------------------------------------------------------------------
# Case-level bootstrap (weighted-AUROC formulation)
# ----------------------------------------------------------------------------
@dataclass
class BinCache:
    """Precomputed per-bin arrays for fast weighted-AUROC bootstrap.

    A case sampled k times in a replicate contributes sample_weight=k to every
    one of its rows -- this is the exact case-level (block) bootstrap, preserving
    within-case correlation, without physically duplicating rows.
    """

    time_points: np.ndarray  # descending-ordered bin centers actually kept
    positions: np.ndarray  # ordinal position of each kept bin in the full grid
    y: list[np.ndarray]  # per-bin labels
    p: list[np.ndarray]  # per-bin scores
    cidx: list[np.ndarray]  # per-bin case index (0..C-1)
    n_cases: int = 0
    min_samples: int = 30


def build_bin_cache(pred: pd.DataFrame, config: WindowConfig | None = None) -> BinCache:
    config = config or WindowConfig()
    half = config.window_size_min / 2.0
    unit = "cluster_id" if "cluster_id" in pred.columns else "case_id"
    codes, _ = pd.factorize(pred[unit], sort=True)
    n_cases = int(codes.max()) + 1 if codes.size else 0
    tte = pred["t_to_event"].to_numpy()
    lab = pred["label"].to_numpy(dtype=np.int64)
    scr = np.clip(pred["score"].to_numpy(dtype=np.float64), 0.0, 1.0)

    tps, poss, ys, ps, cs = [], [], [], [], []
    full_order = sorted(config.time_points_min, reverse=True)  # farthest-first
    for pos, tp in enumerate(full_order):
        lo, hi = tp - half, tp + half
        m = (tte >= lo) & (tte < hi)
        if m.sum() < config.min_samples_per_window:
            continue
        if np.unique(lab[m]).size < 2:
            continue
        tps.append(tp)
        poss.append(pos)
        ys.append(lab[m])
        ps.append(scr[m])
        cs.append(codes[m])
    return BinCache(
        time_points=np.array(tps),
        positions=np.array(poss),
        y=ys,
        p=ps,
        cidx=cs,
        n_cases=n_cases,
        min_samples=config.min_samples_per_window,
    )


def bootstrap_slope_dauroc(
    cache: BinCache,
    n_boot: int = N_BOOTSTRAP,
    seed: int = BOOTSTRAP_SEED,
) -> dict:
    """Case-level bootstrap of Sen's slope and dAUROC(near-far).

    Returns point estimates on the full data + percentile CIs over valid
    replicates. Edge rule (fixed & logged): in a replicate a bin is dropped if,
    after weighting, either class has zero total weight or total weight <
    min_samples; a replicate is invalid if fewer than 2 bins survive (dAUROC) or
    fewer than 3 survive (slope).
    """
    rng = np.random.default_rng(seed)
    C = cache.n_cases
    positions = cache.positions.astype(float)

    def auroc_series(weights_per_case: np.ndarray) -> np.ndarray:
        vals = np.full(len(cache.y), np.nan)
        for b in range(len(cache.y)):
            w = weights_per_case[cache.cidx[b]]
            yb = cache.y[b]
            pos_w = w > 0
            if pos_w.sum() < cache.min_samples:
                continue
            yb_w, w_w, pb_w = yb[pos_w], w[pos_w], cache.p[b][pos_w]
            # both classes must carry positive weight
            if not (np.any(yb_w == 1) and np.any(yb_w == 0)):
                continue
            if w_w.sum() < cache.min_samples:
                continue
            vals[b] = roc_auc_score(yb_w, pb_w, sample_weight=w_w)
        return vals

    # point estimate (unit weights == full data)
    base_vals = auroc_series(np.ones(C))
    base_slope = sens_slope_on_series(base_vals, positions)
    base_d = _dauroc_near_far(base_vals, cache.time_points)

    slopes, daurocs = [], []
    n_invalid = 0
    for _ in range(n_boot):
        counts = np.bincount(rng.integers(0, C, C), minlength=C).astype(float)
        vals = auroc_series(counts)
        n_valid_bins = int(np.sum(~np.isnan(vals)))
        s = sens_slope_on_series(vals, positions) if n_valid_bins >= 3 else np.nan
        d = _dauroc_near_far(vals, cache.time_points) if n_valid_bins >= 2 else np.nan
        if np.isnan(s) and np.isnan(d):
            n_invalid += 1
            continue
        if not np.isnan(s):
            slopes.append(s)
        if not np.isnan(d):
            daurocs.append(d)

    def ci(a):
        a = np.asarray(a, float)
        if a.size == 0:
            return (float("nan"), float("nan"))
        return (float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5)))

    slo_lo, slo_hi = ci(slopes)
    d_lo, d_hi = ci(daurocs)
    return {
        "sens_slope": base_slope,
        "slope_CI_lo": slo_lo,
        "slope_CI_hi": slo_hi,
        "dAUROC_near_far": base_d,
        "dAUROC_CI_lo": d_lo,
        "dAUROC_CI_hi": d_hi,
        "n_valid_replicates": int(min(len(slopes), len(daurocs))) if (slopes and daurocs) else int(max(len(slopes), len(daurocs))),
        "n_valid_slope": len(slopes),
        "n_valid_dauroc": len(daurocs),
        "n_invalid_replicates": n_invalid,
        "n_bins_full": int(np.sum(~np.isnan(base_vals))),
    }


def _dauroc_near_far(vals: np.ndarray, time_points: np.ndarray) -> float:
    """AUROC(closest-to-onset valid bin) - AUROC(farthest valid bin).
    time_points are descending, so far = first valid, near = last valid."""
    ok = ~np.isnan(vals)
    if ok.sum() < 2:
        return float("nan")
    idx = np.where(ok)[0]
    far_i, near_i = idx[0], idx[-1]  # descending order: far first, near last
    return float(vals[near_i] - vals[far_i])


# ----------------------------------------------------------------------------
# BH-FDR
# ----------------------------------------------------------------------------
def benjamini_hochberg(pvals: np.ndarray, alpha: float = 0.05) -> tuple[np.ndarray, np.ndarray]:
    """Return (qvalues, significant_flags) via Benjamini-Hochberg step-up.
    NaN p-values are excluded from the family and returned as NaN/False."""
    p = np.asarray(pvals, dtype=float)
    ok = ~np.isnan(p)
    q = np.full(p.shape, np.nan)
    sig = np.zeros(p.shape, dtype=bool)
    m = int(ok.sum())
    if m == 0:
        return q, sig
    idx = np.where(ok)[0]
    order = idx[np.argsort(p[idx])]
    ranked = p[order]
    # BH q-values with monotone (cumulative-min from the top) enforcement
    q_raw = ranked * m / (np.arange(1, m + 1))
    q_mono = np.minimum.accumulate(q_raw[::-1])[::-1]
    q_mono = np.clip(q_mono, 0, 1)
    q[order] = q_mono
    # significance: largest k with p_(k) <= k/m*alpha
    thresh = (np.arange(1, m + 1) / m) * alpha
    passed = ranked <= thresh
    if passed.any():
        kmax = np.max(np.where(passed)[0])
        sig[order[: kmax + 1]] = True
    return q, sig


# ----------------------------------------------------------------------------
# Manifest & I/O
# ----------------------------------------------------------------------------
def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
        ).strip()
    except Exception:
        return "unknown"


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _versions() -> dict:
    import scipy
    import sklearn

    return {
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "scikit-learn": sklearn.__version__,
        "pandas": pd.__version__,
        "pymannkendall": getattr(mk, "__version__", "unknown"),
    }


def write_manifest(
    out_dir: Path,
    step: str,
    cells: list[Cell],
    extra: dict | None = None,
    hash_inputs: bool = True,
) -> None:
    """Write run_manifest.json. Timestamp is captured via `date` (Date.now is not
    used inside any workflow; here we're a plain script so os time is fine)."""
    import datetime

    inputs = []
    for c in cells:
        rec = {
            "key": c.key,
            "model": c.model,
            "setting": c.setting,
            "cohort": c.cohort,
            "pred_path": str(c.pred_path.relative_to(REPO_ROOT)),
        }
        if hash_inputs:
            rec["pred_sha256"] = _file_sha256(c.pred_path)
        inputs.append(rec)

    manifest = {
        "step": step,
        "run_time": datetime.datetime.now().isoformat(timespec="seconds"),
        "git_commit": _git_commit(),
        "sign_convention": SIGN_CONVENTION,
        "lead_time_bins_min": list(DEFAULT_TIME_POINTS_MIN),
        "window_size_min": WindowConfig().window_size_min,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "n_bootstrap": N_BOOTSTRAP,
        "bootstrap_resample_unit": (
            "highest identifiable unit: patient (subject_id) for EPIC/VitalDB, "
            "surgical case (case_id) for MOVER/SIS"
        ),
        "grid_n_cells": len(cells),
        "versions": _versions(),
        "inputs": inputs,
    }
    if extra:
        manifest.update(extra)
    (out_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2))


def df_to_md(df: pd.DataFrame, float_fmt: str = "{:.4g}") -> str:
    """Minimal, dependency-free Markdown table (avoids tabulate requirement)."""
    def fmt(v):
        if isinstance(v, float):
            if np.isnan(v):
                return "nan"
            return float_fmt.format(v)
        return str(v)

    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(fmt(row[c]) for c in cols) + " |")
    return "\n".join(lines) + "\n"
