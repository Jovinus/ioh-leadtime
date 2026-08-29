"""External-cohort validation entrypoint.

Loads a trained run directory (`outputs/runs/<name>/`) and evaluates the
best checkpoint on a *different* cohort. Produces:

  - per-minute predictions (raw + isotonic-calibrated)
  - time-window metrics + Mann-Kendall trend test
  - NNE at multiple target sensitivities
  - isotonic calibration model fit on the training cohort's **validation**
    split (loaded from `predictions/val/calibration.joblib`), applied
    to the external predictions — never re-fit on the external set.
  - calibration diagnostics (Brier, ECE) for raw vs calibrated scores

Usage (run inside `screen` for anything longer than a few minutes):

    conda run -n torch python scripts/evaluate_external.py \
        --run-dir outputs/runs/baseline_epic \
        --source vitaldb

The same script handles MOVER SIS by passing `--source mover` — the
caveat that SIS shares a site with EPIC is documented in
[HANDOFF §6.5] and the report should mention it explicitly.
"""

from __future__ import annotations

import argparse
import json
from contextlib import nullcontext
from pathlib import Path

import mlflow
import pandas as pd
import torch

from ioh_prediction.data.normalize import NormalizerStats
from ioh_prediction.data.reference_time import (
    RefTimeConfig,
    build_ref_time_manifest,
)
from ioh_prediction.evaluation import (
    BootstrapConfig,
    OnlineInferenceConfig,
    WindowConfig,
    calibration_diagnostics,
    compute_window_metrics,
    fit_isotonic,
    generate_all_plots,
    mk_for_metrics,
    nne_at_target_sensitivity,
    score_manifest,
    window_metrics_with_ci,
)
from ioh_prediction.evaluation.calibration import CalibrationModel
from ioh_prediction.models import ITEConfig, ITETransformer
from ioh_prediction.training import auto_device

REPO_ROOT = Path(__file__).resolve().parents[1]
TS_GLOB = str(REPO_ROOT / "data" / "timeseries" / "source=*" / "case_id=*" / "data.parquet")


# ---------- helpers ----------


def _load_config(run_dir: Path) -> dict:
    path = run_dir / "config_resolved.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. The run-dir must have been produced by scripts/train.py."
        )
    with path.open() as f:
        return json.load(f)


def _build_model_from_config(cfg: dict) -> ITETransformer:
    """Mirror scripts/train.py:build_model so the loaded ckpt matches.

    `num_classes` was hardcoded to 1 in an earlier sigmoid-on-single-logit
    version; the softmax refactor moved num_classes into the config (default
    2 for binary). Reading it from cfg fixes the state_dict shape mismatch
    that would otherwise raise on the classifier weights.
    """
    m = cfg["model"]
    return ITETransformer(
        ITEConfig(
            d_model=m["d_model"],
            num_layers=m["num_layers"],
            num_heads=m["num_heads"],
            dim_feedforward=m.get("dim_feedforward"),
            dropout=m["dropout"],
            num_classes=m.get("num_classes", 2),
        )
    )


def _load_train_calibration(run_dir: Path) -> CalibrationModel:
    """Load or reconstruct a validation-fitted isotonic calibrator.

    Test and external labels are never used to fit calibration. Legacy runs that
    contain only a test-fitted calibrator must be rescored/retrained or have their
    saved validation predictions used here.
    """
    cal_path = run_dir / "predictions" / "val" / "calibration.joblib"
    if cal_path.exists():
        return CalibrationModel.load(cal_path)

    val_pred_candidates = [
        run_dir / "predictions" / "val" / "predictions_raw.parquet",
        run_dir / "predictions" / "val" / "val_predictions.parquet",
        run_dir / "predictions" / "predictions_raw.parquet",
        run_dir / "predictions" / "val_predictions.parquet",
    ]
    for src in val_pred_candidates:
        if src.exists():
            print(f"Reconstructing validation-fitted calibration from {src}.")
            df = pd.read_parquet(src)
            return fit_isotonic(df["score"].to_numpy(), df["label"].to_numpy())

    raise FileNotFoundError(
        "No validation calibration source found under "
        + str(run_dir / "predictions")
        + ". A legacy test-fitted calibrator is intentionally not accepted."
    )


