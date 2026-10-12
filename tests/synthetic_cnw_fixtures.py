"""Self-contained fictional CNW v1 fixtures for offline compatibility tests."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def synthetic_work_unit(*, project_id="SYNTHETIC_PROJECT", unit_id="SYNTHETIC_SCENE",
                        characters=("甲", "乙", "丙", "丁"), minimum=1200, target=1500,
                        maximum=1800, language="zh-CN") -> dict:
    first = characters[0]
    return {
        "schema_version": "cnw_work_unit_v1", "project_id": project_id,
        "source": {"identity_type": "imported_project", "version": "SYNTHETIC-IMPORTED-v1",
                   "source_root": ".", "manifest_file": "_INBOX/source_manifest.json",
                   "import_id": "synthetic-source", "source_file_sha256": "0" * 64,
                   "source_manifest_sha256": "0" * 64},
        "unit": {"id": unit_id, "kind": "scene", "planning_mode": "author_plot",
                 "language": language, "pov": first, "target_visible_chars": target,
                 "min_visible_chars": minimum, "max_visible_chars": maximum,
                 "policy_sha256": "synthetic-policy-sha256",
                 "chapter_target_visible_chars": target,
                 "scenes": [{"id": "S1", "target_visible_chars": target}]},
        "story": {"source_file": "_INBOX/originals/synthetic.md",
                  "chapter_context": "A fictional test scene with a bounded source passage.",
                  "role_in_story": "Show one source-supported choice.",
                  "reader_reward": "Observe a small change in trust.",
                  "entry_state": "The issue is unsettled.", "exit_state": "The characters choose a next step.",
                  "before_anchor": {"scene": "synthetic", "source_line": 1, "sha256": "0" * 64},
                  "after_anchor": {"scene": "synthetic", "source_line": 2, "sha256": "0" * 64},
                  "required_beats": [
                      {"beat_id": "B01", "goal": "Ask a clear question.", "budget_visible_chars": target // 2},
                      {"beat_id": "B02", "goal": "Answer and choose a next step.", "budget_visible_chars": target - target // 2},
                  ], "characters_in_scene": list(characters),
                  "character_knowledge_boundary_ref": "90_canon/canon.md",
                  "forbidden_future_revelations": ["Do not invent a family relation or future secret."],
                  "voice_sample_refs": list(characters)},
        "review": {"workflow_template_git_blob": "synthetic-cnw-workflow",
                   "require_cnw_11_stages": True, "require_3_verifiers": True,
                   "require_completeness_critic": True, "require_re_review": True},
    }


def write_imported_v1_project(root: Path, *, project_id="SYNTHETIC_PROJECT", unit_id="SYNTHETIC_SCENE",
                              characters=("甲", "乙", "丙", "丁"), minimum=1200,
                              target=1500, maximum=1800, language="zh-CN") -> tuple[Path, dict]:
    root.mkdir(parents=True, exist_ok=True)
    source_relative = "_INBOX/originals/synthetic.md"
    source_path = root / source_relative
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_raw = "Before: a neighbor notices the open door.\nAfter: they agree to speak tomorrow.\n".encode("utf-8")
    source_path.write_bytes(source_raw)
    lines = source_raw.splitlines(keepends=True)
    manifest = {"schema_version": "synthetic_import_manifest_v1", "project_id": project_id,
                "import_id": sha(source_raw), "sources": [{"stored_path": source_relative,
                    "sha256": sha(source_raw), "format": "text"}]}
    manifest_raw = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    manifest_path = root / "_INBOX/source_manifest.json"
    manifest_path.write_bytes(manifest_raw)
    contract = synthetic_work_unit(project_id=project_id, unit_id=unit_id, characters=characters,
                                   minimum=minimum, target=target, maximum=maximum, language=language)
    contract["source"].update(import_id=manifest["import_id"], source_file_sha256=sha(source_raw),
                              source_manifest_sha256=sha(manifest_raw))
    contract["story"]["before_anchor"]["sha256"] = sha(lines[0])
    contract["story"]["after_anchor"]["sha256"] = sha(lines[1])
    contract_path = root / "contracts/synthetic_work_unit.json"
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_text(json.dumps(contract, ensure_ascii=False), encoding="utf-8")
    return contract_path, contract
