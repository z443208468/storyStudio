"""Execution identities and explicit reference reopening for the CNW runner.

This is transport/recovery bookkeeping, not an additional literary stage.
Outputs propagate changes by content; order alone is not a content dependency.
"""
from __future__ import annotations

import copy
import inspect
import json
from pathlib import Path
import re
import uuid


def _modules():
    try:
        from . import cnw_runner as runner, cnw_roles as roles, cnw_review as review
    except ImportError:
        import cnw_runner as runner
        import cnw_roles as roles
        import cnw_review as review
    return runner, roles, review


def _digest(value):
    runner, _, _ = _modules()
    return runner.sha(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8"))


def _code(*functions):
    return _digest([inspect.getsource(getattr(f, "__wrapped__", f)) for f in functions])


def verify_contract(run_dir: Path, state: dict) -> None:
    runner, _, _ = _modules()
    project = runner._run_dir_base(run_dir)
    for path in (runner.assert_output_within_root(project, state["contract_path"]),
                 run_dir / "artifacts/contract.json"):
        if not path.is_file() or runner.sha(path.read_bytes()) != state["contract_sha256"]:
            raise runner.ContractError("RUN_CONTRACT_CHANGED", str(path))


def support_input_snapshot(run_dir: Path, state: dict, name: str, hook: dict) -> Path:
    """Bind a successful support result to its own input, not today's draft."""
    r, _, _ = _modules()
    if not re.fullmatch(r"[a-f0-9]{64}", hook.get("input_sha256", "")):
        raise r.ContractError("CRITICS_INPUT_IDENTITY_INVALID", name)
    if hook.get("input_artifact"):
        artifact = hook["input_artifact"]
        path = r.assert_output_within_root(run_dir, artifact["path"])
        if not path.is_file() or r.sha(path.read_bytes()) != artifact["sha256"] or artifact["sha256"] != hook["input_sha256"]:
            raise r.ContractError("CRITICS_INPUT_CHANGED", name)
        return path
    snapshot = run_dir / f"artifacts/support/critics-input-{hook['input_sha256']}.md"
    candidates = [snapshot]
    if name == "critics_plot":
        record = state["stages"]["plot"]
        candidates += [r.assert_output_within_root(run_dir, a["path"]) for a in
            [record.get("artifact")] + [attempt.get("artifact") for attempt in reversed(record.get("invalidated_attempts", []))] if a]
    else:
        candidates.append(run_dir / "artifacts/support/critics-excerpt.md")
    source = next((path for path in candidates if path.is_file() and r.sha(path.read_bytes()) == hook["input_sha256"]), None)
    if source is None:
        raise r.ContractError("CRITICS_INPUT_MISSING", name)
    if snapshot.is_file() and r.sha(snapshot.read_bytes()) != hook["input_sha256"]:
        raise r.ContractError("CRITICS_INPUT_CHANGED", name)
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_bytes(source.read_bytes())
    hook["input_artifact"] = {"path": snapshot.relative_to(run_dir).as_posix(), "sha256": hook["input_sha256"]}
    r.save_state(run_dir, state)
    return snapshot


def verify_evidence(run_dir: Path, state: dict) -> None:
    runner, _, _ = _modules()
    def verify(value):
        if isinstance(value, dict):
            if isinstance(value.get("path"), str) and "sha256" in value:
                path = runner.assert_output_within_root(run_dir, value["path"])
                if not path.is_file() or runner.sha(path.read_bytes()) != value["sha256"]:
                    raise runner.ContractError("RUN_ARTIFACT_HASH_MISMATCH", value["path"])
            for child in value.values():
                verify(child)
        elif isinstance(value, list):
            for child in value:
                verify(child)
    verify(state["stages"])
    for stage, record in state["stages"].items():
        artifact = record.get("artifact")
        if record.get("status") in runner._MATERIALIZED and (not isinstance(artifact, dict) or not artifact.get("path") or not artifact.get("sha256")):
            raise runner.ContractError("STAGE_ARTIFACT_MISSING", stage)
    # Native reflection is a run artifact; CritiCS retains its separate native
    # evidence, verified by its adapter when that support hook is consumed.
    verify(state.get("support_hooks", {}).get("nk_pov", {}).get("artifact"))
    try:
        from .cnw_critics_adapter import read_native_result
    except ImportError:
        from cnw_critics_adapter import read_native_result
    hooks = [(name, state.get("support_hooks", {}).get(name, {})) for name in ("critics_plot", "critics_text")]
    hooks += [(row["hook"], row["evidence"]) for row in state.get("support_hook_attempts", []) if row.get("hook") in {"critics_plot", "critics_text"}]
    for name, hook in hooks:
        if hook.get("status") != "SUCCEEDED":
            continue
        source = support_input_snapshot(run_dir, state, name, hook)
        action = "plan-critique" if name == "critics_plot" else "text-refine"
        evidence = read_native_result(hook["run_name"], action=action, input_path=source)
        if hook.get("evidence_files") != evidence.get("evidence_files") or hook.get("result") != evidence.get("result"):
            raise runner.ContractError("CRITICS_EVIDENCE_CHANGED", hook["run_name"])
    receipts = state.get("provider_requests", []) + [a["prior_receipt"]
        for a in state.get("provider_attempts", []) if a.get("prior_receipt")]
    for receipt in receipts:
        if receipt.get("status") == "SUCCEEDED":
            runner._receipt_content(run_dir, receipt)
    known = {row.get("request_id") for row in receipts}
    for stage, record in state["stages"].items():
        if set(record.get("provider_request_ids", [])) - known:
            raise runner.ContractError("STAGE_RECEIPT_MISSING", stage)


def stage_identity(run_dir: Path, stage: str, *, project_root: Path | None = None,
                   contract_override: dict | None = None) -> dict:
    """Hash real role inputs and their builders, without calling a provider."""
    r, roles, review = _modules()
    state = r.load_state(run_dir)
    contract = contract_override if contract_override is not None else r._contract_for(run_dir)
    project = Path(project_root).resolve(strict=True) if project_root is not None else r._run_dir_base(run_dir)
    def text(name):
        return r._read_stage_text(run_dir, state, name)
    inputs, builders = {}, []
    executors = {"plot": r.execute_plot, "scene_cards": r.execute_scene_cards,
        "writing_brief": r.execute_writing_brief, "prose": r.execute_prose,
        "lint_layer1": r.execute_lint, "lint_layer2": r.execute_lint,
        "multi_lens_review": r.execute_five_lenses,
        "adversarial_verify": r.execute_three_verifiers,
        "completeness_critic": r.execute_completeness,
        "refine": r.execute_refine, "re_review": r.execute_re_review}
    builders.append(executors[stage])
    if stage in {"plot", "scene_cards", "writing_brief", "prose"}:
        role = {"scene_cards": "cards", "writing_brief": "brief"}.get(stage, stage)
        materials = r._role_sources(role, run_dir, state, contract, project)
        extra = None
        if stage == "plot":
            preparation = roles.read_production_preparation(project, contract)
            if contract["unit"]["kind"] == "scene":
                lines = (r._source_root(contract, project) / contract["story"]["source_file"]).read_text(encoding="utf-8-sig").splitlines()
                anchor = contract["story"]["before_anchor"]
                preparation["preceding_source_text"] = "\n".join(lines[anchor["source_line"]-1:anchor.get("source_line_end", anchor["source_line"])])
            extra = {"production_preparation": preparation}
            builders.append(roles.read_production_preparation)
        if stage == "writing_brief":
            try:
                from . import cnw_nk_adapter as nk
            except ImportError:
                import cnw_nk_adapter as nk
            inputs["nk_payload"] = nk.build_nk_payload(contract, text("scene_cards"), r._role_meta("cards", contract))
            reflection = state.get("support_hooks", {}).get("nk_pov", {}).get("artifact")
            if reflection:
                extra = {"nk_perspective_reflection_support_only": r.assert_output_within_root(run_dir, reflection["path"]).read_text(encoding="utf-8")}
            builders += [nk.build_nk_payload, nk.map_reflection_to_brief, r._nk_pov]
        inputs["messages"] = r._author_messages(role, contract, materials, extra)
        builders += [r._author_messages, roles.build_author_role_messages, roles.read_actual_texts,
                     roles.resolve_author_reads, roles.resolve_arc, roles.creative_assignment]
        if role == "prose":
            builders += [roles.brief_voice_samples, roles.brief_voice_characters, roles.relevant_voice_samples]
        else:
            builders += [r._planning_stage] if role != "brief" else []
    else:
        inputs["prose"] = text("prose")
        if stage in r.LOCAL_STAGES:
            try:
                from . import cnw_lint as lint
            except ImportError:
                import cnw_lint as lint
            inputs["rules"] = (project / "92_style_engine/forbidden_patterns.md").read_text(encoding="utf-8-sig")
            builders += [lint.lint, lint.project_rules]
        else:
            sources = r._review_sources(run_dir, state, contract, project)
            if stage == "multi_lens_review":
                # Completeness adds feedback for subsequent reviews. Its own
                # writes cannot retrospectively invalidate this initial review.
                for lens in r.LENS_IDS:
                    path = project / f"08_review/lens_feedback/{lens}.json"
                    if path.is_file():
                        rows = json.loads(path.read_text(encoding="utf-8"))
                        sources[f"lens_feedback:{lens}"] = "\n".join(row["instruction"] for row in rows if row.get("run_id") != run_dir.name)
                        if not sources[f"lens_feedback:{lens}"]:
                            sources.pop(f"lens_feedback:{lens}", None)
                inputs["lens_messages"] = [review.lens_messages(review.build_lens_input(lens, inputs["prose"], sources)) for lens in r.LENS_IDS]
                builders += [review.build_lens_input, review.lens_messages]
            elif stage == "adversarial_verify":
                inputs.update(lint2=text("lint_layer2"), review=text("multi_lens_review"),
                    evidence={name: sources[name] for name in ("scene_cards", "writing_brief", "character_bible", "timeline", "glossary")}, verifier_goals=review.VERIFIER_GOALS)
                builders += [review.build_verifier_packet, review.verifier_messages]
            elif stage == "completeness_critic":
                inputs.update(verify=text("adversarial_verify"), sources={name: sources[name] for name in ("scene_cards", "writing_brief", "project_specific_canon")})
                builders += [review.build_completeness_input, review.completeness_messages]
            elif stage == "refine":
                inputs.update(verify=text("adversarial_verify"), completeness=text("completeness_critic"), brief=text("writing_brief"))
                builders += [r._confirmed_findings, r._critics_excerpt]
            elif stage == "re_review":
                inputs.update(refine=text("refine"), sources=sources,
                    affected=state["stages"][stage].get("expected_role_ids") or state["stages"]["refine"].get("affected_lenses", list(r.LENS_IDS)), lens_goals=review.LENS_GOALS, verifier_goals=review.VERIFIER_GOALS)
                builders += [review.build_lens_input, review.lens_messages, review.build_verifier_packet, review.verifier_messages]
            builders += [r._review_sources]
    value = {"version": 1, "stage": stage, "contract_sha256": state["contract_sha256"],
        "input_sha256": _digest(inputs),
        "input_hashes": {name: _digest(item) for name, item in sorted(inputs.items())},
        **({"message_sha256": _digest(inputs["messages"])} if "messages" in inputs else {}),
        "builder_sha256": _code(*builders),
        "workflow_sha256": r.sha(r.WORKFLOW_PATH.read_bytes()), "model": r.MODEL,
        "api_url": r.API_URL, "transport_sha256": _code(r._cnw_live_call_in_slot)}
    return {**value, "sha256": _digest(value)}


def archive_stage(run_dir: Path, state: dict, stage: str, reason: str) -> None:
    """Preserve all referenced files before a fixed output path is reused."""
    r, _, _ = _modules()
    record = state["stages"][stage]
    prior = copy.deepcopy({k: v for k, v in record.items() if k != "invalidated_attempts"})
    folder = f"artifacts/history/{stage}-{uuid.uuid4().hex}"
    artifact = prior.get("artifact")
    if artifact and artifact["path"].endswith(".json"):
        # Index bytes remain untouched. Its referenced children receive their
        # own archive mappings so an old index does not point only at overwritten
        # current Lens files.
        source = r.assert_output_within_root(run_dir, artifact["path"])
        prior["artifact_children"] = json.loads(source.read_text(encoding="utf-8"))
    def preserve(value):
        if isinstance(value, dict):
            if isinstance(value.get("path"), str) and "sha256" in value:
                source = r.assert_output_within_root(run_dir, value["path"])
                raw = source.read_bytes()
                if r.sha(raw) != value["sha256"]:
                    raise r.ContractError("RUN_ARTIFACT_HASH_MISMATCH", value["path"])
                relative = f"{folder}/{value['path']}"
                target = r.assert_output_within_root(run_dir, relative)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
                value["path"] = relative
            for child in value.values():
                preserve(child)
        elif isinstance(value, list):
            for child in value:
                preserve(child)
    preserve(prior)
    prior.update(invalidated_reason=reason, invalidated_at=r.now())
    attempts = record.get("invalidated_attempts", []) + [prior]
    # Move outdated receipts out of current call coverage, while retaining them
    # in the exact request cache. Their unique request/raw files never overwrite.
    kept = []
    for receipt in state.get("provider_requests", []):
        if receipt.get("stage") == stage:
            state.setdefault("provider_attempts", []).append({"stage": stage,
                "status": reason, "prior_receipt": receipt, "invalidated_at": r.now()})
        else:
            kept.append(receipt)
    state["provider_requests"] = kept
    state["stages"][stage] = {"status": "INVALIDATED", "dependencies": record.get("dependencies", []), "invalidated_attempts": attempts}
    state.pop("editorial_candidate", None)
    state.pop("editorial_review", None)
    state["status"] = "RUNNING"
    state["next_stage"] = r._next_stage(state)
    state["updated_at"] = r.now()


def execute_checked(run_dir: Path, stage: str) -> dict:
    r, _, _ = _modules()
    state = r.load_state(run_dir)
    verify_contract(run_dir, state)
    verify_evidence(run_dir, state)
    r.validate_literary_source_freeze(state, r._run_dir_base(run_dir))
    for dependency in r.stage_predecessors(stage, state["unit_kind"]):
        if state["stages"][dependency]["status"] not in r._MATERIALIZED:
            raise r.ContractError("STAGE_DEPENDENCY_NOT_ACCEPTED", dependency)
        if state["stages"][dependency].get("execution_identity") != stage_identity(run_dir, dependency):
            raise r.ContractError("STAGE_DEPENDENCY_INPUT_CHANGED", f"{dependency}; resume from the earliest affected role")
    identity = stage_identity(run_dir, stage)
    previous = state["stages"][stage]
    if previous.get("status") in r._MATERIALIZED and previous.get("execution_identity") == identity:
        return {"status": "STAGE_REUSED", "stage": stage, "provider_call": "none"}
    if previous.get("artifact"):
        archive_stage(run_dir, state, stage, "EXECUTION_INPUT_OR_METHOD_CHANGED")
        r.save_state(run_dir, state)
    try:
        result = r._dispatch_cnw_stage(run_dir, stage)
    except Exception as exc:
        # Paid requests can exist even when no final stage report was produced.
        # Preserve their cache and explicitly mark the execution incomplete.
        with r.locked_run(run_dir):
            failed = r.load_state(run_dir)
            record = failed["stages"][stage]
            code = getattr(exc, "code", None)
            if str(exc) == "CAMPAIGN_ESTIMATE_LIMIT_WOULD_BE_EXCEEDED":
                code = str(exc)
            failure = {"at": r.now(), "error_type": type(exc).__name__, "error_code": code,
                       "provider_receipts_retained": sum(row.get("stage") == stage for row in failed.get("provider_requests", []))}
            record.setdefault("execution_failures", []).append(failure)
            if record.get("status") != "REVISION_REQUIRED":
                record["status"] = "EXECUTION_INCOMPLETE"
                failed["status"] = "EXECUTION_INCOMPLETE"
            failed["next_stage"] = stage
            r.save_state(run_dir, failed)
        raise
    fresh = r.load_state(run_dir)
    if fresh["stages"][stage].get("status") in r._MATERIALIZED:
        fresh["stages"][stage]["execution_input_identity"] = identity
        # Brief creates its NK support; re-review can complete additional
        # refinement passes. Capture those declared stage effects as well.
        fresh["stages"][stage]["execution_identity"] = stage_identity(run_dir, stage)
        if stage == "re_review":
            fresh["stages"]["refine"]["execution_identity"] = stage_identity(run_dir, "refine")
        r.save_state(run_dir, fresh)
    return result


def refresh_references(args) -> dict:
    r, _, _ = _modules()
    run_dir = r.run_path(args.run_id, r.runs_root_for(args))
    if not args.reason.strip():
        raise r.ContractError("REFERENCE_REOPEN_REASON_REQUIRED", args.run_id)
    with r.locked_run(run_dir, lock_name="execution.lock"):
        state = r.load_state(run_dir)
        verify_contract(run_dir, state)
        verify_evidence(run_dir, state)
        contract = r._contract_for(run_dir)
        old = state.get("literary_source_hashes", {})
        if not old:
            raise r.ContractError("LITERARY_SOURCE_FREEZE_MISSING", args.run_id)
        actual = r.literary_source_freeze(contract, r._run_dir_base(run_dir))
        changed = sorted(key for key in set(old) | set(actual) if old.get(key) != actual.get(key))
        immutable = [key for key in changed if not key.startswith(("project:", "preparation:"))]
        if immutable:
            raise r.ContractError("IMMUTABLE_SOURCE_CHANGED", ", ".join(immutable))
        state.setdefault("reference_reopens", []).append({"at": r.now(), "reason": args.reason,
            "old_hashes": old, "new_hashes": actual, "changed": changed})
        state["literary_source_hashes"] = actual
        r.save_state(run_dir, state)
        reopened = []
        # Only direct consumers are reopened now. During resume, actual changed
        # output content invalidates consumers; identical output reuses them.
        affected = []
        for stage in r.CNW_STAGES:
            record = state["stages"][stage]
            if record.get("status") not in r._MATERIALIZED:
                continue
            if record.get("execution_identity") != stage_identity(run_dir, stage):
                affected.append(stage)
        for stage in affected:
            archive_stage(run_dir, state, stage, "REFERENCE_REOPEN")
            reopened.append(stage)
        r.save_state(run_dir, state)
        return {"status": "REFERENCES_REOPENED", "run_id": args.run_id,
            "changed": changed, "reopened": reopened, "provider_call": "none"}