# ---------- main ----------


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--run-dir",
        type=Path,
        required=True,
        help="outputs/runs/<name> produced by scripts/train.py",
    )
    p.add_argument(
        "--source",
        choices=["vitaldb", "mover", "mover_epic"],
        required=True,
        help="External cohort. Different from the training cohort.",
    )
    p.add_argument(
        "--out-subdir",
        default=None,
        help="Output subdirectory inside run-dir. Defaults to "
        "`external_<source>`.",
    )
    p.add_argument(
        "--target-sensitivities",
        nargs="*",
        type=float,
        default=[0.80, 0.90],
        help="Target sensitivities for NNE reporting.",
    )
    p.add_argument("--seed", type=int, default=1004)
    p.add_argument(
        "--limit-cases",
        type=int,
        default=None,
        help="If set, score only the first N cases (smoke testing).",
    )
    p.add_argument(
        "--n-boot",
        type=int,
        default=1000,
        help="Bootstrap resamples for time-window CI (0 disables).",
    )
    p.add_argument(
        "--no-plots",
        action="store_true",
        help="Skip matplotlib plot generation.",
    )
    p.add_argument(
        "--no-mlflow",
        action="store_true",
        help="Skip MLflow logging (still writes artifacts to disk).",
    )
    p.add_argument(
        "--mlflow-tracking-uri",
        default="sqlite:///mlflow.db",
        help="MLflow tracking URI (default: sqlite:///mlflow.db). "
        "MLflow 3.x deprecates file:./mlruns and its Overview tab "
        "does not render with the file backend.",
    )
    args = p.parse_args()

    run_dir = args.run_dir.resolve()
    cfg = _load_config(run_dir)
    train_sources = tuple(cfg["data"]["sources"])
    if args.source in train_sources:
        print(
            f"WARNING: --source={args.source} is one of the training "
            f"sources {train_sources}. Results will be optimistic."
        )

    out_dir = run_dir / (args.out_subdir or f"external_{args.source}")
    out_dir.mkdir(parents=True, exist_ok=True)

    # ---- MLflow run for this external evaluation ----
    if args.no_mlflow:
        run_ctx = nullcontext()
    else:
        mlflow.set_tracking_uri(args.mlflow_tracking_uri)
        mlflow.set_experiment(cfg["experiment"]["name"])
        train_run_name = cfg["experiment"].get("run_name") or "anon"
        run_name = f"{train_run_name}_external_{args.source}"
        run_ctx = mlflow.start_run(run_name=run_name)

    with run_ctx:
        if not args.no_mlflow:
            mlflow.log_params(
                {
                    "kind": "external_validation",
                    "external_source": args.source,
                    "train_sources": ",".join(train_sources),
                    "run_dir": str(run_dir),
                    "n_boot": args.n_boot,
                    "limit_cases": args.limit_cases or 0,
                    "seed": args.seed,
                    "window_min": cfg["data"]["window_min"],
                    "max_seq_len": cfg["data"]["max_seq_len"],
                    "d_model": cfg["model"]["d_model"],
                    "num_layers": cfg["model"]["num_layers"],
                }
            )
        _run_eval(args, cfg, run_dir, out_dir, train_sources)


