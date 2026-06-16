# publish.ps1 - ONE command after you export fixed combo GLBs in Blender.
#
# Workflow per item:
#   1. In Blender open D:\blenderprojects\gen\out\<avatar>__<item>.glb, place the
#      item, File > Export > glTF 2.0 over the same file.
#   2. Run this script. It:
#        - reads each combo's exact item->socket transform into item_attach.json
#          (so MULTI-item dress-up composes each item exactly like its combo)
#        - publishes the combo GLBs (single-item view loads them directly)
#        - publishes the tuning to the app
#   3. In the app: leave & re-open Avatar Studio, dress up.
#
#   tools\rig\publish.ps1                 # all avatars
#   tools\rig\publish.ps1 -Avatars pinkcat
param(
    [string] $Avatars = '',
    [string] $OutDir  = 'D:\blenderprojects\gen\out'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$app  = Join-Path $root 'habit_tracker'
$py   = Join-Path $app 'venv\Scripts\python.exe'

Write-Host '==> 1/3 reading item transforms from combos' -ForegroundColor Cyan
& "C:\Users\ishak\anaconda3\python.exe" (Join-Path $PSScriptRoot 'sync_tuning_from_combos.py') --dir $OutDir --avatars $Avatars

Write-Host '==> 2/3 publishing combo GLBs' -ForegroundColor Cyan
Push-Location $app
& $py manage.py import_combos --dir $OutDir --clean
Write-Host '==> 3/3 publishing tuning' -ForegroundColor Cyan
& $py manage.py import_attach_tuning
Pop-Location
Write-Host 'done. In the app: leave & re-open Avatar Studio.' -ForegroundColor Green
