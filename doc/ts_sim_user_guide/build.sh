#!/bin/bash

rm -rf build
mkdir -p build/pdf

pdflatex -output-directory=build/pdf --shell-escape ts_sim_user_guide.tex
pdflatex -output-directory=build/pdf --shell-escape ts_sim_user_guide.tex
