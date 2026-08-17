#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""986 §1·§4 — 🔴🔴🔴 **985 의 세 오기를 다시 재고, 손 전사 자의 분모를 넓힌다**.

담는 것 다섯:

- **§A** 🔴🔴🔴 **985 의 세 오기를 «잰다»**(되돌리지 않고 정정으로 얹는다) ---
  반증조건 `13 / 14` 대 정본 `14 / 14` · 「끊은 자리」 통과 `1` 대 `2` ·
  소비자 `447 → 350` 대 `446 → 349`.
- **§B** 🔴🔴 **PR #243 본문 대 985 문서** --- 네 자리가 어긋났다는 티처 #124 C2 를 «잰다».
- **§C** 🔴🔴🔴 **`[수리] R3` --- 손 전사(AST) 자의 분모를 「이 사이클 러너 전량」으로.**
  985 의 자는 **치환표 생성기 한 파일**만 훑어 `audit985.py:170` 의 하드코딩
  `= 3` 을 **원리상 못 봤다**(실제 합은 **4**).
- **§D** 🔴🔴 **`[수리] R1` --- `⑤′` 절 1 「소비자」의 구판/신판 분모**를 나란히 낸다
  (`조항 60-나` 개정판 요건 ②·③).
- **§E** 🔴 **즉시 정정** --- `조항 60-나` 원문의 포인터 · F5 분모 · 표 칸 깨짐.

씀:
    python3 runners/audit986.py --stage audit --ref <40자 sha>
