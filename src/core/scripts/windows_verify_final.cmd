@echo off
setlocal
set PYTHONPATH=%CD%
set PYTHONWARNINGS=error::ResourceWarning

if not exist "src" (
  echo ERROR: run this from the AI Master OS final release root.
  exit /b 2
)

echo [1/7] Full unit/regression suite...
python -m unittest discover -s tests -p "test_*.py" -v || exit /b 1

echo [2/7] O37 multi-tenant smoke...
python scripts\o37_smoke.py || exit /b 1

echo [3/7] O36 identity/startup smoke...
python scripts\startup_check.py || exit /b 1

echo [4/7] O35 cumulative smoke...
python scripts\o35_smoke.py || exit /b 1

echo [5/7] O34 cumulative smoke...
python scripts\o34_smoke.py || exit /b 1

echo [6/7] O33 + deployment smoke...
python scripts\o33_smoke.py || exit /b 1
python scripts\deploy_smoke.py || exit /b 1

echo [7/7] Final evaluation + compileall...
python run_evaluation.py || exit /b 1
python -m compileall -q src scripts tests engines || exit /b 1

echo.
echo ALL AI MASTER OS FINAL WINDOWS GATE CHECKS PASSED.
exit /b 0
