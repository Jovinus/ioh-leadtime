"""Train reference/baseline models (LogisticRegression, RandomForest, XGBoost,
LSTM) and evaluate them with the SAME online-simulation harness as the ITE
Transformer, so faithfulness + lead-time analyses run on them unchanged.

Design:
  * Reuse each gap run's saved `manifest.csv` and `stratified_subject_split_3way`
    (seed 1004) -> identical train/val/test cohorts to the transformer.
  * LR/RF/XGB features = last-observation-carried-forward (LOCF) per channel at
    the evaluation minute + demographics (last observed value only). LSTM consumes the
    normalized per-minute window sequence.
  * Online-sim scores every minute in [induction_drop, T-1] exactly like
    `evaluation.online_inference.score_case` (same anchor minutes, same
    t_to_event), then writes the identical artifact layout:
        outputs/runs/<model>_gap<g>/predictions/test/{predictions_raw.parquet,
          window_metrics.csv, mann_kendall.csv, calibration.joblib,
          predictions_calibrated.parquet}
        outputs/runs/<model>_gap<g>/external_{vitaldb,mover}/...

Usage:
  python scripts/train_baselines.py --gap 5 --model xgb
  python scripts/train_baselines.py --gap 5 --model logreg --limit-cases 100  # smoke
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from torch import nn

from ioh_prediction.data.eligibility import induction_drop_for
from ioh_prediction.data.normalize import NormalizerStats
from ioh_prediction.data.schema import ALL_CHANNELS, STATIC_FEATURES
from ioh_prediction.data.splits import stratified_subject_split_3way
from ioh_prediction.evaluation.calibration import calibration_diagnostics, fit_isotonic
from ioh_prediction.evaluation.mann_kendall import mk_for_metrics
from ioh_prediction.evaluation.time_window_metrics import compute_window_metrics

REPO = Path(__file__).resolve().parents[1]
RUNS = REPO / "outputs" / "runs"
SEED = 1004
WINDOW_MIN = 120
MODELS = ("logreg", "rf", "xgb", "lstm")


# ----------------------------------------------------------------------------
# LOCF featurization (tabular baselines)
# ----------------------------------------------------------------------------
def locf_matrix(case_df: pd.DataFrame, drop: int, channels=ALL_CHANNELS) -> pd.DataFrame:
    """Per-minute LOCF table indexed by t_min over [drop, T). Rows before the
    induction drop are removed first; then forward-fill each channel so row t
    holds the last observed value at or before minute t."""
    df = case_df[case_df["t_min"] >= drop].sort_values("t_min")
    if df.empty:
        return pd.DataFrame(columns=list(channels))
    T = int(df["t_min"].max())
    full = pd.RangeIndex(drop, T + 1, name="t_min")
    mat = df.set_index("t_min")[list(channels)].reindex(full).ffill()
    return mat  # NaN where never observed yet


def feature_rows_for_minutes(
    locf: pd.DataFrame, minutes: np.ndarray, static_vec: np.ndarray, channels=ALL_CHANNELS
) -> np.ndarray:
    """Feature matrix (len(minutes), n_channels + n_static). Feature at minute t
    = LOCF value at t-1 (last obs strictly before the evaluation minute), i.e.
    no peeking at minute t itself, matching the model's causal window."""
    prev = np.clip(minutes - 1, locf.index.min(), locf.index.max())
    if len(locf) == 0:
        chan = np.full((len(minutes), len(channels)), np.nan, dtype=np.float32)
    else:
        chan = locf.reindex(prev)[list(channels)].to_numpy(dtype=np.float32)
    stat = np.tile(static_vec.astype(np.float32), (len(minutes), 1))
    return np.hstack([chan, stat])


def static_vec_of(row: pd.Series) -> np.ndarray:
    return pd.to_numeric(
        pd.Series([row[f] for f in STATIC_FEATURES]), errors="coerce"
    ).to_numpy(dtype=np.float32)


def build_feature_table(manifest: pd.DataFrame, channels=ALL_CHANNELS):
    """Feature vector at each case's ref_time_min (the training anchor)."""
    X, y, cids = [], [], []
    for _, row in manifest.iterrows():
        drop = induction_drop_for(str(row["source"]))
        ref_t = int(row["ref_time_min"])
        cdf = pd.read_parquet(row["parquet_path"])
        locf = locf_matrix(cdf, drop, channels)
        feat = feature_rows_for_minutes(
            locf, np.array([ref_t]), static_vec_of(row), channels
        )[0]
        X.append(feat)
        y.append(int(row["label"]))
        cids.append(str(row["case_id"]))
    return np.asarray(X, dtype=np.float32), np.asarray(y, dtype=np.int64), cids


