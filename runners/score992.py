#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""992 채점기 — 🔴🔴🔴 **자가 «잡은» 것을 «전부» 최상위 연언에 문다.**

사전등록 `docs/prereg_992_wire_the_rulers.md` §3(예측) · §4(반증조건 14) · §7-가(등록 분모).

🔴 **991 이 어긴 것 넷을 구조로 막는다.**
  ① 🔴🔴🔴 **`§1 등록 분모` 를 «사전등록에서 기계로 긁는다»** --- 991 은 손 딕트였고
     사전등록이 「분모」로 이름 붙인 `V1`~`V12` 를 «어느 산출물에도» 안 채점했다.
  ② 🔴🔴🔴 **자가 잡은 red 를 최상위 연언에 «문다»** ---
     `out992_table.json` 의 「못 읽은 슬롯 0」 · 규칙 D 의 「키 경로와 본문이 다른 슬롯 0」 ·
     `out992_mut.json` · `out992_paper.json` 이 «전부» 든다.
  ③ 🔴🔴🔴 **`F11` 을 «실제로» 구현한다** --- 그리고 **「통과로 셀 수 없나 == false」인 조건은
     분자·분모에서 «둘 다» 빼고 `n/m` 을 갈라 게재한다**(991 은 「못 셈」이라 신고해 놓고
     분자 12 에 넣었다).
  ④ 🔴🔴 **`F14` 를 「부동소수 리터럴 «전수»」로 넓힌다** --- 991 은 `T[...] = <수>` 꼴만 봐서
     `world991.py:445` 의 `want = 0.3596`(주석이 「손으로 옮겼다」고 자백)을 원리상 못 봤다.

씀:
    python3 runners/score992.py --ref <40자 sha>
