$ErrorActionPreference = 'Stop'
$TaskRoot = $PSScriptRoot
$RepositoryRoot = 'D:\CangqiStudio\StoryStudio'
$Destination = Join-Path $TaskRoot 'nk_legacy_cap_parse_20261014.json'
if (Test-Path -LiteralPath $Destination) { throw 'EVIDENCE_ALREADY_EXISTS' }
$Records = @()
foreach ($Name in @('cnw_w10_nk_live.ps1','p2_06_nk_live_probe.ps1','p2_nk_live_probe.ps1')) {
    $CurrentPath = Join-Path $RepositoryRoot ('tools\' + $Name)
    $OriginalPath = Join-Path $TaskRoot ('nk_text_boundary_preimages_20261014\tools\' + $Name)
    $OriginalRaw = [IO.File]::ReadAllBytes($OriginalPath)
    $CurrentRaw = [IO.File]::ReadAllBytes($CurrentPath)
    $OriginalTokens = $null
    $OriginalErrors = $null
    $OriginalAst = [Management.Automation.Language.Parser]::ParseInput([Text.Encoding]::UTF8.GetString($OriginalRaw),[ref]$OriginalTokens,[ref]$OriginalErrors)
    $CurrentTokens = $null
    $CurrentErrors = $null
    $CurrentAst = [Management.Automation.Language.Parser]::ParseFile($CurrentPath,[ref]$CurrentTokens,[ref]$CurrentErrors)
    if ($OriginalErrors.Count -ne 0 -or $CurrentErrors.Count -ne 0) { throw ('SOURCE_PARSE_ERROR:' + $Name) }
    $CurrentSha = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($CurrentRaw)).ToLowerInvariant()
    $AfterSha = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([IO.File]::ReadAllBytes($CurrentPath))).ToLowerInvariant()
    if ($CurrentSha -ne $AfterSha) { throw ('SOURCE_CHANGED_DURING_PARSE:' + $Name) }
    $Records += [ordered]@{
        path = ('tools/' + $Name)
        original_sha256 = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($OriginalRaw)).ToLowerInvariant()
        current_sha256 = $CurrentSha
        original_parse_errors = $OriginalErrors.Count
        current_parse_errors = $CurrentErrors.Count
        original_tokens = $OriginalTokens.Count
        current_tokens = $CurrentTokens.Count
        source_unchanged = $true
    }
}
$Report = [ordered]@{
    status = 'ACTUAL_PARSE_ONLY_NOT_SCRIPT_EXECUTION_OR_ACCEPTANCE'
    powershell_version = $PSVersionTable.PSVersion.ToString()
    project_scripts_executed = 0
    production_api_calls = 0
    fee_reservations = 0
    records = $Records
}
[IO.File]::WriteAllText($Destination,($Report | ConvertTo-Json -Depth 10),[Text.UTF8Encoding]::new($false))
[ordered]@{ destination = $Destination; sha256 = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([IO.File]::ReadAllBytes($Destination))).ToLowerInvariant(); records = $Records.Count } | ConvertTo-Json -Compress
