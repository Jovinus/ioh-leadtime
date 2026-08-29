#!/usr/bin/env bash
# Run external evaluation (VitalDB + MOVER) for every gap_* run directory.
# Sequential by design — single GPU, predictable failure isolation.
set -uo pipefail

GAPS="${GAPS:-0 5 10 15 20 25 30}"
SOURCES="${SOURCES:-vitaldb mover}"
RUNS_ROOT="outputs/runs"

ts() { date '+%Y-%m-%dT%H:%M:%S%z'; }

ok=0; fail=0
for g in $GAPS; do
  rd="${RUNS_ROOT}/gap${g}"
  if [[ ! -d "$rd" ]]; then
    echo "[$(ts)] SKIP gap=$g — no run dir at $rd"
    continue
  fi
  for s in $SOURCES; do
    echo
    echo "=== external eval: gap=$g source=$s  ($(ts)) ==="
    # --no-capture-output: conda run otherwise buffers the child's stdout,
    # which swallows the rich progress bar from online_inference.score_manifest.
    if conda run --no-capture-output -n torch python scripts/evaluate_external.py \
        --run-dir "$rd" --source "$s"; then
      ok=$((ok+1))
    else
      fail=$((fail+1))
      echo "!! FAILED: gap=$g source=$s"
    fi
  done
done

echo
echo "=== EXTERNAL SWEEP DONE  ($(ts)) ==="
echo "  ok:     $ok"
echo "  failed: $fail"
