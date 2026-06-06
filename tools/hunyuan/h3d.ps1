# h3d - HabitBud 3D production CLI launcher.
# Sets env/paths, syncs the scripts to the Hunyuan repo, forwards all args to h3d.py.
#
#   tools\hunyuan\h3d.ps1 gen habit_tracker\assets\t-poses -o D:\Hunyuan3D-2\out_tpose
#   tools\hunyuan\h3d.ps1 gen fox.png -q high
#   tools\hunyuan\h3d.ps1 watch D:\Hunyuan3D-2\inbox -o D:\Hunyuan3D-2\out_tpose
#   tools\hunyuan\h3d.ps1 info D:\Hunyuan3D-2\out_tpose\fox.glb
#
# Everything after the script name is passed straight to h3d.py, so run
#   tools\hunyuan\h3d.ps1 gen --help   for the full option list.

$ErrorActionPreference = 'Stop'
$Hunyuan = 'D:\Hunyuan3D-2'
$Python  = 'C:\Users\ishak\anaconda3\python.exe'

$env:HF_HOME       = 'D:\hf_cache'
$env:HF_HUB_CACHE  = 'D:\hf_cache\hub'
$env:HF_XET_CACHE  = 'D:\hf_cache\xet'
$env:PYTHONUTF8    = '1'
$env:PYTHONUNBUFFERED = '1'

# Keep the working copies in the Hunyuan repo in sync with the source of truth.
Copy-Item "$PSScriptRoot\generate.py" "$Hunyuan\generate.py" -Force
Copy-Item "$PSScriptRoot\h3d.py"      "$Hunyuan\h3d.py"      -Force

# Resolve a relative path argument (gen/watch input) against the caller's CWD,
# since we run from inside the Hunyuan repo.
$caller = Get-Location
$fwd = @()
foreach ($a in $args) {
    if ($a -and -not $a.StartsWith('-') -and (Test-Path (Join-Path $caller $a))) {
        $fwd += (Resolve-Path (Join-Path $caller $a)).Path
    } else {
        $fwd += $a
    }
}

Push-Location $Hunyuan
try { & $Python h3d.py @fwd } finally { Pop-Location }
exit $LASTEXITCODE
