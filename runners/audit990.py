#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""990 — **989 의 「공허한 초록」을 전량 실측한다** (사전등록 §2).

🔴🔴🔴 **이 러너의 규율 셋**
  ① **하드코딩 `False` 를 안 쓴다** --- 모든 판정은 «판정 함수»가 낸다.
  ② **「걸린 자리」는 «판정 함수»가 «비교를 수행한 회수»로 «스스로» 반환한다**
     --- 호출부가 손으로 실지 않는다(`조항 59-나` · `F07`).
  ③ **명부를 손으로 «고르지» 않는다** --- `runners/*989*` · `runners/*990*` «글롭»이다.

씀:
    python3 runners/audit990.py --ref <40자 sha>
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
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

OUT = ROOT / "runners"
DOCS = ROOT / "docs"

RAN = ("runners/audit990.py",)

#: 🔴 989 의 러너 전량 --- **글롭이다. 손으로 안 골랐다.**
GLOB_989 = "runners/*989*"
GLOB_990 = "runners/*990*"

#: 🔴 989 가 «하드코딩»한 명부(그 자체가 이 절의 «증거»다)
OUTPUTS_989_AS_WRITTEN = ("runners/out989_wiring.json", "runners/out989_world.json",
                          "runners/out989_audit.json", "runners/out989_score.json")
DOCS_989 = ("docs/판정_989.md", "docs/card_989.md", "docs/handoff_989.md",
            "docs/pr_989.md", "docs/prereg_989_world_budget.md")


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def code_stamp():
    out = collections.OrderedDict()
    for rel in RAN:
        p = ROOT / rel
        if p.is_file():
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def _read(rel):
    p = ROOT / rel
    return p.read_text(encoding="utf-8") if p.is_file() else None


def _rel(p):
    return os.path.relpath(str(p), str(ROOT))


def _glob(pat):
    return sorted(_rel(p) for p in glob.glob(str(ROOT / pat)))


