@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "PYTHONPATH=%CD%"
set "PYTHONWARNINGS=error::ResourceWarning"
python -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 exit /b 1
python -m compileall -q .
if errorlevel 1 exit /b 1
scripts\windows_offline_quality_verify_o38.cmd
if errorlevel 1 exit /b 1
python scripts\final_release_gate.py --skip-provider
if errorlevel 3 echo FINAL RELEASE GATE IS CONDITIONAL: target-environment evidence remains manual.
if errorlevel 2 exit /b 2
echo ALL O40 WINDOWS FINAL RELEASE CHECKS PASSED.
exit /b 0
