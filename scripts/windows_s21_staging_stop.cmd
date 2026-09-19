@echo off
cd /d "%~dp0.."

if exist "staging\s21.pid" (
    set /p PID=<"staging\s21.pid"
    taskkill /f /pid %PID% >nul 2>&1
    del /q "staging\s21.pid" >nul 2>&1
)

for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":8091" ^| findstr "LISTENING"') do taskkill /f /pid %%P >nul 2>&1

taskkill /f /fi "WINDOWTITLE eq AIOS-S21*" >nul 2>&1
taskkill /f /im python.exe /fi "WINDOWTITLE eq AIOS-S21*" >nul 2>&1

exit /b 0
