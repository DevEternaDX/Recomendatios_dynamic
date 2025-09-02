# Run both backend (FastAPI) and admin UI (Next.js) for development on Windows
# Usage:
#   .\run-dev.ps1         -> starts services in new windows (visible)
#   .\run-dev.ps1 -Background -> starts backend hidden (background) and UI visible

param(
    [switch]$Background
)

try {
    $root = Split-Path -Parent $MyInvocation.MyCommand.Path
} catch {
    $root = Get-Location
}
Set-Location $root

# Ensure admin UI points to local API
$envFile = Join-Path $root "admin-ui\.env.local"
if (-not (Test-Path $envFile)) {
    "NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000" | Out-File -FilePath $envFile -Encoding UTF8
    Write-Output "Created admin-ui/.env.local pointing to http://127.0.0.1:8000"
} else {
    Write-Output "Using existing admin-ui/.env.local"
}

# Ensure python venv exists
$pyExe = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $pyExe)) {
    Write-Output "Creating virtualenv .venv (py -3.11 -m venv .venv)"
    py -3.11 -m venv .venv
}

# Start backend
$backendArgs = @("-m","uvicorn","backend.app:app","--host","127.0.0.1","--port","8000","--reload","--reload-dir","backend")
if ($Background) {
    Start-Process -FilePath $pyExe -ArgumentList $backendArgs -WindowStyle Hidden -WorkingDirectory $root
    Write-Output "Backend started in background (hidden)."
} else {
    Start-Process -FilePath $pyExe -ArgumentList $backendArgs -WorkingDirectory $root
    Write-Output "Backend started in new window."
}

# Start Next dev
$node = "C:\Program Files\nodejs\node.exe"
$adminDir = Join-Path $root "admin-ui"
$nextArgs = @("node_modules/next/dist/bin/next","dev","-p","3000","--turbo")
if (Test-Path $node) {
    Start-Process -FilePath $node -ArgumentList $nextArgs -WorkingDirectory $adminDir
    Write-Output "Next dev started in new window (admin-ui).	Open http://127.0.0.1:3000"
} else {
    Write-Output "node.exe not found at 'C:\Program Files\nodejs\node.exe'. Start Next manually inside admin-ui with 'npm run dev'"
}

Write-Output "Done. Backend: http://127.0.0.1:8000  UI: http://127.0.0.1:3000"


