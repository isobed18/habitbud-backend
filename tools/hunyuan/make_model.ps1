# HabitBud — one-command 3D model generation wrapper.
#
# Usage (from the backend repo root):
#   powershell -ExecutionPolicy Bypass -File tools\hunyuan\make_model.ps1 `
#       -Input habit_tracker\assets\t-poses -Texture -Faces 30000 -Octree 320
#
# Drops <name>.glb files into -Out (default D:\Hunyuan3D-2\out_tpose).

param(
    [Parameter(Mandatory = $true)] [string] $Input,        # folder of input images
    [string] $Out = "D:\Hunyuan3D-2\out_tpose",
    [int]    $Faces = 30000,                                # 0 = no reduction
    [int]    $Octree = 320,
    [int]    $Steps = 50,
    [switch] $Texture
)

$ErrorActionPreference = 'Stop'
$Hunyuan = 'D:\Hunyuan3D-2'
$Python  = 'C:\Users\ishak\anaconda3\python.exe'

# Resolve a relative -Input against the current directory.
if (-not [System.IO.Path]::IsPathRooted($Input)) { $Input = Join-Path (Get-Location) $Input }
if (-not (Test-Path $Input)) { Write-Error "Input folder not found: $Input"; exit 1 }

$env:HF_HOME = 'D:\hf_cache'
$env:HF_HUB_CACHE = 'D:\hf_cache\hub'
$env:HF_XET_CACHE = 'D:\hf_cache\xet'
$env:PYTHONUTF8 = '1'
$env:PYTHONUNBUFFERED = '1'

# Keep the working copy of generate.py in sync with the repo's source.
Copy-Item "$PSScriptRoot\generate.py" "$Hunyuan\generate.py" -Force

$texFlag = @()
if ($Texture) { $texFlag = @('--texture') }

Write-Host "==> Generating 3D models" -ForegroundColor Cyan
Write-Host "    input : $Input"
Write-Host "    out   : $Out"
Write-Host "    faces : $Faces | octree : $Octree | steps : $Steps | texture : $($Texture.IsPresent)"

Push-Location $Hunyuan
& $Python generate.py --input "$Input" --out "$Out" --faces $Faces --octree $Octree --steps $Steps @texFlag
$code = $LASTEXITCODE
Pop-Location

if ($code -eq 0) {
    Write-Host "==> Done. GLBs in $Out" -ForegroundColor Green
    Write-Host "    Next: rig in Blender / RigAnything, or import via manage.py import_avatar_models / import_items"
} else {
    Write-Error "Generation failed (exit $code). See output above."
}
