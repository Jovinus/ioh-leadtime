"""1-epoch smoke test for the Trainer on the small VitalDB cohort.

Verifies: data pipeline -> model forward -> backward -> optimizer step ->
val metrics -> MLflow logging -> best-ckpt save.

Runs in a few minutes on CPU/MPS — small batch / small model on purpose.
"""

from __future__ import annotations

from pathlib import Path

from torch.utils.data import DataLoader

from ioh_prediction.data.collate import CollateConfig, RefTimeCollate
from ioh_prediction.data.dataset import IOHRefTimeDataset
from ioh_prediction.data.normalize import fit_normalizer
from ioh_prediction.data.reference_time import build_ref_time_manifest
from ioh_prediction.data.splits import stratified_subject_split
from ioh_prediction.models import ITEConfig, ITETransformer
from ioh_prediction.training import Trainer, TrainerConfig

REPO_ROOT = Path(__file__).resolve().parents[1]
TS_GLOB = str(REPO_ROOT / "data" / "timeseries" / "source=*" / "case_id=*" / "data.parquet")
CASES_PARQUET = str(REPO_ROOT / "data" / "cases.parquet")


def main() -> None:
    manifest, qc = build_ref_time_manifest(TS_GLOB, sources=("vitaldb",))
    train_m, val_m = stratified_subject_split(manifest, val_frac=0.2, seed=1004)
    print(f"manifest: {len(manifest):,}  train: {len(train_m):,}  val: {len(val_m):,}")

    normalizer = fit_normalizer(
        TS_GLOB,
        case_ids=train_m["case_id"].tolist(),
        cases_parquet=CASES_PARQUET,
    )
    collate = RefTimeCollate(normalizer, CollateConfig(max_seq_len=2048))

    train_ds = IOHRefTimeDataset(train_m, window_min=120)
    val_ds = IOHRefTimeDataset(val_m, window_min=120)
    train_loader = DataLoader(
        train_ds,
        batch_size=16,
        shuffle=True,
        collate_fn=collate,
        num_workers=2,
        persistent_workers=True,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=32,
        shuffle=False,
        collate_fn=collate,
        num_workers=2,
        persistent_workers=True,
    )

    model = ITETransformer(ITEConfig(num_classes=1, d_model=64, num_layers=2))
    cfg = TrainerConfig(
        epochs=1,
        lr=3e-4,
        warmup_frac=0.1,
        run_name="smoke_vitaldb_1ep",
        experiment_name="ioh-prediction-smoke",
        out_dir=str(REPO_ROOT / "outputs" / "ckpts" / "smoke"),
        log_every_n_steps=20,
        patience=10,
    )
    out = Trainer(model, train_loader, val_loader, cfg).fit()
    print("done. best:", out["best_value"], "  ckpt:", out["best_ckpt"])


if __name__ == "__main__":
    main()
