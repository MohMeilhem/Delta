@echo off
rem Delta — start backend (:8000) and frontend (:5173) in two windows
cd /d "%~dp0"

if not exist backend\.venv\Scripts\python.exe (
  echo backend\.venv not found. Run setup.bat first.
  pause
  exit /b 1
)
if not exist frontend\node_modules (
  echo frontend\node_modules not found. Run setup.bat first.
  pause
  exit /b 1
)

start "Delta backend" cmd /k "backend\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000 --app-dir backend"

where node >nul 2>nul
if errorlevel 1 (
  rem Node not on PATH (this dev machine): fall back to the known install path
  start "Delta frontend" cmd /k ""C:\Program Files\nodejs\node.exe" frontend\node_modules\vite\bin\vite.js --config frontend\vite.config.ts frontend"
) else (
  start "Delta frontend" cmd /k "cd frontend && npm run dev"
)

timeout /t 3 /nobreak >nul
start "" http://localhost:5173
