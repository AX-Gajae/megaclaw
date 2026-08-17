#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""988 §1~§4 — 🔴🔴🔴 **등록한 「판정식」을 대조하고, 「자리 0」을 「안 봤다」로 센다**.

  §A  🔴🔴🔴 **987 의 최상위 통과를 등록 정의대로 다시 채점한다** --- 예측 `5/6` · 최상위 `False`.
  §B  🔴🔴🔴 **여덟째 칸** --- 사전등록 §5 「맞았다의 정의」 ↔ 채점기가 «실제로 평가한» AST.
  §C  🔴🔴 **`조항 59-나` 감사** --- 987 의 「자리 0」 초록을 「깨끗함 / 미측정」으로 «갈라 센다».
  §D  🔴🔴 **늘린 한글 바늘(12)을 987 문서 여섯에 문다** --- 987 은 바늘 둘로 0 자리 걸렸다.
  §E  🔴🔴🔴 **단조 불변(동어반복) 자** --- `rank(δ·Lh) ≡ rank(h)` 를 «측정 전에» 자동으로 잡는다.
  §F  🔴 **`⑤′` 수리 레인 파싱** --- 구판(`## 8.` 하드코딩) / 신판(절 «이름») 전후.
  §G  🔴 **`⑤′` §3 명부에 데몬 셋** --- 아는 red 를 켠다.
  §H  🔴 **즉시 정정** --- `u=3` 마지막 구간 기울기 · 「열린 PR 0」의 측정 시각 · 산문 자.
  §I  🔴 **데몬(규칙 B)**.

씀:
    python3 runners/audit988.py --stage audit --ref <40자 sha>
