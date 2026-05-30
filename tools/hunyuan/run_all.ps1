# One-shot: generate GLBs from the 2D animal images, then auto-import them
# into the HabitBud app's Avatar Studio catalog.
#
#   powershell -ExecutionPolicy Bypass -File tools\hunyuan\run_all.ps1
#
# Adjust the paths below if your layout differs.

$ErrorActionPreference = 'Stop'

$Hunyuan = 'C:\Users\ishak\Hunyuan3D-2'
$Backend = 'C:\Users\ishak\habitbud-backend\habit_tracker'
$Input   = "$Backend\assets\animals_gemini_2d"
$Out     = "$Hunyuan\out"

# Keep the multi-GB model cache off the (full) C: drive.
$env:HF_HOME = 'D:\hf_cache'
$env:HF_HUB_CACHE = 'D:\hf_cache\hub'
$env:HF_XET_CACHE = 'D:\hf_cache\xet'
$env:PYTHONUTF8 = '1'

Write-Host "==> 1/2 Generating GLBs (shape-only) from $Input"
Copy-Item "$PSScriptRoot\generate.py" "$Hunyuan\generate.py" -Force
Push-Location $Hunyuan
conda run -n base --no-capture-output python generate.py --input "$Input" --out "$Out" --steps 30 --octree 256
Pop-Location

Write-Host "==> 2/2 Importing GLBs into the app"
& "$Backend\venv\Scripts\python.exe" "$Backend\manage.py" import_avatar_models --dir "$Out" --scale 1.0

Write-Host "Done. Open the app: Profil -> avatar -> 3B"
