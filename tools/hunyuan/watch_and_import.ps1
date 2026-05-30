# =============================================================================
# watch_and_import.ps1
# Watches C:\Users\ishak\Hunyuan3D-2\out_v2 for new/modified .glb files
# and automatically runs the Django import_avatar_models command.
# =============================================================================

$WatchDir   = "D:\Hunyuan3D-2\out_v2"
$PythonExe  = "C:\Users\ishak\habitbud-backend\habit_tracker\venv\Scripts\python.exe"
$ManagePy   = "C:\Users\ishak\habitbud-backend\habit_tracker\manage.py"
$DelaySeconds = 5

# Verify paths
if (-not (Test-Path $WatchDir)) {
    Write-Host "[ERROR] Watch directory does not exist: $WatchDir" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $PythonExe)) {
    Write-Host "[WARN] Venv python not found, falling back to Anaconda python." -ForegroundColor Yellow
    $PythonExe = "C:\Users\ishak\anaconda3\python.exe"
    if (-not (Test-Path $PythonExe)) {
        Write-Host "[ERROR] Anaconda python also not found!" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  GLB File Watcher & Auto-Importer" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Watching : $WatchDir" -ForegroundColor Gray
Write-Host "  Filter   : *.glb" -ForegroundColor Gray
Write-Host "  Python   : $PythonExe" -ForegroundColor Gray
Write-Host "  Delay    : ${DelaySeconds}s after detection" -ForegroundColor Gray
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Watching for new .glb files... (Press Ctrl+C to stop)" -ForegroundColor Green

# ---------------------------------------------------------------------------
# Set up FileSystemWatcher
# ---------------------------------------------------------------------------
$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = $WatchDir
$watcher.Filter = "*.glb"
$watcher.IncludeSubdirectories = $true
$watcher.NotifyFilter = [System.IO.NotifyFilters]::FileName -bor
                         [System.IO.NotifyFilters]::LastWrite -bor
                         [System.IO.NotifyFilters]::Size

$watcher.EnableRaisingEvents = $true

# Track recently processed files to avoid duplicate runs
$script:lastProcessed = @{}

# Handler function shared by Created and Changed events
$action = {
    $path      = $Event.SourceEventArgs.FullPath
    $changeTpe = $Event.SourceEventArgs.ChangeType
    $now       = Get-Date

    # Debounce: skip if we processed the same file in the last 15 seconds
    if ($script:lastProcessed.ContainsKey($path)) {
        $elapsed = ($now - $script:lastProcessed[$path]).TotalSeconds
        if ($elapsed -lt 15) {
            return
        }
    }
    $script:lastProcessed[$path] = $now

    $fileName = [System.IO.Path]::GetFileName($path)

    Write-Host ""
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Detected $changeTpe : $fileName" -ForegroundColor Yellow
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Waiting ${using:DelaySeconds}s for write to finish..." -ForegroundColor Gray

    Start-Sleep -Seconds $using:DelaySeconds

    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Running import_avatar_models..." -ForegroundColor Cyan

    $importArgs = @(
        $using:ManagePy,
        "import_avatar_models",
        "--dir", $using:WatchDir,
        "--scale", "1.0"
    )

    try {
        & $using:PythonExe @importArgs 2>&1 | ForEach-Object { Write-Host "  $_" }
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Import completed for: $fileName" -ForegroundColor Green
    }
    catch {
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Import FAILED: $_" -ForegroundColor Red
    }

    Write-Host ""
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Watching for new .glb files..." -ForegroundColor Green
}

# Register events
Register-ObjectEvent -InputObject $watcher -EventName Created -Action $action -SourceIdentifier "GlbCreated" | Out-Null
Register-ObjectEvent -InputObject $watcher -EventName Changed -Action $action -SourceIdentifier "GlbChanged" | Out-Null

# ---------------------------------------------------------------------------
# Keep the script alive indefinitely
# ---------------------------------------------------------------------------
try {
    while ($true) {
        Wait-Event -Timeout 1 | Out-Null
    }
}
finally {
    # Clean up on exit
    Write-Host "`n[$(Get-Date -Format 'HH:mm:ss')] Stopping watcher..." -ForegroundColor Yellow
    Unregister-Event -SourceIdentifier "GlbCreated" -ErrorAction SilentlyContinue
    Unregister-Event -SourceIdentifier "GlbChanged" -ErrorAction SilentlyContinue
    $watcher.EnableRaisingEvents = $false
    $watcher.Dispose()
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Watcher stopped." -ForegroundColor Red
}
