# ──────────────────────────────────────────────────────
# Run tests using docker compose (PostgreSQL + pytest).
# Usage:  .\scripts\run_tests.ps1
# ──────────────────────────────────────────────────────

docker compose version *> $null
if ($LASTEXITCODE -eq 0) {
    $composeCommand = "docker"
    $composePrefix = @("compose")
}
elseif (Get-Command docker-compose -ErrorAction SilentlyContinue) {
    $composeCommand = "docker-compose"
    $composePrefix = @()
}
else {
    Write-Error "Docker Compose is not available. Install docker compose or docker-compose."
    exit 1
}

Write-Host "🚀 Building and starting test environment..." -ForegroundColor Cyan
& $composeCommand @composePrefix -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from test-runner
$exitCode = $LASTEXITCODE

Write-Host "🧹 Cleaning up containers..." -ForegroundColor Cyan
& $composeCommand @composePrefix -f docker-compose.test.yml down -v

exit $exitCode