def _run_eval(args, cfg: dict, run_dir: Path, out_dir: Path, train_sources: tuple) -> None:
    """Eval body — runs inside the active MLflow run (or nullcontext)."""
    # 1) Manifest for the EXTERNAL cohort (own positives for ref-time match)
    rt_cfg = RefTimeConfig(
        pos_min_pre_onset_min=cfg["data"]["pos_min_pre_onset_min"],
        neg_min_pre_onset_min=cfg["data"]["neg_min_pre_onset_min"],
        pos_gap_min=int(cfg["data"].get("pos_gap_min", 0)),
        seed=args.seed,
    )
    manifest, qc = build_ref_time_manifest(
        TS_GLOB, sources=(args.source,), config=rt_cfg
    )
    if args.limit_cases is not None:
        manifest = manifest.sample(
            n=min(args.limit_cases, len(manifest)),
            random_state=args.seed,
        ).reset_index(drop=True)
    print(
        f"external manifest: {len(manifest):,} cases (positives={int(manifest['label'].sum()):,})"
    )
    manifest.to_csv(out_dir / "manifest.csv", index=False)
    qc.to_csv(out_dir / "manifest.qc.csv", index=False)

    # 2) Load model + normalizer FROM THE TRAINING RUN (never refit)
    normalizer = NormalizerStats.load(run_dir / "normalizer.parquet")
    model = _build_model_from_config(cfg)
    ckpt_path = run_dir / cfg["paths"].get("ckpt_subdir", "ckpts") / "best.pt"
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    model.load_state_dict(ckpt["model_state"])
    device = auto_device(cfg["train"].get("device"))
    model = model.to(device).eval()
    print(
        f"loaded ckpt @ epoch={ckpt['epoch']}  "
        f"train-cohort val_auroc={ckpt['metrics']['val_auroc']:.4f}"
    )
    print(f"device: {device}")

    # 3) Score every minute of every external case
    predictions = score_manifest(
        model,
        normalizer,
        manifest,
        device,
        config=OnlineInferenceConfig(
            window_min=cfg["data"]["window_min"],
            max_seq_len=cfg["data"]["max_seq_len"],
            batch_size=64,
        ),
        progress_desc=f"external/{args.source}",
    )
    raw_path = out_dir / "predictions_raw.parquet"
    predictions.to_parquet(raw_path, index=False)
    print(f"saved {len(predictions):,} predictions -> {raw_path}")

    # 4) Time-window metrics + Mann-Kendall (with bootstrap CIs if enabled)
    window = compute_window_metrics(
        predictions, WindowConfig(window_size_min=2, min_samples_per_window=30)
    )
    window.to_csv(out_dir / "window_metrics.csv", index=False)
    print("\nTime-window metrics:")
    print(window.round(3).to_string(index=False))

    if args.n_boot > 0:
        window_ci = window_metrics_with_ci(
            predictions,
            BootstrapConfig(n_boot=args.n_boot, seed=args.seed),
        )
        window_ci.to_csv(out_dir / "window_metrics_ci.csv", index=False)
        print(f"\nWindow metrics with {args.n_boot}-sample bootstrap CI saved.")

    mk = mk_for_metrics(window)
    mk.to_csv(out_dir / "mann_kendall.csv", index=False)
    print("\nMann-Kendall trend test:")
    print(mk[["metric", "tau", "p_value", "trend_direction", "significant"]].round(4).to_string(index=False))

    # 5) NNE at multiple target sensitivities
    nne_rows = []
    for t_sens in args.target_sensitivities:
        nne = nne_at_target_sensitivity(
            predictions["score"].to_numpy(),
            predictions["label"].to_numpy(),
            target_sensitivity=t_sens,
        )
        nne_rows.append({"target_sensitivity": t_sens, **nne})
    nne_df = pd.DataFrame(nne_rows)
    nne_df.to_csv(out_dir / "nne.csv", index=False)
    print("\nNNE table:")
    print(nne_df.round(4).to_string(index=False))

    # 6) Isotonic calibration: load validation-fit calibrator, apply to external
    calibration = _load_train_calibration(run_dir)
    calibration.save(out_dir / "calibration.joblib")
    predictions_cal = predictions.copy()
    predictions_cal["score"] = calibration.apply(predictions["score"].to_numpy())
    cal_path = out_dir / "predictions_calibrated.parquet"
    predictions_cal.to_parquet(cal_path, index=False)

    raw_diag = calibration_diagnostics(
        predictions["score"].to_numpy(), predictions["label"].to_numpy()
    )
    cal_diag = calibration_diagnostics(
        predictions_cal["score"].to_numpy(), predictions_cal["label"].to_numpy()
    )
    with (out_dir / "calibration_diagnostics.json").open("w") as f:
        json.dump(
            {"raw": raw_diag, "calibrated": cal_diag, "fit_n": calibration.fit_n},
            f,
            indent=2,
        )
    print("\nCalibration (raw -> isotonic fit on train test split -> external):")
    print(f"  brier:  {raw_diag['brier']:.4f} -> {cal_diag['brier']:.4f}")
    print(f"  ECE:    {raw_diag['ece']:.4f} -> {cal_diag['ece']:.4f}")

    # 7) Plots
    plots: list = []
    if not args.no_plots:
        plots = generate_all_plots(out_dir, title_prefix=f"{args.source}")
        print(f"\nPlots: {[str(p.relative_to(out_dir)) for p in plots]}")

    # 8) MLflow logging (scalars + artifacts) — to the active run if any
    if mlflow.active_run() is not None:
        metrics_to_log: dict = {
            "ext_brier_raw": raw_diag["brier"],
            "ext_ece_raw": raw_diag["ece"],
            "ext_brier_calibrated": cal_diag["brier"],
            "ext_ece_calibrated": cal_diag["ece"],
            "ext_n_predictions": len(predictions),
            "ext_n_cases": int(predictions["case_id"].nunique()),
            "ext_n_positive_cases": int(manifest["label"].sum()),
        }
        if not window.empty:
            t0 = window.loc[window["time_window_min"].idxmin()]
            metrics_to_log["ext_auroc_at_0min"] = float(t0["auroc"])
            metrics_to_log["ext_auprc_at_0min"] = float(t0["auprc"])
            metrics_to_log["ext_ppv050_at_0min"] = float(t0["ppv_050"])
        for _, mk_row in mk.iterrows():
            metric = mk_row["metric"]
            metrics_to_log[f"ext_mk_{metric}_tau"] = float(mk_row["tau"])
            metrics_to_log[f"ext_mk_{metric}_p"] = float(mk_row["p_value"])
        for _, row in nne_df.iterrows():
            sens = float(row["target_sensitivity"])
            metrics_to_log[f"ext_nne_at_{int(sens*100):d}sens"] = float(row["nne"])
            metrics_to_log[f"ext_ppv_at_{int(sens*100):d}sens"] = float(row["ppv"])
        # Drop NaN metrics (log_metrics rejects them).
        mlflow.log_metrics({k: v for k, v in metrics_to_log.items() if v == v})

        # Artifacts: CSVs / JSON / model / plots
        for fname in [
            "manifest.csv",
            "manifest.qc.csv",
            "window_metrics.csv",
            "window_metrics_ci.csv",
            "mann_kendall.csv",
            "nne.csv",
            "calibration_diagnostics.json",
            "calibration.joblib",
        ]:
            p = out_dir / fname
            if p.exists():
                mlflow.log_artifact(str(p), artifact_path=f"external_{args.source}")
        # Predictions parquet is large; log under same subfolder.
        for fname in ["predictions_raw.parquet", "predictions_calibrated.parquet"]:
            p = out_dir / fname
            if p.exists():
                mlflow.log_artifact(str(p), artifact_path=f"external_{args.source}/predictions")
        for p in plots:
            mlflow.log_artifact(str(p), artifact_path=f"external_{args.source}/plots")

    print(f"\nAll artifacts: {out_dir}")


if __name__ == "__main__":
    main()
