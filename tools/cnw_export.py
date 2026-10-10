"""Dynamic, payment-free reading/export package for a CNW run.

Reads the current run's v0/v1 prose, its private anchors and revision material,
and writes local HTML/Markdown/TXT under the private deliverables area. No
project-specific strings (思柔/书案/J19:555) are hard-coded; everything comes
from the run manifest and the frozen contract.
"""
from __future__ import annotations

import json
from pathlib import Path

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
    run_id = state["run_id"]
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
    before_anchor = contract["story"]["before_anchor"]
    after_anchor = contract["story"]["after_anchor"]
    files = {}
    (deliverables / "01_初稿.md").write_text(v0, encoding="utf-8")
    (deliverables / "02_修订稿.md").write_text(v1, encoding="utf-8")
    (deliverables / "04_修改说明.md").write_text(
        f"# 修改说明 — {unit['id']}\n\n- Run: `{run_id}`\n- Scene Cards: `artifacts/scene_cards.md`\n- Writing Brief: `artifacts/writing_brief.md`\n- 修订记录见 `artifacts/refine` 与 `09_revision`。\n",
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
        "tools/studio.ps1 show-run -RunId <new-run-id>\n"
        "tools/studio.ps1 verify-live -RunId <new-run-id>\n"
        "tools/studio.ps1 export -RunId <new-run-id>\n"
        "```\n",
        encoding="utf-8")

    reading_parts = []
    if before_anchor:
        reading_parts.append(f"<!-- 前文锚点 {before_anchor.get('scene')} 行 {before_anchor.get('source_line')}–{before_anchor.get('source_line_end')} -->")
    reading_parts.append(f"<!-- 插场开始 {unit['id']} -->")
    reading_parts.append(v1)
    reading_parts.append(f"<!-- 插场结束 {unit['id']} -->")
    if after_anchor:
        reading_parts.append(f"<!-- 后文锚点 {after_anchor.get('scene')} 行 {after_anchor.get('source_line')}–{after_anchor.get('source_line_end')} -->")
    reading = "\n\n".join(reading_parts) + "\n"
    (deliverables / "03_前后文连读.md").write_text(reading, encoding="utf-8")
    html = (
        "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
        f"<title>{_html_escape(unit['id'])} 前后文连读</title>"
        "<style>body{max-width:46rem;margin:2rem auto;font-family:serif;line-height:1.9;padding:0 1rem}"
        "p{margin:.6rem 0} .scene{border-left:3px solid #999;padding-left:1rem}</style></head><body>"
        f"<h1>{_html_escape(unit['id'])}</h1><div class=\"scene\">"
        + "".join(f"<p>{_html_escape(line)}</p>" for line in v1.splitlines() if line.strip())
        + "</div></body></html>\n"
    )
    (deliverables / "03_前后文连读.html").write_text(html, encoding="utf-8")
    (deliverables / "01_初稿.txt").write_text(v0, encoding="utf-8")
    (deliverables / "02_修订稿.txt").write_text(v1, encoding="utf-8")
    manifest = {"schema_version": "cnw_export_manifest_v1", "run_id": run_id, "work_id": unit["id"], "project_id": contract["project_id"], "files": sorted(p.name for p in deliverables.iterdir())}
    (deliverables / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "EXPORT_READY", "run_id": run_id, "deliverables": str(deliverables), "files": manifest["files"], "provider_call": "none"}
