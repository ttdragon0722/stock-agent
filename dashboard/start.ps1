# invest-advisor dashboard launcher — starts FastAPI backend + Next.js frontend.
# Usage:  .\start.ps1          (from D:\coding\stock-agent\dashboard)
# Stop :  close the two spawned windows, or Ctrl+C in each.

$root = $PSScriptRoot

Start-Process powershell -ArgumentList @(
  "-NoExit", "-Command",
  "Set-Location '$root\backend'; python -m uvicorn main:app --port 8787"
) -WindowStyle Normal

Start-Process powershell -ArgumentList @(
  "-NoExit", "-Command",
  "Set-Location '$root\frontend'; npm run dev"
) -WindowStyle Normal

Start-Sleep -Seconds 3
Start-Process "http://localhost:3000"
Write-Host "backend  → http://localhost:8787/docs (Swagger)"
Write-Host "frontend → http://localhost:3000"
