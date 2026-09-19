@echo off
setlocal
set "PYTHONWARNINGS=error::ResourceWarning"
if not defined PYTHONPATH set "PYTHONPATH=%CD%"
echo ===== UI V4.6.0 RC TESTS =====
python -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 (echo UI V4.6.0 RC VERIFICATION FAILED: TESTS & exit /b 1)
echo ===== UI CONSOLE SERVER COMPILE =====
python -m py_compile scripts\console_server.py
if errorlevel 1 (echo UI V4.6.0 RC VERIFICATION FAILED: COMPILE & exit /b 1)
echo ===== UI V4.6.0 RC JAVASCRIPT SYNTAX =====
where node >nul 2>nul
if errorlevel 1 (echo NODE NOT INSTALLED: SKIPPED CONDITIONAL CHECK) else (node --check ui\app.js & if errorlevel 1 (echo UI V4.6.0 RC VERIFICATION FAILED: JS SYNTAX & exit /b 1))
echo ===== UI V4.6.0 RC PACKAGE GATE =====
python -c "import json,zipfile; from pathlib import Path; m=json.loads(Path('ui/meta.json').read_text(encoding='utf-8')); assert m['version']=='4.6.0-rc'; assert 'final_release_candidate' in m['features']; print('PACKAGE MANIFEST: PASS')"
if errorlevel 1 (echo UI V4.6.0 RC VERIFICATION FAILED: MANIFEST & exit /b 1)
echo ALL UI V4.6.0 RC VERIFICATION CHECKS PASSED.
exit /b 0
