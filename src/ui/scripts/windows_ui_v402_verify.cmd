@echo off
setlocal EnableExtensions EnableDelayedExpansion
python -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 (
  echo UI V4.0.2 VERIFICATION FAILED: TESTS
  exit /b 1
)
echo ===== UI CONSOLE SERVER COMPILE =====
python -m py_compile scripts\console_server.py
if errorlevel 1 (
  echo UI V4.0.2 VERIFICATION FAILED: COMPILE
  exit /b 1
)
echo ===== UI V4.0.2 JAVASCRIPT SYNTAX =====
where node >nul 2>nul
if errorlevel 1 (
  echo NODE NOT INSTALLED: SKIPPED CONDITIONAL CHECK
) else (
  node --check ui\app.js
  if errorlevel 1 (
    echo UI V4.0.2 VERIFICATION FAILED: JAVASCRIPT
    exit /b 1
  )
)
echo ALL UI V4.0.2 VERIFICATION CHECKS PASSED.
exit /b 0
