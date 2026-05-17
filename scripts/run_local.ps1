$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot

Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "run_backend.ps1") -WorkingDirectory $root
Start-Sleep -Seconds 2
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "run_frontend.ps1") -WorkingDirectory $root

Write-Host "Backend and frontend are starting in separate PowerShell windows."
Write-Host "Open http://localhost:3000 after the servers finish booting."
Write-Host "If you need the Telegram bot too, run .\scripts\run_bot.ps1 in a third window."

