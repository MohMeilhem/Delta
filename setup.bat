@echo off
rem Delta - one-time setup: creates the backend venv and installs all
rem dependencies. Run this once after unzipping, then use run.bat.
setlocal
cd /d "%~dp0"

echo ============================================
echo  Delta - first-time setup
echo ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  where py >nul 2>nul
  if errorlevel 1 (
    echo [ERROR] Python was not found on PATH.
    echo Install Python 3.11+ from https://python.org and re-run this script.
    pause
    exit /b 1
  )
  set "PYCMD=py"
) else (
  set "PYCMD=python"
)

where node >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Node.js was not found on PATH.
  echo Install it from https://nodejs.org and re-run this script.
  pause
  exit /b 1
)

echo [1/3] Creating backend virtual environment...
if exist backend\.venv (
  echo   backend\.venv already exists, skipping.
) else (
  %PYCMD% -m venv backend\.venv
)

echo [2/3] Installing backend dependencies...
backend\.venv\Scripts\python.exe -m pip install --upgrade pip >nul
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
if errorlevel 1 (
  echo [ERROR] Backend dependency install failed. See above.
  pause
  exit /b 1
)

echo [3/3] Installing frontend dependencies...
pushd frontend
call npm install
set NPM_ERR=%errorlevel%
popd
if not "%NPM_ERR%"=="0" (
  echo [ERROR] Frontend dependency install failed. See above.
  pause
  exit /b 1
)

echo.
echo ============================================
echo  Setup complete. Double-click run.bat to start Delta.
echo ============================================
pause
