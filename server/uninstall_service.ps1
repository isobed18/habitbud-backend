# Remove the HabitBud server task + firewall rule (run as Administrator).
$ErrorActionPreference = 'SilentlyContinue'
Stop-ScheduledTask -TaskName 'HabitBudServer'
Unregister-ScheduledTask -TaskName 'HabitBudServer' -Confirm:$false
Remove-NetFirewallRule -DisplayName 'HabitBud API 8000'
Write-Host 'HabitBudServer task and firewall rule removed.'
