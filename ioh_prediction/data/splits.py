"""Subject-aware, label-stratified train/val (or k-fold) splits.

We **must not** put two cases from the same patient into different folds —
that's classic per-patient leakage. For EPIC, `subject_id = mep_mrn_<MRN>`
so multiple surgeries on the same MRN share an id. For SIS the source
treats one PID = one case, so `subject_id == case_id`. For VitalDB,
`subject_id` is the VitalDB `subjectid` (case_id ≠ patient when a patient
has multiple cases).

Stratification target: the case `label` (positive vs negative). Because
all of a subject's cases share a fold, the stratification is on the
*subject-level* label (majority vote over the subject's cases when they
disagree — rare in practice).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split


def _subject_level_label(manifest: pd.DataFrame) -> pd.Series:
    """Collapse cases to one row per subject with a binary label.

    A subject is positive if any of their cases are positive.
    """
    if "subject_id" not in manifest.columns:
        raise KeyError(
            "manifest is missing `subject_id`. Build it via "
            "`reference_time.build_ref_time_manifest` which joins cases.parquet."
        )
    return manifest.groupby("subject_id")["label"].max()


def _slice_by_subjects(manifest: pd.DataFrame, subjects) -> pd.DataFrame:
    return manifest.loc[manifest["subject_id"].isin(set(subjects))].reset_index(drop=True)


def stratified_subject_split(
    manifest: pd.DataFrame,
    val_frac: float = 0.2,
    seed: int = 1004,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """One-shot stratified train/val split at the *subject* level.

    Implemented on top of `sklearn.model_selection.train_test_split`:
    we split the unique-subject-id array (stratifying on the subject's
    binary label) and then slice the original manifest by membership.
    All cases of one subject stay together.

    Returns `(train_manifest, val_manifest)`.
    """
    if not 0.0 < val_frac < 1.0:
        raise ValueError(f"val_frac must be in (0, 1), got {val_frac}")

    sub_lab = _subject_level_label(manifest).sort_index()
    subjects = sub_lab.index.to_numpy()
    labels = sub_lab.to_numpy()
    train_s, val_s = train_test_split(
        subjects, test_size=val_frac, stratify=labels, random_state=seed
    )
    return _slice_by_subjects(manifest, train_s), _slice_by_subjects(manifest, val_s)


def stratified_subject_split_3way(
    manifest: pd.DataFrame,
    val_frac: float = 0.15,
    test_frac: float = 0.15,
    seed: int = 1004,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Subject-aware train / val / test split with label stratification.

    Two-stage sklearn split:
      1. `train_test_split(subjects, test_size=val_frac+test_frac)`
         carves off the held-out subjects, stratified by subject label.
      2. `train_test_split` of those held-out subjects into val and
         test, again stratified.

    All cases of a subject stay in one fold. Returns
    `(train_manifest, val_manifest, test_manifest)`.
    """
    if val_frac + test_frac >= 1.0 or val_frac <= 0 or test_frac <= 0:
        raise ValueError(
            f"val_frac and test_frac must each be in (0, 1) and sum < 1; "
            f"got val={val_frac}, test={test_frac}"
        )

    sub_lab = _subject_level_label(manifest).sort_index()
    subjects = sub_lab.index.to_numpy()
    labels = sub_lab.to_numpy()

    holdout_frac = val_frac + test_frac
    train_s, holdout_s, _, holdout_lab = train_test_split(
        subjects, labels,
        test_size=holdout_frac,
        stratify=labels,
        random_state=seed,
    )
    val_s, test_s = train_test_split(
        holdout_s,
        test_size=test_frac / holdout_frac,
        stratify=holdout_lab,
        random_state=seed,
    )
    return (
        _slice_by_subjects(manifest, train_s),
        _slice_by_subjects(manifest, val_s),
        _slice_by_subjects(manifest, test_s),
    )


def stratified_subject_kfold(
    manifest: pd.DataFrame,
    k: int = 5,
    seed: int = 1004,
):
    """Yield `(train_manifest, val_manifest)` pairs for `k` folds."""
    if k < 2:
        raise ValueError(f"k must be >= 2, got {k}")

    sub_lab = _subject_level_label(manifest)
    rng = np.random.RandomState(seed)

    fold_assignment: dict[str, int] = {}
    for label_val, group in sub_lab.groupby(sub_lab):
        ids = group.index.to_numpy()
        rng.shuffle(ids)
        for i, sid in enumerate(ids):
            fold_assignment[sid] = i % k

    folds = manifest["subject_id"].map(fold_assignment).to_numpy()
    for f in range(k):
        is_val = folds == f
        yield (
            manifest.loc[~is_val].reset_index(drop=True),
            manifest.loc[is_val].reset_index(drop=True),
        )
