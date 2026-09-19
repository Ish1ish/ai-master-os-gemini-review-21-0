@echo off
setlocal
cd /d "%~dp0.."

if exist "scripts\windows_s21_staging_stop.cmd" call scripts\windows_s21_staging_stop.cmd

for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":8443" ^| findstr "LISTENING"') do taskkill /f /pid %%P >nul 2>&1

exit /b 0
