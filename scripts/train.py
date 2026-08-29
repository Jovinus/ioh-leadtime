"""End-to-end training entrypoint for IOH prediction.

Loads a YAML experiment config (see `configs/experiment/`), builds the
ref-time-matched manifest, splits subject-aware, fits a train-cohort
normalizer, instantiates the ITE Transformer, and hands off to the
trainer. After training, scores the held-out val split with the best
checkpoint and prints time-window / Mann-Kendall / NNE summaries.

Usage (run inside `screen` for anything longer than a few minutes):

    conda run -n torch python scripts/train.py \
        --config configs/experiment/baseline_epic.yaml \
        [--override train.batch_size=16 ...]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import mlflow
import torch
import yaml
from torch.utils.data import DataLoader

from ioh_prediction.data.collate import CollateConfig, RefTimeCollate
from ioh_prediction.data.dataset import IOHRefTimeDataset
from ioh_prediction.data.normalize import fit_normalizer
from ioh_prediction.data.reference_time import (
    RefTimeConfig,
    build_ref_time_manifest,
)
from ioh_prediction.data.splits import (
    stratified_subject_split,
    stratified_subject_split_3way,
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
from ioh_prediction.models import ITEConfig, ITETransformer
from ioh_prediction.training import Trainer, TrainerConfig, auto_device

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TS_GLOB = str(
    REPO_ROOT / "data" / "timeseries" / "source=*" / "case_id=*" / "data.parquet"
)
DEFAULT_CASES_PARQUET = str(REPO_ROOT / "data" / "cases.parquet")


# ---------- config helpers ----------


def _coerce(value: str) -> Any:
    """Coerce a string into bool/int/float/None/str — for `--override` flags."""
    low = value.lower()
    if low in {"true", "false"}:
        return low == "true"
    if low in {"null", "none"}:
        return None
    try:
        if "." in value or "e" in low:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _apply_overrides(cfg: dict, overrides: list[str]) -> dict:
    """Apply dotted `key.path=value` overrides into a nested dict."""
    for spec in overrides or []:
        if "=" not in spec:
            raise ValueError(f"override must be key=value, got {spec!r}")
        key, value = spec.split("=", 1)
        parts = key.split(".")
        cur = cfg
        for p in parts[:-1]:
            if p not in cur or not isinstance(cur[p], dict):
                cur[p] = {}
            cur = cur[p]
        cur[parts[-1]] = _coerce(value)
    return cfg


def load_config(path: Path, overrides: list[str]) -> dict:
    with path.open() as f:
        cfg = yaml.safe_load(f)
    return _apply_overrides(cfg, overrides)


# ---------- builders ----------


def build_manifest_and_normalizer(cfg: dict, paths: dict) -> tuple:
    sources = tuple(cfg["data"]["sources"])
    rt_cfg = RefTimeConfig(
        pos_min_pre_onset_min=cfg["data"]["pos_min_pre_onset_min"],
        neg_min_pre_onset_min=cfg["data"]["neg_min_pre_onset_min"],
        pos_gap_min=int(cfg["data"].get("pos_gap_min", 0)),
        seed=cfg["data"]["seed"],
    )
    manifest, qc = build_ref_time_manifest(DEFAULT_TS_GLOB, sources=sources, config=rt_cfg)

    limit = cfg["data"].get("limit_cases")
    if limit and limit > 0 and len(manifest) > limit:
        manifest = manifest.sample(n=int(limit), random_state=cfg["data"]["seed"]).reset_index(drop=True)
        print(f"limit_cases={limit}: subsampled manifest to {len(manifest):,} rows")

    test_frac = cfg["data"].get("test_frac", 0.0) or 0.0
    if test_frac > 0:
        train_m, val_m, test_m = stratified_subject_split_3way(
            manifest,
            val_frac=cfg["data"]["val_frac"],
            test_frac=test_frac,
            seed=cfg["data"]["seed"],
        )
        print(
            f"manifest={len(manifest):,}  train={len(train_m):,}  "
            f"val={len(val_m):,}  test={len(test_m):,}  sources={sources}"
        )
    else:
        train_m, val_m = stratified_subject_split(
            manifest,
            val_frac=cfg["data"]["val_frac"],
            seed=cfg["data"]["seed"],
        )
        test_m = None
        print(
            f"manifest={len(manifest):,}  train={len(train_m):,}  "
            f"val={len(val_m):,}  test=(disabled)  sources={sources}"
        )

    normalizer = fit_normalizer(
        DEFAULT_TS_GLOB,
        case_ids=train_m["case_id"].tolist(),
        cases_parquet=DEFAULT_CASES_PARQUET,
    )
    Path(paths["normalizer"]).parent.mkdir(parents=True, exist_ok=True)
    normalizer.save(paths["normalizer"])
    Path(paths["manifest"]).parent.mkdir(parents=True, exist_ok=True)
    manifest.to_csv(paths["manifest"], index=False)
    qc.to_csv(Path(paths["manifest"]).with_suffix(".qc.csv"), index=False)
    if test_m is not None:
        test_path = Path(paths["manifest"]).with_name("test_manifest.csv")
        test_m.to_csv(test_path, index=False)

    return manifest, train_m, val_m, test_m, normalizer, qc


def build_loaders(cfg: dict, train_m, val_m, normalizer):
    collate = RefTimeCollate(normalizer, CollateConfig(max_seq_len=cfg["data"]["max_seq_len"]))
    train_ds = IOHRefTimeDataset(train_m, window_min=cfg["data"]["window_min"])
    val_ds = IOHRefTimeDataset(val_m, window_min=cfg["data"]["window_min"])
    common = dict(
        collate_fn=collate,
        num_workers=cfg["train"]["num_workers"],
        persistent_workers=cfg["train"]["num_workers"] > 0,
    )
    train_loader = DataLoader(
        train_ds, batch_size=cfg["train"]["batch_size"], shuffle=True, **common
    )
    val_loader = DataLoader(
        val_ds, batch_size=max(cfg["train"]["batch_size"], 32), shuffle=False, **common
    )
    return train_loader, val_loader, collate


def build_model(cfg: dict) -> ITETransformer:
    m = cfg["model"]
    ite_cfg = ITEConfig(
        d_model=m["d_model"],
        num_layers=m["num_layers"],
        num_heads=m["num_heads"],
        dim_feedforward=m.get("dim_feedforward"),
        dropout=m["dropout"],
        num_classes=m.get("num_classes", 2),
    )
    return ITETransformer(ite_cfg)


# ---------- post-train eval ----------


def post_train_eval(
    model: ITETransformer,
    normalizer,
    val_m,
    device: torch.device,
    paths: dict,
    window_min: int,
    max_seq_len: int,
    n_boot: int = 1000,
    make_plots: bool = True,
    log_mlflow: bool = True,
    split_name: str = "val",   # "val" or "test"
    calibrator=None,
    fit_calibration: bool = False,
):
    model.eval()
    predictions = score_manifest(
        model,
        normalizer,
        val_m,
        device,
        config=OnlineInferenceConfig(
            window_min=window_min,
            max_seq_len=max_seq_len,
            batch_size=64,
        ),
        progress_desc=f"post-eval/{split_name}",
    )
    pred_dir = Path(paths["predictions"]) / split_name
    pred_dir.mkdir(parents=True, exist_ok=True)
    # Save under both legacy (`val_predictions.parquet`) and standard
    # (`predictions_raw.parquet`) names so generate_all_plots and
    # downstream external eval reads cleanly. Both files are written
    # under the split's own subdir.
    predictions.to_parquet(pred_dir / "val_predictions.parquet", index=False)
    predictions.to_parquet(pred_dir / "predictions_raw.parquet", index=False)
    print(f"Saved {len(predictions):,} per-minute predictions to {pred_dir}")

    window = compute_window_metrics(predictions, WindowConfig(window_size_min=2, min_samples_per_window=30))
    window.to_csv(pred_dir / "window_metrics.csv", index=False)
    print("\nTime-window metrics (val cohort):")
    print(window.round(3).to_string(index=False))

    window_ci = None
    if n_boot > 0:
        window_ci = window_metrics_with_ci(predictions, BootstrapConfig(n_boot=n_boot))
        window_ci.to_csv(pred_dir / "window_metrics_ci.csv", index=False)
        print(f"  bootstrap CI ({n_boot} resamples) saved to window_metrics_ci.csv")

    mk = mk_for_metrics(window)
    mk.to_csv(pred_dir / "mann_kendall.csv", index=False)
    print("\nMann-Kendall trend test:")
    print(mk[["metric", "tau", "p_value", "trend_direction", "significant"]].round(4).to_string(index=False))

    nne = nne_at_target_sensitivity(
        predictions["score"].to_numpy(),
        predictions["label"].to_numpy(),
        target_sensitivity=0.80,
    )
    print(f"\nNNE @ 80% sensitivity: threshold={nne['threshold']:.4f}  ppv={nne['ppv']:.3f}  NNE={nne['nne']:.2f}")

    raw_diag = calibration_diagnostics(
        predictions["score"].to_numpy(), predictions["label"].to_numpy()
    )
    diag_payload: dict = {"raw": raw_diag}
    cal_diag: dict | None = None
    # Calibration is a fitted model component: fit it on validation only,
    # then carry it unchanged to test/external cohorts. Fitting on test and
    # evaluating the calibrated score on that same test set is optimistic even
    # when the prediction model itself was not selected on test.
    if fit_calibration:
        scores_np = predictions["score"].to_numpy()
        labels_np = predictions["label"].to_numpy()
        calibrator = fit_isotonic(scores_np, labels_np)
        calibrator.save(pred_dir / "calibration.joblib")
    if calibrator is not None:
        scores_np = predictions["score"].to_numpy()
        labels_np = predictions["label"].to_numpy()
        cal_scores = calibrator.apply(scores_np)
        predictions_cal = predictions.copy()
        predictions_cal["score"] = cal_scores
        predictions_cal.to_parquet(pred_dir / "predictions_calibrated.parquet", index=False)
        cal_diag = calibration_diagnostics(cal_scores, labels_np)
        diag_payload["calibrated"] = cal_diag
        diag_payload["fit_n"] = calibrator.fit_n
        diag_payload["fit_split"] = "validation"
        print(f"\nCalibration (raw -> validation-fitted isotonic -> {split_name}):")
        print(f"  brier:  {raw_diag['brier']:.4f} -> {cal_diag['brier']:.4f}")
        print(f"  ECE:    {raw_diag['ece']:.4f} -> {cal_diag['ece']:.4f}")

    with (pred_dir / "calibration_diagnostics.json").open("w") as f:
        json.dump(diag_payload, f, indent=2)

    plots = []
    if make_plots:
        plots = generate_all_plots(pred_dir, title_prefix=f"train-{split_name}")
        print(f"Plots: {[p.name for p in plots]}")

    # ---- MLflow: log eval scalars and artifacts to the active run ----
    if log_mlflow and mlflow.active_run() is not None:
        # Per-split metric / artifact namespaces so val and test don't
        # clobber each other in MLflow's metric panel.
        m_prefix = f"{split_name}_eval"
        a_prefix = f"post_eval/{split_name}"
        eval_metrics = {
            f"{m_prefix}_brier_raw": raw_diag["brier"],
            f"{m_prefix}_ece_raw": raw_diag["ece"],
            f"{m_prefix}_nne80_threshold": nne["threshold"],
            f"{m_prefix}_nne80_ppv": nne["ppv"],
            f"{m_prefix}_nne80": nne["nne"],
        }
        if cal_diag is not None:
            eval_metrics[f"{m_prefix}_brier_calibrated"] = cal_diag["brier"]
            eval_metrics[f"{m_prefix}_ece_calibrated"] = cal_diag["ece"]
        if not window.empty:
            t0_row = window.loc[window["time_window_min"].idxmin()]
            eval_metrics[f"{m_prefix}_auroc_at_0min"] = float(t0_row["auroc"])
            eval_metrics[f"{m_prefix}_auprc_at_0min"] = float(t0_row["auprc"])
            eval_metrics[f"{m_prefix}_ppv050_at_0min"] = float(t0_row["ppv_050"])
        for metric_name, mk_row in zip(mk["metric"], mk.itertuples()):
            eval_metrics[f"{m_prefix}_mk_{metric_name}_tau"] = float(mk_row.tau)
            eval_metrics[f"{m_prefix}_mk_{metric_name}_p"] = float(mk_row.p_value)
        mlflow.log_metrics({k: v for k, v in eval_metrics.items() if v == v})
        # Artifacts: CSVs / JSON / plots; the calibrator itself is saved only on
        # the validation split, while calibrated predictions exist for both.
        artifact_files = [
            "window_metrics.csv",
            "window_metrics_ci.csv",
            "mann_kendall.csv",
            "calibration_diagnostics.json",
        ]
        if cal_diag is not None:
            artifact_files += ["calibration.joblib", "predictions_calibrated.parquet"]
        for fname in artifact_files:
            p = pred_dir / fname
            if p.exists():
                mlflow.log_artifact(str(p), artifact_path=a_prefix)
        for p in plots:
            mlflow.log_artifact(str(p), artifact_path=f"{a_prefix}/plots")
    return calibrator


# ---------- main ----------


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--config", type=Path, required=True, help="YAML experiment config")
    p.add_argument(
        "--override",
        nargs="*",
        default=[],
        help="dotted overrides, e.g. train.batch_size=16 data.window_min=60",
    )
    p.add_argument(
        "--mlflow-tracking-uri",
        default="sqlite:///mlflow.db",
        help="MLflow tracking URI (default: sqlite:///mlflow.db). "
        "MLflow 3.x deprecates file:./mlruns and its Overview tab "
        "does not render with the file backend.",
    )
    args = p.parse_args()

    cfg = load_config(args.config, args.override)
    out_dir = Path(cfg["paths"]["out_dir"])
    paths = dict(
        out_dir=str(out_dir),
        ckpt=str(out_dir / cfg["paths"].get("ckpt_subdir", "ckpts")),
        predictions=str(out_dir / cfg["paths"].get("predictions_subdir", "predictions")),
        manifest=str(cfg["paths"]["manifest_path"]),
        normalizer=str(cfg["paths"]["normalizer_path"]),
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    # Snapshot the (merged) config alongside the run so the run is reproducible.
    with (out_dir / "config_resolved.json").open("w") as f:
        json.dump(cfg, f, indent=2)

    # Open ONE outer MLflow run that wraps both training and post-eval.
    mlflow.set_tracking_uri(args.mlflow_tracking_uri)
    mlflow.set_experiment(cfg["experiment"]["name"])
    run_name = cfg["experiment"].get("run_name")
    with mlflow.start_run(run_name=run_name) as run:
        print(f"MLflow run: experiment={cfg['experiment']['name']}  run_id={run.info.run_id}")
        # Log the resolved config as an artifact for reproducibility.
        mlflow.log_artifact(str(out_dir / "config_resolved.json"))

        _post_eval_in_run(cfg, paths, out_dir)


def _post_eval_in_run(cfg: dict, paths: dict, out_dir: Path) -> None:
    """Helper invoked from inside the active MLflow run."""
    manifest, train_m, val_m, test_m, normalizer, _ = build_manifest_and_normalizer(cfg, paths)
    # Attach the manifest + normalizer to the MLflow run as artifacts.
    manifest_path = Path(paths["manifest"])
    for p in [
        manifest_path,
        manifest_path.with_suffix(".qc.csv"),
        Path(paths["normalizer"]),
    ]:
        if p.exists():
            mlflow.log_artifact(str(p), artifact_path="data")

    train_loader, val_loader, _ = build_loaders(cfg, train_m, val_m, normalizer)
    model = build_model(cfg)

    tb_log_dir = cfg["paths"].get("tb_log_dir") or str(Path(paths["out_dir"]) / "tb")
    trainer_cfg = TrainerConfig(
        lr=cfg["train"]["lr"],
        weight_decay=cfg["train"]["weight_decay"],
        grad_clip=cfg["train"]["grad_clip"],
        epochs=cfg["train"]["epochs"],
        warmup_frac=cfg["train"]["warmup_frac"],
        loss_type=cfg["train"].get("loss_type", "cross_entropy"),
        cosine_ce_weight=cfg["train"].get("cosine_ce_weight", 0.1),
        class_weights=cfg["train"].get("class_weights"),
        num_classes=cfg["model"].get("num_classes", 2),
        use_amp=cfg["train"]["use_amp"],
        amp_dtype=cfg["train"].get("amp_dtype", "bfloat16"),
        experiment_name=cfg["experiment"]["name"],
        run_name=cfg["experiment"]["run_name"],
        out_dir=paths["ckpt"],
        monitor=cfg["train"]["monitor"],
        monitor_mode=cfg["train"]["monitor_mode"],
        patience=cfg["train"]["patience"],
        tb_log_dir=tb_log_dir,
        extra_params={
            "sources": ",".join(cfg["data"]["sources"]),
            "window_min": cfg["data"]["window_min"],
            "max_seq_len": cfg["data"]["max_seq_len"],
            "d_model": cfg["model"]["d_model"],
            "num_layers": cfg["model"]["num_layers"],
        },
    )
    trainer = Trainer(model, train_loader, val_loader, trainer_cfg)
    summary = trainer.fit()
    print(f"\nTraining done. best {trainer_cfg.monitor}={summary['best_value']}")
    print(f"  best ckpt: {summary['best_ckpt']}")

    # Reload best ckpt and run the online-sim eval on the val cohort.
    best_ckpt = torch.load(summary["best_ckpt"], map_location="cpu", weights_only=False)
    model.load_state_dict(best_ckpt["model_state"])
    device = auto_device(cfg["train"].get("device"))
    model = model.to(device)
    calibrator = post_train_eval(
        model,
        normalizer,
        val_m,
        device,
        paths,
        window_min=cfg["data"]["window_min"],
        max_seq_len=cfg["data"]["max_seq_len"],
        split_name="val",
        fit_calibration=True,
    )

    # Held-out test split (if configured): evaluated with the SAME
    # best ckpt, never used during training or for early stop.
    if test_m is not None and len(test_m) > 0:
        print(f"\n=== Held-out TEST split evaluation ({len(test_m):,} cases) ===")
        post_train_eval(
            model,
            normalizer,
            test_m,
            device,
            paths,
            window_min=cfg["data"]["window_min"],
            max_seq_len=cfg["data"]["max_seq_len"],
            split_name="test",
            calibrator=calibrator,
        )


if __name__ == "__main__":
    main()
