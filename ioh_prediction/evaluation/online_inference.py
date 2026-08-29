"""Per-case online inference: score every minute of every case.

For a single case parquet, builds a `(W=window_min, C)` triplet input at
each minute `t` in `[induction_drop, T-1]` and runs the model in eval mode
to produce a `score(t)` trajectory. The `ref_time_min` from the manifest
is *not* used here — at deployment the model sees no event labels.

Output format:
  DataFrame with columns:
    case_id, source, t_min, t_to_event (NaN for negatives), score, label

`t_to_event` is computed against the manifest's `ref_time_min`. For positives,
`ref_time_min` is real onset minus the training gap; for negatives it is a
gap-shifted sampled pseudo-onset. Therefore, for positives:
  t_to_event = ref_time_min - t_min
  real minutes before onset = t_to_event + training_gap
and `t_to_event >= 0` means "before the model's reference time", not necessarily
"before onset" when a non-zero gap is used.
For negatives:
  t_to_event = pseudo_ref_time_min - t_min   (used for symmetric binning)

This matches the AKI repo `online_inference` convention.
"""

from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn

from ..data.collate import CollateConfig, RefTimeCollate
from ..data.eligibility import induction_drop_for
from ..data.normalize import NormalizerStats
from ..data.schema import ALL_CHANNELS, STATIC_FEATURES

try:  # rich is a soft dep — fall back to a plain loop if missing
    from rich.console import Console
    from rich.progress import (
        BarColumn,
        MofNCompleteColumn,
        Progress,
        TextColumn,
        TimeElapsedColumn,
        TimeRemainingColumn,
    )

    _RICH_AVAILABLE = True
except ImportError:  # pragma: no cover
    _RICH_AVAILABLE = False


@dataclass(frozen=True)
class OnlineInferenceConfig:
    window_min: int = 120
    max_seq_len: int = 2048
    batch_size: int = 64
    # If true, also score at minutes after ref_time_min (right-censored
    # region). For "stable score after onset" hypothesis testing.
    include_post_ref: bool = True


@torch.no_grad()
def score_case(
    model: nn.Module,
    collate: RefTimeCollate,
    case_row: pd.Series,
    device: torch.device,
    config: OnlineInferenceConfig = OnlineInferenceConfig(),
) -> pd.DataFrame:
    """Score every minute of one case. Returns a per-minute DataFrame."""
    source = str(case_row["source"])
    drop = induction_drop_for(source)
    ref_t = int(case_row["ref_time_min"])
    parquet_path = case_row["parquet_path"]
    # Match the Dataset's NA-tolerant cast (pandas nullable dtypes like
    # Int8 produce pd.NA, which np.array(..., dtype=float32) rejects).
    static_vec = pd.to_numeric(
        pd.Series([case_row[f] for f in STATIC_FEATURES]),
        errors="coerce",
    ).to_numpy(dtype=np.float32)

    df = pd.read_parquet(parquet_path).sort_values("t_min").reset_index(drop=True)
    T = int(df["t_min"].max()) + 1
    last_t = T - 1
    if not config.include_post_ref:
        last_t = min(last_t, ref_t)

    anchor_minutes = list(range(drop, last_t + 1))
    if not anchor_minutes:
        return pd.DataFrame(
            columns=["case_id", "source", "t_min", "t_to_event", "score", "label"]
        )

    # For each anchor minute t, build a one-case-batch item matching the
    # IOHRefTimeDataset interface and let `collate` produce the tensor.
    out_rows: list[dict] = []
    items: list[dict] = []
    for t in anchor_minutes:
        lo = max(drop, t - config.window_min)
        window = df[(df["t_min"] >= lo) & (df["t_min"] < t)]
        vitals = window[list(ALL_CHANNELS)].to_numpy(dtype=np.float32)
        tmin = window["t_min"].to_numpy(dtype=np.int32)
        items.append(
            {
                "case_id": str(case_row["case_id"]),
                "source": source,
                "ref_time_min": int(t),  # so collate's t_offset is relative to "now"
                "label": float(case_row["label"]),
                "vitals": vitals,
                "t_min": tmin,
                "static": static_vec,
            }
        )

    # Process in batches.
    n_anchors = len(items)
    for start in range(0, n_anchors, config.batch_size):
        chunk = items[start : start + config.batch_size]
        batch = collate(chunk)
        data = batch["data"].to(device, non_blocking=True)
        mask = batch["mask"].to(device, non_blocking=True)
        # logits: (B, num_classes). Apply softmax along the class axis
        # and take the positive-class probability (index [1]) for the
        # binary case. For multi-class extensions, callers can reach
        # into `score_case` and use the full softmax instead.
        logits = model(data, mask).float().cpu().numpy()
        ex = np.exp(logits - logits.max(axis=-1, keepdims=True))
        softmax = ex / ex.sum(axis=-1, keepdims=True)
        probs = softmax[:, 1]
        for i, item in enumerate(chunk):
            t = item["ref_time_min"]
            out_rows.append(
                dict(
                    case_id=item["case_id"],
                    source=item["source"],
                    t_min=t,
                    t_to_event=int(ref_t - t),
                    score=float(probs[i]),
                    label=int(case_row["label"]),
                )
            )

    return pd.DataFrame(out_rows)


@torch.no_grad()
def score_manifest(
    model: nn.Module,
    normalizer: NormalizerStats,
    manifest: pd.DataFrame,
    device: torch.device,
    config: OnlineInferenceConfig = OnlineInferenceConfig(),
    progress_desc: str | None = "Scoring cases",
) -> pd.DataFrame:
    """Score every case in a manifest. Returns the concatenated trajectory.

    A rich progress bar is rendered when `progress_desc` is non-empty and
    `rich` is installed; pass `progress_desc=None` (or `""`) to silence it.
    """
    model.eval()
    collate = RefTimeCollate(
        normalizer,
        CollateConfig(max_seq_len=config.max_seq_len),
    )
    n_cases = len(manifest)
    frames: list[pd.DataFrame] = []

    use_rich = bool(progress_desc) and _RICH_AVAILABLE and n_cases > 0
    if use_rich:
        # force_terminal=True so the bar still renders when stdout is
        # piped through `tee` inside a screen session (matches trainer.py).
        console = Console(force_terminal=True)
        progress = Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=40),
            MofNCompleteColumn(),
            TextColumn("{task.fields[extra]}"),
            TextColumn("•"),
            TimeElapsedColumn(),
            TextColumn("•"),
            TimeRemainingColumn(),
            console=console,
            refresh_per_second=4,
            transient=False,
        )
    else:
        progress = None

    with progress if progress is not None else nullcontext():
        task_id = (
            progress.add_task(progress_desc, total=n_cases, extra="")
            if progress is not None
            else None
        )
        for _, row in manifest.iterrows():
            frames.append(score_case(model, collate, row, device, config))
            if progress is not None and task_id is not None:
                progress.update(
                    task_id,
                    advance=1,
                    extra=f"case={row['case_id']}",
                )

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def save_predictions(df: pd.DataFrame, path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
