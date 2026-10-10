"""Bounded P2-06 Flash prose call. Stores exact private request/response and settles campaign ledger."""
from __future__ import annotations
import importlib.util, json, os, re, uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RUN_ID='p2-06-draft-20261010'
OUT=ROOT/'runs'/RUN_ID
if OUT.exists(): raise SystemExit('RUN_DIRECTORY_EXISTS')
if not os.environ.get('DEEPSEEK_API_KEY'): raise SystemExit('DEEPSEEK_API_KEY_REQUIRED')
brief=(ROOT/'workspace/cangqi/07_draft/ep001_writing_brief.md').read_text(encoding='utf-8-sig')
nk=(ROOT/'workspace/cangqi/05_scene_cards/ep001_nk_perspective.md').read_text(encoding='utf-8-sig')
spec=importlib.util.spec_from_file_location('p2_cost_guard',ROOT/'tools/p2_cost_guard.py')
guard=importlib.util.module_from_spec(spec); spec.loader.exec_module(guard)
from openai import OpenAI
request_id='p206-draft-'+uuid.uuid4().hex
cap_in,cap_out=12000,2048
class Args: pass
reserve=Args(); reserve.request_id=request_id; reserve.run_id=RUN_ID; reserve.purpose='P2-06 Flash complete-scene v0 generation'; reserve.input_token_cap=cap_in; reserve.output_token_cap=cap_out
guard.command_reserve(reserve)
OUT.mkdir(parents=True,exist_ok=False)
system=('你是中文互动小说场景写作者。严格遵循用户提供的 Writing Brief。只输出完整场景正文，不输出解释、标题以外的元信息或过程。'
        '君天离是唯一第一人称限制视角；不得写其他人内心/动机。插场新增内容都保持候选、非Canon；不写外传秘密或J20内容。'
        '正文须完整收束，并在稿件之外由流程恢复原 J19 玩法/选择。')
user='以下是本场 Writing Brief：\n\n'+brief+'\n\n下列 NK 提示已由 Controller 检查，仅作 POV 边界参考：\n'+nk+'\n\n请写 EP001 唯一完整场景，约500–700中文字符，动作清楚、自然克制。'
try:
    client=OpenAI(api_key=os.environ['DEEPSEEK_API_KEY'],base_url='https://api.deepseek.com/v1',max_retries=0,timeout=90)
    resp=client.chat.completions.create(model='deepseek-flash',messages=[{'role':'system','content':system},{'role':'user','content':user}],temperature=0.7,max_tokens=cap_out,extra_body={'thinking':{'type':'disabled'}})
    choice=resp.choices[0]; content=choice.message.content or ''; usage=resp.usage
    if resp.model!='deepseek-flash' or choice.finish_reason!='stop' or not content.strip(): raise RuntimeError('DRAFT_PROVIDER_RESULT_INVALID')
    (ROOT/'workspace/cangqi/07_draft/ep001_v0.md').write_text(content.rstrip()+'\n',encoding='utf-8')
    evidence={'request_id':request_id,'run_id':RUN_ID,'request':{'model':'deepseek-flash','messages':[{'role':'system','content':system},{'role':'user','content':user}],'temperature':0.7,'max_tokens':cap_out,'reasoning_effort':'none'},'response':resp.model_dump(mode='json')}
    response=evidence['response']
    for ch in response.get('choices',[]):
        msg=ch.get('message') or {}
        msg.pop('reasoning_content',None)
    (OUT/'provider-call.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    settle=Args(); settle.request_id=request_id; settle.provider_request_id=resp.id; settle.returned_model=resp.model; settle.finish_reason=choice.finish_reason; settle.input_tokens=usage.prompt_tokens; settle.output_tokens=usage.completion_tokens
    guard.command_settle(settle)
    (OUT/'run_receipt.json').write_text(json.dumps({'status':'SUCCEEDED','request_id':request_id,'provider_request_id':resp.id,'model':resp.model,'finish_reason':choice.finish_reason,'input_tokens':usage.prompt_tokens,'output_tokens':usage.completion_tokens,'scene_chars':len(content)},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'SUCCEEDED','run_id':RUN_ID,'provider_request_id':resp.id,'input_tokens':usage.prompt_tokens,'output_tokens':usage.completion_tokens,'scene_chars':len(content)},ensure_ascii=False))
except Exception as e:
    settle=Args(); settle.request_id=request_id; settle.provider_request_id=None; settle.returned_model=None; settle.finish_reason=None; settle.input_tokens=None; settle.output_tokens=None
    guard.command_settle(settle)
    (OUT/'run_error.json').write_text(json.dumps({'status':'FAILED_OR_UNKNOWN','request_id':request_id,'error_type':type(e).__name__},indent=2)+'\n',encoding='utf-8')
    raise
