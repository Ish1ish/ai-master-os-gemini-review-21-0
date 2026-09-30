@echo off
setlocal EnableExtensions

set "ROOT=%~dp0..\..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"

cd /d "%ROOT%" || exit /b 2

if not exist "tests" (
  echo ERROR: 21.1 regression gate must run from the project root.
  exit /b 2
)
if not exist "node_bff\package.json" (
  echo ERROR: node_bff package is missing.
  exit /b 2
)

set "AI_OS_ENV=local"
set "PYTHONPATH=%ROOT%\src;%ROOT%\src\core"

echo [1/3] Python 21.1 regression suite...
python -m pytest -q tests
if errorlevel 1 exit /b 1

echo [2/3] Node BFF regression suite...
pushd "%ROOT%\node_bff"
call npm test
set "NODE_TEST_EXIT=%ERRORLEVEL%"
popd
if not "%NODE_TEST_EXIT%"=="0" exit /b %NODE_TEST_EXIT%

echo [3/3] Python compile check...
python -m compileall -q src tests
if errorlevel 1 exit /b 1

echo.
echo ALL 21.1 REGRESSION GATE CHECKS PASSED.
exit /b 0
