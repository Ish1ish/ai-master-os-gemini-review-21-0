@echo off
setlocal
set "PYTHONPATH=%CD%"
set "PYTHONWARNINGS=error::ResourceWarning"
rem Regression tests must always use the local fake-provider runtime; do not inherit production mode.
set "AI_OS_ENV=local"
python -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 goto :fail
python -m compileall -q src engines scripts run_evaluation.py
if errorlevel 1 goto :fail
python -c "import os; os.environ['AI_OS_ENV']='production'; os.environ['AI_OS_IDENTITY_SIGNING_SECRET']='verification-secret-32-bytes-min'; from src.identity import IdentityProvider; IdentityProvider(); print('O38 production identity startup PASS')"
if errorlevel 1 goto :fail
echo ALL O38 WINDOWS SECURITY HARDENING CHECKS PASSED.
exit /b 0
:fail
echo O38 WINDOWS SECURITY HARDENING FAILED.
exit /b 1
