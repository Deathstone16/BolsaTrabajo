$ErrorActionPreference = 'Stop'
$bolsaPath = Split-Path $PSScriptRoot -Parent
$rootPath = Split-Path (Split-Path $bolsaPath -Parent) -Parent
$apiPath = Join-Path $rootPath 'api\ia_api\backend'
$pidPath = Join-Path $bolsaPath '.ia-match-processes.json'

if (Test-Path -LiteralPath $pidPath) {
    $running = @(Get-Content -LiteralPath $pidPath -Raw | ConvertFrom-Json | Where-Object {
        $process = Get-Process -Id $_.id -ErrorAction SilentlyContinue
        $process -and $process.StartTime.ToUniversalTime().Ticks -eq ([datetime]$_.started).ToUniversalTime().Ticks
    })
    if ($running.Count) { throw 'Hay procesos ia-match activos. Ejecutá scripts\stop_ia_match.ps1 primero.' }
}
& "$bolsaPath\.venv\Scripts\python.exe" "$PSScriptRoot\configure_ia_match.py"
if ($LASTEXITCODE) { throw 'Falló la configuración.' }
Push-Location $apiPath
try { docker compose up -d redis; if ($LASTEXITCODE) { throw 'No se pudo iniciar Redis. Abrí Docker Desktop.' } }
finally { Pop-Location }
Push-Location $bolsaPath
try {
    $databaseEngine = & '.\.venv\Scripts\python.exe' -c 'import os; from dotenv import load_dotenv; load_dotenv(); print(os.environ.get("DB_ENGINE", "sqlite"))'
    if ($LASTEXITCODE) { throw 'No se pudo leer la configuración de base de datos.' }
    if ($databaseEngine.Trim() -eq 'postgresql') {
        # El contenedor es opcional: también se admite PostgreSQL externo.
        $localPostgres = docker container ls -a --filter 'name=^/ien-postgres-integracion$' --format '{{.Names}}'
        if ($localPostgres) {
            docker start ien-postgres-integracion | Out-Null
            if ($LASTEXITCODE) { throw 'No se pudo iniciar PostgreSQL local.' }
            for ($attempt = 0; $attempt -lt 30; $attempt++) {
                docker exec ien-postgres-integracion pg_isready -q | Out-Null
                if ($LASTEXITCODE -eq 0) { break }
                Start-Sleep -Seconds 1
            }
            if ($LASTEXITCODE) { throw 'PostgreSQL local no está listo.' }
        }
    } elseif (Test-Path db.sqlite3) {
        Copy-Item -LiteralPath db.sqlite3 -Destination ('db.sqlite3.ia-match-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.bak')
    }
    & '.\.venv\Scripts\python.exe' manage.py migrate
    if ($LASTEXITCODE) { throw 'Falló migrate.' }
}
finally { Pop-Location }

$processes = @()
function Start-IAProcess($name, $directory, $arguments) {
    $process = Start-Process -FilePath "$directory\.venv\Scripts\python.exe" -ArgumentList $arguments -WorkingDirectory $directory -WindowStyle Hidden -RedirectStandardOutput "$directory\$name.log" -RedirectStandardError "$directory\$name-error.log" -PassThru
    $script:processes += @{id=$process.Id; name=$name; started=$process.StartTime.ToUniversalTime().ToString('o')}
    $script:processes | ConvertTo-Json | Set-Content -LiteralPath $pidPath
}
Start-IAProcess 'fastapi' $apiPath @('-u','-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8001')
Start-IAProcess 'celery' $apiPath @('-u','-m','celery','-A','app.core.celery_app.celery_app','worker','--pool=solo','--loglevel=INFO')
Start-IAProcess 'django' $bolsaPath @('-u','-m','daphne','-b','127.0.0.1','-p','8000','ientrabajo.asgi:application')
Start-IAProcess 'extraction-dispatcher' $bolsaPath @('-u','manage.py','run_integration_dispatcher','--kind','extraction')
Start-IAProcess 'match-dispatcher' $bolsaPath @('-u','manage.py','run_integration_dispatcher','--kind','match')
Write-Output 'Web: http://127.0.0.1:8000/ | API única de CV y compatibilidad: http://127.0.0.1:8001/docs'
