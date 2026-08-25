$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$env:PSYCHE_OS_PERSONAL_BUILD_ID = (git -C $repo rev-parse HEAD).Trim()
$env:PSYCHE_OS_PERSONAL_PROFILE_DIGEST = (Get-FileHash (Join-Path $repo 'docs\architecture\REAL_DATA_GATE_PROFILE.yaml') -Algorithm SHA256).Hash.ToLowerInvariant()
if ($env:PSYCHE_OS_PERSONAL_BUILD_ID -notmatch '^[0-9a-f]{40}$') { throw 'Personal build identity must be an exact commit SHA.' }
& npm run sidecar:build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& npx tauri build --features personal-product --config src-tauri/tauri.personal.conf.json
exit $LASTEXITCODE
