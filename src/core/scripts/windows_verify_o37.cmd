@echo off
setlocal
set PYTHONPATH=%CD%
set PYTHONWARNINGS=error::ResourceWarning

if not exist "src" (
  echo ERROR: run this from the O37 project root.
  exit /b 2
)

echo [1/6] O37 unit/regression tests...
python -m unittest discover -s tests -p "test_*.py" -v || exit /b 1

echo [2/6] O37 multi-tenant smoke...
python scripts\o37_smoke.py || exit /b 1

echo [3/6] O36 cumulative identity smoke...
python scripts\startup_check.py || exit /b 1

echo [4/6] O33 cumulative smoke...
python scripts\o33_smoke.py || exit /b 1

echo [5/6] deployment smoke...
python scripts\deploy_smoke.py || exit /b 1

echo [6/6] compileall...
python -m compileall -q src scripts tests || exit /b 1

echo.
echo ALL O37 WINDOWS VERIFICATION CHECKS PASSED.
exit /b 0
