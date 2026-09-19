@echo off
setlocal
set "PYTHONPATH=%CD%"
set "PYTHONWARNINGS=error::ResourceWarning"
echo ===== O46 FULL REGRESSION =====
python -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 goto :fail
echo ===== O46 COMPILEALL =====
python -m compileall -q src
if errorlevel 1 goto :fail
echo ===== O44 GOVERNANCE SMOKE REGRESSION =====
python scripts\o44_governance_smoke.py
if errorlevel 1 goto :fail
echo ===== O45 EXECUTION SMOKE REGRESSION =====
python scripts\o45_execution_smoke.py
if errorlevel 1 goto :fail
echo ===== O46 GOVERNED LOOP SMOKE =====
python scripts\o46_governed_loop_smoke.py
if errorlevel 1 goto :fail
echo ALL O46 VERIFICATION CHECKS PASSED.
exit /b 0
:fail
echo O46 VERIFICATION FAILED.
exit /b 1
