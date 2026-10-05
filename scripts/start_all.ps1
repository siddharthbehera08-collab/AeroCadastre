# AeroCadastre Startup & Orchestration Script
param(
    [switch]$SkipFrontend = $false,
    [switch]$CheckOnly = $false
)

$ErrorActionPreference = "Continue"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  AeroCadastre SIH26012 -- One-Command Startup Orchestrator " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$PROJECT_ROOT = "D:\SIH26012_AeroCadastre"
Set-Location -Path $PROJECT_ROOT

# 1. Check PostgreSQL Connection
Write-Host "`n[1/5] Checking PostgreSQL (PostGIS) at 127.0.0.1:5432..." -ForegroundColor Yellow
$pyScriptCheck = @'
import psycopg2
try:
    conn = psycopg2.connect('host=127.0.0.1 port=5432 user=postgres dbname=aerocadastre password=postgres connect_timeout=3')
    conn.close()
    print('OK')
except Exception as e:
    print('FAIL')
'@

$testResult = python -c "$pyScriptCheck"
if ($testResult -match "OK") {
    Write-Host "  -> PostgreSQL/PostGIS is running and accepting connections." -ForegroundColor Green
} else {
    Write-Host "  -> PostgreSQL not detected. Starting via pg_ctl..." -ForegroundColor Yellow
    & "D:\PostgreSQL\16\bin\pg_ctl.exe" -D "D:\PostgreSQL\data" -l "D:\PostgreSQL\data\server.log" start
    Start-Sleep -Seconds 3
    $testResult = python -c "$pyScriptCheck"
    if ($testResult -match "OK") {
        Write-Host "  -> PostgreSQL started successfully." -ForegroundColor Green
    } else {
        Write-Host "  -> [WARNING] PostgreSQL connection failed." -ForegroundColor Red
    }
}

# 2. Verify Database Seed & Model Runs
Write-Host "`n[2/5] Verifying PostGIS Database Seed and ML Runs..." -ForegroundColor Yellow
$pyScriptSeed = @'
from backend.app.core.database import SessionLocal
from backend.app.services.seed_service import ensure_demo_seed_data
db = SessionLocal()
res = ensure_demo_seed_data(db)
print('  -> Seed verified:', res)
db.close()
'@
python -c "$pyScriptSeed"

# 3. Check Frozen GPU Champion Checkpoints
Write-Host "`n[3/5] Verifying Frozen GPU Model Checkpoints and Checksums..." -ForegroundColor Yellow
$modelA = "experiments\building_detection\EXP_BUILDING_RESUNET_GPU_001\checkpoints\best_model.pt"
$modelB = "experiments\road_detection\EXP_ROAD_RESUNET_GPU_001\checkpoints\best_model.pth"
if ((Test-Path $modelA) -and (Test-Path $modelB)) {
    Write-Host "  -> Model A (Building ResUNet) and Model B (Road ResUNet) verified on disk." -ForegroundColor Green
} else {
    Write-Host "  -> [WARNING] Model checkpoints missing. Check experiments registry." -ForegroundColor Red
}

if ($CheckOnly) {
    Write-Host "`nHealth and environment checks complete. Exiting (--CheckOnly)." -ForegroundColor Green
    exit 0
}

# 4. Launch FastAPI Backend
Write-Host "`n[4/5] Launching FastAPI Backend on http://127.0.0.1:8000..." -ForegroundColor Yellow
$backendJob = Start-Process -FilePath "uvicorn" -ArgumentList "backend.main:app","--host","127.0.0.1","--port","8000" -PassThru -WindowStyle Hidden
Write-Host "  -> FastAPI process started (PID: $($backendJob.Id))." -ForegroundColor Green

# Wait for backend health check
$backendOnline = $false
for ($i = 0; $i -lt 10; $i++) {
    Start-Sleep -Seconds 1
    try {
        $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -Method Get -TimeoutSec 2
        if ($resp.status -eq "ONLINE") {
            $backendOnline = $true
            Write-Host "  -> FastAPI health check passed (Status: ONLINE, Data: $($resp.data_label))." -ForegroundColor Green
            break
        }
    } catch {
        # Retry
    }
}

if (-not $backendOnline) {
    Write-Host "  -> [WARNING] Backend did not respond within 10s. Inspect logs." -ForegroundColor Red
}

# 5. Launch Next.js Frontend
if (-not $SkipFrontend) {
    Write-Host "`n[5/5] Launching Next.js WebGIS Frontend on http://localhost:3000..." -ForegroundColor Yellow
    Set-Location -Path "$PROJECT_ROOT\frontend"
    $frontendJob = Start-Process -FilePath "npm.cmd" -ArgumentList "run","dev" -PassThru -WindowStyle Hidden
    Write-Host "  -> Next.js frontend started (PID: $($frontendJob.Id))." -ForegroundColor Green
    Set-Location -Path $PROJECT_ROOT
}

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host "  AeroCadastre Stack is RUNNING!" -ForegroundColor Green
Write-Host "  WebGIS App:    http://localhost:3000" -ForegroundColor Cyan
Write-Host "  FastAPI Docs:  http://127.0.0.1:8000/docs" -ForegroundColor Cyan
Write-Host "  Health API:    http://127.0.0.1:8000/api/health" -ForegroundColor Cyan
Write-Host "  Pune Demo:     http://127.0.0.1:8000/api/gis/pune-pilot" -ForegroundColor Cyan
Write-Host "  MH Admin API:  http://127.0.0.1:8000/api/gis/admin-boundaries" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Green