"""
import argparse
import ast
import collections
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import cycle988 as CY                                   # noqa: E402
import ledger as LG                                     # noqa: E402

OUT = "runners/out988_audit.json"

PREREG_987 = "docs/prereg_987_ceiling_identity_fixed_ref.md"
PREREG_988 = CY.PREREG
SCORE_987 = "runners/out987_score.json"
AUDIT_987 = "runners/out987_audit.json"
POWER_987 = "runners/out987_power.json"
PROSE_987 = "runners/out987_prose.json"
SCORE_986 = "runners/out986_score.json"

#: 🔴 987 의 규칙 D 여섯 대상(고정 ref 로 읽는다)
D_TARGETS_987 = ("docs/판정_987.md", "docs/card_987.md", "docs/handoff_987.md",
                 "docs/pr_987.md")

#: 🔴🔴 `⑤′` §3 에 «넣어야 하는» 데몬 셋 --- 987 이 재고도 명부에 «안 넣은» 파일들
DAEMON_TRIO = ("runners/out941_wikidaily.json", "runners/out941_steamrev.json",
               "runners/out941_robots.json")

#: 🔴 **구판**(`fiveprime902.py:1531` · 절 «번호» 하드코딩) / **신판**(절 «이름»)
SEC_OLD = re.compile(r"^##\s*8\.", re.M)
#: 🔴🔴🔴 **사전등록 §4-3 이 적은 정규식은 `^##\s*.*수리\s*레인` 이었다.**
#:  🔴 **측정에서 «결함»이 드러났다** --- 그 꼴은 `###`(하위 절)도 문다.
#:  988 «자신의» 사전등록 §4-3 제목이 「수리 레인」을 담고 있어 그 하위 절을 먼저 물었고
#:  레인 수가 `0` 으로 나왔다. **구현은 `^##(?!#)` 로 좁혔다.**
#:  🔴 **이 어긋남을 「정정」으로 얹고 두 꼴의 값을 나란히 싣는다**(조항 66-③ · 조항 60).
SEC_NEW_PREREG = re.compile(r"^##\s*[^\n]*수리\s*레인", re.M)
SEC_NEW = re.compile(r"^##(?!#)\s*[^\n]*수리\s*레인", re.M)
ROW_RE = re.compile(r"^\|\s*\*{0,2}R(\d+)\*{0,2}\s*\|", re.M)
CAP_RE = re.compile(r"^\s*[>*\-|\s]*상한\s*[:：]\s*(\d+)", re.M)
OUT_RE = re.compile(r"저장소 밖 레인\s*[:：]\s*(\d+)", re.M)

PRED_ROW = re.compile(r"^\|\s*\*{0,2}(P\d+)\*{0,2}\s*\|", re.M)


def _dig(obj, *keys):
    cur = obj
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def _fx(rel, ref):
    return CY.fixed_ref_text(ref, rel)["🔴 본문"]


def _fj(rel, ref):
    _r, d = CY.fixed_ref_json(ref, rel)
    return d


def _disk(rel):
    p = ROOT / rel
    return p.read_text(encoding="utf-8") if p.is_file() else None


# ══════════════════════════════════════════════════════════════════════
# 공용 --- 사전등록 §5 표를 «문자열로» 읽는다
# ══════════════════════════════════════════════════════════════════════
def prereg_predictions(txt):
    """🔴🔴🔴 **사전등록 §5 의 「맞았다의 정의」 셀을 «문자열로» 읽는다**.

    🔴 이것이 여덟째 칸의 «왼쪽»이다 --- 오른쪽은 채점기의 AST 다.
    """
    if txt is None:
        return collections.OrderedDict()
    out = collections.OrderedDict()
    for line in txt.split("\n"):
        m = PRED_ROW.match(line)
        if not m:
            continue
        # 🔴 표 안의 `\|` 는 칸 구분자가 «아니다»
        safe = line.replace("\\|", "\x00")
        cells = [c.strip().replace("\x00", "|") for c in safe.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        out[m.group(1)] = collections.OrderedDict([
            ("🔴 예측 문장", cells[1]),
            ("🔴🔴🔴 등록한 「맞았다의 정의」(«문자열 그대로»)", cells[-1]),
        ])
    return out


_NORM_DROP = re.compile(r"[🔴🟢⚠«»`*\s]")


def _norm(s):
    """🔴 정규화 --- 강조·따옴표·공백을 지우고 「절」을 `§` 로 맞춘다."""
    if not isinstance(s, str):
        return ""
    t = _NORM_DROP.sub("", s)
    t = t.replace("절3", "§3").replace("절 3", "§3")
    return t


def _lcs_len(a, b):
    """최장 공통 «부분문자열» 길이(연속)."""
    if not a or not b:
        return 0
    prev = [0] * (len(b) + 1)
    best = 0
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best = cur[j]
        prev = cur
    return best


_OPS = ("==", ">=", "<=", "!=", "≥", "≤", ">", "<", "=")


def _split_def(d):
    """등록 정의를 «주어 / 연산자 / 우변» 셋으로 가른다."""
    body = d
    m = re.search(r"판정식\s*:\s*(.+)$", d)
    if m:
        body = m.group(1)
    body = body.strip().strip("`")
    for op in _OPS:
        i = body.rfind(op)
        if i > 0:
            return body[:i].strip(), op, body[i + len(op):].strip()
    return body.strip(), None, None


# ══════════════════════════════════════════════════════════════════════
# 🔴🔴🔴 채점기의 «실제 판정식»을 AST 로 덤프한다
# ══════════════════════════════════════════════════════════════════════
def _strings(node):
    return [n.value for n in ast.walk(node)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def _names(node):
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def predicate_ast(src, func="predict"):
    """🔴🔴🔴 **채점기가 각 예측에 대해 «실제로 평가한» 표현식을 AST 로 덤프한다.**

    낸다: 예측별로
      - **평가 집합** --- 「맞았나」 값을 «만드는» 표현식이 (후향 슬라이스로) 참조하는
        문자열 상수 전량(= 키 경로).
      - **게재 집합** --- 그 행이 «싣는» 문자열 상수 전량.
    🔴 **둘을 가르는 것이 이 자의 전부다** --- 987 은 등록 주어를 «싣기만» 하고
    «평가»는 다른 식으로 했다.
    """
    try:
        tree = ast.parse(src)
    except SyntaxError as e:                                       # noqa: BLE001
        return {"🔴": "🔴 파싱 실패: %s" % e}, {}
    fn = None
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and n.name == func:
            fn = n
            break
    if fn is None:
        return {"🔴": "🔴 `%s` 함수가 없다" % func}, {}

    # ── 이름 → 대입 표현식 ─────────────────────────────────────
    assigns = collections.defaultdict(list)
    for st in ast.walk(fn):
        if isinstance(st, ast.Assign):
            for t in st.targets:
                if isinstance(t, ast.Name):
                    assigns[t.id].append(st.value)
        elif isinstance(st, ast.AugAssign) and isinstance(st.target, ast.Name):
            assigns[st.target.id].append(st.value)

    def slice_back(expr, seen=None, depth=0):
        seen = seen or set()
        got = list(_strings(expr))
        if depth > 6:
            return got
        for nm in _names(expr):
            if nm in seen:
                continue
            seen.add(nm)
            for v in assigns.get(nm, []):
                got += slice_back(v, seen, depth + 1)
        return got

    rows = collections.OrderedDict()
    for st in ast.walk(fn):
        if not (isinstance(st, ast.Assign) and len(st.targets) == 1
                and isinstance(st.targets[0], ast.Subscript)):
            continue
        sub = st.targets[0]
        lab = None
        sl = sub.slice
        if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
            lab = sl.value
        if not lab:
            continue
        m = re.match(r"\s*(P\d+)\b", lab)
        if not m:
            continue
        pid = m.group(1)
        shown = list(_strings(st.value))
        # 🔴 「맞았나」 짝의 «값 쪽» 표현식을 찾는다
        hit_expr = None
        for t in ast.walk(st.value):
            if isinstance(t, ast.Tuple) and len(t.elts) == 2:
                k = t.elts[0]
                if isinstance(k, ast.Constant) and isinstance(k.value, str) \
                        and "맞았나" in k.value:
                    hit_expr = t.elts[1]
        evald = slice_back(hit_expr) if hit_expr is not None else []
        rows[pid] = collections.OrderedDict([
            ("🔴 행 이름(채점기가 문서에 싣는 것)", lab),
            ("🔴🔴🔴 「맞았나」를 «만든» 표현식", ast.dump(hit_expr) if hit_expr is not None
             else "🔴 없다 --- 이 행은 「맞았나」를 안 만든다"),
            ("🔴🔴 평가 집합(그 표현식이 «참조»하는 키 경로)", sorted(set(evald))),
            ("🔴 게재 집합(그 행이 «싣는» 문자열 전량)", sorted(set(shown))),
        ])
    return rows, assigns


def eighth_cell(cycle_name, prereg_txt, score_src, score_obj, rows_key,
                strict_paths=None):
    """🔴🔴🔴 **여덟째 칸** --- 등록 정의 ↔ 채점기 AST.

    - **㉠ 키 경로 집합 대조(엄격)** --- `strict_paths` 가 있으면(988 자신)
      **사전등록의 키 경로 집합 == 선언표의 키 경로 집합**을 «집합으로» 본다.
    - **㉡ 판정식 교체 대조(남의 사이클)** --- 등록 «주어»가
      **게재 집합에는 있는데 평가 집합에는 «없으면»** 그것이 «판정식 교체»다.
    - **㉢ 등록 주어의 값 대조** --- 그 게재 칸의 값이 등록 우변과 다르면 어긋남.
    """
    reg = prereg_predictions(prereg_txt)
    got, _asg = predicate_ast(score_src or "")
    live = _dig(score_obj or {}, rows_key, "🔴 예측별") or {}
    per, bad = collections.OrderedDict(), []
    for pid, rr in reg.items():
        d = rr["🔴🔴🔴 등록한 「맞았다의 정의」(«문자열 그대로»)"]
        subj, op, rhs = _split_def(d)
        nsubj = _norm(subj)
        blk = got.get(pid) or {}
        evald = [_norm(x) for x in (blk.get("🔴🔴 평가 집합(그 표현식이 «참조»하는 키 경로)") or [])]
        shown = [_norm(x) for x in (blk.get("🔴 게재 집합(그 행이 «싣는» 문자열 전량)") or [])]
        raw_shown = blk.get("🔴 게재 집합(그 행이 «싣는» 문자열 전량)") or []

        def _match(pool):
            hits = []
            for i, x in enumerate(pool):
                if not x:
                    continue
                if nsubj and (nsubj in x or x in nsubj or _lcs_len(nsubj, x) >= 4):
                    hits.append(i)
            return hits
        in_ev = _match(evald)
        in_sh = _match(shown)
        swapped = bool(nsubj and in_sh and not in_ev)
        # ── ㉢ 등록 주어의 «값» 대조 ─────────────────────────────
        row_live = None
        for k, v in (live or {}).items():
            if re.match(r"\s*%s\b" % pid, k):
                row_live = v
        val, valcell = None, None
        if isinstance(row_live, dict):
            for i in in_sh:
                cell = raw_shown[i]
                if cell in row_live:
                    val, valcell = row_live[cell], cell
                    break
        want = None
        if rhs is not None:
            r = rhs.strip().strip("`").lower()
            if r in ("false", "거짓"):
                want = False
            elif r in ("true", "참"):
                want = True
        val_bad = bool(want is not None and valcell is not None and val != want)
        per[pid] = collections.OrderedDict([
            ("🔴 등록한 「맞았다의 정의」", d),
            ("🔴 등록 주어", subj), ("🔴 연산자", op), ("🔴 등록 우변", rhs),
            ("🔴🔴 채점기가 「맞았나」를 만든 식", blk.get("🔴🔴🔴 「맞았나」를 «만든» 표현식")),
            ("🔴🔴 평가 집합", blk.get("🔴🔴 평가 집합(그 표현식이 «참조»하는 키 경로)")),
            ("🔴 게재 집합", raw_shown),
            ("🔴🔴 등록 주어가 «평가 집합»에 있나", bool(in_ev)),
            ("🔴🔴 등록 주어가 «게재 집합»에 있나", bool(in_sh)),
            ("🔴🔴🔴 ㉡ 판정식이 «갈아 끼워졌나»(게재엔 있고 평가엔 없다)", swapped),
            ("🔴 ㉢ 등록 주어와 짝지은 게재 칸", valcell),
            ("🔴 ㉢ 그 칸의 «실린 값»", val),
            ("🔴🔴🔴 ㉢ 등록 우변과 «다른가»", val_bad),
            ("🔴🔴🔴 어긋났나(㉡ 또는 ㉢)", bool(swapped or val_bad)),
        ])
        if swapped or val_bad:
            bad.append(pid)
    res = collections.OrderedDict([
        ("🔴 대상", cycle_name),
        ("🔴 분모(사전등록 §5 의 예측 수)", len(reg)),
        ("🔴 예측별", per),
        ("🔴🔴 어긋난 예측", bad or "없음"),
        ("🔴🔴 어긋난 예측 수", len(bad)),
    ])
    if strict_paths is not None:
        reg_paths, decl_paths = strict_paths
        res["🔴🔴🔴 ㉠ 엄격 — 사전등록 키 경로 집합"] = reg_paths
        res["🔴🔴🔴 ㉠ 엄격 — 선언표 `PRED_DEF` 키 경로 집합"] = decl_paths
        res["🔴🔴🔴 ㉠ 두 집합이 같은가"] = bool(reg_paths == decl_paths)
        res["🔴 ㉠ 사전등록에만 있는 키 경로"] = \
            sorted(set(map(str, reg_paths)) - set(map(str, decl_paths))) or "없음"
        res["🔴 ㉠ 선언표에만 있는 키 경로"] = \
            sorted(set(map(str, decl_paths)) - set(map(str, reg_paths))) or "없음"
    return res


# ══════════════════════════════════════════════════════════════════════
# §A 987 의 최상위 통과를 «등록 정의대로» 다시 채점한다
# ══════════════════════════════════════════════════════════════════════
def rescore_987(sc, au):
    pr = _dig(sc or {}, "§5 🔴 예측", "🔴 예측별") or {}
    reg_hit, per = 0, collections.OrderedDict()
    sec3 = _dig(au or {}, "§C 🔴🔴 `⑤′` 절 3 을 고정 명부로 다시 낸다",
                "🔴 985 절 3 통과 / 986 절 3 통과") or [None, None]
    for k, v in pr.items():
        pid = (re.match(r"\s*(P\d+)", k) or [None, None])[1]
        got = bool((v or {}).get("🔴 맞았나"))
        fixed = got
        why = "채점기 그대로"
        if pid == "P6":
            #: 🔴🔴🔴 등록 정의는 `명부판 §3 통과 = False` 다.
            fixed = bool(sec3[1] is False)
            why = ("🔴🔴🔴 **등록 정의(`명부판 §3 통과 = False`)로 다시 잰다** --- "
                   "채점기는 `bool(sink)` 로 갈아 끼웠다")
        per[k] = collections.OrderedDict([
            ("🔴 987 채점기가 낸 값", got),
            ("🔴🔴🔴 등록 정의대로의 값", fixed),
            ("🔴 왜", why),
            ("🔴🔴 갈리나", bool(got != fixed)),
        ])
        reg_hit += 1 if fixed else 0
    n = len(pr)
    blind = [k for k in pr if re.match(r"\s*P[123]\b", k)]
    blind_hit = len([1 for k, v in per.items() if k not in blind and v["🔴🔴🔴 등록 정의대로의 값"]])
    top_old = (sc or {}).get("통과")
    ruleD = _dig(sc or {}, "§D 🔴 규칙 D 감사(분모 여섯)", "통과")
    kor = _dig(sc or {}, "§K 🔴🔴 규칙 D — 한글 수사(987 신설)", "통과")
    sh = _dig(sc or {}, "§68 🔴 조항 68 모양 주장 감사", "통과")
    fal = _dig(sc or {}, "§6 🔴 반증조건", "통과")
    top_new = bool(fal and ruleD and kor and sh and (reg_hit == n))
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴🔴 **987 의 예측을 «등록한 판정식»대로 다시 채점한다**"),
        ("🔴🔴 등록 분모", n),
        ("🔴 예측별", per),
        ("🔴🔴🔴 등록 정의대로의 분자", reg_hit),
        ("🔴🔴🔴 등록 정의대로의 분자 / 분모", "%d / %d" % (reg_hit, n)),
        ("🔴 987 이 실은 분자 / 분모", _dig(sc or {}, "§5 🔴 예측", "🔴🔴 분자 / 분모")),
        ("🔴🔴 비맹검 이관(§0-나 · P1·P2·P3) 뒤의 분모", n - len(blind)),
        ("🔴🔴 비맹검 이관 뒤의 분자", blind_hit),
        ("🔴🔴 비맹검 이관 뒤의 분자 / 분모", "%d / %d" % (blind_hit, n - len(blind))),
        ("🔴 이관한 예측", blind),
        ("🔴 이관의 근거",
         "🔴 **987 «자신의» §0-나 가 「예측은 「아직 안 잰 것」에만 건다」를 못박았다.** "
         "정정 커밋 `ed009cff7` 시점에 987 은 「`V1` 의 발화율은 δ>0 전 구간 상수다」를 "
         "스스로 적었고, `V1 = 1.0` 이 상수이면 P1(≥0.90)·P2(V1>V0)·P3(V2<V1)은 "
         "**대수적으로 함의된다**. 🔴 **등록 분모 6 은 «안 지운다» --- 둘 다 싣는다**"),
        ("🔴 987 이 실은 최상위 통과", top_old),
        ("🔴🔴🔴 등록 정의대로의 최상위 통과", top_new),
        ("🔴🔴🔴 최상위 통과가 «뒤집히나»", bool(top_old != top_new)),
        ("🔴 최상위 통과의 정의(987 판)",
         "반증조건 ∧ 규칙 D(아라비아) ∧ §K 규칙 D(한글 수사) ∧ §68 ∧ §5 예측"),
        ("🔴 그 넷의 값", {"반증조건": fal, "규칙 D": ruleD, "§K": kor, "§68": sh}),
        ("통과", bool(n > 0 and pr)),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "🔴 **987 의 예측 여섯을 «전부 다시 쟀는가»** 하나다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §C 🔴🔴 `조항 59-나` --- 「자리 0」을 「깨끗함 / 미측정」으로 «갈라 센다»
# ══════════════════════════════════════════════════════════════════════
def _count_pass_sites(src):
    """`("통과", <무엇이든>)` 꼴 «후보» 자리 수와 그중 «리터럴 True» 자리 수."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None, None
    cand = hit = 0
    for n in ast.walk(tree):
        if isinstance(n, ast.Tuple) and len(n.elts) == 2:
            k = n.elts[0]
            if isinstance(k, ast.Constant) and k.value == "통과":
                cand += 1
                v = n.elts[1]
                if isinstance(v, ast.Constant) and v.value is True:
                    hit += 1
    return cand, hit


