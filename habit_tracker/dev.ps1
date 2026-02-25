# HabitBud Dev Launcher (PowerShell)
# Usage: .\dev.ps1        — Start Redis + Django server
#        .\dev.ps1 reset   — Reset DB, then start
#        .\dev.ps1 redis   — Start Redis only

param(
    [string]$Action = "start"
)

$ErrorActionPreference = "Stop"
$REDIS_CONTAINER = "habitbud_redis"
$REDIS_PORT = 6379

function Start-Redis {
    Write-Host "`n🔴 Checking Redis..." -ForegroundColor Cyan
    
    # Check if container exists and is running
    $running = docker ps --filter "name=$REDIS_CONTAINER" --format "{{.Names}}" 2>$null
    if ($running -eq $REDIS_CONTAINER) {
        Write-Host "✅ Redis already running on port $REDIS_PORT" -ForegroundColor Green
        return
    }
    
    # Check if container exists but stopped
    $exists = docker ps -a --filter "name=$REDIS_CONTAINER" --format "{{.Names}}" 2>$null
    if ($exists -eq $REDIS_CONTAINER) {
        Write-Host "▶️  Starting existing Redis container..." -ForegroundColor Yellow
        docker start $REDIS_CONTAINER | Out-Null
    } else {
        Write-Host "📦 Creating Redis container..." -ForegroundColor Yellow
        docker run -d --name $REDIS_CONTAINER -p "${REDIS_PORT}:6379" redis:7-alpine redis-server --appendonly yes | Out-Null
    }
    
    # Wait for Redis to be ready
    $attempts = 0
    while ($attempts -lt 10) {
        try {
            $tcp = New-Object System.Net.Sockets.TcpClient
            $tcp.Connect("127.0.0.1", $REDIS_PORT)
            $tcp.Close()
            Write-Host "✅ Redis is ready on port $REDIS_PORT" -ForegroundColor Green
            return
        } catch {
            $attempts++
            Start-Sleep -Milliseconds 500
        }
    }
    Write-Host "❌ Redis failed to start!" -ForegroundColor Red
    exit 1
}

function Start-Server {
    Write-Host "`n🚀 Starting Django server..." -ForegroundColor Cyan
    
    # Set Redis env vars for Django
    $env:REDIS_HOST = "127.0.0.1"
    $env:REDIS_PORT = $REDIS_PORT
    
    # Run migrations
    Write-Host "📦 Checking migrations..." -ForegroundColor Yellow
    & .\venv\Scripts\python.exe manage.py migrate --noinput
    
    # Start server
    Write-Host "`n✅ Server starting at http://localhost:8000" -ForegroundColor Green
    & .\venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
}

function Reset-Database {
    Write-Host "`n🔄 Resetting database..." -ForegroundColor Cyan
    $env:REDIS_HOST = "127.0.0.1"
    $env:REDIS_PORT = $REDIS_PORT
    & .\venv\Scripts\python.exe manage.py reset_db
}

# Main
switch ($Action) {
    "start" {
        Start-Redis
        Start-Server
    }
    "reset" {
        Start-Redis
        Reset-Database
        Start-Server
    }
    "redis" {
        Start-Redis
    }
    default {
        Write-Host "Usage: .\dev.ps1 [start|reset|redis]" -ForegroundColor Yellow
    }
}
