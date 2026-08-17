#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""989 감사 — **경로 동일성 여덟째 칸** · **「걸린 자리」 정의** · **단조 자 수리**.

사전등록 `docs/prereg_989_world_budget.md` §2·§3 을 그대로 따른다.

🔴 이 러너는 «세계 자료»를 안 읽는다. 세계 명제는 `runners/world989.py` 가 낸다.
   **이 러너의 산출물은 §1(세계 명제)에 «못 들어간다».**
"""
import argparse
import ast
import collections
import datetime as dt
import hashlib
import json
import math
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

import audit988 as A8                                # noqa: E402

RAN = ("runners/audit989.py", "runners/audit988.py")
OUT = ROOT / "runners"
PREREG_989 = "docs/prereg_989_world_budget.md"
PREREG_987 = "docs/prereg_987_ceiling_identity_fixed_ref.md"
PREREG_988 = "docs/prereg_988_registered_predicate.md"
MONO_TOL = 1e-12
# 🔴 989 의 러너 전량 — §1-5 ㉠ 의 정적 분모
RAN_989 = ("runners/world989.py", "runners/audit989.py", "runners/score989.py",
           "runners/note989_gen.py")


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _r(x, n=6):
    if x is None:
        return None
    x = float(x)
    return None if not np.isfinite(x) else round(x, n)


def code_stamp():
    out = collections.OrderedDict()
    for rel in RAN:
        p = ROOT / rel
        out[rel] = hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
    return out


def _show(ref, rel):
    try:
        return subprocess.check_output(
            ["git", "-c", "core.quotePath=false", "show", "%s:%s" % (ref, rel)],
            cwd=str(ROOT)).decode("utf-8")
    except subprocess.CalledProcessError:
        return None


# ══════════════════════════════════════════════════════════════════════
# §A 🔴🔴🔴 경로 동일성 — 여덟째 칸의 «신판»
# ══════════════════════════════════════════════════════════════════════
def _cellmap(src, func="predict"):
    """🔴 예측별로 **「게재 칸 이름 → 그 칸을 «만든» 표현식」** 을 낸다.

    구판(`audit988.predicate_ast`)은 **게재 «문자열 전량»** 과 **평가 집합**만 냈다.
    신판은 그 사이의 «다리»(칸 → 만든 식)를 놓는다 --- 그게 「경로 동일성」의 핵이다.
    """
    out = collections.OrderedDict()
    try:
        tree = ast.parse(src or "")
    except SyntaxError:
        return out, {}
    fn = None
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and n.name == func:
            fn = n
            break
    if fn is None:
        return out, {}
    assigns = collections.defaultdict(list)
    for st in ast.walk(fn):
        if isinstance(st, ast.Assign):
            for t in st.targets:
                if isinstance(t, ast.Name):
                    assigns[t.id].append(st.value)
    for st in ast.walk(fn):
        if not (isinstance(st, ast.Assign) and len(st.targets) == 1
                and isinstance(st.targets[0], ast.Subscript)):
            continue
        sl = st.targets[0].slice
        if not (isinstance(sl, ast.Constant) and isinstance(sl.value, str)):
            continue
        m = re.match(r"\s*(P\d+)\b", sl.value)
        if not m:
            continue
        cells, hit_expr = collections.OrderedDict(), None
        for t in ast.walk(st.value):
            if isinstance(t, ast.Tuple) and len(t.elts) == 2 \
                    and isinstance(t.elts[0], ast.Constant) \
                    and isinstance(t.elts[0].value, str):
                cname = t.elts[0].value
                cells[cname] = t.elts[1]
                if "맞았나" in cname:
                    hit_expr = t.elts[1]
        out[m.group(1)] = (cells, hit_expr)
    return out, assigns


def _paths(expr, assigns, seen=None, depth=0):
    """🔴 표현식의 «후향 슬라이스 문자열 키 경로 집합»."""
    if expr is None:
        return set()
    seen = set() if seen is None else seen
    got = {n.value for n in ast.walk(expr)
           if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    if depth > 6:
        return got
    for nm in {n.id for n in ast.walk(expr) if isinstance(n, ast.Name)}:
        if nm in seen:
            continue
        seen.add(nm)
        for v in assigns.get(nm, []):
            got |= _paths(v, assigns, seen, depth + 1)
    return got


def path_identity_ast(cycle, prereg_txt, score_src):
    """🔴🔴🔴 **경로 동일성** --- 「등록 주어 → 게재 «칸 이름» → 그 칸을 «만든» 식」.

    🔴 **구판**(`audit988._match`)은 등록 «주어»(산문)를 «평가 집합»(키 경로)과
    직접 퍼지 대조했다. **이름 공간이 다르다.** 그래서 `P4` 를 «허위 양성»으로 잡았다.
    🔴 **신판**은 퍼지를 **칸 «이름» 찾기 한 걸음에만** 쓰고, 판정은
    **두 «표현식»의 키 경로 포함 관계**로 낸다.
    """
    reg = A8.prereg_predictions(prereg_txt)
    cmap, assigns = _cellmap(score_src or "")
    per = collections.OrderedDict()
    swapped, renamed, unmatched, compared = [], [], [], 0
    for pid, rr in reg.items():
        d = rr["🔴🔴🔴 등록한 「맞았다의 정의」(«문자열 그대로»)"]
        subj, op, rhs = A8._split_def(d)
        nsubj = A8._norm(subj)
        cells, hit_expr = cmap.get(pid, (collections.OrderedDict(), None))
        # ── ① 등록 주어 → 게재 «칸 이름» (여기서만 퍼지 · 라벨은 산문이다) ──
        cand = None
        for cname in cells:
            if "맞았나" in cname:
                continue
            x = A8._norm(cname)
            if not x or not nsubj:
                continue
            if x == nsubj:
                cand = (cname, "정확")
                break
            if cand is None and (nsubj in x or x in nsubj
                                 or A8._lcs_len(nsubj, x) >= 4):
                cand = (cname, "느슨")
        row = collections.OrderedDict([
            ("🔴 등록한 「맞았다의 정의」", d),
            ("🔴 등록 주어", subj), ("🔴 연산자", op), ("🔴 등록 우변", rhs),
            ("🔴 게재 칸 전량", list(cells.keys())),
        ])
        if cand is None or hit_expr is None:
            row["🔴🔴 대응한 게재 칸"] = None
            row["🔴🔴🔴 판정"] = "🔴 미대응 --- 「교체」로 «안» 센다(조항 59-나)"
            row["🔴 비교를 «수행»했나"] = False
            unmatched.append(pid)
            per[pid] = row
            continue
        cname, how = cand
        pc = _paths(cells[cname], assigns)
        ph = _paths(hit_expr, assigns)
        ident = bool(pc) and pc <= ph
        compared += 1
        row["🔴🔴 대응한 게재 칸"] = cname
        row["🔴 칸 찾기(정확 / 느슨)"] = how
        row["🔴🔴 그 칸을 «만든» 식의 키 경로"] = sorted(pc)
        row["🔴🔴 「맞았나」 식의 키 경로"] = sorted(ph)
        row["🔴🔴🔴 경로 동일성(칸 경로 ⊆ 맞았나 경로)"] = ident
        row["🔴 칸 이름이 등록 주어와 «글자 그대로» 같은가"] = bool(how == "정확")
        row["🔴 비교를 «수행»했나"] = True
        if not ident:
            row["🔴🔴🔴 판정"] = "🔴🔴🔴 판정식 «교체» --- 반증"
            row["🔴 칸 경로에만 있는 것"] = sorted(pc - ph)
            swapped.append(pid)
        elif how != "정확":
            row["🔴🔴🔴 판정"] = "🔴 라벨 «개명» --- 판정식은 같다. «반증이 아니다»"
            renamed.append(pid)
        else:
            row["🔴🔴🔴 판정"] = "동일"
        per[pid] = row
    return collections.OrderedDict([
        ("🔴 대상", cycle), ("🔴 자", "AST 모드(채점기가 행을 «리터럴»로 짓는다)"),
        ("🔴 분모(사전등록 §5 의 예측 수)", len(reg)),
        ("🔴 예측별", per),
        ("🔴🔴🔴 판정식 교체", swapped or "없음"),
        ("🔴🔴🔴 판정식 교체 수", len(swapped)),
        ("🔴🔴 라벨 개명(반증 아님)", renamed or "없음"),
        ("🔴🔴 라벨 개명 수", len(renamed)),
        ("🔴 미대응(측정 못 함)", unmatched or "없음"),
        ("🔴🔴🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", compared),
        ("🔴🔴 미측정인가(조항 59-나 · 걸린 자리 0)", bool(compared == 0)),
    ])


def path_identity_table(cycle, prereg_txt, score_mod):
    """🔴 **선언표 모드** --- 채점기가 `PRED_DEF` 하나로만 도는 경우(988).

    🔴 이때 「그 칸을 만든 식」은 **표의 행 자체**다. 경로 동일성은
    **사전등록이 등록한 키 경로 == 표가 선언한 키 경로**로 «직접» 난다.
    🔴 **AST 모드를 그대로 물리면 「게재 칸」이 하나도 안 잡혀 «빈 집합 위의 초록»이 된다** ---
    그것을 「통과」로 세지 않으려고 모드를 가른다(조항 59-나).
    """
    reg = A8.prereg_predictions(prereg_txt)
    decl = getattr(score_mod, "PRED_DEF", None) or {}
    per, swapped, compared = collections.OrderedDict(), [], 0
    for pid, rr in reg.items():
        d = rr["🔴🔴🔴 등록한 「맞았다의 정의」(«문자열 그대로»)"]
        m = re.search(r"판정식\s*:\s*(.+)$", d)
        body = (m.group(1) if m else d).strip().strip("`")
        m2 = re.match(r"([A-Za-z_0-9]+)#(.+)$", body)
        reg_src, reg_keys, reg_op, reg_val = None, None, None, None
        if m2:
            reg_src = m2.group(1)
            rest = m2.group(2)
            for op in ("==", ">=", "<=", "!=", ">", "<"):
                i = rest.rfind(op)
                if i > 0:
                    reg_keys = [c.strip().strip("`")
                                for c in rest[:i].split("|")]
                    reg_op, reg_val = op, rest[i + len(op):].strip()
                    break
        got = decl.get(pid)
        row = collections.OrderedDict([
            ("🔴 등록한 「맞았다의 정의」", d),
            ("🔴 사전등록 산출물", reg_src),
            ("🔴 사전등록 키 경로", reg_keys),
            ("🔴 사전등록 연산자", reg_op),
            ("🔴 선언표 행", (list(got[0:1]) + [list(got[1])] + list(got[2:]))
             if got else None),
        ])
        if got is None or reg_keys is None:
            row["🔴🔴🔴 판정"] = "🔴 미대응 --- 「교체」로 «안» 센다"
            row["🔴 비교를 «수행»했나"] = False
            per[pid] = row
            continue
        compared += 1
        d_src, d_keys, d_op = got[0], [str(x) for x in got[1]], got[2]
        ident = (A8._norm(d_src) == A8._norm(reg_src or "")
                 and [A8._norm(x) for x in d_keys] == [A8._norm(x) for x in reg_keys]
                 and d_op == reg_op)
        row["🔴 비교를 «수행»했나"] = True
        row["🔴🔴🔴 경로 동일성"] = bool(ident)
        row["🔴🔴🔴 판정"] = "동일" if ident else "🔴🔴🔴 판정식 «교체» --- 반증"
        if not ident:
            swapped.append(pid)
        per[pid] = row
    return collections.OrderedDict([
        ("🔴 대상", cycle), ("🔴 자", "선언표 모드(`PRED_DEF` 하나로만 돈다)"),
        ("🔴 분모(사전등록 §5 의 예측 수)", len(reg)),
        ("🔴 예측별", per),
        ("🔴🔴🔴 판정식 교체", swapped or "없음"),
        # 🔴 사전등록 §4 의 `P5` 가 «등록한 문자열 그대로»의 키다(`조항 72-라`).
        #    🔴 구판 키 이름은 `🔴🔴🔴 판정식 교체 수` 였다 --- 등록 문안에 맞춰 «고쳤다».
        ("🔴 %s 에서 판정식 교체 수" % cycle, len(swapped)),
        ("🔴🔴🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", compared),
        ("🔴🔴 미측정인가(조항 59-나 · 걸린 자리 0)", bool(compared == 0)),
    ])


# ══════════════════════════════════════════════════════════════════════
# §C 🔴🔴 988 의 P1 을 «신판 자»로 다시 잰다
# ══════════════════════════════════════════════════════════════════════
def rescore_988(ident987, sc988, mono):
    """🔴 988 의 예측을 «두 수리»로 다시 잰다.

    🔴 **`P1`** --- 「어긋난 예측이 «정확히 하나»」. 구판 자가 «둘」을 세어 떨어졌다.
    🔴 **`P4`** --- 「발화한 변이체 == ["V1"]」. 🔴🔴 **988 은 등록 기준(「짝마다 발화」)을
       `n_fire == n_ok`(변이체마다 «100%%»)로 갈아 끼웠다.** 등록 문안 그대로 재면
       `V0 / V1′` 계열도 발화해 **`P4` 는 «틀렸다»**.
    """
    n_new = ident987["🔴🔴🔴 판정식 교체 수"]
    fired_reg = mono["🔴🔴🔴 등록 문안으로 발화한 계열"]
    fired_988 = mono["🔴 988 구현으로 발화한 계열"]
    p4_reg = bool([x for x in fired_reg if x.startswith("V1 ")] == fired_reg)
    old_rows = A8._dig(sc988 or {}, "§5 🔴 예측", "🔴 예측별") or {}
    per = collections.OrderedDict()
    hit_old, hit_path, hit_both = 0, 0, 0
    for pid, row in old_rows.items():
        was = bool(row.get("🔴 맞았나"))
        v_path, v_both, note = was, was, "안 바뀐다"
        if pid == "P1":
            v_path = v_both = bool(n_new == 1)
            note = ("🔴🔴 988 은 구판 자가 «둘»(P4·P6)을 세어 자기 예측을 떨궜다. "
                    "🔴 `P4` 는 «허위 양성»이고 참값은 «하나»(P6)이므로 «맞았다»")
        if pid == "P4":
            v_both = p4_reg
            note = ("🔴🔴🔴 988 은 등록 기준(「짝마다 |스피어만|=1 이면 발화」)을 "
                    "`n_fire == n_ok`(변이체마다 100%%)로 «갈아 끼웠다». "
                    "🔴 등록 문안 그대로 재면 발화 계열이 %s 라 «V1 만»이 «아니다» --- "
                    "`조항 72-라` 위반이고 이 예측은 «틀렸다»" % (fired_reg,))
        hit_old += int(was)
        hit_path += int(v_path)
        hit_both += int(v_both)
        per[pid] = collections.OrderedDict([
            ("🔴 988 이 적은 값", was),
            ("🔴 ① 경로 동일성만 물린 값", v_path),
            ("🔴🔴 ② 경로 동일성 + `조항 72-라` 를 물린 값", v_both),
            ("🔴 바뀌었나", bool(was != v_both)), ("🔴 왜", note)])
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴 988 의 예측을 «경로 동일성 자»와 «조항 72-라»로 다시 채점한다"),
        ("🔴 신판 자가 987 에서 센 판정식 교체 수", n_new),
        ("🔴 구판 자가 987 에서 센 수(988 이 적은 것)", 2),
        ("🔴 등록 문안으로 발화한 계열", fired_reg),
        ("🔴 988 구현으로 발화한 계열", fired_988),
        ("🔴 예측별", per),
        ("🔴🔴 ⓐ 988 이 적은 분자 / 분모", "%d / %d" % (hit_old, len(per))),
        ("🔴🔴 ⓑ 경로 동일성만 물린 분자 / 분모(= 티처 #127 이 준 수)",
         "%d / %d" % (hit_path, len(per))),
        ("🔴🔴🔴 ⓒ 경로 동일성 + `조항 72-라` 를 물린 분자 / 분모",
         "%d / %d" % (hit_both, len(per))),
        ("🔴🔴🔴 ⓐ 와 ⓒ 는 «같은 수»이나 «다른 집합»이다",
         collections.OrderedDict([
             ("988 이 맞았다고 센 것",
              [p for p, r in per.items() if r["🔴 988 이 적은 값"]]),
             ("🔴 ⓒ 에서 맞은 것",
              [p for p, r in per.items()
               if r["🔴🔴 ② 경로 동일성 + `조항 72-라` 를 물린 값"]])])),
        ("🔴🔴🔴 정정이 필요한가", bool(hit_old != hit_both or hit_old != hit_path)),
        ("🔴 이 정정은 «얹기»다", "🔴 988 문서를 안 지운다. 정정 블록을 «추가»한다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §D 🔴 `R1` --- 「걸린 자리」의 정의를 못 박고 988 을 다시 잰다
# ══════════════════════════════════════════════════════════════════════
HIT_KEY = re.compile(r"걸린|잡은|매치|어긋난|발화한|물린|검사한|대조한")
DEN_KEY = re.compile(r"분모|대상|센\s|후보|명부|목록")
MADE_KEY = re.compile(r"등록\s*바늘|바늘\s*수|만든|생성|후보\s*자리")


def _walk_pass(obj, path=()):
    """🔴 `통과` 키를 내는 절을 «전량» 훑는다 --- 명부를 손으로 «안» 고른다(`R1`)."""
    if isinstance(obj, dict):
        if "통과" in obj and isinstance(obj.get("통과"), bool):
            yield path, obj
        for k, v in obj.items():
            for x in _walk_pass(v, path + (str(k),)):
                yield x
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            for x in _walk_pass(v, path + ("[%d]" % i,)):
                yield x


def _ints(d, rex):
    out = collections.OrderedDict()
    for k, v in d.items():
        if isinstance(v, bool) or not isinstance(v, int):
            continue
        if rex.search(str(k)):
            out[str(k)] = v
    return out


def hits_audit(objs):
    """🔴🔴🔴 **`조항 59-나` 개정 --- 「걸린 자리」 = 자가 «비교»를 «수행»한 회수.**

    🔴 **바늘 «생성» 수 · 후보 «자리» 수는 「걸린 자리」가 «아니다»**(`F07`).
    🔴 **명부를 손으로 «안» 고른다** --- `통과` 키를 내는 절 «전량»에 자동으로 문다.
    """
    rows, unmeasured, greens, mislabeled = collections.OrderedDict(), [], 0, []
    for name, obj in objs.items():
        for path, node in _walk_pass(obj, (name,)):
            key = " | ".join(path) or name
            if key in rows:
                continue
            hits = _ints(node, HIT_KEY)
            dens = _ints(node, DEN_KEY)
            made = _ints(node, MADE_KEY)
            n_hit = max(hits.values()) if hits else None
            n_den = max(dens.values()) if dens else None
            green = bool(node.get("통과"))
            greens += int(green)
            # 🔴 「걸린 자리」를 «셀 수 없는» 절은 「미측정」이 «아니다» --- 갈라 센다
            if n_hit is None:
                verdict = "🔴 걸린 자리를 이 절에서 «셀 수 없다»(자동 자의 한계)"
            elif n_hit == 0:
                verdict = "🔴🔴🔴 미측정 --- 걸린 자리 0(조항 59-나)"
            else:
                verdict = "잰 것이 있다"
            if green and n_hit == 0:
                unmeasured.append(key)
            if made and n_hit is not None and made and n_hit != list(made.values())[0]:
                mislabeled.append(collections.OrderedDict([
                    ("절", key), ("🔴 «만든» 수", made), ("🔴 «걸린» 수", n_hit)]))
            rows[key] = collections.OrderedDict([
                ("🔴 통과", green),
                ("🔴 대상 분모(자동)", n_den), ("🔴 분모 키", list(dens.keys())[:4]),
                ("🔴🔴🔴 걸린 자리(자동)", n_hit), ("🔴 걸린 자리 키", list(hits.keys())[:4]),
                ("🔴 «만든» 수(걸린 자리로 «쓰면 안 되는» 것)", made or None),
                ("🔴🔴 판정", verdict),
            ])
    return collections.OrderedDict([
        ("🔴 무엇",
         "🔴🔴🔴 `조항 59-나` 를 개정한다 --- 「걸린 자리」 = **자가 «비교»를 «수행»한 회수**. "
         "🔴 **바늘 «생성» 수·후보 «자리» 수를 넣으면 «반증»**(`F07`). "
         "🔴 **명부를 손으로 안 고르고 `통과` 키를 내는 절 «전량»에 문다**"),
        ("🔴 988 의 명부가 한 주행 안에서 갈렸다", [4, 5]),
        ("🔴🔴🔴 `통과` 키를 내는 절 수(자동 · 손으로 안 골랐다)", len(rows)),
        ("🔴 그중 `통과 True` 인 절 수", greens),
        ("🔴 절별", rows),
        ("🔴🔴🔴 `통과 True` 인데 걸린 자리가 0 인 절", unmeasured or "없음"),
        ("🔴🔴🔴 그 수(= 988 이 「미측정 0」이라 적은 자리)", len(unmeasured)),
        ("🔴🔴 988 이 적은 「미측정」 수", 0),
        ("🔴 «만든» 수와 «걸린» 수가 다른 절", mislabeled or "없음"),
        ("🔴🔴🔴 정정이 필요한가", bool(len(unmeasured) > 0)),
        ("🔴🔴🔴 `R1` 의 날 — 「걸린 자리 수」 칸 전량 재분류", hits_reclass(objs)),
        ("통과", bool(len(rows) > 0)),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 자가 «비교를 수행한 회수»를 절 전량에서 «실제로 세었다»(빈 명부가 아니다)"),
    ])

HITN = re.compile(r"걸린\s*자리\s*수")
# 🔴 «만든» 수 --- 바늘을 만들었을 뿐 어느 자리에도 «안 걸릴» 수 있다. 걸린 자리로 «못» 쓴다
MADEN = re.compile(r"(등록\s*)?바늘\s*수|만든|생성")
# 🔴 «훑은» 자리 수 --- 자리«마다» 비교가 «실제로 수행»된다. 걸린 자리로 쓸 수 «있으나»
#    이름을 「검사한 자리」로 시정해야 한다(🔴 티처 #127: F14·F15 는 «진짜로» 검사됐다)
CANDN = re.compile(r"후보\s*자리\s*수")


def _nodes_with(obj, rex, path=()):
    if isinstance(obj, dict):
        if any(rex.search(str(k)) for k in obj):
            yield path, obj
        for k, v in obj.items():
            for x in _nodes_with(v, rex, path + (str(k),)):
                yield x
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            for x in _nodes_with(v, rex, path + ("[%d]" % i,)):
                yield x


def hits_reclass(objs):
    """🔴🔴🔴 **`R1` 의 «날»** --- 988 이 「걸린 자리 수」라 부른 칸을 «전량» 훑어
    **그 수가 사실은 「만든 수」인 자리**와 **0 인 자리**를 갈라 낸다.

    🔴 **명부를 손으로 안 고른다.** `걸린 자리 수` 라는 «칸 이름»으로만 찾는다.
    """
    rows, zero, made_as_hit, relabel = collections.OrderedDict(), [], [], []
    for name, obj in objs.items():
        for path, node in _nodes_with(obj, HITN, (name,)):
            hk = [k for k in node if HITN.search(str(k))]
            if not hk:
                continue
            n_hit = node.get(hk[0])
            if isinstance(n_hit, bool) or not isinstance(n_hit, int):
                continue
            key = " | ".join(path + (str(node.get("🔴 이름") or ""),)).strip(" |")
            made = collections.OrderedDict(
                (str(k), v) for k, v in node.items()
                if not isinstance(v, bool) and isinstance(v, int)
                and MADEN.search(str(k)))
            cand = collections.OrderedDict(
                (str(k), v) for k, v in node.items()
                if not isinstance(v, bool) and isinstance(v, int)
                and CANDN.search(str(k)))
            # 🔴 그 절 «바깥»(형제 칸)에서도 「만든 수」를 찾는다
            outer = collections.OrderedDict()
            for name2, obj2 in objs.items():
                for p2, n2 in _nodes_with(obj2, MADEN, (name2,)):
                    if p2 == path[:len(p2)] and len(p2) >= len(path) - 1:
                        for k, v in n2.items():
                            if not isinstance(v, bool) and isinstance(v, int) \
                                    and MADEN.search(str(k)):
                                outer[str(k)] = v
            same = sorted({k for k, v in list(made.items()) + list(outer.items())
                           if v == n_hit})
            same_cand = sorted({k for k, v in cand.items() if v == n_hit})
            row = collections.OrderedDict([
                ("🔴 988 이 「걸린 자리 수」라 적은 값", n_hit),
                ("🔴 같은 절의 «만든» 수", made or None),
                ("🔴 같은 절의 «훑은 자리» 수", cand or None),
                ("🔴 바깥의 «만든» 수", outer or None),
                ("🔴 어긋난 수", node.get("🔴 어긋난 수")),
                ("🔴 988 의 갈래", node.get("🔴🔴🔴 갈래(조항 59-나)")),
            ])
            if n_hit == 0:
                row["🔴🔴🔴 989 재분류"] = "🔴🔴🔴 미측정 --- 걸린 자리 0"
                zero.append(key)
            elif same:
                row["🔴🔴🔴 989 재분류"] = (
                    "🔴🔴🔴 미측정 --- 이 수는 「걸린 자리」가 «아니라» «만든 수»다(%s). "
                    "`F07` 이 금지하는 바로 그것이다" % ", ".join(same))
                made_as_hit.append(key)
            elif same_cand:
                row["🔴🔴🔴 989 재분류"] = (
                    "🟢 잰 것이 있다 --- 이 수는 «훑은 자리» 수(%s)이고 «자리마다 비교가 "
                    "실제로 수행»됐다. 🔴 **「걸린 자리」가 아니라 「검사한 자리」로 «이름만» "
                    "시정한다** --- 🔴 티처 #127 이 인정한 자리다(F14·F15 는 진짜로 검사됐다)"
                    % ", ".join(same_cand))
                relabel.append(key)
            else:
                row["🔴🔴🔴 989 재분류"] = "잰 것이 있다"
            rows[key] = row
    n_un = len(zero) + len(made_as_hit)
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴🔴 988 의 「걸린 자리 수」 칸을 «전량» 훑어 재분류한다(`R1` · `F07`)"),
        ("🔴 훑은 칸 수", len(rows)), ("🔴 칸별", rows),
        ("🔴🔴🔴 걸린 자리가 «0» 이라 미측정", zero or "없음"),
        ("🔴🔴🔴 «만든 수»를 걸린 자리로 실어 미측정", made_as_hit or "없음"),
        ("🟢 «훑은 자리» 수라 «이름만» 시정하면 되는 칸(미측정이 «아니다»)",
         relabel or "없음"),
        ("🔴🔴 티처 #127 이 인정한 것",
         "🔴 **「`0` 은 언제나 안 봤다」는 «과했다».** `F14`·`F15` 는 **자리마다 비교가 "
         "«실제로 수행»됐고 어긋남 0** 이다. **988 의 「갈라 세라」가 옳았다.**"),
        ("🔴🔴🔴 989 가 다시 센 「미측정」 수", n_un),
        ("🔴🔴 988 이 적은 「미측정」 수", 0),
        ("🔴🔴🔴 정정이 필요한가", bool(n_un > 0)),
    ])




# ══════════════════════════════════════════════════════════════════════
# §E 🔴 `R4` --- 단조 불변 자를 고친다
# ══════════════════════════════════════════════════════════════════════
def monotone_fixed():
    """🔴🔴🔴 **등록 기준을 «그대로» 평가하고 음성 대조를 갈아 끼운다.**

    🔴 **988 의 병 둘**
      ① 등록 기준은 **「비단조면 발화 0」** 인데 구현이 `n_fire == n_ok` 였다
         --- **100% 가 아니면 «통과»** 라 실측 `41/400` 이 «안 떨어졌다»(`조항 72` 위반).
      ② 음성 대조 `㉱` 가 **구성상 «단조 감소»**(`h = max(ctl) − ctl` · `㉱ = ctl + Δ`)라
         **참 귀무가 아니다.**
    🔴 **989 판** --- 음성 대조를 **무작위 치환**과 **U자**로 바꾸고,
       **`V0`/`V1′` 중복 입력을 지우고**, **둘째 연언 계열 `(㉰−㉱, h)`** 도 문다.
    """
    import power985 as P5                                        # noqa: E402
    import mix980 as MX                                          # noqa: E402
    NB_GRID = list(MX.NB_GRID)
    gr = json.loads((ROOT / "runners/out983_grid.json").read_text(encoding="utf-8"))
    rp = json.loads((ROOT / "runners/out983_reps.json").read_text(encoding="utf-8"))
    _pts, reps = P5.arms_points(gr), P5.arms_reps(rp)
    A_CTL, A_PRE, A_PLA = P5.A_CTL, P5.A_PRE, P5.A_PLA
    rng = np.random.RandomState(989)

    pairs = collections.OrderedDict([
        ("V0 / V1′ 첫째 항 `(㉮−㉱, h)`", []),      # 🔴 988 은 이 계열을 «둘»에 중복 입력했다
        ("🔴 신설 V0 둘째 연언 계열 `(㉰−㉱, h)`", []),
        ("V1 `(㉮−㉰, h)`", []),
        ("V2 `(㉮₂−㉱, h)`", []),
    ])
    ctrl = collections.OrderedDict([
        ("🔴 음성 대조 ㉠ — 무작위 «치환»(참 귀무)", []),
        ("🔴 음성 대조 ㉡ — U자(비단조 · 참 귀무)", []),
        ("🔴 988 이 쓴 음성 대조 `㉱ 대 h`(🔴 구성상 «단조 감소»)", []),
        ("🔴 양성 대조 — 심은 단조 짝 `3h+1 대 h`", []),
    ])
    n_used, mono_ctl = 0, []
    for uk in ("u=0", "u=3"):
        R = reps[uk]
        for r in range(len(R[A_CTL][0])):
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
            Xc = np.column_stack([np.ones(len(h)), np.asarray(NB_GRID, float),
                                  np.asarray(h, float)])
            beta, *_ = np.linalg.lstsq(Xc, v0, rcond=None)
            res = v0 - Xc.dot(beta)
            Lo = res / (float(np.std(res)) or 1.0)
            s_pl = A8._spear(pla, h)
            if s_pl is not None:
                mono_ctl.append(s_pl)
            for d in (0.05, 2.00):
                ora = [pre[i] + d * Lh[i] for i in range(len(NB_GRID))]
                ora2 = [pre[i] + d * Lo[i] for i in range(len(NB_GRID))]
                pairs["V0 / V1′ 첫째 항 `(㉮−㉱, h)`"].append(
                    ([ora[i] - pla[i] for i in range(len(NB_GRID))], h))
                pairs["🔴 신설 V0 둘째 연언 계열 `(㉰−㉱, h)`"].append(
                    ([pre[i] - pla[i] for i in range(len(NB_GRID))], h))
                pairs["V1 `(㉮−㉰, h)`"].append(
                    ([ora[i] - pre[i] for i in range(len(NB_GRID))], h))
                pairs["V2 `(㉮₂−㉱, h)`"].append(
                    ([ora2[i] - pla[i] for i in range(len(NB_GRID))], h))
            perm = list(np.asarray(h)[rng.permutation(len(h))])
            uu = [(x - mu) ** 2 for x in h]
            ctrl["🔴 음성 대조 ㉠ — 무작위 «치환»(참 귀무)"].append((perm, h))
            ctrl["🔴 음성 대조 ㉡ — U자(비단조 · 참 귀무)"].append((uu, h))
            ctrl["🔴 988 이 쓴 음성 대조 `㉱ 대 h`(🔴 구성상 «단조 감소»)"].append((list(pla), h))
            ctrl["🔴 양성 대조 — 심은 단조 짝 `3h+1 대 h`"].append(
                ([3.0 * x + 1.0 for x in h], h))

    def rule(ps, criterion):
        """🔴 `criterion` = 'registered'(등록 문안 그대로 · 발화 = n_fire >= 1)
           또는 '988'(구현 · 발화 = n_fire == n_ok)."""
        rows, fired = collections.OrderedDict(), []
        for name, series in ps.items():
            vals, n_ok, n_fire = [], 0, 0
            for a, b in series:
                s = A8._spear(a, b)
                if s is None:
                    continue
                n_ok += 1
                vals.append(round(s, 12))
                if abs(s) >= 1.0 - MONO_TOL:
                    n_fire += 1
            fire = (n_fire >= 1) if criterion == "registered" else \
                   (n_ok > 0 and n_fire == n_ok)
            rows[name] = collections.OrderedDict([
                ("🔴 짝 수(분모)", n_ok), ("🔴 `|스피어만| = 1` 인 짝", n_fire),
                ("🔴 비율", _r(float(n_fire) / n_ok) if n_ok else None),
                ("🔴 스피어만 최소 / 최대",
                 [min(vals), max(vals)] if vals else None),
                ("🔴🔴🔴 발화", bool(fire)),
                ("🔴 걸린 자리(= 비교를 «수행»한 회수)", n_ok),
            ])
            if fire:
                fired.append(name)
        return rows, fired

    rows_r, fired_r = rule(pairs, "registered")
    rows_8, fired_8 = rule(pairs, "988")
    ctl_r, ctl_fired_r = rule(ctrl, "registered")
    ctl_8, ctl_fired_8 = rule(ctrl, "988")

    neg = ["🔴 음성 대조 ㉠ — 무작위 «치환»(참 귀무)",
           "🔴 음성 대조 ㉡ — U자(비단조 · 참 귀무)"]
    old_neg = "🔴 988 이 쓴 음성 대조 `㉱ 대 h`(🔴 구성상 «단조 감소»)"
    pos = "🔴 양성 대조 — 심은 단조 짝 `3h+1 대 h`"
    # 🔴 등록 문안 그대로: 「비단조 짝을 넣으면 «발화가 0»」
    demo_ok = bool(all(ctl_r[k]["🔴 `|스피어만| = 1` 인 짝"] == 0 for k in neg)
                   and ctl_r[pos]["🔴🔴🔴 발화"])
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴🔴 `R4` --- **단조 불변 자의 등록 기준을 «러너가 그대로» 평가하고 "
                  "음성 대조를 «참 귀무»로 갈아 끼운다**"),
        ("🔴🔴🔴 988 의 병 ①(조항 72 위반)",
         "🔴 등록 문안 = 「비단조 짝을 넣으면 «발화 0»」 · 구현 = `n_fire == n_ok` "
         "(**100%% 가 아니면 통과**) --- 실측 발화 `%d / %d`"
         % (ctl_8[old_neg]["🔴 `|스피어만| = 1` 인 짝"], ctl_8[old_neg]["🔴 짝 수(분모)"])),
        ("🔴🔴🔴 988 의 병 ②(음성 대조가 참 귀무가 아니다)",
         "🔴 `h = max(ctl) − ctl` · `㉱ = ctl + Δ` 라 «구성상 단조 감소» --- "
         "평균 스피어만 %s" % _r(float(np.mean(mono_ctl)) if mono_ctl else None)),
        ("🔴 988 음성 대조의 평균 스피어만", _r(float(np.mean(mono_ctl)) if mono_ctl else None)),
        ("🔴 쓸 수 있는 복제 수", n_used),
        ("🔴🔴 대조별 — 등록 문안 그대로", ctl_r),
        ("🔴 대조별 — 988 구현", ctl_8),
        ("🔴🔴🔴 참 귀무 대비 988 음성 대조의 발화 배수",
         (None if any(ctl_r[k]["🔴 `|스피어만| = 1` 인 짝"] for k in neg)
          else ("🔴 참 귀무 둘 다 «0 발화» · 988 대조는 %d 발화 --- 나눌 수 없다(분모 0)"
                % ctl_8[old_neg]["🔴 `|스피어만| = 1` 인 짝"]))),
        ("🔴🔴 계열별 — 등록 문안 그대로", rows_r),
        ("🔴 계열별 — 988 구현", rows_8),
        ("🔴🔴🔴 등록 문안으로 발화한 계열", sorted(fired_r)),
        ("🔴 988 구현으로 발화한 계열", sorted(fired_8)),
        ("🔴🔴🔴 검정력 시연(조항 64) — 등록 문안 그대로 갈리나", demo_ok),
        ("🔴 V0 / V1′ 중복 입력을 지웠나", True),
        ("🔴 둘째 연언 계열을 물렸나", True),
        ("통과", bool(demo_ok)),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 «참 귀무»(무작위 치환 · U자)에서 발화가 0 이고 심은 단조 짝에서 발화한다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §F 🔴 「964·965 에 이미 자가 있었다」는 «거짓»이다
# ══════════════════════════════════════════════════════════════════════
def prior_ruler_claim():
    out = collections.OrderedDict()
    for rel in ("runners/checks964.py", "runners/meta965.py"):
        p = ROOT / rel
        if not p.is_file():
            out[rel] = {"🔴": "🔴 파일이 없다"}
            continue
        src = p.read_text(encoding="utf-8")
        lines = src.split("\n")
        hits = [i + 1 for i, ln in enumerate(lines)
                if re.search(r"스피어만|spearman|단조", ln)]
        namecite = [i for i in hits
                    if re.search(r"964|965|\.py|docs/", lines[i - 1])]
        out[rel] = collections.OrderedDict([
            ("줄 수", len(lines)),
            ("🔴 「스피어만 / 단조」 히트 줄", hits),
            ("🔴 그중 «파일명 인용»뿐인 줄", namecite),
            ("🔴🔴 «두 수치 계열»을 인자로 받는 자가 있나", bool(len(hits) > len(namecite))),
        ])
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴 988 이 «셋»(사전등록·산출물·판정문)에 실은 "
                  "「964·965 에 이미 자가 있었다」를 잰다"),
        ("🔴 파일별", out),
        ("🔴🔴🔴 그 주장이 참인가",
         bool(any(v.get("🔴🔴 «두 수치 계열»을 인자로 받는 자가 있나") for v in out.values()))),
        ("🔴🔴🔴 정정 문안",
         "🔴 **거짓이다.** `checks964.py` 의 히트는 «파일명 인용»뿐이고 `meta965` 의 자 셋은 "
         "**전부 AST / 소스 «정적» 자**라 「두 «수치 계열»이 서로의 단조 변환인가」를 "
         "**원리상 못 본다.** 🔴 **988 이 «세 번째, 종류가 다른» 자를 새로 만든 것이다.**"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §G 🔴🔴🔴 §1-5 — 이 사이클이 «세계»를 만졌나
# ══════════════════════════════════════════════════════════════════════
def world_touch(world_obj, verdict_txt):
    # ── ㉠ 정적 --- 989 러너의 `data/` 문자열 리터럴 ──────────────
    static = collections.OrderedDict()
    for rel in RAN_989:
        p = ROOT / rel
        if not p.is_file():
            continue
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        got = sorted({n.value for n in ast.walk(tree)
                      if isinstance(n, ast.Constant) and isinstance(n.value, str)
                      and n.value.startswith("data/")})
        if got:
            static[rel] = got
    static_paths = sorted({x for v in static.values() for x in v})
    # ── ㉠ 런타임 --- `world989` 이 «연» 경로 ──────────────────────
    runtime = A8._dig(world_obj or {}, "🔴🔴🔴 §1-5 ㉠ 이 러너가 «연» `data/` 경로",
                      "경로별 연 횟수") or {}
    # ── ㉡ 판정문의 «세계 자료를 인용한» 주장 문장 ─────────────────
    anchors = sorted(set(list(runtime.keys()) + static_paths))
    nums = []
    for k in ("🔴 Δ(1800)", "🔴 Δ(천장)", "🔴 Δ(천장) / SE_짝", "🔴 교차 예산 N*",
              "🔴🔴 도메인 «균등» Δ(천장)"):
        v = A8._dig(world_obj or {}, "§3 🔴🔴🔴 판정", k)
        if v is not None:
            nums.append(str(v))
    sents, cited = [], []
    if verdict_txt:
        for s in re.split(r"(?<=[.다])\s*\n|\n\n", verdict_txt):
            s = s.strip()
            if not s or s.startswith("#"):
                continue
            sents.append(s)
            if any(a in s for a in anchors) or any(n in s for n in nums):
                cited.append(s)
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴🔴 **「이 명제가 세계에 대한 것인가」를 스스로 검사하는 자**(사전등록 §1-5)"),
        ("🔴 ㉠ 정적 — 989 러너의 `data/` 리터럴", static),
        ("🔴 ㉠ 정적 경로 수", len(static_paths)),
        ("🔴🔴🔴 ㉠ 런타임 — `world989` 이 «실제로 연» `data/` 경로", runtime),
        ("🔴🔴🔴 ㉠ 런타임 경로 수", len(runtime)),
        ("🔴 정적과 런타임이 같은가", bool(set(static_paths) == set(runtime.keys()))),
        ("🔴 다르면 그 차이",
         collections.OrderedDict([
             ("정적에만", sorted(set(static_paths) - set(runtime.keys())) or "없음"),
             ("런타임에만", sorted(set(runtime.keys()) - set(static_paths)) or "없음")])),
        ("🔴 세계 자료에서 온 수(판정문에서 찾을 닻)", nums),
        ("🔴 판정문 문장 수", len(sents)),
        ("🔴🔴🔴 ㉡ 세계 자료를 인용한 주장 문장 수", len(cited)),
        ("🔴 그 문장들(앞 12)", cited[:12]),
        ("🔴🔴🔴 F04 — 연 `data/` 경로가 0 인가(참이면 반증)", bool(len(runtime) == 0)),
        ("🔴🔴🔴 F05 — 세계 자료를 인용한 주장이 0 인가(참이면 반증)", bool(len(cited) == 0)),
    ])


# ══════════════════════════════════════════════════════════════════════
def stage_all(ref):
    t0 = _now()
    cs0 = code_stamp()
    pre987 = _show(ref, PREREG_987) or (ROOT / PREREG_987).read_text(encoding="utf-8")
    pre988 = _show(ref, PREREG_988) or (ROOT / PREREG_988).read_text(encoding="utf-8")
    src987 = _show(ref, "runners/score987.py")
    au988 = json.loads((ROOT / "runners/out988_audit.json").read_text(encoding="utf-8"))
    sc988 = json.loads((ROOT / "runners/out988_score.json").read_text(encoding="utf-8"))
    wjs = ROOT / "runners/out989_world.json"
    world = json.loads(wjs.read_text(encoding="utf-8")) if wjs.is_file() else {}
    vp = ROOT / "docs/판정_989.md"
    verdict = vp.read_text(encoding="utf-8") if vp.is_file() else None

    import score988 as S8                                        # noqa: E402
    mono = monotone_fixed()
    id987 = path_identity_ast("987", pre987, src987)
    id988 = path_identity_table("988", pre988, S8)

    # 🔴 검정력 시연(조항 64) --- 신판이 987 의 `P6` 을 «여전히» 잡아야 한다
    demo = bool("P6" in (id987["🔴🔴🔴 판정식 교체"] or []))
    old987 = A8._dig(au988, "§B 🔴🔴🔴 여덟째 칸 — 등록 판정식 대조",
                     "🔴🔴 987 에서 어긋난 예측") or []

    res = collections.OrderedDict([
        ("무엇", "989 감사 — 🔴🔴🔴 **경로 동일성 여덟째 칸** · 「걸린 자리」 정의 · 단조 자 수리"),
        ("🔴 축", "자기 자(곁). 🔴 **세계 명제는 `out989_world.json` 이 낸다**"),
        ("사전등록", "docs/prereg_989_world_budget.md §2 · §3"),
        ("🔴 고정 ref", ref),
        ("§A 🔴🔴🔴 경로 동일성 — 987 (검정력 시연 · 조항 64)", id987),
        ("§A-나 🔴🔴 구판(퍼지) 대 신판(경로 동일성)", collections.OrderedDict([
            ("🔴 구판이 「어긋났다」고 센 것", old987),
            ("🔴 구판이 센 수", len(old987)),
            ("🔴🔴🔴 신판이 「판정식 교체」로 센 것", id987["🔴🔴🔴 판정식 교체"]),
            ("🔴🔴🔴 신판이 센 수", id987["🔴🔴🔴 판정식 교체 수"]),
            ("🔴🔴 신판이 「라벨 개명」으로 갈라낸 것", id987["🔴🔴 라벨 개명(반증 아님)"]),
            ("🔴🔴🔴 허위 양성이었던 것",
             sorted(set(old987) - set(id987["🔴🔴🔴 판정식 교체"] if isinstance(
                 id987["🔴🔴🔴 판정식 교체"], list) else [])) or "없음"),
            ("🔴🔴🔴 검정력 시연 — 신판이 `P6` 을 여전히 잡나", demo),
            ("🔴 왜 구판이 틀렸나",
             "🔴 등록 «주어»(산문)를 «평가 집합»(키 경로)과 «직접» 퍼지 대조했다 --- "
             "**이름 공간이 다르다.** `score987.py:800-801` 은 등록 주어(`잡은 수`)를 "
             "**그대로 싣고** `n4 >= 1` 을 **그대로 평가한다** --- 주어·연산자·우변이 전부 같다"),
        ])),
        ("§B 🔴🔴🔴 경로 동일성 여덟째 칸", id988),
        ("§E 🔴🔴🔴 `R4` — 단조 불변 자 수리", mono),
        ("§C 🔴🔴 988 의 예측을 다시 채점한다", rescore_988(id987, sc988, mono)),
        ("§D 🔴🔴🔴 `R1` — 「걸린 자리」의 정의", hits_audit(collections.OrderedDict([
            ("out988_audit", au988), ("out988_score", sc988)]))),
        ("§F 🔴🔴 「964·965 에 이미 자가 있었다」 검사", prior_ruler_claim()),
        ("§G 🔴🔴🔴 §1-5 — 이 사이클이 «세계»를 만졌나", world_touch(world, verdict)),
    ])
    secs = [k for k in res if k.startswith("§")]
    ok = collections.OrderedDict()
    for k in secs:
        v = res[k]
        ok[k] = bool(v.get("통과")) if isinstance(v, dict) and "통과" in v else None
    res["🔴 절별 통과"] = ok
    res["통과"] = bool(demo and res["§E 🔴🔴🔴 `R4` — 단조 불변 자 수리"]["통과"]
                     and not res["§G 🔴🔴🔴 §1-5 — 이 사이클이 «세계»를 만졌나"][
                         "🔴🔴🔴 F04 — 연 `data/` 경로가 0 인가(참이면 반증)"])
    res["🔴 도장"] = collections.OrderedDict([
        ("ref", ref), ("🔴 코드 sha256(시작)", cs0),
        ("🔴 코드 sha256(끝)", code_stamp()),
        ("🔴 코드가 주행 중 바뀌었나", cs0 != code_stamp()),
        ("시작(UTC)", t0), ("끝(UTC)", _now())])
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all")
    ap.add_argument("--ref", required=True)
    a = ap.parse_args()
    if len(a.ref) != 40:
        raise SystemExit("🔴 --ref 는 40자 sha 여야 한다")
    res = stage_all(a.ref)
    (OUT / "out989_audit.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
