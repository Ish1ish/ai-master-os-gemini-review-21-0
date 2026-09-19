@echo off
setlocal
set "PYTHONPATH=%CD%"
set "PYTHONWARNINGS=error::ResourceWarning"
echo [1/3] Full offline unit/regression suite...
python -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 goto :fail
echo [2/3] compileall...
python -m compileall -q src engines scripts tests
if errorlevel 1 goto :fail
echo [3/3] Offline evaluation harness (fake providers only)...
python run_evaluation.py
if errorlevel 1 goto :fail
echo ALL O38 OFFLINE QUALITY CHECKS PASSED.
exit /b 0
:fail
echo O38 OFFLINE QUALITY CHECKS FAILED.
exit /b 2
