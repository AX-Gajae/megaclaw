# -*- coding: utf-8 -*-
"""노트 905 — 66짝이 식3 하나에서만 떨어지는가(팔 ㄱ) · 조건의 판정 단위는 짝인가 도메인인가(팔 ㄴ).

사전등록: `docs/prereg_905_cond.md`
          (커밋 9a8d42a04639265abfbd6cf1e0cec81538052a58 · 2026-08-11T08:22:38+09:00)

물음의 출처: 팔 ㄱ = 이슈 **#151**(티처 #67 C1·C2·M11·M12) · 팔 ㄴ = **내가 골랐다**(사전등록 §1).

🔴 **채점기를 한 글자도 안 고친다** — `ident901.py`·`ident902.py`·`inv901.py`·`pairboot.py` 는
   **읽기만** 한다. 등급을 다시 안 매긴다. `out902_identify.json:판정 표` 의 **라벨을 읽어 센다**.
🔴 **효과 크기를 안 낸다** → 규약 47 의 구간이 없다(사전등록 §2 에 미리 못 박았다).
🔴 **배선 검사는 각 assert 를 국소적으로 시험한다**(티처 #67 m3) — `OFF` 로 검사 하나만 끄고
   같은 파손 입력을 다시 넣어 **다른 검사가 대신 발화하지 않는지** 본다.
🔴 **심는 결함은 전부 입력 파손이다** — 시험 전용 인자를 안 쓴다(티처 #67 m2).

실행: python3 runners/cond905.py
"""
from __future__ import annotations

import copy
import datetime as dt
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runners"))

# 🔴 도장은 **실행 시작**에서 찍는다(티처 #64 C3)
T0 = time.time()
START = dt.datetime.now().isoformat(timespec="seconds")

from inv901 import sha                                    # noqa: E402  (읽기 전용)

PREREG = {"파일": "docs/prereg_905_cond.md",
          "커밋": "9a8d42a04639265abfbd6cf1e0cec81538052a58",
          "커밋 시각": "2026-08-11T08:22:38+09:00"}

SRC902 = ROOT / "runners/out902_identify.json"
PREREG_MD = ROOT / "docs/prereg_905_cond.md"
LEDGER = ROOT / "data/lab/denominator.json"
OUT = ROOT / "runners/out905_cond.json"

DENOMS = ("D1", "D2", "D3", "D4")
TYPES = ("b", "c", "l", "d")
LABELS = ("예", "아니오", "모른다")

# 산출물의 조건 키 이름(902 가 쓴 그대로 · 이름을 바꾸지 않는다)
COND = {
    "식1": "식1 처치/대조",
    "식2": "식2 사전 관측(약·생산자 단위)",
    "식3": "식3 역인과 아님",
    "식4": "식4 교란 관측",
}

# 🔴 생산 함수 진입 계수기 — 배선 검사가 **그 함수를 실제로 불렀다**는 유일한 증거
CALLS: Counter = Counter()

# 🔴 국소 시험용 — 이 집합에 든 검사 **하나만** 꺼진다(전역 무력화가 아니다)
OFF: set[str] = set()


def _A(aid: str, cond: bool, msg: str) -> None:
    """번호 붙은 검사. `OFF` 에 그 번호가 있으면 **그 하나만** 꺼진다."""
    if aid in OFF:
        return
    if not cond:
        raise AssertionError(f"[{aid}] {msg}")


# ══ 생산 함수 ══════════════════════════════════════════════════════════
def read_pairs(table: dict) -> list[dict]:
    """`판정 표` → 짝 한 줄씩. 🔴 등급을 다시 안 매긴다 — 라벨을 **읽는다**.

    R1 조건 라벨이 셋(예/아니오/모른다) 밖이면 죽는다 — 「없다」를 조용히 한 칸으로 안 센다
    R2 형이 넷 밖이면 죽는다
    R3 분모 딱지가 넷 밖이면 죽는다
    """
    CALLS["read_pairs"] += 1
    rows = []
    for dom, dv in table.items():
        pairs = dv.get("짝") or {}
        for col, p in pairs.items():
            lab = {k: p.get(v) for k, v in COND.items()}
            for k, v in lab.items():
                _A("R1", v in LABELS,
                   f"{dom}/{col}: {k} 라벨이 셋 밖이다/없다 — {v!r}")
            typ = p.get("형")
            _A("R2", typ in TYPES, f"{dom}/{col}: 형이 넷 밖이다/없다 — {typ!r}")
            g1 = p.get("식1 근거") or {}
            den = g1.get("분모") if isinstance(g1, dict) else None
            _A("R3", den in DENOMS,
               f"{dom}/{col}: 분모 딱지가 넷({'/'.join(DENOMS)}) 밖이다/없다 — {den!r}")
            rows.append({
                "도메인": dom, "짝": col, "티어": p.get("등급"),
                "등급": p.get("등급(식별)"), "형": typ, "분모": den,
                "식3 근거": p.get("식3 근거"),
                **lab,
            })
    return rows


