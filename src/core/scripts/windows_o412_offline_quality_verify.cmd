@echo off
setlocal
cd /d "%~dp0.."
set PYTHONPATH=%CD%
set PYTHONWARNINGS=error::ResourceWarning

echo [1/3] Backend test suite...
python -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 exit /b 1

echo [2/3] Compile check...
python -m compileall -q .
if errorlevel 1 exit /b 1

echo [3/3] O41.2 semantic hardening regression suite...
python -m unittest tests.test_o41_semantic_hardening -v
if errorlevel 1 exit /b 1

echo ALL O41.2 OFFLINE DECISION QUALITY CHECKS PASSED.
exit /b 0
