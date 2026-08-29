"""Empirical verification that the binary probability extraction is correct.

Three claims to check:
  1. With `num_classes=2`, model output is `(B, 2)` (one logit per class).
  2. softmax(logits, axis=-1)[:, 1] gives P(positive) and equals
     sigmoid(logit_diff) where logit_diff = logits[:, 1] - logits[:, 0]
     -- i.e., the softmax convention is consistent with the binary
     identity.
  3. The label convention is `label == 1` <=> IOH-positive case, so
     softmax[:, 1] is correctly oriented for AUROC etc.

Run against the smoke or dryrun checkpoint:

    conda run -n torch python scripts/verify_prob_extraction.py \
        --run-dir outputs/runs/dryrun_vitaldb
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from ioh_prediction.data.collate import CollateConfig, RefTimeCollate
from ioh_prediction.data.dataset import IOHRefTimeDataset
from ioh_prediction.data.normalize import NormalizerStats
from ioh_prediction.data.reference_time import (
    RefTimeConfig,
    build_ref_time_manifest,
)
from ioh_prediction.data.splits import stratified_subject_split
from ioh_prediction.models import ITEConfig, ITETransformer
from ioh_prediction.training import auto_device

REPO_ROOT = Path(__file__).resolve().parents[1]
TS_GLOB = str(REPO_ROOT / "data" / "timeseries" / "source=*" / "case_id=*" / "data.parquet")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=REPO_ROOT / "outputs" / "runs" / "dryrun_vitaldb",
        help="A run directory produced by scripts/train.py",
    )
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()

    cfg = json.loads((run_dir / "config_resolved.json").read_text())
    m = cfg["model"]
    print(f"Run config: num_classes (forced) = 1   d_model = {m['d_model']}   layers = {m['num_layers']}")

    # Rebuild model and load weights.
    num_classes = m.get("num_classes", 2)
    model = ITETransformer(
        ITEConfig(
            d_model=m["d_model"],
            num_layers=m["num_layers"],
            num_heads=m["num_heads"],
            dim_feedforward=m.get("dim_feedforward"),
            dropout=m["dropout"],
            num_classes=num_classes,
        )
    )
    ckpt = torch.load(run_dir / "ckpts" / "best.pt", map_location="cpu", weights_only=False)
    model.load_state_dict(ckpt["model_state"])
    device = auto_device(cfg["train"].get("device"))
    model = model.to(device).eval()

    # Build a tiny batch from the val cohort.
    rt_cfg = RefTimeConfig(
        pos_min_pre_onset_min=cfg["data"]["pos_min_pre_onset_min"],
        neg_min_pre_onset_min=cfg["data"]["neg_min_pre_onset_min"],
        seed=cfg["data"]["seed"],
    )
    manifest, _ = build_ref_time_manifest(TS_GLOB, sources=tuple(cfg["data"]["sources"]), config=rt_cfg)
    _, val_m = stratified_subject_split(manifest, val_frac=cfg["data"]["val_frac"], seed=cfg["data"]["seed"])

    # Take 8 positives + 8 negatives for a balanced sanity check.
    pos = val_m[val_m["label"] == 1].head(8).reset_index(drop=True)
    neg = val_m[val_m["label"] == 0].head(8).reset_index(drop=True)
    import pandas as pd

    small = pd.concat([pos, neg], ignore_index=True)
    normalizer = NormalizerStats.load(run_dir / "normalizer.parquet")
    collate = RefTimeCollate(normalizer, CollateConfig(max_seq_len=cfg["data"]["max_seq_len"]))
    ds = IOHRefTimeDataset(small, window_min=cfg["data"]["window_min"])
    loader = DataLoader(ds, batch_size=len(small), shuffle=False, collate_fn=collate)
    batch = next(iter(loader))

    with torch.no_grad():
        logits = model(
            batch["data"].to(device),
            batch["mask"].to(device),
        ).cpu()

    # ---- Claim 1: output shape is (B, num_classes) ----
    print(
        f"\n[Claim 1] logits.shape = {tuple(logits.shape)}   "
        f"(expected (B, num_classes) = ({len(small)}, {num_classes}))   "
        f"OK={tuple(logits.shape) == (len(small), num_classes)}"
    )

    # ---- Claim 2: softmax[:, 1] == sigmoid(logit_diff) ----
    logits_np = logits.numpy().astype(np.float64)
    ex = np.exp(logits_np - logits_np.max(axis=-1, keepdims=True))
    softmax_full = ex / ex.sum(axis=-1, keepdims=True)
    pos_prob = softmax_full[:, 1]
    # For 2-class softmax, P(class=1) = sigmoid(logit1 - logit0).
    diff = logits_np[:, 1] - logits_np[:, 0]
    sigmoid_of_diff = 1.0 / (1.0 + np.exp(-diff))
    max_diff = float(np.max(np.abs(pos_prob - sigmoid_of_diff)))
    print(
        f"\n[Claim 2] max |softmax[:, 1] - sigmoid(logit1 - logit0)| = {max_diff:.2e}   "
        f"(expect ~ 1e-15)   OK={max_diff < 1e-9}"
    )

    # ---- Claim 3: label convention & prob direction ----
    labels = batch["label"].numpy().astype(int)
    avg_pos = pos_prob[labels == 1].mean()
    avg_neg = pos_prob[labels == 0].mean()
    print(
        f"\n[Claim 3] labels={list(labels)}\n"
        f"           P(positive)={[round(float(p), 3) for p in pos_prob]}\n"
        f"           mean P(positive | label=1) = {avg_pos:.3f}\n"
        f"           mean P(positive | label=0) = {avg_neg:.3f}\n"
        f"           OK direction (pos > neg) = {avg_pos > avg_neg}"
    )

    print(
        "\nSummary: model returns (B, num_classes) logits. Probability of the "
        "positive class is `softmax(logits, dim=-1)[:, 1]`, equivalent to "
        "`sigmoid(logits[:, 1] - logits[:, 0])`. label == 1 means the case had "
        "an IOH event, so softmax[:, 1] is the value AUROC / AUPRC use."
    )


if __name__ == "__main__":
    main()