def cross_by_condition(rows: list[dict], a: str, b: str) -> dict:
    """두 조건의 교차표. 🔴 **X1 합이 분모와 다르면 죽는다**(조항 60 — 분모가 새는 길을 막는다)."""
    CALLS["cross_by_condition"] += 1
    c: Counter = Counter()
    for r in rows:
        if r.get(a) in LABELS and r.get(b) in LABELS:
            c[(r[a], r[b])] += 1
    tot = sum(c.values())
    _A("X1", tot == len(rows),
       f"교차표 합 {tot} ≠ 분모 {len(rows)} — 라벨이 셋 밖인 짝이 조용히 빠졌다")
    return {"분모": len(rows),
            "표": {f"{a}={x} × {b}={y}": c[(x, y)]
                  for x in LABELS for y in LABELS if c[(x, y)]},
            f"{a} 주변": dict(Counter(r[a] for r in rows if r.get(a) in LABELS)),
            f"{b} 주변": dict(Counter(r[b] for r in rows if r.get(b) in LABELS))}


_TIMEFIELDS = re.compile(r"도메인에 있는 시점 필드[^:]*:\s*(.+)$")


def why_unknown(rows: list[dict]) -> dict:
    """🔴 식3=「모른다」인 짝이 **무엇을 안 적어 뒀는지**를 열 이름으로 뽑는다.

    U1 「모른다」인 짝이 하나도 없으면 죽는다 — **빈 것을 부정으로 읽지 않는다**(조항 59)
    U2 근거에서 「도메인에 있는 시점 필드」 목록을 못 뽑으면 죽는다 — 조용한 빈 목록 금지
    """
    CALLS["why_unknown"] += 1
    unk = [r for r in rows if r.get("식3") == "모른다"]
    _A("U1", len(unk) > 0,
       "식3=「모른다」인 짝이 0 이다 — 「없다」인지 「라벨을 못 읽었다」인지 갈리지 않는다")
    per, forms, domfields = [], Counter(), {}
    for r in unk:
        why = r.get("식3 근거")
        s = why if isinstance(why, str) else ""
        m = _TIMEFIELDS.search(s)
        got = []
        if m:
            got = [t.split("=")[0].strip() for t in m.group(1).split(",") if t.strip()]
        _A("U2", bool(got),
           f"{r['도메인']}/{r['짝']}: 근거에서 시점 필드 목록을 못 뽑았다 — {s[:80]!r}")
        # 🔴 문형: 수를 지운 뼈대만 센다
        forms[re.sub(r"[^가-힣A-Za-z]+", "·", s)[:60]] += 1
        # 🔴 지목된 열 — 문형이 지시적("이 열")이면 그 짝 자신의 열로 푼다
        deictic = "이 열의" in s
        named = r["짝"] if deictic else None
        per.append({"도메인": r["도메인"], "🔴 안 적어 둔 열(개입 열)": r["짝"],
                    "형": r["형"], "등급": r["등급"], "식1": r["식1"],
                    "🔴 도메인이 대신 가진 시점 필드": got,
                    "지시적 문형(「이 열의」)": deictic,
                    "근거가 지목한 열(풀어서)": named})
        domfields.setdefault(r["도메인"], got)
    mism = sum(1 for x in per if x["근거가 지목한 열(풀어서)"] != x["🔴 안 적어 둔 열(개입 열)"])
    names = sorted({n for v in domfields.values() for n in v})
    return {
        "🔴 모른다 짝 수(분모)": len(unk),
        "짝별": per,
        "🔴 어긋남(근거가 지목한 열 ≠ 짝 자신의 개입 열)": mism,
        "🔴 근거 문형 가짓수": len(forms),
        "근거 문형": dict(forms),
        "🔴 지시적 문형인 짝 수": sum(1 for x in per if x["지시적 문형(「이 열의」)"]),
        "도메인별 「대신 가진 시점 필드」": domfields,
        "🔴 그 시점 필드 이름 전량(합집합)": names,
        "🔴 그 이름의 가짓수": len(names),
        "도메인 수(분모)": len(domfields),
    }


def unit_of_condition(rows: list[dict], keys: tuple[str, ...]) -> dict:
    """🔴 팔 ㄴ — 각 조건이 **도메인 안에서 상수인가**(도메인의 성질인가 짝의 성질인가).

    N1 도메인이 12 가 아니면 죽는다 — 도메인이 조용히 빠지면 「상수」가 공짜로 참이 된다
    """
    CALLS["unit_of_condition"] += 1
    doms = sorted({r["도메인"] for r in rows})
    _A("N1", len(doms) == 12,
       f"도메인 수가 {len(doms)} 다(12 이어야 한다) — 빠진 도메인은 상수 판정을 공짜로 만든다")
    out = {"도메인 수(분모)": len(doms), "짝 수(분모)": len(rows), "조건별": {}}
    for k in keys:
        const, varying, dof = 0, [], 0
        for d in doms:
            vals = {r.get(k) for r in rows if r["도메인"] == d}
            dof += len(vals)
            if len(vals) == 1:
                const += 1
            else:
                varying.append(d)
        out["조건별"][k] = {
            "🔴 도메인 안 상수인 도메인 수": const,
            "분모(도메인)": len(doms),
            "도메인 안에서 변하는 도메인": varying,
            "🔴 실효 자유도(도메인별 값 가짓수 합)": dof,
            "🔴 짝으로 세면": len(rows),
            "🔴 짝의 성질인가": const < len(doms),
        }
    return out


