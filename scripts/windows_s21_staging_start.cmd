@echo off
cd /d "%~dp0.."
set "PYTHONPATH=%CD%;%CD%\src;%CD%\src\core"

netstat -ano | findstr ":8091" | findstr "LISTENING" >nul
if not errorlevel 1 exit /b 1

start "AIOS-S21" /b python "scripts\s21_staging_server.py"

exit /b 0
