@echo off
setlocal

cd /d "%~dp0.."

set "PYTHONPATH=%CD%;%CD%\src;%CD%\src\core"
set "EVIDENCE_DIR=staging\release_candidate"
if not exist "%EVIDENCE_DIR%" mkdir "%EVIDENCE_DIR%"

python -m unittest discover -s tests -p "test_*.py" -v > "%EVIDENCE_DIR%\full_regression.txt" 2>&1
if errorlevel 1 exit /b 1

python -m compileall -q src tests > "%EVIDENCE_DIR%\compileall.txt" 2>&1
if errorlevel 1 exit /b 1

netstat -ano | findstr ":8091" | findstr "LISTENING" > "%EVIDENCE_DIR%\s21_8091_listener.txt" 2>&1
if errorlevel 1 exit /b 1

netstat -ano | findstr ":8443" | findstr "LISTENING" > "%EVIDENCE_DIR%\caddy_8443_listener.txt" 2>&1
if errorlevel 1 exit /b 1

set "TOKEN_FILE=staging\operator_token.txt"
if not exist "%TOKEN_FILE%" exit /b 1

set /p TOKEN=<"%TOKEN_FILE%"

curl -k -sS -i -X POST "https://localhost:8443/api/runs" -H "Content-Type: application/json" -H "Authorization: Bearer %TOKEN%" --data "{\"intent\":\"s31-release-candidate-freeze\"}" > "%EVIDENCE_DIR%\live_https_response.txt" 2>&1
if errorlevel 1 exit /b 1

findstr /c:"HTTP/1.1 200 OK" "%EVIDENCE_DIR%\live_https_response.txt" >nul
if errorlevel 1 exit /b 1

findstr /c:"\"authenticated\": true" "%EVIDENCE_DIR%\live_https_response.txt" >nul
if errorlevel 1 exit /b 1

findstr /c:"\"status\": \"ADMITTED\"" "%EVIDENCE_DIR%\live_https_response.txt" >nul
if errorlevel 1 exit /b 1

findstr /c:"\"external_action_executed\": false" "%EVIDENCE_DIR%\live_https_response.txt" >nul
if errorlevel 1 exit /b 1

findstr /c:"\"memory_write_executed\": false" "%EVIDENCE_DIR%\live_https_response.txt" >nul
if errorlevel 1 exit /b 1

(
  echo S31 RELEASE CANDIDATE FREEZE
  echo.
  echo FULL_REGRESSION=PASS
  type "%EVIDENCE_DIR%\full_regression.txt" | findstr /c:"Ran " /c:"OK"
  echo COMPILEALL=PASS
  echo LIVE_HTTPS=PASS
  findstr /c:"HTTP/1.1 200 OK" /c:"\"authenticated\": true" /c:"\"status\": \"ADMITTED\"" "%EVIDENCE_DIR%\live_https_response.txt"
  echo EXTERNAL_ACTION_EXECUTED=false
  echo MEMORY_WRITE_EXECUTED=false
  echo.
  echo STAGING_ONLY=TRUE
  echo INTERNET_FACING_PRODUCTION_APPROVAL=FALSE
) > "%EVIDENCE_DIR%\release_candidate_manifest.txt"

exit /b 0
