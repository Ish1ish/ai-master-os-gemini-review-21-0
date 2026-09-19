@echo off
cd /d "%~dp0.."
set "PYTHONPATH=%CD%;%CD%\src;%CD%\src\core"
python scripts\s36_3_runtime_provider_wiring_gate.py
