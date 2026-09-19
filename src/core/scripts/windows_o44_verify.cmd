@echo off
setlocal
set "PYTHONPATH=%CD%"
set "PYTHONWARNINGS=error::ResourceWarning"
echo ===== O44 BACKEND TESTS =====
python -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 goto :fail
echo ===== O44 COMPILEALL =====
python -m compileall -q src
if errorlevel 1 goto :fail
echo ===== O44 GOVERNANCE SMOKE =====
python scripts\o44_governance_smoke.py
if errorlevel 1 goto :fail
echo ALL O44 GOVERNANCE VERIFICATION CHECKS PASSED.
exit /b 0
:fail
echo O44 GOVERNANCE VERIFICATION FAILED.
exit /b 1