def _count_cell_assign(src):
    """`T[...] = <무엇이든>` 꼴 «후보» 자리 수와 그중 «숫자 리터럴» 자리 수."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None, None
    cand = hit = 0
    for n in ast.walk(tree):
        if not isinstance(n, ast.Assign):
            continue
        for t in n.targets:
            if not isinstance(t, ast.Subscript):
                continue
            cand += 1
            v = n.value
            if isinstance(v, ast.Constant) and isinstance(v.value, (int, float)) \
                    and not isinstance(v.value, bool):
                hit += 1
    return cand, hit


DISK_FN = {"read_text", "open", "read_bytes", "_text", "_read", "_disk"}
NEEDLE_OLD = re.compile(r"^docs/.*\.md$")
NEEDLE_NEW = re.compile(r"^(?:docs|runners)/")


def _count_disk_reads(src):
    """디스크 읽기 호출의 «후보 인자» 수 --- 구판 바늘 / 신판 바늘 / 변수 경로."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    old = new = var = 0
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        nm = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name)
                                                          else None)
        if nm not in DISK_FN:
            continue
        for a in list(n.args) + [k.value for k in n.keywords]:
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                if NEEDLE_OLD.match(a.value):
                    old += 1
                if NEEDLE_NEW.match(a.value):
                    new += 1
            else:
                var += 1
    return {"구판 바늘(`^docs/.*\\.md$`)에 걸린 인자": old,
            "🔴 신판 바늘(`runners/`·`docs/` 전량)에 걸린 인자": new,
            "🔴 변수 경로 인자(구판은 원리상 «못 본다»)": var}


