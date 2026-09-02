@echo off
title ALTAIR Quant Lab - Jupyter Notebook
echo ======================================================================
echo Starting ALTAIR Swing Trade Engine (STE) Quantitative Research Lab...
echo ======================================================================
cd /d "%~dp0"
python -m notebook --notebook-dir="%~dp0" --port=8888
pause
