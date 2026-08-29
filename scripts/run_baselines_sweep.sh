#!/usr/bin/env bash
# Full baseline gap sweep: {logreg,rf,xgb,lstm} x GAPS, each with test + externals.
# Writes outputs/runs/<model>_gap<g>/. Tabular models first (fast), LSTM last.
#   GAPS="0 5 10 15 20 25 30"  MODELS="logreg rf xgb lstm"  bash scripts/run_baselines_sweep.sh
set -uo pipefail
cd "$(dirname "$0")/.."

GAPS="${GAPS:-0 5 10 15 20 25 30}"
MODELS="${MODELS:-logreg rf xgb lstm}"
EPOCHS="${EPOCHS:-40}"

for m in $MODELS; do
  for g in $GAPS; do
    echo "==================== $m gap$g ===================="
    python scripts/train_baselines.py --gap "$g" --model "$m" --epochs "$EPOCHS" \
      || echo "!!! FAILED: $m gap$g (continuing)"
  done
done
echo "SWEEP COMPLETE"
