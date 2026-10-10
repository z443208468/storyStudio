[CmdletBinding()]
param(
    [Parameter(Position=0,Mandatory=$true)]
    [ValidateSet('doctor','prepare','import-source','project-init','project-import','project-contract','project-incremental','canon-audit','handoff','support-workflow','verify','scene','legacy-scene','resume','refresh-references','produce','step','prepare-live','live-call','accept-role','w10-nk-live','w10-critics-live','review','promote','export','show-run','verify-history','verify-live','sprint','nk-start','nk-stop')]
    [string]$Command,
    [ValidateSet('offline','live')][string]$Mode,
    [ValidateSet('plot','scene_cards','writing_brief','prose','lint_layer1','lint_layer2','multi_lens_review','adversarial_verify','completeness_critic','refine','re_review','cards','brief','pov','draft','lint1','lint2','lens5','verifier3','completeness','re-review','revise')][string]$Stage,
    [string]$RunId,
    [string]$ProjectRoot,
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
    [switch]$Pipeline,
    [switch]$CreateOnly,
    [int]$Port = 3175
)
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$WorkspaceRoot = Join-Path $Root 'workspace'
$ProjectRootPath = if ($ProjectRoot) { (Resolve-Path -LiteralPath $ProjectRoot).Path } else { Join-Path $WorkspaceRoot 'cangqi' }
if (-not $ProjectRootPath.StartsWith(($WorkspaceRoot.TrimEnd('\') + '\'),[StringComparison]::OrdinalIgnoreCase)) { throw 'PROJECT_ROOT_OUTSIDE_PRIVATE_WORKSPACE' }
$SourceRoot = Join-Path $Root 'inputs/private/release/300a829c7524d620ab89177afcf52c03dffea633392c632f69a943f798dad3b2/Cangqi_Jun_Release_2_3'
$Python = Join-Path $Root 'runtime/envs/critics-api/Scripts/python.exe'
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
    if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) { throw 'PINNED_PYTHON_MISSING' }
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
    Assert-Prepared | Out-Null
    $Work=Join-Path $Root 'workspace/cangqi'
    $Out=Join-Path $Root 'deliverables/EP001'
    $V0=Get-Content -LiteralPath (Join-Path $Work '07_draft/ep001_v0.md') -Raw
    $V1=Get-Content -LiteralPath (Join-Path $Work '09_revision/ep001_v1.md') -Raw
    $Anchors=Get-Content -LiteralPath (Join-Path $Work '06_plot/ep001_source_anchors.md') -Raw
    $AnchorLines=$Anchors -split "`r?`n"
    $FrontIndex=[Array]::FindIndex($AnchorLines,[Predicate[string]]{ param($line) $line -match '^## 前锚：J19' })
    $FlowIndex=[Array]::FindIndex($AnchorLines,[Predicate[string]]{ param($line) $line -match '^## 紧随本场的原流程' })
    if ($FrontIndex -lt 0 -or $FlowIndex -le $FrontIndex) { throw 'SOURCE_ANCHOR_EXPORT_MATCH_FAILED' }
    $Prev=($AnchorLines[($FrontIndex+1)..($FlowIndex-1)] | Where-Object { $_.Trim() } | Select-Object -Last 1)
    $FlowEnd=$FlowIndex+1
    while ($FlowEnd -lt $AnchorLines.Count -and $AnchorLines[$FlowEnd] -notmatch '^## ') { $FlowEnd++ }
    $FlowText=($AnchorLines[($FlowIndex+1)..($FlowEnd-1)] -join "`n").Trim()
    $FlowParagraphs=@($FlowText -split "\r?\n\s*\r?\n" | Where-Object { $_.Trim() })
    if ($FlowParagraphs.Count -lt 2) { throw 'SOURCE_ANCHOR_EXPORT_MATCH_FAILED' }
    $Gameplay=$FlowParagraphs[0].Trim(); $Confession=$FlowParagraphs[1].Trim()
    if (-not $Prev -or -not $Gameplay -or -not $Confession) { throw 'SOURCE_ANCHOR_EXPORT_MATCH_FAILED' }
    foreach ($pair in @(@('01_初稿.md',$V0),@('01_初稿.txt',$V0),@('02_修订稿.md',$V1),@('02_修订稿.txt',$V1))) { Write-Utf8 (Join-Path $Out $pair[0]) ($pair[1].Trim()+"`r`n") }
    $ContextMd=@"
# EP001 前后文连读

## 原文前锚（J19:555）

$Prev

## 新增场景（P2-06 v1）

$($V1.Trim())

## 原文立即恢复（J19:557、559）

$Gameplay

$Confession

## 后续原路由

后续 J20 仍按玩家在 J19 的原操作进入；本阅读摘录不展开分支正文。上述插场未改变任何路线状态。

---

本文件中的新增场景是候选性生产文本，不晋升 Canon；前后锚仍以源稿为准。
"@
    Write-Utf8 (Join-Path $Out '03_前后文连读.md') $ContextMd
    Write-Utf8 (Join-Path $Out '03_前后文连读.txt') $ContextMd
    $Esc=[System.Net.WebUtility]::HtmlEncode($ContextMd)
    $Html="<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>EP001 前后文连读</title><style>body{max-width:54rem;margin:3rem auto;padding:0 1.25rem;font:1.05rem/1.9 system-ui,'Microsoft YaHei',sans-serif;color:#222}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}</style></head><body><pre>$Esc</pre></body></html>"
    Write-Utf8 (Join-Path $Out '03_前后文连读.html') $Html
    $Notes=@"
# EP001 修改说明

- **Plot / Scene Card**：以书案腾空为单一目标，四个人物只按可见动作分工；不扩充路线、秘密或关系。
- **NK → Brief**：NK 原句“书摞歪斜，我们同时伸手按住；听到提醒后，我把手部动作放慢下来”进入 Brief 的 POV 检查栏，用来限定可写动作，不逐字充当正文。
- **剧情批评**：CritiCS ``three_critic()`` 的五个角色调用与 ``modifiedStoryline()`` 均实际执行。其多场扩写、额外悬念和未锚定的关系解释被拒；当前 Plot/Card 仍只有腾空书案这一场。
- **文字批评**：``Two_refinement()`` 仅审 v0 中“思柔递书…… / 柳浅按住最外侧…… / 明穗没说话……”这连续三句。Leader 建议加“像提醒，也像确认”被拒，因为这会替思柔解释意图；仅把“边角对齐”收紧为“边角码齐”，没有把三句审稿冒称全文审稿。
- **v0 → v1**：开头从“老师的话音还没落”改为“老师说完”，明确动作发生在前锚之后；删去“木面上一层薄薄的灰痕”、笔/袖口及“把面前的纸铺开”等卡片外细节；保留书摞歪斜、共同按住、听提醒后放慢、书案腾空。
- **流程**：v1 保存在 `workspace/cangqi/09_revision/`，用户可按个人创作判断是否继续采用；本交付不代表用户创意签收。
"@
    Write-Utf8 (Join-Path $Out '04_修改说明.md') $Notes
    Write-Utf8 (Join-Path $Out '04_修改说明.txt') $Notes
    $Manifest=Get-ChildItem -LiteralPath $Out -File | Where-Object Name -ne 'manifest.json' | ForEach-Object { [ordered]@{path=$_.Name;sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash} }
    $Manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $Out 'manifest.json') -Encoding utf8
    [ordered]@{status='EXPORTED';directory=$Out;files=$Manifest.Count;offline_html=$true}
}
switch ($Command) {
    'doctor' {
        $Checks=[ordered]@{workspace=(Test-Path -LiteralPath (Join-Path $Root 'workspace/cangqi'));private_source=(Test-Path -LiteralPath (Join-Path $SourceRoot 'source_manifest.json'));python=(Test-Path -LiteralPath $Python);studio_script=$PSCommandPath;branch=(& git -C $Root branch --show-current).Trim()}
        $Checks | ConvertTo-Json -Depth 4
    }
    'prepare' { Assert-Prepared | ConvertTo-Json -Depth 4 }
    'import-source' {
        $Manifest=Read-Json (Join-Path $SourceRoot 'source_manifest.json')
        if ($Manifest.source_version -ne 'JUN-SINGLE-02.3' -or $Manifest.zip.sha256 -ne '300A829C7524D620AB89177AFCF52C03DFFEA633392C632F69A943F798DAD3B2') { throw 'PRIVATE_SOURCE_IDENTITY_MISMATCH' }
        [ordered]@{status='SOURCE_READY';version=$Manifest.source_version;sha256=$Manifest.zip.sha256;root=$SourceRoot;copy='read-only, already imported'} | ConvertTo-Json -Depth 4
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
            $Log=Get-Content -LiteralPath (Join-Path $Root 'reviews/P2_ACCEPTANCE_LOG.md') -Raw
            if (-not $Log.Contains('P2-04') -or -not $Log.Contains('REMOTE_READBACK')) { throw 'LIVE_ACCEPTANCE_EVIDENCE_MISSING' }
            'Accepted P2-04 live evidence located; no provider request repeated.'
        }
    }
    'scene' {
        if (-not $Stage) { throw 'SCENE_STAGE_REQUIRED: -Stage plot|draft|revise' }
        $Path=switch ($Stage) { plot { Join-Path $Root 'workspace/cangqi/06_plot/ep001_plot.v1.md' } draft { Join-Path $Root 'workspace/cangqi/07_draft/ep001_v0.md' } revise { Join-Path $Root 'workspace/cangqi/09_revision/ep001_v1.md' } }
        if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "CHECKPOINT_MISSING:$Stage" }
        [ordered]@{status='LEGACY_CHECKPOINT_ONLY';stage=$Stage;path=$Path;sha256=(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash;provider_call='none; historical P2 checkpoint'} | ConvertTo-Json -Depth 4
    }
    'project-init' {
        if (-not $ProjectId) { throw 'PROJECT_ID_REQUIRED' }
        & $Python (Join-Path $Root 'tools/cnw_project.py') init --project-id $ProjectId --workspace-root $WorkspaceRoot
        if ($LASTEXITCODE -ne 0) { throw "CNW_PROJECT_INIT_FAILED:$LASTEXITCODE" }
    }
    'project-import' {
        if (-not $ProjectId -or -not $InputFile) { throw 'PROJECT_IMPORT_REQUIRES_PROJECT_ID_AND_INPUT_FILE' }
        $ImportArgs=@((Join-Path $Root 'tools/cnw_project.py'),'import-source','--project-id',$ProjectId,'--workspace-root',$WorkspaceRoot,'--input',(Resolve-Path -LiteralPath $InputFile).Path)
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
        if (-not $ProjectId -or -not $InputFile) { throw 'PROJECT_INCREMENTAL_REQUIRES_PROJECT_ID_AND_INPUT_FILE' }
        & $Python (Join-Path $Root 'tools/cnw_project.py') incremental-update --project-id $ProjectId --workspace-root $WorkspaceRoot --input (Resolve-Path -LiteralPath $InputFile).Path
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
    'legacy-scene' { & $PSCommandPath scene -Stage $Stage }
    'produce' {
        if (-not $Contract -or -not $RunId -or -not $Mode) { throw 'PRODUCE_REQUIRES_MODE_CONTRACT_AND_NEW_RUN_ID' }
        if (-not $ProjectRoot) { $ProjectRootPath = Join-Path $WorkspaceRoot 'cangqi' }
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
        if (-not $ProjectRoot) { $ProjectRootPath = Join-Path $WorkspaceRoot 'cangqi' }
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
        if (-not $ProjectRoot) { $ProjectRootPath = Join-Path $WorkspaceRoot 'cangqi' }
        $Pwsh = (Get-Command pwsh -ErrorAction Stop).Source
        $NkScript = Join-Path $Root 'tools/cnw_w10_nk_live.ps1'
        $NkArgs = @('-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',$NkScript,'-RunId',$RunId,'-ProjectRoot',$ProjectRootPath,'-PayloadPath',$InputFile)
        if ($KeyPath) { $NkArgs += @('-KeyPath',$KeyPath) }
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
            & $Python (Join-Path $Root 'tools/cnw_w10_critics.py') --run-dir $RunPath --action $CriticsAction
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
        $SprintScript=Join-Path $Root 'tools/cnw_sprint.py'
        & $Python $SprintScript --project-root $ProjectRootPath --sprint-id $SprintId --plan $PlanPath
        if ($LASTEXITCODE -ne 0) { throw "CNW_SPRINT_FAILED:$LASTEXITCODE" }
    }
    'resume' {
        if (-not $RunId -or $RunId -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$') { throw 'VALID_RUN_ID_REQUIRED' }
        $RunProjectRoot=$ProjectRootPath
        $Run=Join-Path $RunProjectRoot ("runs/$RunId")
        if (-not (Test-Path -LiteralPath $Run -PathType Container)) { $RunProjectRoot=$Root; $Run=Join-Path $RunProjectRoot ("runs/$RunId") }
        if (-not (Test-Path -LiteralPath $Run -PathType Container)) { throw 'RUN_NOT_FOUND' }
        if (Test-Path -LiteralPath (Join-Path $Run 'run_state.json') -PathType Leaf) { Invoke-CnwRunner @('resume','--run-id',$RunId,'--project-root',$RunProjectRoot); break }
        $Ledger=Read-Json (Join-Path $Root 'runtime/private/p2-cost-ledger.json')
        $Rows=@($Ledger.requests | Where-Object run_id -eq $RunId)
        [ordered]@{status='RUN_REOPENED_READ_ONLY';run_id=$RunId;path=$Run;ledger_rows=$Rows.Count;provider_requests=@($Rows | Where-Object provider_request_id).Count;no_replay=$true} | ConvertTo-Json -Depth 4
    }
    'refresh-references' {
        if (-not $RunId -or -not $Reason) { throw 'REFERENCE_REOPEN_REQUIRES_RUN_ID_AND_REASON' }
        Invoke-CnwRunner @('refresh-references','--run-id',$RunId,'--reason',$Reason)
    }
    'export' { if ($RunId) { Invoke-CnwRunner @('export','--run-id',$RunId) } else { Export-ReadingPackage | ConvertTo-Json -Depth 6 } }
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