# ══ 배선 검사 — 🔴 각 검사를 **국소적으로** 시험한다 ═════════════════════
def _probe(fn, *a, **kw):
    try:
        fn(*a, **kw)
        return False, "🔴 발화 안 함"
    except AssertionError as e:
        return True, f"AssertionError: {e}"


def wiring(table: dict, rows: list[dict]) -> dict:
    w = {"🔴 규약": ("검사는 생산 함수를 **부른다**(지역 복제본 금지). 증거는 진입 계수기 `CALLS`. "
                  "🔴 각 검사를 **하나만 꺼서** 다시 넣는다 — 다른 검사가 대신 발화하면 "
                  "국소 시험 실패다(티처 #67 m3). 🔴 심는 결함은 **전부 입력 파손**이다(m2)"),
         "검사": {}}

    def one(aid, fn, fnname, broken, clean, 심은것):
        before = CALLS[fnname]
        fired, msg = _probe(fn, *broken)                    # ㉮ 파손 · 전부 켬
        c1 = CALLS[fnname]
        OFF.add(aid)
        try:
            loc, locmsg = _probe(fn, *broken)               # ㉯ 파손 · 그 검사만 끔
        finally:
            OFF.discard(aid)
        c2 = CALLS[fnname]
        neg, negmsg = _probe(fn, *clean)                    # ㉰ 정상 · 전부 켬
        c3 = CALLS[fnname]
        w["검사"][aid] = {
            "부른 생산 함수": f"{fn.__qualname__}",
            "심은 결함(입력 파손)": 심은것,
            "㉮ 파손·전부 켬 — 발화": fired,
            "발화 메시지": msg,
            "🔴 ㉯ 파손·이 검사만 끔 — 발화": loc,
            "㉯ 메시지": locmsg,
            "🔴 국소 시험 통과(㉯ 가 발화 안 함)": (not loc),
            "㉰ 정상·전부 켬 — 발화": neg,
            "㉰ 메시지": negmsg if neg else "발화 안 함(정상)",
            "🔴 결함을 지우면 통과로 바뀌나": (fired and not neg),
            "진입 계수기 증가(㉮/㉯/㉰)": [c1 - before, c2 - c1, c3 - c2],
            "🔴 계수기가 셋 다 늘었나": (c1 > before and c2 > c1 and c3 > c2),
        }

    # ── R1 · read_pairs — 조건 라벨을 셋 밖으로
    t = copy.deepcopy(table)
    d0 = next(iter(t)); p0 = next(iter(t[d0]["짝"]))
    t[d0]["짝"][p0][COND["식3"]] = "몰?루"
    one("R1", read_pairs, "read_pairs", (t,), (table,),
        f"`판정 표/{d0}/짝/{p0}/{COND['식3']}` 을 셋 밖 라벨 `몰?루` 로 바꿨다")

    # ── R2 · read_pairs — 형을 지운다
    t = copy.deepcopy(table)
    t[d0]["짝"][p0].pop("형", None)
    one("R2", read_pairs, "read_pairs", (t,), (table,),
        f"`판정 표/{d0}/짝/{p0}/형` 을 지웠다")

    # ── R3 · read_pairs — 분모 딱지를 넷 밖으로
    t = copy.deepcopy(table)
    t[d0]["짝"][p0]["식1 근거"]["분모"] = "D9"
    one("R3", read_pairs, "read_pairs", (t,), (table,),
        f"`판정 표/{d0}/짝/{p0}/식1 근거/분모` 를 `D9` 로 바꿨다")

    # ── X1 · cross_by_condition — 라벨 하나를 셋 밖으로(합이 분모보다 작아진다)
    rb = [dict(r) for r in rows]
    rb[0]["식1"] = "X"
    one("X1", cross_by_condition, "cross_by_condition",
        (rb, "식1", "식3"), (rows, "식1", "식3"),
        "첫 짝의 식1 라벨을 셋 밖 `X` 로 바꿨다 — 교차표에서 조용히 빠진다")

    # ── U1 · why_unknown — 「모른다」를 전부 「예」로 바꾼다
    rb = [dict(r) for r in rows]
    for r in rb:
        if r.get("식3") == "모른다":
            r["식3"] = "예"
    one("U1", why_unknown, "why_unknown", (rb,), (rows,),
        "모든 짝의 식3=「모른다」를 「예」로 바꿨다 — 「모른다」가 0 이 된다")

    # ── U2 · why_unknown — 근거에서 시점 필드 목록을 없앤다
    rb = [dict(r) for r in rows]
    for r in rb:
        if r.get("식3") == "모른다":
            r["식3 근거"] = "설명 없음"
            break
    one("U2", why_unknown, "why_unknown", (rb,), (rows,),
        "첫 「모른다」 짝의 식3 근거를 `설명 없음` 으로 바꿨다 — 시점 필드 목록이 사라진다")

    # ── N1 · unit_of_condition — 도메인 하나를 통째로 뺀다
    drop = sorted({r["도메인"] for r in rows})[0]
    rb = [r for r in rows if r["도메인"] != drop]
    ck = tuple(COND.keys())
    one("N1", unit_of_condition, "unit_of_condition", (rb, ck), (rows, ck),
        f"도메인 `{drop}` 의 짝을 통째로 뺐다 — 도메인 수가 12 에서 준다")

    n = len(w["검사"])
    fired = sum(1 for v in w["검사"].values() if v["㉮ 파손·전부 켬 — 발화"])
    local = sum(1 for v in w["검사"].values() if v["🔴 국소 시험 통과(㉯ 가 발화 안 함)"])
    neg = sum(1 for v in w["검사"].values() if not v["㉰ 정상·전부 켬 — 발화"])
    flip = sum(1 for v in w["검사"].values() if v["🔴 결함을 지우면 통과로 바뀌나"])
    cnt = sum(1 for v in w["검사"].values() if v["🔴 계수기가 셋 다 늘었나"])
    w["🔴 분모(심은 결함 수)"] = n
    w["발화"] = fired
    w["🔴 국소 시험 통과"] = local
    w["음성 대조 통과"] = neg
    w["🔴 지우면 통과로 바뀐 수"] = flip
    w["🔴 계수기가 늘어난 수"] = cnt
    w["통과"] = (fired == n and local == n and neg == n and flip == n and cnt == n)
    return w


