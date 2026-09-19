@echo off
setlocal
cd /d "%~dp0.."
set "PYTHONPATH=%CD%;%CD%\src;%CD%\src\core"

netstat -ano | findstr ":8091" | findstr "LISTENING" >nul
if not errorlevel 1 goto :ensure_caddy

start "AIOS-S21" /b python "scripts\s21_staging_server.py"

for /l %%N in (1,1,20) do (
    netstat -ano | findstr ":8091" | findstr "LISTENING" >nul
    if not errorlevel 1 goto :ensure_caddy
    ping 127.0.0.1 -n 2 >nul
)

exit /b 1

:ensure_caddy
netstat -ano | findstr ":8443" | findstr "LISTENING" >nul
if not errorlevel 1 exit /b 0

start "AIOS-CADDY" /b tools\caddy\caddy.exe run --config tools\caddy\Caddyfile

for /l %%N in (1,1,30) do (
    netstat -ano | findstr ":8443" | findstr "LISTENING" >nul
    if not errorlevel 1 exit /b 0
    ping 127.0.0.1 -n 2 >nul
)

exit /b 1
