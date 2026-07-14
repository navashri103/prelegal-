Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Test-Path .env)) {
    Write-Error "Missing .env file. Copy .env.example to .env and add your OPENROUTER_API_KEY."
    exit 1
}

docker build -t prelegal .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

docker rm -f prelegal 2>$null | Out-Null

docker run -d --name prelegal -p 8000:8000 -v prelegal-db:/app/db --env-file .env prelegal
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Prelegal is starting at http://localhost:8000"
