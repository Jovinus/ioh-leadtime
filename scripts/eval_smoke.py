"""End-to-end online-simulation smoke test.

Loads the smoke-trained checkpoint, scores a small subset of VitalDB val
cases at every minute, then runs:
  - time-window metrics (AUROC/PPV per minute-to-event bin)
  - Mann-Kendall trend test across those windows
  - NNE @ 80% sensitivity on the pooled scores
  - isotonic calibration diagnostics
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import torch

from ioh_prediction.data.normalize import fit_normalizer
from ioh_prediction.data.reference_time import build_ref_time_manifest
from ioh_prediction.data.splits import stratified_subject_split
from ioh_prediction.evaluation import (
    OnlineInferenceConfig,
    WindowConfig,
    alert_burden_curve,
    calibration_diagnostics,
    compute_window_metrics,
    fit_isotonic,
    mk_for_metrics,
    nne_at_target_sensitivity,
    score_manifest,
)
from ioh_prediction.models import ITEConfig, ITETransformer
from ioh_prediction.training import auto_device

REPO_ROOT = Path(__file__).resolve().parents[1]
TS_GLOB = str(REPO_ROOT / "data" / "timeseries" / "source=*" / "case_id=*" / "data.parquet")
CASES_PARQUET = str(REPO_ROOT / "data" / "cases.parquet")
CKPT_PATH = REPO_ROOT / "outputs" / "ckpts" / "smoke" / "best.pt"
N_CASES_TO_SCORE = 50   # subset for smoke timing


def main() -> None:
    print(f"Loading checkpoint: {CKPT_PATH}")
    ckpt = torch.load(CKPT_PATH, map_location="cpu", weights_only=False)
    print(f"  ckpt epoch={ckpt['epoch']}, val_auroc={ckpt['metrics']['val_auroc']:.4f}")

    manifest, _ = build_ref_time_manifest(TS_GLOB, sources=("vitaldb",))
    train_m, val_m = stratified_subject_split(manifest, val_frac=0.2, seed=1004)
    # Same normalizer as training (refit on train cases only — for online inference)
    normalizer = fit_normalizer(
        TS_GLOB,
        case_ids=train_m["case_id"].tolist(),
        cases_parquet=CASES_PARQUET,
    )

    device = auto_device()
    print(f"Device: {device}")
    model = ITETransformer(ITEConfig(num_classes=1, d_model=64, num_layers=2))
    model.load_state_dict(ckpt["model_state"])
    model = model.to(device).eval()

    # Subset val cases for smoke timing.
    val_subset = val_m.sample(n=min(N_CASES_TO_SCORE, len(val_m)), random_state=1004).reset_index(drop=True)
    print(f"Scoring {len(val_subset)} val cases...")

    predictions = score_manifest(
        model,
        normalizer,
        val_subset,
        device,
        config=OnlineInferenceConfig(window_min=120, max_seq_len=2048, batch_size=64),
        progress_desc="smoke-val",
    )
    print(f"  produced {len(predictions):,} per-minute scores across {predictions['case_id'].nunique()} cases")

    out_dir = REPO_ROOT / "outputs" / "eval_smoke"
    out_dir.mkdir(parents=True, exist_ok=True)
    predictions.to_parquet(out_dir / "predictions.parquet", index=False)

    # ---- Time-window metrics ----
    window = compute_window_metrics(predictions, WindowConfig(window_size_min=2, min_samples_per_window=10))
    print()
    print("Time-window metrics:")
    print(window.round(3).to_string(index=False))

    # ---- Mann-Kendall ----
    print()
    print("Mann-Kendall trend test:")
    mk = mk_for_metrics(window)
    print(mk[["metric", "tau", "p_value", "trend_direction", "significant"]].round(4).to_string(index=False))

    # ---- NNE / alert burden ----
    print()
    print("NNE @ 80% sensitivity (pooled across all bins):")
    nne = nne_at_target_sensitivity(
        predictions["score"].to_numpy(),
        predictions["label"].to_numpy(),
        target_sensitivity=0.80,
    )
    print(f"  threshold={nne['threshold']:.4f}  sens={nne['sensitivity']:.3f}  ppv={nne['ppv']:.3f}  NNE={nne['nne']:.2f}")

    # ---- Calibration ----
    print()
    print("Calibration diagnostics (raw scores):")
    raw_diag = calibration_diagnostics(
        predictions["score"].to_numpy(), predictions["label"].to_numpy(),
    )
    print(f"  brier={raw_diag['brier']:.4f}  ece={raw_diag['ece']:.4f}")

    # Fit isotonic on train half? For smoke we fit and apply on the same
    # set — not a clean calibration claim, just a smoke check.
    iso = fit_isotonic(predictions["score"].to_numpy(), predictions["label"].to_numpy())
    calibrated = iso.apply(predictions["score"].to_numpy())
    iso_diag = calibration_diagnostics(calibrated, predictions["label"].to_numpy())
    print(f"  after-isotonic brier={iso_diag['brier']:.4f}  ece={iso_diag['ece']:.4f}")

    window.to_csv(out_dir / "window_metrics.csv", index=False)
    mk.to_csv(out_dir / "mk_test.csv", index=False)
    print()
    print(f"Artifacts written to {out_dir}")


if __name__ == "__main__":
    main()
