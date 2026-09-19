@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "PYTHONPATH=%CD%"
set "PYTHONWARNINGS=error::ResourceWarning"
python -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 exit /b 1
python -m compileall -q .
if errorlevel 1 exit /b 1
echo [3/3] O41 semantic opportunity-quality regression suite...
python run_evaluation.py
if errorlevel 1 exit /b 1
echo ALL O41 OFFLINE DECISION QUALITY CHECKS PASSED.
exit /b 0
