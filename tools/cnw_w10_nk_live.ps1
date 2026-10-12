param(
    [Parameter(Mandatory=$true)][string]$RunId,
    [Parameter(Mandatory=$true)][string]$ProjectRoot,
    [Parameter(Mandatory=$true)][string]$PayloadPath,
    [string]$KeyPath,
    [string]$W10Preflight
)
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$WorkspaceRoot = (Resolve-Path -LiteralPath (Join-Path $Root 'workspace')).Path
$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
if (-not $ProjectRoot.StartsWith($WorkspaceRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'PROJECT_ROOT_OUTSIDE_PRIVATE_WORKSPACE' }
$Index = Get-Content -LiteralPath (Join-Path $Root 'patches\nk\PATCH_INDEX.json') -Raw | ConvertFrom-Json
$Build = Join-Path $Root ("runtime\patched\NK\" + [string]$Index.runtime_build_id)
if ($RunId -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{1,95}$') { throw 'RUN_ID_INVALID' }
$Run = Join-Path $ProjectRoot ("runs\" + $RunId)
$Port = 3175
$RequestId = 'nk-' + [guid]::NewGuid().ToString('N')
$Capture = Join-Path $Run ("nk-provider-" + $RequestId + '.jsonl')
$Preload = Join-Path $Root 'tools\nk-live-fetch.cjs'
$Npm = (Get-Command npm.cmd).Source
$Python = Join-Path $Root 'runtime\envs\critics-api\Scripts\python.exe'
$EnvNames = @('DEEPSEEK_API_KEY','NODE_OPTIONS','STORYSTUDIO_NK_LIVE_CAPTURE','STORYSTUDIO_NK_LIVE_REQUEST_ID')
$OldEnv = @{}
foreach ($Name in $EnvNames) {
    $Value = [Environment]::GetEnvironmentVariable($Name, 'Process')
    if ($null -ne $Value) { $OldEnv[$Name] = $Value }
}
if (-not (Test-Path -LiteralPath $Run -PathType Container)) { throw 'LIVE_RUN_DIRECTORY_MISSING' }
$RunResolved = (Resolve-Path -LiteralPath $Run).Path
$RunsResolved = (Resolve-Path -LiteralPath (Join-Path $ProjectRoot 'runs')).Path
if (-not $RunResolved.StartsWith($RunsResolved + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'LIVE_RUN_PATH_UNSAFE' }
$StatePath = Join-Path $Run 'run_state.json'
if (-not (Test-Path -LiteralPath $StatePath -PathType Leaf)) { throw 'LIVE_RUN_STATE_MISSING' }
$State = Get-Content -LiteralPath $StatePath -Raw | ConvertFrom-Json
if ($State.run_id -ne $RunId -or $State.mode -ne 'live' -or $State.fixture_only -ne $false -or
    $State.w10_contract_preflight.status -ne 'ACCEPTED' -or $State.w10_contract_preflight.scope -ne 'W10_SINGLE_SCENE' -or
    $State.stages.pov.status -ne 'READY_FOR_EXECUTION' -or $State.stages.plot.status -ne 'ACCEPTED' -or
    $State.stages.cards.status -ne 'ACCEPTED') { throw 'W10_NK_STAGE_NOT_AUTHORIZED_OR_READY' }
$PreflightArgs = @((Join-Path $Root 'tools\cnw_live_executor.py'),'--run-dir',$Run,'--verify-preflight-only')
if ($W10Preflight) { $PreflightArgs += @('--preflight',(Resolve-Path -LiteralPath $W10Preflight).Path) }
& $Python @PreflightArgs
if ($LASTEXITCODE -ne 0) { throw 'W10_NK_TRUSTED_PREFLIGHT_FAILED' }
if (Test-Path -LiteralPath $PayloadPath -PathType Leaf) { $PayloadResolved = (Resolve-Path -LiteralPath $PayloadPath).Path }
else { $PayloadResolved = (Resolve-Path -LiteralPath (Join-Path $Run $PayloadPath)).Path }
if (-not $PayloadResolved.StartsWith($RunResolved + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'NK_PAYLOAD_PATH_UNSAFE' }
if ((Get-Item -LiteralPath $PayloadResolved).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'NK_PAYLOAD_PATH_UNSAFE' }
try { $Body = Get-Content -LiteralPath $PayloadResolved -Raw | ConvertFrom-Json -AsHashtable }
catch { throw 'NK_PAYLOAD_JSON_INVALID' }
if (-not $Body.perspectives -or $Body.perspectives.Count -ne 1 -or $Body.perspectives[0].narrator -ne '君天离') { throw 'NK_PAYLOAD_SCOPE_INVALID' }
if (Test-Path -LiteralPath $Capture) { throw 'NK_CAPTURE_ALREADY_EXISTS' }
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) { throw "PORT_IN_USE:$Port" }

$Server = $null
try {
    if (-not $env:DEEPSEEK_API_KEY -and $KeyPath) {
        $RawKey = [IO.File]::ReadAllText((Resolve-Path -LiteralPath $KeyPath))
        if ($RawKey -match '(?im)^\s*(?:DEEPSEEK_API_KEY\s*=\s*)?["'']?(sk-[A-Za-z0-9_-]{20,})') { $env:DEEPSEEK_API_KEY = $Matches[1] }
        else { $env:DEEPSEEK_API_KEY = $RawKey.Trim().Trim('"', "'") }
        $RawKey = $null
    }
    if (-not $env:DEEPSEEK_API_KEY) { throw 'DEEPSEEK_API_KEY_REQUIRED' }
    & $Python (Join-Path $Root 'tools\p2_cost_guard.py') reserve --request-id $RequestId --run-id $RunId --purpose 'single short NK generate-perspective live call' --input-token-cap 10000 --output-token-cap 512
    if ($LASTEXITCODE -ne 0) { throw 'NK_COST_RESERVATION_FAILED' }
    $env:STORYSTUDIO_NK_LIVE_CAPTURE = $Capture
    $env:STORYSTUDIO_NK_LIVE_REQUEST_ID = $RequestId
    $PreloadNodePath = $Preload.Replace('\','/')
    $env:NODE_OPTIONS = "--require=$PreloadNodePath"
    $Server = Start-Process -FilePath $Npm -ArgumentList @('start','--','--port',"$Port") -WorkingDirectory $Build -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $Run 'nk-server.stdout.log') -RedirectStandardError (Join-Path $Run 'nk-server.stderr.log')
    $Ready = $false
    for ($i = 0; $i -lt 60; $i++) {
        try { $null = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/" -TimeoutSec 1; $Ready = $true; break }
        catch { Start-Sleep -Milliseconds 250 }
    }
    if (-not $Ready) {
        if (-not (Test-Path -LiteralPath $Capture)) {
            & $Python (Join-Path $Root 'tools\p2_cost_guard.py') settle --request-id $RequestId --input-tokens 0 --output-tokens 0
        }
        throw 'NK_LIVE_SERVER_DID_NOT_START'
    }
    $Listener = Get-NetTCPConnection -LocalPort $Port -State Listen
    if ($Listener.LocalAddress -ne '127.0.0.1') { throw 'NK_LIVE_SERVER_NOT_LOOPBACK' }

    $RequestPath = Join-Path $Run ("nk-http-request-" + $RequestId + '.json')
    $HttpResponsePath = Join-Path $Run ("nk-http-response-" + $RequestId + '.json')
    $BodyJson = $Body | ConvertTo-Json -Depth 30 -Compress
    [IO.File]::WriteAllText($RequestPath, $BodyJson, [Text.UTF8Encoding]::new($false))
    $InputSha = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($BodyJson))).ToLowerInvariant()
    $HttpResponse = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/api/generate-perspective" -Method Post -ContentType 'application/json' -Body $BodyJson -SkipHttpErrorCheck -TimeoutSec 180
    [ordered]@{ status_code = $HttpResponse.StatusCode; content = ($HttpResponse.Content | ConvertFrom-Json) } |
        ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $HttpResponsePath -Encoding utf8NoBOM
    & taskkill.exe /PID $Server.Id /T /F | Out-Null
    $Server = $null

    if (-not (Test-Path -LiteralPath $Capture)) { throw 'NK_PROVIDER_CAPTURE_MISSING' }
    $Record = Get-Content -LiteralPath $Capture | ForEach-Object { $_ | ConvertFrom-Json } | Select-Object -Last 1
    if ($Record.request_id -ne $RequestId -or $Record.host -ne 'https://api.deepseek.com' -or $Record.status -ne 200) { throw 'NK_PROVIDER_CALL_NOT_ACCEPTED' }
    $ProviderResponse = $Record.response
    $Choice = $ProviderResponse.choices | Select-Object -First 1
    $Usage = $ProviderResponse.usage
    if ($ProviderResponse.model -ne 'deepseek-flash' -or $Choice.finish_reason -ne 'stop') { throw 'NK_PROVIDER_RESULT_METADATA_INVALID' }
    if ($null -eq $Usage.prompt_tokens -or $null -eq $Usage.completion_tokens) { throw 'NK_PROVIDER_USAGE_MISSING' }
    $SettleArgs = @('settle','--request-id',$RequestId,'--provider-request-id',[string]$ProviderResponse.id,'--returned-model',[string]$ProviderResponse.model,'--finish-reason',[string]$Choice.finish_reason)
    if ($null -ne $Usage.prompt_tokens -and $null -ne $Usage.completion_tokens) {
        $SettleArgs += @('--input-tokens',"$($Usage.prompt_tokens)",'--output-tokens',"$($Usage.completion_tokens)")
    }
    $SettlementText = & $Python (Join-Path $Root 'tools\p2_cost_guard.py') @SettleArgs
    if ($LASTEXITCODE -ne 0) { throw 'NK_COST_SETTLEMENT_FAILED' }
    $Settlement = $SettlementText | ConvertFrom-Json
    if ($Settlement.status -eq 'SETTLED_OVER_BUDGET') {
        & $Python (Join-Path $Root 'tools\cnw_live_executor.py') --run-dir $Run --record-nk-budget-failure $RequestId
        if ($LASTEXITCODE -ne 0) { throw 'NK_OVER_BUDGET_ATTEMPT_RECORD_FAILED' }
        throw 'NK_LIVE_COST_BUDGET_EXCEEDED'
    }
    if ($Settlement.status -ne 'SETTLED') { throw 'NK_COST_SETTLEMENT_NOT_ACCEPTED' }
    if ($HttpResponse.StatusCode -ne 200) { throw "NK_HTTP_STATUS:$($HttpResponse.StatusCode)" }
    $Result = $HttpResponse.Content | ConvertFrom-Json
    if ($Result.perspectives.Count -ne 1 -or -not $Result.perspectives[0].reflection) { throw 'NK_LIVE_ZOD_RESULT_INVALID' }
    $RawResponsePath = Join-Path $Run ("artifacts\live\" + $RequestId + "\response.json")
    $RawResponseParent = Split-Path -Parent $RawResponsePath
    New-Item -ItemType Directory -Path $RawResponseParent -Force | Out-Null
    [ordered]@{ request_id = $RequestId; host = $Record.host; path = $Record.path; status = $Record.status; requested_model = $Record.requested_model; response = $ProviderResponse } |
        ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $RawResponsePath -Encoding utf8NoBOM
    $RawBytes = [IO.File]::ReadAllBytes($RawResponsePath)
    $RawSha = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($RawBytes)).ToLowerInvariant()
    $OutputSha = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes([string]$Choice.message.content))).ToLowerInvariant()
    $Ledger = Get-Content -LiteralPath (Join-Path $Root 'runtime\private\p2-cost-ledger.json') -Raw | ConvertFrom-Json
    $LedgerRow = @($Ledger.requests | Where-Object { $_.request_id -eq $RequestId })
    if ($LedgerRow.Count -ne 1 -or $LedgerRow[0].status -ne 'SETTLED' -or $Usage.prompt_tokens -gt 10000 -or $Usage.completion_tokens -gt 512) { throw 'NK_COST_LEDGER_ROW_INVALID' }
    $Receipt = [ordered]@{
        stage = 'pov'
        request_id = $RequestId
        provider_request_id = [string]$ProviderResponse.id
        model = [string]$ProviderResponse.model
        status = 'SUCCEEDED'
        http_status = [int]$HttpResponse.StatusCode
        finish_reason = [string]$Choice.finish_reason
        usage = @{ prompt_tokens = [int]$Usage.prompt_tokens; completion_tokens = [int]$Usage.completion_tokens }
        input_payload_path = [IO.Path]::GetRelativePath($RunResolved, $RequestPath).Replace('\','/')
        input_sha256 = $InputSha
        output_sha256 = $OutputSha
        raw_response_path = [IO.Path]::GetRelativePath($RunResolved, $RawResponsePath).Replace('\','/')
        raw_response_sha256 = $RawSha
        cost_cny = [double]$LedgerRow[0].estimated_actual_cny
        ledger_settlement = @{ status = 'SETTLED'; request_id = $RequestId }
        mode = 'LIVE'
        fixture_only = $false
    }
    $ReceiptPath = Join-Path $Run 'artifacts\live\pov-receipt.json'
    $Receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $ReceiptPath -Encoding utf8NoBOM
    $BoundResult = & $Python (Join-Path $Root 'tools\cnw_live_executor.py') --run-dir $Run --bind-nk-receipt 'artifacts/live/pov-receipt.json'
    if ($LASTEXITCODE -ne 0) { throw 'NK_RECEIPT_BINDING_FAILED' }
    [ordered]@{
        status = 'SUCCEEDED'
        request_id = $RequestId
        requested_model = $Record.requested_model
        returned_model = $ProviderResponse.model
        provider_request_id = $ProviderResponse.id
        finish_reason = $Choice.finish_reason
        input_tokens = $Usage.prompt_tokens
        output_tokens = $Usage.completion_tokens
        nk_http_status = $HttpResponse.StatusCode
        validated_perspective_count = $Result.perspectives.Count
        receipt_path = [IO.Path]::GetRelativePath($RunResolved, $ReceiptPath).Replace('\','/')
        bound_stage_status = ($BoundResult | ConvertFrom-Json).status
    } | ConvertTo-Json -Depth 6
}
finally {
    if ($Server -and -not $Server.HasExited) { & taskkill.exe /PID $Server.Id /T /F | Out-Null }
    foreach ($Name in $EnvNames) {
        if ($Name -eq 'DEEPSEEK_API_KEY') { $env:DEEPSEEK_API_KEY = $null }
        if ($OldEnv.ContainsKey($Name)) { [Environment]::SetEnvironmentVariable($Name,$OldEnv[$Name],'Process') }
        else { Remove-Item "Env:$Name" -ErrorAction SilentlyContinue }
    }
}
