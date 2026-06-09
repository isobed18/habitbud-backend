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
    [switch]   $Socket,                                          # use a socket-empty avatar instead of a skeleton
    [string]   $Hand = 'R',
    [string]   $Avatar,                                          # defaults per mode below
    [string]   $Out,
    [string]   $OutDir = 'D:\blenderprojects\out',
    [string]   $Blender = 'D:\Blender Foundation\Blender 5.1\blender.exe'
)
$ErrorActionPreference = 'Stop'
$root    = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$config  = Join-Path $PSScriptRoot 'item_attach.json'
$itemDir = Join-Path $root 'habit_tracker\media\models\items'
if ($Socket) {
    $script = Join-Path $PSScriptRoot 'attach_socket.py'
    if (-not $Avatar) { $Avatar = 'D:\blenderprojects\sagelsoket_pinkcat.glb' }
    $prefix = 'pinkcat'
} else {
    $script = Join-Path $PSScriptRoot 'attach_item.py'
    if (-not $Avatar) { $Avatar = 'D:\blenderprojects\foxrigged.fbx' }
    $prefix = 'fox'
}

function Resolve-Item([string]$name) {
    if (Test-Path $name) { return (Resolve-Path $name).Path }
    $p = Join-Path $itemDir ($name + '.glb')
    if (Test-Path $p) { return $p }
    throw "item not found: $name (looked in $itemDir)"
}

function Attach([string]$itemPath, [string]$outPath) {
    Write-Host "==> $([System.IO.Path]::GetFileNameWithoutExtension($itemPath)) -> $outPath" -ForegroundColor Cyan
    if ($Socket) {
        & $Blender --background --python $script -- `
            --avatar $Avatar --item $itemPath --out $outPath --config $config
    } else {
        & $Blender --background --python $script -- `
            --avatar $Avatar --item $itemPath --out $outPath --hand $Hand --config $config
    }
    if ($LASTEXITCODE -ne 0) { throw "attach failed for $itemPath" }
}

New-Item -ItemType Directory -Force $OutDir | Out-Null

if ($All) {
    $json = Get-Content $config -Raw | ConvertFrom-Json
    if ($Socket) { $names = $json.sockets.socket_r }   # quick single-avatar test: hand items
    else         { $names = $json.bone.PSObject.Properties.Name | Where-Object { $_ -notlike '_*' } }
    foreach ($n in $names) {
        $ip = Join-Path $itemDir ($n + '.glb')
        if (Test-Path $ip) { Attach $ip (Join-Path $OutDir "${prefix}_$n.glb") }
        else { Write-Host "skip $n (no GLB)" -ForegroundColor DarkYellow }
    }
} else {
    if (-not $Item) { throw 'provide -Item <name> or -All' }
    $ip = Resolve-Item $Item
    if (-not $Out) { $Out = Join-Path $OutDir ("${prefix}_" + [System.IO.Path]::GetFileNameWithoutExtension($ip) + '.glb') }
    Attach $ip $Out
}
Write-Host "done. GLBs in $OutDir" -ForegroundColor Green
