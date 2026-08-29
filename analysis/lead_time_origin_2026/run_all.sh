#!/usr/bin/env bash
# Reproduce B1-B4 from cached per-minute scores and the source per-minute MAP series.
#
# step0_repro comes first and halts the pipeline on any disagreement with a published
# number, so a later step never runs against a cohort or an operating point that has
# silently shifted.  It checks Table 2 three ways: against the values printed in the
# manuscript, against the source CSV those were read from, and against a fresh
# recomputation of the alarm rule from the cached scores.
#
# Do not wrap this in `conda run -n torch bash -lc`: the login shell re-runs conda init
# and resolves python to base.  Activate the environment first, then run this.
set -euo pipefail
cd "$(dirname "$0")"

python step0_repro.py
python b1_prevalent_incident.py
python b1b_suppression.py
python b2_departure_timing.py
python b3_cross_family_path.py
python b4_divergence_asymmetry.py
python make_nt_figure.py
python collect_results.py

# The one-file record for circulation (manuscript + supplement + every analysis + the
# decision package + the opinion), and its DOCX. pandoc lives in base, not torch.
#   conda run -n torch python analysis/build_full_record.py
#   PATH="/opt/anaconda3/bin:$PATH" pandoc analysis/FULL_RECORD.md \
#     --from=gfm+superscript --resource-path=analysis --to=docx --toc --toc-depth=2 \
#     --output=analysis/FULL_RECORD.docx
#   conda run -n torch python analysis/fix_docx_tables.py analysis/FULL_RECORD.docx
