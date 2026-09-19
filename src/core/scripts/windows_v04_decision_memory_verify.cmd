@echo off
setlocal
set "PYTHONWARNINGS=error::ResourceWarning"
set "PYTHONPATH=%CD%"
echo ===== V0.4 CORE REGRESSION =====
python -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 (echo V0.4 CORE VERIFICATION FAILED: TESTS & exit /b 1)
echo ===== V0.4 COMPILEALL =====
python -m compileall -q src
if errorlevel 1 (echo V0.4 CORE VERIFICATION FAILED: COMPILE & exit /b 1)
echo ALL V0.4 CORE VERIFICATION CHECKS PASSED.
exit /b 0