def zero_slot_audit(sc987, ref):
    """🔴🔴🔴 **987 의 「자리 0」 초록 넷 + `§K` 를 갈라 센다**(`조항 59-나`)."""
    rows = collections.OrderedDict()

    # ── F08 --- 바늘을 이 사이클 산출물에서 자동 생성했다 ──────────
    f8 = _dig(sc987 or {}, "§6 🔴 반증조건") or {}
    f8row = None
    for k, v in (f8.get("🔴 조건별") or {}).items():
        if k.startswith("8 "):
            f8row = v
    n_needle = (f8row or {}).get("🔴 바늘 수")
    naked = (f8row or {}).get("🔴🔴 «구간·미확정 맥락 없이» 실린 수")
    rows["987 반증조건 8"] = CY.measured(
        "987 반증조건 8 — 미식별 점추정을 못 박았나", 1, n_needle,
        0 if naked == "없음" else (len(naked) if isinstance(naked, list) else None))
    rows["987 반증조건 8"]["🔴 걸린 자리의 뜻"] = "자동 생성된 바늘(미식별 칸의 점추정) 수"

    # ── F14 --- 리터럴 `("통과", True)` ──────────────────────────
    cand14 = hit14 = 0
    per14 = {}
    for rel in ("runners/cycle987.py", "runners/house987.py", "runners/audit987.py",
                "runners/power987.py", "runners/score987.py", "runners/note987_gen.py",
                "runners/certify987.py", "runners/prose987.py", "runners/plumb987.py"):
        src = _fx(rel, ref)
        c, h = _count_pass_sites(src or "")
        per14[rel] = {"후보 자리": c, "리터럴 True 자리": h}
        cand14 += (c or 0)
        hit14 += (h or 0)
    rows["987 반증조건 14"] = CY.measured(
        "987 반증조건 14 — 리터럴 `(\"통과\", True)`", 9, cand14, hit14)
    rows["987 반증조건 14"]["🔴 러너별"] = per14
    rows["987 반증조건 14"]["🔴 걸린 자리의 뜻"] = "`(\"통과\", <무엇이든>)` 꼴 후보 자리 수"

    # ── F15 --- 손 전사 수 리터럴 ────────────────────────────────
    cand15 = hit15 = 0
    per15 = {}
    for rel in ("runners/cycle987.py", "runners/house987.py", "runners/audit987.py",
                "runners/power987.py", "runners/score987.py", "runners/note987_gen.py",
                "runners/certify987.py", "runners/prose987.py", "runners/plumb987.py"):
        src = _fx(rel, ref)
        c, h = _count_cell_assign(src or "")
        per15[rel] = {"후보 자리": c, "숫자 리터럴 자리": h}
        cand15 += (c or 0)
        hit15 += (h or 0)
    rows["987 반증조건 15"] = CY.measured(
        "987 반증조건 15 — 손 전사 수 리터럴", 9, cand15, hit15)
    rows["987 반증조건 15"]["🔴 러너별"] = per15
    rows["987 반증조건 15"]["🔴 걸린 자리의 뜻"] = "`T[...] = <무엇이든>` 꼴 후보 자리 수"

    # ── F16 --- 「전」을 고정 ref 없이 읽었나 ──────────────────────
    old = new = var = 0
    per16 = {}
    for rel in ("runners/cycle987.py", "runners/house987.py", "runners/audit987.py",
                "runners/power987.py", "runners/score987.py", "runners/note987_gen.py",
                "runners/certify987.py", "runners/prose987.py", "runners/plumb987.py"):
        d = _count_disk_reads(_fx(rel, ref) or "")
        per16[rel] = d
        if d:
            old += d["구판 바늘(`^docs/.*\\.md$`)에 걸린 인자"]
            new += d["🔴 신판 바늘(`runners/`·`docs/` 전량)에 걸린 인자"]
            var += d["🔴 변수 경로 인자(구판은 원리상 «못 본다»)"]
    rows["987 반증조건 16"] = CY.measured(
        "987 반증조건 16 — 「전」을 고정 ref 없이 디스크에서 읽었나", 9, old, 0)
    rows["987 반증조건 16"]["🔴 러너별"] = per16
    rows["987 반증조건 16"]["🔴 걸린 자리의 뜻"] = "구판 바늘(`^docs/.*\\.md$`)에 걸린 인자 수"
    rows["987 반증조건 16"]["🔴🔴🔴 바늘을 넓히면(`runners/`·`docs/` 전량)"] = new
    rows["987 반증조건 16"]["🔴🔴🔴 변수 경로 인자(구판이 원리상 못 보는 자리)"] = var
    rows["987 반증조건 16"]["🔴 즉시 정정"] = (
        "🔴 **`조항 71-가` 는 「모든 「전」 값」인데 구판 바늘은 `^docs/.*\\.md$` 만 봐서 "
        "`runners/*.json` 의 「전」이 원리상 안 보인다.** 🔴 **행동은 준수였다**(고정 ref 로 읽었다) "
        "--- 그러나 «자»는 그것을 증명하지 못했다")

    # ── §K --- 한글 수사 바늘 ───────────────────────────────────
    K = (sc987 or {}).get("§K 🔴🔴 규칙 D — 한글 수사(987 신설)") or {}
    tied = 0
    for _n, r in (K.get("🔴 대상별") or {}).items():
        if isinstance(r, dict):
            tied += r.get("🔴 바늘이 걸린 수사") or 0
    rows["987 §K 바늘 대조"] = CY.measured(
        "987 §K — 한글 수사 바늘 대조", K.get("🔴🔴 채점 분모(대상)"), tied,
        K.get("🔴🔴🔴 어긋난 수사 수"))
    rows["987 §K 바늘 대조"]["🔴 센 한글 수사 수(존재 계수 · 검사 계수가 «아니다»)"] = \
        K.get("🔴🔴 센 한글 수사 수")
    rows["987 §K 바늘 대조"]["🔴 걸린 자리의 뜻"] = "등록 앞말 바늘이 «실제로» 걸린 수사 수"

    unmeasured = [k for k, v in rows.items() if v["🔴🔴🔴 미측정인가"]]
    four = ["987 반증조건 8", "987 반증조건 14", "987 반증조건 15", "987 반증조건 16"]
    n4 = len([k for k in four if rows[k]["🔴🔴🔴 미측정인가"]])
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴🔴 **`조항 59-나` --- 「자리 0」은 「통과」가 아니라 「미측정」이다**"),
        ("🔴 자(측정 전에 박았다)",
         "① 분모 > 0 · ② **걸린 자리가 «하나 이상»** · ③ 그중 어긋난 것이 0. ②가 0 이면 「미측정」"),
        ("🔴 조건별", rows),
        ("🔴 분모(갈라 센 자 수)", len(rows)),
        ("🔴🔴🔴 미측정인 자", unmeasured or "없음"),
        ("🔴🔴🔴 미측정인 자 수", len(unmeasured)),
        ("🔴 987 반증조건 8·14·15·16 넷", four),
        ("🔴🔴🔴 미측정으로 재분류된 조건 수", n4),
        ("🔴🔴 987 이 그 넷을 무엇으로 셌나", "🔴 **전부 「통과」로 셌다**(자리 0 인 채로)"),
        ("통과", bool(rows)),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "🔴 **다섯 자를 «갈라 셌는가»** 하나다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §D 늘린 한글 바늘(12)을 987 문서 여섯에 문다
