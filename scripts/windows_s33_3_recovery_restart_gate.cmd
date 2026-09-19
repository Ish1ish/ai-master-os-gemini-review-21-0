@echo off
setlocal
cd /d "%~dp0.."

set "PYTHONPATH=%CD%;%CD%\src;%CD%\src\core"

python scripts\s33_3_refresh_operator_token.py
if errorlevel 1 exit /b 1

if not exist "config\o39_operations_manifest.json" exit /b 1
if not exist "scripts\windows_s32_ops_stop.cmd" exit /b 1
if not exist "scripts\windows_s32_ops_start.cmd" exit /b 1
if not exist "staging\operator_token.txt" exit /b 1
if not exist "staging\ops_snapshot" mkdir "staging\ops_snapshot"

call scripts\windows_s32_ops_stop.cmd
if errorlevel 1 exit /b 1

for /l %%N in (1,1,15) do (
    netstat -ano | findstr ":8091" | findstr "LISTENING" >nul
    if errorlevel 1 goto :port8091_down
    ping 127.0.0.1 -n 2 >nul
)
exit /b 1

:port8091_down
for /l %%N in (1,1,15) do (
    netstat -ano | findstr ":8443" | findstr "LISTENING" >nul
    if errorlevel 1 goto :ports_down
    ping 127.0.0.1 -n 2 >nul
)
exit /b 1

:ports_down
call scripts\windows_s32_ops_start.cmd
if errorlevel 1 exit /b 1

call scripts\windows_s32_ops_status.cmd
if errorlevel 1 exit /b 1

set "TOKEN_FILE=staging\operator_token.txt"
set /p TOKEN=<"%TOKEN_FILE%"

curl -k -sS -i -X POST "https://localhost:8443/api/runs" -H "Content-Type: application/json" -H "Authorization: Bearer %TOKEN%" --data "{\"intent\":\"s33-3-recovery-restart-gate\"}" > "staging\ops_snapshot\s33_3_live_https_response.txt" 2>&1
if errorlevel 1 exit /b 1

findstr /c:"HTTP/1.1 200 OK" "staging\ops_snapshot\s33_3_live_https_response.txt" >nul
if errorlevel 1 exit /b 1
findstr /c:"\"authenticated\": true" "staging\ops_snapshot\s33_3_live_https_response.txt" >nul
if errorlevel 1 exit /b 1
findstr /c:"\"status\": \"ADMITTED\"" "staging\ops_snapshot\s33_3_live_https_response.txt" >nul
if errorlevel 1 exit /b 1
findstr /c:"\"external_action_executed\": false" "staging\ops_snapshot\s33_3_live_https_response.txt" >nul
if errorlevel 1 exit /b 1
findstr /c:"\"memory_write_executed\": false" "staging\ops_snapshot\s33_3_live_https_response.txt" >nul
if errorlevel 1 exit /b 1

(
  type "staging\ops_snapshot\s33_3_live_https_response.txt" | findstr /c:"HTTP/1.1 200 OK" /c:"\"authenticated\": true" /c:"\"status\": \"ADMITTED\"" /c:"\"external_action_executed\": false" /c:"\"memory_write_executed\": false"
) > "staging\ops_snapshot\s33_3_recovery_gate_summary.txt"

exit /b 0
