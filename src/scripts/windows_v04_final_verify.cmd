@echo off
setlocal
set "ROOT=%~dp0.."
pushd "%ROOT%\core"
call scripts\windows_v04_decision_memory_verify.cmd
if errorlevel 1 (popd & exit /b 1)
popd
pushd "%ROOT%\ui"
call scripts\windows_ui_v49_verify.cmd
if errorlevel 1 (popd & exit /b 1)
popd
echo ALL AI MASTER OS V0.4 DECISION MEMORY VERIFICATION CHECKS PASSED.
exit /b 0
