#!/usr/bin/env bash
# Lead-time / gap sweep on EPIC. For each gap g in $GAPS, retrain from
# scratch with `data.pos_gap_min=g` so positives' ref_time becomes
# `first_onset - g`, write artefacts under outputs/runs/gap${g}/, and
# leave per-gap test-split predictions for the aggregator.
#
# External (VitalDB, MOVER) evals are NOT run inside the sweep — the
# clinical-faithfulness summary in this experiment is EPIC test-split
# only (memory: project-gap-sweep-eval). Pick the chosen gap and run
# scripts/evaluate_external.py separately if you want external numbers.
#
# Always invoke through a screen session — full sweep on EPIC takes
# hours.
#
# Env vars (all optional, sensible defaults):
#   GAPS="0 5 10 15 20 25 30"   space-separated gap values, in minutes
#   EPOCHS=50                   epochs per gap
#   BASE_CONFIG=configs/experiment/baseline_epic.yaml
#   EXTRA_OVERRIDES=...         forwarded to train.py per gap
#   RUN_PREFIX=gap              outputs/runs/${RUN_PREFIX}${g}
#   RUN_NAME_PREFIX=baseline_epic_gap   MLflow run_name prefix
#   SKIP_EXISTING=1             skip a gap if its out_dir already has best.pt

set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p outputs

GAPS="${GAPS:-0 5 10 15 20 25 30}"
EPOCHS="${EPOCHS:-50}"
BASE_CONFIG="${BASE_CONFIG:-configs/experiment/baseline_epic.yaml}"
EXTRA_OVERRIDES="${EXTRA_OVERRIDES:-}"
RUN_PREFIX="${RUN_PREFIX:-gap}"
RUN_NAME_PREFIX="${RUN_NAME_PREFIX:-baseline_epic_gap}"
SKIP_EXISTING="${SKIP_EXISTING:-1}"

echo "=== STAGE 0: env ==="
echo "  date:           $(date)"
echo "  pwd:            $(pwd)"
echo "  python:         $(which python)"
echo "  gaps:           ${GAPS}"
echo "  epochs/gap:     ${EPOCHS}"
echo "  base config:    ${BASE_CONFIG}"
echo "  extra overrides:${EXTRA_OVERRIDES}"
python -c "import torch; print(f'  torch:          {torch.__version__}'); print(f'  mps:            {torch.backends.mps.is_available()}'); print(f'  cuda:           {torch.cuda.is_available()}')"
echo

fail_count=0
skip_count=0
ok_count=0
for g in ${GAPS}; do
    run_dir="outputs/runs/${RUN_PREFIX}${g}"
    run_name="${RUN_NAME_PREFIX}${g}"
    if [ "${SKIP_EXISTING}" = "1" ] && [ -f "${run_dir}/ckpts/best.pt" ]; then
        echo "=== gap=${g}: SKIP (already has ${run_dir}/ckpts/best.pt) ==="
        skip_count=$((skip_count + 1))
        continue
    fi

    echo "=== gap=${g}: TRAIN ($(date)) ==="
    echo "  run_dir:  ${run_dir}"
    echo "  run_name: ${run_name}"

    # shellcheck disable=SC2086  # intentionally word-split EXTRA_OVERRIDES
    python scripts/train.py \
        --config "${BASE_CONFIG}" \
        --override \
            "train.epochs=${EPOCHS}" \
            "data.pos_gap_min=${g}" \
            "experiment.run_name=${run_name}" \
            "paths.out_dir=${run_dir}" \
            "paths.manifest_path=${run_dir}/manifest.csv" \
            "paths.normalizer_path=${run_dir}/normalizer.parquet" \
            ${EXTRA_OVERRIDES}
    rc=$?
    if [ "${rc}" != "0" ]; then
        echo "  gap=${g}: TRAIN FAILED (exit=${rc}); continuing sweep"
        fail_count=$((fail_count + 1))
    else
        ok_count=$((ok_count + 1))
    fi
    echo
done

echo "=== SWEEP DONE  ($(date)) ==="
echo "  ok:      ${ok_count}"
echo "  skipped: ${skip_count}"
echo "  failed:  ${fail_count}"
if [ "${ok_count}" -gt 0 ] || [ "${skip_count}" -gt 0 ]; then
    echo
    echo "Next: python scripts/aggregate_gap_sweep.py --runs-glob 'outputs/runs/${RUN_PREFIX}*' --out outputs/gap_sweep_summary"
fi
exit "${fail_count}"
