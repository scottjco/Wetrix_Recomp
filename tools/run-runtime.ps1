param([string]$RomPath = (Join-Path $PSScriptRoot '..\Assets\data.z64'))
$ErrorActionPreference = 'Stop'
try {
    $runtimePath = Join-Path $PSScriptRoot '..\build\windows\Release\WetrixRuntime.exe'
    if (-not (Test-Path -LiteralPath $runtimePath)) { throw 'Build WetrixRuntime first; see README.md.' }
    Push-Location (Join-Path $PSScriptRoot '..')
    try { & $runtimePath $RomPath; $result = $LASTEXITCODE } finally { Pop-Location }
    exit $result
} catch { Write-Error $_ -ErrorAction Continue; exit 1 }
