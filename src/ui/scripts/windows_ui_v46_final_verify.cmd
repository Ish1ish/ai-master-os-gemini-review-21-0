@echo off
setlocal
set "PYTHONWARNINGS=error::ResourceWarning"
if not defined PYTHONPATH set "PYTHONPATH=%CD%"
echo ===== UI V4.6.0 FINAL TESTS =====
python -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 (echo UI V4.6.0 FINAL VERIFICATION FAILED: TESTS & exit /b 1)
echo ===== UI CONSOLE SERVER COMPILE =====
python -m py_compile scripts\console_server.py
if errorlevel 1 (echo UI V4.6.0 FINAL VERIFICATION FAILED: COMPILE & exit /b 1)
echo ===== UI V4.6.0 FINAL JAVASCRIPT SYNTAX =====
where node >nul 2>nul
if errorlevel 1 (echo NODE NOT INSTALLED: SKIPPED CONDITIONAL CHECK) else (node --check ui\app.js & if errorlevel 1 (echo UI V4.6.0 FINAL VERIFICATION FAILED: JS SYNTAX & exit /b 1))
echo ===== UI V4.6.0 FINAL PACKAGE GATE =====
python -c "import json; from pathlib import Path; m=json.loads(Path('ui/meta.json').read_text(encoding='utf-8')); assert m['version']=='4.6.0'; assert m['console_version']=='4.6.0'; assert m['release']=='FINAL'; assert 'final_release' in m['features']; assert 'final_release_candidate' not in m['features']; print('PACKAGE MANIFEST: PASS')"
if errorlevel 1 (echo UI V4.6.0 FINAL VERIFICATION FAILED: MANIFEST & exit /b 1)
echo ===== UI V4.6.0 FINAL ARTIFACT CHECK =====
python -c "from pathlib import Path; import zipfile; required=['ui/index.html','ui/app.js','ui/styles.css','ui/meta.json','scripts/console_server.py','scripts/windows_start_console.cmd']; assert all(Path(x).exists() for x in required); print('ARTIFACT STRUCTURE: PASS')"
if errorlevel 1 (echo UI V4.6.0 FINAL VERIFICATION FAILED: ARTIFACT & exit /b 1)
echo ALL UI V4.6.0 FINAL VERIFICATION CHECKS PASSED.
exit /b 0