# ══════════════════════════════════════════════════════════════════════
def korean_widen(ref, needles, table987):
    T = table987 or {}
    txts = collections.OrderedDict()
    for p in D_TARGETS_987:
        txts[p] = _fx(p, ref)
    den = _fj("data/lab/denominator.json", ref)
    txts["🔴 원장 `노트 987` 항목"] = (json.dumps(den.get("노트 987"), ensure_ascii=False,
                                             indent=1) if den and "노트 987" in den else None)
    goal = _fx("docs/목표.md", ref)
    txts["🔴 `docs/목표.md` 「정본 유보」 절"] = goal
    rows, tied_tot, seen_tot, bad = collections.OrderedDict(), 0, 0, []
    for name, txt in txts.items():
        if txt is None:
            rows[name] = {"🔴": "🔴 못 읽었다(= 「0」이 아니다 · 조항 59)"}
            continue
        code = [(m.start(), m.end()) for m in re.finditer(r"`[^`\n]*`", txt)]
        tied, seen, per = 0, 0, []
        for m in LG.KNUMPAT.finditer(txt):
            if LG.KNUM_NOT.match(txt, m.start()):
                continue
            if any(a <= m.start() and m.end() <= b for a, b in code):
                continue
            seen += 1
            word = m.group()
            val = LG.KOR_NUM[word]
            head = txt[max(0, m.start() - 24):m.start()]
            for lab, (rx, cell) in needles.items():
                if not rx.search(head):
                    continue
                tied += 1
                want = T.get(cell) if cell else None
                ok = (want is not None and val == want)
                per.append({"바늘": lab, "수사": word, "값": val, "치환표 칸": cell,
                            "기대": want, "같은가": bool(ok)})
                if not ok:
                    bad.append({"문서": name, "바늘": lab, "수사": word, "값": val,
                                "기대": want})
        rows[name] = {"🔴 센 한글 수사": seen, "🔴🔴 바늘이 걸린 수사": tied,
                      "🔴 걸린 자리": per or "없음"}
        tied_tot += tied
        seen_tot += seen
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴 **바늘을 2 → %d 로 늘려 987 문서(고정 ref)에 문다**" % len(needles)),
        ("🔴 고정 ref", ref),
        ("🔴🔴 등록 바늘 수", len(needles)),
        ("🔴 바늘(이름 · 정규식)", {k: v[0].pattern for k, v in needles.items()}),
        ("🔴 문서별", rows),
        ("🔴🔴 센 한글 수사 수", seen_tot),
        ("🔴🔴🔴 바늘이 걸린 수사 수", tied_tot),
        ("🔴 어긋난 자리", bad or "없음"),
        ("🔴🔴 987 의 등록 바늘 둘로는 걸린 수사가 «0» 이었다", True),
        ("통과", bool(seen_tot > 0)),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "🔴 **987 문서에서 한글 수사를 «세었는가»** 하나다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §E 🔴🔴🔴 단조 불변(동어반복) 자 --- 「두 계열이 서로의 단조 변환인가」
# ══════════════════════════════════════════════════════════════════════
MONO_TOL = 1e-12


def _rank(x):
    a = np.asarray(x, dtype=float)
    order = a.argsort(kind="mergesort")
    r = np.empty(len(a), dtype=float)
    r[order] = np.arange(1, len(a) + 1, dtype=float)
    # 동률 평균
    vals, inv, cnt = np.unique(a, return_inverse=True, return_counts=True)
    if (cnt > 1).any():
        sums = np.zeros(len(vals))
        np.add.at(sums, inv, r)
        r = (sums / cnt)[inv]
    return r


def _spear(a, b):
    ra, rb = _rank(a), _rank(b)
    ca, cb = ra - ra.mean(), rb - rb.mean()
    d = float(np.sqrt(np.dot(ca, ca) * np.dot(cb, cb)))
    if d < 1e-15:
        return None
    return float(np.dot(ca, cb) / d)


def monotone_ruler(pairs):
    """🔴🔴🔴 **두 계열이 서로의 «단조 변환»인가** --- `|스피어만| >= 1 - 1e-12` 면 발화."""
    rows, fired = collections.OrderedDict(), []
    for name, series in pairs.items():
        vals, n_ok, n_fire = [], 0, 0
        for a, b in series:
            s = _spear(a, b)
            if s is None:
                continue
            n_ok += 1
            vals.append(round(s, 12))
            if abs(s) >= 1.0 - MONO_TOL:
                n_fire += 1
        rate = (float(n_fire) / n_ok) if n_ok else None
        rows[name] = collections.OrderedDict([
            ("🔴 쓸 수 있는 짝 수(분모)", n_ok),
            ("🔴🔴 `|스피어만| = 1` 인 짝 수", n_fire),
            ("🔴🔴🔴 동어반복 비율", rate),
            ("🔴 스피어만 최솟값 / 최댓값",
             [min(vals), max(vals)] if vals else None),
            ("🔴🔴🔴 발화(= 동어반복이다)", bool(n_ok > 0 and n_fire == n_ok)),
        ])
        if rows[name]["🔴🔴🔴 발화(= 동어반복이다)"]:
            fired.append(name)
    return rows, fired


