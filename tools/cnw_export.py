"""Dynamic, payment-free reading/export package for a CNW run.

Reads the current run's v0/v1 prose, its private anchors and revision material,
and writes local HTML/Markdown/TXT under the private deliverables area. No
project-specific strings (思柔/书案/J19:555) are hard-coded; everything comes
from the run manifest and the frozen contract.
"""
from __future__ import annotations

import json
import hashlib
import os
import tempfile
import uuid
from pathlib import Path
import re

try:
    from .cnw_contract import ContractError, SUPPORTED_LOCALE_MATRIX, load_contract
except ImportError:
    from cnw_contract import ContractError, SUPPORTED_LOCALE_MATRIX, load_contract

ROOT = Path(__file__).resolve().parents[1]


def _new_export_file(path: Path, raw: bytes, attempts: Path) -> None:
    """Publish one complete new file; retain failed write attempts separately."""
    if path.exists():
        if not path.is_file() or path.read_bytes() != raw:
            raise ContractError("INPUT_PACK_EXPORT_CHANGED", "bound export bytes changed; no overwrite")
        return
    with tempfile.NamedTemporaryFile(mode="wb", dir=attempts, delete=False, prefix="write-") as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        pending = Path(stream.name)
    pending.rename(path)


def _publish_job_export(destination: Path, outputs: dict[str, bytes], binding: dict) -> None:
    try:
        from .project_paths import _assert_no_reparse
    except ImportError:
        from project_paths import _assert_no_reparse
    _assert_no_reparse(destination, code="INPUT_PACK_EXPORT_UNSAFE")
    destination.parent.mkdir(parents=True, exist_ok=True)
    marker = ".story-studio-export.json"
    outputs[marker] = (json.dumps(binding, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    if destination.exists():
        if not destination.is_dir() or not (destination / marker).is_file():
            raise ContractError("INPUT_PACK_EXPORT_ALREADY_EXISTS", "unknown export directory retained")
        if {p.name for p in destination.iterdir()} != set(outputs):
            raise ContractError("INPUT_PACK_EXPORT_CHANGED", "bound export file set differs")
        for name, raw in outputs.items():
            path = destination / name
            _assert_no_reparse(path, code="INPUT_PACK_EXPORT_UNSAFE")
            if not path.is_file() or path.read_bytes() != raw:
                raise ContractError("INPUT_PACK_EXPORT_CHANGED", "bound export bytes differ; no overwrite")
        return
    digest = hashlib.sha256(outputs[marker]).hexdigest()
    staging = destination.with_name(f".{destination.name}.export-{digest}")
    attempts = staging.with_name(staging.name + ".write-attempts")
    for directory in (staging, attempts):
        _assert_no_reparse(directory, code="INPUT_PACK_EXPORT_UNSAFE")
        directory.mkdir(exist_ok=True)
    marker_path = staging / marker
    if any(staging.iterdir()) and (not marker_path.is_file() or marker_path.read_bytes() != outputs[marker]):
        raise ContractError("INPUT_PACK_EXPORT_BINDINGS_CHANGED", "staging transaction differs")
    _new_export_file(marker_path, outputs[marker], attempts)
    if {p.name for p in staging.iterdir()} - set(outputs):
        raise ContractError("INPUT_PACK_EXPORT_CHANGED", "unknown staging files retained")
    for name, raw in outputs.items():
        path = staging / name
        _assert_no_reparse(path, code="INPUT_PACK_EXPORT_UNSAFE")
        _new_export_file(path, raw, attempts)
    _assert_no_reparse(destination, code="INPUT_PACK_EXPORT_UNSAFE")
    staging.rename(destination)


def _read(run_dir: Path, relative: str) -> str:
    path = run_dir / relative
    if not path.is_file() or path.is_symlink():
        raise ContractError("EXPORT_ARTIFACT_MISSING", relative)
    return path.read_text(encoding="utf-8-sig")


def _html_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def export_reading_package(run_dir: str | Path, state: dict, *, project_root: str | Path, job_id: str | None = None) -> dict:
    run = Path(run_dir)
    project = Path(project_root)
    contract = load_contract(run / "artifacts/contract.json")
    unit = contract["unit"]
    if contract.get("schema_version") == "cnw_work_unit_v2":
        # New contracts must carry an explicit locale. Do not make an
        # incomplete v2 contract look valid by falling back to `language`.
        locale = unit.get("language_locale")
        if not isinstance(locale, str) or unit.get("language") != locale:
            raise ContractError("EXPORT_LOCALE_INVALID", str(locale))
    else:
        # Historical v1 contracts predate language_locale. Preserve the
        # original behavior of falling back to their declared language.
        locale = unit.get("language_locale", unit.get("language"))
    if not isinstance(locale, str) or not re.fullmatch(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", locale):
        raise ContractError("EXPORT_LOCALE_INVALID", str(locale))
    if contract.get("schema_version") == "cnw_work_unit_v2" and locale not in SUPPORTED_LOCALE_MATRIX:
        raise ContractError("EXPORT_LOCALE_UNSUPPORTED", locale)
    run_id = state["run_id"]
    if contract.get("schema_version") == "cnw_work_unit_v2":
        try:
            from .cnw_project import _registered_project_identity
        except ImportError:
            from cnw_project import _registered_project_identity
        project = project.resolve(strict=True)
        identity = _registered_project_identity(project)
        if (identity.get("project_id") != contract.get("project_id") or
                identity.get("project_instance_id") != contract.get("project_instance_id")):
            raise ContractError("PROJECT_INSTANCE_IDENTITY_MISMATCH", "export contract differs from the explicitly selected project")
        try:
            from .cnw_contract import validate_v2_source_identity
        except ImportError:
            from cnw_contract import validate_v2_source_identity
        validate_v2_source_identity(contract, source_root=project)
        deliverables = project / "deliverables" / identity["project_instance_id"] / run_id
    else:
        # Keep the historical v1 destination stable for existing workflows.
        deliverables = ROOT / "deliverables" / contract["project_id"] / run_id
    if job_id is not None:
        if contract.get("schema_version") != "cnw_work_unit_v2" or str(uuid.UUID(job_id)) != job_id:
            raise ContractError("INPUT_PACK_EXPORT_BINDINGS_CHANGED", "managed export requires a V2 job identity")
    else:
        deliverables.mkdir(parents=True, exist_ok=True)
    outputs = {}
    def emit(name: str, text: str):
        outputs[name] = text.encode("utf-8")

    def stage_text(stage: str) -> str:
        record = state["stages"].get(stage, {})
        artifact = record.get("artifact") or {}
        if not artifact.get("path"):
            return ""
        return (run / artifact["path"]).read_text(encoding="utf-8-sig")

    v0 = stage_text("prose")
    v1 = stage_text("refine") or v0
    scene_cards = stage_text("scene_cards")
    brief = stage_text("writing_brief")
    review_record = state["stages"].get("re_review", {})
    review_text = stage_text("re_review")
    review = json.loads(review_text) if review_text else {}
    cards_path = (state.get("stages", {}).get("scene_cards", {}).get("artifact") or {}).get("path", "NOT_MATERIALIZED")
    brief_path = (state.get("stages", {}).get("writing_brief", {}).get("artifact") or {}).get("path", "NOT_MATERIALIZED")
    refine_path = (state.get("stages", {}).get("refine", {}).get("artifact") or {}).get("path", "NOT_MATERIALIZED")
    reviewed = review_record.get("status") in ("STAGE_MATERIALIZED", "CONTROLLER_ACCEPTED") and review.get("status") in ("CLEAN", "NO_CHANGED_TEXT")
    candidate_status = "REVIEWED_CANDIDATE" if reviewed else "UNREVIEWED_CANDIDATE"
    execution = {"pipeline_status": state.get("status", "UNKNOWN"),
                 "re_review_status": review_record.get("status", "NOT_RUN"),
                 "candidate_status": candidate_status, "user_creative_accepted": False}
    try:
        from .cnw_contract import uses_advisory_length, validate_output_length
    except ImportError:
        from cnw_contract import uses_advisory_length, validate_output_length
    if uses_advisory_length(contract):
        execution.update(length_policy='ADVISORY', target_visible_chars=unit['target_visible_chars'],
                         actual_visible_chars=validate_output_length(contract, v1)['visible_chars'])
    if state.get("mode") == "offline" and contract.get("schema_version") == "cnw_work_unit_v2":
        receipts = state.get("provider_requests", [])
        simulated = bool(receipts) and all(row.get("mode") == "MOCK_ONLY" and row.get("simulation_status") == "SIMULATED"
                                          and row.get("fixture_only") is True for row in receipts)
        execution.update(execution_mode="MOCK_ONLY" if simulated else "OFFLINE_UNVERIFIED" if receipts else "OFFLINE_NOT_EXECUTED",
                         simulation_status="SIMULATED" if simulated else "NOT_VERIFIED" if receipts else "NOT_EXECUTED",
                         live_validation_status="NOT_LIVE_VALIDATED")
    emit("00_运行状态.md",
        "# 运行状态\n\n" + "\n".join(f"- {name}: `{value}`" for name, value in execution.items())
        + "\n\n导出是可读候选的保存，不代表完整工作流验收或用户创意接受。\n")
    before_anchor = contract.get("story", {}).get("before_anchor")
    after_anchor = contract.get("story", {}).get("after_anchor")
    before_text = after_text = ""
    selected_adapt_excerpt = None
    if contract["story"].get("source_file"):
        if contract.get("schema_version") == "cnw_work_unit_v2" and contract.get("work_intent") == "ADAPT_SOURCE":
            try:
                from .cnw_roles import read_production_preparation
            except ImportError:
                from cnw_roles import read_production_preparation
            prepared = read_production_preparation(project, contract)
            selected_adapt_excerpt = prepared["documents"].get("selected_source_excerpt")
            selection = contract["story"].get("source_selection", {})
            selected_hash = selection.get("wire_excerpt_sha256", selection.get("selected_sha256"))
            saved_path = run / "artifacts/production_preparation.json"
            if (not isinstance(selected_adapt_excerpt, str) or
                    prepared["source_hashes"].get("selected_source_excerpt") != selected_hash or
                    not saved_path.is_file() or saved_path.is_symlink()):
                raise ContractError("SOURCE_SELECTION_INVALID", "ADAPT export requires the frozen selected source excerpt")
            saved = json.loads(saved_path.read_text(encoding="utf-8"))
            if saved.get("documents", {}).get("selected_source_excerpt") != selected_adapt_excerpt:
                raise ContractError("SOURCE_SPAN_HASH_MISMATCH", "saved ADAPT excerpt differs from the selected source span")
        else:
            try:
                from .cnw_runner import _source_root
                from .cnw_contract import _safe_source_file, _validate_story_anchors
            except ImportError:
                from cnw_runner import _source_root
                from cnw_contract import _safe_source_file, _validate_story_anchors
            source_root = _source_root(contract, project)
            source = _safe_source_file(source_root, contract["story"]["source_file"])
            _validate_story_anchors(contract, source_root, source)
            lines = source.read_text(encoding="utf-8-sig").splitlines(keepends=True)
            def anchor_text(anchor):
                return "".join(lines[anchor["source_line"]-1:anchor.get("source_line_end", anchor["source_line"])]).strip()
            before_text, after_text = anchor_text(before_anchor), anchor_text(after_anchor)
    files = {}
    emit("01_初稿.md", v0)
    emit("02_修订稿.md", v1)
    emit("04_修改说明.md",
        f"# 修改说明 — {unit['id']}\n\n- Run: `{run_id}`\n- Scene Cards: `{cards_path}`\n- Writing Brief: `{brief_path}`\n- Refinement candidate: `{refine_path}`。\n")
    sources = "\n".join(f"- {key}: {value}" for key, value in contract["source"].items() if isinstance(value, str))
    emit("06_原作者方法覆盖报告.md",
        "# 原作者方法覆盖报告\n\n"
        "- CNW pin: 97ad71fe5e5e76a82275c6c63d4add06fb60ab6e\n"
        "- Workflow: plot → scene_cards → writing_brief → prose → lint_layer1 → lint_layer2 → multi_lens_review → adversarial_verify → completeness_critic → refine → re_review\n"
        "- 五 Lens: style / character / plot / canon / story_specific\n"
        "- 反证: correctness / character_consistency / continuity_plausibility\n"
        f"\n## 来源\n{sources}\n")
    if job_id is not None:
        emit("05_复用操作说明.md",
            "# 包任务恢复说明\n\n"
            "本次结果为 MOCK_ONLY / SIMULATED，NOT_LIVE_VALIDATED；Live 未授权。\n"
            "从应用仓库目录使用启动本任务时所选的 DataHome，重新打开同一包任务：\n\n"
            "```powershell\n"
            "$DataHome = '<启动本任务时所选 DataHome>'\n"
            f"$JobFile = Join-Path $DataHome 'shared/input_pack_jobs/{job_id}/result.json'\n"
            "tools/studio.ps1 project-pack -DataHome $DataHome -JobFile $JobFile -Offline -PrepareRuns\n"
            "tools/studio.ps1 project-pack -DataHome $DataHome -JobFile $JobFile -Offline -Mode offline -ExecuteJob\n"
            "```\n\n"
            "应用保留同一任务的合同、Run、阶段产物和失败历史，核验身份后恢复；"
            "无需手填合同、WorkId 或 RunId。已经完成的任务核验并复用现有成果。\n"
            "离线生成仅在明确的测试模拟传输环境中执行；普通离线入口不能自行调用模型。"
            "没有模拟传输时会保留任务并在 Provider 调用前拒绝。"
            "本说明不授予生产调用、费用或正文晋升权限。\n")
    else:
        emit("05_复用操作说明.md",
            "# 复用操作说明\n\n"
            "```powershell\n"
            f"tools/studio.ps1 produce -Mode live -ProjectRoot <project> -Contract <contract> -WorkId {unit['id']} -RunId <new-run-id>\n"
            "tools/studio.ps1 show-run -ProjectRoot <project> -RunId <new-run-id>\n"
            "tools/studio.ps1 verify-live -ProjectRoot <project> -RunId <new-run-id>\n"
            "tools/studio.ps1 export -ProjectRoot <project> -RunId <new-run-id>\n"
            "```\n")

    reading_parts = []
    intent = contract.get("work_intent")
    if intent == "ADAPT_SOURCE":
        if selected_adapt_excerpt:
            reading_parts.extend(("<!-- 选定来源片段 -->", selected_adapt_excerpt, "<!-- 改编稿开始 -->"))
        reading_parts.append(v1)
    elif intent == "ORIGINAL_EPISODE":
        reading_parts.append(v1)
    else:
        if before_anchor:
            reading_parts.append(f"<!-- 前文锚点 {before_anchor.get('scene')} 行 {before_anchor.get('source_line')}–{before_anchor.get('source_line_end')} -->")
            if before_text:
                reading_parts.append(before_text)
        reading_parts.append(f"<!-- 插场开始 {unit['id']} -->")
        reading_parts.append(v1)
        reading_parts.append(f"<!-- 插场结束 {unit['id']} -->")
        if after_anchor:
            reading_parts.append(f"<!-- 后文锚点 {after_anchor.get('scene')} 行 {after_anchor.get('source_line')}–{after_anchor.get('source_line_end')} -->")
            if after_text:
                reading_parts.append(after_text)
    reading = "\n\n".join(reading_parts) + "\n"
    emit("03_前后文连读.md", reading)
    html = (
        f"<!doctype html><html lang=\"{_html_escape(locale)}\"><head><meta charset=\"utf-8\">"
        f"<title>{_html_escape(unit['id'])} 前后文连读</title>"
        "<style>body{max-width:46rem;margin:2rem auto;font-family:serif;line-height:1.9;padding:0 1rem}"
        "p{margin:.6rem 0} .scene{border-left:3px solid #999;padding-left:1rem}</style></head><body>"
        f"<h1>{_html_escape(unit['id'])}</h1>"
        f"<p>候选状态：{candidate_status}；运行状态：{_html_escape(str(execution['pipeline_status']))}。导出不代表验收。</p>"
        + (f"<p>执行标记：{execution['execution_mode']} / {execution['simulation_status']}；NOT_LIVE_VALIDATED。</p>" if "execution_mode" in execution else "")
        + "".join(f"<p>{_html_escape(line)}</p>" for line in before_text.splitlines() if line.strip())
        + "<div class=\"scene\">"
        + "".join(f"<p>{_html_escape(line)}</p>" for line in v1.splitlines() if line.strip())
        + "</div>"
        + "".join(f"<p>{_html_escape(line)}</p>" for line in after_text.splitlines() if line.strip())
        + "</body></html>\n"
    )
    emit("03_前后文连读.html", html)
    emit("01_初稿.txt", v0)
    emit("02_修订稿.txt", v1)
    if job_id is not None:
        binding = {"schema_version": "cnw_package_export_transaction_v1", "job_id": job_id,
                   "project_instance_id": contract["project_instance_id"], "run_id": run_id,
                   "contract_sha256": state["contract_sha256"], "destination": str(deliverables),
                   "stages": {name: {"artifact": row["artifact"], "execution_identity": row["execution_identity"]}
                              for name, row in state["stages"].items()}}
        manifest = {"schema_version": "cnw_export_manifest_v1", "run_id": run_id, "work_id": unit["id"],
                    "project_id": contract["project_id"], **execution, "export_transaction": binding,
                    "file_sha256": {name: hashlib.sha256(raw).hexdigest() for name, raw in outputs.items()},
                    "files": sorted([*outputs, "manifest.json", ".story-studio-export.json"])}
        emit("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        _publish_job_export(deliverables, outputs, binding)
    else:
        for name, raw in outputs.items():
            (deliverables / name).write_text(raw.decode("utf-8"), encoding="utf-8")
        manifest = {"schema_version": "cnw_export_manifest_v1", "run_id": run_id, "work_id": unit["id"], "project_id": contract["project_id"], **execution, "files": sorted(p.name for p in deliverables.iterdir())}
        (deliverables / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "EXPORT_READY", "run_id": run_id, **execution, "deliverables": str(deliverables), "files": manifest["files"], "provider_call": "none"}
