@echo off
setlocal
cd /d "%~dp0.."

set "PYTHONPATH=%CD%;%CD%\src;%CD%\src\core"

python scripts\s34_identity_secret_contract_gate.py > "staging\ops_snapshot\s34_identity_secret_contract.txt" 2>&1
if errorlevel 1 exit /b 1

type "staging\ops_snapshot\s34_identity_secret_contract.txt"
exit /b 0
