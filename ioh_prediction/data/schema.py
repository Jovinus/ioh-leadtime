"""Canonical feature / channel definitions for IOH modeling.

The source-of-truth for the *dataset* schema lives in the preprocessing
repository. This file just declares which columns the *model* consumes and in
what order.
"""

# Per-minute continuous channels fed to the model.
# `procedure_group` is intentionally NOT here (HANDOFF §6.4 — cohort proxy).
VITAL_CHANNELS: tuple[str, ...] = (
    "MAP",
    "SBP",
    "DBP",
    "NIBP_MAP",
    "NIBP_SBP",
    "NIBP_DBP",
    "HR",
    "SpO2",
    "ETCO2",
    "Temp",
)

VENT_CHANNELS: tuple[str, ...] = (
    "FiO2",
    "MAC",
    "TV",
    "RR",
    "PEEP",
    "PIP",
)

ALL_CHANNELS: tuple[str, ...] = VITAL_CHANNELS + VENT_CHANNELS

# Static demographics fed alongside the time series.
STATIC_FEATURES: tuple[str, ...] = (
    "age",
    "sex",
    "height_cm",
    "weight_kg",
)

# Unified type dictionary for the ITE Transformer: demographics first
# (so type ids 0..len(STATIC_FEATURES)-1 are demographics), then all
# time-series channels. This is the table the model's `type_emb`
# embedding indexes into — DO NOT renumber without retraining.
TYPE_DICT: dict[str, int] = {
    **{name: i for i, name in enumerate(STATIC_FEATURES)},
    **{name: i + len(STATIC_FEATURES) for i, name in enumerate(ALL_CHANNELS)},
}
N_TYPES: int = len(TYPE_DICT)

# Labels available in the per-minute parquet — pick one for training.
LABEL_COLUMNS = {
    "d1": "in_event_d1",
    "d3": "in_event_d3",  # primary outcome (MAP<65 sustained >=3 min)
    "d5": "in_event_d5",
}
PRIMARY_LABEL = "in_event_d3"
