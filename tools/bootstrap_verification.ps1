[CmdletBinding()]
param(
    [switch]$Offline,
    [string]$Python313 = 'python',
    [string]$Python311,
    [string]$UvExecutable = 'uv'
)
$ErrorActionPreference = 'Stop'
$BootstrapRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
function Invoke-BootstrapCommand {
    param([string]$Program, [string[]]$CommandArguments)
    & $Program @CommandArguments
    if ($LASTEXITCODE -ne 0) { throw "BOOTSTRAP_COMMAND_FAILED:$Program`:$LASTEXITCODE" }
}
$BootstrapPins = [ordered]@{
    'claude-novel-workflow' = '97ad71fe5e5e76a82275c6c63d4add06fb60ab6e'
    'CritiCS' = 'fbf66cbc913012c6f80af1687e27f0ce350475e3'
    'narrative-keyframing' = 'b857f34b7d371ae82c30e00eb021884c14d08ae9'
}
foreach ($BootstrapComponent in $BootstrapPins.Keys) {
    $BootstrapSource = Join-Path $BootstrapRoot "third_party/$BootstrapComponent"
    $BootstrapCommit = & git -C $BootstrapSource rev-parse HEAD
    if ($LASTEXITCODE -ne 0 -or $BootstrapCommit.Trim() -ne $BootstrapPins[$BootstrapComponent]) {
        throw "BOOTSTRAP_FIXED_SOURCE_MISSING_OR_MISMATCH:$BootstrapComponent"
    }
    $BootstrapDirty = & git -C $BootstrapSource status --porcelain
    if ($LASTEXITCODE -ne 0 -or $BootstrapDirty) { throw "BOOTSTRAP_FIXED_SOURCE_DIRTY:$BootstrapComponent" }
}
$BootstrapIndex = Get-Content -LiteralPath (Join-Path $BootstrapRoot 'patches/critics/PATCH_INDEX.json') -Raw | ConvertFrom-Json
$BootstrapEnv = Join-Path $BootstrapRoot 'runtime/envs/critics-api'
foreach ($BootstrapTarget in @(
    (Join-Path $BootstrapRoot 'runtime/reference/cnw_97ad71fe5e5e'),
    (Join-Path $BootstrapRoot "runtime/patched/CritiCS/$($BootstrapIndex.runtime_build_id)"),
    $BootstrapEnv
)) {
    if (Test-Path -LiteralPath $BootstrapTarget) { throw 'BOOTSTRAP_NEW_EMPTY_CLONE_REQUIRED; preserve existing runtime' }
}
Invoke-BootstrapCommand $Python313 @('-c', 'import sys,importlib.metadata as m; assert sys.version_info[:2]==(3,13); assert m.version("httpx")=="0.28.1"; assert m.version("pytest")=="9.1.1"; print("VERIFICATION_PYTHON_DEPENDENCIES_READY")')
Invoke-BootstrapCommand $Python313 @((Join-Path $BootstrapRoot 'tools/capture_cnw_reference.py'), '--repo-root', $BootstrapRoot)
Invoke-BootstrapCommand 'pwsh' @('-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',(Join-Path $BootstrapRoot 'tools/build_critics.ps1'))
if (-not $Python311) {
    $BootstrapFindArguments = @('python','find','--no-python-downloads','3.11')
    if ($Offline) { $BootstrapFindArguments += '--offline' }
    $Python311 = & $UvExecutable @BootstrapFindArguments
    if ($LASTEXITCODE -ne 0 -or -not $Python311) { throw 'BOOTSTRAP_PYTHON311_REQUIRED' }
    $Python311 = $Python311.Trim()
}
$BootstrapUvArguments = @('venv','--no-python-downloads','--python',$Python311,$BootstrapEnv)
if ($Offline) { $BootstrapUvArguments += '--offline' }
Invoke-BootstrapCommand $UvExecutable $BootstrapUvArguments
$BootstrapInstallArguments = @('pip','install','--no-progress','--no-python-downloads','--python',
    (Join-Path $BootstrapEnv 'Scripts/python.exe'),'--index-url','https://pypi.org/simple','-r',
    (Join-Path $BootstrapRoot 'requirements/critics-api.lock'))
if ($Offline) { $BootstrapInstallArguments += '--offline' }
Invoke-BootstrapCommand $UvExecutable $BootstrapInstallArguments
Invoke-BootstrapCommand $UvExecutable @('pip','check','--offline','--python',(Join-Path $BootstrapEnv 'Scripts/python.exe'))
Invoke-BootstrapCommand 'pwsh' @('-NoLogo','-NoProfile','-NonInteractive','-File',(Join-Path $BootstrapRoot 'tools/studio.ps1'),'doctor','-AppOnly')
[ordered]@{status='VERIFICATION_BOOTSTRAP_READY';offline=[bool]$Offline;project='NOT_SELECTED';
    provider_call='none';generic_live_production='NOT_RUN';nk='NOT_BUILT_OR_STARTED';
    verification_python=$Python313;source_pins=$BootstrapPins} | ConvertTo-Json -Depth 4
