@echo off
setlocal EnableExtensions

REM AI Master OS — one-time Windows workspace organizer.
REM Safe behavior: COPY ONLY. Existing source folders are never deleted or moved.

set "DESKTOP=%USERPROFILE%\Desktop"
set "SOURCE=%DESKTOP%\AI Documents\#00 MASTER INDEX\15 AI OS RUNTIME BUILD"
set "PACKAGE=%SOURCE%\OS_Counterfactual_Control_Plane_v0.1.0"
set "HOME=%DESKTOP%\AI Master OS"

if not exist "%PACKAGE%\core\src\counterfactual_preflight.py" (
  echo SOURCE PACKAGE NOT FOUND:
  echo %PACKAGE%
  exit /b 1
)

for %%D in (
  "00_CONTROL"
  "01_CORE_RUNTIME"
  "02_UI_CONSOLE"
  "03_RELEASES"
  "04_MILESTONES"
  "05_AUDITS"
  "06_ARCHIVE"
  "07_WORKSPACE"
) do if not exist "%HOME%\%%~D" mkdir "%HOME%\%%~D"

copy /Y "%PACKAGE%\README.md" "%HOME%\00_CONTROL\README.md" >nul
copy /Y "%PACKAGE%\MILESTONE.md" "%HOME%\04_MILESTONES\COUNTERFACTUAL_V0.2.0_MILESTONE.md" >nul
copy /Y "%PACKAGE%\release_manifest.json" "%HOME%\00_CONTROL\release_manifest.json" >nul
copy /Y "%PACKAGE%\windows\organize_ai_master_os.cmd" "%HOME%\00_CONTROL\organize_ai_master_os.cmd" >nul

robocopy "%PACKAGE%\core" "%HOME%\01_CORE_RUNTIME" /E /XD __pycache__ .pytest_cache data\tmp /XF *.pyc >nul
robocopy "%PACKAGE%\ui" "%HOME%\02_UI_CONSOLE" /E /XD __pycache__ .pytest_cache >nul
robocopy "%PACKAGE%\docs" "%HOME%\05_AUDITS" /E >nul

if exist "%SOURCE%\AI_Master_OS_Final_Release_Audit_v1.0_RC.zip" copy /Y "%SOURCE%\AI_Master_OS_Final_Release_Audit_v1.0_RC.zip" "%HOME%\03_RELEASES\" >nul
if exist "%SOURCE%\AI_Master_OS_UI_Console_v4.6.0_FINAL.zip" copy /Y "%SOURCE%\AI_Master_OS_UI_Console_v4.6.0_FINAL.zip" "%HOME%\03_RELEASES\" >nul
if exist "%SOURCE%\O46 — Full Governed Autonomous Loop.zip" copy /Y "%SOURCE%\O46 — Full Governed Autonomous Loop.zip" "%HOME%\06_ARCHIVE\" >nul

>"%HOME%\00_CONTROL\WINDOWS_PATHS.cmd" echo @echo off
>>"%HOME%\00_CONTROL\WINDOWS_PATHS.cmd" echo set "AI_MASTER_OS_HOME=%HOME%"
>>"%HOME%\00_CONTROL\WINDOWS_PATHS.cmd" echo set "AI_MASTER_OS_CORE=%HOME%\01_CORE_RUNTIME"
>>"%HOME%\00_CONTROL\WINDOWS_PATHS.cmd" echo set "AI_MASTER_OS_UI=%HOME%\02_UI_CONSOLE"
>>"%HOME%\00_CONTROL\WINDOWS_PATHS.cmd" echo set "AI_MASTER_OS_RELEASES=%HOME%\03_RELEASES"
>>"%HOME%\00_CONTROL\WINDOWS_PATHS.cmd" echo set "AI_MASTER_OS_AUDITS=%HOME%\05_AUDITS"

>"%HOME%\00_CONTROL\PROJECT_LAYOUT.txt" echo AI Master OS — Canonical Windows Workspace
>>"%HOME%\00_CONTROL\PROJECT_LAYOUT.txt" echo.
>>"%HOME%\00_CONTROL\PROJECT_LAYOUT.txt" echo %HOME%
>>"%HOME%\00_CONTROL\PROJECT_LAYOUT.txt" echo   00_CONTROL       = manifests, paths, operator notes
>>"%HOME%\00_CONTROL\PROJECT_LAYOUT.txt" echo   01_CORE_RUNTIME  = canonical backend runtime
>>"%HOME%\00_CONTROL\PROJECT_LAYOUT.txt" echo   02_UI_CONSOLE    = canonical control center
>>"%HOME%\00_CONTROL\PROJECT_LAYOUT.txt" echo   03_RELEASES      = frozen ZIP releases and release artifacts
>>"%HOME%\00_CONTROL\PROJECT_LAYOUT.txt" echo   04_MILESTONES    = milestone specs and completion records
>>"%HOME%\00_CONTROL\PROJECT_LAYOUT.txt" echo   05_AUDITS        = final audit / go-live evidence
>>"%HOME%\00_CONTROL\PROJECT_LAYOUT.txt" echo   06_ARCHIVE       = older verified baselines
>>"%HOME%\00_CONTROL\PROJECT_LAYOUT.txt" echo   07_WORKSPACE     = active experiments and temporary work

echo.
echo AI MASTER OS WORKSPACE CREATED:
echo %HOME%
echo.
echo IMPORTANT: source files were COPIED, not moved or deleted.
exit /b 0
