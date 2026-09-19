@echo off
setlocal
cd /d "%~dp0.."
set PYTHONPATH=%CD%
set PYTHONWARNINGS=error::ResourceWarning

echo [1/4] Backend test suite...
python -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 exit /b 1

echo [2/4] Compile check...
python -m compileall -q .
if errorlevel 1 exit /b 1

echo [3/4] O41.4 decision surface regression suite...
python -m unittest tests.test_o41_decision_surface_integrity tests.test_o41_semantic_hardening -v
if errorlevel 1 exit /b 1

echo [4/4] Decision surface marker...
findstr /C:"decision_surface" src\localization.py >nul
if errorlevel 1 exit /b 1
findstr /C:"Validation Model" ui\AI_Master_OS_UI_Console_v1.6.0\ui\app.js >nul
if errorlevel 1 exit /b 1

echo ALL O41.4 OFFLINE DECISION SURFACE CHECKS PASSED.
exit /b 0
