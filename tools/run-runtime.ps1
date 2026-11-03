param([string]$RomPath = (Join-Path $PSScriptRoot '..\Assets\data.z64'))
$ErrorActionPreference = 'Stop'
try {
    $RomPath = (Resolve-Path -LiteralPath $RomPath).Path
    $expectedHash = '790f36a3ddd64e4dcd08c479b0b66f9080d0191473e92fa895f53d15706167bb'
    if ((Get-FileHash -LiteralPath $RomPath -Algorithm SHA256).Hash -ne $expectedHash) { throw 'ROM does not match the verified Wetrix revision.' }
    $runtimePath = Join-Path $PSScriptRoot '..\build\windows\Release\WetrixRuntime.exe'
    if (-not (Test-Path -LiteralPath $runtimePath)) { throw 'Build WetrixRuntime first; see README.md.' }
    Push-Location (Join-Path $PSScriptRoot '..')
    try { & $runtimePath $RomPath; $result = $LASTEXITCODE } finally { Pop-Location }
    exit $result
} catch { Write-Error $_ -ErrorAction Continue; exit 1 }
