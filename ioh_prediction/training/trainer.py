"""Pure-PyTorch trainer for the ITE Transformer.

Intentionally small. The orchestration concerns belong to the train
script; this module handles only:

  - device auto-detection (CUDA -> MPS -> CPU)
  - AdamW + cosine-with-warmup
  - mixed precision on CUDA only (skipped on MPS/CPU)
  - gradient clipping
  - BCEWithLogitsLoss with optional `pos_weight`
  - per-epoch train/val metrics
  - best-checkpoint save based on a monitored metric
  - MLflow logging (params + per-epoch metrics + best ckpt artifact)
"""

from __future__ import annotations

import math
from contextlib import nullcontext
from dataclasses import asdict, dataclass, field
from pathlib import Path

import mlflow
import numpy as np
import torch
import torch.nn.functional as F
from torch import nn
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter

try:  # rich is a soft dep — fall back to plain prints if missing
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

from .losses import build_loss
from .metrics import binary_metrics, multiclass_metrics


# ---------- Device & optimizer helpers ----------


def auto_device(prefer: str | None = None) -> torch.device:
    """Pick the best available device unless `prefer` overrides."""
    if prefer:
        return torch.device(prefer)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def build_optimizer(
    model: nn.Module, lr: float, weight_decay: float
) -> torch.optim.Optimizer:
    """AdamW with weight-decay only on 2-D+ tensors (excludes biases / norms)."""
    decay, no_decay = [], []
    for p in model.parameters():
        if not p.requires_grad:
            continue
        (decay if p.dim() >= 2 else no_decay).append(p)
    return torch.optim.AdamW(
        [
            {"params": decay, "weight_decay": weight_decay},
            {"params": no_decay, "weight_decay": 0.0},
        ],
        lr=lr,
        betas=(0.9, 0.999),
    )


def build_scheduler(
    optimizer: torch.optim.Optimizer,
    total_steps: int,
    warmup_steps: int,
) -> torch.optim.lr_scheduler.LambdaLR:
    def lr_lambda(step: int) -> float:
        if step < warmup_steps:
            return step / max(1, warmup_steps)
        # Cosine from 1.0 -> 0.0 over the remaining steps.
        progress = (step - warmup_steps) / max(1, total_steps - warmup_steps)
        return 0.5 * (1.0 + math.cos(math.pi * progress))

    return torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda=lr_lambda)


# ---------- Config ----------


@dataclass
class TrainerConfig:
    # Optimizer
    lr: float = 3e-4
    weight_decay: float = 1e-2
    grad_clip: float = 1.0

    # Schedule
    epochs: int = 30
    warmup_frac: float = 0.05            # fraction of total steps for warmup

    # Loss
    loss_type: str = "cross_entropy"     # or "cosine_ce"
    cosine_ce_weight: float = 0.1
    # Per-class scalar weights for the CE term (shape == [num_classes]).
    # None = uniform.
    class_weights: list[float] | None = None
    num_classes: int = 2

    # Mixed precision
    use_amp: bool = True                 # enable torch.amp.autocast
    # "bfloat16" works on CUDA (Ampere+) and MPS (Apple Silicon, PyTorch
    # 2.3+); same dynamic range as FP32, no GradScaler needed.
    # "float16" works on older CUDA (Volta+) and on MPS but is less
    # stable; requires GradScaler to avoid gradient underflow.
    # Set use_amp=False to fall back to FP32.
    amp_dtype: str = "bfloat16"          # "bfloat16" | "float16"

    # Device
    device: str | None = None            # "cuda" | "mps" | "cpu" | None (auto)

    # MLflow
    experiment_name: str = "ioh-prediction"
    run_name: str | None = None
    tracking_uri: str = "sqlite:///mlflow.db"
    extra_params: dict = field(default_factory=dict)  # logged via mlflow.log_params

    # TensorBoard (set tb_log_dir to None to disable)
    tb_log_dir: str | None = "outputs/tb"

    # Checkpoints
    out_dir: str = "outputs/ckpts"
    monitor: str = "val_auroc"           # any val metric key; higher = better
    monitor_mode: str = "max"            # "max" or "min"
    patience: int = 5                    # early-stop on no improvement
    save_last: bool = True

    # Logging
    log_every_n_steps: int = 50
    # rich progress bar (live, in-place updates). Auto-disabled when
    # rich isn't installed. The bar is force-rendered as a "terminal" so
    # it still shows up when attached via `screen -r`; the trade-off is
    # that the log file captured by `tee` will contain ANSI control
    # codes. Strip them with: `sed -E 's/\x1b\[[0-9;]*[a-zA-Z]//g'`.
    use_rich_progress: bool = True


