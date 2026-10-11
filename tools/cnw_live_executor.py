"""Execute and validate one frozen W10 provider request from a private run."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

try:
    from .cnw_contract import ContractError, load_contract
    from .cnw_generate import validate_generated_scene
    from .cnw_live_provider import accept_validated_stage, complete, safe_run
    from .cnw_roles import validate_role_output
    from .cnw_runner import load_state, safe_run_input, validate_literary_source_freeze
except ImportError:
    from cnw_contract import ContractError, load_contract
    from cnw_generate import validate_generated_scene
    from cnw_live_provider import accept_validated_stage, complete, safe_run
    from cnw_roles import validate_role_output
    from cnw_runner import load_state, safe_run_input, validate_literary_source_freeze

try:
    from .cnw_live_provider import record_nk_pov_receipt
    from . import p2_cost_guard
except ImportError:
    from cnw_live_provider import record_nk_pov_receipt
    import p2_cost_guard


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


ROLE_STAGE = {"plot": "plot", "cards": "cards", "brief": "brief", "prose": "draft"}
REVIEW_ROLES = {
    "lens5": ("style", "character", "plot", "canon", "story_specific"),
    "verifier3": ("verifier_1", "verifier_2", "verifier_3"),
    "completeness": (None,),
    "refine": (None,),
    "re-review": ("style", "character", "plot", "canon", "story_specific"),
}
LENS_SOURCES = {
    "style": ("style_guide", "language_rules"),
    "character": ("character_bible", "voice_samples", "address_terms"),
    "plot": ("plot", "scene_cards", "brief"),
    "canon": ("canon", "source_anchors", "knowledge_boundaries"),
    "story_specific": ("story_contract", "canon", "brief"),
}


def _support_integration_mode(contract: dict, name: str) -> str:
    """Use opt-in v2 integrations while preserving frozen v1 behavior."""
    if contract.get("schema_version") != "cnw_work_unit_v2":
        return "ENABLED"
    integrations = contract.get("integrations", {})
    mode = integrations.get(name, "DISABLED") if isinstance(integrations, dict) else None
    if mode not in {"DISABLED", "ENABLED"}:
        raise ContractError("SUPPORT_INTEGRATION_CONFIG_INVALID", f"integrations.{name}")
    return mode


def prepare_role_request(run_dir: str | Path, project_root: str | Path, *, role: str,
                         inputs: dict[str, str | Path], preflight_path: str | Path) -> dict:
    run = safe_run(run_dir)
    if role not in ROLE_STAGE:
        raise ContractError("LIVE_ROLE_INVALID", role)
    project = Path(project_root).resolve(strict=True)
    state = load_state(run)
    contract_path = (project / state["contract_path"]).resolve(strict=True)
    contract = load_contract(contract_path)
    stage = ROLE_STAGE[role]
    stage_record = state.get("stages", {}).get(stage, {})
    try:
        from .cnw_roles import build_role_packet, _read_project_file
    except ImportError:
        from cnw_roles import build_role_packet, _read_project_file
    if (state.get("mode") != "live" or state.get("fixture_only") is not False
            or stage_record.get("status") != "READY_FOR_EXECUTION"):
        raise ContractError("LIVE_STAGE_NOT_READY", stage)
    if role == "brief" and _support_integration_mode(contract, "nk") == "ENABLED":
        pov_record = state.get("stages", {}).get("pov", {})
        if pov_record.get("status") != "ACCEPTED" or not pov_record.get("artifact"):
            raise ContractError("LIVE_BRIEF_POV_NOT_ACCEPTED", "brief requires this run's accepted NK POV")
        pov_artifact_path = safe_run_input(run / pov_record["artifact"]["path"], run)
        pov_artifact = json.loads(pov_artifact_path.read_text(encoding="utf-8"))
        pov_content = pov_artifact.get("content")
        receipts = [row for row in state.get("provider_requests", []) if row.get("stage") == "pov"]
        if (not isinstance(pov_content, str) or len(receipts) != 1
                or digest(pov_artifact_path.read_bytes()) != pov_record["artifact"]["sha256"]
                or digest(pov_content.encode("utf-8")) != receipts[0].get("output_sha256")):
            raise ContractError("LIVE_BRIEF_POV_BINDING_INVALID", run.name)
        try:
            response = json.loads(pov_content)
            from .cnw_nk_adapter import map_reflection_to_brief
        except (json.JSONDecodeError, ImportError) as exc:
            if isinstance(exc, json.JSONDecodeError):
                raise ContractError("LIVE_BRIEF_POV_BINDING_INVALID", "NK content is not JSON") from exc
            from cnw_nk_adapter import map_reflection_to_brief
        pov_receipt = receipts[0]
        nk_map_receipt = {"status": "LIVE_ACCEPTED", "request_id": pov_receipt["request_id"],
            "provider_request_id": pov_receipt["provider_request_id"], "model": pov_receipt["model"],
            "finish_reason": pov_receipt["finish_reason"], "usage": pov_receipt["usage"],
            "http_status": pov_receipt["http_status"], "validated_response_sha256": digest(
                json.dumps(response, ensure_ascii=False, sort_keys=True).encode("utf-8")),
            "raw_response_sha256": pov_receipt["raw_response_sha256"]}
        mapped_reflection, _mapping = map_reflection_to_brief("", response, nk_map_receipt)
        context_dir = run / "artifacts/context"
        context_dir.mkdir(parents=True, exist_ok=True)
        nk_path = context_dir / "nk-reflection.md"
        if nk_path.exists() and nk_path.read_text(encoding="utf-8") != mapped_reflection:
            raise ContractError("LIVE_NK_REFLECTION_COLLISION", run.name)
        if not nk_path.exists():
            nk_path.write_text(mapped_reflection, encoding="utf-8")
        if "nk_reflection" in inputs:
            supplied_path, supplied_text = _read_project_file(inputs["nk_reflection"], project)
            if supplied_text.strip() != mapped_reflection.strip():
                raise ContractError("LIVE_NK_REFLECTION_SOURCE_MISMATCH", str(supplied_path))
        inputs = {**inputs, "nk_reflection": nk_path}
    elif role == "brief" and "nk_reflection" in inputs:
        raise ContractError("LIVE_NK_DISABLED_INPUT_FORBIDDEN", "NK is disabled for this contract")
    try:
        from .cnw_w10_policy import verify_preflight_file
    except ImportError:
        from cnw_w10_policy import verify_preflight_file
    preflight, preflight_sha = verify_preflight_file(
        preflight_path, contract_path, run_dir=run, project_root=project)
    role_packet = build_role_packet(role, contract_path, inputs,
        accepted_receipts=state.get("role_receipts", []), mode="live", w10_preflight=preflight)
    user_packet = {key: value for key, value in role_packet.items() if key != "prompt"}
    messages = [{"role": "system", "content": role_packet["prompt"]},
                {"role": "user", "content": json.dumps(user_packet, ensure_ascii=False, sort_keys=True)}]
    output = {"schema_version": "cnw_live_stage_request_v1", "builder_id": "cnw_roles.build_role_packet",
        "role": role, "stage": stage, "role_id": None, "run_id": run.name,
        "contract_sha256": state["contract_sha256"], "stage_fingerprint": stage_record["fingerprint"],
        "preflight_path": str(Path(preflight_path).resolve(strict=True)),
        "preflight_evidence_sha256": preflight_sha, "project_root": str(project),
        "input_paths": {key: str(Path(value).resolve(strict=True)) for key, value in inputs.items()},
        "role_packet_sha256": digest(json.dumps(role_packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")),
        "messages": messages, "fixture_only": False}
    output["input_sha256"] = digest(json.dumps(messages, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    target = run / "artifacts" / "requests" / f"{stage}-{stage_record['fingerprint'][:12]}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink():
        raise ContractError("LIVE_STAGE_PACKET_COLLISION", stage)
    encoded = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    if target.exists():
        if target.read_text(encoding="utf-8") != encoded:
            raise ContractError("LIVE_STAGE_PACKET_COLLISION", stage)
    else:
        target.write_text(encoded, encoding="utf-8")
    return {"status": "LIVE_STAGE_PACKET_READY", "stage": stage,
            "packet": target.relative_to(run).as_posix(), "packet_sha256": digest(target.read_bytes()),
            "input_sha256": output["input_sha256"], "provider_call": "none"}


def build_review_request(run: Path, stage: str, role_id: str | None) -> dict:
    """Build a deterministic, run-bound packet for review and revision roles."""
    state = load_state(run)
    validate_literary_source_freeze(state, run.parent.parent)
    stage_record = state.get("stages", {}).get(stage, {})
    if stage not in REVIEW_ROLES or stage_record.get("status") != "READY_FOR_EXECUTION":
        raise ContractError("LIVE_REVIEW_STAGE_NOT_READY", stage)
    allowed_role_ids = (tuple(stage_record.get("expected_role_ids", [])) if stage == "re-review"
                        else REVIEW_ROLES[stage])
    if role_id not in allowed_role_ids:
        raise ContractError("LIVE_REVIEW_ROLE_INVALID", f"{stage}:{role_id}")
    contract = load_contract(run / "artifacts/contract.json")
    prose_stage = "refine" if stage == "re-review" else "draft"
    prose_file = run / f"artifacts/stages/{prose_stage}-prose.md"
    if not prose_file.is_file() or prose_file.is_symlink():
        raise ContractError("LIVE_REVIEW_PROSE_MISSING", prose_stage)
    prose = prose_file.read_text(encoding="utf-8")
    inputs = {"contract": state["contract_sha256"], "prose": digest(prose_file.read_bytes())}
    context = {"unit": contract["unit"], "prose": prose}
    project_root = run.parent.parent
    source = contract["source"]
    try:
        from .cnw_contract import validate_source_identity
    except ImportError:
        from cnw_contract import validate_source_identity
    if source.get("identity_type") == "imported_project":
        release_root = (project_root / source.get("source_root", ".")).resolve(strict=True)
        expected_id = source["import_id"]
        expected_manifest = source["source_manifest_sha256"]
    else:
        release_root = ROOT / "inputs/private/release" / source["zip_sha256"].lower() / "Cangqi_Jun_Release_2_3"
        expected_id = source["zip_sha256"]
        expected_manifest = source["local_private_source_manifest_sha256"]
    validate_source_identity(contract, source_root=release_root,
        expected_version=source["version"], expected_zip_sha256=expected_id,
        expected_manifest_sha256=expected_manifest)
    script_path = (release_root / contract["story"]["source_file"]).resolve(strict=True)
    source_lines = script_path.read_text(encoding="utf-8-sig").splitlines()
    anchor_start = int(contract["story"]["before_anchor"]["source_line_end"])
    anchor_end = int(contract["story"]["after_anchor"]["source_line_end"])
    anchors = "\n".join(f"{number}: {source_lines[number - 1]}" for number in range(anchor_start, anchor_end + 1))
    fixed_sources = {
        "style_guide": project_root / "92_style_engine/style_guide.md",
        "language_rules": project_root / "92_style_engine/forbidden_patterns.md",
        "character_bible": project_root / "90_canon/character_bible.md",
        "voice_samples": project_root / "92_style_engine/character_voice_samples.md",
        "address_terms": project_root / "90_canon/glossary.md",
        "canon": project_root / "90_canon/canon.md",
        "knowledge_boundaries": project_root / "90_canon/character_bible.md",
    }
    sources = {}
    for name, file in fixed_sources.items():
        if not file.is_file() or file.is_symlink():
            raise ContractError("LIVE_REVIEW_SOURCE_MISSING", name)
        raw = file.read_bytes()
        sources[name] = file.read_text(encoding="utf-8-sig")
        inputs[name] = digest(raw)
    sources["source_anchors"] = anchors
    inputs["source_anchors"] = digest(anchors.encode("utf-8"))
    sources["story_contract"] = json.dumps(contract, ensure_ascii=False, sort_keys=True)
    inputs["story_contract"] = state["contract_sha256"]
    for stage_name, source_name in (("plot", "plot"), ("cards", "scene_cards"), ("brief", "brief")):
        record = state["stages"].get(stage_name, {})
        if record.get("status") != "ACCEPTED":
            continue
        artifact = record.get("artifact", {})
        file = safe_run_input(run / artifact.get("path", ""), run)
        raw = file.read_bytes()
        if digest(raw) != artifact.get("sha256"):
            raise ContractError("LIVE_REVIEW_DEPENDENCY_HASH_MISMATCH", stage_name)
        sources[source_name] = json.loads(raw.decode("utf-8"))["content"]
        inputs[source_name] = digest(sources[source_name].encode("utf-8"))
    lens_sources = LENS_SOURCES.get(role_id or "")
    if stage in {"lens5", "re-review"}:
        if not lens_sources:
            raise ContractError("LIVE_REVIEW_ROLE_INVALID", str(role_id))
        context["sources"] = {name: sources[name] for name in lens_sources}
    else:
        context["sources"] = sources
    for dep in ("brief", "lint1", "lint2", "lens5", "verifier3", "completeness"):
        record = state["stages"].get(dep, {})
        if record.get("status") != "ACCEPTED":
            continue
        artifact = record.get("artifact", {})
        file = safe_run_input(run / artifact.get("path", ""), run)
        raw = file.read_bytes()
        if digest(raw) != artifact.get("sha256"):
            raise ContractError("LIVE_REVIEW_DEPENDENCY_HASH_MISMATCH", dep)
        inputs[dep] = digest(raw)
        context[dep] = json.loads(raw.decode("utf-8"))
    prior_findings = []
    lens_record = state["stages"].get("lens5", {})
    for lens_id, entry in sorted(lens_record.get("role_artifacts", {}).items()):
        lens_file = safe_run_input(run / entry["path"], run)
        lens_raw = lens_file.read_bytes()
        if digest(lens_raw) != entry.get("sha256"):
            raise ContractError("LIVE_REVIEW_DEPENDENCY_HASH_MISMATCH", f"lens5:{lens_id}")
        artifact = json.loads(lens_raw.decode("utf-8"))
        parsed = json.loads(artifact["content"])
        prior_findings.extend({**finding, "lens_id": lens_id} for finding in parsed.get("findings", []))
        inputs[f"lens5:{lens_id}"] = digest(lens_raw)
    if prior_findings:
        context["prior_findings"] = prior_findings
    role_name = role_id or "completeness"
    if stage in {"lens5", "re-review"}:
        lens_goal = {
            "style": "检查语言、节奏、可读性、重复和场景呈现。",
            "character": "检查人物声音区分、台词行为一致性及知识边界。",
            "plot": "检查场景卡动作、阻碍、回应、结果及与前后锚衔接。",
            "canon": "只用给定原稿锚、Canon 与知识边界核验事实，不把推断当事实。",
            "story_specific": "检查本合同的玩家选择开放性、场景功能、戏剧体验和禁区。",
        }[role_name]
        instruction = f"你是独立的 {role_name} Lens。{lens_goal}只使用 sources 中本岗位列出的来源和完整 prose。给出可定位的问题，不写泛泛建议。输出 JSON：{{\"lens_id\":\"{role_name}\",\"findings\":[{{\"finding_id\":\"F1\",\"severity\":\"major|minor\",\"evidence\":\"原文短引\",\"issue\":\"具体问题\",\"recommendation\":\"可执行修改\"}}]}}。无问题时 findings 为空。"
    elif stage == "verifier3":
        instruction = f"你是 {role_name}。核验已提供的审稿 findings 是否被证据支持。输出 JSON：{{\"verifier_id\":\"{role_name}\",\"votes\":[{{\"finding_id\":\"F1\",\"verdict\":\"not_refuted|refuted|uncertain\",\"evidence\":\"证据说明\"}}]}}。不得添加新 finding。"
    elif stage == "completeness":
        instruction = "你是完整性审稿人。逐段检查正文及合同 beat，输出 JSON：{\"inspected_full_text_sha256\":\"正文 SHA256\",\"candidate_findings\":[{\"finding_id\":\"C1\",\"issue\":\"缺口\",\"evidence\":\"正文证据\"}]}。候选不等于已确认缺陷。"
    elif stage == "refine":
        instruction = "根据合同、正文和已接受的审稿意见修订整场正文。只输出 JSON：{\"prose\":\"完整修订正文\",\"beat_evidence\":{},\"dialogue_evidence\":{},\"action_evidence\":{},\"start_state_evidence\":\"...\",\"end_state_evidence\":\"...\"}。保留有效戏剧内容，满足合同篇幅。"
    else:
        raise ContractError("LIVE_REVIEW_ROLE_INVALID", stage)
    messages = [{"role": "system", "content": instruction},
                {"role": "user", "content": json.dumps(context, ensure_ascii=False, sort_keys=True)}]
    canonical = json.dumps(messages, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"schema_version": "cnw_live_stage_request_v1", "builder_id": "cnw_live_executor.build_review_request",
        "role": role_name, "stage": stage, "role_id": role_id, "run_id": run.name,
        "contract_sha256": state["contract_sha256"], "stage_fingerprint": stage_record["fingerprint"],
        "context_hashes": inputs, "messages": messages, "input_sha256": digest(canonical), "fixture_only": False}


def prepare_review_request(run_dir: str | Path, *, stage: str, role_id: str | None) -> dict:
    run = safe_run(run_dir)
    packet = build_review_request(run, stage, role_id)
    target = run / "artifacts/requests" / f"{stage}-{role_id or 'default'}-{packet['stage_fingerprint'][:12]}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(packet, ensure_ascii=False, indent=2) + "\n"
    if target.exists() and target.read_text(encoding="utf-8") != encoded:
        raise ContractError("LIVE_STAGE_PACKET_COLLISION", stage)
    if not target.exists():
        target.write_text(encoded, encoding="utf-8")
    return {"status": "LIVE_STAGE_PACKET_READY", "stage": stage, "role_id": role_id,
            "packet": target.relative_to(run).as_posix(), "packet_sha256": digest(target.read_bytes()),
            "input_sha256": packet["input_sha256"], "provider_call": "none"}


def _validate(stage: str, role_id: str | None, contract: dict, content: str) -> tuple[dict, str]:
    if stage in {"plot", "cards", "brief"}:
        validate_role_output(stage, contract, content)
        return {"status": "ROLE_OUTPUT_VALID", "validator": "cnw_roles.validate_role_output"}, content
    if stage in {"draft", "refine"}:
        try:
            result = json.loads(content)
            prose = result["prose"]
            validation = validate_generated_scene(contract, prose,
                finish_reason="stop", beat_evidence=result["beat_evidence"],
                dialogue_evidence=result["dialogue_evidence"],
                action_evidence=result["action_evidence"],
                start_state_evidence=result["start_state_evidence"],
                end_state_evidence=result["end_state_evidence"])
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ContractError("LIVE_SCENE_OUTPUT_SCHEMA_INVALID", stage) from exc
        if validation["status"] != "CONTENT_VALID":
            raise ContractError("LIVE_SCENE_CONTENT_RETURN", json.dumps(validation, ensure_ascii=False))
        return {"status": "CONTENT_VALID", "validator": "cnw_generate.validate_generated_scene",
                "evidence": {key: value for key, value in result.items() if key != "prose"},
                "content_validation": validation}, prose
    if stage in {"lens5", "verifier3", "completeness", "re-review"}:
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ContractError("LIVE_REVIEW_OUTPUT_NOT_JSON", stage) from exc
        if stage in {"lens5", "re-review"}:
            if parsed.get("lens_id") != role_id or not isinstance(parsed.get("findings"), list):
                raise ContractError("LIVE_LENS_OUTPUT_INVALID", str(role_id))
            finding_ids = [row.get("finding_id") for row in parsed["findings"] if isinstance(row, dict)]
            if (len(finding_ids) != len(parsed["findings"]) or len(set(finding_ids)) != len(finding_ids)
                    or any(not all(isinstance(row.get(key), str) and row[key].strip()
                                   for key in ("finding_id", "severity", "evidence", "issue", "recommendation"))
                           or row.get("severity") not in {"major", "minor"} for row in parsed["findings"])):
                raise ContractError("LIVE_LENS_FINDINGS_INVALID", str(role_id))
        elif stage == "verifier3":
            if parsed.get("verifier_id") != role_id or not isinstance(parsed.get("votes"), list):
                raise ContractError("LIVE_VERIFIER_OUTPUT_INVALID", str(role_id))
            finding_ids = [row.get("finding_id") for row in parsed["votes"] if isinstance(row, dict)]
            if len(finding_ids) != len(parsed["votes"]) or len(finding_ids) != len(set(finding_ids)):
                raise ContractError("LIVE_VERIFIER_VOTES_INVALID", str(role_id))
            if any(row.get("verdict") not in {"not_refuted", "refuted", "uncertain"} for row in parsed["votes"]):
                raise ContractError("LIVE_VERIFIER_VOTES_INVALID", str(role_id))
        elif stage == "completeness":
            if not isinstance(parsed.get("candidate_findings"), list) or not parsed.get("inspected_full_text_sha256"):
                raise ContractError("LIVE_COMPLETENESS_OUTPUT_INVALID", "full-text hash and candidate_findings are required")
        return {"status": "REVIEW_COMPLETED", "validator": "cnw_live_executor.schema"}, content
    raise ContractError("LIVE_STAGE_INVALID", stage)


def execute(run_dir: str | Path, *, stage: str, packet_path: str | Path,
            input_token_cap: int, output_token_cap: int, role_id: str | None = None,
            transport=None) -> dict:
    run = safe_run(run_dir)
    packet_value = Path(packet_path)
    packet_file = safe_run_input(packet_value if packet_value.is_absolute() else run / packet_value, run)
    try:
        packet = json.loads(packet_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError("LIVE_STAGE_PACKET_INVALID", str(packet_file)) from exc
    if (packet.get("schema_version") != "cnw_live_stage_request_v1"
            or packet.get("stage") != stage or packet.get("role_id") != role_id
            or not isinstance(packet.get("messages"), list)
            or packet.get("fixture_only") is not False):
        raise ContractError("LIVE_STAGE_PACKET_BINDING_MISMATCH", stage)
    state = load_state(run)
    stage_record = state.get("stages", {}).get(stage, {})
    if (packet.get("run_id") != run.name or packet.get("contract_sha256") != state.get("contract_sha256")
            or packet.get("stage_fingerprint") != stage_record.get("fingerprint")
            or stage_record.get("status") != "READY_FOR_EXECUTION"):
        raise ContractError("LIVE_STAGE_PACKET_STALE", stage)
    if packet.get("builder_id") == "cnw_live_executor.build_review_request":
        rebuilt = build_review_request(run, stage, role_id)
        if packet != rebuilt:
            raise ContractError("LIVE_REVIEW_PACKET_REBUILD_MISMATCH", stage)
    elif packet.get("builder_id") == "cnw_roles.build_role_packet":
        role = packet.get("role")
        if ROLE_STAGE.get(role) != stage:
            raise ContractError("LIVE_STAGE_PACKET_BINDING_MISMATCH", stage)
        inputs = packet.get("input_paths")
        if not isinstance(inputs, dict) or not inputs:
            raise ContractError("LIVE_STAGE_PACKET_INVALID", "role input paths are required")
        rebuilt = prepare_role_request(run, packet["project_root"], role=role,
            inputs=inputs, preflight_path=packet["preflight_path"])
        rebuilt_path = run / rebuilt["packet"]
        if (rebuilt_path.resolve() != packet_file.resolve()
                or digest(rebuilt_path.read_bytes()) != packet.get("packet_sha256")):
            raise ContractError("LIVE_STAGE_PACKET_REBUILD_MISMATCH", stage)
        os.environ["STORYSTUDIO_W10_PREFLIGHT_PATH"] = packet["preflight_path"]
    else:
        raise ContractError("LIVE_STAGE_PACKET_BUILDER_UNTRUSTED", str(packet.get("builder_id")))
    contract_path = run / "artifacts/contract.json"
    contract = load_contract(contract_path)
    messages = packet["messages"]
    input_sha = digest(json.dumps(messages, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    content, receipt = complete(run, stage=stage, role_id=role_id, messages=messages,
        input_sha256=input_sha, input_token_cap=input_token_cap,
        output_token_cap=output_token_cap, transport=transport)
    validation, artifact_content = _validate(stage, role_id, contract, content)
    if stage in {"lens5", "verifier3", "completeness", "re-review"}:
        context = json.loads(packet["messages"][1]["content"])
        parsed = json.loads(content)
        if stage == "verifier3":
            expected_ids = {row["finding_id"] for row in context.get("prior_findings", [])}
            vote_ids = {row["finding_id"] for row in parsed.get("votes", [])}
            if vote_ids != expected_ids:
                raise ContractError("LIVE_VERIFIER_COVERAGE_INVALID", str(role_id))
        if stage == "completeness":
            expected_full_text = digest(context["prose"].encode("utf-8"))
            if parsed.get("inspected_full_text_sha256") != expected_full_text:
                raise ContractError("LIVE_COMPLETENESS_TEXT_HASH_MISMATCH", stage)
    if stage in {"plot", "cards", "brief", "draft"}:
        pending = {"stage": stage, "role": packet.get("role"), "role_id": role_id,
            "request_id": receipt["request_id"], "provider_request_id": receipt["provider_request_id"],
            "packet_path": packet_file.relative_to(run).as_posix(), "content": content,
            "artifact_content": artifact_content, "validation": validation,
            "content_sha256": digest(content.encode("utf-8")),
            "artifact_content_sha256": digest(artifact_content.encode("utf-8"))}
        try:
            from . import cnw_runner as runner
        except ImportError:
            import cnw_runner as runner
        with runner.locked_run(run):
            current = runner.load_state(run)
            if current["stages"][stage].get("status") != "READY_FOR_EXECUTION":
                raise ContractError("LIVE_STAGE_NOT_READY", stage)
            current.setdefault("pending_role_outputs", {})[stage] = pending
            current["updated_at"] = runner.now()
            runner.save_state(run, current)
        return {"status": "PROVIDER_RESULT_PENDING_CONTROLLER_ACCEPTANCE", "run_id": run.name,
            "stage": stage, "role": packet.get("role"), "request_id": receipt["request_id"],
            "output_sha256": pending["content_sha256"], "provider_call": "performed"}
    acceptance = accept_validated_stage(run, stage=stage, content=content,
        validation=validation, role_id=role_id)
    return {"status": acceptance["status"], "run_id": run.name, "stage": stage,
            "role_id": role_id, "request_id": receipt["request_id"],
            "provider_request_id": receipt["provider_request_id"],
            "input_sha256": receipt["input_sha256"], "output_sha256": receipt["output_sha256"],
            "validation": validation, "artifact": acceptance.get("artifact")}


def accept_controller_role_output(run_dir: str | Path, *, stage: str, evidence_path: str | Path) -> dict:
    if stage not in {"plot", "cards", "brief", "draft"}:
        raise ContractError("CONTROLLER_ACCEPTANCE_ARGUMENT_INVALID", stage)
    run = safe_run(run_dir)
    state = load_state(run)
    pending = state.get("pending_role_outputs", {}).get(stage)
    if not isinstance(pending, dict):
        raise ContractError("CONTROLLER_PENDING_ROLE_OUTPUT_MISSING", stage)
    project_root = run.parent.parent
    supplied_evidence = Path(evidence_path).absolute()
    if any(part.is_symlink() for part in (supplied_evidence, *supplied_evidence.parents) if part.exists()):
        raise ContractError("CONTROLLER_EVIDENCE_PATH_INVALID", str(supplied_evidence))
    evidence_file = supplied_evidence.resolve(strict=True)
    if not evidence_file.is_relative_to(project_root / "08_review"):
        raise ContractError("CONTROLLER_EVIDENCE_PATH_INVALID", str(evidence_file))
    evidence = json.loads(evidence_file.read_text(encoding="utf-8"))
    controller_ref = evidence.get("controller_acceptance_ref")
    if (evidence.get("schema_version") != "cnw_controller_stage_acceptance_v1"
            or evidence.get("decision") != "ACCEPT"
            or evidence.get("controller") != "P3.1_W10_INDEPENDENT_CONTROLLER"
            or evidence.get("run_id") != run.name or evidence.get("stage") != stage
            or evidence.get("contract_sha256") != state.get("contract_sha256")
            or evidence.get("request_id") != pending.get("request_id")
            or evidence.get("provider_request_id") != pending.get("provider_request_id")
            or evidence.get("output_sha256") != pending.get("content_sha256")
            or not isinstance(controller_ref, str) or not controller_ref.strip()):
        raise ContractError("CONTROLLER_EVIDENCE_BINDING_INVALID", stage)
    if (digest(pending.get("content", "").encode("utf-8")) != pending.get("content_sha256")
            or digest(pending.get("artifact_content", "").encode("utf-8")) != pending.get("artifact_content_sha256")):
        raise ContractError("CONTROLLER_PENDING_OUTPUT_HASH_MISMATCH", stage)
    packet_path = safe_run_input(run / pending["packet_path"], run)
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    role = packet["role"]
    try:
        from .cnw_roles import build_role_packet, role_receipt
    except ImportError:
        from cnw_roles import build_role_packet, role_receipt
    w10_preflight = json.loads(Path(packet["preflight_path"]).read_text(encoding="utf-8"))
    contract_path = Path(packet["project_root"]) / state["contract_path"]
    role_packet = build_role_packet(role, contract_path, packet["input_paths"],
        accepted_receipts=state.get("role_receipts", []), mode="live", w10_preflight=w10_preflight)
    output = pending["artifact_content"]
    if stage == "draft":
        target = run / "artifacts/stages/draft-prose.md"
        if target.exists() or target.is_symlink():
            raise ContractError("LIVE_STAGE_ARTIFACT_COLLISION", target.name)
        target.write_text(output, encoding="utf-8")
    else:
        target = run / f"artifacts/stages/{stage}.md"
        if target.exists() or target.is_symlink():
            raise ContractError("LIVE_STAGE_ARTIFACT_COLLISION", target.name)
    matches = [row for row in state.get("provider_requests", [])
               if row.get("request_id") == pending.get("request_id")]
    if (len(matches) != 1 or matches[0].get("provider_request_id") != pending.get("provider_request_id")
            or matches[0].get("stage") != stage
            or matches[0].get("output_sha256") != pending.get("content_sha256")
            or matches[0].get("stage_fingerprint") != state["stages"][stage].get("fingerprint")):
        raise ContractError("CONTROLLER_PROVIDER_RECEIPT_BINDING_INVALID", stage)
    accepted = accept_validated_stage(run, stage=stage, content=pending["content"],
        validation=pending["validation"])
    target.write_text(output, encoding="utf-8")
    receipt = role_receipt(role, role_packet, output, status="CONTROLLER_ACCEPTED",
        provider_request_ids=[pending["provider_request_id"]], controller_accept_ref=controller_ref)
    receipt["provider_request_id"] = pending["provider_request_id"]
    try:
        from .cnw_runner import locked_run, load_state, save_state, now as runner_now
    except ImportError:
        from cnw_runner import locked_run, load_state, save_state, now as runner_now
    with locked_run(run):
        current = load_state(run)
        if current.get("pending_role_outputs", {}).get(stage, {}).get("content_sha256") != pending["content_sha256"]:
            raise ContractError("CONTROLLER_PENDING_OUTPUT_CHANGED", stage)
        current.setdefault("role_receipts", []).append(receipt)
        del current["pending_role_outputs"][stage]
        current["stages"][stage]["controller_accept_ref"] = controller_ref
        current["stages"][stage]["provider_output_sha256"] = pending["content_sha256"]
        current["stages"][stage]["controller_evidence"] = {
            "path": evidence_file.relative_to(project_root).as_posix(),
            "sha256": digest(evidence_file.read_bytes())}
        current["stages"][stage]["role_output_path"] = target.relative_to(run).as_posix()
        current["stages"][stage]["role_output_sha256"] = digest(target.read_bytes())
        current["updated_at"] = runner_now()
        save_state(run, current)
    return {"status": accepted["status"], "stage": stage, "controller_accept_ref": controller_ref,
            "controller_evidence_sha256": digest(evidence_file.read_bytes()),
            "role_receipt_sha256": digest(json.dumps(receipt, ensure_ascii=False, sort_keys=True).encode("utf-8"))}


def bind_nk_receipt(run_dir: str | Path, receipt_path: str | Path) -> dict:
    run = safe_run(run_dir)
    receipt_value = Path(receipt_path)
    receipt_file = safe_run_input(receipt_value if receipt_value.is_absolute() else run / receipt_value, run)
    receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    record_nk_pov_receipt(run, receipt)
    raw_path = safe_run_input(receipt["raw_response_path"], run)
    payload = json.loads(raw_path.read_text(encoding="utf-8"))
    body = payload.get("response", payload)
    content = body["choices"][0]["message"]["content"]
    if digest(content.encode("utf-8")) != receipt["output_sha256"]:
        raise ContractError("NK_PROVIDER_OUTPUT_HASH_MISMATCH", receipt["request_id"])
    accepted = accept_validated_stage(run, stage="pov", content=content,
        validation={"status": "REVIEW_COMPLETED", "validator": "pinned-NK-Zod+raw-response+cost-reconciliation"})
    return {"status": accepted["status"], "run_id": run.name, "stage": "pov",
            "request_id": receipt["request_id"], "provider_request_id": receipt["provider_request_id"],
            "artifact": accepted.get("artifact")}


def execute_local_lint(run_dir: str | Path, *, stage: str) -> dict:
    """Run the deterministic lint layer and close it through the live-stage gate."""
    if stage not in {"lint1", "lint2"}:
        raise ContractError("LIVE_LOCAL_STAGE_INVALID", stage)
    run = safe_run(run_dir)
    state = load_state(run)
    stage_record = state.get("stages", {}).get(stage, {})
    if state.get("mode") != "live" or stage_record.get("status") != "READY_FOR_EXECUTION":
        raise ContractError("LIVE_STAGE_NOT_READY", stage)
    source_stage = "refine" if state["stages"].get("refine", {}).get("status") == "ACCEPTED" else "draft"
    source_record = state["stages"].get(source_stage, {})
    source_path = run / source_record.get("prose_path", f"artifacts/stages/{source_stage}-prose.md")
    if not source_path.is_file() or source_path.is_symlink():
        raise ContractError("LIVE_LINT_SOURCE_MISSING", str(source_path))
    try:
        from .cnw_lint import lint
    except ImportError:
        from cnw_lint import lint
    layer = "surface" if stage == "lint1" else "structural"
    result = lint(source_path.read_text(encoding="utf-8"), layer)
    result.update({"stage": stage, "input_path": source_path.relative_to(run).as_posix(),
                   "input_sha256": digest(source_path.read_bytes())})
    content = json.dumps(result, ensure_ascii=False, sort_keys=True)
    validation_status = "LINT_CLEAN" if not result["findings"] else "LINT_COMPLETE"
    acceptance = accept_validated_stage(run, stage=stage, content=content,
        validation={"status": validation_status, "validator": "cnw_lint.lint",
                    "findings": len(result["findings"]), "source_sha256": result["source_sha256"]})
    return {"status": acceptance["status"], "run_id": run.name, "stage": stage,
            "layer": layer, "findings": len(result["findings"]), "provider_call": "none"}


def record_nk_budget_failure(run_dir: str | Path, request_id: str) -> dict:
    run = safe_run(run_dir)
    ledger = json.loads(p2_cost_guard.LEDGER.read_text(encoding="utf-8"))
    rows = [row for row in ledger.get("requests", []) if row.get("request_id") == request_id and row.get("run_id") == run.name]
    if len(rows) != 1 or rows[0].get("status") != "SETTLED_OVER_BUDGET":
        raise ContractError("NK_OVER_BUDGET_LEDGER_ROW_INVALID", request_id)
    try:
        from .cnw_live_provider import _load_live_state
        from .cnw_runner import locked_run, save_state
    except ImportError:
        from cnw_live_provider import _load_live_state
        from cnw_runner import locked_run, save_state
    with locked_run(run):
        state = load_state(run)
        _load_live_state(run, "pov")
        if not any(row.get("request_id") == request_id for row in state.get("provider_attempts", [])):
            state.setdefault("provider_attempts", []).append({"stage": "pov", "request_id": request_id,
                "status": "SETTLED_OVER_BUDGET", "ledger_settlement": rows[0],
                "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")})
            state["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
            save_state(run, state)
    return {"status": "NK_OVER_BUDGET_ATTEMPT_RECORDED", "request_id": request_id}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bind-nk-receipt")
    parser.add_argument("--record-nk-budget-failure")
    parser.add_argument("--accept-controller-role-output", action="store_true")
    parser.add_argument("--controller-evidence")
    parser.add_argument("--prepare-role")
    parser.add_argument("--prepare-stage", choices=("lens5", "verifier3", "completeness", "refine", "re-review"))
    parser.add_argument("--project-root")
    parser.add_argument("--inputs-json")
    parser.add_argument("--preflight")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--stage", choices=("plot", "cards", "brief", "draft", "lint1", "lint2", "lens5", "verifier3", "completeness", "refine", "re-review"))
    parser.add_argument("--packet")
    parser.add_argument("--role-id")
    parser.add_argument("--input-token-cap", type=int)
    parser.add_argument("--output-token-cap", type=int)
    args = parser.parse_args(argv)
    if args.preflight:
        os.environ["STORYSTUDIO_W10_PREFLIGHT_PATH"] = str(Path(args.preflight).resolve(strict=True))
    if args.bind_nk_receipt:
        result = bind_nk_receipt(args.run_dir, args.bind_nk_receipt)
    elif args.record_nk_budget_failure:
        result = record_nk_budget_failure(args.run_dir, args.record_nk_budget_failure)
    elif args.accept_controller_role_output:
        if not args.stage or not args.controller_evidence:
            raise ContractError("CONTROLLER_ACCEPTANCE_ARGUMENT_INVALID", "stage and ref required")
        result = accept_controller_role_output(args.run_dir, stage=args.stage, evidence_path=args.controller_evidence)
    elif args.stage in {"lint1", "lint2"} and not args.packet:
        result = execute_local_lint(args.run_dir, stage=args.stage)
    elif args.prepare_stage:
        result = prepare_review_request(args.run_dir, stage=args.prepare_stage, role_id=args.role_id)
    elif args.prepare_role:
        if not args.project_root or not args.inputs_json or not args.preflight:
            raise ContractError("LIVE_ROLE_PACKET_ARGUMENTS_REQUIRED", "project root, input map, and preflight path are required")
        input_map_file = Path(args.inputs_json).resolve(strict=True)
        input_map = json.loads(input_map_file.read_text(encoding="utf-8"))
        if not isinstance(input_map, dict):
            raise ContractError("LIVE_ROLE_INPUT_MAP_INVALID", str(input_map_file))
        result = prepare_role_request(args.run_dir, args.project_root, role=args.prepare_role,
            inputs=input_map, preflight_path=args.preflight)
    else:
        if not args.stage or not args.packet or not args.input_token_cap or not args.output_token_cap:
            raise ContractError("LIVE_EXECUTION_ARGUMENTS_REQUIRED", "--stage, --packet, and positive token caps are required")
        result = execute(args.run_dir, stage=args.stage, packet_path=args.packet,
            role_id=args.role_id, input_token_cap=args.input_token_cap,
            output_token_cap=args.output_token_cap)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractError, OSError, ValueError) as exc:
        print(f"CNW_LIVE_EXECUTION_FAILED:{exc}", file=sys.stderr)
        raise SystemExit(2)
