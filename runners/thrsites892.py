# -*- coding: utf-8 -*-
"""노트 892 곁가지 — **옛 문턱 0.0045 가 어디에서 아직 판정을 하고 있나를 센다**.

티처 #54 M6: *'새 문턱의 배선처가 0곳이다. 옛 `0.0045` 는 `.py` 92행/46파일이고 그중
살아 있는 판정 ≥17파일.'* 그런데 **'살아 있는'의 정의가 적혀 있지 않았다** --- 그래서
여기서 정의를 코드로 못박고 센다. 인용·주석·원장·논문의 0.0045 는 **역사 기록이라 안 고친다**.

분류(줄 단위):
    주석      `#` 로 시작하는 줄 --- **역사**
    글        삼중따옴표 안(모듈/함수 독스트링) --- **역사**
    보고      코드지만 0.0045 가 **출력 딕트의 값**일 뿐(`"문턱": 0.0045`) --- 그 노트의 기록
    판정      코드이고 0.0045 가 **비교에 쓰인다**(`> 0.0045`, `abs(x) <= 0.0045`, …)
    배선      0.0045 가 **다른 상수로 스케일링**된다(`0.0045 * sqrt(...)`) --- 티처 #54 의 파생 결함

도달성:
    라이브러리  `lab/ serve/ ingest/ core/ harness/ state/` --- **항상 살아 있다**
    러너 main   `runners/*.py` 의 `main()` 안 --- 그 노트를 다시 돌릴 때만 산다
    러너 임포트  다른 모듈이 임포트하는 러너의 **모듈 수준/함수** 코드 --- 살아 있다

🔴 **`runners/ff753.py:211-229` 에 대하여**: 티처는 *'새 자를 재는 러너가 옛 자로 판정하는
모듈을 자료원으로 썼다'* 고 적었다. 세어 보면 ff753 은 **57개 파일이 임포트**하지만 그
0.0045 는 전부 `main()` **안**에 있고 `ff753.main()` 을 부르는 곳은 **0곳**이다(임포터는
`base()`·`shell()`·`board()` 만 쓴다). 그러므로 그 줄들은 **노트 753 의 역사 기록**이고
파생 오염이 아니다. 티처 #54 M6 의 이 대목은 **부분 철회**한다.
"""
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
OUT = ROOT / "data/lab/thresh_sites_892.json"
OLD = "0.0045"
LIB_DIRS = ("lab", "serve", "ingest", "core", "harness", "state", "viz")
CMP = re.compile(r"[<>]=?\s*0\.0045|0\.0045\s*[<>]=?|==\s*0\.0045")
SCALE = re.compile(r"0\.0045\s*[*/]|[*/]\s*0\.0045")


def string_lines(path, src):
    """삼중따옴표 문자열(독스트링 포함)이 차지하는 줄 번호 집합."""
    out = set()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            lo = getattr(node, "lineno", None)
            hi = getattr(node, "end_lineno", lo)
            if lo and hi and hi > lo:            # 여러 줄 문자열만
                out.update(range(lo, hi + 1))
    return out


def classify(line, in_str, in_comment):
    if in_comment:
        return "주석"
    if in_str:
        return "글"
    if SCALE.search(line):
        return "🔴 배선"
    if CMP.search(line):
        return "🔴 판정"
    return "보고"


def reach(rel, lineno, src_lines, func_of):
    if rel.split("/")[0] in LIB_DIRS:
        return "라이브러리(항상 산다)"
    fn = func_of.get(lineno)
    if rel.startswith("runners/"):
        return "러너 main(그 노트를 다시 돌릴 때만)" if fn == "main" \
            else f"러너 모듈/함수 `{fn or '모듈수준'}`"
    return "논문·그림(역사)"


def func_map(src):
    """줄 번호 → 그 줄을 감싸는 최상위 함수 이름."""
    m = {}
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return m
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for ln in range(node.lineno, (node.end_lineno or node.lineno) + 1):
                m.setdefault(ln, node.name)
    return m


def scan():
    rows = []
    for p in sorted(ROOT.rglob("*.py")):
        rel = str(p.relative_to(ROOT))
        if rel.startswith(".") or "/.git/" in rel:
            continue
        src = p.read_text(errors="replace")
        if OLD not in src:
            continue
        lines = src.splitlines()
        sl = string_lines(p, src)
        fm = func_map(src)
        for i, line in enumerate(lines, 1):
            if OLD not in line:
                continue
            rows.append({
                "파일": rel, "줄": i,
                "분류": classify(line, i in sl, line.lstrip().startswith("#")),
                "도달": reach(rel, i, lines, fm),
                "본문": line.strip()[:180],
            })
    return rows


def main():
    rows = scan()
    kinds = {}
    for r in rows:
        kinds.setdefault(r["분류"], []).append(f"{r['파일']}:{r['줄']}")
    live = [r for r in rows
            if r["분류"] in ("🔴 판정", "🔴 배선")
            and not r["도달"].startswith("러너 main")]
    runner_main = [r for r in rows if r["분류"] in ("🔴 판정", "🔴 배선")
                   and r["도달"].startswith("러너 main")]
    out = {
        "노트": 892,
        "무엇": "옛 문턱 0.0045 의 전수 조사 --- 무엇이 역사이고 무엇이 살아 있는 판정인가",
        "총 줄": len(rows),
        "총 파일": len(set(r["파일"] for r in rows)),
        "분류별 줄 수": {k: len(v) for k, v in sorted(kinds.items())},
        "🔴 살아 있는 판정·배선(= 고칠 후보)": live,
        "러너 main 안의 판정(= 그 노트의 역사 · 안 고친다)": {
            "줄 수": len(runner_main),
            "파일": sorted(set(r["파일"] for r in runner_main)),
        },
        "ff753 검산": {
            "ff753 을 임포트하는 파일 수":
                len([q for q in ROOT.rglob("*.py")
                     if q.name not in ("ff753.py", Path(__file__).name)
                     and re.search(r"import ff753\b", q.read_text(errors="replace"))]),
            #: 🔴 이 검사기 자신을 빼지 않으면 **자기 정규식에 자기가 걸린다**(초판이 1을 냈다)
            "ff753.main() 을 부르는 곳":
                len([q for q in ROOT.rglob("*.py")
                     if q.name != Path(__file__).name
                     and re.search(r"(FF|ff753)\.main\(", q.read_text(errors="replace"))]),
            "ff753 의 0.0045 가 든 함수":
                sorted(set(r["도달"] for r in rows if r["파일"] == "runners/ff753.py")),
            "결론": "임포터는 base()·shell()·board() 만 쓴다 --- ff753 의 0.0045 는 "
                  "노트 753 의 역사 기록이고 파생 오염이 아니다(티처 #54 M6 부분 철회)",
        },
        "전량": rows,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "전량"},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
