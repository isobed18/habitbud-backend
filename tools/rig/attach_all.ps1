# attach_all.ps1 - batch-attach items to avatar sockets. Fully customizable.
#
# In Blender, add Empties to each avatar (parented to the body), named to match
# the sockets in item_attach.json, e.g.:
#   socket_r     -> right hand   (hand items)
#   socket_head  -> head         (hats / glasses / mask)
# Export each avatar as .glb into -AvatarsDir. Then:
#
#   tools\rig\attach_all.ps1                              # all sockets, all their items
#   tools\rig\attach_all.ps1 -Sockets socket_r           # HAND only
#   tools\rig\attach_all.ps1 -Sockets socket_head        # HEAD only
#   tools\rig\attach_all.ps1 -Sockets socket_r,socket_head  # hand + head
#   tools\rig\attach_all.ps1 -Items magic_wand,coffee_mug   # only these items
#   tools\rig\attach_all.ps1 -Avatars fox,cat               # only these avatars
#   tools\rig\attach_all.ps1 -Force                      # overwrite (default: skip existing)
#
# Output: <avatar>__<item>.glb in -OutDir. Existing files are KEPT by default so
# your manual fixes (same filename) survive a re-run; pass -Force to regenerate.
param(
    [string[]] $Sockets,                                        # default: all sockets in config
    [string[]] $Items,                                          # default: each socket's full item list
    [string[]] $Avatars,                                        # default: every .glb in AvatarsDir
    [switch]   $Force,                                          # overwrite existing outputs
    [string]   $AvatarsDir = 'D:\blenderprojects\gen\avatars_socketed',
    [string]   $ItemsDir   = 'D:\blenderprojects\gen\items',
    [string]   $OutDir     = 'D:\blenderprojects\gen\out',
    [string]   $Blender    = 'D:\Blender Foundation\Blender 5.1\blender.exe'
)
$ErrorActionPreference = 'Stop'
$script = Join-Path $PSScriptRoot 'attach_socket.py'
$config = Join-Path $PSScriptRoot 'item_attach.json'

if (-not (Test-Path $AvatarsDir)) { throw "AvatarsDir not found: $AvatarsDir" }
if (-not (Test-Path $ItemsDir))   { throw "ItemsDir not found: $ItemsDir" }
New-Item -ItemType Directory -Force $OutDir | Out-Null

$cfg = Get-Content $config -Raw | ConvertFrom-Json
$socketMap = $cfg.sockets

# Which sockets to process.
if (-not $Sockets) { $Sockets = $socketMap.PSObject.Properties.Name }

# Avatars to process.
$avFiles = Get-ChildItem $AvatarsDir -Filter *.glb
if ($Avatars) {
    $avFiles = $avFiles | Where-Object {
        $base = ($_.BaseName -replace '_socketed$','')
        $Avatars -contains $_.BaseName -or $Avatars -contains $base
    }
}
if (-not $avFiles) { throw "no matching .glb avatars in $AvatarsDir" }

# Build the work list: (avatar, socket, item) triples.
$jobs = @()
foreach ($av in $avFiles) {
    foreach ($sock in $Sockets) {
        $sockItems = $socketMap.$sock
        if (-not $sockItems) { Write-Host "warn: socket '$sock' not in config" -ForegroundColor DarkYellow; continue }
        foreach ($it in $sockItems) {
            if ($Items -and ($Items -notcontains $it)) { continue }
            $jobs += [pscustomobject]@{ Avatar = $av; Socket = $sock; Item = $it }
        }
    }
}

$total = $jobs.Count; $n = 0; $ok = 0; $skip = 0; $kept = 0; $fail = 0
Write-Host "Sockets: $($Sockets -join ', ')  |  $total combos  |  out: $OutDir  |  $(if($Force){'overwrite'}else{'skip existing'})" -ForegroundColor Cyan

foreach ($j in $jobs) {
    $n++
    $avName  = $j.Avatar.BaseName -replace '_socketed$',''
    $itPath  = Join-Path $ItemsDir ($j.Item + '.glb')
    $out     = Join-Path $OutDir ("${avName}__$($j.Item).glb")
    if (-not (Test-Path $itPath)) { Write-Host "[$n/$total] skip $($j.Item) (no item GLB)" -ForegroundColor DarkYellow; $skip++; continue }
    if ((Test-Path $out) -and -not $Force) { Write-Host "[$n/$total] keep $(Split-Path $out -Leaf) (exists)" -ForegroundColor DarkGray; $kept++; continue }
    Write-Host "[$n/$total] $avName + $($j.Item) @ $($j.Socket)" -ForegroundColor Cyan
    & $Blender --background --python $script -- `
        --avatar $j.Avatar.FullName --item $itPath --out $out --socket $j.Socket --config $config | Out-Null
    if ($LASTEXITCODE -eq 0) { $ok++ } else { Write-Host "  FAILED" -ForegroundColor Red; $fail++ }
}
Write-Host "done: $ok generated, $kept kept, $skip no-item, $fail failed -> $OutDir" -ForegroundColor Green
