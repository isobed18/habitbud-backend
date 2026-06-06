# attach_all.ps1 - attach every hand item to every avatar's right-hand socket.
#
# You only need to add ONE Empty per avatar in Blender:
#   * name it exactly  socket_r   (right hand)
#   * parent it to the body, position it at the right hand, size it to taste
#   * export the avatar as .glb into -AvatarsDir
# This script then produces <avatar>__<item>.glb for every hand item, automatically.
#
# Usage:
#   tools\rig\attach_all.ps1                                  # all defaults
#   tools\rig\attach_all.ps1 -Socket socket_r                # custom socket name
#   tools\rig\attach_all.ps1 -AvatarsDir D:\blenderprojects\gen\avatars_socketed `
#                            -ItemsDir   D:\blenderprojects\gen\items `
#                            -OutDir     D:\blenderprojects\gen\out
#   tools\rig\attach_all.ps1 -Items magic_wand,coffee_mug    # only these items
#
param(
    [string]   $Socket    = 'socket_r',
    [string]   $AvatarsDir = 'D:\blenderprojects\gen\avatars_socketed',
    [string]   $ItemsDir   = 'D:\blenderprojects\gen\items',
    [string]   $OutDir     = 'D:\blenderprojects\gen\out',
    [string[]] $Items,                                          # default: hand_items from config
    [string]   $Blender    = 'D:\Blender Foundation\Blender 5.1\blender.exe'
)
$ErrorActionPreference = 'Stop'
$script = Join-Path $PSScriptRoot 'attach_socket.py'
$config = Join-Path $PSScriptRoot 'item_attach.json'

if (-not (Test-Path $AvatarsDir)) { throw "AvatarsDir not found: $AvatarsDir" }
if (-not (Test-Path $ItemsDir))   { throw "ItemsDir not found: $ItemsDir" }
New-Item -ItemType Directory -Force $OutDir | Out-Null

# Item list: explicit -Items, else hand_items from the config.
if (-not $Items) { $Items = (Get-Content $config -Raw | ConvertFrom-Json).hand_items }

$avatars = Get-ChildItem $AvatarsDir -Filter *.glb
if (-not $avatars) { throw "no .glb avatars in $AvatarsDir" }

$total = $avatars.Count * $Items.Count
$n = 0; $ok = 0; $skip = 0
Write-Host "Attaching $($Items.Count) item(s) to $($avatars.Count) avatar(s) = $total combos  (socket: $Socket)" -ForegroundColor Cyan

foreach ($av in $avatars) {
    $avName = [System.IO.Path]::GetFileNameWithoutExtension($av.Name)
    foreach ($it in $Items) {
        $n++
        $itPath = Join-Path $ItemsDir ($it + '.glb')
        if (-not (Test-Path $itPath)) { Write-Host "[$n/$total] skip $it (no GLB in ItemsDir)" -ForegroundColor DarkYellow; $skip++; continue }
        $out = Join-Path $OutDir ("${avName}__${it}.glb")
        Write-Host "[$n/$total] $avName + $it -> $(Split-Path $out -Leaf)" -ForegroundColor Cyan
        & $Blender --background --python $script -- `
            --avatar $av.FullName --item $itPath --out $out --socket $Socket --config $config
        if ($LASTEXITCODE -eq 0) { $ok++ } else { Write-Host "  FAILED" -ForegroundColor Red }
    }
}
Write-Host "done: $ok ok, $skip skipped, $($total-$ok-$skip) failed -> $OutDir" -ForegroundColor Green
