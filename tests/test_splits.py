"""Unit tests for subject-aware train/val/test splits."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ioh_prediction.data.splits import (
    stratified_subject_kfold,
    stratified_subject_split,
    stratified_subject_split_3way,
)


def _synthetic_manifest(n_subjects: int = 200, cases_per_sub: int = 2, pos_rate: float = 0.5, seed: int = 0) -> pd.DataFrame:
    rng = np.random.RandomState(seed)
    rows = []
    for s in range(n_subjects):
        sub = f"sub{s:04d}"
        label = int(rng.uniform() < pos_rate)
        for c in range(cases_per_sub):
            rows.append({"case_id": f"{sub}_c{c}", "subject_id": sub, "label": label})
    return pd.DataFrame(rows)


# ---------- 2-way ----------


def test_2way_no_subject_leakage():
    manifest = _synthetic_manifest()
    train, val = stratified_subject_split(manifest, val_frac=0.2, seed=1)
    train_subs = set(train["subject_id"])
    val_subs = set(val["subject_id"])
    assert train_subs.isdisjoint(val_subs)
    assert len(train) + len(val) == len(manifest)


def test_2way_label_stratification():
    manifest = _synthetic_manifest(n_subjects=400, pos_rate=0.3)
    train, val = stratified_subject_split(manifest, val_frac=0.2, seed=2)
    p_total = manifest["label"].mean()
    p_train = train["label"].mean()
    p_val = val["label"].mean()
    # Both folds within 5 pp of overall prevalence.
    assert abs(p_train - p_total) < 0.05
    assert abs(p_val - p_total) < 0.05


# ---------- 3-way ----------


def test_3way_returns_three_disjoint_subject_sets():
    manifest = _synthetic_manifest(n_subjects=300, cases_per_sub=3)
    tr, va, te = stratified_subject_split_3way(
        manifest, val_frac=0.15, test_frac=0.15, seed=42
    )
    tr_s = set(tr["subject_id"])
    va_s = set(va["subject_id"])
    te_s = set(te["subject_id"])
    assert tr_s.isdisjoint(va_s)
    assert tr_s.isdisjoint(te_s)
    assert va_s.isdisjoint(te_s)
    assert len(tr) + len(va) + len(te) == len(manifest)


def test_3way_fractions_approximate():
    manifest = _synthetic_manifest(n_subjects=400)
    tr, va, te = stratified_subject_split_3way(
        manifest, val_frac=0.15, test_frac=0.15, seed=3
    )
    n = len(manifest)
    assert abs(len(va) / n - 0.15) < 0.05
    assert abs(len(te) / n - 0.15) < 0.05
    assert abs(len(tr) / n - 0.70) < 0.05


def test_3way_label_stratified():
    manifest = _synthetic_manifest(n_subjects=400, pos_rate=0.4)
    tr, va, te = stratified_subject_split_3way(
        manifest, val_frac=0.15, test_frac=0.15, seed=4
    )
    p = manifest["label"].mean()
    assert abs(tr["label"].mean() - p) < 0.05
    assert abs(va["label"].mean() - p) < 0.07
    assert abs(te["label"].mean() - p) < 0.07


def test_3way_rejects_bad_fractions():
    manifest = _synthetic_manifest()
    with pytest.raises(ValueError):
        stratified_subject_split_3way(manifest, val_frac=0.6, test_frac=0.5)
    with pytest.raises(ValueError):
        stratified_subject_split_3way(manifest, val_frac=0.0, test_frac=0.2)


def test_3way_determinism():
    manifest = _synthetic_manifest(n_subjects=100)
    a = stratified_subject_split_3way(manifest, 0.2, 0.2, seed=7)
    b = stratified_subject_split_3way(manifest, 0.2, 0.2, seed=7)
    for x, y in zip(a, b):
        assert list(x["subject_id"]) == list(y["subject_id"])


# ---------- k-fold sanity ----------


def test_kfold_yields_k_pairs():
    manifest = _synthetic_manifest(n_subjects=100)
    folds = list(stratified_subject_kfold(manifest, k=5, seed=1))
    assert len(folds) == 5
    for tr, va in folds:
        assert set(tr["subject_id"]).isdisjoint(set(va["subject_id"]))
