"""Offline-isolated CNW review orchestration. MOCK_ONLY output is never live evidence."""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path
from typing import Any
try:
    from .cnw_lint import lint
except ImportError:
    from cnw_lint import lint

LENSES={
 "style":("style_guide","language_rules"),
 "character":("character_bible","voice_samples","address_terms"),
 "plot":("plot","scene_cards","brief"),
 "canon":("canon","source_anchors","knowledge_boundaries"),
 "story_specific":("story_contract","canon","brief")}
VERIFIERS=("continuity_counterexample","character_counterexample","evidence_counterexample")
def digest(s:str)->str:return hashlib.sha256(s.encode("utf-8")).hexdigest()
def lens_packet(name:str,draft:str,sources:dict[str,str])->dict:
    if name not in LENSES: raise ValueError("unknown lens")
    selected={k:sources[k] for k in LENSES[name] if k in sources}
    return {"lens_id":name,"draft":draft,"sources":selected,"input_sha256":digest(json.dumps({"lens_id":name,"draft":draft,"sources":selected},ensure_ascii=False,sort_keys=True)),"execution_mode":"MOCK_ONLY","provider_request_id":None}
def mock_lens(packet:dict)->dict:
    name=packet["lens_id"]; draft=packet["draft"]
    # Distinct, explicitly simulated outputs. These are protocol fixtures, not literary judgments.
    finding=[]
    if name=="plot" and "CNW_BEAT" in "": finding=[]
    return {"lens_id":name,"input_sha256":packet["input_sha256"],"input_packet":packet,"execution_mode":"MOCK_ONLY","provider_request_id":None,"findings":finding,"simulated_output":{"scope":name,"assessment":"fixture output; no semantic/model judgment performed"},"simulation":"distinct offline injected transport; no provider call"}
def verifier_packets(findings:list[dict],draft:str,sources:dict[str,str]|None=None)->list[dict]:
    return [{"verifier_id":v,"challenge_angle":v,"findings":findings,"draft":draft,"sources":sources or {},"input_sha256":digest(json.dumps({"verifier_id":v,"challenge_angle":v,"findings":findings,"draft":draft,"sources":sources or {}},ensure_ascii=False,sort_keys=True)),"execution_mode":"MOCK_ONLY","provider_request_id":None} for v in VERIFIERS]
def tally_verifiers(verdicts:list[dict])->dict:
    if len(verdicts)!=3 or len({x.get("verifier_id") for x in verdicts})!=3: raise ValueError("exactly three isolated verifier identities required")
    if {x.get("verifier_id") for x in verdicts}!=set(VERIFIERS): raise ValueError("unexpected verifier identity")
    if any(x.get("execution_mode")!="MOCK_ONLY" or x.get("provider_request_id") is not None for x in verdicts): raise ValueError("offline verifier cannot claim provider identity")
    # uncertain/refuted means the claim is not confirmed; exactly one vote per verifier is required.
    grouped={}; per_verifier={}
    for v in verdicts:
        seen=set()
        for item in v.get("votes",[]):
            finding_id=item.get("finding_id")
            if finding_id in seen: raise ValueError("duplicate vote by verifier for a finding")
            seen.add(finding_id)
            if item.get("verdict") not in {"not_refuted","refuted","uncertain"}: raise ValueError("invalid verifier verdict")
            grouped.setdefault(finding_id,[]).append(item["verdict"])
        per_verifier[v["verifier_id"]]=seen
    if per_verifier and len({tuple(sorted(x)) for x in per_verifier.values()})!=1: raise ValueError("each verifier must vote once on every finding")
    return {k:{"not_refuted":sum(x=="not_refuted" for x in votes),"status":"CONFIRMED" if sum(x=="not_refuted" for x in votes)>=2 else "REFUTED_OR_UNCERTAIN"} for k,votes in grouped.items()}
def completeness_packet(draft:str,findings:list[dict],rejected:list[dict],sources:dict[str,str]|None=None)->dict:
    packet={"draft":draft,"confirmed_findings":findings,"rejected_findings":rejected,"sources":sources or {},"execution_mode":"MOCK_ONLY","provider_request_id":None}
    packet["input_sha256"]=digest(json.dumps(packet,ensure_ascii=False,sort_keys=True))
    return packet
def review_offline(draft:str,sources:dict[str,str],verifier_votes:dict[str,list[str]]|None=None,completeness_findings:list[dict]|None=None)->dict:
    lenses=[mock_lens(lens_packet(n,draft,sources)) for n in LENSES]
    raw=[]
    for layer in ("surface","structural"):
        raw.extend({**f,"finding_id":f"{layer}-{i+1}","layer":layer} for i,f in enumerate(lint(draft,layer)["findings"]))
    votes=verifier_votes or {}
    vpack=verifier_packets(raw,draft,sources)
    verdicts=[{**p,"votes":[{"finding_id":f["finding_id"],"verdict":votes.get(p["verifier_id"],[])[i] if i<len(votes.get(p["verifier_id"],[])) else "uncertain"} for i,f in enumerate(raw)]} for p in vpack]
    vote_result=tally_verifiers(verdicts) if raw else {}
    votes_by_id={}
    for verdict in verdicts:
        for vote in verdict["votes"]: votes_by_id.setdefault(vote["finding_id"],[]).append(vote["verdict"])
    confirmed=[]; rejected=[]
    for finding in raw:
        statuses=votes_by_id.get(finding["finding_id"],[])
        item={**finding,"verifier_votes":statuses}
        (confirmed if sum(v=="not_refuted" for v in statuses)>=2 else rejected).append(item)
    complete=completeness_packet(draft,confirmed,rejected,sources)
    complete["candidate_findings"]=completeness_findings or []
    complete["input_sha256"]=digest(json.dumps({k:v for k,v in complete.items() if k!="input_sha256"},ensure_ascii=False,sort_keys=True))
    all_hashes=[x["input_sha256"] for x in lenses]
    if len(set(all_hashes))!=5: raise AssertionError("lens packets must be distinct")
    return {"execution_mode":"MOCK_ONLY","provider_request_ids":[],"lenses":lenses,"lint_findings":raw,"verifiers":verdicts,"verifier_summary":vote_result,"completeness":complete,"text_modified":False,"review_status":"OFFLINE_SIMULATION_ONLY"}
def main():
    p=argparse.ArgumentParser(); p.add_argument("draft",type=Path); p.add_argument("--sources",type=Path,required=True); p.add_argument("--output",type=Path,required=True); a=p.parse_args()
    result=review_offline(a.draft.read_text(encoding="utf-8-sig"),json.loads(a.sources.read_text(encoding="utf-8-sig")))
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
if __name__=="__main__":main()
