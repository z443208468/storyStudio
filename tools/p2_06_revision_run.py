"""Bounded Flash revision for P2-06; one same-scene v1 revision from classified feedback."""
from __future__ import annotations
import importlib.util,json,os,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; RUN_ID='p2-06-revise-20261010'; OUT=ROOT/'runs'/RUN_ID
if OUT.exists(): raise SystemExit('RUN_DIRECTORY_EXISTS')
if not os.environ.get('DEEPSEEK_API_KEY'): raise SystemExit('DEEPSEEK_API_KEY_REQUIRED')
brief=(ROOT/'workspace/cangqi/07_draft/ep001_writing_brief.md').read_text(encoding='utf-8-sig')
v0=(ROOT/'workspace/cangqi/07_draft/ep001_v0.md').read_text(encoding='utf-8-sig')
classification=(ROOT/'workspace/cangqi/07_draft/ep001_revision_classification.md').read_text(encoding='utf-8-sig')
spec=importlib.util.spec_from_file_location('p2_cost_guard',ROOT/'tools/p2_cost_guard.py'); guard=importlib.util.module_from_spec(spec); spec.loader.exec_module(guard)
from openai import OpenAI
request_id='p206-revise-'+uuid.uuid4().hex
class Args: pass
r=Args(); r.request_id=request_id; r.run_id=RUN_ID; r.purpose='P2-06 Flash revise same complete scene to v1'; r.input_token_cap=12000; r.output_token_cap=2048; guard.command_reserve(r)
OUT.mkdir(parents=True,exist_ok=False)
system='按场景 Brief 和已分类的评审决策，对完整 v0 做一次定向修订，输出同一场景完整 v1 正文，不要解释。严格君天离第一人称限制 POV。不得复活被拒建议；不添加读心、关系解释、J19/J20之外状态变化或 Brief 未要求的额外场后动作。只保留同一连续场景，场景中新设细节仍是候选非Canon。'
user='SCENE BRIEF:\n'+brief+'\n\nCLASSIFIED FEEDBACK:\n'+classification+'\n\nCOMPLETE SCENE v0:\n'+v0+'\n\n请给出完整修订稿。'
try:
 c=OpenAI(api_key=os.environ['DEEPSEEK_API_KEY'],base_url='https://api.deepseek.com/v1',max_retries=0,timeout=90)
 resp=c.chat.completions.create(model='deepseek-flash',messages=[{'role':'system','content':system},{'role':'user','content':user}],temperature=0.3,max_tokens=2048,extra_body={'thinking':{'type':'disabled'}})
 choice=resp.choices[0]; content=choice.message.content or ''; u=resp.usage
 if resp.model!='deepseek-flash' or choice.finish_reason!='stop' or not content.strip(): raise RuntimeError('REVISION_PROVIDER_RESULT_INVALID')
 (ROOT/'workspace/cangqi/07_draft/ep001_v1.md').write_text(content.rstrip()+'\n',encoding='utf-8')
 raw=resp.model_dump(mode='json')
 for ch in raw.get('choices',[]): (ch.get('message') or {}).pop('reasoning_content',None)
 (OUT/'provider-call.json').write_text(json.dumps({'request_id':request_id,'run_id':RUN_ID,'request':{'model':'deepseek-flash','system':system,'user':user,'max_tokens':2048,'reasoning_effort':'none'},'response':raw},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 s=Args(); s.request_id=request_id; s.provider_request_id=resp.id; s.returned_model=resp.model; s.finish_reason=choice.finish_reason; s.input_tokens=u.prompt_tokens; s.output_tokens=u.completion_tokens; guard.command_settle(s)
 (OUT/'run_receipt.json').write_text(json.dumps({'status':'SUCCEEDED','request_id':request_id,'provider_request_id':resp.id,'model':resp.model,'finish_reason':choice.finish_reason,'input_tokens':u.prompt_tokens,'output_tokens':u.completion_tokens,'scene_chars':len(content)},indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'status':'SUCCEEDED','run_id':RUN_ID,'provider_request_id':resp.id,'input_tokens':u.prompt_tokens,'output_tokens':u.completion_tokens,'scene_chars':len(content)}))
except Exception as e:
 s=Args(); s.request_id=request_id; s.provider_request_id=None; s.returned_model=None; s.finish_reason=None; s.input_tokens=None; s.output_tokens=None; guard.command_settle(s)
 (OUT/'run_error.json').write_text(json.dumps({'status':'FAILED_OR_UNKNOWN','request_id':request_id,'error_type':type(e).__name__},indent=2)+'\n',encoding='utf-8'); raise
