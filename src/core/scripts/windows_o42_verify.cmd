@echo off
setlocal
cd /d "%~dp0.."
set "PYTHONPATH=%CD%"
set "PYTHONWARNINGS=error::ResourceWarning"
echo ===== O42 WINDOWS VERIFICATION =====
python -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 exit /b 1
python -m compileall -q src engines scripts tests
if errorlevel 1 exit /b 1
python scripts\o42_validation_smoke.py
if errorlevel 1 exit /b 1
echo ALL O42 VERIFICATION CHECKS PASSED.
endlocal
