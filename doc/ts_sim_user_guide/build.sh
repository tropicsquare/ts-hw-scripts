#!/bin/bash

rm -rf build
mkdir build
mkdir build/pdf

pdflatex -output-directory=build/pdf ts_sim_user_guide.tex
pdflatex -output-directory=build/pdf ts_sim_user_guide.tex
