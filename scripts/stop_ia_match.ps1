$pidPath = Join-Path (Split-Path $PSScriptRoot -Parent) '.ia-match-processes.json'
function Stop-IAChildren($parentId) {
    foreach ($child in (Get-CimInstance Win32_Process -Filter "ParentProcessId=$parentId")) {
        Stop-IAChildren $child.ProcessId
        Stop-Process -Id $child.ProcessId -ErrorAction SilentlyContinue
    }
}
if (Test-Path -LiteralPath $pidPath) {
    foreach ($entry in (Get-Content -LiteralPath $pidPath -Raw | ConvertFrom-Json)) {
        $process = Get-Process -Id $entry.id -ErrorAction SilentlyContinue
        if ($process -and $process.StartTime.ToUniversalTime().Ticks -eq ([datetime]$entry.started).ToUniversalTime().Ticks) {
            Stop-IAChildren $entry.id
            Stop-Process -Id $entry.id
        }
    }
    Remove-Item -LiteralPath $pidPath
}