# ---------- Trainer ----------


class Trainer:
    def __init__(
        self,
        model: nn.Module,
        train_loader: DataLoader,
        val_loader: DataLoader,
        config: TrainerConfig = TrainerConfig(),
    ):
        self.config = config
        self.device = auto_device(config.device)
        self.model = model.to(self.device)
        self.train_loader = train_loader
        self.val_loader = val_loader

        self.criterion = build_loss(
            loss_type=config.loss_type,
            num_classes=config.num_classes,
            class_weights=config.class_weights,
            cosine_ce_weight=config.cosine_ce_weight,
        ).to(self.device)

        self.optimizer = build_optimizer(model, config.lr, config.weight_decay)
        total_steps = max(1, config.epochs * len(train_loader))
        warmup_steps = max(1, int(total_steps * config.warmup_frac))
        self.scheduler = build_scheduler(self.optimizer, total_steps, warmup_steps)

        # Mixed precision: autocast on both CUDA and MPS when available.
        # Bf16 is the default — works natively on Ampere+ NVIDIA cards and
        # on Apple Silicon, with FP32-equivalent dynamic range so we don't
        # need a GradScaler. Fp16 stays as an option for older hardware
        # but requires the scaler to avoid gradient underflow.
        amp_supported = self.device.type in ("cuda", "mps")
        self._use_amp = config.use_amp and amp_supported
        if self._use_amp:
            dtype_map = {"bfloat16": torch.bfloat16, "float16": torch.float16}
            if config.amp_dtype not in dtype_map:
                raise ValueError(
                    f"amp_dtype must be 'bfloat16' or 'float16', got {config.amp_dtype!r}"
                )
            self._amp_dtype = dtype_map[config.amp_dtype]
            self._amp_ctx = torch.amp.autocast(
                device_type=self.device.type, dtype=self._amp_dtype
            )
            # GradScaler is only needed for FP16 (FP16 range is too narrow
            # for naive backward to avoid gradient underflow). BF16 has the
            # same range as FP32, so we skip it. GradScaler currently only
            # supports CUDA; on MPS we run FP16 without scaling (works in
            # practice for shallow models but watch for NaN losses).
            if self._amp_dtype is torch.float16 and self.device.type == "cuda":
                self._scaler: torch.amp.GradScaler | None = torch.amp.GradScaler("cuda")
            else:
                self._scaler = None
        else:
            self._amp_dtype = torch.float32
            self._amp_ctx = nullcontext()
            self._scaler = None

        self.out_dir = Path(config.out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)

        # TensorBoard writer — None means TB is disabled.
        if config.tb_log_dir:
            tb_root = Path(config.tb_log_dir)
            run_tag = config.run_name or "run"
            self.tb_writer: SummaryWriter | None = SummaryWriter(
                log_dir=str(tb_root / run_tag)
            )
        else:
            self.tb_writer = None

        self._best_value: float | None = None
        self._best_path: Path | None = None
        self._epochs_since_improve = 0
        self._global_step = 0

    # ----- core loops -----

    def _train_epoch(
        self,
        epoch: int,
        progress: "Progress | None" = None,
        task_id: int | None = None,
    ) -> dict[str, float]:
        self.model.train()
        losses: list[float] = []
        for step, batch in enumerate(self.train_loader):
            data = batch["data"].to(self.device, non_blocking=True)
            mask = batch["mask"].to(self.device, non_blocking=True)
            # CrossEntropy expects integer class indices. See _val_epoch
            # for the MPS int64 round-trip caveat — train loop only
            # uses `label` on-device, so the issue doesn't surface here,
            # but the cast pattern stays consistent for readability.
            label = batch["label"].long().to(self.device, non_blocking=True)

            self.optimizer.zero_grad(set_to_none=True)
            with self._amp_ctx:
                logits = self.model(data, mask)
                loss = self.criterion(logits, label)

            if self._scaler is not None:
                self._scaler.scale(loss).backward()
                self._scaler.unscale_(self.optimizer)
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.config.grad_clip)
                self._scaler.step(self.optimizer)
                self._scaler.update()
            else:
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.config.grad_clip)
                self.optimizer.step()
            self.scheduler.step()

            losses.append(float(loss.item()))
            self._global_step += 1
            if self.tb_writer is not None:
                # Per-step scalars live under the same `train/` group as
                # the per-epoch ones, just with `step_*` names. TB
                # distinguishes them by their step axis automatically.
                self.tb_writer.add_scalar("train/step_loss", float(loss.item()), self._global_step)
                self.tb_writer.add_scalar(
                    "train/step_lr", self.optimizer.param_groups[0]["lr"], self._global_step
                )
            running = float(np.mean(losses[-self.config.log_every_n_steps :]))
            cur_lr = self.optimizer.param_groups[0]["lr"]
            if progress is not None and task_id is not None:
                progress.update(
                    task_id,
                    advance=1,
                    extra=f"loss={running:.4f}  lr={cur_lr:.2e}",
                )
            elif (step + 1) % self.config.log_every_n_steps == 0:
                print(f"  [epoch {epoch} step {step + 1}/{len(self.train_loader)}] loss={running:.4f}")

        return {"train_loss": float(np.mean(losses))}

    @torch.no_grad()
    def _val_epoch(self, epoch: int) -> dict[str, float]:
        self.model.eval()
        all_logits: list[np.ndarray] = []
        all_labels: list[np.ndarray] = []
        losses: list[float] = []

        for batch in self.val_loader:
            data = batch["data"].to(self.device, non_blocking=True)
            mask = batch["mask"].to(self.device, non_blocking=True)
            # Keep the CPU copy for metric collection — PyTorch MPS has a
            # known issue where int64 tensors round-tripped through .to(mps)
            # then .cpu() come back as uninitialized memory. Using the
            # original CPU long tensor directly avoids the corruption.
            label_cpu = batch["label"].long()
            label = label_cpu.to(self.device, non_blocking=True)
            with self._amp_ctx:
                logits = self.model(data, mask)
                loss = self.criterion(logits, label)
            losses.append(float(loss.item()))
            all_logits.append(logits.detach().float().cpu().numpy())
            all_labels.append(label_cpu.numpy())

        logits_arr = np.concatenate(all_logits)            # (N, C)
        labels_arr = np.concatenate(all_labels).astype(np.int64)
        probs = F.softmax(torch.from_numpy(logits_arr), dim=-1).numpy()

        # One-time diagnostic per epoch: shapes + label distribution.
        # Cheap and helpful when AUROC unexpectedly comes back NaN.
        print(
            f"  val diag: logits.shape={logits_arr.shape}  "
            f"labels.shape={labels_arr.shape}  "
            f"label_uniques={sorted(np.unique(labels_arr).tolist())}  "
            f"probs1 range=[{probs[:,1].min():.3f}, {probs[:,1].max():.3f}]  "
            f"any nan={bool(np.any(np.isnan(probs[:,1])))}"
        )

        if self.config.num_classes == 2:
            m = binary_metrics(probs[:, 1], labels_arr)
        else:
            m = multiclass_metrics(probs, labels_arr, self.config.num_classes)

        return {
            "val_loss": float(np.mean(losses)),
            "val_auroc": m["auroc"],
            "val_auprc": m["auprc"],
            "val_accuracy": m["accuracy"],
            "val_ppv": m["ppv"],
            "val_sensitivity": m["sensitivity"],
            "val_f1": m["f1"],
            "val_brier": m.get("brier", float("nan")),
        }

    # ----- checkpoint -----

    def _is_improvement(self, value: float) -> bool:
        if self._best_value is None or math.isnan(self._best_value):
            return not math.isnan(value)
        if self.config.monitor_mode == "max":
            return value > self._best_value
        return value < self._best_value

    def _save_checkpoint(self, epoch: int, metrics: dict, tag: str) -> Path:
        path = self.out_dir / f"{tag}.pt"
        torch.save(
            {
                "epoch": epoch,
                "model_state": self.model.state_dict(),
                "optimizer_state": self.optimizer.state_dict(),
                "scheduler_state": self.scheduler.state_dict(),
                "metrics": metrics,
                "config": asdict(self.config),
            },
            path,
        )
        return path

    # ----- public entrypoint -----

    def fit(self) -> dict:
        # If there's already an active run (started by an outer wrapper
        # like scripts/train.py), reuse it so post-train evaluation logs
        # into the same run. Otherwise open our own.
        outer_run = mlflow.active_run()
        if outer_run is None:
            mlflow.set_tracking_uri(self.config.tracking_uri)
            mlflow.set_experiment(self.config.experiment_name)
            run_ctx = mlflow.start_run(run_name=self.config.run_name)
        else:
            run_ctx = nullcontext()
        with run_ctx:
            mlflow.log_params(
                {
                    "device": str(self.device),
                    "epochs": self.config.epochs,
                    "lr": self.config.lr,
                    "weight_decay": self.config.weight_decay,
                    "grad_clip": self.config.grad_clip,
                    "warmup_frac": self.config.warmup_frac,
                    "loss_type": self.config.loss_type,
                    "cosine_ce_weight": self.config.cosine_ce_weight,
                    "class_weights": str(self.config.class_weights),
                    "num_classes": self.config.num_classes,
                    "use_amp": self._use_amp,
                    "amp_dtype": str(self._amp_dtype).removeprefix("torch."),
                    "batch_size": getattr(self.train_loader, "batch_size", "?"),
                    "monitor": self.config.monitor,
                    "tb_log_dir": self.config.tb_log_dir or "(disabled)",
                    **self.config.extra_params,
                }
            )

            history: list[dict] = []
            use_rich = self.config.use_rich_progress and _RICH_AVAILABLE
            if use_rich:
                # force_terminal=True so the bar still renders when
                # stdout is piped through `tee` inside a screen session.
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
                if progress is not None:
                    total_task = progress.add_task(
                        "[bold green]Total",
                        total=self.config.epochs,
                        extra="",
                    )
                else:
                    total_task = None

                for epoch in range(1, self.config.epochs + 1):
                    step_task = None
                    if progress is not None:
                        step_task = progress.add_task(
                            f"  epoch {epoch}/{self.config.epochs}",
                            total=len(self.train_loader),
                            extra="",
                        )
                    train_m = self._train_epoch(epoch, progress=progress, task_id=step_task)
                    if progress is not None and step_task is not None:
                        progress.remove_task(step_task)
                    val_m = self._val_epoch(epoch)
                    metrics = {**train_m, **val_m, "lr": self.optimizer.param_groups[0]["lr"]}
                    mlflow.log_metrics(metrics, step=epoch)
                    if self.tb_writer is not None:
                        # Split into two top-level groups so TB sidebars
                        # show `train/` and `val/` separately.
                        train_scalars = {
                            "train/loss": train_m["train_loss"],
                            "train/lr": metrics["lr"],
                        }
                        val_scalars = {
                            f"val/{k.removeprefix('val_')}": v
                            for k, v in val_m.items()
                            if isinstance(v, (int, float))
                        }
                        for tag, v in {**train_scalars, **val_scalars}.items():
                            if v == v:  # skip NaN
                                self.tb_writer.add_scalar(tag, float(v), epoch)
                    history.append({"epoch": epoch, **metrics})

                    epoch_summary = (
                        f"[epoch {epoch}/{self.config.epochs}] "
                        f"train_loss={train_m['train_loss']:.4f}  "
                        f"val_loss={val_m['val_loss']:.4f}  "
                        f"val_auroc={val_m['val_auroc']:.4f}  "
                        f"val_auprc={val_m['val_auprc']:.4f}  "
                        f"val_acc={val_m['val_accuracy']:.4f}  "
                        f"val_ppv={val_m['val_ppv']:.4f}"
                    )
                    if progress is not None:
                        progress.console.log(epoch_summary)
                    else:
                        print(epoch_summary)

                    monitor_value = metrics[self.config.monitor]
                    if self._is_improvement(monitor_value):
                        self._best_value = monitor_value
                        self._best_path = self._save_checkpoint(epoch, metrics, tag="best")
                        self._epochs_since_improve = 0
                        msg = f"  ✓ new best {self.config.monitor} = {monitor_value:.4f}"
                        if progress is not None:
                            progress.console.log(msg)
                        else:
                            print(msg)
                    else:
                        self._epochs_since_improve += 1

                    if self.config.save_last:
                        self._save_checkpoint(epoch, metrics, tag="last")

                    if progress is not None and total_task is not None:
                        progress.update(
                            total_task,
                            advance=1,
                            extra=(
                                f"best {self.config.monitor}="
                                f"{self._best_value:.4f}" if self._best_value is not None else ""
                            ),
                        )

                    if self._epochs_since_improve >= self.config.patience:
                        msg = (
                            f"Early stop: no improvement in {self.config.monitor} "
                            f"for {self.config.patience} epochs."
                        )
                        if progress is not None:
                            progress.console.log(msg)
                        else:
                            print(msg)
                        break

            if self._best_path is not None and self._best_path.exists():
                mlflow.log_artifact(str(self._best_path))

            if self.tb_writer is not None:
                self.tb_writer.flush()
                self.tb_writer.close()

            return {
                "history": history,
                "best_value": self._best_value,
                "best_ckpt": str(self._best_path) if self._best_path else None,
            }
