@echo off
setlocal
set "ROOT=%~dp0.."
pushd "%ROOT%"
set "PYTHONPATH=%CD%"
set "PYTHONWARNINGS=error::ResourceWarning"
echo ===== V0.5 CORE REGRESSION =====
python -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 (popd & echo V0.5 CORE VERIFICATION FAILED: TESTS & exit /b 1)
echo ===== V0.5 COMPILEALL =====
python -m compileall -q src
if errorlevel 1 (popd & echo V0.5 CORE VERIFICATION FAILED: COMPILE & exit /b 1)
echo ===== V0.5 ADAPTIVE SMOKE =====
python scripts\adaptive_decision_smoke.py
if errorlevel 1 (popd & echo V0.5 CORE VERIFICATION FAILED: SMOKE & exit /b 1)
echo ALL V0.5 CORE VERIFICATION CHECKS PASSED.
popd
exit /b 0
