param([switch]$BoundedOpenAI)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$env:PSYCHE_OS_PERSONAL_BUILD_ID = (git -C $repo rev-parse HEAD).Trim()
$profilePath = if ($BoundedOpenAI) { 'docs\architecture\REAL_DATA_GATE_PROFILE_OPENAI.yaml' } else { 'docs\architecture\REAL_DATA_GATE_PROFILE.yaml' }
$env:PSYCHE_OS_PERSONAL_PROFILE_ID = if ($BoundedOpenAI) { 'local_personal_bounded_openai_reflection_windows_v1' } else { 'local_personal_evidence_reflection_windows_v1' }
$profileText = [System.IO.File]::ReadAllText((Join-Path $repo $profilePath), [System.Text.UTF8Encoding]::new($false))
# Profile identity is a repository semantic: E11 hashes UTF-8 content with LF
# line endings.  Never bind admission to the Windows checkout representation.
$profileBytes = [System.Text.UTF8Encoding]::new($false).GetBytes($profileText.Replace("`r`n", "`n").Replace("`r", "`n"))
$sha256 = [System.Security.Cryptography.SHA256]::Create()
try { $env:PSYCHE_OS_PERSONAL_PROFILE_DIGEST = ([System.BitConverter]::ToString($sha256.ComputeHash($profileBytes))).Replace('-', '').ToLowerInvariant() }
finally { $sha256.Dispose() }
if ($env:PSYCHE_OS_PERSONAL_BUILD_ID -notmatch '^[0-9a-f]{40}$') { throw 'Personal build identity must be an exact commit SHA.' }
& npm run sidecar:build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& npx tauri build --features personal-product --config src-tauri/tauri.personal.conf.json
exit $LASTEXITCODE