"""
import argparse
import ast
import collections
import datetime as dt
import glob
import hashlib
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

import ledger as LG                                # noqa: E402

OUT = ROOT / "runners"
DOCS = ROOT / "docs"
PREREG = "docs/prereg_992_wire_the_rulers.md"

GLOB_RUNNERS = "runners/*992*.py"
GLOB_OUTPUTS = "runners/*992*"
GLOB_TPL = "docs/tpl/*992*.tpl"

DOCS_992 = ("docs/판정_992.md", "docs/card_992.md", "docs/handoff_992.md",
            "docs/pr_992.md", PREREG)
CARD_OUTSIDE = Path(os.path.expanduser(
    "~/.claude/projects/-Users-ax-world-model/memory/project-lab-state.md"))
LEDGER = "data/lab/denominator.json"

ORD = "§1 🔴🔴🔴 순서 분해 — 자 셋 × 두 순서 × 대칭 배분(λ 전량)"
ROW = "🔴🔴🔴 한 줄 표"
CMP = "🔴 성분"
SEB = "§1-나 🔴🔴🔴 SE 표 — 자 3 × 성분 8 = 24 칸 전량"
EXP = "§2 🔴🔴🔴 탐색 격자"
JUD = "§5 🔴🔴🔴 판정"

#: 🔴🔴🔴 **`V1`~`V12` --- 사전등록 §0-나 가 「분모」로 등기한 재현 항목 열둘.**
#:   991 은 이 이름을 사전등록에 박아 놓고 «어느 산출물에도» 안 채점했다(티처 #130 치-7).
#:   🔴 두 값을 «둘 다 산출물에서» 읽는다. 손 전사 `0`.
VITEMS = collections.OrderedDict([
    ("V1", [ORD, "0", "R_pool 묶음", ROW, "Δ(1800)"]),
    ("V2", [ORD, "0", "R_pool 묶음", ROW, "순서 A 증강"]),
    ("V3", [ORD, "0", "R_pool 묶음", ROW, "순서 A 굶김"]),
    ("V4", [ORD, "0", "R_pool 묶음", ROW, "순서 B 증강"]),
    ("V5", [ORD, "0", "R_pool 묶음", ROW, "순서 B 굶김"]),
    ("V6", [ORD, "0", "R_pool 묶음", ROW, "상호작용"]),
    ("V7", [ORD, "0", "R_pool 묶음", ROW, "대칭 증강"]),
    ("V8", [ORD, "0", "R_pool 묶음", ROW, "대칭 굶김"]),
    ("V9", [ORD, "0", "R_eq 균등", ROW, "순서 A 굶김"]),
    ("V10", [ORD, "0", "R_champ 챔피언가중", ROW, "순서 A 굶김"]),
    ("V11", [ORD, "0", "R_pool 묶음", CMP, "Δ = H − B", "🔴🔴🔴 t_clu"]),
    ("V12", [ORD, "0", "R_champ 챔피언가중", CMP, "상호작용 A′ − A", "🔴🔴🔴 t_clu"]),
])
VTOL = 1e-9

FALSIFY = collections.OrderedDict([
    ("F01", "사전등록 blob 을 측정 뒤에 고쳤다"),
    ("F02", "막힌 명령을 우회하고 신고를 안 했다 · 또는 `HEAD` 가 움직였다"),
    ("F03", "등록 분모와 다른 수로 채점했다 · 등기한 목록(`V1`~`V12` 포함)을 «안» 채점했다"),
    ("F04", "이 사이클의 러너가 «연» `data/` 경로가 0 이다"),
    ("F05", "판정문의 주장 문장 중 «세계 자료를 인용한» 것이 0 이다"),
    ("F06", "등록 기준을 러너가 «다른 식»으로 평가했다 · 자에 따라 «부호 또는 2·SE 판정»이 "
            "갈렸는데 판정문 맨 위에 안 실었다"),
    ("F07", "「걸린 자리」에 «바늘·후보 생성 수»를 넣었다"),
    ("F08", "「걸린 자리 0」을 「통과」로 셌다 · 미측정이 하나라도 있다"),
    ("F09", "값을 낸 뒤 러너를 고치고 안 다시 돌렸다 · 🔴 **소비자 도장이 생산자보다 앞선다**"),
    ("F10", "문서 고리가 수렴 안 했다"),
    ("F11", "여섯 자리가 «다른 수»를 적는다"),
    ("F12", "규칙 D — 치환표 밖의 수가 있다 · 🔴 **키 경로와 본문이 다른 슬롯이 있다**"),
    ("F13", "이 사이클 산출물 중 문서에 «한 번도» 인용 안 된 것이 있다"),
    ("F14", "이 사이클 러너에 리터럴 `(\"통과\", True)` 또는 «손 전사 부동소수 리터럴»이 있다"),
])

PRED_DEF = collections.OrderedDict([
    ("P1", (["out992_order.json", EXP, "R_pool 묶음",
             "🔴🔴🔴 argmax 가 격자 오른쪽 끝인가"], "==", False)),
    ("P2", (["out992_order.json", EXP, "R_pool 묶음",
             "🔴🔴🔴 최적 집합의 크기가 1 을 넘나"], "==", True)),
    ("P3", (["out992_wiring.json", "§B 🔴🔴🔴 991 의 여섯을 실측한다",
             "🔴🔴🔴 구성상 거짓 수"], ">=", 2)),
    ("P4", (["out992_audit.json", "§B 🔴🔴 990 의 배선 일곱 — 진짜 AST",
             "🔴🔴🔴 그 수"], "==", 6)),
    ("P5", (["out992_score.json", "§5 🔴 반증조건", "F11", "근거",
             "🔴🔴🔴 어긋난 슬롯 수"], "==", 0)),
])


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p):
    return os.path.relpath(str(p), str(ROOT))


def _glob(pat):
    return sorted(_rel(p) for p in glob.glob(str(ROOT / pat)))


def _read(rel):
    p = ROOT / rel
    return p.read_text(encoding="utf-8") if p.is_file() else None


def _load(rel):
    p = ROOT / rel
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def _git(args):
    r = subprocess.run(["git"] + args, cwd=str(ROOT), capture_output=True)
    return r.returncode, r.stdout.decode("utf-8", "replace"), \
        r.stderr.decode("utf-8", "replace")


def RAN_992():
    return sorted(set(_glob(GLOB_RUNNERS) + _glob(GLOB_TPL)))


# ══════════════════════════════════════════════════════════════════════
# 🔴🔴🔴 §1 등록 분모 --- **사전등록에서 «기계로» 긁는다**
# ══════════════════════════════════════════════════════════════════════
_DENOM_RX = re.compile(r"`분모:\s*([^`]+)`\s*\|\s*(\d+)")


def scrape_denom():
    """🔴 `docs/prereg_992_*.md` §7-가 표의 «`분모: 이름` | 값» 줄을 전수 긁는다."""
    src = _read(PREREG) or ""
    out = collections.OrderedDict()
    for m in _DENOM_RX.finditer(src):
        out[m.group(1).strip()] = int(m.group(2))
    return out


DENOM = scrape_denom()


# ══════════════════════════════════════════════════════════════════════
def j_F01(ref):
    rc, out, err = _git(["show", "%s:%s" % (ref, PREREG)])
    hits = 1
    if rc != 0:
        return None, {"🔴 못 읽었다": err[:200]}, hits
    a = hashlib.sha256(out.encode("utf-8")).hexdigest()
    b = hashlib.sha256((_read(PREREG) or "").encode("utf-8")).hexdigest()
    return bool(a != b), {"ref 의 blob sha256": a, "디스크 sha256": b,
                          "🔴 같나": bool(a == b)}, hits


def j_F02():
    hits = 0
    vt = _read("docs/판정_992.md") or ""
    hits += 1
    has_sec = bool(re.search(r"막힌 명령", vt))
    hits += 1
    said = bool(re.search(r"막힌 명령.{0,400}?(없었다|없다)", vt, re.S))
    A = _load("runners/out992_audit.json")
    C = A.get("§C 🔴🔴🔴 `F02` — 리플로그 「구간 전수」") or {}
    n_all = C.get("🔴 리플로그 전체 항목 수")
    n_rng = C.get("🔴🔴🔴 사전등록 «이후» 항목 수(= 구간 분모)")
    bad = C.get("🔴🔴🔴 그 수")
    sym = C.get("🔴 점 표본(990 판) — `git symbolic-ref -q HEAD`")
    hits += int(n_all or 0)
    unmeasured = bool(n_all is None or bad is None)
    moved = bool(unmeasured or bad or sym != "refs/heads/main")
    return bool(moved or not has_sec), collections.OrderedDict([
        ("🔴 판정문에 「막힌 명령」 신고 절이 있나", has_sec),
        ("🔴 「없었다」를 «명시»했나", said),
        ("🔴 리플로그 전체 항목 수", n_all),
        ("🔴🔴🔴 사전등록 «이후» 항목 수(= 구간 분모)", n_rng),
        ("🔴🔴🔴 위반 항목 수", bad),
        ("🔴 점 표본 --- `git symbolic-ref -q HEAD`", sym),
        ("🔴🔴🔴 `HEAD` 가 움직였나", moved),
    ]), hits


def _vcheck():
    """🔴🔴🔴 `V1`~`V12` --- 991 과 992 의 «같은 칸»을 값으로 견준다."""
    rows, hits, bad, unread = collections.OrderedDict(), 0, [], []
    for k, path in VITEMS.items():
        hits += 1
        a, ea = LG.resolve(["out991_order.json"] + path)
        b, eb = LG.resolve(["out992_order.json"] + path)
        ok = None
        if ea is None and eb is None and isinstance(a, (int, float)) \
                and isinstance(b, (int, float)):
            ok = bool(abs(float(a) - float(b)) <= VTOL)
        rows[k] = collections.OrderedDict([
            ("🔴 키 경로", " | ".join(path)),
            ("991 의 칸", a if ea is None else None),
            ("992 의 칸", b if eb is None else None),
            ("🔴 못 읽었나", ea or eb or "없음"),
            ("🔴🔴 재현했나(|차| <= 1e-9)", ok),
        ])
        if ok is None:
            unread.append(k)
        elif not ok:
            bad.append(k)
    return rows, hits, bad, unread


def j_F03():
    """🔴 등록 분모 + 🔴🔴🔴 **등기한 «모든» 목록을 전수 대조한다**."""
    W = _load("runners/out992_order.json")
    hits = 0
    rulers = ["R_pool 묶음", "R_eq 균등", "R_champ 챔피언가중"]
    comps = ["Δ = H − B", "순서 A · 증강 A = M − B", "순서 A · 굶김 S_A = H − M",
             "순서 B · 증강 A′ = H − S", "순서 B · 굶김 S_B = S − B",
             "상호작용 A′ − A", "대칭 배분 · 증강 (A + A′)/2",
             "대칭 배분 · 굶김 (S_A + S_B)/2"]
    block = W.get(ORD) or {}
    miss = []
    for u, per_rn in block.items():
        for rn in rulers:
            per = (per_rn.get(rn) or {}).get(CMP) or {}
            for nm in comps:
                hits += 1
                if nm not in per:
                    miss.append({"λ": u, "자": rn, "성분": nm})
    E = W.get(EXP) or {}
    judge_in_grid = bool(E.get("🔴🔴🔴 판정 칸(`base 1800` = `B`)이 이 격자에 있나"))
    hits += 1
    vrows, vhits, vbad, vunread = _vcheck()
    hits += vhits
    used = collections.OrderedDict([
        ("반증조건", len(FALSIFY)), ("예측", len(PRED_DEF)),
        ("자", len(rulers)), ("분해 순서", 2),
        ("세계 자료 원천", len((W.get("🔴🔴🔴 세계 자료(런타임 지문)") or {}))),
        ("세계 명제", 2),
        ("재현 항목", len(VITEMS)),
        ("탐색 격자 칸", int(E.get("🔴 격자 칸 수") or 0)),
    ])
    bad = [k for k, v in used.items() if DENOM.get(k) != v]
    hits += len(used)
    return bool(bad or miss or judge_in_grid or vbad or vunread or not DENOM), \
        collections.OrderedDict([
            ("🔴🔴🔴 등록 분모(사전등록 §7-가 에서 «기계로» 긁었다)", dict(DENOM)),
            ("🔴 긁은 분모 수", len(DENOM)),
            ("🔴 실제로 쓴 분모", dict(used)),
            ("🔴 어긋난 분모", bad or "없음"),
            ("🔴🔴🔴 자 × 성분 중 «안 기록한» 자리", miss or "없음"),
            ("🔴🔴🔴 판정 칸(`base 1800`)이 탐색 격자에 «있나»", judge_in_grid),
            ("🔴🔴🔴 `V1`~`V12` 재현 항목(991 ↔ 992 · 둘 다 산출물에서 읽었다)", vrows),
            ("🔴🔴🔴 재현 분모", len(VITEMS)),
            ("🔴🔴🔴 재현한 수", len(VITEMS) - len(vbad) - len(vunread)),
            ("🔴🔴🔴 «안» 재현된 항목", vbad or "없음"),
            ("🔴🔴🔴 못 읽은 항목", vunread or "없음"),
            ("🔴 왜 이 자가 생겼나",
             "🔴 **991 은 `V1`~`V12` 를 사전등록에 「분모」로 이름 붙여 놓고 «어느 산출물에도» "
             "안 채점했다**(티처 #130 치-7). 992 는 사전등록의 «모든» 등기 분모를 "
             "「기계로 긁어」 `§1` 에 넣고 여기서 «전수» 대조한다"),
        ]), hits


def j_F04():
    A = _load("runners/out992_audit.json")
    G = A.get("§E 🔴🔴🔴 `F05` — 「칸 인용」") or {}
    n = G.get("🔴🔴🔴 ㉠ 런타임 최대")
    return bool(not n), {"🔴 런타임 연 `data/` 경로 수": n,
                         "🔴 산출물별": G.get("🔴 ㉠ 산출물별")}, 1


def j_F05():
    A = _load("runners/out992_audit.json")
    G = A.get("§E 🔴🔴🔴 `F05` — 「칸 인용」") or {}
    N = G.get("🔴🔴🔴 ㉢ 판정문의 슬롯 수 `N`(= 치환표가 심은 수)")
    M = G.get("🔴🔴🔴 ㉢ 그중 «세계 자료 지문이 걸린 산출물 칸»에서 온 것 `M`")
    hits = int(N or 0) + 1
    unmeasured = bool(N is None or M is None)
    return bool(unmeasured or not M), collections.OrderedDict([
        ("🔴🔴🔴 판정문의 슬롯 수 `N`", N),
        ("🔴🔴🔴 그중 세계 자료 칸에서 온 것 `M`", M),
        ("🔴🔴🔴 몫 `M/N`", G.get("🔴🔴🔴 ㉢ 몫 `M/N`")),
        ("⚠ 990 판(파일명 grep) --- 나란히 싣는다",
         G.get("🔴🔴🔴 ㉡ 그중 세계 자료를 «인용한» 문장 수(옛 자 --- 파일명 grep)")),
        ("🔴 못 쟀나(대장이 없다)", unmeasured),
    ]), hits


_KEYPATH = re.compile(r"판정식:\s*(\S+?)#(.+?)\s*(==|<=|>=)\s*([^\s`]+)\s*`")


def j_F06():
    """🔴🔴🔴 **992 판** --- 「부호」만이 아니라 **「`2·SE` 판정이 갈리면」**도 문다."""
    src = _read(PREREG) or ""
    hits = 0
    reg = collections.OrderedDict()
    for line in src.split("\n"):
        for m in _KEYPATH.finditer(line.replace("\\|", "|")):
            f, path, op, val = m.groups()
            keys = [k.strip() for k in path.split("|") if k.strip()]
            reg.setdefault(f, []).append((tuple(keys), op, val.strip()))
    reg_paths = {(f + ".json", tuple(k)) for f, lst in reg.items() for k, _o, _v in lst}
    if not reg_paths:
        return True, {"🔴🔴🔴 사전등록에서 키 경로를 «하나도» 못 읽었다": True}, 1
    def_paths = {(p[0][0], tuple(p[0][1:])) for p in PRED_DEF.values()}
    hits += len(reg_paths) + len(def_paths)
    only_reg = sorted("%s#%s" % (f, " | ".join(k)) for f, k in reg_paths - def_paths)
    only_def = sorted("%s#%s" % (f, " | ".join(k)) for f, k in def_paths - reg_paths)
    # 🔴🔴🔴 «부호 또는 SE 판정»이 자에 따라 갈렸나
    W = _load("runners/out992_order.json")
    S = W.get(SEB) or {}
    split_se = S.get("🔴🔴🔴 자에 따라 «2·SE 판정»이 갈리는 성분")
    split_sg = S.get("🔴🔴🔴 자에 따라 «부호»가 갈리는 성분")
    split_se = split_se if isinstance(split_se, list) else []
    split_sg = split_sg if isinstance(split_sg, list) else []
    flipped = bool(split_se or split_sg)
    vt = _read("docs/판정_992.md") or ""
    head = "\n".join(vt.split("\n")[:16])
    hits += 2
    top_ok = (not flipped) or bool(
        ("자" in head) and (("갈린" in head) or ("산다" in head) or ("뒤집" in head)))
    return bool(only_reg or only_def or not top_ok), collections.OrderedDict([
        ("🔴 사전등록이 적은 키 경로 수", len(reg_paths)),
        ("🔴 `PRED_DEF` 의 키 경로 수", len(def_paths)),
        ("🔴 사전등록에만 있는 것", only_reg or "없음"),
        ("🔴 `PRED_DEF` 에만 있는 것", only_def or "없음"),
        ("🔴🔴🔴 자에 따라 «2·SE 판정»이 갈린 성분", split_se or "없음"),
        ("🔴🔴🔴 자에 따라 «부호»가 갈린 성분", split_sg or "없음"),
        ("🔴🔴🔴 갈렸나(992 판 --- 부호 «또는» SE 판정)", flipped),
        ("🔴🔴🔴 판정문 «맨 위 16 줄»에 그 한 줄이 있나", top_ok),
        ("🔴 991 판이 놓친 것",
         "🔴 **991 의 `F06` 은 「부호」만 봤다** --- 그래서 「상호작용은 «챔피언 자에서» 산다」를 "
         "원리상 못 잡았다(`t_clu` 2.2260)"),
    ]), hits


_HITKEY = re.compile(r"걸린 자리")


def _walk_sections(rel):
    try:
        d = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    except Exception:                                              # noqa: BLE001
        return []
    rows = []

    def walk(o, path):
        if isinstance(o, list):
            for i, v in enumerate(o):
                if isinstance(v, (dict, list)):
                    walk(v, path + ["[%d]" % i])
            return
        if not isinstance(o, dict):
            return
        if "통과" in o:
            hk = [k for k in o if _HITKEY.search(k)]
            hv = [o[k] for k in hk if isinstance(o[k], int)]
            rows.append({"산출물": rel, "절": " | ".join(path) or "(맨 위)",
                         "통과": o["통과"], "걸린 자리 칸": hk,
                         "걸린 자리": (min(hv) if hv else None)})
        for k, v in o.items():
            if isinstance(v, (dict, list)):
                walk(v, path + [k])
    walk(d, [])
    return rows


_HITLIT = re.compile(r"걸린 자리")


def j_F07():
    hits, bad, scanned = 0, [], 0
    for rel in RAN_992():
        if not rel.endswith(".py"):
            continue
        src = _read(rel) or ""
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for n in ast.walk(tree):
            if isinstance(n, ast.Tuple) and len(n.elts) == 2:
                k0 = n.elts[0]
                if isinstance(k0, ast.Constant) and isinstance(k0.value, str) \
                        and _HITLIT.search(k0.value):
                    scanned += 1
                    hits += 1
            if not isinstance(n, ast.Call):
                continue
            lit = [x for x in n.args
                   if isinstance(x, ast.Constant) and isinstance(x.value, bool)]
            hk = [k for k in n.keywords if k.arg == "hits"]
            if not hk:
                continue
            scanned += 1
            hits += 1
            hv = hk[0].value
            is_len = isinstance(hv, ast.Call) and isinstance(hv.func, ast.Name) \
                and hv.func.id == "len"
            if lit and is_len:
                bad.append({"파일": rel, "줄": n.lineno,
                            "꼴": "판정이 «리터럴»인데 `hits=len(...)` 를 실었다"})
            elif lit:
                bad.append({"파일": rel, "줄": n.lineno,
                            "꼴": "🔴 판정이 «리터럴 불리언»이다(하드코딩 판정)"})
    return bool(bad), collections.OrderedDict([
        ("🔴🔴🔴 판정 꼴", "🔴 **«출처»(AST) 로 잰다. «값»으로 안 잰다**(`조항 60-라`)"),
        ("🔴 훑은 자리 수", scanned),
        ("🔴🔴🔴 판정이 «리터럴»인데 걸린 자리를 실은 자리", bad or "없음"),
        ("🔴🔴🔴 그 수", len(bad)),
    ]), hits


def j_F08():
    hits, un, rows = 0, [], 0
    per = collections.OrderedDict()
    for rel in _glob(GLOB_OUTPUTS):
        if not rel.endswith(".json"):
            continue
        new_rows = _walk_sections(rel)
        mine = []
        for r in new_rows:
            rows += 1
            hits += 1
            if r["통과"] is True and (r["걸린 자리"] is None or r["걸린 자리"] == 0):
                mine.append({"산출물": r["산출물"], "절": r["절"],
                             "걸린 자리 칸": r["걸린 자리 칸"] or "없음"})
        un.extend(mine)
        per[rel] = {"절 수": len(new_rows), "🔴 미측정": len(mine)}
    return bool(un), collections.OrderedDict([
        ("🔴 명부의 출처", "글롭 `%s`" % GLOB_OUTPUTS),
        ("🔴 훑은 절 수", rows),
        ("🔴 산출물별", per),
        ("🔴🔴🔴 «미측정»(초록인데 걸린 자리가 0 이거나 칸이 없다)", un or "없음"),
        ("🔴🔴🔴 미측정 수", len(un)),
    ]), hits


def j_F09():
    """🔴🔴🔴 **992 판** --- 「맨 마지막 러너 하나」가 아니라 «도장 위상 정렬 전수»다."""
    L = _load("runners/out992_last.json")
    v = L.get("🔴🔴🔴 F09 반증됐나")
    return (None if v is None else bool(v)), collections.OrderedDict([
        ("🔴 출처", "runners/out992_last.json"),
        ("🔴 도장 sha ≠ 디스크 sha 인 자리 수", L.get("🔴 그 수")),
        ("🔴🔴🔴 소비자 도장이 «생산자보다 앞선» 자리 수",
         L.get("🔴🔴🔴 소비자 도장이 «생산자보다 앞선» 자리 수")),
        ("🔴🔴🔴 그 자리",
         L.get("🔴🔴🔴 위상 어긋남(소비자 < 생산자 · 고리 밖)")),
        ("🔴🔴 고리 «안»의 어긋남 수(= `F10` 이 수렴으로 푼다)",
         L.get("🔴🔴 고리 «안»의 어긋남(= `F10` 이 수렴으로 푼다) 수")),
        ("🔴 그 러너의 걸린 자리", L.get("🔴 걸린 자리(= 비교를 «수행»한 회수)")),
        ("🔴 아직 안 돌았나", bool(not L)),
    ]), (1 if L else 0)


def j_F10():
    hits = 0
    rows = []
    man = _load("runners/out992_docsha.json")
    for rel in DOCS_992[:4]:
        src = _read(rel)
        hits += 1
        cur = hashlib.sha256((src or "").encode("utf-8")).hexdigest()
        prev = (man.get("파일별") or {}).get(rel)
        rows.append({"문서": rel, "지금 sha256": cur, "직전 sha256": prev,
                     "🔴 같나": bool(prev is not None and prev == cur)})
    ok = all(r["🔴 같나"] for r in rows)
    return bool(not ok), collections.OrderedDict([
        ("🔴 자리별", rows), ("🔴 수렴했나", ok),
    ]), hits


def j_F11():
    """🔴🔴🔴 **992 판 --- `F11` 을 «실제로» 구현한다.**

    991 은 이 자를 「단언이라 못 셈」이라 «신고해 놓고» 분자 12 에 그대로 넣었다.
    그리고 대조 대상 슬롯 이름 여섯이 «치환표에 하나도 없어서» `keys` 가 «빈 목록»이었다.

    🔴 **992 판**: `out992_slots.json`(슬롯 대장)에서 **「같은 이름 슬롯」이 두 자리 이상에
    앉은 것**을 골라 **문서 본문의 «글자»를 서로 견준다**. 그리고 사전등록·원장·메모리 카드
    셋에서 그 값이 «보이나»를 따로 센다(여섯 자리).
    """
    man = _load("runners/out992_slots.json").get("파일별") or {}
    hits = 0
    byname = collections.defaultdict(dict)
    for rel, info in man.items():
        for sl in info.get("슬롯") or []:
            byname[sl["슬롯"]][rel] = sl["값"]
    shared = {k: v for k, v in byname.items() if len(v) >= 2}
    bad = []
    for k, places in sorted(shared.items()):
        hits += len(places)
        vals = set(places.values())
        if len(vals) > 1:
            bad.append({"슬롯": k, "자리별": places})
    # 🔴 나머지 세 자리 --- 값이 «보이나»를 센다(어긋남이 아니라 «덮임»이다)
    outside = collections.OrderedDict([
        ("사전등록", _read(PREREG) or ""),
        ("원장", _read(LEDGER) or ""),
        ("메모리 카드", (CARD_OUTSIDE.read_text(encoding="utf-8")
                    if CARD_OUTSIDE.is_file() else "")),
    ])
    cover = collections.OrderedDict()
    for nm, txt in outside.items():
        n = 0
        for k, places in sorted(shared.items()):
            hits += 1
            s = list(places.values())[0]
            if s and s in txt:
                n += 1
        cover[nm] = n
    return bool(bad), collections.OrderedDict([
        ("🔴🔴🔴 두 자리 이상에 앉은 슬롯 수(= 이 자의 «분모»)", len(shared)),
        ("🔴 슬롯 대장의 슬롯 이름 수", len(byname)),
        ("🔴🔴🔴 어긋난 슬롯", bad or "없음"),
        ("🔴🔴🔴 어긋난 슬롯 수", len(bad)),
        ("🔴 여섯 자리", list(man) + list(outside)),
        ("🔴 나머지 세 자리에서 «보이는» 슬롯 수", cover),
        ("🔴 991 이 저지른 것",
         "🔴 **`keys` 가 «빈 목록»이라 `hits = 0` 이었고 「단언이라 못 셈」이라 «신고까지 해 놓고» "
         "분자 12 에 그대로 넣었다.** 정직한 수는 `11/13` 이었다"),
    ]), hits


def j_F12():
    A = _load("runners/out992_audit.json")
    D = A.get("§D 🔴🔴 규칙 D — 992 자신") or {}
    D9 = A.get("§D-나 🔴 규칙 D — 991 을 같은 자로 다시 센다") or {}
    if D.get("🔴🔴🔴 못 쟀다(대장이 없다)") is not False:
        return True, {"🔴🔴🔴 슬롯 대장이 없다(= 「깨끗함」이 «아니다»)": True}, 0
    hits = int(D.get("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)") or 0)
    meas = D.get("🔴🔴🔴 ㉰ 측정치(= 판정에 «무는» 것)만의 수")
    sig = D.get("🔴🔴🔴 유효숫자가 어긋난 슬롯 수")
    badslot = D.get("🔴🔴🔴 키 경로와 본문이 다른 슬롯 합")
    n_files = len(D.get("🔴 파일별") or {})
    denom_ok = bool(n_files == DENOM.get("규칙 D 대상"))
    return bool(meas or badslot or sig or not denom_ok), collections.OrderedDict([
        ("🔴 대상 수(등록 분모)", DENOM.get("규칙 D 대상")),
        ("🔴 실제 대상 수", n_files),
        ("🔴🔴🔴 등록 분모와 실제가 «같나»", denom_ok),
        ("🔴🔴🔴 센 수 합", D.get("🔴🔴🔴 센 수 합")),
        ("🔴🔴🔴 못 찾는 수 합", D.get("🔴🔴🔴 못 찾는 수 합")),
        ("🔴🔴🔴 그 «세 갈래»", D.get("🔴🔴🔴 못 찾는 수의 «세 갈래»")),
        ("🔴🔴🔴 ㉰ 측정치만의 수", meas),
        ("🔴🔴🔴 유효숫자가 어긋난 슬롯 수", sig),
        ("🔴🔴🔴 키 경로와 본문이 다른 슬롯 합(🔴 992 가 «처음으로» 무는 칸)", badslot),
        ("🔴🔴 991 을 «같은 자»로 다시 센 값", collections.OrderedDict([
            ("못 찾는 수 합", D9.get("🔴🔴🔴 못 찾는 수 합")),
            ("㉰ 측정치만", D9.get("🔴🔴🔴 ㉰ 측정치(= 판정에 «무는» 것)만의 수")),
            ("유효숫자 어긋난 슬롯 수", D9.get("🔴🔴🔴 유효숫자가 어긋난 슬롯 수")),
            ("🔴🔴🔴 키 경로와 본문이 다른 슬롯 합",
             D9.get("🔴🔴🔴 키 경로와 본문이 다른 슬롯 합")),
        ])),
        ("🔴 왜 이 칸을 무나",
         "🔴 **991 은 「키 경로와 본문이 다른 슬롯 23」을 «내 놓고» 아무 통과에도 안 물렸다** "
         "(판정문 6 · 카드 6 · handoff 6 · PR 5)"),
    ]), hits


def j_F13():
    A = _load("runners/out992_audit.json")
    R = A.get("§F 🔴🔴 `F13` — 분모에 필터를 적는다") or {}
    cand = [p for p in _glob(GLOB_OUTPUTS) if p.endswith((".json", ".txt"))]
    allc = _glob(GLOB_OUTPUTS)
    doctext = "\n".join(filter(None, (_read(d) for d in DOCS_992)))
    hits, un, cited = 0, [], []
    for p in cand:
        hits += 1
        (cited if os.path.basename(p) in doctext else un).append(p)
    un_all = []
    for p in allc:
        hits += 1
        if os.path.basename(p) not in doctext:
            un_all.append(p)
    return bool(un), collections.OrderedDict([
        ("🔴 명부의 출처", "글롭 `%s` --- 손으로 안 골랐다" % GLOB_OUTPUTS),
        ("🔴🔴🔴 분모 ① 글롭 ∩ {`.json`, `.txt`}(= 판정 분모)", len(cand)),
        ("🔴🔴🔴 분모 ② 글롭 «전량»", len(allc)),
        ("🔴 ① 에서 인용된 것", cited),
        ("🔴🔴🔴 ① 에서 한 번도 인용 «안» 된 것", un or "없음"),
        ("🔴🔴🔴 ② 에서 한 번도 인용 «안» 된 것", un_all or "없음"),
        ("🔴🔴🔴 이 사이클 «러너» 중 문서에 한 번도 안 나오는 것",
         R.get("🔴🔴🔴 이 사이클 «러너» 중 문서에 한 번도 안 나오는 것")),
        ("⚠ 991 의 같은 수(러너 미인용)", R.get("🔴 991 의 같은 수(러너 미인용)")),
    ]), hits


_SLOT = re.compile(r"\{\{[^}]+\}\}")
_NUM = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?(?![\w])")


def _tpl_hand_numbers(src, S):
    spans = [(m.start(), m.end()) for m in _SLOT.finditer(src)]
    allow, _why = LG.allow_spans(src, LG.ALLOW_CTX)
    hand, scanned, exempt = [], 0, 0
    for m in _NUM.finditer(src):
        scanned += 1
        if any(a <= m.start() and m.end() <= b for a, b in spans):
            continue
        if any(a <= m.start() and m.end() <= b for a, b in allow):
            exempt += 1
            continue
        if LG._norm(m.group()) in S:
            continue
        ctx = re.sub(r"\s+", " ", src[max(0, m.start() - 40):m.end() + 40])
        hand.append({"수": m.group(), "맥락": ctx})
    return scanned, hand, exempt


_PREREG_CONST = re.compile(r"```(.*?)```", re.S)
_REPRO_TAG = "[손전사:재현]"


def _prereg_consts():
    """🔴 사전등록 §7 «상수» 블록에 «신고된» 수. 그 밖의 리터럴은 미신고 상수다."""
    src = _read(PREREG) or ""
    out = set()
    for m in _PREREG_CONST.finditer(src):
        for x in re.finditer(r"(?<![\w.])\d+(?:\.\d+)?(?:e-?\d+)?", m.group(1)):
            out.add(LG._norm(x.group()))
    return out


def j_F14():
    """🔴🔴 **992 판** --- **부동소수 리터럴 «전수»**(대입만이 아니다).

    🔴 991 의 자는 `T[...] = <수 리터럴>` 꼴만 봐서 `world991.py:445` 의
    `want = 0.3596`(주석이 「손으로 옮겼다」고 «자백»한 수)을 원리상 못 봤다.
    """
    ran = RAN_992()
    S_self = LG.artifact_numbers("out992_*.json")
    S_pub = LG.artifact_numbers("out97*.json")
    S_pub |= LG.artifact_numbers("out98*.json")
    S_pub |= LG.artifact_numbers("out99[01]*.json")
    consts = _prereg_consts()
    hits, pass_lit, tpl_hand = 0, [], []
    tpl_scanned, tpl_exempt = 0, 0
    hand_float, undeclared, scanned_lit = [], [], 0
    for rel in ran:
        src = _read(rel) or ""
        if rel.endswith(".tpl"):
            sc, hand, ex = _tpl_hand_numbers(src, S_self)
            tpl_scanned += sc
            tpl_exempt += ex
            hits += sc
            for h in hand:
                tpl_hand.append(dict(h, 파일=rel))
            continue
        lines = src.split("\n")
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for t in ast.walk(tree):
            hits += 1
            if isinstance(t, ast.Tuple) and len(t.elts) == 2:
                a, b = t.elts
                if isinstance(a, ast.Constant) and a.value == "통과" \
                        and isinstance(b, ast.Constant) and b.value is True:
                    pass_lit.append({"파일": rel, "줄": t.lineno})
            # 🔴🔴🔴 **부동소수 리터럴 «전수»** --- 대입이든 인자든 비교든 «전부**
            if isinstance(t, ast.Constant) and isinstance(t.value, float):
                scanned_lit += 1
                hits += 1
                nm = LG._norm(repr(t.value))
                line = lines[t.lineno - 1] if 0 < t.lineno <= len(lines) else ""
                seg = line[getattr(t, "col_offset", 0):
                           getattr(t, "end_col_offset", 0)] or repr(t.value)
                # 🔴 «정밀한 수»(소수점 아래 «세 자리 이상»)만 「손 전사」 후보다 ---
                #   `1.0`·`0.95`·`5e-4` 같은 인자·허용오차는 «옮겨 적은 측정치»가 아니다.
                precise = bool(re.search(r"\.\d{3,}", seg))
                if precise and nm in S_pub and nm not in consts \
                        and _REPRO_TAG not in line:
                    hand_float.append({"파일": rel, "줄": t.lineno,
                                       "값": t.value, "소스": seg,
                                       "줄 내용": line.strip()[:120]})
                elif precise and nm not in S_pub and nm not in consts \
                        and nm not in S_self:
                    undeclared.append({"파일": rel, "줄": t.lineno, "값": t.value})
    return bool(pass_lit or tpl_hand or hand_float), collections.OrderedDict([
        ("🔴 분모 `RAN_992`(글롭 --- `prose*`·`fix*`·`docs/tpl/*.tpl` 이 «든다»)", ran),
        ("🔴 분모 크기", len(ran)),
        ("🔴🔴🔴 리터럴 `(\"통과\", True)` 자리", pass_lit or "없음"),
        ("🔴🔴🔴 훑은 «부동소수 리터럴» 수(992 가 넓힌 분모)", scanned_lit),
        ("🔴 판정 꼴", "🔴 **소수점 아래 «세 자리 이상»인 리터럴 ∧ 옛 사이클 산출물이 낸 수 ∧ "
                  "사전등록 §7 이 «안» 신고한 수 ∧ `%s` 꼬리표가 «없는» 줄**" % _REPRO_TAG),
        ("🔴🔴🔴 «손 전사» 부동소수 리터럴(옛 사이클 산출물이 «낸» 수를 소스에 박았다)",
         hand_float or "없음"),
        ("🔴🔴🔴 그 수", len(hand_float)),
        ("🔴 «미신고» 상수(산출물에도 없고 사전등록 §7 에도 없다 — 진단)",
         undeclared[:20] or "없음"),
        ("🔴 그 수(진단)", len(undeclared)),
        ("🔴 사전등록 §7 이 신고한 상수 수", len(consts)),
        ("🔴🔴🔴 템플릿의 «손 전사 수»(`{{슬롯}}` 밖)", tpl_hand or "없음"),
        ("🔴🔴🔴 그 수(템플릿)", len(tpl_hand)),
        ("🔴 템플릿에서 «훑은 자리» 수", tpl_scanned),
        ("🔴 재현 꼬리표", "🔴 옛 사이클의 수를 «일부러» 재현하는 자리는 그 줄에 "
                     "`%s` 를 단다 --- 꼬리표 없는 것만 «손 전사»로 센다" % _REPRO_TAG),
        ("🔴 991 이 못 본 것",
         "🔴 `world991.py:445` 의 `want = 0.3596` --- 991 의 자는 `T[...] = <수>` 꼴만 봤다"),
    ]), hits


# ══════════════════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    a = ap.parse_args()
    if len(a.ref) != 40:
        raise SystemExit("🔴 --ref 는 40자 sha 여야 한다")
    t0 = _now()

    judges = collections.OrderedDict([
        ("F01", lambda: j_F01(a.ref)), ("F02", j_F02), ("F03", j_F03),
        ("F04", j_F04), ("F05", j_F05), ("F06", j_F06), ("F07", j_F07),
        ("F08", j_F08), ("F09", j_F09), ("F10", j_F10), ("F11", j_F11),
        ("F12", j_F12), ("F13", j_F13), ("F14", j_F14),
    ])
    rows = collections.OrderedDict()
    for k, fn in judges.items():
        fal, ev, hits = fn()
        rows[k] = collections.OrderedDict([
            ("조건", FALSIFY[k]),
            ("🔴🔴🔴 반증됐나", fal),
            ("🔴 걸린 자리(= 이 «판정 함수»가 비교를 «수행»한 회수)", hits),
            ("🔴🔴 「통과」로 셀 수 있나(= 잰 것인가)", bool(fal is not None and hits > 0)),
            ("근거", ev),
            ("통과", bool(fal is False)),
        ])
    fals = [k for k, v in rows.items() if v["🔴🔴🔴 반증됐나"] is True]
    unmeasured = [k for k, v in rows.items()
                  if not v["🔴🔴 「통과」로 셀 수 있나(= 잰 것인가)"]]
    # 🔴🔴🔴 **「셀 수 없는」 조건은 분자·분모에서 «둘 다» 뺀다**(992 `R3`).
    countable = [k for k in rows if k not in unmeasured]
    n_ok = len([1 for k in countable if rows[k]["통과"]])
    m_cnt = len(countable)

    preds, phit, p_hits = collections.OrderedDict(), 0, 0
    for k, (path, op, want) in PRED_DEF.items():
        got, err = LG.resolve(path)
        p_hits += 1
        ok = None
        if err is None:
            ok = (got == want) if op == "==" else (
                got <= want if op == "<=" else (
                    got >= want if op == ">=" else None))
        phit += int(bool(ok))
        preds[k] = collections.OrderedDict([
            ("🔴 판정식", "%s#%s %s %s" % (path[0], " | ".join(path[1:]), op, want)),
            ("🔴 산출물이 낸 값", got), ("🔴 못 읽었나", err),
            ("🔴🔴 맞았나", ok),
        ])

    wiring = _load("runners/out992_wiring.json")
    arms = _load("runners/out992_order.json")
    audit = _load("runners/out992_audit.json")
    last = _load("runners/out992_last.json")
    five = _load("runners/fiveprime_992.json")
    table = _load("runners/out992_table.json")
    mut = _load("runners/out992_mut.json")
    paper = _load("runners/out992_paper.json")

    # 🔴🔴🔴 **자가 «잡은» red 를 «전부» 최상위 연언에 문다**(992 의 병이 여기였다)
    D = audit.get("§D 🔴🔴 규칙 D — 992 자신") or {}
    parts = collections.OrderedDict([
        ("반증된 조건 0", bool(not fals)),
        ("🔴🔴 미측정 0(988 판 §59-나 복원)", bool(not unmeasured)),
        ("예측 전량", bool(phit == len(PRED_DEF))),
        ("배선(out992_wiring)", bool(wiring.get("통과"))),
        ("순서(out992_order)", bool(arms.get("통과"))),
        ("자기 자(out992_audit)", bool(audit.get("통과"))),
        ("🔴 990 변이체 실측(out992_mut)", bool(mut.get("통과"))),
        ("🔴 F09 도장 위상(out992_last)", bool(last.get("통과"))),
        ("🔴 ⑤′(fiveprime_992)", bool(five.get("통과"))),
        # 🔴🔴🔴 **992 `R1`** --- 표의 「못 읽은 슬롯 0」을 «최상위»에 문다.
        #   991 은 `out991_table.json` 이 `통과: False` 를 «기록해 놓고» 어디에도 안 물렸고
        #   그래서 문서 넷이 「없음/없음」을 실었다.
        ("🔴🔴🔴 치환표(out992_table) — 못 읽은 슬롯 0", bool(table.get("통과"))),
        # 🔴🔴🔴 **992 `R3`** --- 규칙 D 의 「키 경로와 본문이 다른 슬롯 0」을 «최상위»에 문다.
        ("🔴🔴🔴 규칙 D — 키 경로와 본문이 다른 슬롯 0",
         bool(D.get("🔴🔴🔴 키 경로와 본문이 다른 슬롯 합") == 0
              and D.get("🔴🔴🔴 못 쟀다(대장이 없다)") is False)),
        ("🔴 논문 한 스텝(out992_paper)", bool(paper.get("통과"))),
    ])

    res = collections.OrderedDict()
    res["무엇"] = "992 채점 — 🔴 **자가 «잡은» 것을 «전부» 최상위 연언에 문다**"
    res["사전등록"] = PREREG
    d_hits, d_bad = 0, []
    for _k, _v in DENOM.items():
        d_hits += 1
        if not (isinstance(_v, int) and _v > 0):
            d_bad.append(_k)
    res["§1 🔴 등록 분모"] = collections.OrderedDict(
        list(DENOM.items()) + [
            ("🔴🔴🔴 출처", "🔴 **`%s` §7-가 표에서 «기계로» 긁었다** --- 손 딕트가 «아니다»"
             % PREREG),
            ("🔴 긁은 분모 수", len(DENOM)),
            ("🔴 양의 정수가 아닌 분모", d_bad or "없음"),
            ("통과", bool(not d_bad and len(DENOM) >= 12)),
            ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", d_hits)])
    res["§4 🔴 예측"] = collections.OrderedDict(
        list(preds.items()) + [
            ("🔴 맞은 수", phit), ("🔴 분모", len(PRED_DEF)),
            ("🔴🔴 분자 / 분모", "%d / %d" % (phit, len(PRED_DEF))),
            ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", p_hits),
            ("통과", bool(phit == len(PRED_DEF)))])
    res["§5 🔴 반증조건"] = collections.OrderedDict(
        list(rows.items()) + [
            ("🔴 등록 분모", len(FALSIFY)),
            ("🔴🔴🔴 «셀 수 있는» 분모(= 등록 분모 − 못 센 것)", m_cnt),
            ("🔴 통과 수(셀 수 있는 것 중)", n_ok),
            ("🔴 반증된 수", len(fals)),
            ("🔴 분모", len(FALSIFY)),
            ("🔴🔴 분자 / 분모", "%d / %d" % (n_ok, m_cnt)),
            ("🔴🔴🔴 게재 꼴", "🔴 **`통과 n / 셀 수 있는 분모 m`** --- 「셀 수 없는」 조건은 "
                          "«분자와 분모에서 둘 다» 뺀다(992 `R3`). 991 은 「못 셈」이라 "
                          "신고해 놓고 분자 12 에 넣었다"),
            ("🔴🔴 반증된 조건(식별자만)", fals or "없음"),
            ("🔴🔴 반증된 조건", fals or "없음"),
            ("🔴🔴🔴 «단언»이라 「통과」로 세면 안 되는 조건", unmeasured or "없음"),
            ("🔴🔴 미측정(잰 것이 아닌) 조건", unmeasured or "없음"),
            ("🔴🔴🔴 그 수", len(unmeasured)),
            ("🔴 걸린 자리 합", int(sum(
                v["🔴 걸린 자리(= 이 «판정 함수»가 비교를 «수행»한 회수)"]
                for v in rows.values()))),
            ("통과", bool(not fals and not unmeasured))])
    top_hits = len(parts)
    res["🔴🔴🔴 최상위를 이루는 절의 `통과` 전량"] = collections.OrderedDict(
        list(parts.items()) + [
            ("통과", bool(all(parts.values()))),
            ("🔴 조각 수", len(parts)),
            ("🔴 붉은 조각", [k for k, v in parts.items() if not v] or "없음"),
            ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", top_hits)])
    res["통과"] = bool(all(parts.values()))
    res["🔴 최상위의 정의"] = (
        "🔴 **988 판 `§59-나` 를 복원한 991 판에 «세 조각»을 더했다** --- "
        "🔴🔴🔴 `out992_table.json`(못 읽은 슬롯 0) · 규칙 D 의 「키 경로와 본문이 다른 슬롯 0」 · "
        "`out992_mut.json`. **991 은 앞의 둘을 «잡아 놓고» 아무 데도 안 물렸고 그래서 "
        "문서 넷이 「없음/없음」을 실었다**")
    res["🔴 도장"] = collections.OrderedDict([
        ("ref(부른 쪽이 준 40자 sha)", a.ref),
        ("🔴 코드 sha256", collections.OrderedDict(
            (r, hashlib.sha256((ROOT / r).read_bytes()).hexdigest())
            for r in RAN_992() if (ROOT / r).is_file())),
        ("시작(UTC)", t0), ("끝(UTC)", _now()),
    ])
    (OUT / "out992_score.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    sys.stderr.write("%s  [score] 끝 → out992_score.json (통과=%s · 반증 %s · 못 센 %s)\n"
                     % (_now(), res["통과"], fals or "없음", unmeasured or "없음"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