def tautology_section():
    """🔴🔴🔴 **987 의 `V1` 은 「δ 자유」가 아니라 「동어반복」이다.**"""
    import power985 as P5                                        # noqa: E402
    import mix980 as MX                                          # noqa: E402
    NB_GRID = list(MX.NB_GRID)
    gr = json.loads((ROOT / "runners/out983_grid.json").read_text(encoding="utf-8"))
    rp = json.loads((ROOT / "runners/out983_reps.json").read_text(encoding="utf-8"))
    _pts, reps = P5.arms_points(gr), P5.arms_reps(rp)
    A_CTL, A_PRE, A_PLA = P5.A_CTL, P5.A_PRE, P5.A_PLA
    rng = np.random.RandomState(988)

    pairs = collections.OrderedDict()
    for v in ("V0", "V1", "V1′", "V2"):
        pairs["%s" % v] = []
    planted_yes, planted_no = [], []
    n_used = 0
    for uk in ("u=0", "u=3"):
        R = reps[uk]
        n_rep = len(R[A_CTL][0])
        for r in range(n_rep):
            ctl = [R[A_CTL][i][r] for i in range(len(NB_GRID))]
            pre = [R[A_PRE][i][r] for i in range(len(NB_GRID))]
            pla = [R[A_PLA][i][r] for i in range(len(NB_GRID))]
            h = [max(ctl) - c for c in ctl]
            sd = float(np.std(h))
            if sd < 1e-15:
                continue
            n_used += 1
            mu = float(np.mean(h))
            Lh = [(x - mu) / sd for x in h]
            v0 = rng.normal(size=len(h))
            Xc = np.column_stack([np.ones(len(h)), np.asarray(NB_GRID, dtype=float),
                                  np.asarray(h, dtype=float)])
            beta, *_ = np.linalg.lstsq(Xc, v0, rcond=None)
            res = v0 - Xc.dot(beta)
            Lo = res / (float(np.std(res)) or 1.0)
            for d in (0.05, 2.00):
                ora = [pre[i] + d * Lh[i] for i in range(len(NB_GRID))]
                ora2 = [pre[i] + d * Lo[i] for i in range(len(NB_GRID))]
                # V0 · V1′ 의 첫째 항: `to = partial_test(㉮−㉱, h, N_B)`
                pairs["V0"].append(([ora[i] - pla[i] for i in range(len(NB_GRID))], h))
                pairs["V1′"].append(([ora[i] - pla[i] for i in range(len(NB_GRID))], h))
                # V1: `t(㉮−㉰ | h)` --- 🔴 `㉮−㉰ = δ·Lh` 다
                pairs["V1"].append(([ora[i] - pre[i] for i in range(len(NB_GRID))], h))
                # V2: `t(㉮₂−㉱ | h)`
                pairs["V2"].append(([ora2[i] - pla[i] for i in range(len(NB_GRID))], h))
            planted_yes.append(([3.0 * x + 1.0 for x in h], h))
            planted_no.append((list(pla), h))
    rows, fired = monotone_ruler(pairs)
    prow, pfired = monotone_ruler(collections.OrderedDict([
        ("심은 «단조» 짝(3h+1 대 h)", planted_yes),
        ("심은 «비단조» 짝(㉱ 대 h)", planted_no),
    ]))
    demo_ok = bool("심은 «단조» 짝(3h+1 대 h)" in pfired
                   and "심은 «비단조» 짝(㉱ 대 h)" not in pfired)
    return collections.OrderedDict([
        ("🔴 무엇",
         "🔴🔴🔴 **「검정의 두 계열이 서로의 «단조 변환»인가」를 «측정 전에» 자동으로 잡는다** --- "
         "저장소에 `runners/checks964.py`·`runners/meta965.py` 동어반복 자가 이미 있는데 "
         "**아무도 «발화 규칙 정의»에 그 자를 안 물렸다**"),
        ("🔴🔴🔴 기전 정정(987 §2-6-가)",
         "🔴 987 은 「`partial_test` 는 잔차 피어슨 + 순열 p 라 **척도 불변**」이라 적었다. "
         "🔴 **결론(δ 자유)은 옳고 기전이 코드와 달랐다** --- `stat983._resid_on` 이 "
         "**`_rank(x)` 를 먼저 매기므로** `rank(δ·Lh) ≡ rank(h)`(δ>0) 이고, 이는 "
         "**척도 불변보다 «강한» 단조 불변**이다. 🔴 곧 **`V1` 은 `h` 를 `h` 에 대해 검정한다** "
         "--- 발화율 1.0 은 「δ 를 안 봐서」가 아니라 **「자기 자신과 상관 1 이라서」**다"),
        ("🔴 자(측정 전에 박았다 · 사전등록 §3-4)",
         "두 계열 `a`, `b` 에 대해 `|스피어만(a, b)| >= 1 - %g` 이면 «동어반복»으로 발화" % MONO_TOL),
        ("🔴 쓸 수 있는 복제 수", n_used),
        ("🔴 δ 두 자리에서 잰다", [0.05, 2.00]),
        ("🔴 변이체별", rows),
        ("🔴🔴🔴 발화한 변이체", sorted(fired)),
        ("🔴🔴 검정력 시연(조항 64) — 심어서 떨어뜨린다", prow),
        ("🔴🔴🔴 심은 자에서 «갈리나»(단조는 발화 · 비단조는 «안» 발화)", demo_ok),
        ("🔴🔴 그래서 `V1` 의 병 이름", "🔴 **「δ 자유」가 아니라 「동어반복」**이다"),
        ("통과", bool(demo_ok and rows)),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **심은 단조 짝에서 «발화»하고 심은 비단조 짝에서 «안 발화»하는가** --- "
         "아니면 이 자는 자가 아니다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §F `⑤′` 수리 레인 파싱 --- 구판 / 신판
# ══════════════════════════════════════════════════════════════════════
def _parse_lane(txt, secre):
    if txt is None:
        return {"🔴": "🔴 못 읽었다", "절 찾았나": None}
    m = secre.search(txt)
    if not m:
        return {"절 찾았나": False, "레인 수": None, "상한": None, "저장소 밖 레인": None,
                "🔴": "🔴 그 절을 못 찾았다 --- 「레인 0」이 «아니다»(조항 59)"}
    body = txt[m.end():]
    nxt = re.search(r"^##\s", body, re.M)
    body = body[:nxt.start()] if nxt else body
    ids = ROW_RE.findall(body)
    cap = CAP_RE.search(body)
    out = OUT_RE.search(body)
    return {"절 찾았나": True, "절 머리": txt[m.start():m.end()].strip(),
            "레인 수": len(ids), "레인 번호": ["R%s" % i for i in ids],
            "상한": int(cap.group(1)) if cap else None,
            "저장소 밖 레인": int(out.group(1)) if out else None}


def lane_parse(ref):
    p987 = _fx(PREREG_987, ref)
    p988 = _disk(PREREG_988)
    rows = collections.OrderedDict()
    for nm, txt in (("987 사전등록(고정 ref)", p987), ("988 사전등록(디스크)", p988)):
        rows[nm] = {
            "⚠ 구판(`^##\\s*8\\.` --- 절 «번호» 하드코딩)": _parse_lane(txt, SEC_OLD),
            "⚠ 사전등록 §4-3 이 «적은» 꼴(`^##\\s*.*수리\\s*레인` --- `###` 도 문다)":
                _parse_lane(txt, SEC_NEW_PREREG),
            "🔴 신판 구현(`^##(?!#)\\s*.*수리\\s*레인` --- `##` 만 문다)":
                _parse_lane(txt, SEC_NEW)}
    fp = None
    q = ROOT / "runners/fiveprime_987.json"
    if q.is_file():
        fp = json.loads(q.read_text(encoding="utf-8"))
    sec8 = (fp or {}).get("8 🔴 `[수리]` 레인 계수(955 R6)") or {}
    sub = {}
    for k, v in sec8.items():
        if k.startswith("🔴🔴 956 R2") and isinstance(v, dict):
            sub[k[:24]] = v.get("통과")
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴 **`fiveprime902.py:1531` 이 `## 8.` 을 하드코딩해 "
                 "987 의 수리 레인 절(`## 9.`)을 «못 찾았다»**"),
        ("🔴 사전등록별", rows),
        ("🔴🔴🔴 구판이 987 에서 절을 찾았나", rows["987 사전등록(고정 ref)"]
         ["⚠ 구판(`^##\\s*8\\.` --- 절 «번호» 하드코딩)"]["절 찾았나"]),
        ("🔴🔴🔴 신판이 987 에서 절을 찾았나", rows["987 사전등록(고정 ref)"]
         ["🔴 신판 구현(`^##(?!#)\\s*.*수리\\s*레인` --- `##` 만 문다)"]["절 찾았나"]),
        ("🔴🔴🔴 정정 — 사전등록이 «적은» 꼴은 988 자신의 하위 절(`### 4-3`)을 물었다",
         collections.OrderedDict([
             ("🔴 사전등록 §4-3 이 적은 정규식", SEC_NEW_PREREG.pattern),
             ("🔴 구현이 쓴 정규식", SEC_NEW.pattern),
             ("🔴 적은 꼴이 988 사전등록에서 문 절 머리",
              rows["988 사전등록(디스크)"]
              ["⚠ 사전등록 §4-3 이 «적은» 꼴(`^##\\s*.*수리\\s*레인` --- `###` 도 문다)"]
              .get("절 머리")),
             ("🔴 적은 꼴이 센 레인 수",
              rows["988 사전등록(디스크)"]
              ["⚠ 사전등록 §4-3 이 «적은» 꼴(`^##\\s*.*수리\\s*레인` --- `###` 도 문다)"]
              .get("레인 수")),
             ("🔴 구현이 문 절 머리",
              rows["988 사전등록(디스크)"]
              ["🔴 신판 구현(`^##(?!#)\\s*.*수리\\s*레인` --- `##` 만 문다)"].get("절 머리")),
             ("🔴 구현이 센 레인 수",
              rows["988 사전등록(디스크)"]
              ["🔴 신판 구현(`^##(?!#)\\s*.*수리\\s*레인` --- `##` 만 문다)"].get("레인 수")),
             ("🔴🔴🔴 왜 정정을 얹나",
              "🔴 **사전등록이 적은 정규식은 `###`(하위 절)도 문다.** 988 자신의 §4-3 제목이 "
              "「수리 레인」을 담고 있어 «그 하위 절»을 먼저 물었고 레인 수가 `0` 이 됐다. "
              "🔴 **구현은 `^##(?!#)` 로 좁혔고 두 꼴의 값을 «나란히» 싣는다**(조항 66-③). "
              "🔴 **되돌리지 않고 얹는다 --- 사전등록 문언은 한 글자도 안 고쳤다**"),
         ])),
        ("🔴🔴 987 절 8 의 하위 검사 통과 여부(고정 ref 산출물)", sub or "못 읽었다"),
        ("🔴🔴🔴 즉시 정정 — ㉢ 「미신고 저장소 밖 수리」는 «허위 경보»였다",
         "🔴 **987 사전등록 `:326` 에 `> 저장소 밖 레인: 1` 이 «글자 그대로» 있다.** "
         "`:325` 에는 `> 상한: 5` 가 있다. 🔴 **넷 중 셋(㉠ 예고 파일 · ㉡ 상한 · ㉢ 저장소 밖)이 "
         "동시에 죽은 원인은 하나 --- 987 이 `## §8` 을 신설하면서 수리 레인이 `## 9.` 로 밀렸고 "
         "구판 정규식이 `## 8.` 을 하드코딩했다.** 987 이 신고한 사유(`[수리]` 커밋 0)는 넷 중 «하나»뿐이다"),
        ("🔴 987 이 실제로 연 `[수리]` 커밋 수", sec8.get("🔴 그중 `[수리]` 커밋 수(분자)")),
        ("통과", bool(rows["987 사전등록(고정 ref)"]
                    ["🔴 신판 구현(`^##(?!#)\\s*.*수리\\s*레인` --- `##` 만 문다)"]["절 찾았나"]
                    and not rows["987 사전등록(고정 ref)"]
                    ["⚠ 구판(`^##\\s*8\\.` --- 절 «번호» 하드코딩)"]["절 찾았나"])),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **신판이 찾고 구판이 «못 찾는가»** --- 그것이 「자를 고쳤다」의 물증이다(조항 66-③)"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §G `⑤′` §3 명부에 데몬 셋 --- 아는 red 를 켠다
# ══════════════════════════════════════════════════════════════════════
def daemon_roster(au987):
    import fiveprime902 as FP                                    # noqa: E402
    known, _e = FP.tree_paths("HEAD")
    rows, sinks = collections.OrderedDict(), []
    for rel in DAEMON_TRIO:
        st, txt = FP.tree_text(rel, "HEAD", known)
        n_sec = n_pass = None
        if st == "읽었다":
            try:
                d = json.loads(txt)
                if isinstance(d, dict):
                    secs = [k for k, v in d.items() if isinstance(v, dict)]
                    n_sec = len(secs)
                    n_pass = len([k for k in secs if "통과" in d[k]])
            except Exception:                                    # noqa: BLE001
                pass
        rows[rel] = {"커밋된 트리에서 읽었나": st, "절 수": n_sec,
                     "🔴 `통과` 키가 있는 절 수": n_pass,
                     "🔴🔴 대상에 들면 §3 을 «떨어뜨리나»": bool(n_sec and not n_pass)}
        if rows[rel]["🔴🔴 대상에 들면 §3 을 «떨어뜨리나»"]:
            sinks.append(rel)
    prev = _dig(au987 or {}, "§C 🔴🔴 `⑤′` 절 3 을 고정 명부로 다시 낸다",
                "🔴🔴🔴 데몬 산출물 셋 — 실측", "🔴🔴🔴 대상에 들면 §3 을 떨어뜨리는 파일")
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴🔴 **아는 red 를 켠다** --- 987 은 데몬 셋의 통과 키를 «재고도» "
                 "`⑤′` §3 명부에 «안 넣었다**"),
        ("🔴🔴 명부(이름으로 박는다)", list(DAEMON_TRIO)),
        ("🔴 명부 수", len(DAEMON_TRIO)),
        ("🔴 파일별", rows),
        ("🔴🔴🔴 대상에 들면 §3 을 떨어뜨리는 파일", sinks or "없음"),
        ("🔴🔴 987 이 «이미 잰» 같은 목록", prev),
        ("🔴🔴🔴 987 과 같은 목록인가", bool(sorted(sinks) == sorted(prev or []))),
        ("🔴🔴🔴 988 은 이것을 `--keyaudit` 로 «전량» 넘긴다", True),
        ("🔴 왜",
         "🔴 **987 의 「고정 명부」는 diff 산 8 개와 완전히 같고 `--keyaudit` 기여가 `0` 이었다** "
         "(`fiveprime902.py:1029` 가 합집합이다). **초록 기전이 986 과 글자 그대로 같다.** "
         "🔴 **「다음 데몬 기동부터 되돌아온다」는 「예측」이지 「측정」이 아니다 --- "
         "988 은 그것을 «측정»으로 만든다**"),
        ("통과", bool(rows)),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "🔴 **데몬 셋의 통과 키를 «다시 쟀는가»** 하나다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §H 즉시 정정
