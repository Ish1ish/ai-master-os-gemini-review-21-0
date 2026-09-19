@echo off
setlocal
cd /d "%~dp0.."
set "PYTHONPATH=%CD%"
set "PYTHONWARNINGS=error::ResourceWarning"
echo ===== AI MASTER OS O39 OPERATIONS SNAPSHOT =====
python scripts\ops_snapshot.py --api "http://127.0.0.1:8080" --output "release\ops_snapshot.json"
set "RC=%ERRORLEVEL%"
echo ===== SNAPSHOT SAVED TO release\ops_snapshot.json =====
exit /b %RC%
