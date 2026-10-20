#!/bin/bash
# Compile the clm-mem arXiv paper with the locally built LaTeX format.
cd "$(dirname "$0")"
export TEXINPUTS=".::./texsrc//:"
export TEXFONTMAPS=".:.:/usr/share/texmf-dist/fonts/map/dvips/tetex"
export TEX_MKTEX_FMT=0
pdftex -fmt=pdflatex -interaction=nonstopmode "$@" main.tex
