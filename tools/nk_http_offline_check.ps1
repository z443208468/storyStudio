$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$Index = Get-Content -LiteralPath (Join-Path $Root 'patches\nk\PATCH_INDEX.json') -Raw | ConvertFrom-Json
$Build = Join-Path $Root ("runtime\patched\NK\" + [string]$Index.runtime_build_id)
$RouteFiles = @(Get-ChildItem -LiteralPath (Join-Path $Build 'app\api') -Recurse -File | Where-Object { $_.Name -match '^route\.tsx?$' })
if ($RouteFiles.Count -ne 8) { throw "GENERATION_ROUTE_COUNT_CHANGED:$($RouteFiles.Count)" }
foreach ($RouteFile in $RouteFiles) {
    if ((Get-Content -LiteralPath $RouteFile.FullName -Raw) -notmatch 'reasoningEffort:\s*["'']none["'']') {
        throw "THINKING_MODE_NOT_DISABLED:$($RouteFile.FullName)"
    }
}
$Port = 3173
$NoKeyPort = 3174
$Capture = Join-Path $Root 'runtime\tmp\nk-http-offline-capture.jsonl'
$Preload = Join-Path $Root 'tools\nk-offline-fetch.cjs'
$Fixture = Join-Path $Root 'tools\fixtures\nk-perspective-response.json'
$EnvironmentNames = @(
    'DEEPSEEK_API_KEY', 'STORYSTUDIO_NK_OFFLINE_TEST', 'STORYSTUDIO_NK_OFFLINE_CAPTURE',
    'STORYSTUDIO_NK_OFFLINE_FIXTURE', 'NODE_OPTIONS'
)
$OriginalEnvironment = @{}
foreach ($Name in $EnvironmentNames) {
    $Value = [Environment]::GetEnvironmentVariable($Name, 'Process')
    if ($null -ne $Value) { $OriginalEnvironment[$Name] = $Value }
}
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Capture) | Out-Null
Set-Content -LiteralPath $Capture -Value '' -Encoding utf8NoBOM
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
    throw "PORT_IN_USE:$Port"
}

