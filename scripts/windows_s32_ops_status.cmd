@echo off
setlocal
cd /d "%~dp0.."

if not exist "config\o39_operations_manifest.json" exit /b 1
if not exist "scripts\windows_s21_staging_start.cmd" exit /b 1
if not exist "scripts\windows_s21_staging_stop.cmd" exit /b 1
if not exist "tools\caddy\caddy.exe" exit /b 1
if not exist "tools\caddy\Caddyfile" exit /b 1
if not exist "staging\operator_token.txt" exit /b 1

tools\caddy\caddy.exe validate --config tools\caddy\Caddyfile >nul 2>&1
if errorlevel 1 exit /b 1

netstat -ano | findstr ":8091" | findstr "LISTENING" >nul
if errorlevel 1 exit /b 1

netstat -ano | findstr ":8443" | findstr "LISTENING" >nul
if errorlevel 1 exit /b 1

exit /b 0
