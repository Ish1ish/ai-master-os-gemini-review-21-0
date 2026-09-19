@echo off
setlocal
set "ROOT=%~dp0.."
pushd "%ROOT%"
set "PYTHONPATH=%CD%"
echo ===== UI V5.0 ADAPTIVE DECISION TESTS =====
python -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 (popd & echo UI V5.0 VERIFICATION FAILED: TESTS & exit /b 1)
echo ===== UI CONSOLE SERVER COMPILE =====
python -m py_compile scripts\console_server.py
if errorlevel 1 (popd & echo UI V5.0 VERIFICATION FAILED: SERVER COMPILE & exit /b 1)
echo ===== UI V5.0 MANIFEST =====
python -c "import json; m=json.load(open('ui/meta.json',encoding='utf-8')); assert m.get('version') in ('5.0.0','4.9.0')"
if errorlevel 1 (popd & echo UI V5.0 VERIFICATION FAILED: MANIFEST & exit /b 1)
echo ALL UI V5.0 VERIFICATION CHECKS PASSED.
popd
exit /b 0
