@echo off
setlocal

cd /d "%~dp0.."

set "PYTHONPATH=%CD%;%CD%\src;%CD%\src\core"
set "GATE_DIR=staging\release_gate"
if not exist "%GATE_DIR%" mkdir "%GATE_DIR%"

python -m unittest discover -s tests -p "test_*.py" -v > "%GATE_DIR%\full_regression.txt" 2>&1
if errorlevel 1 exit /b 1

python -m compileall -q src tests > "%GATE_DIR%\compileall.txt" 2>&1
if errorlevel 1 exit /b 1

set "TOKEN_FILE=staging\operator_token.txt"
if not exist "%TOKEN_FILE%" exit /b 1

set /p TOKEN=<"%TOKEN_FILE%"

curl -k -sS -i -X POST "https://localhost:8443/api/runs" -H "Content-Type: application/json" -H "Authorization: Bearer %TOKEN%" --data "{\"intent\":\"s30-staging-release-gate\"}" > "%GATE_DIR%\live_https_response.txt" 2>&1
if errorlevel 1 exit /b 1

findstr /c:"HTTP/1.1 200 OK" "%GATE_DIR%\live_https_response.txt" >nul
if errorlevel 1 exit /b 1

findstr /c:"\"authenticated\": true" "%GATE_DIR%\live_https_response.txt" >nul
if errorlevel 1 exit /b 1

findstr /c:"\"status\": \"ADMITTED\"" "%GATE_DIR%\live_https_response.txt" >nul
if errorlevel 1 exit /b 1

findstr /c:"\"external_action_executed\": false" "%GATE_DIR%\live_https_response.txt" >nul
if errorlevel 1 exit /b 1

findstr /c:"\"memory_write_executed\": false" "%GATE_DIR%\live_https_response.txt" >nul
if errorlevel 1 exit /b 1

exit /b 0
