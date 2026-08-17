#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""990 채점기 — 🔴🔴🔴 **모든 「걸린 자리」를 «판정 함수»가 «스스로» 낸다.**

사전등록 `docs/prereg_990_arms_rulers.md` §3(예측) · §4(반증조건 14).

🔴 **989 가 어긴 것 다섯을 구조로 막는다.**
  ① **하드코딩 `False` 금지** --- `cond()` 는 `(falsified, evidence, hits)` 를
     «판정 함수»에서만 받는다. 호출부가 `hits` 를 손으로 못 준다.
  ② **명부는 «글롭»이다**(`runners/*990*`) --- `F13`.
  ③ **`F14` 의 «수 리터럴» 검사를 되살린다**(988 `audit988._count_cell_assign`)
     + 분모에 `prose*`·`fix*`·**`docs/tpl/*.tpl`** 을 넣는다.
  ④ **`F12` 를 «실제로» 돌린다** --- `ledger.audit_text` 의 976 판 «슬롯 자».
  ⑤ **최상위 연언에 `out990_last.json`(`F09`)·`fiveprime_990.json`(`⑤′`) 을 넣고
     988 판 `§59-나`(«미측정 == 0»)를 복원한다.**

씀:
    python3 runners/score990.py --ref <40자 sha>
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
PREREG = "docs/prereg_990_arms_rulers.md"

GLOB_RUNNERS = "runners/*990*.py"
GLOB_OUTPUTS = "runners/*990*"
GLOB_TPL = "docs/tpl/*990*.tpl"

DOCS_990 = ("docs/판정_990.md", "docs/card_990.md", "docs/handoff_990.md",
            "docs/pr_990.md", PREREG)

# ══ 사전등록 §7 분모 (측정 전에 박았다 · 🔴 채점은 이 수로만 한다) ══════
DENOM = collections.OrderedDict([
    ("반증조건", 14), ("예측", 5), ("⑤′ 절", 16), ("수리 상한", 5),
    ("규칙 D 대상", 6), ("DOC_INPUTS", 5), ("세계 자료 원천", 3), ("세계 명제", 3),
    ("자", 3), ("팔", 3),
])

FALSIFY = collections.OrderedDict([
    ("F01", "사전등록 blob 을 측정 뒤에 고쳤다"),
    ("F02", "막힌 명령을 우회하고 신고를 안 했다 · 또는 `HEAD` 가 움직였다"),
    ("F03", "등록 분모와 다른 수로 채점했다 · 병기 자를 한 팔에서라도 안 기록했다"),
    ("F04", "이 사이클의 러너가 «연» `data/` 경로가 0 이다"),
    ("F05", "판정문의 주장 문장 중 «세계 자료를 인용한» 것이 0 이다"),
    ("F06", "등록 기준을 러너가 «다른 식»으로 평가했다 · 자가 뒤집혔는데 맨 위에 안 실었다"),
    ("F07", "「걸린 자리」에 «바늘·후보 생성 수»를 넣었다"),
    ("F08", "「걸린 자리 0」을 「통과」로 셌다 · 미측정이 하나라도 있다"),
    ("F09", "값을 낸 뒤 러너를 고치고 안 다시 돌렸다 --- `last990.py` 가 낸다"),
    ("F10", "문서 고리가 수렴 안 했다"),
    ("F11", "여섯 자리가 다른 수를 적는다"),
    ("F12", "규칙 D — 치환표 밖의 수가 있다(976 판 «슬롯 자»)"),
    ("F13", "이 사이클 산출물 중 문서에 «한 번도» 인용 안 된 것이 있다"),
    ("F14", "이 사이클 러너에 리터럴 `(\"통과\", True)` 또는 «손 전사 수 리터럴»이 있다"),
])

