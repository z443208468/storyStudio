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

def project_rules(path: Path, layer: str) -> tuple[list, list]:
    """Read executable regex cells from the author's layered Markdown tables.

    Prose-only descriptions remain semantic review items, never guessed regex.
    A cap applies to the whole chapter, as specified by the public template.
    """
    rules, semantic = [], []
    active = False
    columns = []
    wanted = "1" if layer == "surface" else "2"
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        heading = re.match(r"^##\s+Layer\s+(\d+)", line, re.I)
        if heading:
            active = heading.group(1) == wanted
            columns = []
        if not active or not line.strip().startswith("|"):
            continue
        # A regex may contain pipes. Split only outside inline-code spans.
        cells, cell, in_code = [], [], False
        for char in line.strip().strip("|"):
            if char == "`":
                in_code = not in_code
            if char == "|" and not in_code:
                cells.append("".join(cell).strip()); cell = []
            else:
                cell.append(char)
        cells.append("".join(cell).strip())
        if not columns or cells[0].lower() == "rule":
            columns = [value.lower() for value in cells]
            continue
        if all(re.fullmatch(r"[:\- ]+", value) for value in cells):
            continue
        if len(cells) < 2 or cells[0].startswith("<"):
            continue
        pattern_column = next((i for i, name in enumerate(columns) if name.startswith("pattern")), None)
        pattern = re.match(r"^`([^`]+)`", cells[pattern_column]) if pattern_column is not None and pattern_column < len(cells) else None
        if not pattern:
            semantic.append({"rule_id": cells[0], "source_line": number, "description": cells[1]})
            continue
        cap_column = next((i for i, name in enumerate(columns) if name == "cap"), None)
        cap_text = cells[cap_column] if cap_column is not None and cap_column < len(cells) else "0"
        cap_match = re.match(r"^(\d+)(?:\s|$)", cap_text)
        if not cap_match:
            raise ValueError(f"Invalid lint cap at {path}:{number}")
        # Markdown escapes alternation in table cells; Python regex needs |.
        regex = pattern.group(1).replace(r"\|", "|")
        rules.append((cells[0], re.compile(regex), int(cap_match.group(1)), number))
    return rules, semantic


def lint(text: str, layer: str, rules_path: str | Path | None = None) -> dict:
    rules = SURFACE if layer == "surface" else STRUCTURAL if layer == "structural" else None
    if rules is None: raise ValueError("layer must be surface or structural")
    semantic = []
    if rules_path is not None:
        rules, semantic = project_rules(Path(rules_path), layer)
    else:
        rules = [(name, rx, 0, None) for name, rx in rules]
    lines=text.splitlines(); findings=[]
    for rule,rx,cap,source_line in rules:
        count = 0
        for n,line in enumerate(lines,1):
            for match in rx.finditer(line):
                count += 1
                if count > cap:
                    findings.append({"rule_id":rule,"line":n,"matched_text":match.group(0),"context":lines[max(0,n-2):min(len(lines),n+1)],"disposition":"CANDIDATE_ONLY","cap":cap,"rule_source_line":source_line})
    return {"layer":layer,"findings":findings,"source_sha256":__import__('hashlib').sha256(text.encode()).hexdigest(),"text_modified":False,
            "status":"NO_EXECUTABLE_RULES" if not rules else "LINT_COMPLETE" if findings else "LINT_CLEAN",
            "rules_source":str(rules_path) if rules_path else "LEGACY_DEFAULTS",
            "rules_sha256":__import__('hashlib').sha256(Path(rules_path).read_bytes()).hexdigest() if rules_path else None,
            "executable_rule_count":len(rules),"semantic_review_items":semantic}

def main():
    p=argparse.ArgumentParser(); p.add_argument("layer",choices=("surface","structural")); p.add_argument("source",type=Path); p.add_argument("--output",type=Path); p.add_argument("--rules",type=Path); a=p.parse_args()
    result=lint(a.source.read_text(encoding="utf-8-sig"),a.layer,a.rules); raw=json.dumps(result,ensure_ascii=False,indent=2)
    if a.output: a.output.write_text(raw+"\n",encoding="utf-8")
    else: print(raw)
if __name__=="__main__": main()
