@echo off
setlocal
cd /d "%~dp0.."
set "PYTHONPATH=%CD%"
python scripts\console_server.py --host 127.0.0.1 --port 8090 --api http://127.0.0.1:8080
endlocal
