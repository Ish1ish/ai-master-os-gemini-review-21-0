@echo off
setlocal
set "PYTHONWARNINGS=error::ResourceWarning"
set "PYTHONPATH=%CD%"
echo ===== UI V4.9 DECISION MEMORY TESTS =====
python -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 (echo UI V4.9 VERIFICATION FAILED: TESTS & exit /b 1)
python -m py_compile scripts\console_server.py
if errorlevel 1 (echo UI V4.9 VERIFICATION FAILED: COMPILE & exit /b 1)
echo ===== UI V4.9 MANIFEST =====
python -c "import json; from pathlib import Path; m=json.loads(Path('ui/meta.json').read_text(encoding='utf-8')); assert m['current_build']=='4.9.0'; assert 'counterfactual_prediction_memory' in m['features']; print('UI V4.9 MANIFEST: PASS')"
if errorlevel 1 (echo UI V4.9 VERIFICATION FAILED: MANIFEST & exit /b 1)
echo ALL UI V4.9 VERIFICATION CHECKS PASSED.
exit /b 0
