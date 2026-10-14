param([string]$KeyPath)
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$Index = Get-Content -LiteralPath (Join-Path $Root 'patches\nk\PATCH_INDEX.json') -Raw | ConvertFrom-Json
$Build = Join-Path $Root ("runtime\patched\NK\" + [string]$Index.runtime_build_id)
$RunId = 'p2-04-live-20261010'
$Run = Join-Path $Root ("runs\" + $RunId)
$Port = 3175
$RequestId = 'nk-' + [guid]::NewGuid().ToString('N')
$Capture = Join-Path $Run ("nk-provider-" + $RequestId + '.jsonl')
$Preload = Join-Path $Root 'tools\nk-live-fetch.cjs'
$Npm = (Get-Command npm.cmd).Source
$Python = Join-Path $Root 'runtime\envs\critics-api\Scripts\python.exe'
$EnvNames = @('DEEPSEEK_API_KEY','NODE_OPTIONS','STORYSTUDIO_NK_LIVE_CAPTURE','STORYSTUDIO_NK_LIVE_REQUEST_ID','STORYSTUDIO_NK_MAX_INPUT_TOKENS')
$OldEnv = @{}
foreach ($Name in $EnvNames) {
    $Value = [Environment]::GetEnvironmentVariable($Name, 'Process')
    if ($null -ne $Value) { $OldEnv[$Name] = $Value }
}
if (-not $env:DEEPSEEK_API_KEY -and $KeyPath) {
    $RawKey = [IO.File]::ReadAllText((Resolve-Path -LiteralPath $KeyPath))
    if ($RawKey -match '(?im)^\s*(?:DEEPSEEK_API_KEY\s*=\s*)?["'']?(sk-[A-Za-z0-9_-]{20,})') { $env:DEEPSEEK_API_KEY = $Matches[1] }
    else { $env:DEEPSEEK_API_KEY = $RawKey.Trim().Trim('"', "'") }
    $RawKey = $null
}
if (-not $env:DEEPSEEK_API_KEY) { throw 'DEEPSEEK_API_KEY_REQUIRED' }
if (-not (Test-Path -LiteralPath $Run)) { throw 'LIVE_RUN_DIRECTORY_MISSING' }
if (Test-Path -LiteralPath $Capture) { throw 'NK_CAPTURE_ALREADY_EXISTS' }
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) { throw "PORT_IN_USE:$Port" }

$Server = $null
try {
    & $Python (Join-Path $Root 'tools\p2_cost_guard.py') reserve --request-id $RequestId --run-id $RunId --purpose 'single short NK generate-perspective live call' --input-token-cap 10000 --output-token-cap 384000
    if ($LASTEXITCODE -ne 0) { throw 'NK_COST_RESERVATION_FAILED' }
    $env:STORYSTUDIO_NK_LIVE_CAPTURE = $Capture
    $env:STORYSTUDIO_NK_LIVE_REQUEST_ID = $RequestId
    $env:STORYSTUDIO_NK_MAX_INPUT_TOKENS = '10000'
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

    $Task = @{
        id = 'p2-live-perspective'
        narrator = '测试叙述者'
        eventLabel = '灯笼熄灭'
        eventObjective = '一名旅人发现纸灯笼熄灭，描述这一瞬间可见的视角反应。'
        characterSnapshots = @()
    }
    $Body = @{
        eventSequence = @()
        perspectives = @($Task)
        customPrompt = '只写一条简短、具体的视角反思，不超过两句。'
    }
    $RequestPath = Join-Path $Run ("nk-http-request-" + $RequestId + '.json')
    $HttpResponsePath = Join-Path $Run ("nk-http-response-" + $RequestId + '.json')
    $BodyJson = $Body | ConvertTo-Json -Depth 10
    Set-Content -LiteralPath $RequestPath -Value $BodyJson -Encoding utf8NoBOM
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
    & $Python (Join-Path $Root 'tools\p2_cost_guard.py') @SettleArgs
    if ($LASTEXITCODE -ne 0) { throw 'NK_COST_SETTLEMENT_FAILED' }
    if ($HttpResponse.StatusCode -ne 200) { throw "NK_HTTP_STATUS:$($HttpResponse.StatusCode)" }
    $Result = $HttpResponse.Content | ConvertFrom-Json
    if ($Result.perspectives.Count -ne 1 -or -not $Result.perspectives[0].reflection) { throw 'NK_LIVE_ZOD_RESULT_INVALID' }
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
        evidence = @($RequestPath,$HttpResponsePath,$Capture)
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
