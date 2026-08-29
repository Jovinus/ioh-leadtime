#!/usr/bin/env bash
# Reproduce N1-N5 from cached per-minute scores.
#
# step0_repro comes first and halts the pipeline on any disagreement with B1b, so a null is
# never computed for a statistic other than the one it is placed beside.  It checks two
# things: that `per_case_leads` reproduces `b1b_lead_vs_observation.csv`, and that the dense
# elapsed-grid crossing N2 uses agrees exactly with B1b's groupby implementation.
#
# Do not wrap this in `conda run -n torch bash -lc`: the login shell re-runs conda init and
# resolves python to base.  Activate the environment first, then run this.
set -euo pipefail
cd "$(dirname "$0")"

python step0_repro.py
python n1_uniform_placement.py
python n2_score_shuffle.py
python n3_stratified.py
python n4_band_detection.py
python n5_time_to_alert.py
python collect_results.py