FEATURE_NAMES = list(ALL_CHANNELS) + list(STATIC_FEATURES)


# ----------------------------------------------------------------------------
# LSTM model + sequence featurization
# ----------------------------------------------------------------------------
class LSTMClassifier(nn.Module):
    def __init__(self, n_channels: int, hidden: int = 128, layers: int = 1, dropout: float = 0.1):
        super().__init__()
        # input = normalized value + observed-mask per channel
        self.lstm = nn.LSTM(
            input_size=2 * n_channels, hidden_size=hidden, num_layers=layers,
            batch_first=True, dropout=dropout if layers > 1 else 0.0,
        )
        self.head = nn.Sequential(nn.LayerNorm(hidden), nn.Dropout(dropout), nn.Linear(hidden, 2))

    def forward(self, seq: torch.Tensor, lengths: torch.Tensor) -> torch.Tensor:
        packed = nn.utils.rnn.pack_padded_sequence(
            seq, lengths.cpu(), batch_first=True, enforce_sorted=False
        )
        _, (h, _) = self.lstm(packed)
        return self.head(h[-1])


def build_sequence(
    case_df: pd.DataFrame, drop: int, end_min: int, med: np.ndarray, iqr: np.ndarray,
    window_min: int = WINDOW_MIN, channels=ALL_CHANNELS,
) -> np.ndarray:
    """Normalized per-minute window [max(drop, end-window), end): (L, 2C) with
    value=(x-med)/iqr (NaN->0) concatenated with observed-mask."""
    lo = max(drop, end_min - window_min)
    win = case_df[(case_df["t_min"] >= lo) & (case_df["t_min"] < end_min)].sort_values("t_min")
    raw = win[list(channels)].to_numpy(dtype=np.float32)
    if raw.shape[0] == 0:
        return np.zeros((1, 2 * len(channels)), dtype=np.float32)  # empty -> single zero step
    mask = (~np.isnan(raw)).astype(np.float32)
    norm = (raw - med) / iqr
    norm = np.nan_to_num(norm, nan=0.0)
    return np.hstack([norm, mask]).astype(np.float32)


def pad_batch(seqs: list[np.ndarray]) -> tuple[torch.Tensor, torch.Tensor]:
    lengths = torch.tensor([s.shape[0] for s in seqs], dtype=torch.int64)
    maxlen = int(lengths.max())
    C2 = seqs[0].shape[1]
    out = np.zeros((len(seqs), maxlen, C2), dtype=np.float32)
    for i, s in enumerate(seqs):
        out[i, : s.shape[0]] = s
    return torch.from_numpy(out), lengths


# ----------------------------------------------------------------------------
# Training
# ----------------------------------------------------------------------------
def train_tabular(model_name: str, Xtr, ytr, Xval, yval):
    if model_name == "logreg":
        clf = make_pipeline(
            SimpleImputer(strategy="median"),
            StandardScaler(),
            LogisticRegression(max_iter=2000, random_state=SEED),
        )
        clf.fit(Xtr, ytr)
    elif model_name == "rf":
        clf = make_pipeline(
            SimpleImputer(strategy="median"),
            RandomForestClassifier(n_estimators=400, n_jobs=-1, random_state=SEED),
        )
        clf.fit(Xtr, ytr)
    elif model_name == "xgb":
        from xgboost import XGBClassifier

        clf = XGBClassifier(
            n_estimators=600, max_depth=6, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, eval_metric="auc",
            early_stopping_rounds=40, random_state=SEED, n_jobs=-1, tree_method="hist",
        )
        clf.fit(Xtr, ytr, eval_set=[(Xval, yval)], verbose=False)  # NaN handled natively
    else:
        raise ValueError(model_name)
    return clf


