param([string]$OutputBuildId)
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$IndexPath = Join-Path $Root 'patches\nk\PATCH_INDEX.json'
$Index = Get-Content -LiteralPath $IndexPath -Raw | ConvertFrom-Json
if (-not $OutputBuildId) { $OutputBuildId = [string]$Index.runtime_build_id }
if ($OutputBuildId -notmatch '^[a-z0-9][a-z0-9._-]{0,95}$' -or $OutputBuildId.Contains('..')) {
    throw 'INVALID_OUTPUT_BUILD_ID'
}
$Source = Join-Path $Root 'third_party\narrative-keyframing'
$Commit = (& git -C $Source rev-parse HEAD).Trim()
$Tree = (& git -C $Source rev-parse 'HEAD^{tree}').Trim()
if ($LASTEXITCODE -ne 0 -or $Commit -ne [string]$Index.source_commit -or $Tree -ne [string]$Index.source_tree) {
    throw 'NK_SOURCE_IDENTITY_MISMATCH'
}
if (& git -C $Source status --porcelain=v1) { throw 'NK_SOURCE_NOT_CLEAN' }
$PatchRel = [string]$Index.ordered_patch_files[0]
$Patch = Join-Path $Root ($PatchRel.Replace('/', '\'))
if ((Get-FileHash -LiteralPath $Patch -Algorithm SHA256).Hash -ne [string]$Index.patch_sha256[0]) {
    throw 'NK_PATCH_HASH_MISMATCH'
}
$LockRel = [string]$Index.dependency_lock
$Lock = Join-Path $Root ($LockRel.Replace('/', '\'))
if ((Get-FileHash -LiteralPath $Lock -Algorithm SHA256).Hash -ne [string]$Index.dependency_lock_sha256) {
    throw 'NK_LOCK_HASH_MISMATCH'
}
$Manifest = Join-Path $Root ([string]$Index.package_manifest.Replace('/', '\'))
if ((Get-FileHash -LiteralPath $Manifest -Algorithm SHA256).Hash -ne [string]$Index.package_manifest_sha256) {
    throw 'NK_MANIFEST_HASH_MISMATCH'
}
$PatchRoot = [IO.Path]::GetFullPath((Join-Path $Root 'runtime\patched\NK'))
$Target = [IO.Path]::GetFullPath((Join-Path $PatchRoot $OutputBuildId))
if (-not $Target.StartsWith($PatchRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'BUILD_TARGET_ESCAPES_RUNTIME_ROOT'
}
if (Test-Path -LiteralPath $Target) { throw 'BUILD_TARGET_EXISTS; choose a fresh OutputBuildId' }
$TempRoot = Join-Path $Root 'runtime\tmp'
New-Item -ItemType Directory -Force -Path $TempRoot,(Split-Path -Parent $Target) | Out-Null
$Archive = Join-Path $TempRoot ("narrative-keyframing-{0}-source.zip" -f $OutputBuildId)
if (Test-Path -LiteralPath $Archive) { throw 'ARCHIVE_TARGET_EXISTS; choose a fresh OutputBuildId' }
& git -C $Source archive --format=zip --output=$Archive $Commit
if ($LASTEXITCODE -ne 0) { throw 'NK_ARCHIVE_FAILED' }
$ArchiveHash = (Get-FileHash -LiteralPath $Archive -Algorithm SHA256).Hash
if ($ArchiveHash -ne [string]$Index.source_archive_sha256) { throw 'NK_ARCHIVE_HASH_MISMATCH' }
New-Item -ItemType Directory -Path $Target | Out-Null
Expand-Archive -LiteralPath $Archive -DestinationPath $Target
$TargetRel = $Target.Substring($Root.Length + 1).Replace('\', '/')
& git -C $Root apply --check --directory=$TargetRel $PatchRel
if ($LASTEXITCODE -ne 0) { throw 'NK_PATCH_CHECK_FAILED' }
& git -C $Root apply --directory=$TargetRel $PatchRel
if ($LASTEXITCODE -ne 0) { throw 'NK_PATCH_APPLY_FAILED' }
$AppliedLock = Join-Path $Target 'package-lock.json'
$AppliedText = [IO.File]::ReadAllText($AppliedLock).Replace("`r`n", "`n")
$AppliedBytes = [Text.UTF8Encoding]::new($false).GetBytes($AppliedText)
$AppliedHash = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($AppliedBytes))
if ($AppliedHash -ne [string]$Index.dependency_lock_sha256) {
    throw 'NK_APPLIED_LOCK_MISMATCH'
}
$AppliedManifest = Join-Path $Target 'package.json'
$AppliedManifestText = [IO.File]::ReadAllText($AppliedManifest).Replace("`r`n", "`n")
$AppliedManifestBytes = [Text.UTF8Encoding]::new($false).GetBytes($AppliedManifestText)
$AppliedManifestHash = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($AppliedManifestBytes))
if ($AppliedManifestHash -ne [string]$Index.package_manifest_sha256) {
    throw 'NK_APPLIED_MANIFEST_MISMATCH'
}
Write-Output ("BUILD_ID={0}" -f $OutputBuildId)
Write-Output ("SOURCE_COMMIT={0}" -f $Commit)
Write-Output ("SOURCE_TREE={0}" -f $Tree)
Write-Output ("ARCHIVE_SHA256={0}" -f $ArchiveHash)
Write-Output ("PATCH_SHA256={0}" -f $Index.patch_sha256[0])
Write-Output ("LOCK_SHA256={0}" -f $Index.dependency_lock_sha256)
Push-Location $Target
try {
    $env:npm_config_cache = Join-Path $Root 'runtime\cache\npm'
    npm ci --ignore-scripts
    if ($LASTEXITCODE -ne 0) { throw 'NK_NPM_CI_FAILED' }
    npm run build
    if ($LASTEXITCODE -ne 0) { throw 'NK_PRODUCTION_BUILD_FAILED' }
}
finally { Pop-Location }
