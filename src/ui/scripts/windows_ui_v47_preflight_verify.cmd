@echo off
setlocal
cd /d "%~dp0.."
set "PYTHONPATH=%CD%"
set "PYTHONWARNINGS=error::ResourceWarning"
echo ===== UI V4.7.0 COUNTERFACTUAL PREFLIGHT =====
python -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 exit /b 1
python -m py_compile scripts\console_server.py
if errorlevel 1 exit /b 1
python -c "import json,pathlib; m=json.loads(pathlib.Path('ui/meta.json').read_text(encoding='utf-8')); assert m.get('current_build')=='4.7.0'; assert 'counterfactual_preflight' in m.get('features',[]); print('UI V4.7.0 PREFLIGHT MANIFEST: PASS')"
if errorlevel 1 exit /b 1
echo ALL UI V4.7.0 COUNTERFACTUAL PREFLIGHT VERIFICATION CHECKS PASSED.
exit /b 0