def train_lstm(seqs_tr, ytr, seqs_val, yval, device, epochs=40, patience=8, lr=1e-3, bs=64):
    # Seed model initialisation as well as minibatch ordering.  Previously only
    # the NumPy shuffle was seeded, so otherwise-identical LSTM runs could start
    # from different weights.  Keep one RNG alive across epochs so each epoch
    # receives a reproducible but different permutation.
    torch.manual_seed(SEED)
    n_channels = len(ALL_CHANNELS)
    model = LSTMClassifier(n_channels).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-2)
    lossf = nn.CrossEntropyLoss()
    from sklearn.metrics import roc_auc_score
    shuffle_rng = np.random.default_rng(SEED)

    def batches(seqs, y, shuffle):
        idx = np.arange(len(seqs))
        if shuffle:
            shuffle_rng.shuffle(idx)
        for s in range(0, len(idx), bs):
            j = idx[s : s + bs]
            seq, lengths = pad_batch([seqs[k] for k in j])
            yield seq.to(device), lengths, torch.tensor(y[j], device=device)

    best_auroc, best_state, bad = -1.0, None, 0
    for ep in range(epochs):
        model.train()
        for seq, lengths, yb in batches(seqs_tr, ytr, True):
            opt.zero_grad()
            loss = lossf(model(seq, lengths), yb)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
        # val
        model.eval()
        probs, labs = [], []
        with torch.no_grad():
            for seq, lengths, yb in batches(seqs_val, yval, False):
                p = torch.softmax(model(seq, lengths).float(), -1)[:, 1].cpu().numpy()
                probs.append(p)
                labs.append(yb.cpu().numpy())
        auroc = roc_auc_score(np.concatenate(labs), np.concatenate(probs))
        print(f"    lstm ep{ep:02d} val_auroc={auroc:.4f}")
        if auroc > best_auroc:
            best_auroc, best_state, bad = auroc, {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}, 0
        else:
            bad += 1
            if bad >= patience:
                break
    if best_state is not None:
        model.load_state_dict(best_state)
    return model, best_auroc


# ----------------------------------------------------------------------------
# Online-sim scoring (mirrors evaluation.online_inference.score_case)
# ----------------------------------------------------------------------------
def score_manifest_tabular(clf, manifest, channels=ALL_CHANNELS) -> pd.DataFrame:
    frames = []
    for _, row in manifest.iterrows():
        src = str(row["source"])
        drop = induction_drop_for(src)
        ref_t = int(row["ref_time_min"])
        cdf = pd.read_parquet(row["parquet_path"]).sort_values("t_min")
        T = int(cdf["t_min"].max()) + 1
        minutes = np.arange(drop, T)  # anchor minutes = [induction_drop, T-1]
        if minutes.size == 0:
            continue
        locf = locf_matrix(cdf, drop, channels)
        X = feature_rows_for_minutes(locf, minutes, static_vec_of(row), channels)
        proba = clf.predict_proba(X)[:, 1]
        frames.append(pd.DataFrame({
            "case_id": str(row["case_id"]), "source": src, "t_min": minutes,
            "t_to_event": (ref_t - minutes).astype(int),
            "score": proba.astype(float), "label": int(row["label"]),
        }))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def score_manifest_lstm(model, normalizer, manifest, device, bs=128) -> pd.DataFrame:
    med, iqr = normalizer.lookup(ALL_CHANNELS)
    model.eval()
    frames = []
    with torch.no_grad():
        for _, row in manifest.iterrows():
            src = str(row["source"])
            drop = induction_drop_for(src)
            ref_t = int(row["ref_time_min"])
            cdf = pd.read_parquet(row["parquet_path"]).sort_values("t_min")
            T = int(cdf["t_min"].max()) + 1
            minutes = np.arange(drop, T)
            if minutes.size == 0:
                continue
            seqs = [build_sequence(cdf, drop, int(t), med, iqr) for t in minutes]
            probs = np.empty(len(seqs), dtype=np.float32)
            for s in range(0, len(seqs), bs):
                seq, lengths = pad_batch(seqs[s : s + bs])
                out = model(seq.to(device), lengths)
                probs[s : s + bs] = torch.softmax(out.float(), -1)[:, 1].cpu().numpy()
            frames.append(pd.DataFrame({
                "case_id": str(row["case_id"]), "source": src, "t_min": minutes,
                "t_to_event": (ref_t - minutes).astype(int),
                "score": probs.astype(float), "label": int(row["label"]),
            }))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


