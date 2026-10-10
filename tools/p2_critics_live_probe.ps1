param([Parameter(Mandatory=$true)][string]$KeyPath)
$ErrorActionPreference = 'Stop'
$Python = Join-Path (Split-Path -Parent $PSScriptRoot) 'runtime\envs\critics-api\Scripts\python.exe'
$OldKey = [Environment]::GetEnvironmentVariable('DEEPSEEK_API_KEY','Process')
try {
    $RawKey = [IO.File]::ReadAllText((Resolve-Path -LiteralPath $KeyPath))
    if ($RawKey -match '(?im)^\s*(?:DEEPSEEK_API_KEY\s*=\s*)?["'']?(sk-[A-Za-z0-9_-]{20,})') { $env:DEEPSEEK_API_KEY = $Matches[1] }
    else { $env:DEEPSEEK_API_KEY = $RawKey.Trim().Trim('"', "'") }
    $RawKey = $null
    if (-not $env:DEEPSEEK_API_KEY -or $env:DEEPSEEK_API_KEY.Length -lt 20) { throw 'KEY_FILE_EMPTY_OR_UNRECOGNIZED' }
    & $Python (Join-Path $PSScriptRoot 'p2_critics_live_probe.py')
    if ($LASTEXITCODE -ne 0) { throw 'CRITICS_LIVE_PROBE_FAILED' }
} finally {
    if ($null -ne $OldKey) { [Environment]::SetEnvironmentVariable('DEEPSEEK_API_KEY',$OldKey,'Process') }
    else { Remove-Item Env:DEEPSEEK_API_KEY -ErrorAction SilentlyContinue }
    $RawKey = $null
}
