@echo off
setlocal
set "PYTHONPATH=%CD%"
set "PYTHONWARNINGS=error::ResourceWarning"
echo ===== O45 FULL REGRESSION =====
python -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 goto :fail
echo ===== O45 COMPILEALL =====
python -m compileall -q src
if errorlevel 1 goto :fail
echo ===== O44 GOVERNANCE SMOKE REGRESSION =====
python scripts\o44_governance_smoke.py
if errorlevel 1 goto :fail
echo ===== O45 EXECUTION SMOKE =====
python scripts\o45_execution_smoke.py
if errorlevel 1 goto :fail
echo ALL O45 VERIFICATION CHECKS PASSED.
exit /b 0
:fail
echo O45 VERIFICATION FAILED.
exit /b 1