# ----------------------------------------------------------------------------
# Eval + artifact writing (mirrors the transformer post-eval)
# ----------------------------------------------------------------------------
def write_eval(preds: pd.DataFrame, out_dir: Path, calibrator=None, fit_calib=False):
    out_dir.mkdir(parents=True, exist_ok=True)
    preds.to_parquet(out_dir / "predictions_raw.parquet", index=False)
    wm = compute_window_metrics(preds[["t_to_event", "score", "label"]])
    wm.to_csv(out_dir / "window_metrics.csv", index=False)
    mk_for_metrics(wm).to_csv(out_dir / "mann_kendall.csv", index=False)

    if fit_calib:
        calibrator = fit_isotonic(preds["score"].to_numpy(), preds["label"].to_numpy())
        calibrator.save(out_dir / "calibration.joblib")
    if calibrator is not None:
        cal = preds.copy()
        cal["score"] = calibrator.apply(preds["score"].to_numpy())
        cal.to_parquet(out_dir / "predictions_calibrated.parquet", index=False)
        diag = {
            "raw": calibration_diagnostics(preds["score"].to_numpy(), preds["label"].to_numpy()),
            "calibrated": calibration_diagnostics(cal["score"].to_numpy(), cal["label"].to_numpy()),
        }
        (out_dir / "calibration_diagnostics.json").write_text(json.dumps(diag, indent=2, default=float))
    return wm, calibrator


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gap", type=int, required=True)
    ap.add_argument("--model", choices=MODELS, required=True)
    ap.add_argument("--limit-cases", type=int, default=0, help="smoke: cap train/eval cases")
    ap.add_argument("--epochs", type=int, default=40, help="lstm only")
    ap.add_argument("--skip-external", action="store_true")
    args = ap.parse_args()

    src_run = RUNS / f"gap{args.gap}"
    manifest = pd.read_csv(src_run / "manifest.csv")
    normalizer = NormalizerStats.load(src_run / "normalizer.parquet")
    tr, va, te = stratified_subject_split_3way(manifest, 0.15, 0.15, SEED)
    if args.limit_cases:
        tr = tr.groupby("label", group_keys=False).head(max(2, args.limit_cases // 2))
        va = va.head(args.limit_cases // 2)
        te = te.head(args.limit_cases)
    print(f"[{args.model} gap{args.gap}] train={len(tr)} val={len(va)} test={len(te)}")

    out_run = RUNS / f"{args.model}_gap{args.gap}"
    out_run.mkdir(parents=True, exist_ok=True)
    te.to_csv(out_run / "test_manifest.csv", index=False)
    device = torch.device("mps" if torch.backends.mps.is_available()
                          else ("cuda" if torch.cuda.is_available() else "cpu"))
    t0 = time.time()

    if args.model == "lstm":
        med, iqr = normalizer.lookup(ALL_CHANNELS)
        def seqs_of(m):
            out = []
            for _, r in m.iterrows():
                cdf = pd.read_parquet(r["parquet_path"]).sort_values("t_min")
                out.append(build_sequence(cdf, induction_drop_for(str(r["source"])),
                                          int(r["ref_time_min"]), med, iqr))
            return out
        print("  featurizing sequences...")
        model, best_val = train_lstm(seqs_of(tr), tr["label"].to_numpy(),
                                 seqs_of(va), va["label"].to_numpy(), device,
                                 epochs=args.epochs)
        print(f"  lstm best val_auroc={best_val:.4f}")
        torch.save(model.state_dict(), out_run / "lstm.pt")

        def score_test(m):
            return score_manifest_lstm(model, normalizer, m, device)
    else:
        print("  building feature tables...")
        Xtr, ytr, _ = build_feature_table(tr)
        Xva, yva, _ = build_feature_table(va)
        clf = train_tabular(args.model, Xtr, ytr, Xva, yva)
        joblib.dump(clf, out_run / "model.joblib")

        def score_test(m):
            return score_manifest_tabular(clf, m)

    # Fit calibration on validation, then apply the frozen mapping to test and
    # external cohorts. Test labels remain evaluation-only.
    print("  scoring validation for calibration...")
    preds_va = score_test(va)
    _, calibrator = write_eval(
        preds_va, out_run / "predictions" / "val", fit_calib=True
    )

    print("  scoring test...")
    preds_te = score_test(te)
    write_eval(preds_te, out_run / "predictions" / "test", calibrator=calibrator)

    # Externals reuse the saved manifests and validation-fitted calibrator.
    if not args.skip_external:
        for ext in ("vitaldb", "mover"):
            ext_man_path = src_run / f"external_{ext}" / "manifest.csv"
            if not ext_man_path.exists():
                continue
            ext_man = pd.read_csv(ext_man_path)
            if args.limit_cases:
                ext_man = ext_man.head(args.limit_cases)
            print(f"  scoring external {ext} ({len(ext_man)})...")
            preds_ext = score_test(ext_man)
            if len(preds_ext):
                write_eval(preds_ext, out_run / f"external_{ext}", calibrator=calibrator)

    meta = {"model": args.model, "gap": args.gap, "seed": SEED, "device": str(device),
            "n_train": len(tr), "n_val": len(va), "n_test": len(te),
            "elapsed_sec": round(time.time() - t0, 1), "feature_names": FEATURE_NAMES,
            "calibration_fit_split": "validation",
            "feature_mode": "LOCF last-obs + demographics" if args.model != "lstm"
            else "normalized per-minute window sequence (value+mask)"}
    (out_run / "baseline_meta.json").write_text(json.dumps(meta, indent=2))
    print(f"  done in {meta['elapsed_sec']}s -> {out_run}")


if __name__ == "__main__":
    main()
