@echo off
setlocal
set "PYTHONPATH=%CD%"
python -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 exit /b 1
python -m compileall -q .
if errorlevel 1 exit /b 1
python scripts\execution_intent_smoke.py
if errorlevel 1 exit /b 1
echo ALL PHASE 2 EXECUTION PLANNING CHECKS PASSED.
exit /b 0