# ══ 원장 훑기 (사전등록 §5) ════════════════════════════════════════════
def ledger_scan() -> dict:
    d = json.loads(LEDGER.read_text())
    needles = ["식3", "역인과", "관측 시점", "시점 필드", "reverse", "모른다"]
    out = {"원장 최상위 항목(분모)": len(d), "🔴 바늘": needles}
    hits = {}
    for nd in needles:
        h = [k for k, v in d.items()
             if nd in k or nd in json.dumps(v, ensure_ascii=False)]
        hits[nd] = h
        out[f"바늘 `{nd}` 에 걸린 항목 수"] = len(h)
    uni = sorted(set().union(*hits.values()) if hits else set())
    out["🔴 합집합(이 물음에 걸리는 옛 항목 수)"] = len(uni)
    out["🔴 합집합 목록"] = uni
    core = sorted(set(hits["식3"]) | set(hits["역인과"]) | set(hits["관측 시점"]))
    out["🔴 좁은 바늘(식3·역인과·관측 시점) 합집합 수"] = len(core)
    out["🔴 좁은 바늘 목록"] = core
    out["🔴 903 은 여덟 · 904 는 넷을 찾았다"] = (
        "🔴 **그 수와 직접 안 잇는다** — 903 은 바늘 `entry_friction` 하나, "
        "904 는 물음에 맞춘 바늘 일곱을 둘로 나눠, 905 는 위 여섯 바늘로 세었다. "
        "**같은 이름의 다른 자다**(조항 60)")
    return out


# ══ §6 대조 — 🔴 하드코딩 금지(티처 #67 C5) ═════════════════════════════
def check_wording(verdict: str, section_head: str) -> dict:
    """사전등록 파일을 **읽어** §6 의 해당 갈래 뼈대를 뽑고 판정문과 기계로 댄다."""
    md = PREREG_MD.read_text()
    i = md.find(section_head)
    if i < 0:
        return {"찾았나": False, "🔴 판정": "사전등록에서 그 갈래를 못 찾았다"}
    seg = md[i + len(section_head):]
    j = seg.find("\n###")
    seg = seg[:j] if j > 0 else seg
    body = " ".join(ln.lstrip("> ").strip() for ln in seg.splitlines() if ln.strip().startswith(">"))

    def norm(s: str) -> str:
        """🔴 마크다운 강조(`**`·백틱)만 지운다 — 글자는 하나도 안 바꾼다."""
        return re.sub(r"\s+", " ", s.replace("**", "").replace("`", "")).strip()

    body = norm(body)
    vn = norm(verdict)
    frags = [f.strip(" .·,") for f in re.split(r"\{[^}]*\}", body)]
    frags = [f for f in frags if len(f) >= 6]
    pos, miss = 0, []
    for f in frags:
        k = vn.find(f, pos)
        if k < 0:
            miss.append(f)
        else:
            pos = k + len(f)
    return {"찾았나": True, "뼈대 조각 수(분모)": len(frags),
            "🔴 대조 전 정규화": "마크다운 강조(`**`·백틱)와 연속 공백만 지웠다 — 글자는 안 바꿨다",
            "🔴 순서대로 다 들어 있나": not miss, "빠진 조각": miss}


