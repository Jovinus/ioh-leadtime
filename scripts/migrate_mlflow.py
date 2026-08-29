"""Migrate runs from the file-based MLflow store to a SQLite store.

MLflow 3.x deprecates `file:./mlruns` and the Overview tab no longer
works against the file backend. This helper copies every experiment +
run from the source store (file or sqlite) into a destination SQLite
store, preserving params, metrics (with step + timestamp), tags, and
artifacts.

Usage:
    conda run -n torch python scripts/migrate_mlflow.py \
        --src "file:./mlruns" --dst "sqlite:///mlflow.db"
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import mlflow
from mlflow.entities import RunStatus
from mlflow.tracking import MlflowClient


def _ensure_experiment(dst_client: MlflowClient, src_exp) -> str:
    """Create-or-get an experiment in the destination by name."""
    existing = dst_client.get_experiment_by_name(src_exp.name)
    if existing is not None:
        return existing.experiment_id
    return dst_client.create_experiment(name=src_exp.name)


def _copy_run(src_client: MlflowClient, dst_client: MlflowClient, src_run, dst_exp_id: str) -> str:
    """Create a new run in `dst_exp_id` mirroring `src_run`. Returns dst run_id."""
    info = src_run.info
    run_name = src_run.data.tags.get("mlflow.runName")
    dst_run = dst_client.create_run(
        experiment_id=dst_exp_id,
        start_time=info.start_time,
        run_name=run_name,
    )
    dst_run_id = dst_run.info.run_id

    # Tags
    for k, v in src_run.data.tags.items():
        if k.startswith("mlflow.") and k not in ("mlflow.runName", "mlflow.source.git.commit"):
            # Skip mlflow-internal tags that the client manages itself,
            # except a few that are safe to carry.
            continue
        dst_client.set_tag(dst_run_id, k, v)

    # Params
    for k, v in src_run.data.params.items():
        dst_client.log_param(dst_run_id, k, v)

    # Metrics: replay every (step, value, timestamp) so chart shape is preserved.
    for metric_key in src_run.data.metrics.keys():
        history = src_client.get_metric_history(info.run_id, metric_key)
        for m in history:
            dst_client.log_metric(
                dst_run_id, metric_key, m.value, timestamp=m.timestamp, step=m.step
            )

    # Artifacts: download to a tmpdir, then upload preserving relative paths.
    with tempfile.TemporaryDirectory() as tmp:
        try:
            local_root = src_client.download_artifacts(info.run_id, "", tmp)
        except Exception as exc:
            print(f"  warn: artifact download failed for run {info.run_id}: {exc}")
            local_root = None
        if local_root and Path(local_root).exists():
            for item in Path(local_root).iterdir():
                if item.is_dir():
                    dst_client.log_artifacts(dst_run_id, str(item), artifact_path=item.name)
                else:
                    dst_client.log_artifact(dst_run_id, str(item))

    # Terminate the run with the original status if it was terminal.
    if info.status in (RunStatus.to_string(RunStatus.FINISHED), "FINISHED"):
        dst_client.set_terminated(dst_run_id, status="FINISHED", end_time=info.end_time)
    elif info.status in (RunStatus.to_string(RunStatus.FAILED), "FAILED"):
        dst_client.set_terminated(dst_run_id, status="FAILED", end_time=info.end_time)
    return dst_run_id


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--src", default="file:./mlruns", help="source tracking URI")
    p.add_argument("--dst", default="sqlite:///mlflow.db", help="destination tracking URI")
    p.add_argument(
        "--purge-dst",
        action="store_true",
        help="If dst is sqlite, delete its file first.",
    )
    args = p.parse_args()

    if args.purge_dst and args.dst.startswith("sqlite:///"):
        dst_path = Path(urlparse(args.dst).path.lstrip("/"))
        if dst_path.exists():
            print(f"removing existing {dst_path}")
            dst_path.unlink()

    src_client = MlflowClient(tracking_uri=args.src)
    dst_client = MlflowClient(tracking_uri=args.dst)

    src_experiments = src_client.search_experiments()
    print(f"src experiments: {len(src_experiments)}")

    n_runs = 0
    for src_exp in src_experiments:
        if src_exp.name == "Default":
            # Skip the default empty experiment.
            pass
        dst_exp_id = _ensure_experiment(dst_client, src_exp)
        runs = src_client.search_runs(experiment_ids=[src_exp.experiment_id], max_results=10000)
        print(f"  {src_exp.name}: {len(runs)} run(s)")
        for r in runs:
            _copy_run(src_client, dst_client, r, dst_exp_id)
            n_runs += 1
    print(f"done. migrated {n_runs} run(s) to {args.dst}")


if __name__ == "__main__":
    sys.exit(main() or 0)
