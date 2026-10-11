"""Dynamic, payment-free reading/export package for a CNW run.

Reads the current run's v0/v1 prose, its private anchors and revision material,
and writes local HTML/Markdown/TXT under the private deliverables area. No
project-specific strings (思柔/书案/J19:555) are hard-coded; everything comes
from the run manifest and the frozen contract.
"""
from __future__ import annotations

import json
from pathlib import Path
import re

try:
    from .cnw_contract import ContractError, load_contract
except ImportError:
    from cnw_contract import ContractError, load_contract

ROOT = Path(__file__).resolve().parents[1]


def _read(run_dir: Path, relative: str) -> str:
    path = run_dir / relative
    if not path.is_file() or path.is_symlink():
        raise ContractError("EXPORT_ARTIFACT_MISSING", relative)
    return path.read_text(encoding="utf-8-sig")


def _html_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def export_reading_package(run_dir: str | Path, state: dict, *, project_root: str | Path) -> dict:
    run = Path(run_dir)
    project = Path(project_root)
    contract = load_contract(run / "artifacts/contract.json")
    unit = contract["unit"]
    locale = unit.get("language_locale", unit.get("language"))
    if not isinstance(locale, str) or not re.fullmatch(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", locale):
        raise ContractError("EXPORT_LOCALE_INVALID", str(locale))
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
    deliverables.mkdir(parents=True, exist_ok=True)

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
    (deliverables / "00_运行状态.md").write_text(
        "# 运行状态\n\n" + "\n".join(f"- {name}: `{value}`" for name, value in execution.items())
        + "\n\n导出是可读候选的保存，不代表完整工作流验收或用户创意接受。\n", encoding="utf-8")
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
    (deliverables / "01_初稿.md").write_text(v0, encoding="utf-8")
    (deliverables / "02_修订稿.md").write_text(v1, encoding="utf-8")
    (deliverables / "04_修改说明.md").write_text(
        f"# 修改说明 — {unit['id']}\n\n- Run: `{run_id}`\n- Scene Cards: `{cards_path}`\n- Writing Brief: `{brief_path}`\n- Refinement candidate: `{refine_path}`。\n",
        encoding="utf-8")
    sources = "\n".join(f"- {key}: {value}" for key, value in contract["source"].items() if isinstance(value, str))
    (deliverables / "06_原作者方法覆盖报告.md").write_text(
        "# 原作者方法覆盖报告\n\n"
        "- CNW pin: 97ad71fe5e5e76a82275c6c63d4add06fb60ab6e\n"
        "- Workflow: plot → scene_cards → writing_brief → prose → lint_layer1 → lint_layer2 → multi_lens_review → adversarial_verify → completeness_critic → refine → re_review\n"
        "- 五 Lens: style / character / plot / canon / story_specific\n"
        "- 反证: correctness / character_consistency / continuity_plausibility\n"
        f"\n## 来源\n{sources}\n",
        encoding="utf-8")
    (deliverables / "05_复用操作说明.md").write_text(
        "# 复用操作说明\n\n"
        "```powershell\n"
        f"tools/studio.ps1 produce -Mode live -ProjectRoot <project> -Contract <contract> -WorkId {unit['id']} -RunId <new-run-id>\n"
        "tools/studio.ps1 show-run -ProjectRoot <project> -RunId <new-run-id>\n"
        "tools/studio.ps1 verify-live -ProjectRoot <project> -RunId <new-run-id>\n"
        "tools/studio.ps1 export -ProjectRoot <project> -RunId <new-run-id>\n"
        "```\n",
        encoding="utf-8")

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
    (deliverables / "03_前后文连读.md").write_text(reading, encoding="utf-8")
    html = (
        f"<!doctype html><html lang=\"{_html_escape(locale)}\"><head><meta charset=\"utf-8\">"
        f"<title>{_html_escape(unit['id'])} 前后文连读</title>"
        "<style>body{max-width:46rem;margin:2rem auto;font-family:serif;line-height:1.9;padding:0 1rem}"
        "p{margin:.6rem 0} .scene{border-left:3px solid #999;padding-left:1rem}</style></head><body>"
        f"<h1>{_html_escape(unit['id'])}</h1>"
        f"<p>候选状态：{candidate_status}；运行状态：{_html_escape(str(execution['pipeline_status']))}。导出不代表验收。</p>"
        + "".join(f"<p>{_html_escape(line)}</p>" for line in before_text.splitlines() if line.strip())
        + "<div class=\"scene\">"
        + "".join(f"<p>{_html_escape(line)}</p>" for line in v1.splitlines() if line.strip())
        + "</div>"
        + "".join(f"<p>{_html_escape(line)}</p>" for line in after_text.splitlines() if line.strip())
        + "</body></html>\n"
    )
    (deliverables / "03_前后文连读.html").write_text(html, encoding="utf-8")
    (deliverables / "01_初稿.txt").write_text(v0, encoding="utf-8")
    (deliverables / "02_修订稿.txt").write_text(v1, encoding="utf-8")
    manifest = {"schema_version": "cnw_export_manifest_v1", "run_id": run_id, "work_id": unit["id"], "project_id": contract["project_id"], **execution, "files": sorted(p.name for p in deliverables.iterdir())}
    (deliverables / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "EXPORT_READY", "run_id": run_id, **execution, "deliverables": str(deliverables), "files": manifest["files"], "provider_call": "none"}
