param([string]$RomPath = (Join-Path $PSScriptRoot '..\Assets\data.z64'))
$ErrorActionPreference = 'Stop'
try {
    $expectedHash = '790f36a3ddd64e4dcd08c479b0b66f9080d0191473e92fa895f53d15706167bb'
    if ((Get-FileHash -LiteralPath $RomPath -Algorithm SHA256).Hash -ne $expectedHash) {
        throw 'This ROM does not match the verified Wetrix revision. Diagnostic stopped.'
    }
    $probePath = Join-Path $PSScriptRoot '..\build\windows\Release\WetrixBootProbe.exe'
    if (-not (Test-Path -LiteralPath $probePath)) {
        throw 'Build the diagnostic first: cmake --preset windows, then cmake --build --preset boot-probe'
    }
    & $probePath $RomPath
    exit $LASTEXITCODE
} catch {
    Write-Error $_ -ErrorAction Continue
    exit 1
}
