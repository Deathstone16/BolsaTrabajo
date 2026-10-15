$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'stop_ia_match.ps1')
& (Join-Path $PSScriptRoot 'start_ia_match.ps1')
