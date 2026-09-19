@echo off
setlocal
cd /d "%~dp0.."
set "PYTHONPATH=%CD%"
set "PYTHONWARNINGS=error::ResourceWarning"

echo [1/4] RUNNING V0.5 REGRESSION TESTS
python -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 goto :fail

echo [2/4] COMPILEALL
python -m compileall -q src scripts tests
if errorlevel 1 goto :fail

echo [3/4] V0.6 CONTEXTUAL FINGERPRINT SMOKE
python scripts\contextual_fingerprint_smoke.py
if errorlevel 1 goto :fail

echo [4/4] CONTEXTUAL FINGERPRINT FILE CHECK
python -c "from src.decision_fingerprint import DecisionFingerprint; assert DecisionFingerprint.MATCH_FIELDS == ('action_types','tools','risk_class','project_id','tenant_id','evidence_pattern'); print('V0.6 CONTRACT CHECK PASS')"
if errorlevel 1 goto :fail

echo.
echo ALL V0.6 CONTEXTUAL DECISION FINGERPRINT CHECKS PASSED.
exit /b 0

:fail
echo.
echo V0.6 VERIFICATION FAILED.
exit /b 1
