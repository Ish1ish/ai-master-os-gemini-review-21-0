@echo off
setlocal
cd /d "%~dp0.."
set "PYTHONPATH=%CD%;%CD%\src;%CD%\src\core"

if not exist "tools\caddy\caddy.exe" exit /b 1
if not exist "tools\caddy\Caddyfile" exit /b 1

tools\caddy\caddy.exe validate --config tools\caddy\Caddyfile >nul 2>&1
if errorlevel 1 exit /b 1

python scripts\s35_edge_network_contract_gate.py
if errorlevel 1 exit /b 1

type staging\ops_snapshot\s35_edge_network_contract.json
exit /b 0
