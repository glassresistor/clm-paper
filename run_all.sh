#!/bin/bash
# Reproduce the full artifact: experiment -> figures -> paper.
# Requires python3 with matplotlib (figures) and a locally built pdflatex
# format in paper/ (already committed; see paper/build.sh).
set -euo pipefail
cd "$(dirname "$0")"
python3 clm_exp.py      # run the harness on stub backends -> exp-data/results.json
python3 make_figs.py    # data figures   -> paper/figures/fig_{tokens,tiers,phases,retention}.pdf
python3 make_arch.py    # architecture schematic -> paper/figures/fig_arch.pdf
bash paper/build.sh     # compile        -> paper/main.pdf