$env:DEEPSEEK_API_KEY = 'offline-test-only-never-sent'
$env:STORYSTUDIO_NK_OFFLINE_TEST = '1'
$env:STORYSTUDIO_NK_OFFLINE_CAPTURE = $Capture
$env:STORYSTUDIO_NK_OFFLINE_FIXTURE = $Fixture
$env:NODE_OPTIONS = "--require $Preload"
$Server = $null
$NoKeyServer = $null
try {
    $Npm = (Get-Command npm.cmd).Source
    $Server = Start-Process -FilePath $Npm -ArgumentList @(
        'start', '--', '--port', "$Port"
    ) -WorkingDirectory $Build -WindowStyle Hidden -PassThru

    $Ready = $false
    for ($i = 0; $i -lt 40; $i++) {
        try {
            $null = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/" -TimeoutSec 1
            $Ready = $true
            break
        } catch { Start-Sleep -Milliseconds 250 }
    }
    if (-not $Ready) { throw 'NK_SERVER_DID_NOT_START' }

    $Url = "http://127.0.0.1:$Port/api/generate-perspective"
    $Bad = Invoke-WebRequest -Uri $Url -Method Post -ContentType 'application/json' -Body '{}' -SkipHttpErrorCheck
    if ($Bad.StatusCode -ne 400) { throw "BAD_INPUT_STATUS:$($Bad.StatusCode)" }
    $Task = @{ id = 'offline-task'; narrator = 'Test narrator'; eventLabel = 'Repair lantern'; eventObjective = 'Make a choice'; characterSnapshots = @() }
    $Body = @{ eventSequence = @(); perspectives = @($Task) }
    $Good = Invoke-WebRequest -Uri $Url -Method Post -ContentType 'application/json' -Body ($Body | ConvertTo-Json -Depth 10) -SkipHttpErrorCheck
    if ($Good.StatusCode -ne 200) { throw "GOOD_INPUT_STATUS:$($Good.StatusCode)" }
    $GoodObject = $Good.Content | ConvertFrom-Json
    if ($GoodObject.perspectives.Count -ne 1 -or -not $GoodObject.perspectives[0].reflection) { throw 'GOOD_OUTPUT_CONTRACT_FAILED' }

    $TooFewBody = @{ eventSequence = @(); perspectives = @($Task, ($Task.Clone())) ; customPrompt = 'OFFLINE_CASE_TOO_FEW' }
    $TooFew = Invoke-WebRequest -Uri $Url -Method Post -ContentType 'application/json' -Body ($TooFewBody | ConvertTo-Json -Depth 10) -SkipHttpErrorCheck
    if ($TooFew.StatusCode -ne 502) { throw "TOO_FEW_STATUS:$($TooFew.StatusCode)" }

    $FailureStatuses = @{}
    foreach ($Case in @('EMPTY', 'MALFORMED', 'TRUNCATED')) {
        $CaseBody = @{ eventSequence = @(); perspectives = @($Task); customPrompt = "OFFLINE_CASE_$Case" }
        $Response = Invoke-WebRequest -Uri $Url -Method Post -ContentType 'application/json' -Body ($CaseBody | ConvertTo-Json -Depth 10) -SkipHttpErrorCheck
        if ($Response.StatusCode -lt 400) { throw "INVALID_MODEL_OUTPUT_ACCEPTED:$Case" }
        $FailureStatuses[$Case] = $Response.StatusCode
    }

    $Captured = Get-Content -LiteralPath $Capture | ForEach-Object { $_ | ConvertFrom-Json }
    foreach ($Case in @('GOOD', 'TOO_FEW', 'EMPTY', 'MALFORMED', 'TRUNCATED')) {
        $Call = $Captured | Where-Object case -eq $Case | Select-Object -First 1
        if (-not $Call -or -not $Call.config_valid -or $Call.model -ne 'deepseek-flash' -or $Call.response_format -ne 'json_object') {
            throw "CAPTURED_PROVIDER_CONFIG_INVALID:$Case"
        }
    }
    $Listener = Get-NetTCPConnection -LocalPort $Port -State Listen
    if ($Listener.LocalAddress -ne '127.0.0.1') { throw "NON_LOOPBACK_LISTENER:$($Listener.LocalAddress -join ',')" }
    & taskkill.exe /PID $Server.Id /T /F | Out-Null
    $Server = $null
    foreach ($Name in $EnvironmentNames) { Remove-Item "Env:$Name" -ErrorAction SilentlyContinue }
    if (Get-NetTCPConnection -LocalPort $NoKeyPort -State Listen -ErrorAction SilentlyContinue) {
        throw "PORT_IN_USE:$NoKeyPort"
    }
    $NoKeyServer = Start-Process -FilePath $Npm -ArgumentList @(
        'start', '--', '--port', "$NoKeyPort"
    ) -WorkingDirectory $Build -WindowStyle Hidden -PassThru
    $NoKeyReady = $false
    for ($i = 0; $i -lt 40; $i++) {
        try {
            $null = Invoke-WebRequest -Uri "http://127.0.0.1:$NoKeyPort/" -TimeoutSec 1
            $NoKeyReady = $true
            break
        } catch { Start-Sleep -Milliseconds 250 }
    }
    if (-not $NoKeyReady) { throw 'NK_NO_KEY_SERVER_DID_NOT_START' }
    $Routes = @(
        '/api/extract-characters', '/api/extract-evidence', '/api/generate-narrative',
        '/api/generate-perspective', '/api/generate-traits/physiology',
        '/api/generate-traits/psychology', '/api/generate-traits/sociology',
        '/api/interpolate-character'
    )
    foreach ($Route in $Routes) {
        $Response = Invoke-WebRequest -Uri "http://127.0.0.1:$NoKeyPort$Route" -Method Post -ContentType 'application/json' -Body '{}' -SkipHttpErrorCheck
        if ($Response.StatusCode -ne 401) { throw "NO_KEY_ROUTE_STATUS:${Route}:$($Response.StatusCode)" }
    }
    $NoKeyListener = Get-NetTCPConnection -LocalPort $NoKeyPort -State Listen
    if ($NoKeyListener.LocalAddress -ne '127.0.0.1') { throw "NON_LOOPBACK_NO_KEY_LISTENER:$($NoKeyListener.LocalAddress -join ',')" }
    $Report = [ordered]@{
        status = 'PASS'
        bad_input_status = $Bad.StatusCode
        good_input_status = $Good.StatusCode
        too_few_status = $TooFew.StatusCode
        malformed_statuses = $FailureStatuses
        listener = '127.0.0.1'
        no_key_routes = $Routes.Count
        reasoning_disabled_routes = $RouteFiles.Count
        no_key_status = 401
        captured_calls = $Captured.Count
        external_provider_calls = 0
        provider_requests = @($Captured | Select-Object host, model, response_format, reasoning_effort, max_output_tokens, case, config_valid, prompt_sha256, prompt_length)
    }
    $ReportPath = Join-Path $Root 'evidence\nk\http-offline-check.json'
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $ReportPath) | Out-Null
    $ReportJson = $Report | ConvertTo-Json -Depth 6
    Set-Content -LiteralPath $ReportPath -Value $ReportJson -Encoding utf8NoBOM
    $ReportJson
}
finally {
    if ($Server -and -not $Server.HasExited) { Stop-Process -Id $Server.Id -Force }
    if ($NoKeyServer -and -not $NoKeyServer.HasExited) { Stop-Process -Id $NoKeyServer.Id -Force }
    foreach ($CandidatePort in @($Port, $NoKeyPort)) {
        foreach ($Connection in (Get-NetTCPConnection -LocalPort $CandidatePort -State Listen -ErrorAction SilentlyContinue)) {
            & taskkill.exe /PID $Connection.OwningProcess /T /F | Out-Null
        }
    }
    foreach ($Name in $EnvironmentNames) {
        if ($OriginalEnvironment.ContainsKey($Name)) {
            [Environment]::SetEnvironmentVariable($Name, $OriginalEnvironment[$Name], 'Process')
        } else {
            Remove-Item "Env:$Name" -ErrorAction SilentlyContinue
        }
    }
}
