@echo off
setlocal
cd /d "%~dp0.."
set "PYTHONPATH=%CD%"
set "PYTHONWARNINGS=error::ResourceWarning"
python -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 exit /b 1
python scripts\execution_observability_smoke.py
if errorlevel 1 exit /b 1
