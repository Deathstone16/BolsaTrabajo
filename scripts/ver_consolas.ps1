param(
    [ValidateSet('todas', 'django', 'api', 'celery', 'extraction', 'matching')]
    [string]$Servicio = 'todas'
)

$ErrorActionPreference = 'Stop'
$bolsaPath = Split-Path $PSScriptRoot -Parent
$rootPath = Split-Path (Split-Path $bolsaPath -Parent) -Parent
$apiPath = Join-Path $rootPath 'api\ia_api\backend'
$services = @{
    django = @{Title = 'Django - Web 8000'; Directory = $bolsaPath; Log = 'django'}
    api = @{Title = 'FastAPI - API 8001'; Directory = $apiPath; Log = 'fastapi'}
    celery = @{Title = 'Celery - Analisis y compatibilidad'; Directory = $apiPath; Log = 'celery'}
    extraction = @{Title = 'Dispatcher - CV y ofertas'; Directory = $bolsaPath; Log = 'extraction-dispatcher'}
    matching = @{Title = 'Dispatcher - Matching'; Directory = $bolsaPath; Log = 'match-dispatcher'}
}

if ($Servicio -eq 'todas') {
    $powershellPath = (Get-Process -Id $PID).Path
    $terminal = Get-Command wt.exe -ErrorAction SilentlyContinue
    if (-not $terminal) { throw 'No se encontro Windows Terminal (wt.exe).' }
    $terminalArguments = @('--window', 'IEN-Ejecucion')
    foreach ($serviceName in @('django', 'api', 'celery', 'extraction', 'matching')) {
        if ($serviceName -ne 'django') { $terminalArguments += ';' }
        $terminalArguments += @(
            'new-tab', '--title', $services[$serviceName].Title, '--suppressApplicationTitle',
            '--startingDirectory', $bolsaPath, $powershellPath,
            '-NoLogo', '-NoProfile', '-NoExit', '-File', $PSCommandPath, '-Servicio', $serviceName
        )
    }
    & $terminal.Source @terminalArguments
    if ($LASTEXITCODE) { throw 'No se pudo abrir la ventana de consolas.' }
    Write-Output 'Una ventana de Windows Terminal con cinco pestanas de logs.'
    return
}

$service = $services[$Servicio]
$Host.UI.RawUI.WindowTitle = 'IEN | ' + $service.Title
Write-Host $service.Title -ForegroundColor Cyan
Write-Host 'Logs en vivo. Ctrl+C o cerrar esta ventana detiene solo el visor.' -ForegroundColor DarkGray
Write-Host 'Los servidores siguen ejecutandose en segundo plano.' -ForegroundColor DarkGray

$sources = foreach ($suffix in @('.log', '-error.log')) {
    $path = Join-Path $service.Directory ($service.Log + $suffix)
    [pscustomobject]@{Path = $path; Position = [long]0; Started = $false; IsError = $suffix -eq '-error.log'}
}

while ($true) {
    foreach ($source in $sources) {
        if (-not (Test-Path -LiteralPath $source.Path)) { continue }
        $stream = $null
        $reader = $null
        try {
            $stream = [System.IO.File]::Open($source.Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
            if (-not $source.Started) {
                # Limitar el historial inicial; luego mostrar solo contenido nuevo.
                $source.Position = [Math]::Max([long]0, $stream.Length - 6000)
                $source.Started = $true
            }
            if ($source.Position -gt $stream.Length) { $source.Position = [long]0 }
            if ($source.Position -eq $stream.Length) { continue }
            [void]$stream.Seek($source.Position, [System.IO.SeekOrigin]::Begin)
            $reader = [System.IO.StreamReader]::new($stream, [System.Text.Encoding]::UTF8)
            $chunk = $reader.ReadToEnd()
            $source.Position = $stream.Position
            if ($chunk) {
                $label = if ($source.IsError) { 'LOG/STDERR' } else { 'STDOUT' }
                Write-Host ("`n--- {0} ---" -f $label) -ForegroundColor DarkCyan
                Write-Host $chunk -NoNewline
            }
        } catch [System.IO.IOException] {
            # Reintentar si el servicio esta recreando o rotando el log.
        } finally {
            if ($reader) { $reader.Dispose() }
            elseif ($stream) { $stream.Dispose() }
        }
    }
    Start-Sleep -Milliseconds 700
}
