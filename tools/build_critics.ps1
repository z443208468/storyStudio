param(
    [string]$OutputBuildId
)
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$IndexPath = Join-Path $Root 'patches\critics\PATCH_INDEX.json'
$Index = Get-Content -LiteralPath $IndexPath -Raw | ConvertFrom-Json
if (-not $OutputBuildId) { $OutputBuildId = $Index.runtime_build_id }
if ($OutputBuildId -notmatch '^[a-z0-9][a-z0-9._-]{0,95}$' -or $OutputBuildId -in @('.', '..') -or $OutputBuildId.Contains('..')) {
    throw 'INVALID_OUTPUT_BUILD_ID'
}
$Source = Join-Path $Root 'third_party\CritiCS'
$ExpectedCommit = [string]$Index.source_commit
$Commit = (& git -C $Source rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $Commit -ne $ExpectedCommit) { throw 'CRITICS_SOURCE_COMMIT_MISMATCH' }
$Dirty = & git -C $Source status --porcelain=v1
if ($LASTEXITCODE -ne 0 -or $Dirty) { throw 'CRITICS_SOURCE_NOT_CLEAN' }
$PatchRel = [string]$Index.ordered_patch_files[0]
$Patch = Join-Path $Root ($PatchRel.Replace('/', '\'))
$PatchHash = (Get-FileHash -LiteralPath $Patch -Algorithm SHA256).Hash
if ($PatchHash -ne [string]$Index.patch_sha256[0]) { throw 'CRITICS_PATCH_HASH_MISMATCH' }
$Lock = Join-Path $Root ([string]$Index.dependency_lock.Replace('/', '\'))
if ((Get-FileHash -LiteralPath $Lock -Algorithm SHA256).Hash -ne [string]$Index.dependency_lock_sha256) { throw 'CRITICS_LOCK_HASH_MISMATCH' }
$PatchRoot = [IO.Path]::GetFullPath((Join-Path $Root 'runtime\patched\CritiCS'))
$Target = [IO.Path]::GetFullPath((Join-Path $PatchRoot $OutputBuildId))
if (-not $Target.StartsWith($PatchRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'BUILD_TARGET_ESCAPES_RUNTIME_ROOT' }
if (Test-Path -LiteralPath $Target) { throw 'BUILD_TARGET_EXISTS; choose a fresh OutputBuildId to preserve prior evidence' }
$TempRoot = Join-Path $Root 'runtime\tmp'
New-Item -ItemType Directory -Force -Path $TempRoot,(Split-Path -Parent $Target) | Out-Null
$Archive = Join-Path $TempRoot ("CritiCS-{0}-source.zip" -f $OutputBuildId)
if (Test-Path -LiteralPath $Archive) { throw 'ARCHIVE_TARGET_EXISTS; preserve it and choose a fresh OutputBuildId' }
& git -C $Source archive --format=zip --output=$Archive $ExpectedCommit
if ($LASTEXITCODE -ne 0) { throw 'GIT_ARCHIVE_FAILED' }
$ArchiveHash = (Get-FileHash -LiteralPath $Archive -Algorithm SHA256).Hash
New-Item -ItemType Directory -Path $Target | Out-Null
Expand-Archive -LiteralPath $Archive -DestinationPath $Target
$TargetRel = $Target.Substring($Root.Length + 1).Replace('\', '/')
& git -C $Root apply --check --directory=$TargetRel $PatchRel
if ($LASTEXITCODE -ne 0) { throw 'CRITICS_PATCH_CHECK_FAILED' }
& git -C $Root apply --directory=$TargetRel $PatchRel
if ($LASTEXITCODE -ne 0) { throw 'CRITICS_PATCH_APPLY_FAILED' }
Write-Output ("BUILD_ID={0}" -f $OutputBuildId)
Write-Output ("SOURCE_COMMIT={0}" -f $Commit)
Write-Output ("ARCHIVE_SHA256={0}" -f $ArchiveHash)
Write-Output ("PATCH_SHA256={0}" -f $PatchHash)
Write-Output ("LOCK_SHA256={0}" -f $Index.dependency_lock_sha256)
