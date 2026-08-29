"""Inspect whether the AUROC dip at 25–30 min before onset is a
cohort-selection artefact.

For each cohort, we bin per-minute predictions by `t_to_event` (the
same 5-min spacing Table 3 uses), then for each bin tabulate:
  - n_total, n_pos, n_neg
  - prevalence
  - ref_time_min distribution of the cases that contribute to the bin
    (a sample's ref_time tells us 'how far this minute was into the
    case before the event/pseudo-event')
  - case-length distribution

If a sudden distribution shift between bin t=30 and bin t=25 lines up
with the AUROC dip, the dip is sample bias.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from ioh_prediction.evaluation.time_window_metrics import DEFAULT_TIME_POINTS_MIN

WINDOW_SIZE_MIN = 2


def _bin_label(tp: int, half_w: float) -> str:
    return f"{tp:3d} [{tp - half_w:.0f},{tp + half_w:.0f})"


def analyze_cohort(name: str, pred_path: Path, manifest_path: Path | None) -> pd.DataFrame:
    preds = pd.read_parquet(pred_path)
    # join ref_time_min and case_length_min from the manifest so we can
    # see how each bin's contributors are distributed.
    join_cols = []
    if manifest_path and manifest_path.exists():
        manifest = pd.read_csv(manifest_path)
        keep = [c for c in ("case_id", "ref_time_min", "case_length_min", "first_onset_min", "label")
                if c in manifest.columns]
        manifest = manifest[keep].drop_duplicates(subset="case_id")
        # the prediction parquet already carries `label`, so we drop it
        # from the manifest side to avoid collisions
        manifest = manifest.drop(columns=[c for c in ("label",) if c in manifest.columns])
        preds = preds.merge(manifest, on="case_id", how="left")
        join_cols = [c for c in ("ref_time_min", "case_length_min", "first_onset_min")
                     if c in preds.columns]

    half_w = WINDOW_SIZE_MIN / 2.0
    rows: list[dict] = []
    for tp in DEFAULT_TIME_POINTS_MIN:
        lo, hi = tp - half_w, tp + half_w
        sub = preds[(preds["t_to_event"] >= lo) & (preds["t_to_event"] < hi)]
        if sub.empty:
            continue
        n_total = len(sub)
        n_pos = int((sub["label"] == 1).sum())
        n_neg = n_total - n_pos
        row: dict = {
            "t_to_event": tp,
            "n_total": n_total,
            "n_pos": n_pos,
            "n_neg": n_neg,
            "prev (n_pos / n_total)": round(n_pos / n_total, 3) if n_total else float("nan"),
            "uniq_cases_in_bin": int(sub["case_id"].nunique()),
        }
        for col in join_cols:
            vals = pd.to_numeric(sub[col], errors="coerce").dropna()
            if vals.empty:
                row[f"{col}_p50"] = float("nan")
                row[f"{col}_p25_p75"] = "—"
                continue
            row[f"{col}_p50"] = round(float(vals.median()), 1)
            row[f"{col}_p25_p75"] = (
                f"[{float(vals.quantile(0.25)):.0f}, {float(vals.quantile(0.75)):.0f}]"
            )
        rows.append(row)
    out = pd.DataFrame(rows)
    out["cohort"] = name
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--run-dir", type=Path, required=True)
    p.add_argument(
        "--out-csv",
        type=Path,
        default=Path("reports/tables/bin_selection_bias.csv"),
    )
    args = p.parse_args()

    sources: list[tuple[str, Path, Path | None]] = []
    # EPIC val (legacy or 3-way)
    legacy_val = args.run_dir / "predictions" / "predictions_raw.parquet"
    new_val = args.run_dir / "predictions" / "val" / "predictions_raw.parquet"
    new_test = args.run_dir / "predictions" / "test" / "predictions_raw.parquet"
    if new_val.exists():
        sources.append(("EPIC val", new_val, args.run_dir / "manifest.csv"))
    elif legacy_val.exists():
        sources.append(("EPIC val", legacy_val, args.run_dir / "manifest.csv"))
    if new_test.exists():
        sources.append(("EPIC test", new_test, args.run_dir / "test_manifest.csv"))
    for ext, label in [("vitaldb", "VitalDB"), ("mover", "MOVER SIS")]:
        d = args.run_dir / f"external_{ext}"
        if (d / "predictions_raw.parquet").exists():
            sources.append((label, d / "predictions_raw.parquet", d / "manifest.csv"))

    frames: list[pd.DataFrame] = []
    for name, pp, mp in sources:
        print(f"\n=== {name} ===")
        df = analyze_cohort(name, pp, mp)
        # Compact, readable per-cohort print
        cols = [
            "t_to_event", "n_total", "n_pos", "n_neg",
            "prev (n_pos / n_total)", "uniq_cases_in_bin",
        ]
        if "ref_time_min_p50" in df.columns:
            cols += ["ref_time_min_p50", "ref_time_min_p25_p75"]
        if "case_length_min_p50" in df.columns:
            cols += ["case_length_min_p50"]
        print(df[cols].to_string(index=False))
        frames.append(df)

    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if not combined.empty:
        combined.to_csv(args.out_csv, index=False)
        print(f"\nSaved: {args.out_csv}")


if __name__ == "__main__":
    main()
