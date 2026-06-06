# attach.ps1 - bind an item GLB to the rigged avatar's hand bone (one command).
#
#   tools\rig\attach.ps1 -Item magic_wand
#   tools\rig\attach.ps1 -Item coffee_mug -Hand L
#   tools\rig\attach.ps1 -Item dumbell -Avatar D:\blenderprojects\foxrigged.fbx -Out D:\blenderprojects\out\fox_dumbell.glb
#   tools\rig\attach.ps1 -All                          # every hand item in the config
#
# -Item may be a name (magic_wand) found under media\models\items, or a full path.
param(
    [string]   $Item,
    [switch]   $All,
    [string]   $Hand = 'R',
    [string]   $Avatar = 'D:\blenderprojects\foxrigged.fbx',
    [string]   $Out,
    [string]   $OutDir = 'D:\blenderprojects\out',
    [string]   $Blender = 'D:\Blender Foundation\Blender 5.1\blender.exe'
)
$ErrorActionPreference = 'Stop'
$repo    = Split-Path (Split-Path $PSScriptRoot -Parent) -Leaf  # unused, clarity
$root    = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$script  = Join-Path $PSScriptRoot 'attach_item.py'
$config  = Join-Path $PSScriptRoot 'item_attach.json'
$itemDir = Join-Path $root 'habit_tracker\media\models\items'

function Resolve-Item([string]$name) {
    if (Test-Path $name) { return (Resolve-Path $name).Path }
    $p = Join-Path $itemDir ($name + '.glb')
    if (Test-Path $p) { return $p }
    throw "item not found: $name (looked in $itemDir)"
}

function Attach([string]$itemPath, [string]$outPath) {
    Write-Host "==> $([System.IO.Path]::GetFileNameWithoutExtension($itemPath)) -> $outPath" -ForegroundColor Cyan
    & $Blender --background --python $script -- `
        --avatar $Avatar --item $itemPath --out $outPath --hand $Hand --config $config
    if ($LASTEXITCODE -ne 0) { throw "attach failed for $itemPath" }
}

New-Item -ItemType Directory -Force $OutDir | Out-Null

if ($All) {
    $names = (Get-Content $config -Raw | ConvertFrom-Json).PSObject.Properties.Name |
             Where-Object { $_ -notlike '_*' }
    foreach ($n in $names) {
        $ip = Join-Path $itemDir ($n + '.glb')
        if (Test-Path $ip) { Attach $ip (Join-Path $OutDir "fox_$n.glb") }
        else { Write-Host "skip $n (no GLB)" -ForegroundColor DarkYellow }
    }
} else {
    if (-not $Item) { throw 'provide -Item <name> or -All' }
    $ip = Resolve-Item $Item
    if (-not $Out) { $Out = Join-Path $OutDir ("fox_" + [System.IO.Path]::GetFileNameWithoutExtension($ip) + '.glb') }
    Attach $ip $Out
}
Write-Host "done. GLBs in $OutDir" -ForegroundColor Green
