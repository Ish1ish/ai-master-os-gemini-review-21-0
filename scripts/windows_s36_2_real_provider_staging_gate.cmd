@echo off
cd /d "%~dp0.."
set "PYTHONPATH=%CD%;%CD%\src;%CD%\src\core"
python scripts\s36_2_real_provider_staging_gate.py
