$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$env:PSYCHE_OS_PERSONAL_BUILD_ID = (git -C $repo rev-parse HEAD).Trim()
$profileBytes = [System.IO.File]::ReadAllBytes((Join-Path $repo 'docs\architecture\REAL_DATA_GATE_PROFILE.yaml'))
$sha256 = [System.Security.Cryptography.SHA256]::Create()
try { $env:PSYCHE_OS_PERSONAL_PROFILE_DIGEST = ([System.BitConverter]::ToString($sha256.ComputeHash($profileBytes))).Replace('-', '').ToLowerInvariant() }
finally { $sha256.Dispose() }
if ($env:PSYCHE_OS_PERSONAL_BUILD_ID -notmatch '^[0-9a-f]{40}$') { throw 'Personal build identity must be an exact commit SHA.' }
& npm run sidecar:build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& npx tauri build --features personal-product --config src-tauri/tauri.personal.conf.json
exit $LASTEXITCODE
