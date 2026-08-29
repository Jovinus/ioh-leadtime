"""Per-minute eligibility / mask helpers.

These functions encode `HANDOFF.md` §6 rules so the rest of the codebase
doesn't have to remember them.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# §6.1: EPIC anchors on anesthesia start; VitalDB/SIS on surgical start.
# EPIC's first ~15-20 min are induction artefact; drop the first 25.
INDUCTION_DROP_MIN: dict[str, int] = {
    "mover_epic": 25,
    "vitaldb": 10,
    "mover": 10,
}


def induction_drop_for(source: str) -> int:
    return INDUCTION_DROP_MIN[source]


def training_mask(df: pd.DataFrame) -> pd.Series:
    """Boolean per-minute mask: True where this minute is usable for loss.

    Combines:
      - `label_mask == 0` (HANDOFF §6.3: induction + post-onset right-censoring)
      - source-specific induction-drop (HANDOFF §6.1)
    """
    if "source" not in df or "t_min" not in df or "label_mask" not in df:
        raise ValueError("DataFrame must have columns: source, t_min, label_mask")

    src = df["source"].iloc[0] if isinstance(df["source"].dtype, pd.CategoricalDtype) else df["source"].iloc[0]
    drop_min = INDUCTION_DROP_MIN.get(str(src), 10)

    return (df["label_mask"] == 0) & (df["t_min"] >= drop_min)


def map_imputed_heuristic(df: pd.DataFrame, tol: float = 0.6) -> pd.Series:
    """HANDOFF §6.2: heuristic flag for EPIC MAP that was imputed as
    `(SBP + 2·DBP) / 3`. True where the minute looks imputed.

    Always returns False for non-EPIC rows.
    """
    src = df["source"].iloc[0] if len(df) else None
    if str(src) != "mover_epic":
        return pd.Series(False, index=df.index)

    formula = (df["SBP"] + 2 * df["DBP"]) / 3.0
    diff = (df["MAP"] - formula).abs()
    # measured MAP differs from the formula by > tol; imputed MAP equals it.
    return diff.fillna(np.inf) <= tol
