@echo off
setlocal
cd /d "%~dp0.."
set "PYTHONPATH=%CD%"
set "PYTHONWARNINGS=error::ResourceWarning"

echo ===== UI V4.0.0 TESTS =====
python -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 (
  echo UI V4.0.0 VERIFICATION FAILED: TESTS
  exit /b 1
)

echo ===== UI CONSOLE SERVER COMPILE =====
python -m py_compile scripts\console_server.py
if errorlevel 1 (
  echo UI V4.0.0 VERIFICATION FAILED: COMPILE
  exit /b 1
)

echo ===== UI V4.0.0 JAVASCRIPT SYNTAX =====
where node >nul 2>&1
if errorlevel 1 (
  echo NODE NOT INSTALLED: SKIPPED CONDITIONAL CHECK
) else (
  node --check ui\app.js
  if errorlevel 1 (
    echo UI V4.0.0 VERIFICATION FAILED: JAVASCRIPT SYNTAX
    exit /b 1
  )
)

echo ALL UI V4.0.0 VERIFICATION CHECKS PASSED.
exit /b 0