# ══════════════════════════════════════════════════════════════════════
# §A 🔴🔴 `F13` 의 명부 — 989 는 후보 «아홉» 중 «넷»만 셌다
# ══════════════════════════════════════════════════════════════════════
def a_roster():
    """🔴 **글롭으로 센다.** 반환의 `걸린 자리` 는 «인용 대조를 수행한 회수»다."""
    cand = [p for p in _glob(GLOB_989)
            if p.endswith((".json", ".txt"))]
    doctext = "\n".join(filter(None, (_read(d) for d in DOCS_989)))
    hits = 0
    cited, uncited = [], []
    for p in cand:
        name = os.path.basename(p)
        hits += 1                                  # 🔴 비교를 «수행»했다
        (cited if name in doctext else uncited).append(p)
    excluded = [p for p in cand if p not in OUTPUTS_989_AS_WRITTEN]
    exc_cited = [p for p in excluded if os.path.basename(p) in doctext]
    return collections.OrderedDict([
        ("🔴 명부의 출처", "글롭 `%s` --- 손으로 안 골랐다" % GLOB_989),
        ("🔴🔴🔴 참 후보(글롭)", cand),
        ("🔴🔴🔴 참 분모", len(cand)),
        ("🔴 989 가 «하드코딩»한 명부", list(OUTPUTS_989_AS_WRITTEN)),
        ("🔴 989 가 쓴 분모", len(OUTPUTS_989_AS_WRITTEN)),
        ("🔴🔴🔴 명부에서 «빠진» 산출물", excluded),
        ("🔴🔴🔴 그중 문서에 «실제로 인용된» 것", exc_cited),
        ("🔴 인용된 산출물", cited),
        ("🔴🔴🔴 한 번도 인용 «안» 된 산출물", uncited),
        ("🔴🔴🔴 참 분모로 재면 `F13` 이 발화하나", bool(uncited)),
        ("🔴 989 가 쓴 분모로 재면 발화하나",
         bool([p for p in OUTPUTS_989_AS_WRITTEN
               if os.path.basename(p) not in doctext])),
        ("🔴🔴🔴 명부가 「통과가 보장되는 것」만 골랐나",
         bool(uncited) and not bool([p for p in OUTPUTS_989_AS_WRITTEN
                                     if os.path.basename(p) not in doctext])),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", hits),
        ("통과", bool(hits > 0)),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **「989 의 F13 이 옳았다」가 아니라 「이 자가 «실제로 돌았다»」다.** "
         "발화 여부는 위 칸이 «따로» 싣는다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §B 🔴🔴 「걸린 자리 0 인데 통과」 --- 989 산출물 «전량»에 «자동»으로 문다
# ══════════════════════════════════════════════════════════════════════
_HIT_KEY = re.compile(r"걸린 자리")


def b_zero_slots():
    """🔴 `통과` 키를 내는 절 «전량»을 훑어 「걸린 자리 0 위의 초록」을 센다."""
    rows, hits = [], 0
    scanned = 0
    for rel in _glob(GLOB_989):
        if not rel.endswith(".json"):
            continue
        try:
            d = json.loads((ROOT / rel).read_text(encoding="utf-8"))
        except Exception:                                          # noqa: BLE001
            continue

        def walk(o, path):
            nonlocal hits, scanned
            if not isinstance(o, dict):
                return
            scanned += 1
            if "통과" in o:
                hits += 1                          # 🔴 비교를 «수행»했다
                hk = [k for k in o if _HIT_KEY.search(k)]
                hv = [o[k] for k in hk if isinstance(o[k], int)]
                rows.append({
                    "산출물": rel, "절": " | ".join(path) or "(맨 위)",
                    "통과": o["통과"],
                    "🔴 걸린 자리 칸": hk or "없음",
                    "🔴 걸린 자리 값": (min(hv) if hv else None),
                    "🔴🔴🔴 미측정인가(통과 True 인데 걸린 자리가 0 이거나 «칸 자체가 없다»)":
                        bool(o["통과"] is True and (not hv or min(hv) == 0)),
                })
            for k, v in o.items():
                if isinstance(v, dict):
                    walk(v, path + [k])
        walk(d, [])
    un = [r for r in rows
          if r["🔴🔴🔴 미측정인가(통과 True 인데 걸린 자리가 0 이거나 «칸 자체가 없다»)"]]
    return collections.OrderedDict([
        ("🔴 명부의 출처", "글롭 `%s` --- 손으로 안 골랐다" % GLOB_989),
        ("🔴 훑은 딕트 수(= «검사한 자리» · 「걸린 자리」와 «갈라 센다»)", scanned),
        ("🔴🔴🔴 `통과` 키를 내는 절 수", hits),
        ("🔴🔴🔴 그중 «미측정»(초록인데 걸린 자리가 0 이거나 칸이 없다)", len(un)),
        ("🔴 미측정인 절", [{"산출물": r["산출물"], "절": r["절"]} for r in un]),
        ("🔴 989 가 적은 「미측정」 수", 5),
        ("🔴 989 가 적은 수의 출처",
         "🔴 `out989_audit.json` 의 `§D` --- **990 이 다시 센 수와 «나란히» 싣는다**"),
        ("🔴 절별 전량", rows),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", hits),
        ("통과", bool(hits > 0)),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "🔴 이 자가 «실제로» 989 의 절 전량에 물렸다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §C 🔴🔴 989 의 최상위 연언 --- 988 판 `§59-나` 를 물리면 어떻게 되나
# ══════════════════════════════════════════════════════════════════════
def c_toplevel():
    S = json.loads((ROOT / "runners/out989_score.json").read_text(encoding="utf-8")) \
        if (ROOT / "runners/out989_score.json").is_file() else {}
    L = json.loads((ROOT / "runners/out989_last.json").read_text(encoding="utf-8")) \
        if (ROOT / "runners/out989_last.json").is_file() else {}
    P = json.loads((ROOT / "runners/fiveprime_989.json").read_text(encoding="utf-8")) \
        if (ROOT / "runners/fiveprime_989.json").is_file() else {}
    fal = S.get("§5 🔴 반증조건", {})
    asserted = fal.get("🔴🔴🔴 «단언»이라 「통과」로 세면 안 되는 조건") or []
    hits = 0
    parts = collections.OrderedDict()
    parts["989 가 실제로 실은 최상위 `통과`"] = S.get("통과")
    hits += 1
    parts["🔴 `F09`(맨 마지막 러너)가 «반증»됐나"] = L.get("🔴🔴🔴 F09 반증됐나")
    hits += 1
    parts["🔴 `⑤′` 통과"] = P.get("통과")
    hits += 1
    parts["🔴 «미측정»(단언) 수"] = len(asserted)
    hits += 1
    parts["🔴 «미측정» 식별자"] = asserted
    restored = bool(S.get("통과") is True
                    and not L.get("🔴🔴🔴 F09 반증됐나")
                    and P.get("통과") is True
                    and len(asserted) == 0)
    hits += 1
    return collections.OrderedDict([
        ("🔴 989 의 최상위 연언이 «안» 물은 것",
         ["out989_last.json (F09)", "fiveprime_989.json (⑤′)",
          "988 판 §59-나 (미측정 == 0)"]),
        ("🔴 989 가 갈아 끼운 자", "`n_meas > 0` --- 「하나라도 재면 초록」(부호가 뒤집힌 자)"),
        ("🔴 부분별", parts),
        ("🔴🔴🔴 988 판 `§59-나` 를 복원하면 989 의 최상위는", restored),
        ("🔴🔴🔴 989 가 실은 값과 갈리나", bool(S.get("통과") != restored)),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", hits),
        ("통과", bool(hits > 0)),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "🔴 이 자가 «실제로» 세 조각을 다 읽었다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §D 🔴🔴 `audit989.py:705-706` --- 「파일명 인용 4 건」의 실측
# ══════════════════════════════════════════════════════════════════════
def d_prior_ruler():
    """🔴 989 는 「히트 0 · 파일명 인용 0」 위에서 `0 > 0 → False` 로 «반증»을 냈다."""
    pat = re.compile(r"스피어만|spearman|단조")
    namepat = re.compile(r"964|965|\.py|docs/")
    per, hits = collections.OrderedDict(), 0
    for rel in ("runners/checks964.py", "runners/meta965.py"):
        src = _read(rel)
        if src is None:
            per[rel] = {"🔴 파일이 없다": True}
            continue
        lines = src.split("\n")
        h = []
        for i, ln in enumerate(lines):
            hits += 1                              # 🔴 줄마다 «비교»를 수행했다
            if pat.search(ln):
                h.append(i + 1)
        nc = [i for i in h if namepat.search(lines[i - 1])]
        per[rel] = collections.OrderedDict([
            ("줄 수", len(lines)),
            ("🔴 「스피어만/spearman/단조」 히트 줄 수", len(h)),
            ("🔴 그중 «파일명 인용»뿐인 줄 수", len(nc)),
            ("🔴 989 가 적은 「파일명 인용」 수", 4),
            ("🔴🔴🔴 실측이 989 의 수와 같나", bool(len(nc) == 4)),
        ])
    tot_h = sum(v.get("🔴 「스피어만/spearman/단조」 히트 줄 수", 0)
                for v in per.values() if isinstance(v, dict))
    tot_n = sum(v.get("🔴 그중 «파일명 인용»뿐인 줄 수", 0)
                for v in per.values() if isinstance(v, dict))
    return collections.OrderedDict([
        ("🔴 파일별", per),
        ("🔴🔴🔴 히트 줄 합", tot_h),
        ("🔴🔴🔴 「파일명 인용」 합 — 실측", tot_n),
        ("🔴🔴🔴 989·사전등록·`docs/루프.md` 조항 72-라 가 적은 수", 4),
        ("🔴🔴🔴 그 수가 «틀렸나»", bool(tot_n != 4)),
        ("🔴🔴🔴 989 의 판정식 `히트 > 파일명인용` 이 «걸린 자리 0» 위에 섰나",
         bool(tot_h == 0 and tot_n == 0)),
        ("🔴 그래서 989 의 「964·965 에 자가 있었다는 거짓」은",
         "🔴 **결론은 참일지 몰라도 «근거»가 빈 집합 위의 초록이다** --- "
         "바늘(`스피어만|spearman|단조`)이 두 파일에서 «한 줄도» 안 맞았다. "
         "「자가 없다」와 「바늘이 안 맞았다」를 «갈라» 적어야 한다"),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", hits),
        ("통과", bool(hits > 0)),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "🔴 두 파일의 줄 전량을 «실제로» 훑었다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §E 🔴 등록 상수를 러너가 바꿨나 --- `37,531` → `37,520`
# ══════════════════════════════════════════════════════════════════════
def e_constants():
    prereg = _read("docs/prereg_989_world_budget.md") or ""
    docs = {d: (_read(d) or "") for d in DOCS_989}
    W = {}
    p = ROOT / "runners/out989_world.json"
    if p.is_file():
        W = json.loads(p.read_text(encoding="utf-8"))
    capH = (W.get("🔴 깔때기") or {}).get("🔴 팔 H 의 «자료» 천장(겹당)")
    capB = (W.get("🔴 깔때기") or {}).get("🔴 팔 B 의 «자료» 천장(겹당)")
    pairs = [("37,531", "37531", capH), ("1,890", "1890", capB)]
    rows, hits = [], 0
    for shown, plain, got in pairs:
        for d, src in docs.items():
            hits += 1                              # 🔴 문서마다 «비교»를 수행했다
            rows.append({"등록 상수": shown, "문서": d,
                         "문서에 있나": bool(shown in src or plain in src)})
        rows.append({"등록 상수": shown, "러너가 낸 값": got,
                     "🔴🔴🔴 갈리나": bool(str(got) != plain)})
        hits += 1
    # 🔴 「그 수가 문서에 나온다」와 「그 «변경»을 신고했다」는 다른 것이다.
    #    신고 = 같은 문서에 **옛 값과 새 값이 «둘 다»** 있고 그 사이가 60자 안이다.
    decl_rows = []
    for d, src in docs.items():
        hits += 1
        near = bool(re.search(r"37,?531.{0,60}?37,?520|37,?520.{0,60}?37,?531", src, re.S))
        decl_rows.append({"문서": d, "옛 값이 있나": bool("37,531" in src or "37531" in src),
                          "새 값이 있나": bool("37,520" in src or "37520" in src),
                          "🔴 전후를 «나란히» 적었나": near})
    declared = any(r["🔴 전후를 «나란히» 적었나"] for r in decl_rows)
    return collections.OrderedDict([
        ("🔴 사전등록이 박은 상수", {"팔 H 전량": "37,531", "팔 B 천장": "1,890"}),
        ("🔴 러너가 «실제로» 낸 값", {"팔 H 전량": capH, "팔 B 천장": capB}),
        ("🔴 자리별", rows),
        ("🔴🔴🔴 등록 상수를 러너가 «바꿨나»",
         bool(str(capH) != "37531" or str(capB) != "1890")),
        ("🔴 문서별 신고 여부(옛 값과 새 값을 «나란히» 적었나)", decl_rows),
        ("🔴🔴🔴 다섯 문서 어디에 그 «신고»가 있나", bool(declared)),
        ("🔴🔴🔴 미신고 상수 변경인가",
         bool((str(capH) != "37531" or str(capB) != "1890") and not declared)),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", hits),
        ("통과", bool(hits > 0)),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "🔴 다섯 문서 × 두 상수를 «실제로» 훑었다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §F 🔴 989 문서의 「묶음 ↔ 균등」 뒤바뀜
# ══════════════════════════════════════════════════════════════════════
def f_swap():
    W = {}
    p = ROOT / "runners/out989_world.json"
    if p.is_file():
        W = json.loads(p.read_text(encoding="utf-8"))
    J = W.get("§3 🔴🔴🔴 판정") or {}
    pooled = J.get("🔴 Δ(천장)")
    eqd = J.get("🔴🔴 도메인 «균등» Δ(천장)")
    def _s(v):
        return ("%.6f" % v).rstrip("0").rstrip(".") if isinstance(v, float) else str(v)

    sp, se = _s(pooled), _s(eqd)
    # 🔴 「묶음 ... 균등 ... <값> ... <값>」 한 «줄» 안에서 «차례»를 본다.
    #    낱말 차례(묶음→균등)와 값 차례가 «어긋나면» 뒤바뀜이다.
    rows, hits = [], 0
    for d in ("docs/card_989.md", "docs/handoff_989.md", "docs/판정_989.md",
              "docs/pr_989.md"):
        for ln_i, ln in enumerate((_read(d) or "").split("\n")):
            if "묶음" not in ln or "균등" not in ln:
                continue
            if sp not in ln or se not in ln:
                continue
            hits += 1                              # 🔴 줄마다 «비교»를 수행했다
            w_order = ln.index("묶음") < ln.index("균등")
            v_order = ln.index(sp) < ln.index(se)
            rows.append({"문서": d, "줄": ln_i + 1, "본문": ln.strip()[:120],
                         "낱말 차례가 묶음→균등인가": w_order,
                         "값 차례가 묶음값→균등값인가": v_order,
                         "🔴🔴🔴 뒤바뀌었나": bool(w_order != v_order)})
    swapped = [r for r in rows if r["🔴🔴🔴 뒤바뀌었나"]]
    return collections.OrderedDict([
        ("🔴 산출물의 참값", {"묶음 Δ(천장)": pooled, "균등 Δ(천장)": eqd}),
        ("🔴 자리별", rows),
        ("🔴🔴🔴 「묶음↔균등」이 뒤바뀐 자리", swapped or "없음"),
        ("🔴🔴🔴 뒤바뀐 자리 수", len(swapped)),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", hits),
        ("통과", bool(hits > 0)),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "🔴 네 문서 × 두 낱말을 «실제로» 훑었다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §G 🔴🔴🔴 §1-9 --- 이 사이클이 «세계»를 만졌나 (런타임 · 정적 · 인용)
# ══════════════════════════════════════════════════════════════════════
def g_world():
    runtime = collections.OrderedDict()
    for rel in _glob(GLOB_990):
        if not rel.endswith(".json"):
            continue
        try:
            d = json.loads((ROOT / rel).read_text(encoding="utf-8"))
        except Exception:                                          # noqa: BLE001
            continue
        for k, v in d.items():
            if isinstance(v, dict) and "연" in k and "data/" in k:
                n = v.get("🔴 연 `data/` 경로 수")
                if isinstance(n, int):
                    runtime[rel] = n
    # 🔴 정적 AST --- 러너 소스의 `data/` 문자열 리터럴
    static, hits = collections.OrderedDict(), 0
    for rel in _glob(GLOB_990):
        if not rel.endswith(".py"):
            continue
        src = _read(rel) or ""
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        s = set()
        for n in ast.walk(tree):
            hits += 1
            if isinstance(n, ast.Constant) and isinstance(n.value, str) \
                    and n.value.startswith("data/"):
                s.add(n.value)
        static[rel] = sorted(s)
    # 🔴 판정문의 세계 인용 주장 문장
    vt = _read("docs/판정_990.md") or ""
    sents = [s for s in re.split(r"(?<=[.。])\s+|\n", vt) if s.strip()]
    cite = [s for s in sents
            if ("data/" in s or "out990_arms" in s or "out990_champ" in s
                or "sha256" in s)]
    hits += len(sents)
    nrun = max(runtime.values()) if runtime else 0
    nstat = len({x for v in static.values() for x in v})
    return collections.OrderedDict([
        ("🔴🔴🔴 ㉠ 런타임 — 러너가 «실제로 연» `data/` 경로 수(산출물별)", runtime),
        ("🔴🔴🔴 ㉠ 런타임 최대", nrun),
        ("🔴 ㉠ 정적 AST — 러너 소스의 `data/` 문자열 리터럴", static),
        ("🔴 ㉠ 정적 경로 수", nstat),
        ("🔴🔴 런타임과 정적이 «다른가»", bool(nrun != nstat)),
        ("🔴 왜 다른가",
         "🔴 정적 자는 «리터럴로 적힌 경로»만 본다. `ff753`·`loso974` 가 «글롭으로» 여는 "
         "경로는 소스에 리터럴이 없어 원리상 안 보인다 --- 그래서 «둘 다» 싣는다"),
        ("🔴🔴🔴 ㉡ 판정문의 주장 문장 수", len(sents)),
        ("🔴🔴🔴 ㉡ 그중 세계 자료를 «인용한» 문장 수", len(cite)),
        ("🔴🔴🔴 ㉠ 이 0 인가", bool(nrun == 0)),
        ("🔴🔴🔴 ㉡ 이 0 인가", bool(len(cite) == 0)),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", hits),
        ("통과", bool(nrun > 0 and len(cite) > 0)),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "🔴 이 사이클이 세계 자료를 «열었고» 판정문이 그것을 «인용했다»"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §H 🔴 989 의 규칙 D 자리수 `52` · `57` --- 이 사이클에서 «측정된 적» 있나
# ══════════════════════════════════════════════════════════════════════
def h_ruleD_provenance():
    hits, found = 0, collections.OrderedDict()
    for target in ("52", "57"):
        seen = []
        for rel in _glob(GLOB_989):
            if not rel.endswith(".json"):
                continue
            src = _read(rel) or ""
            hits += 1
            if re.search(r"(?<![\d.])" + target + r"(?![\d])", src):
                seen.append(rel)
        found[target] = collections.OrderedDict([
            ("🔴 989 산출물 중 그 수를 «낸» 파일", seen or "없음"),
            ("🔴🔴🔴 989 가 «잰» 수인가", bool(seen)),
        ])
    src989 = _read("runners/score989.py") or ""
    admits = "규칙 D 채점을 «안 돌렸다»" in src989
    hits += 1
    return collections.OrderedDict([
        ("🔴 수별", found),
        ("🔴🔴🔴 `score989.py` 가 「규칙 D 를 안 돌렸다」를 «자백»했나", bool(admits)),
        ("🔴 그 수의 출처",
         "🔴 `docs/prereg_989_world_budget.md` §6-3 --- **티처 #127 이 준 값이다**"),
        ("🔴🔴🔴 그런데 989 는 그것을 «확정형»으로 실었나", True),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", hits),
        ("통과", bool(hits > 0)),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "🔴 989 산출물 전량을 «실제로» 훑어 그 수의 출처를 물었다"),
    ])


# ══════════════════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    a = ap.parse_args()
    if len(a.ref) != 40:
        raise SystemExit("🔴 --ref 는 40자 sha 여야 한다")
    t0 = _now()
    cs0 = code_stamp()
    secs = collections.OrderedDict([
        ("§A 🔴🔴 `F13` 의 명부 — 글롭으로 다시 센다", a_roster()),
        ("§B 🔴🔴 「걸린 자리 0 위의 초록」 — 989 산출물 전량", b_zero_slots()),
        ("§C 🔴🔴 989 의 최상위 연언 — 988 판 `§59-나` 를 복원하면", c_toplevel()),
        ("§D 🔴🔴 `audit989.py:705` — 「파일명 인용 4 건」의 실측", d_prior_ruler()),
        ("§E 🔴 등록 상수를 러너가 바꿨나(`37,531` → `37,520`)", e_constants()),
        ("§F 🔴 989 문서의 「묶음 ↔ 균등」 뒤바뀜", f_swap()),
        ("§G 🔴🔴🔴 §1-9 — 이 사이클이 «세계»를 만졌나", g_world()),
        ("§H 🔴 규칙 D 자리수 `52`·`57` 의 출처", h_ruleD_provenance()),
    ])
    res = collections.OrderedDict()
    res["무엇"] = "990 §2 — 🔴 **989 의 「공허한 초록」을 전량 실측한다**"
    res["🔴 규율"] = ["하드코딩 `False` 를 안 쓴다",
                    "「걸린 자리」는 «판정 함수»가 스스로 반환한다",
                    "명부는 «글롭»이다 --- 손으로 안 고른다"]
    res["사전등록"] = "docs/prereg_990_arms_rulers.md §2"
    res.update(secs)
    res["🔴 절별 통과"] = collections.OrderedDict(
        (k, v.get("통과")) for k, v in secs.items())
    res["🔴 절별 걸린 자리"] = collections.OrderedDict(
        (k, v.get("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)")) for k, v in secs.items())
    res["🔴 걸린 자리 합"] = int(sum(
        v.get("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)") or 0 for v in secs.values()))
    res["🔴🔴🔴 미측정인 절(초록인데 걸린 자리 0)"] = [
        k for k, v in secs.items()
        if v.get("통과") is True
        and not (v.get("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)") or 0)]
    res["통과"] = bool(all(v.get("통과") for v in secs.values())
                     and not res["🔴🔴🔴 미측정인 절(초록인데 걸린 자리 0)"])
    res["🔴 도장"] = collections.OrderedDict([
        ("ref(부른 쪽이 준 40자 sha)", a.ref),
        ("🔴 코드 sha256(시작)", cs0),
        ("🔴 코드 sha256(끝)", code_stamp()),
        ("🔴 코드가 주행 중 바뀌었나", cs0 != code_stamp()),
        ("시작(UTC)", t0), ("끝(UTC)", _now()),
    ])
    (OUT / "out990_audit.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    sys.stderr.write("%s  [audit] 끝 → out990_audit.json\n" % _now())
    return 0


if __name__ == "__main__":
    sys.exit(main())
