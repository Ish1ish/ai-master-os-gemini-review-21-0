@echo off
setlocal
set "PYTHONPATH=%CD%"
set "PYTHONWARNINGS=error::ResourceWarning"

if not exist "src" (
  echo ERROR: run this from the O38 project root.
  exit /b 2
)

echo [1/3] O38 regression/security verification...
call scripts\windows_verify_o38.cmd
if errorlevel 1 exit /b 1

echo [2/3] Go-Live validation gate...
set "GATE_ARGS="
if defined AI_OS_O38_ARCHIVE set "GATE_ARGS=%GATE_ARGS% --archive "%AI_OS_O38_ARCHIVE%""
if defined AI_OS_PRIOR_ARCHIVE set "GATE_ARGS=%GATE_ARGS% --prior-archive "%AI_OS_PRIOR_ARCHIVE%""
python scripts\go_live_gate.py %GATE_ARGS%
set "GATE_RC=%ERRORLEVEL%"
if "%GATE_RC%"=="0" (
  echo [3/3] Go-Live gate READY.
  exit /b 0
)
if "%GATE_RC%"=="3" (
  echo.
  echo O38 GO-LIVE GATE IS CONDITIONAL. Review the JSON above and complete the target-environment checks.
  exit /b 3
)

echo.
echo O38 GO-LIVE GATE FAILED. Review the gate output above.
exit /b 1
