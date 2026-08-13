$ErrorActionPreference = "Stop"

$desktopRoot = Split-Path -Parent $PSScriptRoot
$repoRoot = Split-Path -Parent $desktopRoot
$app = Join-Path $desktopRoot "src-tauri\target\debug\psyche-os-desktop.exe"

if (-not (Test-Path -LiteralPath $app)) {
    throw "Debug desktop binary is missing. Run 'npm --prefix desktop run tauri -- build --debug' first."
}

Push-Location $repoRoot
try {
    uv run python scripts/dev/test_e02_desktop.py --executable $app
    if ($LASTEXITCODE -ne 0) {
        throw "Native desktop UIA test failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
