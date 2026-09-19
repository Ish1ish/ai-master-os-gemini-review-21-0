@echo off
cd /d "%~dp0.."
set "PYTHONPATH=%CD%;%CD%\src;%CD%\src\core"
python scripts\s36_1_provider_adapter_discovery.py
