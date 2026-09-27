@echo off
setlocal
set "PYTHONPATH=%CD%\src;%CD%\src\core;%CD%\src\core\src"
set "PYTHONWARNINGS=error::ResourceWarning"
echo ===== O46 FULL REGRESSION =====
python -c "import pathlib,src,unittest; core_src=str(pathlib.Path.cwd()/'src'/'core'/'src'); src.__path__.append(core_src) if core_src not in src.__path__ else None; suite=unittest.defaultTestLoader.discover('tests',pattern='test_*.py'); result=unittest.TextTestRunner(verbosity=2).run(suite); raise SystemExit(0 if result.wasSuccessful() else 1)"
if errorlevel 1 goto :fail
echo ===== O46 COMPILEALL =====
python -m compileall -q src
if errorlevel 1 goto :fail
echo ===== O44 GOVERNANCE SMOKE REGRESSION =====
python src\core\scripts\o44_governance_smoke.py
if errorlevel 1 goto :fail
echo ===== O45 EXECUTION SMOKE REGRESSION =====
python src\core\scripts\o45_execution_smoke.py
if errorlevel 1 goto :fail
echo ===== O46 GOVERNED LOOP SMOKE =====
python src\core\scripts\o46_governed_loop_smoke.py
if errorlevel 1 goto :fail
echo ALL O46 VERIFICATION CHECKS PASSED.
exit /b 0
:fail
echo O46 VERIFICATION FAILED.
exit /b 1
