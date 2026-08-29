from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


def _module():
    path = (
        Path(__file__).parents[1] / "analysis" / "plan_additions_2026" / "repeated_events.py"
    )
    spec = importlib.util.spec_from_file_location("repeated_events", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_later_event_requires_complete_normotensive_washout(tmp_path):
    rows = []
    for case_id in ("eligible", "low_map", "missing_map"):
        for t_min in range(0, 23):
            if case_id == "missing_map" and t_min == 15:
                continue
            event_id = 1 if 5 <= t_min <= 7 else (2 if 20 <= t_min <= 22 else None)
            map_value = 60.0 if event_id is not None else 70.0
            if case_id == "low_map" and t_min == 15:
                map_value = 64.0
            rows.append(
                {
                    "source": "synthetic",
                    "case_id": case_id,
                    "t_min": t_min,
                    "MAP": map_value,
                    "event_id_d3": event_id,
                }
            )

    path = tmp_path / "data.parquet"
    pd.DataFrame(rows).to_parquet(path, index=False)
    module = _module()
    module.TS = str(path)

    events = module._events()
    later = events[events["event_number"] > 1]
    assert later[["case_id", "event_id"]].to_records(index=False).tolist() == [
        ("eligible", 2)
    ]