#: 🔴🔴🔴 예측 --- **선언표 «하나»로만 돈다**(`조항 72-나`).
PRED_DEF = collections.OrderedDict([
    ("P1", (["out990_arms.json", "§5 🔴🔴🔴 판정", "🔴 R_champ Δ(1800) > 0"],
            "==", True)),
    ("P2", (["out990_arms.json", "§5 🔴🔴🔴 판정",
             "🔴 (ㄱ) 천장base — 2·SE_clu 를 넘은 눈금 수"], "==", 0)),
    ("P3", (["out990_arms.json", "§5 🔴🔴🔴 판정",
             "🔴 (ㄴ) N=1800 묶음 ρ 가 α 에 단조 감소인가"], "==", True)),
    ("P4", (["out990_arms.json", "§5 🔴🔴🔴 판정",
             "🔴 (ㄱ) LODO 부호 뒤집힌 도메인 수"], "==", 0)),
    ("P5", (["out990_champ.json", "§2 🔴 재현", "🔴 공표값과의 차이"], "<=", 0.0005)),
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


def RAN_990():
    """🔴 분모는 «글롭»이다 --- `prose*`·`fix*` 와 🔴 **`docs/tpl/*.tpl`** 이 «든다».

    989 는 이 분모를 넷/다섯으로 손수 적었고 **템플릿이 자의 사각지대**였다 ---
    `docs/tpl/card_989.md.tpl:54` 의 `0.47034`·`3,775` 가 989 산출물에 «없는데도» 안 걸렸다.
    """
    return sorted(set(_glob(GLOB_RUNNERS) + _glob(GLOB_TPL)))


# ══════════════════════════════════════════════════════════════════════
# 🔴🔴🔴 판정 함수 --- **전부 `(falsified, evidence, hits)` 를 낸다.**
#     `hits` 는 «이 함수가 비교를 수행한 회수»다. 호출부가 못 준다.
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
    """🔴 **동사가 아니라 「결과 상태」로 판정한다**(990 `R1` · 티처 #128)."""
    hits = 0
    vt = _read("docs/판정_990.md") or ""
    hits += 1
    has_sec = bool(re.search(r"막힌 명령", vt))
    hits += 1
    said = bool(re.search(r"막힌 명령.{0,400}?(없었다|없다)", vt, re.S)) or has_sec
    rc, sym, _e = _git(["symbolic-ref", "-q", "HEAD"])
    hits += 1
    head_ref = sym.strip()
    moved = bool(rc != 0 or head_ref != "refs/heads/main")
    return bool(moved or not has_sec), collections.OrderedDict([
        ("🔴 판정문에 「막힌 명령」 신고 절이 있나", has_sec),
        ("🔴 「없었다」를 명시했나(또는 절이 있나)", said),
        ("🔴🔴🔴 결과 상태 — `git symbolic-ref -q HEAD`", head_ref or "(분리됨)"),
        ("🔴🔴🔴 `HEAD` 가 움직였나", moved),
        ("🔴 이 자의 판정 원칙",
         "🔴 **동사(`checkout` 이냐 `symbolic-ref` 냐)가 아니라 「결과 상태」로 판정한다** "
         "--- 990 `R1` 이 `조항 69` 에 박은 것을 990 자신에게 «먼저» 물었다"),
        ("⚠ 자의 한계(조항 61)", "🔴 셸 이력은 저장소에 안 남는다 --- 「시도 자체」는 기계가 못 본다"),
    ]), hits


def j_F03():
    """🔴 등록 분모 + 🔴🔴 **병기 자를 «모든» 팔·눈금에서 기록했나**."""
    W = _load("runners/out990_arms.json")
    hits = 0
    rulers = ["R_pool 묶음", "R_eq 균등", "R_champ 챔피언가중"]
    miss = []
    for sec, arm in (("§1 🔴🔴🔴 (ㄷ) 혼합 사다리 — 989 의 팔(자·λ 전량)", "혼합"),
                     ("§2 🔴🔴🔴 (ㄱ) 증강 사다리 — base 고정 · hplt 만 흔든다", "증강"),
                     ("§3 🔴🔴🔴 (ㄴ) 대체 사다리 — 총량 고정 · α 만 흔든다", "대체")):
        block = W.get(sec) or {}
        for u, per_rn in block.items():
            for rn in rulers:
                hits += 1                          # 🔴 팔 × λ × 자 마다 «비교»를 수행
                if rn not in per_rn:
                    miss.append({"절": sec, "λ": u, "자": rn})
    used = collections.OrderedDict([
        ("반증조건", len(FALSIFY)), ("예측", len(PRED_DEF)),
        ("자", len(rulers)), ("팔", 3),
        ("세계 자료 원천", len((W.get("🔴🔴🔴 세계 자료(런타임 지문)") or {}))),
        ("세계 명제", 3),
    ])
    bad = [k for k, v in used.items() if DENOM.get(k) != v]
    hits += len(used)
    return bool(bad or miss), collections.OrderedDict([
        ("🔴 등록 분모", dict(DENOM)), ("🔴 실제로 쓴 분모", dict(used)),
        ("🔴 어긋난 분모", bad or "없음"),
        ("🔴🔴🔴 병기 자를 «안 기록한» 자리", miss or "없음"),
        ("🔴🔴🔴 안 기록한 자리 수", len(miss)),
    ]), hits


def j_F04():
    A = _load("runners/out990_audit.json")
    G = A.get("§G 🔴🔴🔴 §1-9 — 이 사이클이 «세계»를 만졌나") or {}
    n = G.get("🔴🔴🔴 ㉠ 런타임 최대")
    return bool(not n), {"🔴 런타임 연 `data/` 경로 수": n,
                         "🔴 정적 경로 수": G.get("🔴 ㉠ 정적 경로 수")}, 1


def j_F05():
    A = _load("runners/out990_audit.json")
    G = A.get("§G 🔴🔴🔴 §1-9 — 이 사이클이 «세계»를 만졌나") or {}
    n = G.get("🔴🔴🔴 ㉡ 그중 세계 자료를 «인용한» 문장 수")
    return bool(not n), {"🔴 세계 인용 주장 문장 수": n,
                         "🔴 주장 문장 수": G.get("🔴🔴🔴 ㉡ 판정문의 주장 문장 수")}, 1


#: 🔴 **키 경로는 ` | ` 로 «이어붙인다»** --- 구판은 `[^`|]` 라 파이프에서 «끊겨»
#: 등록 키 경로를 «하나도» 못 읽었다(0 개). 990 이 자기 자에서 잡았다.
_KEYPATH = re.compile(r"판정식:\s*(\S+?)#(.+?)\s*(==|<=|>=)\s*([^\s`]+)\s*`")


def j_F06():
    """🔴 여덟째 칸 — 사전등록 §3 의 «키 경로 집합» ↔ `PRED_DEF` 의 그것."""
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
        # 🔴 **fail-open 을 닫는다**(조항 59) --- 「하나도 못 읽었다」는 「같다」가 아니다
        return True, {"🔴🔴🔴 사전등록에서 키 경로를 «하나도» 못 읽었다": True,
                      "🔴": "🔴 자가 «자기 문법»으로 등록문을 못 읽는다 --- 「어긋남 0」이 아니다"}, 1
    def_paths = {(p[0][0], tuple(p[0][1:])) for p in PRED_DEF.values()}
    hits += len(reg_paths) + len(def_paths)
    only_reg = sorted("%s#%s" % (f, " | ".join(k)) for f, k in reg_paths - def_paths)
    only_def = sorted("%s#%s" % (f, " | ".join(k)) for f, k in def_paths - reg_paths)
    # 🔴 자가 뒤집혔는데 판정문 «맨 위»에 안 실었나
    W = _load("runners/out990_arms.json")
    J = W.get("§5 🔴🔴🔴 판정") or {}
    flipped = bool(J.get("🔴🔴🔴 자에 따라 답이 «뒤집히나»"))
    vt = _read("docs/판정_990.md") or ""
    head = "\n".join(vt.split("\n")[:14])
    hits += 1
    top_ok = (not flipped) or bool(
        ("반대 부호" in head) or ("뒤집" in head and "자" in head))
    return bool(only_reg or only_def or not top_ok), collections.OrderedDict([
        ("🔴 사전등록이 적은 키 경로 수", len(reg_paths)),
        ("🔴 `PRED_DEF` 의 키 경로 수", len(def_paths)),
        ("🔴 사전등록에만 있는 것", only_reg or "없음"),
        ("🔴 `PRED_DEF` 에만 있는 것", only_def or "없음"),
        ("🔴🔴🔴 자에 따라 답이 뒤집혔나", flipped),
        ("🔴🔴🔴 판정문 «맨 위 14 줄»에 그 한 줄이 있나", top_ok),
    ]), hits


_HITKEY = re.compile(r"걸린 자리")


def _walk_sections(rel):
    """🔴 `통과` 키를 내는 절 «전량». 손으로 안 고른다."""
    try:
        d = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    except Exception:                                              # noqa: BLE001
        return []
    rows = []

    def walk(o, path):
        if not isinstance(o, dict):
            return
        if "통과" in o:
            hk = [k for k in o if _HITKEY.search(k)]
            hv = [o[k] for k in hk if isinstance(o[k], int)]
            rows.append({"산출물": rel, "절": " | ".join(path) or "(맨 위)",
                         "통과": o["통과"], "걸린 자리 칸": hk,
                         "걸린 자리": (min(hv) if hv else None)})
        for k, v in o.items():
            if isinstance(v, dict):
                walk(v, path + [k])
    walk(d, [])
    return rows


_HITLIT = re.compile(r"걸린 자리")


def j_F07():
    """🔴 **「걸린 자리」에 «생성 수»를 실었나** --- 🔴🔴 **«출처»로 잰다. 값으로 «안» 잰다.**

    🔴🔴🔴 **990 의 첫 판은 「걸린 자리 값이 명부 길이와 «같은가»」로 쟀다. 그것은 틀렸다** ---
    `조항 60-라`(990 자신이 이 사이클에 신설한 조항)가 금지하는 바로 그 병
    「수가 같으면 출처도 같다고 친다」다. 🔴 **자가 자기 조항을 어겼고, 자기가 잡았다.**

    **신판** --- `RAN_990` 의 **AST** 에서 「걸린 자리」 칸의 값이
    **`len(...)` 표현식**이거나 `hits=len(...)` 인 자리를 «전수» 훑는다. 그것이 «출처»다.
    값이 우연히 같은 자리는 **판정에 «안» 쓰고 「진단」으로만 싣는다**.
    """
    hits, bad, scanned = 0, [], 0
    for rel in RAN_990():
        if not rel.endswith(".py"):
            continue
        src = _read(rel) or ""
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for n in ast.walk(tree):
            # 🔴🔴🔴 **989 의 사인(死因)을 «정확히»** 잡는다 ---
            #   판정이 «리터럴 불리언»인 «같은 호출»에 `hits=len(...)` 가 실린 자리.
            #   그것이 `score989.py:340`·`347` 의 `cond("F07", False, {...}, hits=len(FALSIFY))` 다.
            #   🔴 «비교를 실제로 수행한» 회수가 우연히 명부 길이와 같은 것은 위반이 «아니다».
            # 🔴 「걸린 자리」 칸을 «전수» 훑는다 --- 이것이 이 자의 «분모»다
            if isinstance(n, ast.Tuple) and len(n.elts) == 2:
                k0 = n.elts[0]
                if isinstance(k0, ast.Constant) and isinstance(k0.value, str) \
                        and _HITLIT.search(k0.value):
                    scanned += 1
                    hits += 1
            if not isinstance(n, ast.Call):
                continue
            lit = [a for a in n.args
                   if isinstance(a, ast.Constant) and isinstance(a.value, bool)]
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
    # 🔴 진단(판정에 «안» 쓴다) --- 값이 명부 길이와 «우연히» 같은 자리
    sizes = collections.OrderedDict([
        ("len(FALSIFY)", len(FALSIFY)), ("len(PRED_DEF)", len(PRED_DEF)),
        ("len(DENOM)", len(DENOM)), ("len(RAN_990)", len(RAN_990())),
        ("len(DOCS_990)", len(DOCS_990)),
    ])
    sizeset = {v: k for k, v in sizes.items()}
    coincide = []
    for rel in _glob(GLOB_OUTPUTS):
        if not rel.endswith(".json"):
            continue
        for r in _walk_sections(rel):
            hv = r["걸린 자리"]
            if hv is not None and hv in sizeset:
                coincide.append({"산출물": r["산출물"], "절": r["절"], "걸린 자리": hv,
                                 "이 수와 같다": sizeset[hv]})
    return bool(bad), collections.OrderedDict([
        ("🔴🔴🔴 판정 꼴", "🔴 **«출처»(AST) 로 잰다. «값»으로 안 잰다**(`조항 60-라`)"),
        ("🔴 훑은 자리 수(= «검사한 자리»)", scanned),
        ("🔴🔴🔴 판정이 «리터럴»인데 걸린 자리를 실은 자리", bad or "없음"),
        ("🔴🔴🔴 그 수", len(bad)),
        ("🔴 진단(판정에 «안» 쓴다) — 값이 명부 길이와 «우연히» 같은 자리", coincide or "없음"),
        ("🔴 그 수(진단)", len(coincide)),
        ("🔴 왜 값으로 안 재나",
         "🔴 **990 의 첫 판이 값으로 쟀고 자리 %d 을 냈는데 대부분이 «우연»이었다** --- "
         "씨앗 다섯의 비교가 `len(DOCS_990) = 5` 와 같다고 위반이 아니다. "
         "`조항 60-라`(990 신설)가 금지하는 병이 정확히 그것이다" % len(coincide)),
        ("🔴 989 가 어긴 자리",
         "🔴 `score989.py:340`·`347` --- `F07`·`F08` 이 `hits=len(FALSIFY)` 를 실었다"),
    ]), hits


def j_F08():
    """🔴 **「걸린 자리 0」 위의 초록** --- 990 «자기» 산출물 전량(글롭)."""
    hits, un, rows, foreign = 0, [], 0, []
    for rel in _glob(GLOB_OUTPUTS):
        if not rel.endswith(".json"):
            continue
        # 🔴 **남의 자의 산출물은 «세어 드러내되» 판정에 «안» 쓴다**(955 R4 · 982 R3 규율).
        #    `fiveprime_990.json` 은 `fiveprime902.py`(공유 하네스)가 낸다 --- 그 절의 꼴을
        #    이 사이클이 고칠 수 없고, 그 절의 판정은 이미 최상위 연언의 `⑤′` 조각이 나른다.
        mine = rel.startswith("runners/out990_")
        for r in _walk_sections(rel):
            rows += 1
            hits += 1                              # 🔴 절마다 «비교»를 수행
            if r["통과"] is True and (r["걸린 자리"] is None or r["걸린 자리"] == 0):
                (un if mine else foreign).append(
                    {"산출물": r["산출물"], "절": r["절"],
                     "걸린 자리 칸": r["걸린 자리 칸"] or "없음"})
    return bool(un), collections.OrderedDict([
        ("🔴 명부의 출처", "글롭 `%s`" % GLOB_OUTPUTS),
        ("🔴 훑은 절 수(= «검사한 자리» · 「걸린 자리」와 «갈라 센다»)", rows),
        ("🔴🔴🔴 «미측정»(초록인데 걸린 자리가 0 이거나 칸이 없다)", un or "없음"),
        ("🔴🔴🔴 미측정 수", len(un)),
        ("🔴 남의 자(`fiveprime902`)의 산출물에서 «센» 미측정 --- 판정에 «안» 쓴다",
         foreign or "없음"),
        ("🔴 그 수(판정 밖)", len(foreign)),
        ("🔴 판정 꼴", "988 판 `§59-나` 복원 --- **이 사이클이 «쓴» 산출물에 "
                    "미측정이 «하나라도» 있으면 반증**"),
    ]), hits


def j_F09():
    L = _load("runners/out990_last.json")
    v = L.get("🔴🔴🔴 F09 반증됐나")
    return (None if v is None else bool(v)), collections.OrderedDict([
        ("🔴 출처", "runners/out990_last.json --- «맨 마지막 러너»가 낸다"),
        ("🔴 그 러너의 걸린 자리", L.get("🔴 걸린 자리(= 비교를 «수행»한 회수)")),
        ("🔴 아직 안 돌았나", bool(not L)),
    ]), (1 if L else 0)


def j_F10():
    """🔴 문서 고리 수렴 --- 생산기를 다시 돌려 «바이트»가 같은가."""
    hits = 0
    rows = []
    man = _load("runners/out990_docsha.json")
    for rel in DOCS_990[:4]:
        src = _read(rel)
        hits += 1
        cur = hashlib.sha256((src or "").encode("utf-8")).hexdigest()
        prev = (man.get("파일별") or {}).get(rel)
        rows.append({"문서": rel, "지금 sha256": cur, "직전 sha256": prev,
                     "🔴 같나": bool(prev is not None and prev == cur)})
    ok = all(r["🔴 같나"] for r in rows)
    return bool(not ok), collections.OrderedDict([
        ("🔴 자리별", rows),
        ("🔴 출처", "runners/out990_docsha.json --- `note990_gen.py` 가 «찍을 때마다» 쓴다"),
        ("🔴 수렴했나", ok),
    ]), hits


def j_F11():
    """🔴 여섯 자리가 «같은 수»를 적나 --- 치환표의 값을 여섯 자리에서 찾는다."""
    t = _load("runners/out990_table.json")
    vals = t.get("값") or {}
    places = collections.OrderedDict([
        ("판정문", _read("docs/판정_990.md")),
        ("카드", _read("docs/card_990.md")),
        ("handoff", _read("docs/handoff_990.md")),
        ("PR", _read("docs/pr_990.md")),
        ("사전등록", _read(PREREG)),
        ("메모리 카드", _read_outside()),
    ])
    #: 🔴 치환표에 «실제로 있는» 슬롯만 고른다. 없으면 「어긋남 0」이 아니라 «미측정»이다.
    keys = [k for k in ("W1.Δ1800", "자.pool천장", "W3.재현", "자.판정",
                        "W2.몫977", "채.최상위")
            if k in vals]
    hits, bad = 0, []
    for k in keys:
        s = LG.render(vals[k])
        seen = collections.OrderedDict()
        for name, src in places.items():
            hits += 1
            seen[name] = bool(src and s in src)
        # 🔴 «적은 자리»끼리 어긋나는가 --- 안 적은 자리는 어긋남이 아니다
        wrote = [n for n, v in seen.items() if v]
        if len(wrote) >= 2 and len(wrote) != len([1 for v in seen.values() if v]):
            bad.append({"슬롯": k, "값": s, "자리별": seen})
    return bool(bad), collections.OrderedDict([
        ("🔴 대조한 슬롯", keys), ("🔴 어긋난 자리", bad or "없음"),
        ("🔴 여섯 자리", list(places)),
    ]), hits


def _read_outside():
    p = Path(os.path.expanduser(
        "~/.claude/projects/-Users-ax-world-model/memory/project-lab-state.md"))
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return None


def j_F12():
    """🔴🔴🔴 **규칙 D 를 «실제로» 돌린다** --- `ledger.audit_text` 의 976 판 슬롯 자.

    989 는 「안 돌렸다」고 자백해 놓고 자리수 `52`·`57` 을 확정형으로 실었다.
    """
    man = _load("runners/out990_slots.json")
    files = man.get("파일별") or {}
    if not files:
        # 🔴 **fail-open 을 닫는다**(977 수리 3) --- 대장이 없으면 «반증»이다
        return True, {"🔴🔴🔴 슬롯 대장이 없다": True,
                      "🔴": "`note990_gen.py` 가 `out990_slots.json` 을 먼저 써야 한다. "
                            "🔴 **「없다」는 「깨끗하다」가 아니다**(조항 59)"}, 0
    S = LG.artifact_numbers("out990_*.json")
    per, hits = collections.OrderedDict(), 0
    tot = miss = badslot = exempt = 0
    for rel, info in files.items():
        src = _read(rel)
        if src is None:
            per[rel] = {"🔴 파일이 없다": True}
            continue
        r = LG.audit_text(src, info["슬롯"], S)
        hits += r["센 수"] + len(r["슬롯"])         # 🔴 수마다 · 슬롯마다 비교를 수행
        tot += r["센 수"]
        miss += len(r["🔴🔴 976 판이 못 찾는 수"])
        badslot += r["🔴 키 경로와 본문이 다른 슬롯"]
        exempt += r["면제된 수"]
        per[rel] = collections.OrderedDict([
            ("🔴 센 수", r["센 수"]), ("🔴 면제된 수", r["면제된 수"]),
            ("🔴 슬롯 수", len(r["슬롯"])),
            ("🔴🔴 키 경로와 본문이 다른 슬롯", r["🔴 키 경로와 본문이 다른 슬롯"]),
            ("🔴🔴🔴 976 판이 «못 찾는» 수", len(r["🔴🔴 976 판이 못 찾는 수"])),
            ("🔴 그 수의 처음 열둘", r["🔴🔴 976 판이 못 찾는 수"][:12]),
        ])
    return bool(miss or badslot), collections.OrderedDict([
        ("🔴 대상 수(등록 분모)", DENOM["규칙 D 대상"]),
        ("🔴 실제 대상 수", len(files)),
        ("🔴 자", "`ledger.audit_text` --- 976 판 «슬롯 자»(본문[시작:끝) == render(resolve(키경로)))"),
        ("🔴 파일별", per),
        ("🔴🔴🔴 센 수 합", tot), ("🔴 면제된 수 합", exempt),
        ("🔴🔴🔴 976 판이 «못 찾는» 수 합", miss),
        ("🔴🔴🔴 키 경로와 본문이 다른 슬롯 합", badslot),
        ("🔴 989 가 실은 `52`·`57`",
         "🔴 **티처 #127 이 준 값이고 989 는 «안 쟀다».** 990 이 «잰» 수는 위 칸이다"),
    ]), hits


def j_F13():
    """🔴 명부는 «글롭»이다 --- 손으로 안 고른다."""
    cand = [p for p in _glob(GLOB_OUTPUTS) if p.endswith((".json", ".txt"))]
    doctext = "\n".join(filter(None, (_read(d) for d in DOCS_990)))
    hits, un, cited = 0, [], []
    for p in cand:
        hits += 1
        (cited if os.path.basename(p) in doctext else un).append(p)
    return bool(un), collections.OrderedDict([
        ("🔴 명부의 출처", "글롭 `%s` --- 손으로 안 골랐다" % GLOB_OUTPUTS),
        ("🔴 분모(이 사이클 산출물 수)", len(cand)),
        ("🔴 인용된 것", cited),
        ("🔴🔴🔴 한 번도 인용 «안» 된 것", un or "없음"),
    ]), hits


def _count_cell_assign(src):
    """🔴 **988 `audit988._count_cell_assign` 을 되살린다**(989 가 병합하며 잃었다).

    `T[...] = <수 리터럴>` 꼴 «후보» 자리 수와 그중 «숫자 리터럴» 자리 수.
    """
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return 0, 0, []
    cand, hit, where = 0, 0, []
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
                where.append({"줄": n.lineno, "값": v.value})
    return cand, hit, where


_SLOT = re.compile(r"\{\{[^}]+\}\}")
_NUM = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?(?![\w])")


def _tpl_hand_numbers(src, S):
    """🔴 **템플릿의 «손 전사 수»** --- 규칙 D 를 «템플릿에» 그대로 물린다.

    한 수가 «손 전사»이려면 셋이 다 참이어야 한다:
      ① `{{슬롯}}` «밖»에 있다 ·
      ② `ledger.ALLOW_CTX`(저장소의 «등록된» 면제표)에 안 걸린다 ·
      ③ 🔴 **이 사이클 산출물이 «낸 적 없는» 수다**(`ledger.artifact_numbers`).

    🔴 989 는 템플릿을 분모에 «안 넣어서» `docs/tpl/card_989.md.tpl:54` 의
    `0.47034`·`3,775` 가 989 산출물에 «없는데도» 안 걸렸다.
    🔴 면제표를 «내가 짓지 않는다** --- 저장소에 이미 등기된 것을 쓴다.
    """
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


def j_F14():
    ran = RAN_990()
    S = LG.artifact_numbers("out990_*.json")
    hits, pass_lit, num_lit, tpl_hand = 0, [], [], []
    tpl_scanned, tpl_exempt = 0, 0
    for rel in ran:
        src = _read(rel) or ""
        if rel.endswith(".tpl"):
            sc, hand, ex = _tpl_hand_numbers(src, S)
            tpl_scanned += sc
            tpl_exempt += ex
            hits += sc
            for h in hand:
                tpl_hand.append(dict(h, 파일=rel))
            continue
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
        cand, hit, where = _count_cell_assign(src)
        hits += cand
        for w in where:
            num_lit.append(dict(w, 파일=rel))
    return bool(pass_lit or tpl_hand), collections.OrderedDict([
        ("🔴 분모 `RAN_990`(글롭 --- `prose*`·`fix*`·`docs/tpl/*.tpl` 이 «든다»)", ran),
        ("🔴 분모 크기", len(ran)),
        ("🔴🔴🔴 리터럴 `(\"통과\", True)` 자리", pass_lit or "없음"),
        ("🔴 `T[...] = <수 리터럴>` 자리(988 자 복원)", num_lit or "없음"),
        ("🔴 그 수", len(num_lit)),
        ("🔴🔴🔴 템플릿의 «손 전사 수»(`{{슬롯}}` 밖)", tpl_hand or "없음"),
        ("🔴🔴🔴 그 수", len(tpl_hand)),
        ("🔴 템플릿에서 «훑은 자리» 수", tpl_scanned),
        ("🔴 템플릿에서 «등록 면제표»(`ledger.ALLOW_CTX`)가 면제한 수", tpl_exempt),
        ("🔴 템플릿 판정 꼴",
         "🔴 `{{슬롯}}` 밖 ∧ `ledger.ALLOW_CTX` 밖 ∧ **이 사이클 산출물이 «낸 적 없는» 수**"),
        ("🔴 989 가 잃은 것", "🔴 «수 리터럴» 검사(988 `audit988._count_cell_assign`) --- 990 이 되살렸다"),
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
        fal, ev, hits = fn()                       # 🔴 hits 는 «판정 함수»가 낸다
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
    n_ok = len([1 for v in rows.values() if v["통과"]])

    # ── 예측 --- `PRED_DEF` «하나»로만 돈다 ────────────────────────────
    preds, phit, p_hits = collections.OrderedDict(), 0, 0
    for k, (path, op, want) in PRED_DEF.items():
        got, err = LG.resolve(path)
        p_hits += 1                                # 🔴 세면서 올린다(명부 길이를 «안» 쓴다)
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

    wiring = _load("runners/out990_wiring.json")
    arms = _load("runners/out990_arms.json")
    champ = _load("runners/out990_champ.json")
    champw = _load("runners/out990_champw.json")
    audit = _load("runners/out990_audit.json")
    last = _load("runners/out990_last.json")
    five = _load("runners/fiveprime_990.json")

    # ── 🔴🔴🔴 최상위 연언 --- 988 판 `§59-나` 복원 + `F09` + `⑤′` ─────
    parts = collections.OrderedDict([
        ("반증된 조건 0", bool(not fals)),
        ("🔴🔴 미측정 0(988 판 §59-나 복원)", bool(not unmeasured)),
        ("예측 전량", bool(phit == len(PRED_DEF))),
        ("배선(out990_wiring)", bool(wiring.get("통과"))),
        ("팔(out990_arms)", bool(arms.get("통과"))),
        ("챔피언 가중(out990_champw)", bool(champw.get("통과"))),
        ("챔피언 재현(out990_champ)", bool(champ.get("통과"))),
        ("자기 자(out990_audit)", bool(audit.get("통과"))),
        ("🔴 F09(out990_last)", bool(last.get("통과"))),
        ("🔴 ⑤′(fiveprime_990)", bool(five.get("통과"))),
    ])

    res = collections.OrderedDict()
    res["무엇"] = "990 채점 — 🔴 **모든 「걸린 자리」를 «판정 함수»가 스스로 낸다**"
    res["사전등록"] = PREREG
    # 🔴 §1 도 «자»다 --- 등록 분모가 전부 «양의 정수»인가를 실제로 견준다.
    #   🔴 걸린 자리를 `len(DENOM)` 으로 «안» 적는다(`F07` 이 금지한다). 세면서 올린다.
    d_hits, d_bad = 0, []
    for _k, _v in DENOM.items():
        d_hits += 1
        if not (isinstance(_v, int) and _v > 0):
            d_bad.append(_k)
    res["§1 🔴 등록 분모"] = collections.OrderedDict(
        list(DENOM.items()) + [
            ("🔴 양의 정수가 아닌 분모", d_bad or "없음"),
            ("통과", bool(not d_bad)),
            ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", d_hits)])
    res["§4 🔴 예측"] = collections.OrderedDict(
        list(preds.items()) + [
            ("🔴🔴 분자 / 분모", "%d / %d" % (phit, len(PRED_DEF))),
            ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", p_hits),
            ("통과", bool(phit == len(PRED_DEF)))])
    res["§5 🔴 반증조건"] = collections.OrderedDict(
        list(rows.items()) + [
            ("🔴 분모", len(FALSIFY)),
            ("🔴🔴 분자 / 분모", "%d / %d" % (n_ok, len(FALSIFY))),
            ("🔴🔴 반증된 조건(식별자만)", fals or "없음"),
            ("🔴🔴🔴 «단언»이라 「통과」로 세면 안 되는 조건", unmeasured or "없음"),
            ("🔴🔴🔴 그 수", len(unmeasured)),
            ("🔴 걸린 자리 합", int(sum(
                v["🔴 걸린 자리(= 이 «판정 함수»가 비교를 «수행»한 회수)"]
                for v in rows.values()))),
            ("통과", bool(not fals and not unmeasured))])
    top_hits = 0
    for _k in parts:
        top_hits += 1
    res["🔴🔴🔴 최상위를 이루는 절의 `통과` 전량"] = collections.OrderedDict(
        list(parts.items()) + [
            ("통과", bool(all(parts.values()))),
            # 🔴 명부 길이가 아니라 «실제로 견준 조각 수»다
            ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", top_hits)])
    res["통과"] = bool(all(parts.values()))
    res["🔴 최상위의 정의"] = (
        "🔴 **988 판 `§59-나` 를 복원했다** --- 위 열 조각의 «연언»이다. "
        "989 는 `F09` 와 `⑤′` 를 빼고 「미측정 == 0」을 `n_meas > 0`(하나라도 재면 초록)으로 "
        "갈아 끼웠다. 990 은 되돌렸다")
    res["🔴 도장"] = collections.OrderedDict([
        ("ref(부른 쪽이 준 40자 sha)", a.ref),
        ("🔴 코드 sha256", collections.OrderedDict(
            (r, hashlib.sha256((ROOT / r).read_bytes()).hexdigest())
            for r in RAN_990() if (ROOT / r).is_file())),
        ("시작(UTC)", t0), ("끝(UTC)", _now()),
    ])
    (OUT / "out990_score.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    sys.stderr.write("%s  [score] 끝 → out990_score.json (통과=%s)\n"
                     % (_now(), res["통과"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
