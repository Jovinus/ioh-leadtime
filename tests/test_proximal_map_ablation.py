from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


def _module():
    path = (
        Path(__file__).parents[1] / "analysis" / "plan_additions_2026" / "proximal_map_ablation.py"
    )
    spec = importlib.util.spec_from_file_location("proximal_map_ablation", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_eligible_manifest_requires_five_minutes_at_earliest_anchor():
    m = _module()
    manifest = pd.DataFrame(
        {
            "case_id": ["early", "boundary", "valid"],
            "source": ["mover_epic"] * 3,
            # EPIC drop=25; max horizon=10; full five-minute history requires ref>=40.
            "ref_time_min": [39, 40, 41],
        }
    )
    got = m._eligible_manifest(manifest)
    assert got["case_id"].tolist() == ["boundary", "valid"]
