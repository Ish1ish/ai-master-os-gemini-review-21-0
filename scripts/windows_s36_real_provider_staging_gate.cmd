@echo off
setlocal
cd /d "%~dp0.."

set "PYTHONPATH=%CD%;%CD%\src;%CD%\src\core"

python scripts\s36_real_provider_staging_gate.py
if errorlevel 1 exit /b 1

type staging\provider_evidence\s36_provider_evidence.json
exit /b 0