# ══ main ══════════════════════════════════════════════════════════════
def main():
    out = {
        "노트": 905,
        "사전등록": PREREG,
        "시작 시각": START,
        "물음의 출처": {
            "팔 ㄱ": "이슈 #151 (티처 #67 C1·C2·M11·M12)",
            "팔 ㄴ": "🔴 내가 골랐다 — 사전등록 §1. 티처·이슈·직전 노트가 이 형태로 지목한 적 없다"},
        "🔴 효과 크기": "없음 — 라벨 계수와 분모만. 그래서 규약 47 의 구간이 없다(사전등록 §2)",
        "🔴 채점기 무접촉": ("ident901.py · ident902.py · inv901.py · pairboot.py · quote901.py 를 "
                       "한 글자도 안 고쳤다. out902_identify.json:판정 표 를 읽기만 했다"),
        "🔴 자를 뗐다(⓪-가)": ("판 ρ(0.47034 · 문턱 0.00353 · 챔피언 유보 3,775)를 안 썼다. "
                        "대신 쓴 자: out902_identify.json:판정 표 의 조건 라벨 계수 + 분모 병기"),
        "코드 sha256": {
            "runners/cond905.py": sha(Path(__file__)),
            "runners/inv901.py": sha(ROOT / "runners/inv901.py"),
            "runners/ident902.py": sha(ROOT / "runners/ident902.py"),
        },
        "입력 sha256": {
            "runners/out902_identify.json": sha(SRC902),
            "docs/prereg_905_cond.md": sha(PREREG_MD),
            "data/lab/denominator.json": sha(LEDGER),
        },
    }

    out["0-가 원장이 이미 뭐라 했나"] = ledger_scan()

    table = json.loads(SRC902.read_text())["판정 표"]

    # ── ② 배선 검사 (측정보다 먼저) ─────────────────────────────────
    rows0 = read_pairs(table)
    before = dict(CALLS)
    w = wiring(table, rows0)
    out["2 배선 검사"] = w
    out["2 배선 검사"]["검사 전 계수기"] = before
    if not w["통과"]:
        out["🔴 중단"] = "배선 검사가 통과 못 했다 — 사전등록 §8 대로 측정을 안 한다"
        OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
        raise SystemExit("🔴 배선 검사 실패 — 측정 중단")

    # ── ③ 측정 ────────────────────────────────────────────────────
    rows = read_pairs(table)
    all_n = len(rows)
    sub66 = [r for r in rows if r["형"] != "d" and r["분모"] == "D3"]
    A1 = [r for r in rows if r["등급"] == "A" and r["티어"] == "T1"]

    # 3-가 · 66짝의 조건별 분포와 교차표
    ga = {
        "🔴 모집단": "(형≠d) ∧ (분모=D3) 인 짝",
        "🔴 수(분모)": len(sub66),
        "짝 전량(분모)": all_n,
        "🔴 §0 에서 받은 수(확인 — 예측 아님)": {
            f"{k} 분포": dict(sorted(Counter(r[k] for r in sub66).items()))
            for k in COND},
        "등급 분해": dict(sorted(Counter(r["등급"] for r in sub66).items())),
        "도메인 분해": dict(sorted(Counter(r["도메인"] for r in sub66).items())),
    }
    ga["🔴 식1 × 식3 교차표(아무도 안 센 수)"] = cross_by_condition(sub66, "식1", "식3")
    for a in ("식2", "식4"):
        ga[f"식1 × {a} 교차표"] = cross_by_condition(sub66, "식1", a)
    ga["식3 × 식4 교차표"] = cross_by_condition(sub66, "식3", "식4")

    # 🔴 「식3 하나뿐인가」 — 조건별로 몇 개가 걸리는지 짝마다 센다
    def fails(r):
        return [k for k in COND if r[k] != "예"]

    fail_sets = Counter(" + ".join(fails(r)) or "(없음 · 넷 다 예)" for r in sub66)
    only3 = [r for r in sub66 if fails(r) == ["식3"]]
    ga["🔴 짝마다 「예가 아닌 조건」의 조합 분포"] = dict(sorted(fail_sets.items()))
    ga["🔴 식3 **하나만** 걸리는 짝 수"] = len(only3)
    ga["🔴 식3 하나만 걸리는 짝의 식3 라벨"] = dict(
        sorted(Counter(r["식3"] for r in only3).items()))
    ga["🔴 걸리는 조건이 둘 이상인 짝 수"] = sum(
        1 for r in sub66 if len(fails(r)) >= 2)
    ga["🔴 넷 다 예인 짝 수(=A 가 됐어야 할 짝)"] = sum(1 for r in sub66 if not fails(r))
    ga["🔴 66 중 A 등급 수"] = sum(1 for r in sub66 if r["등급"] == "A")
    ga["🔴 이 사이클의 유일한 분모(티처 #67 C2)"] = (
        f"{ga['🔴 66 중 A 등급 수']}/{len(sub66)} — 「/21」이 아니다. "
        "분모 딱지는 짝이 아니라 도메인의 성질이라 21 안에는 반증 기회가 있는 짝이 하나도 없다")
    ga["🔴 A∧T1 21짝(대조군) 조건별 분포"] = {
        f"{k} 분포": dict(sorted(Counter(r[k] for r in A1).items())) for k in COND}
    ga["A∧T1 수(분모)"] = len(A1)
    out["3-가 팔 ㄱ · 66짝은 식3 하나에서만 떨어지는가"] = ga

    # 3-나 · 「모른다」가 무엇을 안 적어 뒀는가
    gb = why_unknown(sub66)
    gb["🔴 식1 통과분 안에서의 모른다 수"] = sum(
        1 for r in sub66 if r["식3"] == "모른다" and r["식1"] == "예")
    gb["🔴 식1 미통과분 안에서의 모른다 수"] = sum(
        1 for r in sub66 if r["식3"] == "모른다" and r["식1"] != "예")
    gb["🔴 분모가 다르다(조항 60)"] = (
        "「모른다 63」의 분모는 66 이고 「식1 예 54」의 분모도 66 이지만, "
        "「54 중 몇이 모른다인가」는 세 번째 수다 — 위 두 줄이 그 분해다")
    out["3-나 「모른다」는 무엇을 안 적어 뒀는가 (열 이름)"] = gb

    # 3-나′ 🔴 사후 집계 — 사전등록에 없는 절. **예측이 아니다**
    #      (티처 #67 M11: 「수가 강제하는데 안 들었다」를 안 되풀이하려고 넣는다.
    #       사후라는 사실을 절 이름에 박는다)
    없는도메인 = sorted(d for d, f in gb["도메인별 「대신 가진 시점 필드」"].items()
                    if f == ["없음"])
    있는도메인 = sorted(d for d, f in gb["도메인별 「대신 가진 시점 필드」"].items()
                    if f != ["없음"])
    only3_unk = [r for r in only3 if r["식3"] == "모른다"]
    gb2 = {
        "🔴 이 절은 사후 집계다": ("사전등록 §4 의 예측이 아니다. 이미 잰 라벨을 다시 묶었을 뿐이고 "
                          "모집단(66짝)을 안 바꿨다. **예측 명부에 안 올린다**"),
        "🔴 왜 넣나": ("판정문이 「모른다」라 적을 때, 그 「모른다」 안에 **「도메인에 시점 필드가 "
                   "아예 없다」와 「있는데 개입 열을 안 덮는다」가 섞여 있다.** 이 저장소가 "
                   "조항 59 로 갈라 온 셋을 한 칸 더 가른다"),
        "무리 ㄱ · 도메인에 시점 필드가 하나도 없다(「없다」)": {
            "도메인": 없는도메인, "도메인 수": len(없는도메인),
            "식3 하나만 걸리고 모른다 인 짝 수": sum(
                1 for r in only3_unk if r["도메인"] in 없는도메인),
            "66짝 중 그 도메인의 짝 수": sum(1 for r in sub66 if r["도메인"] in 없는도메인)},
        "무리 ㄴ · 시점 필드는 있는데 개입 열을 안 덮는다(「안 적어 뒀다」)": {
            "도메인": 있는도메인, "도메인 수": len(있는도메인),
            "식3 하나만 걸리고 모른다 인 짝 수": sum(
                1 for r in only3_unk if r["도메인"] in 있는도메인),
            "66짝 중 그 도메인의 짝 수": sum(1 for r in sub66 if r["도메인"] in 있는도메인),
            "도메인별 필드 이름": {d: gb["도메인별 「대신 가진 시점 필드」"][d]
                          for d in 있는도메인}},
        "🔴 합(분모 대조)": len(only3_unk),
        "🔴 못 잰 것": ("무리 ㄴ 의 필드 이름 중 `source`·`label_basis`·`ingested_from`·"
                   "`extraction_confidence`·`_page` 가 **정말 시점인지는 안 쟀다** — "
                   "902 가 그 이름들을 「시점 필드」로 부른 것을 옮겼을 뿐이다"),
    }
    out["3-나′ 🔴 사후 집계 — 「모른다」 안의 두 무리 (예측 아님)"] = gb2

    # 3-다 · 팔 ㄴ — 조건의 판정 단위
    keys = tuple(COND.keys()) + ("형", "분모", "등급")
    gc = unit_of_condition(rows, keys)
    gc["🔴 물음"] = ("식별 조건 넷의 판정 단위는 짝인가 도메인인가 — "
                  "즉 105짝은 105번의 독립 판정인가, 12개 도메인 사실의 복제인가")
    gc["🔴 도메인의 성질인 조건(12/12 상수)"] = [
        k for k, v in gc["조건별"].items() if v["🔴 도메인 안 상수인 도메인 수"] == 12]
    gc["🔴 짝의 성질인 조건"] = [
        k for k, v in gc["조건별"].items() if v["🔴 도메인 안 상수인 도메인 수"] < 12]
    gc["🔴 티처 #67 C2 재현(분모 딱지)"] = gc["조건별"]["분모"]["🔴 도메인 안 상수인 도메인 수"]
    out["3-다 팔 ㄴ · 조건의 판정 단위는 짝인가 도메인인가"] = gc

    # ── ④ 예측 판정 ───────────────────────────────────────────────
    x13 = ga["🔴 식1 × 식3 교차표(아무도 안 센 수)"]["표"]
    no_in_yes = x13.get("식1=예 × 식3=아니오", 0)
    no_in_no = x13.get("식1=아니오 × 식3=아니오", 0)
    unk_in_no = x13.get("식1=아니오 × 식3=모른다", 0)
    n_fail1 = sum(1 for r in sub66 if r["식1"] != "예")
    p1 = (no_in_no == 0 and unk_in_no == n_fail1)
    p2 = (gb["🔴 어긋남(근거가 지목한 열 ≠ 짝 자신의 개입 열)"] == 0)
    cb = gc["조건별"]
    p3 = (all(cb[k]["🔴 도메인 안 상수인 도메인 수"] == 12 for k in ("식2", "식3", "식4"))
          and cb["식1"]["🔴 도메인 안 상수인 도메인 수"] < 12)

    S0_받은 = [
        "66짝/식1 주변분포", "66짝/식2 주변분포", "66짝/식3 주변분포", "66짝/식4 주변분포",
        "A∧T1 21짝 조건별 주변분포", "(형≠d)∧D3 짝 수", "분모 딱지 12/12 도메인",
        "식3 근거의 문형",
    ]
    예측_키 = [
        "66짝/식1 × 식3 교차표",
        "모른다 근거가 지목한 열 ≠ 짝 자신의 개입 열 어긋남 수",
        "조건별 도메인 안 상수인 도메인 수",
    ]
    inter = sorted(set(S0_받은) & set(예측_키))
    p4 = (len(inter) == 0)

    out["0-나 §0 대 예측 교집합 (이슈 #152 처방 · 기계로 센다)"] = {
        "§0 에서 받았다고 자백한 사실 키": S0_받은,
        "예측이 주장하는 사실 키": 예측_키,
        "🔴 교집합": inter,
        "🔴 교집합 수": len(inter),
        "🔴 판정": ("교집합 0 — 예측 셋은 자백한 것에서 오지 않았다"
                 if p4 else "🔴 교집합이 비지 않았다 — 겹치는 예측은 「확인」으로 강등한다"),
        "🔴 「확인」으로만 세는 것(예측 아님)": [
            "66짝의 조건별 주변분포(티처 #67 C1 표)", "A∧T1 21 전량 예",
            "식3 근거의 문형 가짓수(표본 1을 이미 봤다)"],
    }

    out["4 예측 판정"] = {
        "P1 식3=아니오 가 전부 식1=예 쪽에 있다": {
            "식1=예 × 식3=아니오": no_in_yes,
            "식1=아니오 × 식3=아니오": no_in_no,
            "식1=아니오 × 식3=모른다": unk_in_no,
            "식1≠예 인 짝 수": n_fail1,
            "판정": "확인" if p1 else "🔴 반증"},
        "P2 근거가 지목한 열 == 짝 자신의 개입 열 (어긋남 0)": {
            "어긋남": gb["🔴 어긋남(근거가 지목한 열 ≠ 짝 자신의 개입 열)"],
            "분모": gb["🔴 모른다 짝 수(분모)"],
            "🔴 정직 표지": ("문형이 지시적(「이 열의」)인 짝이 "
                        f"{gb['🔴 지시적 문형인 짝 수']}/{gb['🔴 모른다 짝 수(분모)']} 다. "
                        "지시적이면 이 예측은 **원리상 반증되기 어렵다** — 약한 예측이었다"),
            "판정": "확인" if p2 else "🔴 반증"},
        "P3 식2·식3·식4 는 12/12 상수 · 식1 은 12 미만": {
            "식1 상수 도메인": cb["식1"]["🔴 도메인 안 상수인 도메인 수"],
            "식2 상수 도메인": cb["식2"]["🔴 도메인 안 상수인 도메인 수"],
            "식3 상수 도메인": cb["식3"]["🔴 도메인 안 상수인 도메인 수"],
            "식4 상수 도메인": cb["식4"]["🔴 도메인 안 상수인 도메인 수"],
            "분모": 12,
            "판정": "확인" if p3 else "🔴 반증"},
        "P4 §0 자백과 예측의 교집합 0": {
            "교집합 수": len(inter), "판정": "확인" if p4 else "🔴 반증"},
        "🔴 예측 수(분모)": 4,
        "🔴 확인": sum([p1, p2, p3, p4]),
    }

    # ── ⑤ 판정 (사전등록 §6 어법 그대로) ────────────────────────────
    M = sum(1 for r in only3 if r["식3"] == "모른다")
    X = sum(1 for r in only3 if r["식3"] == "아니오")
    names = gb["🔴 그 시점 필드 이름 전량(합집합)"]
    kA = ga["🔴 66 중 A 등급 수"]
    other = sorted({c for r in sub66 if fails(r) != ["식3"] and fails(r) for c in fails(r)}
                   - {"식3"})

    if len(only3) > 0 and len(only3) == sum(1 for r in sub66 if r["식1"] == "예"):
        vA = ("🔴 「고를 수 있는 짝이 하나도 없다」는 틀렸다 — "
              f"{len(only3)}짝이 있고, 그 전부가 식3 한 조건에서만 떨어진다"
              f"(모른다 {M} · 아니오 {X}). 없는 것은 짝이 아니라 개입 값의 관측 시점 필드다. "
              f"그 {M}건은 「없다」가 아니라 「모른다」이고, 모르는 내용은 열 이름으로 적을 수 있다 — "
              "짝마다 그 짝 자신의 개입 열이고, 도메인이 대신 가진 시점 필드는 "
              f"{', '.join(names)} 이며 개입 열을 안 덮는다. "
              f"🔴 그리고 이 사이클의 유일한 분모는 {kA}/{len(sub66)} 이다(「/21」이 아니다)")
        갈래A = "㉠"
    else:
        vA = (f"🔴 식3 하나가 아니다 — {len(sub66) - len(only3)}짝이 식3 밖의 조건"
              f"({', '.join(other) if other else '없음'})에서도 떨어진다. "
              "그러면 66 의 A=0 은 「관측 시점을 안 적어 뒀다」가 아니라 채점기의 구조이고, "
              "다음 팔은 수집기가 아니라 채점기다")
        갈래A = "㉡"

    domain_conds = [k for k in COND if cb[k]["🔴 도메인 안 상수인 도메인 수"] == 12]
    if domain_conds:
        vB = (f"🔴 식별 조건 넷 중 {len(domain_conds)}개는 짝의 성질이 아니라 도메인의 성질이다"
              "(12/12 도메인에서 도메인 안 상수). 그러므로 105짝은 105번의 독립 판정이 아니다 — "
              f"조건 {', '.join(domain_conds)}은 12번밖에 안 잰 것이고, "
              f"짝을 더 모아도 그 {len(domain_conds)}개는 원리상 안 움직인다. "
              "늘려야 하는 것은 짝이 아니라 도메인/수집기다")
        갈래B = "㉠"
    else:
        vB = ("🔴 네 조건 모두 도메인 안에서 변한다 — 105짝은 105번의 판정이다. "
              "티처 #67 C2 의 「분모 딱지는 도메인의 성질」은 분모 딱지 한 칸에 한정된 사실이고 "
              "조건 넷으로 넓혀지지 않는다")
        갈래B = "㉡"

    headA = ("### 팔 ㄱ — 갈래 ㉠" if 갈래A == "㉠" else "### 팔 ㄱ — 갈래 ㉡")
    headB = ("### 팔 ㄴ — 갈래 ㉠" if 갈래B == "㉠" else "### 팔 ㄴ — 갈래 ㉡")
    wa = check_wording(vA, headA)
    wb = check_wording(vB, headB)

    title = (f"🔴🔴 905 — 「짝이 하나도 없다」는 틀렸다: {len(only3)}짝이 있고 식3 하나에서만 "
             f"떨어진다(모른다 {M}). 그리고 조건 {len(domain_conds)}/4 는 짝이 아니라 도메인의 성질이다"
             ) if (갈래A == "㉠" and 갈래B == "㉠") else vA.split(". ")[0]

    out["5 판정"] = {
        "팔 ㄱ 갈래": 갈래A, "팔 ㄱ 판정문": vA,
        "팔 ㄴ 갈래": 갈래B, "팔 ㄴ 판정문": vB,
        "🔴 사전등록 §6 뼈대와 기계 대조(팔 ㄱ)": wa,
        "🔴 사전등록 §6 뼈대와 기계 대조(팔 ㄴ)": wb,
        "🔴 커밋 제목에 그대로 쓸 문장": title,
        "통과": bool(wa.get("🔴 순서대로 다 들어 있나") and wb.get("🔴 순서대로 다 들어 있나")),
    }

    out["6 못 잰 것 (🔴 「없다」가 아니다)"] = [
        "「도메인이 대신 가진 시점 필드」가 **정말 시점인가** — 이름만 읽었다. "
        "`source`·`label_basis` 같은 이름이 시점인지 아닌지는 **안 쟀다**(902 가 그렇게 부른 것을 옮겼다)",
        "식3 을 「예」로 바꾸려면 무엇을 수집해야 하는가 — 안 쟀다. 열 이름까지만이다",
        "효과 크기 · 구간 — 안 냈다(사전등록 §2 에 미리 못 박았다)",
        "A∧T1 21짝의 식3=예가 **몇 가지 근거**에서 오는가 — 근거 문자열의 가짓수를 A 쪽에서는 안 셌다",
        "KOSTAT 격자 생활인구 — 🔴 **안 받았다**(「없다」가 아니다 · ⓪-나)",
        "채점기 `ident902.py` 가 「시점 필드」로 인정하는 이름 규칙 — 코드를 안 읽었다(무접촉 규율)",
        "팝업·아이돌(D1 30짝) — 66 밖이라 팔 ㄱ 에서 안 봤다. 팔 ㄴ 에서는 105 전량을 봤다",
    ]
    out["🔴 계수기(생산 함수 진입 총계)"] = dict(CALLS)
    out["끝 시각"] = dt.datetime.now().isoformat(timespec="seconds")
    out["초"] = round(time.time() - T0, 3)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print("완료 →", OUT)
    print("배선", w["발화"], "/", w["🔴 분모(심은 결함 수)"],
          "국소", w["🔴 국소 시험 통과"], "통과", w["통과"])
    print("66짝", len(sub66), "· 식3 하나만", len(only3), "· 모른다", M, "· 아니오", X)
    print("팔 ㄴ 도메인의 성질인 조건", domain_conds)
    print("예측", out["4 예측 판정"]["🔴 확인"], "/ 4")


if __name__ == "__main__":
    main()
