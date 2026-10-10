"""Deterministic Chinese prose lint. Findings are candidates; source text is immutable."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

SURFACE = [
    ("PLACEHOLDER", re.compile(r"(?:TODO|FIXME|待补充|此处填写|[\[【](?:待填|占位|PLACEHOLDER)[\]】])", re.I)),
    ("RESIDUAL_INSTRUCTION", re.compile(r"(?:根据.{0,12}要求.{0,8}续写|以下是.{0,8}正文|作为AI|作为语言模型)")),
    ("DOUBLE_SPACE", re.compile(r" {2,}")),
    ("TRAILING_WHITESPACE", re.compile(r"[ \t]+$")),
    ("REPEATED_PUNCTUATION", re.compile(r"[！？。]{2,}|[，、；：]{2,}")),
]
STRUCTURAL = [
    ("NEGATION_REFRAME", re.compile(r"(?:并非|不是|不只是).{1,24}[，，—：:；;，]?(?:而是|而|只是)")),
    ("ABSTRACT_EMOTION", re.compile(r"(?:感到|觉得|显得)(?:很|十分|异常)?(?:愤怒|悲伤|难过|害怕|紧张|失望|欣慰)")),
    ("REALIZATION_CLICHE", re.compile(r"(?:就在这时|那一刻).{0,16}(?:意识到|明白了|终于懂得)")),
    ("SIMILE_CLICHE", re.compile(r"仿佛.{0,18}(?:一般|一样)")),
    ("EMPTY_SUMMARY", re.compile(r"(?:一切都结束了|事情就这样过去了|这就是人生)")),
]

def lint(text: str, layer: str) -> dict:
    rules = SURFACE if layer == "surface" else STRUCTURAL if layer == "structural" else None
    if rules is None: raise ValueError("layer must be surface or structural")
    lines=text.splitlines(); findings=[]
    for n,line in enumerate(lines,1):
        for rule,rx in rules:
            for match in rx.finditer(line):
                findings.append({"rule_id":rule,"line":n,"matched_text":match.group(0),"context":lines[max(0,n-2):min(len(lines),n+1)],"disposition":"CANDIDATE_ONLY"})
    return {"layer":layer,"findings":findings,"source_sha256":__import__('hashlib').sha256(text.encode()).hexdigest(),"text_modified":False}

def main():
    p=argparse.ArgumentParser(); p.add_argument("layer",choices=("surface","structural")); p.add_argument("source",type=Path); p.add_argument("--output",type=Path); a=p.parse_args()
    result=lint(a.source.read_text(encoding="utf-8-sig"),a.layer); raw=json.dumps(result,ensure_ascii=False,indent=2)
    if a.output: a.output.write_text(raw+"\n",encoding="utf-8")
    else: print(raw)
if __name__=="__main__": main()
