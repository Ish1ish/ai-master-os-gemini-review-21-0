@echo off
setlocal
cd /d "%~dp0.."
set "PYTHONPATH=%CD%"
set "PYTHONPATH=%CD%"
set "PYTHONWARNINGS=error::ResourceWarning"
echo ===== O43 WINDOWS VERIFICATION =====
python -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 exit /b 1
python -m compileall -q src engines scripts tests
if errorlevel 1 exit /b 1
python scripts\o43_learning_smoke.py
if errorlevel 1 exit /b 1
echo ALL O43 VERIFICATION CHECKS PASSED.
endlocal
