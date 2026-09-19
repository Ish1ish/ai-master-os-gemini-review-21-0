@echo off
setlocal
cd /d "%~dp0.."

set "SNAP=staging\ops_snapshot"
if not exist "%SNAP%" mkdir "%SNAP%"

python scripts\s32_ops_snapshot.py > "%SNAP%\snapshot.txt"
if errorlevel 1 exit /b 1

exit /b 0
