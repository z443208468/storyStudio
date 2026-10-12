[CmdletBinding()]
param(
    [Parameter(Position=0,Mandatory=$true)]
    [ValidateSet('doctor','setup','prepare','import-source','source-list','project-init','project-import','project-contract','project-incremental','canon-audit','handoff','arc-review','standard-operation','support-workflow','verify','scene','legacy-scene','resume','refresh-references','produce','step','prepare-live','live-call','accept-role','w10-nk-live','w10-critics-live','review','promote','export','show-run','verify-history','verify-live','sprint','nk-start','nk-stop')]
    [string]$Command,
    [ValidateSet('offline','live')][string]$Mode,
    [ValidateSet('plot','scene_cards','writing_brief','prose','lint_layer1','lint_layer2','multi_lens_review','adversarial_verify','completeness_critic','refine','re_review','cards','brief','pov','draft','lint1','lint2','lens5','verifier3','completeness','re-review','revise')][string]$Stage,
    [string]$RunId,
    [string]$ProjectRoot,
    [string]$DataHome,
    [string]$DataHomePointer,
    [ValidateSet('scene','episode')][string]$Unit,
    [string]$Contract,
    [string]$WorkId,
    [string]$ProjectId,
    [string]$InputFile,
    [ValidateSet('md','txt','json')][string]$Format,
    [string]$StepName,
    [string]$Candidate,
    [string]$ReviewEvidence,
    [string]$W10Preflight,
    [string]$ControllerEvidence,
    [string]$RoleId,
    [string]$KeyPath,
    [int]$InputTokenCap,
    [int]$OutputTokenCap,
    [string]$SprintId,
    [string]$SprintPlan,
    [ValidateSet('01','02','03','04','05')][string]$WorkflowNumber,
    [ValidateSet('full','light','targeted')][string]$AuditScope = 'full',
    [string[]]$AuditChapter,
    [string]$AuditTarget,
    [string]$Reason,
    [string]$ArcRef,
    [string]$LastEpisode,
    [ValidateSet('decompose','extract_canon','jet_diagnostic','character_os','revision_plan')][string]$Operation,
    [string[]]$SourceFile,
    [string]$OperationTarget,
    [switch]$Pipeline,
    [switch]$AppOnly,
    [switch]$CreateOnly,
    [int]$Port = 3175
)
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$ProjectRootPath = if ($ProjectRoot) { (Resolve-Path -LiteralPath $ProjectRoot -ErrorAction Stop).Path } else { $null }
if ($ProjectRootPath -and -not (Test-Path -LiteralPath $ProjectRootPath -PathType Container)) { throw 'PROJECT_ROOT_REQUIRED' }
$PinnedPython = Join-Path $Root 'runtime/envs/critics-api/Scripts/python.exe'
$Python = if (Test-Path -LiteralPath $PinnedPython -PathType Leaf) { $PinnedPython } else { (Get-Command python.exe -ErrorAction SilentlyContinue).Source }
function Assert-ProjectSelected {
    if (-not $ProjectRootPath) { throw 'PROJECT_REQUIRED: pass -ProjectRoot explicitly' }
}
$ProjectCommands = @('import-source','source-list','project-contract','project-incremental','canon-audit','handoff','arc-review','standard-operation','support-workflow','scene','legacy-scene','resume','refresh-references','produce','step','prepare-live','live-call','accept-role','w10-nk-live','w10-critics-live','review','promote','export','show-run','verify-history','verify-live','sprint')
if ($Command -in $ProjectCommands -or ($Command -eq 'verify' -and $Mode -eq 'live')) { Assert-ProjectSelected }
function Read-Json([string]$Path) { Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json }
function Assert-Hash([string]$Path,[string]$Expected,[string]$Name) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "MISSING_FILE:$Name" }
    $Actual=(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
    if ($Actual -ne $Expected) { throw "HASH_MISMATCH:$Name" }
}
function Write-Utf8([string]$Path,[string]$Text) {
    $Parent=Split-Path -Parent $Path
    New-Item -ItemType Directory -Force -Path $Parent | Out-Null
    [IO.File]::WriteAllText($Path,$Text,[Text.UTF8Encoding]::new($false))
}
function Invoke-CnwRunner([string[]]$Arguments) {
    $Runner=Join-Path $Root 'tools/cnw_runner.py'
    if (-not (Test-Path -LiteralPath $Runner -PathType Leaf)) { throw 'CNW_RUNNER_MISSING' }
    if (-not $Python -or -not (Test-Path -LiteralPath $Python -PathType Leaf)) { throw 'PYTHON_RUNTIME_MISSING' }
    if ($Arguments -notcontains '--project-root') { $Arguments += @('--project-root',$ProjectRootPath) }
    & $Python $Runner @Arguments
    if ($LASTEXITCODE -ne 0) { throw "CNW_RUNNER_FAILED:$LASTEXITCODE" }
}
function Assert-Prepared {
    $Critics=Read-Json (Join-Path $Root 'patches/critics/PATCH_INDEX.json')
    $Nk=Read-Json (Join-Path $Root 'patches/nk/PATCH_INDEX.json')
    Assert-Hash (Join-Path $Root $Critics.dependency_lock) $Critics.dependency_lock_sha256 'CritiCS lock'
    Assert-Hash (Join-Path $Root $Nk.dependency_lock) $Nk.dependency_lock_sha256 'NK lock'
    Assert-Hash (Join-Path $Root $Nk.package_manifest) $Nk.package_manifest_sha256 'NK package manifest'
    if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) { throw 'PINNED_PYTHON_MISSING' }
    if (-not (Test-Path -LiteralPath (Join-Path $Root $Critics.runtime_path))) { throw 'PINNED_CRITICS_BUILD_MISSING' }
    if (-not (Test-Path -LiteralPath (Join-Path $Root (Join-Path 'runtime/patched/NK' $Nk.runtime_build_id)))) { throw 'PINNED_NK_BUILD_MISSING' }
    $PyVersion=(& $Python --version 2>&1 | Out-String).Trim()
    $NodeVersion=(& node.exe --version 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) { throw 'NODE_RUNTIME_MISSING' }
    $NpmVersion=(& npm.cmd --version 2>&1 | Out-String).Trim()
    if ($PyVersion -ne ('Python '+$Critics.python)) { throw 'PYTHON_VERSION_MISMATCH' }
    if ($NodeVersion -ne $Nk.node_version -or $NpmVersion -ne $Nk.npm_version) { throw 'NODE_OR_NPM_VERSION_MISMATCH' }
    [ordered]@{status='READY';python=$PyVersion;node=$NodeVersion;npm=$NpmVersion;critics_build=$Critics.runtime_build_id;nk_build=$Nk.runtime_build_id;locks='verified'}
}
function Export-ReadingPackage {
    if (-not $RunId) { throw 'RUN_ID_REQUIRED' }
    Invoke-CnwRunner @('export','--run-id',$RunId)
}
switch ($Command) {
    'doctor' {
        $EngineFiles=@('tools/cnw_runner.py','tools/cnw_roles.py','tools/cnw_contract.py','tools/project_paths.py','templates/config/workflow.template.yml')
        $MissingEngineFiles=@($EngineFiles | Where-Object { -not (Test-Path -LiteralPath (Join-Path $Root $_) -PathType Leaf) })
        $CoreRuntime='RUNTIME_MISSING'
        if ($Python -and (Test-Path -LiteralPath $Python -PathType Leaf)) {
            & $Python -c 'import httpx' 2>$null
            if ($LASTEXITCODE -eq 0) { $CoreRuntime='READY' }
        }
        $AssetHealth=[ordered]@{author_reference='UNVERIFIED';optional_critics='UNVERIFIED';optional_nk='UNVERIFIED'}
        if ($Python -and (Test-Path -LiteralPath $Python -PathType Leaf)) {
            $HealthOutput=& $Python (Join-Path $Root 'tools/studio_health.py') --repo-root $Root
            if ($LASTEXITCODE -eq 0) {
                $Health=$HealthOutput | ConvertFrom-Json
                $AssetHealth.author_reference=$Health.author_reference
                $AssetHealth.optional_critics=$Health.optional_critics
                $AssetHealth.optional_nk=$Health.optional_nk
            }
        }
        $Result=[ordered]@{status=$(if ($MissingEngineFiles.Count -eq 0) { 'ENGINE_READY' } else { 'ENGINE_INCOMPLETE' });missing_engine_files=$MissingEngineFiles;core_runtime=$CoreRuntime;author_reference=$AssetHealth.author_reference;optional_critics=$AssetHealth.optional_critics;optional_nk=$AssetHealth.optional_nk;project=$(if ($AppOnly -or -not $ProjectRootPath) { 'NOT_SELECTED' } else { $ProjectRootPath });provider_call='none';generic_live_production='NOT_RUN'}
        $Result | ConvertTo-Json -Depth 4
    }
    'setup' {
        if (-not $DataHome) { throw 'DATA_HOME_REQUIRED: pass -DataHome explicitly' }
        if (-not $Python) { throw 'PYTHON_RUNTIME_MISSING' }
        $SetupArgs=@((Join-Path $Root 'tools/cnw_project.py'),'setup','--data-home',$DataHome)
        if ($DataHomePointer) { $SetupArgs += @('--pointer-path',$DataHomePointer) }
        & $Python @SetupArgs
        if ($LASTEXITCODE -ne 0) { throw "STORYSTUDIO_SETUP_FAILED:$LASTEXITCODE" }
    }
    'prepare' { Assert-Prepared | ConvertTo-Json -Depth 4 }
    'import-source' {
        if (-not $InputFile) { throw 'SOURCE_IMPORT_REQUIRES_INPUT_FILE' }
        $SourcePath=(Resolve-Path -LiteralPath $InputFile).Path
        $ImportArgs=@((Join-Path $Root 'tools/cnw_project.py'),'source-import','--project-root',$ProjectRootPath,'--input',$SourcePath)
        if ($Format) { $ImportArgs += @('--format',$Format) }
        & $Python @ImportArgs
        if ($LASTEXITCODE -ne 0) { throw "CNW_SOURCE_IMPORT_FAILED:$LASTEXITCODE" }
    }
    'source-list' {
        & $Python (Join-Path $Root 'tools/cnw_project.py') source-list --project-root $ProjectRootPath
        if ($LASTEXITCODE -ne 0) { throw "CNW_SOURCE_LIST_FAILED:$LASTEXITCODE" }
    }
    'verify' {
        if (-not $Mode) { throw 'VERIFY_MODE_REQUIRED: -Mode offline|live' }
        if ($Mode -eq 'offline') {
            Assert-Prepared | Out-Null
            & $Python (Join-Path $Root 'tools/critics_offline_check.py')
            if ($LASTEXITCODE -ne 0) { throw 'CRITICS_OFFLINE_CHECK_FAILED' }
            & (Join-Path $Root 'tools/nk_http_offline_check.ps1')
            if ($LASTEXITCODE -ne 0) { throw 'NK_OFFLINE_CHECK_FAILED' }
        } else {
            if (-not $RunId) { throw 'VERIFY_LIVE_REQUIRES_RUN_ID' }
            Invoke-CnwRunner @('verify-live','--run-id',$RunId,'--project-root',$ProjectRootPath)
        }
    }
    'scene' {
        if (-not $Stage -or -not $WorkId -or $WorkId -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{1,95}$') { throw 'LEGACY_SCENE_REQUIRES_EXPLICIT_PROJECT_STAGE_AND_WORK_ID' }
        $RelativePath=switch ($Stage) {
            'plot' { "06_plot/${WorkId}_plot.v1.md" }
            'draft' { "07_draft/${WorkId}_v0.md" }
            'revise' { "09_revision/${WorkId}_v1.md" }
            default { throw 'LEGACY_SCENE_STAGE_INVALID: use plot|draft|revise' }
        }
        $Path=Join-Path $ProjectRootPath $RelativePath
        if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "CHECKPOINT_MISSING:$Stage" }
        [ordered]@{status='LEGACY_CHECKPOINT_ONLY';stage=$Stage;work_id=$WorkId;path=$RelativePath;sha256=(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash;provider_call='none'} | ConvertTo-Json -Depth 4
    }
    'legacy-scene' { & $PSCommandPath scene -ProjectRoot $ProjectRootPath -Stage $Stage -WorkId $WorkId }
    'project-init' {
        if (-not $ProjectId -or -not $DataHome) { throw 'PROJECT_INIT_REQUIRES_PROJECT_ID_AND_DATA_HOME' }
        & $Python (Join-Path $Root 'tools/cnw_project.py') registered-init --project-id $ProjectId --data-home $DataHome
        if ($LASTEXITCODE -ne 0) { throw "CNW_PROJECT_INIT_FAILED:$LASTEXITCODE" }
    }
    'project-import' {
        if (-not $ProjectId -or -not $DataHome -or -not $InputFile) { throw 'PROJECT_IMPORT_REQUIRES_PROJECT_ID_DATA_HOME_AND_INPUT_FILE' }
        $ImportArgs=@((Join-Path $Root 'tools/cnw_project.py'),'registered-import','--project-id',$ProjectId,'--data-home',$DataHome,'--input',(Resolve-Path -LiteralPath $InputFile).Path)
        if ($Format) { $ImportArgs += @('--format',$Format) }
        & $Python @ImportArgs
        if ($LASTEXITCODE -ne 0) { throw "CNW_PROJECT_IMPORT_FAILED:$LASTEXITCODE" }
    }
    'project-contract' {
        if (-not $ProjectRoot -or -not $InputFile) { throw 'PROJECT_CONTRACT_REQUIRES_PROJECT_ROOT_AND_PRIVATE_DRAFT_JSON' }
        $DraftPath=(Resolve-Path -LiteralPath $InputFile).Path
        if (-not $DraftPath.StartsWith(($ProjectRootPath.TrimEnd('\')+'\'),[StringComparison]::OrdinalIgnoreCase)) { throw 'CONTRACT_DRAFT_OUTSIDE_PROJECT' }
        & $Python (Join-Path $Root 'tools/cnw_project.py') draft-contract --project-root $ProjectRootPath --draft $DraftPath
        if ($LASTEXITCODE -ne 0) { throw "CNW_CONTRACT_DRAFT_FAILED:$LASTEXITCODE" }
    }
    'project-incremental' {
        if (-not $InputFile) { throw 'PROJECT_INCREMENTAL_REQUIRES_INPUT_FILE' }
        $IncrementalArgs=@((Join-Path $Root 'tools/cnw_project.py'),'registered-incremental','--project-root',$ProjectRootPath,'--input',(Resolve-Path -LiteralPath $InputFile).Path)
        if ($Format) { $IncrementalArgs += @('--format',$Format) }
        & $Python @IncrementalArgs
        if ($LASTEXITCODE -ne 0) { throw "CNW_PROJECT_INCREMENTAL_FAILED:$LASTEXITCODE" }
    }
    'canon-audit' {
        $AuditArguments = @('canon-audit','--project-root',$ProjectRootPath,'--scope',$AuditScope)
        foreach ($Chapter in $AuditChapter) { $AuditArguments += @('--chapter',$Chapter) }
        if ($AuditTarget) { $AuditArguments += @('--target',$AuditTarget) }
        & $Python (Join-Path $Root 'tools/cnw_project.py') @AuditArguments
        if ($LASTEXITCODE -ne 0) { throw "CNW_CANON_AUDIT_FAILED:$LASTEXITCODE" }
    }
    'handoff' {
        $HandoffArguments = @('handoff','--project-root',$ProjectRootPath)
        if ($Pipeline) { $HandoffArguments += '--pipeline' }
        & $Python (Join-Path $Root 'tools/cnw_project.py') @HandoffArguments
        if ($LASTEXITCODE -ne 0) { throw "CNW_HANDOFF_FAILED:$LASTEXITCODE" }
    }
    'support-workflow' {
        if (-not $WorkflowNumber) { throw 'SUPPORT_WORKFLOW_REQUIRES_NUMBER' }
        & $Python (Join-Path $Root 'tools/cnw_project.py') support-workflow --project-root $ProjectRootPath --number $WorkflowNumber
        if ($LASTEXITCODE -ne 0) { throw "CNW_SUPPORT_WORKFLOW_FAILED:$LASTEXITCODE" }
    }
    'produce' {
        if (-not $Contract -or -not $RunId -or -not $Mode) { throw 'PRODUCE_REQUIRES_MODE_CONTRACT_AND_NEW_RUN_ID' }
        $ContractPath = if ([IO.Path]::IsPathRooted($Contract)) { $Contract } else { Join-Path $ProjectRootPath $Contract }
        $RunnerArgs=@('produce','--mode',$Mode,'--contract',$ContractPath,'--run-id',$RunId)
        if ($Unit) { $RunnerArgs += @('--unit',$Unit) }
        if ($WorkId) { $RunnerArgs += @('--work-id',$WorkId) }
        if ($Mode -eq 'live' -and $CreateOnly) { $RunnerArgs += @('--create-only') }
        $RunnerArgs += @('--project-root',$ProjectRootPath)
        Invoke-CnwRunner $RunnerArgs
    }
    'step' {
        if (-not $RunId -or -not $StepName) { throw 'STEP_REQUIRES_RUN_ID_AND_STEP_NAME' }
        $RunnerArgs=@('step','--run-id',$RunId,'--stage',$StepName)
        if ($WorkId) { $RunnerArgs += @('--work-id',$WorkId) }
        Invoke-CnwRunner $RunnerArgs
    }
    'prepare-live' {
        if (-not $RunId -or -not $Stage) { throw 'PREPARE_LIVE_REQUIRES_RUN_AND_STAGE' }
        $RunPath = Join-Path $ProjectRootPath ("runs\" + $RunId)
        $Executor = Join-Path $Root 'tools/cnw_live_executor.py'
        if ($Stage -in @('lens5','verifier3','completeness','refine','re-review')) {
            $PrepareArgs = @($Executor,'--run-dir',$RunPath,'--prepare-stage',$Stage)
            if ($RoleId) { $PrepareArgs += @('--role-id',$RoleId) }
        } else {
            $Role = switch ($Stage) { plot {'plot'} cards {'cards'} brief {'brief'} draft {'prose'} default { throw "LIVE_ROLE_STAGE_INVALID:$Stage" } }
            if (-not $InputFile -or -not $W10Preflight) { throw 'PREPARE_LIVE_ROLE_REQUIRES_INPUT_MAP_AND_W10_PREFLIGHT' }
            $PrepareArgs = @($Executor,'--run-dir',$RunPath,'--prepare-role',$Role,'--project-root',$ProjectRootPath,'--inputs-json',(Resolve-Path -LiteralPath $InputFile).Path,'--preflight',(Resolve-Path -LiteralPath $W10Preflight).Path)
        }
        & $Python @PrepareArgs
        if ($LASTEXITCODE -ne 0) { throw "CNW_LIVE_PREPARE_FAILED:$LASTEXITCODE" }
    }
    'accept-role' {
        if (-not $RunId -or -not $Stage -or -not $ControllerEvidence) { throw 'ACCEPT_ROLE_REQUIRES_RUN_STAGE_AND_CONTROLLER_EVIDENCE' }
        $RunPath = Join-Path $ProjectRootPath ("runs\" + $RunId)
        & $Python (Join-Path $Root 'tools/cnw_live_executor.py') --run-dir $RunPath --stage $Stage --accept-controller-role-output --controller-evidence (Resolve-Path -LiteralPath $ControllerEvidence).Path
        if ($LASTEXITCODE -ne 0) { throw "CNW_CONTROLLER_ROLE_ACCEPT_FAILED:$LASTEXITCODE" }
    }
    'live-call' {
        if (-not $RunId -or -not $Stage) { throw 'LIVE_CALL_REQUIRES_RUN_AND_STAGE' }
        $RunPath = Join-Path $ProjectRootPath ("runs\" + $RunId)
        $Executor = Join-Path $Root 'tools/cnw_live_executor.py'
        if ($Stage -in @('lint1','lint2')) {
            if ($InputFile -or $RoleId -or $InputTokenCap -gt 0 -or $OutputTokenCap -gt 0) { throw 'LOCAL_LINT_TAKES_NO_PACKET_OR_PROVIDER_CAPS' }
            $LiveArgs = @($Executor,'--run-dir',$RunPath,'--stage',$Stage)
        } else {
            if (-not $InputFile -or $InputTokenCap -lt 1 -or $OutputTokenCap -lt 1) { throw 'LIVE_CALL_REQUIRES_RUN_STAGE_PACKET_AND_POSITIVE_CAPS' }
            $LiveArgs = @($Executor,'--run-dir',$RunPath,'--stage',$Stage,'--packet',$InputFile,'--input-token-cap',"$InputTokenCap",'--output-token-cap',"$OutputTokenCap")
            if ($RoleId) { $LiveArgs += @('--role-id',$RoleId) }
        }
        & $Python @LiveArgs
        if ($LASTEXITCODE -ne 0) { throw "CNW_LIVE_CALL_FAILED:$LASTEXITCODE" }
    }
    'w10-nk-live' {
        if (-not $RunId -or -not $InputFile) { throw 'W10_NK_LIVE_REQUIRES_RUN_ID_AND_PAYLOAD' }
        $Pwsh = (Get-Command pwsh -ErrorAction Stop).Source
        $NkScript = Join-Path $Root 'tools/cnw_w10_nk_live.ps1'
        $NkArgs = @('-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',$NkScript,'-RunId',$RunId,'-ProjectRoot',$ProjectRootPath,'-PayloadPath',$InputFile)
        if ($KeyPath) { $NkArgs += @('-KeyPath',$KeyPath) }
        if ($W10Preflight) { $NkArgs += @('-W10Preflight',(Resolve-Path -LiteralPath $W10Preflight).Path) }
        & $Pwsh @NkArgs
        if ($LASTEXITCODE -ne 0) { throw "W10_NK_LIVE_FAILED:$LASTEXITCODE" }
    }
    'w10-critics-live' {
        if (-not $RunId -or $Stage -notin @('plot','draft')) { throw 'W10_CRITICS_LIVE_REQUIRES_RUN_AND_STAGE_plot_or_draft' }
        $OldKey = $env:DEEPSEEK_API_KEY
        try {
            if (-not $env:DEEPSEEK_API_KEY -and $KeyPath) {
                $RawKey = [IO.File]::ReadAllText((Resolve-Path -LiteralPath $KeyPath))
                if ($RawKey -match '(?im)^\s*(?:DEEPSEEK_API_KEY\s*=\s*)?["'']?(sk-[A-Za-z0-9_-]{20,})') { $env:DEEPSEEK_API_KEY = $Matches[1] }
                else { $env:DEEPSEEK_API_KEY = $RawKey.Trim().Trim('"', "'") }
                $RawKey = $null
            }
            $RunPath = Join-Path $ProjectRootPath ("runs\" + $RunId)
            $CriticsAction = if ($Stage -eq 'plot') { 'plan-critique' } else { 'text-refine' }
            $CriticsArgs = @((Join-Path $Root 'tools/cnw_w10_critics.py'),'--run-dir',$RunPath,'--action',$CriticsAction)
            if ($W10Preflight) { $CriticsArgs += @('--preflight',(Resolve-Path -LiteralPath $W10Preflight).Path) }
            & $Python @CriticsArgs
            if ($LASTEXITCODE -ne 0) { throw "W10_CRITICS_FAILED:$LASTEXITCODE" }
        } finally {
            $env:DEEPSEEK_API_KEY = $OldKey
            $RawKey = $null
        }
    }
    'review' { if (-not $RunId) { throw 'RUN_ID_REQUIRED' }; Invoke-CnwRunner @('review','--run-id',$RunId) }
    'promote' {
        if (-not $RunId -or -not $Candidate -or -not $ReviewEvidence) { throw 'PROMOTE_REQUIRES_RUN_ID_CANDIDATE_AND_REVIEW_EVIDENCE' }
        Invoke-CnwRunner @('promote','--run-id',$RunId,'--project-root',$ProjectRootPath,'--candidate',$Candidate,'--review-evidence',$ReviewEvidence)
    }
    'show-run' { if (-not $RunId) { throw 'RUN_ID_REQUIRED' }; Invoke-CnwRunner @('show-run','--run-id',$RunId) }
    'verify-history' { if (-not $RunId) { throw 'RUN_ID_REQUIRED' }; Invoke-CnwRunner @('verify-history','--run-id',$RunId) }
    'verify-live' { if (-not $RunId) { throw 'RUN_ID_REQUIRED' }; Invoke-CnwRunner @('verify-live','--run-id',$RunId) }
    'sprint' {
        if (-not $SprintId -or -not $SprintPlan) { throw 'SPRINT_REQUIRES_SPRINT_ID_AND_FIXTURE_PLAN' }
        $PlanPath=(Resolve-Path -LiteralPath $SprintPlan).Path
        if ($Mode -eq 'live') { Invoke-CnwRunner @('sprint','--run-id',$SprintId,'--sprint-plan',$PlanPath,'--mode','live'); break }
        $SprintScript=Join-Path $Root 'tools/cnw_sprint.py'
        & $Python $SprintScript --project-root $ProjectRootPath --sprint-id $SprintId --plan $PlanPath
        if ($LASTEXITCODE -ne 0) { throw "CNW_SPRINT_FAILED:$LASTEXITCODE" }
    }
    'resume' {
        if (-not $RunId -or $RunId -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$') { throw 'VALID_RUN_ID_REQUIRED' }
        $RunProjectRoot=$ProjectRootPath
        $Run=Join-Path $RunProjectRoot ("runs/$RunId")
        if (-not (Test-Path -LiteralPath $Run -PathType Container)) { throw 'RUN_NOT_FOUND' }
        if (Test-Path -LiteralPath (Join-Path $Run 'run_state.json') -PathType Leaf) { Invoke-CnwRunner @('resume','--run-id',$RunId,'--project-root',$RunProjectRoot); break }
        throw 'RUN_STATE_MISSING: selected project run is not a CNW resumable run'
    }
    'standard-operation' {
        if (-not $Operation) { throw 'STANDARD_OPERATION_REQUIRED' }
        $StandardArguments = @('standard-operation','--project-root',$ProjectRootPath,'--operation',$Operation)
        foreach ($StandardSource in $SourceFile) { $StandardArguments += @('--source',$StandardSource) }
        if ($OperationTarget) { $StandardArguments += @('--target',$OperationTarget) }
        & $Python (Join-Path $Root 'tools/cnw_project.py') @StandardArguments
        if ($LASTEXITCODE -ne 0) { throw "CNW_STANDARD_OPERATION_FAILED:$LASTEXITCODE" }
    }
    'arc-review' {
        if (-not $ArcRef) { throw 'ARC_REFERENCE_REQUIRED' }
        $ArcArgs=@('--project-root',$ProjectRootPath,'--arc-ref',$ArcRef)
        if ($LastEpisode) { $ArcArgs += @('--last-episode',$LastEpisode) }
        & $Python (Join-Path $Root 'tools/cnw_arc.py') @ArcArgs
        if ($LASTEXITCODE -ne 0) { throw "CNW_ARC_REVIEW_FAILED:$LASTEXITCODE" }
    }
    'refresh-references' {
        if (-not $RunId -or -not $Reason) { throw 'REFERENCE_REOPEN_REQUIRES_RUN_ID_AND_REASON' }
        Invoke-CnwRunner @('refresh-references','--run-id',$RunId,'--reason',$Reason)
    }
    'export' { if (-not $RunId) { throw 'RUN_ID_REQUIRED' }; Invoke-CnwRunner @('export','--run-id',$RunId) }
    'nk-start' {
        Assert-Prepared | Out-Null
        if ($Port -lt 1024 -or $Port -gt 65535) { throw 'INVALID_PORT' }
        if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) { throw "PORT_IN_USE:$Port" }
        $Index=Read-Json (Join-Path $Root 'patches/nk/PATCH_INDEX.json'); $Build=Join-Path $Root (Join-Path 'runtime/patched/NK' $Index.runtime_build_id)
        $Npm=(Get-Command npm.cmd).Source
        $Proc=Start-Process -FilePath $Npm -ArgumentList @('--prefix',$Build,'start','--','--port',"$Port") -WorkingDirectory $Build -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $Root 'runtime/private/nk-studio.stdout.log') -RedirectStandardError (Join-Path $Root 'runtime/private/nk-studio.stderr.log')
        $Ready=$false
        for ($i=0; $i -lt 60; $i++) {
            $Listener=Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
            if ($Listener) { $Ready=$true; break }
            if ($Proc.HasExited) { break }
            Start-Sleep -Milliseconds 250
        }
        if (-not $Ready) { throw 'NK_SERVER_DID_NOT_BECOME_READY; inspect runtime/private/nk-studio.*.log' }
        Start-Sleep -Milliseconds 750
        $Listener=Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        if (-not $Listener) { throw 'NK_SERVER_READINESS_NOT_STABLE' }
        if (@($Listener | Where-Object LocalAddress -ne '127.0.0.1').Count -gt 0) { throw 'NK_SERVER_NOT_LOOPBACK' }
        Write-Utf8 (Join-Path $Root 'runtime/private/nk-studio-process.json') (([ordered]@{launcher_pid=$Proc.Id;server_pid=$Listener[0].OwningProcess;port=$Port;build=$Index.runtime_build_id} | ConvertTo-Json -Depth 3))
        [ordered]@{status='READY';pid=$Proc.Id;port=$Port;host='127.0.0.1';build=$Index.runtime_build_id;stop_command='tools/studio.ps1 nk-stop'} | ConvertTo-Json -Depth 4
    }
    'nk-stop' {
        $Stopped=0
        $Index=Read-Json (Join-Path $Root 'patches/nk/PATCH_INDEX.json')
        $Build=(Join-Path $Root (Join-Path 'runtime/patched/NK' $Index.runtime_build_id)).TrimEnd('\')
        $StatePath=Join-Path $Root 'runtime/private/nk-studio-process.json'
        if (-not (Test-Path -LiteralPath $StatePath -PathType Leaf)) {
            if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) { throw 'NK_PROCESS_RECORD_MISSING_WITH_ACTIVE_LISTENER' }
            [ordered]@{status='STOPPED';port=$Port;stopped=0;listener_remaining=$false} | ConvertTo-Json -Depth 4
            return
        }
        $State=Read-Json $StatePath
        if ($State.port -ne $Port -or $State.build -ne $Index.runtime_build_id) { throw 'NK_PROCESS_RECORD_MISMATCH' }
        $Listeners=@(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
        foreach ($Listener in $Listeners) {
            if ($Listener.LocalAddress -ne '127.0.0.1' -and $Listener.LocalAddress -ne '::1') { throw "REFUSE_NON_LOOPBACK_LISTENER:$($Listener.LocalAddress):$Port" }
            if ($Listener.OwningProcess -ne [int]$State.server_pid) { throw "REFUSE_UNVERIFIED_PORT_OWNER:$Port" }
        }
        $Pids=@([int]$State.server_pid,[int]$State.launcher_pid | Select-Object -Unique)
        foreach ($ProcessId in $Pids) {
            if (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue) { Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue; $Stopped++ }
        }
        for ($i=0; $i -lt 15; $i++) {
            $RemainingProcess=@($Pids | Where-Object { Get-Process -Id $_ -ErrorAction SilentlyContinue })
            $RemainingListener=Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
            if (-not $RemainingProcess -and -not $RemainingListener) { break }
            Start-Sleep -Milliseconds 100
        }
        if ($RemainingProcess -or $RemainingListener) { throw "NK_PROCESS_OR_LISTENER_REMAINS:$Port" }
        Remove-Item -LiteralPath $StatePath -Force -ErrorAction SilentlyContinue
        [ordered]@{status='STOPPED';port=$Port;stopped=$Stopped;listener_remaining=$false} | ConvertTo-Json -Depth 4
    }
}
