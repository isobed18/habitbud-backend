# Deprecated thin shim -> use h3d.ps1 (the 3D production CLI).
#   old:  make_model.ps1 -Input <folder> -Texture -Faces 30000
#   new:  h3d.ps1 gen <folder> -q balanced
# Kept so existing muscle memory / docs still work; forwards to `h3d gen`.
param(
    [Parameter(Mandatory = $true)] [string] $Input,
    [string] $Out = 'D:\Hunyuan3D-2\out_tpose',
    [int]    $Faces = 30000,
    [int]    $Octree = 320,
    [int]    $Steps = 50,
    [switch] $Texture
)
$h3d = Join-Path $PSScriptRoot 'h3d.ps1'
$fwd = @('gen', $Input, '-o', $Out, '--faces', $Faces, '--octree', $Octree, '--steps', $Steps)
if (-not $Texture) { $fwd += '--no-texture' }
& $h3d @fwd
exit $LASTEXITCODE
