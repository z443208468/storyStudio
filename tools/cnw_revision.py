"""Offline length/beat regression gates for a CNW scene revision."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import re

try:
    from .cnw_contract import ContractError, count_visible_chars, load_contract
    from .cnw_generate import _private_project_root, _project_input, validate_generated_scene
except ImportError:  # direct script execution
    from cnw_contract import ContractError, count_visible_chars, load_contract
    from cnw_generate import _private_project_root, _project_input, validate_generated_scene


def validate_revision(contract: dict, v0: str, v1: str, *, finish_reason: str, v0_beat_evidence: dict[str, str], v1_beat_evidence: dict[str, str], v1_dialogue_evidence: list[str], v1_action_evidence: list[str], start_state_evidence: str, end_state_evidence: str, shortening_reason: str = "") -> dict:
    before = count_visible_chars(v0)
    after = validate_generated_scene(contract, v1, finish_reason=finish_reason, beat_evidence=v1_beat_evidence, dialogue_evidence=v1_dialogue_evidence, action_evidence=v1_action_evidence, start_state_evidence=start_state_evidence, end_state_evidence=end_state_evidence)
    regression = after["actual_visible_chars"] < contract["unit"]["min_visible_chars"]
    dropped_beats = [beat_id for beat_id, evidence in v0_beat_evidence.items() if evidence and evidence in v0 and not (v1_beat_evidence.get(beat_id) and v1_beat_evidence[beat_id] in v1)]
    if dropped_beats:
        after["failure_codes"].append("REVISION_REGRESSION")
        after["dropped_beat_ids"] = dropped_beats
        regression = True
    if after["actual_visible_chars"] < contract["unit"]["min_visible_chars"]:
        after["failure_codes"].append("REVISION_REGRESSION")
        regression = True
    after["failure_codes"] = list(dict.fromkeys(after["failure_codes"]))
    after["v0_visible_chars"] = before
    after["v1_visible_chars"] = after["actual_visible_chars"]
    if before and after["actual_visible_chars"] < before * 0.75 and not shortening_reason.strip():
        after["failure_codes"].append("REVISION_SHRINK_OVER_25_PERCENT_REQUIRES_REASON")
        after["status"] = "CONTENT_RETURN"
    elif before and after["actual_visible_chars"] < before * 0.75:
        after["shortening_reason"] = shortening_reason.strip()
    after["status"] = "CONTENT_RETURN" if regression or after["failure_codes"] else "CONTENT_VALID"
    # A shorter edit is allowed when it remains in range and preserves required beats.
    return after


def build_revision_plan(accepted_review: dict, *, allow_fixture:bool=False) -> dict:
    """Derive the plan from a hash-bound accepted review and its three independent verifier votes."""
    if accepted_review.get("status")!="EXTERNAL_ACCEPTED" or accepted_review.get("execution_mode") not in {"LIVE","TEST_FIXTURE_ONLY"}:
        raise ContractError("ACCEPTED_REVIEW_EVIDENCE_REQUIRED","unaccepted or mock review cannot create a production revision plan")
    fixture=accepted_review.get("fixture_only") is True or accepted_review.get("execution_mode")=="TEST_FIXTURE_ONLY"
    if fixture and not allow_fixture: raise ContractError("MOCK_REVIEW_CANNOT_CREATE_PRODUCTION_PLAN","fixture evidence is test-only")
    for key in ("candidate_sha256","contract_sha256","source_identity_sha256","controller_acceptance_ref"):
        if not accepted_review.get(key): raise ContractError("ACCEPTED_REVIEW_BINDING_MISSING",key)
    expected_lenses={"style","character","plot","canon","story_specific"}; expected_verifiers={"verifier_1","verifier_2","verifier_3"}
    requests=accepted_review.get("provider_requests",[])
    lens_rows=[x for x in requests if x.get("stage")=="lens5"]; verifier_rows=[x for x in requests if x.get("stage")=="verifier3"]
    if ({x.get("lens_id") for x in lens_rows}!=expected_lenses or len(lens_rows)!=5 or {x.get("verifier_id") for x in verifier_rows}!=expected_verifiers or len(verifier_rows)!=3):
        raise ContractError("ACCEPTED_REVIEW_CALL_SET_INVALID","five Lens and three Verifier receipts are required")
    provider_ids=[x.get("provider_request_id") for x in lens_rows+verifier_rows]
    if not all(isinstance(x,str) and x for x in provider_ids) or len(set(provider_ids))!=8: raise ContractError("ACCEPTED_REVIEW_CALL_ID_INVALID","eight distinct provider request IDs required")
    verifier_by_id={x["verifier_id"]:x["provider_request_id"] for x in verifier_rows}
    verifier_outputs={}
    for row in verifier_rows:
        content=row.get("response_content")
        if not isinstance(content,str) or hashlib.sha256(content.encode()).hexdigest()!=row.get("output_sha256"):
            raise ContractError("VERIFIER_RAW_OUTPUT_UNBOUND",row["verifier_id"])
        try: parsed=json.loads(content)
        except json.JSONDecodeError as exc: raise ContractError("VERIFIER_OUTPUT_SCHEMA_INVALID",row["verifier_id"]) from exc
        if parsed.get("verifier_id")!=row["verifier_id"] or not isinstance(parsed.get("votes"),list): raise ContractError("VERIFIER_OUTPUT_SCHEMA_INVALID",row["verifier_id"])
        vote_ids=[vote.get("finding_id") for vote in parsed["votes"]]
        if len(vote_ids)!=len(set(vote_ids)) or any(vote.get("verdict") not in {"not_refuted","refuted","uncertain"} for vote in parsed["votes"]): raise ContractError("VERIFIER_OUTPUT_SCHEMA_INVALID",row["verifier_id"])
        verifier_outputs[row["verifier_id"]]={vote.get("finding_id"):vote.get("verdict") for vote in parsed["votes"]}
    source_catalog=accepted_review.get("source_catalog",{}); allowed={"P0","P1","P2","P3"}; seen=set(); items=[]
    for item in accepted_review.get("findings",[]):
        issue_id=str(item.get("issue_id","")).strip()
        if not issue_id or issue_id in seen or item.get("severity") not in allowed: raise ContractError("REVISION_ISSUE_INVALID",issue_id or "missing or duplicate issue id/severity")
        seen.add(issue_id)
        source=item.get("source"); source_record=source_catalog.get(source)
        if (not source_record or not isinstance(source_record.get("text"),str)
            or hashlib.sha256(source_record["text"].encode()).hexdigest()!=source_record.get("sha256")
            or source_record.get("source_manifest_sha256")!=accepted_review["source_identity_sha256"]):
            raise ContractError("REVISION_ISSUE_SOURCE_UNVERIFIED",issue_id)
        excerpt=item.get("evidence","")
        if not excerpt or excerpt not in source_record["text"]: raise ContractError("REVISION_ISSUE_EVIDENCE_NOT_IN_SOURCE",issue_id)
        votes=item.get("verifier_votes",[])
        if len(votes)!=3 or {v.get("verifier_id") for v in votes}!=expected_verifiers or len({v.get("verifier_id") for v in votes})!=3:
            raise ContractError("REVISION_ISSUE_VOTES_INCOMPLETE",issue_id)
        for vote in votes:
            if vote.get("provider_request_id")!=verifier_by_id.get(vote.get("verifier_id")) or vote.get("verdict") not in {"not_refuted","refuted","uncertain"}:
                raise ContractError("REVISION_ISSUE_VOTE_UNBOUND",issue_id)
            if verifier_outputs.get(vote["verifier_id"],{}).get(issue_id)!=vote["verdict"]: raise ContractError("REVISION_ISSUE_VOTE_NOT_IN_RAW_OUTPUT",issue_id)
        if sum(v["verdict"]=="not_refuted" for v in votes)<2: continue
        required=("owner","fix","acceptance"); missing=[key for key in required if not str(item.get(key,"")).strip()]
        if missing: raise ContractError("REVISION_ISSUE_INCOMPLETE",f"{issue_id}: {', '.join(missing)}")
        needs_author=item.get("canon_change") is True
        items.append({"issue_id":issue_id,"severity":item["severity"],"owner":item["owner"],"source":source,"source_sha256":source_record["sha256"],"evidence":excerpt,"verifier_votes":votes,"fix":item["fix"],"acceptance":item["acceptance"],"estimated_cost":item.get("estimated_cost","not_estimated"),"depends_on":item.get("depends_on",[]),"status":"NEEDS_AUTHOR_DECISION" if needs_author else "OPEN"})
    order={"P0":0,"P1":1,"P2":2,"P3":3}
    review_sha=hashlib.sha256(json.dumps(accepted_review,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return {"schema":1,"status":"AUTHOR_OR_CONTROLLER_REVIEW_REQUIRED","self_acceptance":False,"review_evidence_sha256":review_sha,"candidate_sha256":accepted_review["candidate_sha256"],"contract_sha256":accepted_review["contract_sha256"],"source_identity_sha256":accepted_review["source_identity_sha256"],"issues":sorted(items,key=lambda x:(order[x["severity"]],x["issue_id"]))}


def build_revision_record(v0:str,v1:str,plan:dict,*,shortening_reason:str="")->dict:
    before=count_visible_chars(v0); after=count_visible_chars(v1)
    if before and after<before*.75 and not shortening_reason.strip(): raise ContractError("REVISION_SHRINK_OVER_25_PERCENT_REQUIRES_REASON","record the specific cuts and retained story function")
    import difflib
    return {"schema":1,"v0_sha256":hashlib.sha256(v0.encode()).hexdigest(),"v1_sha256":hashlib.sha256(v1.encode()).hexdigest(),"v0_visible_chars":before,"v1_visible_chars":after,"shrink_ratio":round(1-after/before,6) if before else 0,"shortening_reason":shortening_reason.strip() or None,"issue_ids":[item["issue_id"] for item in plan.get("issues",[])],"diff":"".join(difflib.unified_diff(v0.splitlines(keepends=True),v1.splitlines(keepends=True),fromfile="v0",tofile="v1")),"original_preserved":True,"plan_self_acceptance":False}


def build_rereview_packets(v0:str,v1:str,affected_lenses:list[str],sources:dict[str,str])->list[dict]:
    """Build fresh, isolated re-review requests; no transport is invoked here."""
    required={"style":{"style_guide","language_rules"},"character":{"character_bible","voice_samples","address_terms"},"plot":{"plot","scene_cards","brief"},"canon":{"canon","source_anchors","knowledge_boundaries"},"story_specific":{"story_contract","canon","brief"}}
    if len(set(affected_lenses))!=len(affected_lenses) or set(affected_lenses)-set(required): raise ContractError("REREVIEW_LENS_INVALID", str(affected_lenses))
    packets=[]; diff={"v0_sha256":hashlib.sha256(v0.encode()).hexdigest(),"v1_sha256":hashlib.sha256(v1.encode()).hexdigest(),"v0":v0,"v1":v1}
    for lens in affected_lenses:
        missing=required[lens]-set(sources)
        if missing: raise ContractError("REREVIEW_SOURCES_MISSING", f"{lens}: {', '.join(sorted(missing))}")
        context={key:sources[key] for key in sorted(required[lens])}
        payload={"lens_id":lens,"draft":v1,"change_context":diff,"sources":context,"execution_mode":"MOCK_ONLY","provider_request_id":None}
        payload["input_sha256"]=hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
        packets.append(payload)
    return packets


def promote_revision(project_root:str|Path,run_dir:str|Path,candidate_path:str|Path,contract:dict,review_evidence:dict,*,test_fixture:bool=False)->dict:
    """Promote only an externally accepted, hash-bound candidate; preserve prior text and index."""
    project_input=Path(project_root).absolute(); run_input=Path(run_dir).absolute()
    for value in (project_input,run_input):
        if any(part.is_symlink() for part in (value,*value.parents) if part.exists()): raise ContractError("PROMOTION_PATH_SYMLINK_REJECTED",str(value))
    project=project_input.resolve(strict=True); run=run_input.resolve(strict=True)
    if test_fixture:
        fixture_root=(Path(__file__).resolve().parents[1]/"tests"/"_isolated_workspace").resolve()
        if not project.is_relative_to(fixture_root): raise ContractError("FIXTURE_PROMOTION_OUTSIDE_ISOLATED_TEST_ROOT",str(project))
    else:
        project=_private_project_root(project)
    allowed_run_roots = [(project / "runs").resolve(), (Path(__file__).resolve().parents[1] / "runs").resolve()]
    if not any(run.is_relative_to(root) for root in allowed_run_roots): raise ContractError("PROMOTION_RUN_PATH_UNSAFE",str(run))
    candidate=Path(candidate_path)
    if not candidate.is_absolute(): candidate=run/candidate
    cursor=candidate
    while cursor!=run.parent:
        if cursor.is_symlink(): raise ContractError("PROMOTION_CANDIDATE_UNSAFE",str(cursor))
        if cursor==cursor.parent: break
        cursor=cursor.parent
    candidate=candidate.resolve(strict=True)
    if not candidate.is_relative_to(run) or not candidate.is_file(): raise ContractError("PROMOTION_CANDIDATE_UNSAFE",str(candidate))
    raw=candidate.read_bytes(); candidate_sha=hashlib.sha256(raw).hexdigest(); unit=contract.get("unit",{}); work_id=unit.get("id")
    source_identity=contract.get("source",{}).get("source_manifest_sha256") or contract.get("source",{}).get("local_private_source_manifest_sha256")
    contract_identity=hashlib.sha256(json.dumps(contract,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    index=project/"07_draft"/"manuscript_index.md"
    if index.is_symlink(): raise ContractError("PROMOTION_INDEX_SYMLINK_REJECTED",str(index))
    if (review_evidence.get("status")!="EXTERNAL_ACCEPTED" or (review_evidence.get("fixture_only") is True and not test_fixture)
        or review_evidence.get("candidate_sha256")!=candidate_sha or review_evidence.get("work_id")!=work_id
        or not review_evidence.get("controller_acceptance_ref") or review_evidence.get("source_identity_sha256")!=source_identity
        or review_evidence.get("contract_sha256")!=contract_identity):
        raise ContractError("EXTERNAL_REVIEW_EVIDENCE_REQUIRED","acceptance must bind candidate, work id, contract and source")
    accepted_review=review_evidence.get("accepted_review")
    if not isinstance(accepted_review,dict): raise ContractError("ACCEPTED_REVIEW_EVIDENCE_REQUIRED","the accepted source review must accompany the promotion record")
    plan=build_revision_plan(accepted_review,allow_fixture=test_fixture)
    if review_evidence.get("revision_plan")!=plan or plan.get("candidate_sha256")!=candidate_sha or plan.get("contract_sha256")!=contract_identity or plan.get("source_identity_sha256")!=source_identity:
        raise ContractError("REVISION_PLAN_BINDING_MISMATCH","plan is not derived from this accepted review and candidate")
    v0_rel=review_evidence.get("v0_path")
    if not isinstance(v0_rel,str): raise ContractError("REVISION_BASELINE_REQUIRED","original v0 path is required")
    v0_path=Path(v0_rel); v0_path=v0_path if v0_path.is_absolute() else run/v0_path
    cursor=v0_path
    while cursor!=run.parent:
        if cursor.is_symlink(): raise ContractError("REVISION_BASELINE_UNSAFE",str(cursor))
        if cursor==cursor.parent: break
        cursor=cursor.parent
    v0_path=v0_path.resolve(strict=True)
    if not v0_path.is_relative_to(run) or not v0_path.is_file(): raise ContractError("REVISION_BASELINE_UNSAFE",str(v0_path))
    v0=v0_path.read_text(encoding="utf-8-sig"); v1=raw.decode("utf-8-sig")
    validation=review_evidence.get("validation_evidence")
    if not isinstance(validation,dict): raise ContractError("REVISION_VALIDATION_EVIDENCE_REQUIRED","W06 contract evidence is required before promotion")
    validated=validate_revision(contract,v0,v1,finish_reason=validation.get("finish_reason",""),v0_beat_evidence=validation.get("v0_beat_evidence",{}),v1_beat_evidence=validation.get("v1_beat_evidence",{}),v1_dialogue_evidence=validation.get("dialogue_evidence",[]),v1_action_evidence=validation.get("action_evidence",[]),start_state_evidence=validation.get("start_state_evidence",""),end_state_evidence=validation.get("end_state_evidence",""),shortening_reason=validation.get("shortening_reason",""))
    if validated.get("status")!="CONTENT_VALID": raise ContractError("REVISION_CONTRACT_VALIDATION_FAILED",json.dumps(validated,ensure_ascii=False))
    record=build_revision_record(v0,v1,plan,shortening_reason=validation.get("shortening_reason",""))
    if review_evidence.get("revision_record")!=record: raise ContractError("REVISION_RECORD_MISMATCH","v0/v1 hashes, diff, plan and shrink reason must match")
    if not isinstance(work_id,str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}",work_id): raise ContractError("PROMOTION_WORK_ID_INVALID",str(work_id))
    folder="episodes" if unit.get("kind")=="episode" else "scenes" if unit.get("kind")=="scene" else None
    if not folder: raise ContractError("PROMOTION_UNIT_KIND_INVALID",str(unit.get("kind")))
    destination=project/"07_draft"/folder/f"{work_id}.md"
    archive=None
    for output in (project/"07_draft",destination.parent,index):
        if output.is_symlink(): raise ContractError("PROMOTION_OUTPUT_SYMLINK_REJECTED",str(output))
        if output.exists() and not output.resolve().is_relative_to(project): raise ContractError("PROMOTION_OUTPUT_OUTSIDE_PROJECT",str(output))
    destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.exists():
        prior=destination.read_bytes(); prior_sha=hashlib.sha256(prior).hexdigest()
        archive=project/"09_revision"/"accepted_archive"/f"{work_id}.{prior_sha}.md"; archive.parent.mkdir(parents=True,exist_ok=True)
        if archive.exists() and hashlib.sha256(archive.read_bytes()).hexdigest()!=prior_sha: raise ContractError("PROMOTION_ARCHIVE_COLLISION",str(archive))
        if not archive.exists(): archive.write_bytes(prior)
    destination.parent.mkdir(parents=True,exist_ok=True)
    tmp=destination.with_name(destination.name+".tmp"); tmp.write_bytes(raw); os.replace(tmp,destination)
    line=f"- {work_id} | {unit['kind']} | {destination.relative_to(project).as_posix()} | SHA256={candidate_sha} | review={review_evidence['controller_acceptance_ref']} | source={review_evidence['source_identity_sha256']}"
    prior_index=index.read_text(encoding="utf-8") if index.exists() else "# Manuscript Index\n"
    rows=[row for row in prior_index.splitlines() if not row.startswith(f"- {work_id} |")]
    idx_tmp=index.with_name(index.name+".tmp"); idx_tmp.write_text("\n".join([*rows,line])+"\n",encoding="utf-8"); os.replace(idx_tmp,index)
    return {"status":"PROMOTED","work_id":work_id,"path":destination.relative_to(project).as_posix(),"candidate_sha256":candidate_sha,"archive_path":archive.relative_to(project).as_posix() if archive else None,"review_evidence_sha256":hashlib.sha256(json.dumps(review_evidence,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),"provider_call":"none"}


def validate_episode_assembly(expected_scene_ids: list[str], scene_results: dict[str, dict]) -> dict:
    missing = [scene_id for scene_id in expected_scene_ids if scene_id not in scene_results or scene_results[scene_id].get("status") != "CONTENT_VALID" or scene_results[scene_id].get("finish_reason") != "stop"]
    return {"status": "CONTENT_VALID" if not missing else "CONTENT_RETURN", "failure_codes": [] if not missing else ["TRUNCATED_OR_UNFINISHED"], "missing_scene_ids": missing}


def plan_persisted_continuation(project_root: str | Path, run_id: str, contract: dict, current_text: str, validation: dict, *, max_attempts: int = 2) -> dict:
    if max_attempts != 2:
        raise ContractError("CONTINUATION_LIMIT_FIXED", "W06 permits at most two attempts")
    root = _private_project_root(project_root)
    if not run_id or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for ch in run_id) or run_id in {".", ".."}:
        raise ContractError("RUN_ID_INVALID", run_id)
    log = root / "runs" / run_id / "continuation.jsonl"
    if any(part.is_symlink() for part in (log, *log.parents) if part.exists()):
        raise ContractError("CONTINUATION_STATE_UNSAFE", "continuation state contains a symlink")
    log.parent.mkdir(parents=True, exist_ok=True)
    contract_sha = hashlib.sha256(json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    entries = []
    if log.exists():
        try:
            entries = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line]
        except (OSError, json.JSONDecodeError) as exc:
            raise ContractError("CONTINUATION_STATE_INVALID", "continuation log is unreadable") from exc
    previous_hash = "0" * 64
    for index, entry in enumerate(entries, 1):
        payload = {key: value for key, value in entry.items() if key != "entry_sha256"}
        digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        if (entry.get("attempt") != index or entry.get("run_id") != run_id or entry.get("contract_sha256") != contract_sha
                or entry.get("previous_sha256") != previous_hash or entry.get("entry_sha256") != digest):
            raise ContractError("CONTINUATION_STATE_INVALID", f"broken chain at attempt {index}")
        previous_hash = digest
    if len(entries) >= max_attempts:
        return {"status": "RETURN_ROOT_CAUSE_REVIEW_REQUIRED", "attempts_used": len(entries), "max_attempts": max_attempts, "provider_call": "none"}
    if validation.get("status") == "CONTENT_VALID":
        return {"status": "CONTINUATION_NOT_REQUIRED", "attempts_used": len(entries), "provider_call": "none"}
    attempt = len(entries) + 1
    payload = {"attempt": attempt, "run_id": run_id, "contract_sha256": contract_sha, "previous_sha256": previous_hash,
               "text_sha256": hashlib.sha256(current_text.encode("utf-8")).hexdigest(),
               "actual_visible_chars": count_visible_chars(current_text),
               "missing_beat_ids": validation.get("missing_beat_ids", []), "failure_codes": validation.get("failure_codes", [])}
    payload["entry_sha256"] = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    with log.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        stream.flush()
    if attempt >= max_attempts:
        return {"status": "RETURN_ROOT_CAUSE_REVIEW_REQUIRED", "attempts_used": attempt, "max_attempts": max_attempts, "provider_call": "none"}
    missing = validation.get("missing_beat_ids", [])
    if not missing and "RETURN_UNDERPRODUCED" in validation.get("failure_codes", []):
        missing = [beat["beat_id"] for beat in contract["story"]["required_beats"]]
    result = {"status": "CONTINUE_MISSING_BEATS" if missing else "REVIEW_FAILURE_CODES", "missing_beat_ids": missing,
              "current_visible_chars": count_visible_chars(current_text), "failure_codes": validation.get("failure_codes", []),
              "max_attempts": max_attempts, "provider_call": "not_performed_by_W06_planner"}
    return {**result, "attempts_used": attempt, "state_log": str(log.relative_to(root)), "state_sha256": payload["entry_sha256"]}


def main(argv=None) -> int:
    argv=list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in {"plan","rereview","promote"}:
        command=argv.pop(0); parser=argparse.ArgumentParser(description=f"CNW revision {command}")
        parser.add_argument("--project-root",required=True)
        if command=="plan":
            parser.add_argument("--review",required=True); parser.add_argument("--output",required=True)
        elif command=="rereview":
            parser.add_argument("--v0",required=True); parser.add_argument("--v1",required=True); parser.add_argument("--affected-lenses",required=True); parser.add_argument("--sources",required=True); parser.add_argument("--plan",required=True); parser.add_argument("--shortening-reason",default=""); parser.add_argument("--output",required=True)
        else:
            parser.add_argument("--run-id",required=True); parser.add_argument("--candidate",required=True); parser.add_argument("--evidence",required=True)
        args=parser.parse_args(argv); project=_private_project_root(args.project_root)
        if command=="plan":
            raw=json.loads(_project_input(project,args.review).read_text(encoding="utf-8-sig"))
            result=build_revision_plan(raw); output=_project_input(project,args.output) if (project/args.output).exists() else project/args.output
            if not output.resolve().is_relative_to(project): raise ContractError("REVISION_OUTPUT_OUTSIDE_PROJECT",str(output))
            output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        elif command=="rereview":
            v0=_project_input(project,args.v0).read_text(encoding="utf-8-sig"); v1=_project_input(project,args.v1).read_text(encoding="utf-8-sig")
            sources=json.loads(_project_input(project,args.sources).read_text(encoding="utf-8-sig")); plan=json.loads(_project_input(project,args.plan).read_text(encoding="utf-8-sig"))
            result={"status":"REREVIEW_REQUESTS_PREPARED_MOCK_ONLY","revision_record":build_revision_record(v0,v1,plan,shortening_reason=args.shortening_reason),"packets":build_rereview_packets(v0,v1,[x.strip() for x in args.affected_lenses.split(",") if x.strip()],sources),"provider_call":"none"}
            output=project/args.output
            if not output.resolve().is_relative_to(project): raise ContractError("REREVIEW_OUTPUT_OUTSIDE_PROJECT",str(output))
            output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        else:
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}",args.run_id): raise ContractError("RUN_ID_INVALID",args.run_id)
            try:
                from . import cnw_runner
            except ImportError:
                import cnw_runner
            result=cnw_runner.promote_run(argparse.Namespace(run_id=args.run_id,project_root=str(project),candidate=args.candidate,review_evidence=args.evidence))
        print(json.dumps(result,ensure_ascii=False,indent=2)); return 0
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--v0", required=True)
    parser.add_argument("--v1", required=True)
    parser.add_argument("--evidence", help="private JSON evidence map; required to issue PASS/RETURN")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--continuation-run-id", help="persist and enforce the attempt limit under runs/<id>/")
    parser.add_argument("--mode", choices=("offline", "live"), default="offline")
    args = parser.parse_args(argv)
    if args.mode == "live":
        raise ContractError("LIVE_EXECUTOR_NOT_AVAILABLE", "W06 revision validation is offline; live execution remains gated for W10")
    project_root = _private_project_root(args.project_root)
    contract = load_contract(_project_input(project_root, args.contract))
    v0 = _project_input(project_root, args.v0).read_text(encoding="utf-8-sig")
    v1 = _project_input(project_root, args.v1).read_text(encoding="utf-8-sig")
    if not args.evidence:
        raise ContractError("REVISION_EVIDENCE_REQUIRED", "cannot issue revision acceptance from character counts alone")
    evidence = json.loads(_project_input(project_root, args.evidence).read_text(encoding="utf-8"))
    result = validate_revision(contract, v0, v1, finish_reason=evidence["finish_reason"], v0_beat_evidence=evidence["v0_beat_evidence"], v1_beat_evidence=evidence["v1_beat_evidence"], v1_dialogue_evidence=evidence["dialogue_evidence"], v1_action_evidence=evidence["action_evidence"], start_state_evidence=evidence["start_state_evidence"], end_state_evidence=evidence["end_state_evidence"])
    if args.continuation_run_id and result["status"] != "CONTENT_VALID":
        result["continuation"] = plan_persisted_continuation(project_root, args.continuation_run_id, contract, v1, result)
    elif result["status"] != "CONTENT_VALID":
        raise ContractError("CONTINUATION_RUN_ID_REQUIRED", "a failed revision must be recorded in its persistent run state")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] != "CONTENT_VALID":
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"CNW_REVISION_FAILED:{exc}", file=sys.stderr)
        raise SystemExit(2)
