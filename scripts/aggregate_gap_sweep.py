"""Aggregate clinical-faithfulness metrics across a gap sweep.

Reads each gap run-dir's EPIC **test split** artefacts
(`predictions/test/window_metrics_ci.csv`, `mann_kendall.csv`,
`calibration_diagnostics.json`) and emits:

  - `gap_sweep_summary.csv` — one row per (gap, t_to_event_bin) with
    AUROC/AUPRC/PPV/sensitivity (+ CI when available).
  - `gap_sweep_matched.csv` — one row per gap at the bin
    `t_to_event = gap` (the model's training horizon). Carries MK tau
    and pre/post calibration Brier/ECE too.
  - `auroc_trajectory_by_gap.png` — overlay of AUROC trajectories,
    one line per gap.
  - `matched_horizon_auroc_vs_gap.png` — the headline "lead-time
    degradation" curve.

Val split is intentionally excluded (early-stop bias); externals are
out of scope per the gap-sweep memory.

Usage:
    python scripts/aggregate_gap_sweep.py \
        --runs-glob 'outputs/runs/gap*' \
        --out outputs/gap_sweep_summary
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


_GAP_RX = re.compile(r"gap(\d+)$")


def _gap_from_run_dir(run_dir: Path) -> int | None:
    m = _GAP_RX.search(run_dir.name)
    if m:
        return int(m.group(1))
    cfg_path = run_dir / "config_resolved.json"
    if cfg_path.exists():
        cfg = json.loads(cfg_path.read_text())
        g = cfg.get("data", {}).get("pos_gap_min")
        if g is not None:
            return int(g)
    return None


def _load_one(run_dir: Path) -> tuple[pd.DataFrame, dict] | None:
    test_dir = run_dir / "predictions" / "test"
    wm_path = test_dir / "window_metrics_ci.csv"
    if not wm_path.exists():
        wm_path = test_dir / "window_metrics.csv"
    if not wm_path.exists():
        print(f"  skip {run_dir.name}: missing window_metrics in {test_dir}")
        return None
    wm = pd.read_csv(wm_path)

    mk_path = test_dir / "mann_kendall.csv"
    mk = pd.read_csv(mk_path) if mk_path.exists() else pd.DataFrame()

    diag_path = test_dir / "calibration_diagnostics.json"
    diag = json.loads(diag_path.read_text()) if diag_path.exists() else {}

    return wm, {"mk": mk, "diag": diag}


def _matched_row(wm: pd.DataFrame, gap: int) -> dict:
    if wm.empty or "time_window_min" not in wm.columns:
        return {}
    idx = (wm["time_window_min"] - gap).abs().idxmin()
    row = wm.loc[idx].to_dict()
    row["t_to_event_matched_min"] = float(row.get("time_window_min", float("nan")))
    return row


def _mk_auroc(mk: pd.DataFrame) -> dict:
    if mk.empty:
        return {}
    sub = mk.loc[mk["metric"] == "auroc"]
    if sub.empty:
        return {}
    r = sub.iloc[0]
    return {
        "mk_auroc_tau": float(r["tau"]),
        "mk_auroc_p": float(r["p_value"]),
        "mk_auroc_significant": bool(r.get("significant", False)),
    }


def _calibration_summary(diag: dict) -> dict:
    out = {}
    if "raw" in diag:
        out["brier_raw"] = float(diag["raw"]["brier"])
        out["ece_raw"] = float(diag["raw"]["ece"])
    if "calibrated" in diag:
        out["brier_calibrated"] = float(diag["calibrated"]["brier"])
        out["ece_calibrated"] = float(diag["calibrated"]["ece"])
    if "fit_n" in diag:
        out["calibration_fit_n"] = int(diag["fit_n"])
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--runs-glob",
        required=True,
        help="Glob for run dirs, e.g. 'outputs/runs/gap*'",
    )
    p.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output directory for summary CSVs + plots.",
    )
    args = p.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)

    candidates = sorted(Path().glob(args.runs_glob))
    if not candidates:
        raise SystemExit(f"no run dirs matched glob: {args.runs_glob}")

    long_rows: list[pd.DataFrame] = []
    matched_rows: list[dict] = []
    trajectories: dict[int, pd.DataFrame] = {}
    for run_dir in candidates:
        if not run_dir.is_dir():
            continue
        gap = _gap_from_run_dir(run_dir)
        if gap is None:
            print(f"  skip {run_dir}: cannot infer gap from name or config")
            continue
        loaded = _load_one(run_dir)
        if loaded is None:
            continue
        wm, extras = loaded
        wm = wm.copy()
        wm.insert(0, "gap_min", gap)
        wm.insert(1, "run_dir", str(run_dir))
        long_rows.append(wm)
        trajectories[gap] = wm

        matched = _matched_row(wm, gap)
        matched.update(_mk_auroc(extras["mk"]))
        matched.update(_calibration_summary(extras["diag"]))
        matched["gap_min"] = gap
        matched["run_dir"] = str(run_dir)
        matched_rows.append(matched)
        print(
            f"  gap={gap:>2}  run_dir={run_dir.name}  "
            f"matched AUROC@t={matched.get('time_window_min', float('nan'))}: "
            f"{matched.get('auroc', float('nan')):.3f}"
        )

    if not long_rows:
        raise SystemExit("no usable run dirs after filtering")

    long_df = pd.concat(long_rows, ignore_index=True)
    long_path = args.out / "gap_sweep_summary.csv"
    long_df.to_csv(long_path, index=False)
    print(f"\nwrote {long_path}  ({len(long_df):,} rows)")

    matched_df = pd.DataFrame(matched_rows).sort_values("gap_min").reset_index(drop=True)
    front_cols = [
        "gap_min", "t_to_event_matched_min", "auroc", "auprc",
        "ppv_050", "sensitivity_050",
        "mk_auroc_tau", "mk_auroc_p",
        "brier_raw", "brier_calibrated", "ece_raw", "ece_calibrated",
    ]
    keep = [c for c in front_cols if c in matched_df.columns]
    matched_df = matched_df[keep + [c for c in matched_df.columns if c not in keep]]
    matched_path = args.out / "gap_sweep_matched.csv"
    matched_df.to_csv(matched_path, index=False)
    print(f"wrote {matched_path}  ({len(matched_df):,} rows)")

    fig, ax = plt.subplots(figsize=(8, 5))
    for gap, wm in sorted(trajectories.items()):
        d = wm.sort_values("time_window_min", ascending=False)
        ax.plot(d["time_window_min"], d["auroc"], marker="o", label=f"gap={gap} min")
    ax.axhline(0.5, color="grey", linestyle="--", linewidth=0.8, label="chance")
    ax.invert_xaxis()
    ax.set_xlabel("Minutes before event onset (t_to_event)")
    ax.set_ylabel("AUROC")
    ax.set_ylim(0.4, 1.0)
    ax.set_title("AUROC trajectory by training gap (EPIC test split)")
    ax.legend(loc="lower right", fontsize=9)
    fig.tight_layout()
    traj_path = args.out / "auroc_trajectory_by_gap.png"
    fig.savefig(traj_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {traj_path}")

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(matched_df["gap_min"], matched_df["auroc"], marker="o", color="C0")
    if {"auroc_ci_lo", "auroc_ci_hi"}.issubset(matched_df.columns):
        ax.fill_between(
            matched_df["gap_min"],
            matched_df["auroc_ci_lo"],
            matched_df["auroc_ci_hi"],
            alpha=0.2, color="C0", label="95% CI",
        )
        ax.legend(loc="lower left")
    ax.axhline(0.5, color="grey", linestyle="--", linewidth=0.8)
    ax.set_xlabel("Training gap (minutes before onset)")
    ax.set_ylabel("AUROC at matched horizon")
    ax.set_ylim(0.4, 1.0)
    ax.set_title("Lead-time degradation (EPIC test split)")
    fig.tight_layout()
    matched_plot_path = args.out / "matched_horizon_auroc_vs_gap.png"
    fig.savefig(matched_plot_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {matched_plot_path}")


if __name__ == "__main__":
    main()
