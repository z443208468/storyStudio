$ErrorActionPreference = 'Stop'
$sourcePath = 'D:\CangqiStudio\StoryStudio\tools\studio.ps1'
$resultPath = 'D:\CangqiStudio\StoryStudio_R5_Atom07_Current_20261013\studio_ps1_lf_parser_equivalence_20261014.json'
if (Test-Path -LiteralPath $resultPath) { throw 'EVIDENCE_TARGET_ALREADY_EXISTS' }
$sourceBytes = [System.IO.File]::ReadAllBytes($sourcePath)
$sourceText = [System.Text.Encoding]::UTF8.GetString($sourceBytes)
$lfText = $sourceText.Replace("`r`n", "`n")
$sourceTokens = $null
$sourceErrors = $null
$lfTokens = $null
$lfErrors = $null
$sourceAst = [System.Management.Automation.Language.Parser]::ParseInput($sourceText, [ref]$sourceTokens, [ref]$sourceErrors)
$lfAst = [System.Management.Automation.Language.Parser]::ParseInput($lfText, [ref]$lfTokens, [ref]$lfErrors)
if (@($sourceErrors).Count -ne 0 -or @($lfErrors).Count -ne 0) { throw 'POWERSHELL_PARSE_ERRORS' }
$sourceTokenRecords = @($sourceTokens | ForEach-Object { [ordered]@{ kind = $_.Kind.ToString(); flags = $_.TokenFlags.ToString(); text = $_.Text.Replace("`r`n", "`n") } })
$lfTokenRecords = @($lfTokens | ForEach-Object { [ordered]@{ kind = $_.Kind.ToString(); flags = $_.TokenFlags.ToString(); text = $_.Text } })
$sourceAstRecords = @($sourceAst.FindAll({ param($node) $true }, $true) | ForEach-Object { [ordered]@{ type = $_.GetType().FullName; text = $_.Extent.Text.Replace("`r`n", "`n") } })
$lfAstRecords = @($lfAst.FindAll({ param($node) $true }, $true) | ForEach-Object { [ordered]@{ type = $_.GetType().FullName; text = $_.Extent.Text } })
$tokensEqual = (ConvertTo-Json -InputObject $sourceTokenRecords -Depth 10 -Compress) -ceq (ConvertTo-Json -InputObject $lfTokenRecords -Depth 10 -Compress)
$astEqual = (ConvertTo-Json -InputObject $sourceAstRecords -Depth 10 -Compress) -ceq (ConvertTo-Json -InputObject $lfAstRecords -Depth 10 -Compress)
function Get-ByteSha([byte[]] $bytes) { [Convert]::ToHexString([System.Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant() }
$afterBytes = [System.IO.File]::ReadAllBytes($sourcePath)
$unchanged = (Get-ByteSha $sourceBytes) -ceq (Get-ByteSha $afterBytes)
$report = [ordered]@{ status = 'READ_ONLY_PARSER_EQUIVALENCE_NOT_EXECUTION_OR_ACCEPTANCE'; path = 'tools/studio.ps1'; powershell_version = $PSVersionTable.PSVersion.ToString(); original_sha256 = Get-ByteSha $sourceBytes; lf_sha256 = Get-ByteSha ([System.Text.Encoding]::UTF8.GetBytes($lfText)); source_parse_error_count = @($sourceErrors).Count; lf_parse_error_count = @($lfErrors).Count; tokens_equal = $tokensEqual; ast_equal = $astEqual; token_count = $sourceTokenRecords.Count; ast_node_count = $sourceAstRecords.Count; source_unchanged = $unchanged; script_executed = $false }
[System.IO.File]::WriteAllText($resultPath, (ConvertTo-Json -InputObject $report -Depth 10), [System.Text.UTF8Encoding]::new($false))
ConvertTo-Json -InputObject $report -Depth 10
if (-not $tokensEqual -or -not $astEqual -or -not $unchanged) { throw 'POWERSHELL_LF_PARSER_NOT_EQUIVALENT' }
