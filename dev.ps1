# Delta — one-command dev startup for Windows (equivalent of `make dev`).
# Starts backend on :8000 and frontend on :5173 in two windows.

$root = $PSScriptRoot
$node = "C:\Program Files\nodejs"
if (Test-Path $node) { $env:Path = "$node;$env:Path" }

Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$root\backend'; .venv\Scripts\python -m uvicorn app.main:app --reload --port 8000"
)

Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "`$env:Path='$node;'+`$env:Path; cd '$root\frontend'; npm run dev"
)

Write-Host "Delta starting: backend http://localhost:8000 — frontend http://localhost:5173"
