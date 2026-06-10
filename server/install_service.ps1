# HabitBud — install the backend as an always-on Windows "service".
# Run ONCE from an elevated (Administrator) PowerShell:
#   powershell -ExecutionPolicy Bypass -File server\install_service.ps1
#
# What it does:
#   1. Opens TCP 8000 in Windows Firewall (LAN devices can reach the API).
#   2. Registers a Task Scheduler job that starts run_server.ps1 at boot
#      (SYSTEM account, hidden window, auto-restart loop inside the script).
#   3. Starts it now.
# Remove with:  server\uninstall_service.ps1

$ErrorActionPreference = 'Stop'

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
        ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error 'Run this from an elevated (Administrator) PowerShell.'
    exit 1
}

$runner = Join-Path $PSScriptRoot 'run_server.ps1'

# 1) Firewall: allow inbound 8000 (idempotent).
if (-not (Get-NetFirewallRule -DisplayName 'HabitBud API 8000' -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName 'HabitBud API 8000' -Direction Inbound `
        -Action Allow -Protocol TCP -LocalPort 8000 | Out-Null
    Write-Host 'Firewall rule added (TCP 8000 inbound).' -ForegroundColor Green
} else {
    Write-Host 'Firewall rule already present.' -ForegroundColor DarkGray
}

# 2) Scheduled task at boot.
$action    = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$runner`""
$trigger   = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -RunLevel Highest
$settings  = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Days 3650) -StartWhenAvailable

Register-ScheduledTask -TaskName 'HabitBudServer' -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings -Force | Out-Null
Write-Host 'Scheduled task "HabitBudServer" registered (runs at boot).' -ForegroundColor Green

# 3) Start now.
Start-ScheduledTask -TaskName 'HabitBudServer'
Write-Host 'Server starting. Check: curl http://localhost:8000/api/health/' -ForegroundColor Cyan
