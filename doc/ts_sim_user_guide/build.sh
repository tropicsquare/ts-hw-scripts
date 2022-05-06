#!/bin/bash

rm -rf build
mkdir -p build/pdf

export GITTAG=$(git describe --tags --abbrev=0 HEAD)
export GITREV=$(git describe --tags HEAD)

pdflatex -output-directory=build/pdf ts_sim_user_guide.tex
pdflatex -output-directory=build/pdf ts_sim_user_guide.tex
