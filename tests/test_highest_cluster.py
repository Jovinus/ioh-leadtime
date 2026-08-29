from pathlib import Path

import pandas as pd

from analysis.ioh_faithfulness_2026.lib import attach_highest_cluster


def test_mover_uses_case_as_highest_identifiable_cluster():
    pred = pd.DataFrame({"case_id": ["a", "a", "b"]})
    got = attach_highest_cluster(pred, Path("unused.parquet"), "mover")
    assert got["cluster_id"].tolist() == ["a", "a", "b"]
    assert got["cluster_level"].unique().tolist() == ["case"]


def test_epic_uses_subject_mapping(tmp_path):
    run = tmp_path / "gap0"
    pred_path = run / "predictions" / "test" / "predictions_raw.parquet"
    pred_path.parent.mkdir(parents=True)
    pd.DataFrame(
        {"case_id": ["a", "b"], "subject_id": ["patient", "patient"]}
    ).to_csv(run / "test_manifest.csv", index=False)
    pred = pd.DataFrame({"case_id": ["a", "a", "b"]})
    got = attach_highest_cluster(pred, pred_path, "epic_test")
    assert got["cluster_id"].tolist() == ["patient"] * 3
    assert got["cluster_level"].unique().tolist() == ["patient"]

