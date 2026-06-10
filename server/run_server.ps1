# HabitBud — run the backend as a resilient LAN server on this PC.
# Serves HTTP + WebSockets with Daphne on 0.0.0.0:8000 and auto-restarts on crash.
# Logs: server\logs\daphne-YYYYMMDD.log
#
#   powershell -ExecutionPolicy Bypass -File server\run_server.ps1
#   (or let the scheduled task from install_service.ps1 run it at boot)

$ErrorActionPreference = 'Continue'
$root   = Split-Path $PSScriptRoot -Parent
$appDir = Join-Path $root 'habit_tracker'
$python = Join-Path $appDir 'venv\Scripts\python.exe'
$logDir = Join-Path $PSScriptRoot 'logs'
New-Item -ItemType Directory -Force $logDir | Out-Null

$env:PYTHONUTF8 = '1'
$env:PYTHONUNBUFFERED = '1'

Set-Location $appDir

# One-time per boot: apply migrations + collect static.
& $python manage.py migrate --noinput
& $python manage.py collectstatic --noinput | Out-Null

while ($true) {
    $log = Join-Path $logDir ("daphne-" + (Get-Date -Format 'yyyyMMdd') + ".log")
    "[$(Get-Date -Format s)] starting daphne on 0.0.0.0:8000" | Tee-Object -FilePath $log -Append
    & $python -m daphne -b 0.0.0.0 -p 8000 habit_tracker.asgi:application *>> $log
    "[$(Get-Date -Format s)] daphne exited (code $LASTEXITCODE) — restarting in 3s" | Tee-Object -FilePath $log -Append
    Start-Sleep -Seconds 3
}
