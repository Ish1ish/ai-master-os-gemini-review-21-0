@echo off
setlocal
cd /d "%~dp0.."
set "PYTHONPATH=%CD%"
set "PYTHONWARNINGS=error::ResourceWarning"
echo ============================================================
echo          AI MASTER OS O39 WINDOWS VERIFICATION
echo ============================================================
python -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 goto fail
python -m compileall -q .
if errorlevel 1 goto fail
scripts\windows_offline_quality_verify_o38.cmd
if errorlevel 1 goto fail
python scripts\ops_snapshot.py --api "http://127.0.0.1:8080" --output "release\ops_snapshot.json"
if errorlevel 1 goto fail
findstr /i /c:"provider_calls\": \"NONE\"" release\ops_snapshot.json >nul
if errorlevel 1 goto fail
findstr /i /c:"secrets_printed\": false" release\ops_snapshot.json >nul
if errorlevel 1 goto fail
echo ALL O39 WINDOWS VERIFICATION CHECKS PASSED.
exit /b 0
:fail
echo O39 WINDOWS VERIFICATION FAILED.
exit /b 1
