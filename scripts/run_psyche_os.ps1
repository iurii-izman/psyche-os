param()
$root = Split-Path -Parent $PSScriptRoot
$app = Join-Path $root "desktop\src-tauri\target\release\psyche-os.exe"
$local = Join-Path $root ".env.local"
if (-not (Test-Path -LiteralPath $app)) { Write-Error "Packaged app missing. Run: npm --prefix desktop run tauri:build"; exit 1 }
if (Test-Path -LiteralPath $local) {
  $line = Select-String -LiteralPath $local -Pattern '^OPENAI_API_KEY=(.+)$' | Select-Object -First 1
  if ($line) { $env:OPENAI_API_KEY = $line.Matches[0].Groups[1].Value }
}
Start-Process -FilePath $app -WorkingDirectory (Split-Path $app)