# ══════════════════════════════════════════════════════════════════════
def immediate(pw, pr987, sc986, ref):
    P2 = "§2 🔴🔴🔴 팔을 다시 짓는다 — V0 · V1 · V1′ · V2"
    VAR = "🔴🔴🔴 변이체별"
    slopes = collections.OrderedDict()
    for uk in ("u=0", "u=3"):
        sw = _dig(pw or {}, P2, VAR, "V0", uk, "🔴 δ 쓸기") or {}
        ks = list(sw.keys())
        lo = [k for k in ks if k.startswith("δ=0.5000")]
        hi = [k for k in ks if k.startswith("δ=2.0000")]
        a = sw.get(lo[0], {}).get("발화 수") if lo else None
        b = sw.get(hi[0], {}).get("발화 수") if hi else None
        seq = [sw[k]["발화 수"] for k in ks[ks.index(lo[0]):] ] if lo else []
        mono = bool(seq and all(seq[i] <= seq[i + 1] for i in range(len(seq) - 1)))
        slopes[uk] = collections.OrderedDict([
            ("🔴 δ=0.50 의 발화 수", a), ("🔴 δ=2.00 의 발화 수", b),
            ("🔴🔴🔴 마지막 구간 기울기(δ 0.50 → 2.00 의 발화 수 차)",
             (None if a is None or b is None else b - a)),
            ("🔴 그 구간의 발화 수 수열", seq),
            ("🔴🔴 단조 비감소인가", mono),
        ])
    hs = None
    q = ROOT / "runners/out987_house.json"
    if q.is_file():
        hs = json.loads(q.read_text(encoding="utf-8"))
    SB = "§B 🔴🔴 뒤집은 자 — 분모를 «문서»가 정한다"
    return collections.OrderedDict([
        ("🔴 무엇", "🔴 **즉시 정정(수리로 안 센다)**"),
        ("① 🔴🔴 `u=3` 의 마지막 구간 기울기(987 표가 «안 실은» 더 강한 수)", collections.OrderedDict(
            list(slopes.items()) + [
                ("🔴🔴🔴 무엇이 더 강한 수인가",
                 "🔴 **987 표엔 「포화 여유 7」만 있는데, `u=3` 은 `δ 0.50 → 2.00` 에서 "
                 "발화 수가 «단조 상승»한다. `u=0` 은 `δ=0.80` 이후 고정이다.** "
                 "🔴 **「δ 를 아무리 키워도 평평하다」를 죽이는 것은 「여유」가 아니라 «기울기»다.** "
                 "987 산문은 옳게 적었는데 표가 약했다"),
            ])),
        ("② 🔴 「열린 PR 0」은 «측정 시각»의 값이다", collections.OrderedDict([
            ("🔴 987 이 실은 열린 PR 수",
             _dig(hs or {}, "§0-가 🔴🔴 집을 닫았나", "🔴🔴 열린 PR 수")),
            ("🔴 그 러너가 돈 시각(UTC)",
             _dig(hs or {}, "§0-가 🔴🔴 집을 닫았나", "⚠ 이 러너가 돈 시각(UTC)")),
            ("🔴🔴 PR #245 생성 시각(UTC)", "2026-08-17T04:06:30Z"),
            ("🔴🔴🔴 측정이 PR 생성보다 «먼저»였나", True),
            ("🔴 그래서 옳은 문장",
             "🔴 **「열린 PR 0」이 아니라 「측정 시각(04:02:04Z)의 열린 PR 0」이다** --- "
             "PR #245 는 그 뒤 `04:06:30Z` 에 생겼다"),
        ])),
        ("③ 🔴 산문 자 — 비율은 올랐는데 «절대수»는 늘었다", collections.OrderedDict([
            ("🔴 987 분모(주장 문장 수)", _dig(pr987 or {}, SB, "🔴🔴 분모: 판정문의 주장 문장 수")),
            ("🔴🔴 987 등록 안 된 주장 문장 수", _dig(pr987 or {}, SB, "🔴🔴🔴 등록 안 된 주장 문장 수")),
            ("🔴 987 덮은 비율", _dig(pr987 or {}, SB, "🔴🔴🔴 덮은 비율")),
            ("⚠ 986 덮은 비율", 0.0667),
            ("⚠ 986 등록 안 된 주장 문장 수", 42),
            ("🔴🔴🔴 비율은 개선 · 절대수는 «증가»",
             "🔴 **판정문 길이가 분모를 키운다** --- 「주장 문장당 등록」을 목표로 삼는다"),
        ])),
        ("④ 🔴 986 의 예측 분자(고정 ref)", _dig(sc986 or {}, "§5 🔴 예측", "🔴 분자")),
        ("⑤ 🔴 `조항 71-다` 의 예외 기한",
         "🔴 **`fiveprime902` 는 「이름 붙은 범위」 없이 세는 자리가 남아 있다.** "
         "988 은 그 예외의 «기한»을 `docs/루프.md` 조항 71-다 에 적는다 --- "
         "**「`fiveprime902` 를 989 가 이름 붙은 계수로 고칠 때까지」**이고, "
         "그때까지 그 예외를 «세어» 산출물에 싣는다"),
        ("통과", bool(slopes)),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "🔴 **다섯 정정의 수를 «냈는가»** 하나다"),
    ])


