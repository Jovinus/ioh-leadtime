#!/usr/bin/env bash
# Full baseline pipeline: train -> external val (vitaldb) -> external val (mover).
# Run inside a screen session so the long job survives disconnects.
# All output is teed to outputs/baseline_full.log.

set -u  # error on undefined vars; don't use -e so that a stage failure still
        # surfaces in the log instead of being silently swallowed by screen exit.

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p outputs

EPOCHS="${EPOCHS:-50}"
RUN_DIR="outputs/runs/baseline_epic"
# Extra dotted overrides forwarded to scripts/train.py. Space-separated.
# Examples:
#   EXTRA_OVERRIDES="train.batch_size=64"
#   EXTRA_OVERRIDES="train.batch_size=64 train.lr=6e-4 train.num_workers=2"
# MPS note: BS=128 with M=2048 and n_heads=4 hits INT_MAX inside MPSGraph
# during attention backward (BS * n_heads * (M+1)^2 > 2^31-1). Use BS=64
# (or anything ≤ 96) when running locally on Apple Silicon.
EXTRA_OVERRIDES="${EXTRA_OVERRIDES:-}"

echo "=== STAGE 0: env ==="
echo "  date:   $(date)"
echo "  pwd:    $(pwd)"
echo "  python: $(which python)"
python -c "import torch; print(f'  torch:  {torch.__version__}'); print(f'  mps:    {torch.backends.mps.is_available()}'); print(f'  cuda:   {torch.cuda.is_available()}')"
echo

echo "=== STAGE 1: train (${EPOCHS} epochs on EPIC) ==="
# shellcheck disable=SC2086  # we intentionally word-split EXTRA_OVERRIDES.
python scripts/train.py \
    --config configs/experiment/baseline_epic.yaml \
    --override "train.epochs=${EPOCHS}" ${EXTRA_OVERRIDES}
rc=$?
echo "  stage1 exit=${rc}"
if [ "${rc}" != "0" ]; then
    echo "TRAIN FAILED, skipping external validation stages."
    exit "${rc}"
fi

echo
echo "=== STAGE 2: external validation on VitalDB ==="
python scripts/evaluate_external.py \
    --run-dir "${RUN_DIR}" \
    --source vitaldb
echo "  stage2 exit=$?"

echo
echo "=== STAGE 3: external validation on MOVER SIS ==="
python scripts/evaluate_external.py \
    --run-dir "${RUN_DIR}" \
    --source mover
echo "  stage3 exit=$?"

echo
echo "=== ALL STAGES DONE  ($(date)) ==="
