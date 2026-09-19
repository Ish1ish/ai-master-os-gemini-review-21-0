@echo off
setlocal
set "ROOT=%~dp0.."
set "CORE=%ROOT%\core"
set "UI=%ROOT%\ui"
set "PYTHONWARNINGS=error::ResourceWarning"

echo ===== AI MASTER OS FINAL E2E AUDIT =====
if not exist "%CORE%\scripts\windows_o46_verify.cmd" (echo CORE AUDIT SCRIPT MISSING & exit /b 1)
if not exist "%UI%\scripts\windows_ui_v46_final_verify.cmd" (echo UI AUDIT SCRIPT MISSING & exit /b 1)
if not exist "%UI%\scripts\windows_ui_v47_preflight_verify.cmd" (echo UI V4.7 AUDIT SCRIPT MISSING & exit /b 1)

pushd "%CORE%"
set "PYTHONPATH=%CD%"
echo ===== CORE / O46 VERIFICATION =====
call scripts\windows_o46_verify.cmd
if errorlevel 1 (popd & echo FINAL E2E AUDIT FAILED: CORE & exit /b 1)
popd

pushd "%UI%"
set "PYTHONPATH=%CD%"
echo ===== UI V4.6.0 FINAL VERIFICATION =====
call scripts\windows_ui_v46_final_verify.cmd
if errorlevel 1 (popd & echo FINAL E2E AUDIT FAILED: UI & exit /b 1)
popd

echo ===== CROSS-SYSTEM FINAL PACKAGE GATE =====
python scripts\final_e2e_audit.py --package-only
if errorlevel 1 (echo FINAL E2E AUDIT FAILED: PACKAGE & exit /b 1)

echo ALL AI MASTER OS FINAL E2E AUDIT CHECKS PASSED.
exit /b 0