"""
import argparse
import ast
import collections
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import cycle986 as CY                                  # noqa: E402
import cycle985 as CY5                                 # noqa: E402
import audit985 as A5                                  # noqa: E402
import fiveprime902 as F                               # noqa: E402

OUT = "runners/out986_audit.json"
DEN = "data/lab/denominator.json"
BODY985 = ("docs/판정_985.md", "docs/card_985.md", "docs/handoff_985.md")
PR985 = 243

#: 🔴🔴🔴 **R3 의 바늘** --- 「서식 문자열 안에 «산술 자리»의 맨 수를 박았나」.
#:  `"통과 %d + 분모 제거 1 + 거짓 %d = 3"` 이 정확히 이 꼴이다(`audit985.py:170`).
#:  🔴 **`%`/f-string 자리표가 «있는데»** 그 옆에 **`= 3`·`+ 1`·`/ 17`** 같은
#:  맨 수가 있으면, 그 수는 **계산이 아니라 손으로 박은 것**이다.
ARITH_LIT = re.compile(r"(?:^|[^%\w.])([=+×÷/−-])\s*(\d+(?:\.\d+)?)(?![\w.%])")
PLACEHOLDER = re.compile(r"%[-#0-9. +]*[sdifgeSDIFGE]|\{[^{}]*\}")


def _load(rel):
    p = ROOT / rel
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def _text(rel):
    p = ROOT / rel
    return p.read_text(encoding="utf-8") if p.is_file() else None


# ══════════════════════════════════════════════════════════════════════
# §A 🔴🔴🔴 985 의 세 오기 --- 정정으로 «얹는다»
# ══════════════════════════════════════════════════════════════════════
def three_errata():
    sc = _load("runners/out985_score.json") or {}
    au = _load("runners/out985_audit.json") or {}
    f6 = sc.get("§6 🔴 반증조건") or {}
    canon = f6.get("🔴🔴 분자 / 분모")
    canon_bad = f6.get("🔴🔴 반증된 조건")
    # ── ① 반증조건 --- 문서가 실은 값을 «읽어» 센다 ────────────────
    docs = {}
    for p in BODY985:
        t = _text(p) or ""
        docs[p] = {"「13 / 14」가 있나": ("13 / 14" in t),
                   "「14 / 14」가 있나": ("14 / 14" in t)}
    n_13 = len([1 for v in docs.values() if v["「13 / 14」가 있나"]])
    # ── ② 「끊은 자리」 --- 하드코딩 문자열과 «실제 합» ────────────────
    sb = (au.get("§B 🔴 「끊은 자리」를 갈라 센다 · 공통 17")
          or au.get("§B 🔴 「끊은 자리」") or {})
    if not sb:
        for k, v in au.items():
            if k.startswith("§B") and isinstance(v, dict):
                sb = v
                break
    inner = None
    for k, v in (sb or {}).items():
        if "갈라 세면" in k and isinstance(v, dict):
            inner = v
            break
    n_pass = (inner or {}).get("① 수")
    n_drop = (inner or {}).get("② 수")
    n_false = (inner or {}).get("③ 수")
    hard = None
    for k, v in (inner or {}).items():
        if "「셋」의 정체" in k:
            hard = v
    real = None
    if all(isinstance(x, int) for x in (n_pass, n_drop, n_false)):
        real = n_pass + n_drop + n_false
    hard_n = None
    if isinstance(hard, str):
        m = re.search(r"=\s*(\d+)", hard)
        hard_n = int(m.group(1)) if m else None
    # ── ③ 소비자 --- `fiveprime_985_cert.json` 의 «잰» 값 ─────────────
    cert = _load("runners/fiveprime_985_cert.json") or {}
    sec1 = cert.get("1 소비자 역참조") or {}
    n_cons = sec1.get("🔴 분모 ② 역참조 소비자 수")
    n_py = sec1.get("🔴 분모 ②-py 역참조 소비자 중 .py")
    cons = sec1.get("역참조 소비자(전량)") or []
    minus_den = len([c for c in cons if c != DEN])
    minus_den_py = len([c for c in cons if c != DEN and c.endswith(".py")])
    pr_txt = pr_body()
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴🔴 **985 의 세 오기를 «잰다»** --- 되돌리지 않고 정정으로 얹는다"),
        ("① 반증조건", collections.OrderedDict([
            ("🔴🔴🔴 정본(`out985_score.json` §6)", canon),
            ("🔴🔴 정본의 「반증된 조건」", canon_bad),
            ("🔴 985 문서가 실은 값", "13 / 14"),
            ("🔴 문서별", docs),
            ("🔴🔴 「13 / 14」를 실은 문서 수", n_13),
            ("🔴🔴🔴 어긋나나", bool(canon is not None and n_13 > 0 and canon != "13 / 14")),
            ("🔴 기전", "🔴 **`note985_gen` 이 `09:40:04` 에 표·문서를 찍고 `score985` 가 "
                     "`09:40:06` 에 다시 돌았는데 아무도 문서를 다시 안 찍었다.** "
                     "🔴 **986 의 `cycle986.stale_docs` 가 정확히 이것을 잡는다**"),
        ])),
        ("② 「끊은 자리」", collections.OrderedDict([
            ("🔴 통과로 «실제로» 바뀐 수", n_pass),
            ("🔴 분모에서 «뺀» 수", n_drop),
            ("🔴 다시 재니 «거짓»인 수", n_false),
            ("🔴🔴🔴 셋의 실제 합", real),
            ("🔴🔴 `out985_audit.json` 이 실은 문자열", hard),
            ("🔴🔴 그 문자열이 못 박은 수", hard_n),
            ("🔴🔴🔴 어긋나나", bool(real is not None and hard_n is not None and real != hard_n)),
            ("🔴 PR #243 본문이 실은 통과 수", 1 if (pr_txt and "통과 1 + 분모 제거" in pr_txt)
             else ("🔴 못 읽었다" if pr_txt is None else "🔴 그 문자열이 없다")),
            ("🔴🔴 정본 통과 수", n_pass),
        ])),
        ("③ `⑤′` 절 1 소비자", collections.OrderedDict([
            ("🔴🔴🔴 정본 소비자 수(`fiveprime_985_cert.json` 에서 읽었다)", n_cons),
            ("🔴 그중 .py", n_py),
            ("🔴🔴🔴 원장을 뺀 판", minus_den),
            ("🔴 원장을 뺀 판의 .py", minus_den_py),
            ("🔴 PR #243 본문이 실은 값", "447 → 350"),
            ("🔴 PR #243 본문이 실은 값(.py)", ".py 147 → 103"),
            ("🔴 그 값의 정체", "🔴 **사전등록 §4-6 의 「측정 «전»」 탐색값이다** --- "
                           "985 의 어디에도 왜 달라졌는지가 없다(티처 #124 C2)"),
            ("🔴🔴🔴 어긋나나", bool(n_cons is not None and n_cons != 447)),
        ])),
        ("통과", bool(canon is not None and real is not None and n_cons is not None)),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **세 오기의 «정본 값»을 셋 다 산출물에서 읽었는가.** 하나라도 못 읽으면 "
         "「0 이다」가 아니라 「모른다」라 불통과다(조항 59)"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §B 🔴🔴 PR #243 본문 대 985 문서
# ══════════════════════════════════════════════════════════════════════
def pr_body(n=PR985):
    try:
        return subprocess.check_output(
            ["gh", "pr", "view", str(n), "--json", "body", "-q", ".body"],
            cwd=str(ROOT), stderr=subprocess.DEVNULL).decode("utf-8")
    except Exception:                                              # noqa: BLE001
        return None


def pr_vs_docs():
    txt = pr_body()
    if txt is None:
        return collections.OrderedDict([
            ("🔴", "🔴 **PR 본문을 못 읽었다** --- 「어긋난 것이 없다」가 아니라 "
                  "「모른다」다(조항 59)"),
            ("통과", False),
            ("🔴 이 절의 `통과` 가 뜻하는 것", "🔴 **PR 본문을 «읽었는가»** 하나다"),
        ])
    joined = "\n".join(_text(p) or "" for p in BODY985)
    #: 🔴 (PR 본문이 적은 문자열, 985 문서·정본이 적은 문자열). 둘 다 있으면 «어긋난» 것이다.
    needles = collections.OrderedDict([
        ("반증조건 분자/분모", ("반증조건 14 / 14", "13 / 14")),
        ("「끊은 자리」 통과 수", ("통과 1 + 분모 제거 1", "2 / 1 / 1")),
        ("소비자 분모", ("447 → 350", "446")),
        ("소비자 분모 · `.py`", (".py 147 → 103", "349")),
    ])
    rows, bad = collections.OrderedDict(), []
    for name, (in_pr, in_doc) in needles.items():
        a = in_pr in txt
        b = in_doc in joined
        rows[name] = {"PR 본문에 `%s` 가 있나" % in_pr: a,
                      "985 문서에 `%s` 가 있나" % in_doc: b,
                      "🔴 어긋나나": bool(a and b)}
        if a and b:
            bad.append(name)
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴 **PR #%d 본문이 문서와 다른가**(티처 #124 C2)" % PR985),
        ("🔴 PR 본문 글자 수", len(txt)),
        ("🔴 985 문서 셋 글자 수 합", len(joined)),
        ("🔴 자리별", rows),
        ("🔴🔴🔴 어긋난 자리 수", len(bad)),
        ("🔴🔴 어긋난 자리", bad or "없음"),
        ("🔴🔴🔴 그래서 986 이 하는 것",
         "🔴 **PR 본문을 규칙 D 분모에 넣고 «치환표에서 짓는다»**(사전등록 §2-2). "
         "985 는 다섯 자리를 완벽히 고쳤는데 **어떤 자도 안 덮는 여섯째 자리**를 남겼다"),
        ("통과", True),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "🔴 **PR 본문을 읽고 자리별로 «쟀는가»** 하나다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §C 🔴🔴🔴 R3 --- 손 전사 자의 분모를 「이 사이클 러너 전량」으로
# ══════════════════════════════════════════════════════════════════════
def _doc_ids(tree):
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef,
                          ast.AsyncFunctionDef)):
            body = getattr(n, "body", None)
            if body and isinstance(body[0], ast.Expr) \
                    and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                out.add(id(body[0].value))
    return out


def _fmt_literals(rel):
    """🔴 **서식 문자열 안의 «산술 자리» 맨 수**를 찾는다(R3 의 신판 자).

    조건 둘을 **다** 만족할 때만 잡는다:
    ① 그 문자열에 `%d`·`{}` 같은 **자리표**가 있다(= 무언가를 «계산해» 채운다) ·
    ② 그런데 **`= 3`·`+ 1`·`/ 17`** 처럼 **맨 수**가 산술 자리에 있다.

    🔴 **`audit985.py:170` 의 `"통과 %d + 분모 제거 1 + 거짓 %d = 3"` 이 정확히 이 꼴이다.**
    독스트링은 뺀다(산문이다).
    """
    txt = _text(rel)
    if txt is None:
        return None, "🔴 파일이 없다"
    try:
        tree = ast.parse(txt)
    except SyntaxError as e:                                       # noqa: BLE001
        return None, "🔴 파싱 실패: %s" % e
    docs = _doc_ids(tree)
    hits = []
    for n in ast.walk(tree):
        vals = []
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs:
            vals.append((n, n.value))
        elif isinstance(n, ast.JoinedStr):
            s = "".join(p.value for p in n.values
                        if isinstance(p, ast.Constant) and isinstance(p.value, str))
            vals.append((n, s + "{}"))
        for node, s in vals:
            if not PLACEHOLDER.search(s):
                continue
            for m in ARITH_LIT.finditer(s):
                hits.append({"줄": getattr(node, "lineno", None),
                             "부호": m.group(1), "맨 수": m.group(2),
                             "보기": s[max(0, m.start() - 40):m.end() + 20]})
    return hits, None


def _table_literals(rel):
    """⚠ **구판 자**(985 R2 · `ast_table_hits`) --- `T[...] = <수>` 하나만 본다."""
    txt = _text(rel)
    if txt is None:
        return None
    try:
        tree = ast.parse(txt)
    except SyntaxError:
        return None
    hits = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant) \
                and isinstance(n.value.value, (int, float)) \
                and not isinstance(n.value.value, bool):
            for t in n.targets:
                if isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name) \
                        and t.value.id == "T":
                    hits.append({"줄": n.lineno, "값": n.value.value})
    return hits


def hand_transcription():
    rows_new, rows_old = collections.OrderedDict(), collections.OrderedDict()
    tot_new, unread = 0, []
    for rel in CY.RAN_986:
        hits, err = _fmt_literals(rel)
        if hits is None:
            rows_new[rel] = {"🔴": err}
            unread.append(rel)
            continue
        rows_new[rel] = {"자리 수": len(hits), "자리": hits or "없음"}
        tot_new += len(hits)
    # 🔴 **구판/신판 전후**(조항 66-③) --- 985 의 분모(치환표 생성기 하나)로도 잰다
    old_target = "runners/note985_gen.py"
    rows_old[old_target] = {"자리 수": len(_table_literals(old_target) or []),
                            "자리": _table_literals(old_target) or "없음"}
    # 🔴 **검정력 시연** --- 같은 신판 자를 985 의 러너에 물린다. 안 걸리면 자가 아니다.
    demo = collections.OrderedDict()
    demo_tot = 0
    for rel in CY5.RAN_985:
        hits, err = _fmt_literals(rel)
        if hits is None:
            demo[rel] = {"🔴": err}
            continue
        demo[rel] = {"자리 수": len(hits),
                     "보기": hits[:3] if hits else "없음"}
        demo_tot += len(hits)
    a985 = [h for h in (_fmt_literals("runners/audit985.py")[0] or [])
            if h["부호"] == "=" and h["맨 수"] == "3"]
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴🔴 **`[수리] R3` --- 손 전사(AST) 자의 분모를 「이 사이클 러너 전량」으로**"),
        ("🔴 왜", "🔴 **`out985_audit.json` §B 의 `「통과 2 + 분모 제거 1 + 거짓 1 = 3」` 이 "
               "하드코딩 리터럴이고 실제 합은 4 다**(`audit985.py:170` 의 `= 3` 이 문자열). "
               "🔴 **985 자신이 983 R2·반증조건 13 으로 잡으려던 형태인데 AST 자가 "
               "「치환표 생성기만」 훑어 감사 러너를 원리상 못 봤다**"),
        ("🔴 신판 자", "**서식 자리표가 있는 문자열 안의 «산술 자리» 맨 수**"
                   "(`= 3` · `+ 1` · `/ 17`). 독스트링은 뺀다"),
        ("⚠ 구판 자", "**`T[...] = <수>` 대입 하나**(985 R2) --- 치환표 생성기에만 걸린다"),
        ("🔴 신판 분모(이 사이클 러너 전량)", len(CY.RAN_986)),
        ("⚠ 구판 분모(치환표 생성기 하나)", 1),
        ("🔴 신판 --- 986 러너별", rows_new),
        ("🔴🔴🔴 신판 --- 986 러너의 손 전사 자리 수", tot_new),
        ("⚠ 구판 --- 985 치환표 생성기", rows_old),
        ("🔴 못 읽은 러너(= 「0 이다」가 아니다 · 조항 59)", unread or "없음"),
        ("🔴🔴 검정력 시연(조항 64) — 같은 신판 자를 985 의 러너 전량에 문다",
         collections.OrderedDict([
             ("🔴 분모", len(CY5.RAN_985)),
             ("🔴🔴🔴 985 러너의 손 전사 자리 수", demo_tot),
             ("🔴🔴🔴 `audit985.py` 의 `= 3` 을 잡았나", bool(a985)),
             ("🔴 그 자리", a985 or "🔴 못 잡았다"),
             ("🔴 러너별", demo),
             ("🔴 왜 이 절이 있나",
              "🔴 **자가 «남의 파일에서 떨어져야» 자다**(조항 64). 985 의 러너에서 "
              "0 이 나오면 이 자는 항진명제다"),
         ])),
        ("통과", bool(not unread and a985)),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **① 986 러너를 전량 읽었고 ② 신판 자가 985 의 `= 3` 을 «실제로» 잡았는가.** "
         "🔴 986 러너의 자리 수가 0 인지 아닌지는 **반증조건 14 가** 진다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §D 🔴🔴 R1 --- `⑤′` 절 1 「소비자」의 구판/신판
# ══════════════════════════════════════════════════════════════════════
def consumer_split(base, head, tree_ref):
    """🔴 `조항 60-나` 개정판 요건 ②·③ --- **구판 분모와 신판 분모를 «같이» 싣고,
    뺀 것의 「잰 날 것」을 전량 싣는다.**"""
    rc, out, err = F._git(["-c", "core.quotepath=false", "diff", "--name-only", "-z",
                           "%s..%s" % (base, head)])
    if rc != 0:
        return {"🔴": "git diff 종료 %d: %s" % (rc, err[:200]), "통과": False}
    changed = sorted(p for p in out.split("\0") if p)
    nd = F._needles(changed)
    needles_all = sorted(set(sum(nd.values(), [])))
    allc, _m = F._grep_l(needles_all, tree_ref)
    kinds, rows = collections.Counter(), collections.defaultdict(list)
    for c in allc:
        if not c.endswith(".py"):
            kinds["비 .py"] += 1
            rows["비 .py"].append(c)
            continue
        k = A5._mention_kind(c, needles_all, tree_ref)
        kinds[k] += 1
        rows[k].append(c)
    code = sorted(rows.get("코드 리터럴", []))
    prose = sorted(rows.get("산문만(주석·독스트링)", []))
    nonpy = sorted(rows.get("비 .py", []))
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴🔴 **`[수리] R1` --- `⑤′` 절 1 의 「소비자」를 "
                 "「코드 리터럴로 «쓴» 파일」로 바꾼다**"),
        ("🔴 범위", "%s..%s (트리 %s)" % (base[:9], head[:9], tree_ref)),
        ("🔴 바뀐 경로 수", len(changed)),
        ("🔴🔴 요건 ② --- 구판 분모와 신판 분모를 «같이» 싣는다(조항 60-나 개정판)",
         collections.OrderedDict([
             ("⚠ 구판 분모(「그 이름을 아무 데서나 «언급»한 파일」)", len(allc)),
             ("⚠ 구판 분모 중 .py", len([c for c in allc if c.endswith(".py")])),
             ("🔴🔴🔴 신판 분모(「코드 리터럴로 «쓴» 파일」)", len(code)),
             ("🔴 줄어드는 수", len(allc) - len(code)),
         ])),
        ("🔴🔴 요건 ③ --- 뺀 것의 「잰 날 것」을 전량 싣는다(= 「안 잰 것」이 아니다)",
         collections.OrderedDict([
             ("🔴 비 `.py`(실행 대상이 아니다) 수", len(nonpy)),
             ("🔴 비 `.py` 전량", nonpy),
             ("🔴 산문만(주석·독스트링) 수", len(prose)),
             ("🔴 산문만 전량", prose),
             ("🔴 왜 이것이 「분모 밖에서 잰 것」인가",
              "🔴 **주석 한 줄이나 독스트링의 인용은 「그 파일을 다시 돌릴 이유」가 아니다.** "
              "그래도 «셌고» 목록을 여기 남긴다 --- 조용히 사라지는 것이 축소다(조항 59)"),
         ])),
        ("🔴🔴🔴 신판 소비자 전량(코드 리터럴)", code),
        ("🔴 갈래별 수", dict(kinds)),
        ("🔴🔴 원장(`%s`)을 빼는 길은 «안» 쓴다" % DEN,
         "🔴 **티처 #124 가 다시 세어 「원장을 빼도 안 열린다」를 확인했고 985 의 판단이 옳다.** "
         "🔴 **열쇠는 「언급」을 「사용」으로 바꾸는 것**이다"),
        ("통과", bool(allc)),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **구판 자가 소비자를 «하나라도» 냈는가.** 0 이면 역참조가 죽은 것이라 "
         "두 분모를 견줄 수 없다(조항 59)"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §E 🔴 즉시 정정 --- 잴 수 있는 것만 «잰다»
# ══════════════════════════════════════════════════════════════════════
def errata_now():
    loop = _text("docs/루프.md") or ""
    orig = "사전등록한 반증조건·예측의 **분모는 채점 시점에 늘리지도 줄이지도 못한다.**"
    idx = loop.find(orig)
    win = loop[idx:idx + 400] if idx >= 0 else ""
    ptr = ("60-나 개정" in win) or ("개정 참조" in win)
    # ── F5 분모 --- 원장이 싣는 산출물 전량 대 인용된 것 ────────────────
    den = _load(DEN) or {}
    ent = json.dumps(den.get("노트 985") or {}, ensure_ascii=False)
    in_ledger = sorted(set(re.findall(r"(?:runners/)?((?:out985|fiveprime)_?[\w]*\.json)", ent)))
    sc = _load("runners/out985_score.json") or {}
    f5 = sc.get("§F5 🔴 인용 산출물 도장") or {}
    cited = f5.get("🔴 인용된 산출물(기계 추출)") or []
    missing = sorted(set(in_ledger) - set(cited))
    # ── 판정_985.md 표 칸 깨짐 ──────────────────────────────────────
    v = (_text("docs/판정_985.md") or "").split("\n")
    broken = []
    for i, ln in enumerate(v, 1):
        if ln.strip().startswith("|") and ln.count("|") >= 2:
            if re.search(r"\|\s*\|\s*\|", ln) and not re.match(r"^\s*\|[\s|:-]*\|\s*$", ln):
                broken.append({"줄": i, "본문": ln.strip()[:120]})
    return collections.OrderedDict([
        ("🔴 무엇", "🔴 **즉시 정정(수리로 안 센다)** --- 잴 수 있는 것만 «잰다»"),
        ("① `조항 60-나` 「개정」이 덧붙임이다", collections.OrderedDict([
            ("🔴 원문을 찾았나", bool(idx >= 0)),
            ("🔴 원문 뒤 400 자 안에 개정 포인터가 있나", ptr),
            ("🔴🔴🔴 그래서 986 이 하는 것",
             "🔴 **원 본문에 「→ 60-나 개정 참조」 한 줄을 넣는다** --- "
             "그게 「문언을 고친다」의 최소치다(티처 #124 즉시정정)"),
        ])),
        ("② F5 도장 분모", collections.OrderedDict([
            ("🔴 985 가 쓴 분모(인용된 산출물)", f5.get("🔴 분모")),
            ("🔴🔴 원장 `노트 985` 항목이 «싣는» 산출물 수", len(in_ledger)),
            ("🔴 원장이 싣는 산출물", in_ledger),
            ("🔴🔴🔴 인용 안 해서 도장 검사를 «피한» 산출물", missing or "없음"),
            ("🔴🔴 그 수", len(missing)),
            ("🔴 왜 문제인가", "🔴 **인용을 안 하면 도장 검사를 피한다** --- "
                          "986 은 분모를 「원장이 싣는 산출물 전량」으로 한다(반증조건 12)"),
        ])),
        ("③ `docs/판정_985.md` 표 칸 깨짐", collections.OrderedDict([
            ("🔴 깨진 줄 수", len(broken)),
            ("🔴 줄", broken[:10] or "없음"),
        ])),
        ("④ 요건 수가 갈렸다", collections.OrderedDict([
            ("🔴 사전등록 §4-2 가 등록한 요건 수", 2),
            ("🔴 `루프.md`·판정문·PR 이 적은 요건 수", 3),
            ("🔴 사전등록에 「③」이 있나",
             bool("③" in (_text("docs/prereg_985_specificity_power.md") or "")
                  .split("### 4-2")[-1].split("### 4-3")[0])),
            ("🔴🔴 그리고 그 새 3 요건을 곧바로 984 에 소급해 스스로 면소했다",
             bool("984 를 이 문언으로 다시 재면" in loop)),
        ])),
        ("⑤ 「984 에 물리면 다섯 칸 어긋난다」의 정체", collections.OrderedDict([
            ("🔴 정본", "4 + 1"),
            ("🔴 다섯째의 출처", "🔴 **985 자신의 편집**(PR 본문은 밝혔고 판정문은 안 밝혔다)"),
            ("🔴🔴🔴 986 부터의 규율",
             "🔴 **검정력 시연은 「자기 입력 교란」으로 한다** --- 자기 판정문에 한 바이트를 "
             "더해 자가 떨어지는지를 본다(`certify986` §라)"),
        ])),
        ("통과", bool(idx >= 0)),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **`조항 60-나` 원문을 «찾았는가»** 하나다 --- 못 찾으면 포인터를 넣을 자리를 모른다"),
    ])


def stage(ref, base, head, tree):
    t0 = CY.now()
    CY.begin(ref)
    cs0 = CY.code_stamp()
    out = collections.OrderedDict()
    out["무엇"] = "986 §1·§4 — 🔴🔴🔴 **985 의 세 오기를 다시 재고 손 전사 자의 분모를 넓힌다**"
    out["🔴 축"] = "자기 자(채점 ↔ 문서 고리)"
    out["§A 🔴🔴🔴 985 의 세 오기"] = three_errata()
    out["§B 🔴🔴 PR #243 본문 대 985 문서"] = pr_vs_docs()
    out["§C 🔴🔴🔴 R3 손 전사 자의 분모"] = hand_transcription()
    out["§D 🔴🔴 R1 소비자 구판/신판"] = consumer_split(base, head, tree)
    out["§E 🔴 즉시 정정"] = errata_now()
    out["통과"] = bool(all(v.get("통과") for k, v in out.items()
                         if k.startswith("§") and isinstance(v, dict)))
    CY.write(OUT, out, ref, cs0, t0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["audit"])
    ap.add_argument("--ref", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", required=True)
    ap.add_argument("--tree", default=None)
    a = ap.parse_args()
    r = stage(a.ref, a.base, a.head, a.tree)
    print(json.dumps({
        "통과": r["통과"],
        "반증조건 정본": r["§A 🔴🔴🔴 985 의 세 오기"]["① 반증조건"]["🔴🔴🔴 정본(`out985_score.json` §6)"],
        "끊은 자리 실제 합": r["§A 🔴🔴🔴 985 의 세 오기"]["② 「끊은 자리」"]["🔴🔴🔴 셋의 실제 합"],
        "PR 어긋난 자리": r["§B 🔴🔴 PR #243 본문 대 985 문서"].get("🔴🔴🔴 어긋난 자리 수"),
        "986 러너 손 전사 자리": r["§C 🔴🔴🔴 R3 손 전사 자의 분모"]["🔴🔴🔴 신판 --- 986 러너의 손 전사 자리 수"],
    }, ensure_ascii=False))
    return 0 if r["통과"] else 1


if __name__ == "__main__":
    sys.exit(main())
