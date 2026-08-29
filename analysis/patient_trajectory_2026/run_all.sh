#!/usr/bin/env bash
# Reproduce the trajectory and observability steps this paper reads, from cached per-minute
# scores.  The cached scores are patient-level derived data and are not redistributable, so
# these steps do not run from a clean checkout; the aggregate CSVs they produce ship beside
# them and are what the paper's tables and figures are built from.
#
# Do not wrap this in `conda run -n torch bash -lc`: the login shell re-runs conda init and
# resolves python to base.  Activate the environment first, then run this.
set -euo pipefail
cd "$(dirname "$0")"

python a4_event_control_divergence.py
python a6_window_trend.py
python a7_observability.py
