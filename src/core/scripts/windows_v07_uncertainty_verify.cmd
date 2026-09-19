@echo off
setlocal
cd /d "%~dp0.."
set "PYTHONPATH=%CD%"
set "PYTHONWARNINGS=error::ResourceWarning"

echo [1/4] RUNNING V0.6 REGRESSION TESTS + V0.7 TESTS
python -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 goto :fail

echo [2/4] COMPILEALL
python -m compileall -q src scripts tests
if errorlevel 1 goto :fail

echo [3/4] V0.7 DECISION UNCERTAINTY SMOKE
python scripts\decision_uncertainty_smoke.py
if errorlevel 1 goto :fail

echo [4/4] V0.7 CONTRACT CHECK
python -c "from src.decision_uncertainty import DecisionUncertainty; assert DecisionUncertainty.sample_sufficiency(2)=='MINIMAL'; assert DecisionUncertainty.sample_sufficiency(10)=='STRONG'; print('V0.7 UNCERTAINTY CONTRACT CHECK PASS')"
if errorlevel 1 goto :fail

echo.
echo ALL V0.7 DECISION UNCERTAINTY CHECKS PASSED.
exit /b 0

:fail
echo.
echo V0.7 VERIFICATION FAILED.
exit /b 1