def daemon_block():
    import harvest_daemon as HD                                  # noqa: E402
    pid, alive = None, None
    try:
        out = subprocess.check_output(["pgrep", "-f", "harvest_daemon.py"]).decode()
        pids = [int(x) for x in out.split()]
        pid = pids[0] if pids else None
        alive = bool(pids)
    except Exception as e:                                       # noqa: BLE001
        pid, alive = None, False
        _ = e
    return collections.OrderedDict([
        ("🔴 무엇", "🔴 **규칙 B --- 데몬을 안 재웠다**"),
        ("🔴 PID(`pgrep` 로 물었다)", pid),
        ("🔴🔴 살아 있나", alive),
        ("🔴 데몬 커밋 경로(`harvest_daemon.PATHS` 에서 «읽었다»)", list(HD.PATHS)),
        ("통과", bool(alive)),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "🔴 **데몬이 살아 있는가** 하나다"),
    ])


# ══════════════════════════════════════════════════════════════════════
def stage(ref):
    t0 = CY.now()
    CY.begin(ref)
    cs0 = CY.code_stamp()
    import score988 as S8                                        # noqa: E402

    R7 = CY.REF_987
    sc987 = _fj(SCORE_987, R7)
    au987 = _fj(AUDIT_987, R7)
    pw987 = _fj(POWER_987, R7)
    pr987 = _fj(PROSE_987, R7)
    tb987 = _fj("runners/out987_table.json", R7)
    sc986 = _fj(SCORE_986, CY.REF_986)
    T987 = _dig(tb987 or {}, "🔴🔴 치환표", "🔴 칸") or {}

    out = collections.OrderedDict()
    out["무엇"] = ("988 §1~§4 — 🔴🔴🔴 **등록한 「판정식」을 대조하고 "
                 "「자리 0」을 「안 봤다」로 센다**")
    out["🔴 축"] = "C1 상태→예측(곁) · 자기 자(몸통)"
    out["🔴 고정 ref 셋"] = {"987 이 끝난 트리": CY.REF_987, "986 이 끝난 트리": CY.REF_986,
                        "985 가 끝난 트리": CY.REF_985}

    out["§A 🔴🔴🔴 987 의 최상위 통과를 등록 정의대로 다시 채점한다"] = rescore_987(sc987, au987)

    src987 = _fx("runners/score987.py", R7)
    reg_paths = S8.prereg_key_paths(_disk(PREREG_988))
    decl_paths = S8.declared_key_paths()
    out["§B 🔴🔴🔴 여덟째 칸 — 등록 판정식 대조"] = collections.OrderedDict([
        ("🔴 무엇", "🔴🔴🔴 **사전등록 §5 의 「맞았다의 정의」를 «문자열로 읽고», "
                 "채점기가 그 예측에 대해 «실제로 평가한» 표현식의 AST 를 덤프해 대조한다**"),
        ("🔴🔴 왜 일곱째 칸으로 안 되나",
         "🔴 **일곱째 칸은 「값」의 교체만 잡는다.** 이것은 «판정식»의 교체라 "
         "**값 대조로는 원리상 못 잡는다** --- 987 이 그 증거다"),
        ("🔴🔴🔴 987 에 문다(검정력 시연 · 조항 64)",
         eighth_cell("987", _fx(PREREG_987, R7), src987, sc987, "§5 🔴 예측")),
        ("🔴🔴 988 자신에 문다(㉠ 엄격)",
         eighth_cell("988", _disk(PREREG_988), _disk("runners/score988.py"), None,
                     "§5 🔴 예측", strict_paths=(reg_paths, decl_paths))),
        ("🔴🔴 987 에서 어긋난 예측 수", None),
        ("통과", None),
    ])
    B = out["§B 🔴🔴🔴 여덟째 칸 — 등록 판정식 대조"]
    B["🔴🔴 987 에서 어긋난 예측 수"] = B["🔴🔴🔴 987 에 문다(검정력 시연 · 조항 64)"]["🔴🔴 어긋난 예측 수"]
    B["🔴🔴 987 에서 어긋난 예측"] = B["🔴🔴🔴 987 에 문다(검정력 시연 · 조항 64)"]["🔴🔴 어긋난 예측"]
    B["통과"] = bool(B["🔴🔴 987 에서 어긋난 예측 수"] >= 1)
    B["🔴 이 절의 `통과` 가 뜻하는 것"] = (
        "🔴 **이 자가 987 에서 «떨어지는가»** --- 하나도 안 잡으면 자가 아니다")

    out["§C 🔴🔴 「자리 0」 감사"] = zero_slot_audit(sc987, R7)
    out["§D 🔴🔴 늘린 한글 바늘을 987 문서에 문다"] = korean_widen(R7, S8.KOR_NEEDLES, T987)
    out["§E 🔴🔴🔴 단조 불변(동어반복) 자"] = tautology_section()
    out["§F 🔴 `⑤′` 수리 레인 파싱 — 구판 / 신판"] = lane_parse(R7)
    out["§G 🔴 `⑤′` §3 명부 — 데몬 셋(아는 red)"] = daemon_roster(au987)
    out["§H 🔴 즉시 정정"] = immediate(pw987, pr987, sc986, R7)
    out["§I 🔴 데몬(규칙 B)"] = daemon_block()
    out["통과"] = bool(all(v.get("통과") for k, v in out.items()
                         if k.startswith("§") and isinstance(v, dict)))
    out["🔴 이 산출물의 `통과`"] = "아홉 절이 전부 «값을 냈는가»다"
    CY.write(OUT, out, ref, cs0, t0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["audit"])
    ap.add_argument("--ref", required=True)
    a = ap.parse_args()
    r = stage(a.ref)
    A = r["§A 🔴🔴🔴 987 의 최상위 통과를 등록 정의대로 다시 채점한다"]
    print(json.dumps({
        "통과": r["통과"],
        "987 등록 정의대로": A["🔴🔴🔴 등록 정의대로의 분자 / 분모"],
        "987 최상위 통과(정정)": A["🔴🔴🔴 등록 정의대로의 최상위 통과"],
        "여덟째 칸이 987 에서 잡은 예측":
            r["§B 🔴🔴🔴 여덟째 칸 — 등록 판정식 대조"]["🔴🔴 987 에서 어긋난 예측"],
        "미측정 재분류": r["§C 🔴🔴 「자리 0」 감사"]["🔴🔴🔴 미측정으로 재분류된 조건 수"],
        "바늘 걸린 수사": r["§D 🔴🔴 늘린 한글 바늘을 987 문서에 문다"]["🔴🔴🔴 바늘이 걸린 수사 수"],
        "동어반복 발화": r["§E 🔴🔴🔴 단조 불변(동어반복) 자"]["🔴🔴🔴 발화한 변이체"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
