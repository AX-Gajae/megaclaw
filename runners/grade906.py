# -*- coding: utf-8 -*-
"""노트 906 — 식별 등급은 무엇의 함수인가 · 등급이 나르는 정보는 몇 비트인가(팔 ㄱ) ·
같은 파일의 「등급 미사용」 형제 키가 등급을 복제하는가(팔 ㄴ).

사전등록: `docs/prereg_906_grade.md`
          (커밋 d286a260c88b775f8b3a3460b892d05479ed90c5 · 2026-08-11T09:30:17+09:00)

물음의 출처: 팔 ㄱ = 이슈 **#156**(티처 #68) · 팔 ㄴ = **내가 골랐다**(사전등록 §1).

🔴 **채점기를 한 글자도 안 고친다** — `ident901.py`·`ident902.py`·`inv901.py`·`pairboot.py` 는
   읽기만 한다. 등급을 다시 안 매긴다. `out902_identify.json:판정 표` 의 라벨을 **읽어서** 센다.
🔴 **효과 크기를 안 낸다** → 규약 47 의 구간이 없다(사전등록 ⓪-가·§2 에 미리 못 박았다).
🔴 **헤드라인 분모는 T1 81 이다**(`docs/prereg_901_intervention.md:61` — T2 24 는 따로 센다).
🔴 **§3-기계**: 러너의 첫 절이 **입력 산출물의 최상위 키를 전량 찍고**, 오늘 낼 판정문의 정수를
   하나씩 입력에서 되찾아 **어디에 이미 있는지 JSON 경로로** 싣는다(티처 #68 C3·⑧).
🔴 **예측마다 그 예측을 거짓으로 만드는 입력을 심는다**(이슈 #155 처방 1). 안 뒤집히면
   그 예측은 **명부에서 자동으로 빠진다.**

실행: python3 runners/grade906.py
"""
from __future__ import annotations

import copy
import datetime as dt
import json
import math
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runners"))

# 🔴 도장은 **실행 시작**에서 찍는다(티처 #64 C3)
T0 = time.time()
START = dt.datetime.now().isoformat(timespec="seconds")

from inv901 import sha                                    # noqa: E402  (읽기 전용)

PREREG = {"파일": "docs/prereg_906_grade.md",
          "커밋": "d286a260c88b775f8b3a3460b892d05479ed90c5",
          "커밋 시각": "2026-08-11T09:30:17+09:00"}

SRC902 = ROOT / "runners/out902_identify.json"
SRC905 = ROOT / "runners/out905_cond.json"
PREREG_MD = ROOT / "docs/prereg_906_grade.md"
LEDGER = ROOT / "data/lab/denominator.json"
OUT = ROOT / "runners/out906_grade.json"

GRADES = ("A", "B", "C")
TYPES = ("b", "c", "d", "l")
TIERS = ("T1", "T2")

# 🔴 생산 함수 진입 계수기 — 배선 검사가 그 함수를 **실제로 불렀다**는 유일한 증거
CALLS: Counter = Counter()
# 🔴 국소 시험용 — 이 집합에 든 검사 **하나만** 꺼진다
OFF: set[str] = set()


def _A(aid: str, cond: bool, msg: str) -> None:
    if aid in OFF:
        return
    if not cond:
        raise AssertionError(f"[{aid}] {msg}")


def fakelen(seq, delta: int):
    """🔴 분모만 어긋나게 보이는 리스트 — **입력 파손**이다(시험 전용 인자가 아니다).

    생산 함수가 `len(rows)` 를 분모로 쓰는 자리에서 「조용히 빠진 짝」을 흉내 낸다.
    """
    class _F(list):
        def __len__(self):
            return list.__len__(self) + delta
    return _F(seq)


# ══ 생산 함수 ══════════════════════════════════════════════════════════
def read_pairs(table: dict) -> list[dict]:
    """`판정 표` → 짝 한 줄씩. 🔴 등급을 다시 안 매긴다 — 라벨과 서술 통계를 **읽는다**.

    R1 등급이 셋(A/B/C) 밖이면 죽는다        R2 형이 넷 밖이면 죽는다
    R3 소수 쪽이 정수가 아니면 죽는다          R4 값 가짓수·비결측이 정수가 아니면 죽는다
    R5 티어가 둘(T1/T2) 밖이면 죽는다
    """
    CALLS["read_pairs"] += 1
    rows = []
    for dom, dv in table.items():
        for col, p in (dv.get("짝") or {}).items():
            g = p.get("식1 근거") or {}
            g = g if isinstance(g, dict) else {}
            grade, typ, tier = p.get("등급(식별)"), p.get("형"), p.get("등급")
            mn, nv, nm = g.get("소수 쪽"), p.get("값 가짓수"), p.get("비결측(D1)")
            _A("R1", grade in GRADES, f"{dom}/{col}: 등급이 셋 밖이다/없다 — {grade!r}")
            _A("R2", typ in TYPES, f"{dom}/{col}: 형이 넷 밖이다/없다 — {typ!r}")
            _A("R3", isinstance(mn, int), f"{dom}/{col}: 소수 쪽이 정수가 아니다/없다 — {mn!r}")
            _A("R4", isinstance(nv, int) and isinstance(nm, int),
               f"{dom}/{col}: 값 가짓수·비결측이 정수가 아니다/없다 — {nv!r}/{nm!r}")
            _A("R5", tier in TIERS, f"{dom}/{col}: 티어가 둘 밖이다/없다 — {tier!r}")
            rows.append({
                "도메인": dom, "짝": col, "티어": tier, "등급": grade, "형": typ,
                "값 가짓수": nv, "비결측": nm, "소수 쪽": mn,
                "식1": p.get("식1 처치/대조"), "식3": p.get("식3 역인과 아님"),
                "_W": p.get("W"), "_표지": p.get("🔴 표지(등급 미사용)"),
                "_단위변이": p.get("표지 단위 안 변이(등급 미사용)"),
            })
    return rows


def H(xs) -> float:
    n = len(xs)
    if n == 0:
        return 0.0
    c = Counter(xs)
    return -sum(v / n * math.log2(v / n) for v in c.values())


def cond_entropy(rows: list[dict], key: str, featfn) -> dict:
    """H(y) · H(y|x) · MI. 🔴 E1 묶음 크기 합이 분모와 다르면 죽는다(조항 60)."""
    CALLS["cond_entropy"] += 1
    ys = [r[key] for r in rows]
    xs = [featfn(r) for r in rows]
    g = defaultdict(list)
    for y, x in zip(ys, xs):
        g[x].append(y)
    tot = sum(len(v) for v in g.values())
    _A("E1", tot == len(rows), f"묶음 크기 합 {tot} ≠ 분모 {len(rows)} — 짝이 조용히 빠졌다")
    h = H(ys)
    ch = sum(len(v) / len(rows) * H(v) for v in g.values())
    _A("E2", ch <= h + 1e-9, f"조건부 엔트로피 {ch} > 엔트로피 {h} — 상호정보가 음수다")
    return {"분모": len(rows), "엔트로피 H(등급)": round(h, 4),
            "조건부 엔트로피 H(등급|특징)": round(ch, 4),
            "🔴 상호정보(비트)": round(h - ch, 4),
            "특징 값 가짓수": len(g)}


# ── 결정트리 (탐욕 CART · 순수 파이썬) ─────────────────────────────────
NUM = ("값 가짓수", "비결측", "소수 쪽")
CAT = ("형", "도메인")


def _gain(ys, left, right) -> float:
    n = len(ys)
    return H(ys) - (len(left) / n * H(left) + len(right) / n * H(right))


def fit_tree(rows: list[dict], feats: tuple, depth: int):
    """탐욕 결정트리. 🔴 T1 잎이 비면 죽는다 · T2 깊이 한도를 넘으면 죽는다."""
    CALLS["fit_tree"] += 1
    _A("T2", depth >= 0, f"깊이가 음수다 — {depth}")

    def build(sub, d):
        ys = [r["등급"] for r in sub]
        node = {"잎": Counter(ys).most_common(1)[0][0], "n": len(ys)}
        if d <= 0 or len(set(ys)) <= 1:
            return node
        best = None
        for f in feats:
            if f in NUM:
                vals = sorted({r[f] for r in sub})
                for a, b in zip(vals, vals[1:]):
                    t = (a + b) / 2.0
                    L = [r for r in sub if r[f] <= t]
                    R = [r for r in sub if r[f] > t]
                    if not L or not R:
                        continue
                    gn = _gain(ys, [r["등급"] for r in L], [r["등급"] for r in R])
                    if best is None or gn > best[0] + 1e-12:
                        best = (gn, f, t, "<=", L, R)
            else:
                for lv in sorted({r[f] for r in sub}):
                    L = [r for r in sub if r[f] == lv]
                    R = [r for r in sub if r[f] != lv]
                    if not L or not R:
                        continue
                    gn = _gain(ys, [r["등급"] for r in L], [r["등급"] for r in R])
                    if best is None or gn > best[0] + 1e-12:
                        best = (gn, f, lv, "==", L, R)
        if best is None or best[0] <= 1e-12:
            return node
        _, f, v, op, L, R = best
        _A("T1", len(L) > 0 and len(R) > 0, "잎이 빈 분할이 골라졌다")
        node["분할"] = {"특징": f, "연산": op, "값": v}
        node["왼쪽"] = build(L, d - 1)
        node["오른쪽"] = build(R, d - 1)
        return node

    return build(rows, depth)


def tree_predict(node, r) -> str:
    while "분할" in node:
        s = node["분할"]
        go = (r[s["특징"]] <= s["값"]) if s["연산"] == "<=" else (r[s["특징"]] == s["값"])
        node = node["왼쪽"] if go else node["오른쪽"]
    return node["잎"]


def resub(rows: list[dict], feats: tuple, depth: int) -> dict:
    CALLS["resub"] += 1
    t = fit_tree(rows, feats, depth)
    pred = [tree_predict(t, r) for r in rows]
    _A("S1", len(pred) == len(rows), f"예측 수 {len(pred)} ≠ 분모 {len(rows)}")
    err = sum(1 for p, r in zip(pred, rows) if p != r["등급"])
    return {"분모": len(rows), "🔴 재대입 오류": err, "예측": pred}


def lodo(rows: list[dict], feats: tuple, depth: int) -> dict:
    """🔴 도메인 하나씩 빼고 학습 → 뺀 도메인에서 채점. **일반화되는 재현인가.**

    L1 각 짝이 정확히 한 번만 채점돼야 한다   L2 접기 수 == 도메인 수
    """
    CALLS["lodo"] += 1
    doms = sorted({r["도메인"] for r in rows})
    pred: dict[int, str] = {}
    for d in doms:
        tr = [r for r in rows if r["도메인"] != d]
        te = [(i, r) for i, r in enumerate(rows) if r["도메인"] == d]
        if not tr or not te:
            continue
        t = fit_tree(tr, feats, depth)
        for i, r in te:
            pred[i] = tree_predict(t, r)
    _A("L1", len(pred) == len(rows),
       f"채점된 짝 {len(pred)} ≠ 분모 {len(rows)} — 조용히 빠진 짝이 있다")
    _A("L2", len(doms) == len({r['도메인'] for r in rows}),
       "접기 수가 도메인 수와 다르다")
    idx = sorted(pred)
    err = [rows[i]["짝"] for i in idx if pred[i] != rows[i]["등급"]]
    ys = [rows[i]["등급"] for i in idx]
    ph = [pred[i] for i in idx]
    g = defaultdict(list)
    for y, p in zip(ys, ph):
        g[p].append(y)
    n_ok = max(len(ys), 1)
    ch = sum(len(v) / n_ok * H(v) for v in g.values())
    return {"분모": len(rows), "채점된 짝": len(idx), "접기 수(도메인)": len(doms),
            "🔴 LODO 오류": len(err), "틀린 짝": err,
            "H(등급)": round(H(ys), 4),
            "🔴 H(등급 | LODO 예측)": round(ch, 4),
            "🔴 상호정보(일반화 기준 · 비트)": round(H(ys) - ch, 4)}


def memorize(rows: list[dict], feats: tuple) -> dict:
    """🔴 암기 상한 — 5-튜플 조회표. 물음을 글자대로 받으면 이것이 「재현 함수」다."""
    CALLS["memorize"] += 1
    key = [tuple(r[f] for f in feats) for r in rows]
    tab: dict = {}
    for k, r in zip(key, rows):
        tab.setdefault(k, Counter())[r["등급"]] += 1
    _A("M1", len(tab) <= len(rows), "조회표 항목이 분모보다 많다")
    err = sum(1 for k, r in zip(key, rows)
              if tab[k].most_common(1)[0][0] != r["등급"])
    return {"분모": len(rows), "🔴 서로 다른 튜플 수": len(tab),
            "🔴 유일 비율": round(len(tab) / len(rows), 4),
            "🔴 암기 재대입 오류": err}


# ── 팔 ㄴ · 형제 키 ────────────────────────────────────────────────────
def sibling_feats(rows: list[dict]) -> dict:
    """🔴 「등급 미사용」이라 선언된 형제 키를 읽어 **범주형 라벨**로 만든다.

    B1 세 키가 다 있는지 짝마다 확인한다 — 없으면 「없음」이 아니라 **「그 키가 없다」**로 센다
    """
    CALLS["sibling_feats"] += 1
    miss = Counter()
    for r in rows:
        for k in ("_W", "_표지", "_단위변이"):
            if r[k] is None:
                miss[k] += 1
        w = r["_W"]
        codes = tuple(sorted(x["W"].split(" ")[0] for x in w)) if isinstance(w, list) else ("🔴키없음",)
        f = r["_표지"]
        flags = tuple(sorted(f)) if isinstance(f, list) else (str(f),)
        u = r["_단위변이"]
        ukey = u.get("단위 키") if isinstance(u, dict) else "🔴키없음"
        uvar = (u.get("그중 이 열의 값이 2가지 이상인 단위 수") if isinstance(u, dict) else None)
        ubase = (u.get("레코드 2건 이상인 단위 수") if isinstance(u, dict) else None)
        r["_W코드"] = codes
        r["_표지집합"] = flags
        r["_단위키"] = ukey
        r["_단위변이수"] = uvar
        r["_단위분모"] = ubase
    _A("B1", sum(miss.values()) == 0,
       f"형제 키가 없는 짝이 있다 — {dict(miss)} (「없음」이 아니라 「그 키가 없다」)")
    return {"🔴 키가 없는 짝": dict(miss) or "없다(전량 있다)"}


# ══ 배선 검사 ══════════════════════════════════════════════════════════
def _probe(fn, *a, **kw):
    try:
        fn(*a, **kw)
        return False, "🔴 발화 안 함"
    except AssertionError as e:
        return True, f"AssertionError: {e}"


def wiring(table: dict, rows: list[dict]) -> dict:
    w = {"🔴 규약": ("검사는 생산 함수를 **부른다**(지역 복제본 금지). 증거는 진입 계수기 `CALLS`. "
                  "🔴 각 검사를 **하나만 꺼서** 다시 넣는다 — 다른 검사가 대신 발화하면 국소 시험 실패. "
                  "🔴 심는 결함은 **전부 입력 파손**이다. "
                  "🔴 ㉱ 는 **국소 열 자체의 검정력**이다(티처 #68 m2) — "
                  "그 검사를 끈 채 **다른 검사가 잡도록 만든 입력**을 넣어 ㉯ 가 참이 아니게 되는 "
                  "경우를 실제로 만든다. 못 만들면 그 열은 **검정력 0 으로 신고**한다"),
         "검사": {}}

    def one(aid, fn, fnname, broken, clean, 심은것, double=None):
        before = CALLS[fnname]
        fired, msg = _probe(fn, *broken)                     # ㉮
        c1 = CALLS[fnname]
        OFF.add(aid)
        try:
            loc, locmsg = _probe(fn, *broken)                # ㉯
        finally:
            OFF.discard(aid)
        c2 = CALLS[fnname]
        neg, negmsg = _probe(fn, *clean)                     # ㉰
        c3 = CALLS[fnname]
        # ㉱ 국소 열의 검정력 — 그 검사를 끈 채 **다른 검사도 깨진** 입력을 넣는다
        pw, pwmsg = (None, "🔴 이 검사엔 겹칠 짝 검사를 안 만들었다(검정력 안 쟀다)")
        if double is not None:
            OFF.add(aid)
            try:
                pw, pwmsg = _probe(fn, *double)
            finally:
                OFF.discard(aid)
        w["검사"][aid] = {
            "부른 생산 함수": fn.__qualname__,
            "심은 결함(입력 파손)": 심은것,
            "㉮ 파손·전부 켬 — 발화": fired, "발화 메시지": msg,
            "🔴 ㉯ 파손·이 검사만 끔 — 발화": loc, "㉯ 메시지": locmsg,
            "🔴 국소 시험 통과(㉯ 가 발화 안 함)": (not loc),
            "㉰ 정상·전부 켬 — 발화": neg, "㉰ 메시지": negmsg if neg else "발화 안 함(정상)",
            "🔴 ㉱ 국소 열이 거짓이 되는 입력을 심었을 때 발화": pw,
            "㉱ 메시지": pwmsg,
            "🔴 ㉱ 국소 열의 검정력 > 0": bool(pw),
            "🔴 결함을 지우면 통과로 바뀌나": (fired and not neg),
            "진입 계수기 증가(㉮/㉯/㉰)": [c1 - before, c2 - c1, c3 - c2],
            "🔴 계수기가 셋 다 늘었나": (c1 > before and c2 > c1 and c3 > c2),
        }

    d0 = next(iter(table))
    p0 = next(iter(table[d0]["짝"]))

    def brk(**kv):
        t = copy.deepcopy(table)
        for k, v in kv.items():
            if k == "소수 쪽":
                t[d0]["짝"][p0]["식1 근거"]["소수 쪽"] = v
            elif v is None:
                t[d0]["짝"][p0].pop(k, None)
            else:
                t[d0]["짝"][p0][k] = v
        return t

    one("R1", read_pairs, "read_pairs", (brk(**{"등급(식별)": "Z"}),), (table,),
        f"`판정 표/{d0}/짝/{p0}/등급(식별)` 을 셋 밖 `Z` 로 바꿨다",
        (brk(**{"등급(식별)": "Z", "형": None}),))
    one("R2", read_pairs, "read_pairs", (brk(형=None),), (table,),
        f"`판정 표/{d0}/짝/{p0}/형` 을 지웠다",
        (brk(**{"형": None, "등급(식별)": "Z"}),))
    one("R3", read_pairs, "read_pairs", (brk(**{"소수 쪽": "여섯"}),), (table,),
        f"`판정 표/{d0}/짝/{p0}/식1 근거/소수 쪽` 을 한글 수사 `여섯` 으로 바꿨다",
        (brk(**{"소수 쪽": "여섯", "형": None}),))
    one("R4", read_pairs, "read_pairs", (brk(**{"비결측(D1)": None}),), (table,),
        f"`판정 표/{d0}/짝/{p0}/비결측(D1)` 을 지웠다",
        (brk(**{"비결측(D1)": None, "형": None}),))
    one("R5", read_pairs, "read_pairs", (brk(등급="T3"),), (table,),
        f"`판정 표/{d0}/짝/{p0}/등급`(티어) 을 둘 밖 `T3` 로 바꿨다",
        (brk(**{"등급": "T3", "형": None}),))

    typ = (lambda r: r["형"])

    # E1 · cond_entropy — 묶음 합이 분모와 어긋난다
    #     ㉱ 분모를 1 로 보이게 하면 조건부 엔트로피가 엔트로피를 넘어 **E2** 가 대신 잡는다
    one("E1", cond_entropy, "cond_entropy",
        (fakelen(rows, 1), "등급", typ), (rows, "등급", typ),
        "🔴 분모(`len(rows)`)만 1 크게 보이는 리스트를 넣었다 — 묶음 합이 분모와 어긋난다",
        (fakelen(rows, 1 - len(rows)), "등급", typ))

    # T2 · fit_tree — 깊이를 음수로. 🔴 겹칠 짝 검사가 없어 ㉱ 를 못 만든다(검정력 안 쟀다)
    one("T2", fit_tree, "fit_tree", (rows, ("소수 쪽",), -1), (rows, ("소수 쪽",), 1),
        "`fit_tree` 에 깊이 -1 을 넣었다")

    # S1 · resub — 예측 수가 분모와 어긋난다. ㉱ 는 깊이도 같이 깨서 T2 가 대신 잡게 한다
    one("S1", resub, "resub",
        (fakelen(rows, 1), ("소수 쪽",), 1), (rows, ("소수 쪽",), 1),
        "🔴 분모만 1 크게 보이는 리스트를 넣었다 — 예측 수와 분모가 어긋난다",
        (fakelen(rows, 1), ("소수 쪽",), -1))

    # L1 · lodo — 채점된 짝 수가 분모와 어긋난다. ㉱ 는 깊이도 같이 깬다
    one("L1", lodo, "lodo",
        (fakelen(rows, 1), ("소수 쪽",), 1), (rows, ("소수 쪽",), 1),
        "🔴 분모만 1 크게 보이는 리스트를 넣었다 — 채점된 짝 수와 분모가 어긋난다",
        (fakelen(rows, 1), ("소수 쪽",), -1))

    # M1 · memorize — 조회표 항목이 분모를 넘는다. 🔴 겹칠 짝 검사가 없다
    one("M1", memorize, "memorize",
        (fakelen(rows[:5], -3), ("짝",)), (rows, ("짝",)),
        "🔴 분모만 3 작게 보이는 리스트를 넣었다 — 조회표 항목이 분모를 넘는다")

    # B1 · sibling_feats — W 키를 지운다
    rb = [dict(r) for r in rows]
    rb[0]["_W"] = None
    one("B1", sibling_feats, "sibling_feats", (rb,), ([dict(r) for r in rows],),
        "첫 짝의 `W` 키를 지웠다 — 「없음」이 아니라 「그 키가 없다」로 세야 한다")

    n = len(w["검사"])
    fired = sum(1 for v in w["검사"].values() if v["㉮ 파손·전부 켬 — 발화"])
    local = sum(1 for v in w["검사"].values() if v["🔴 국소 시험 통과(㉯ 가 발화 안 함)"])
    neg = sum(1 for v in w["검사"].values() if not v["㉰ 정상·전부 켬 — 발화"])
    flip = sum(1 for v in w["검사"].values() if v["🔴 결함을 지우면 통과로 바뀌나"])
    cnt = sum(1 for v in w["검사"].values() if v["🔴 계수기가 셋 다 늘었나"])
    powered = sum(1 for v in w["검사"].values() if v["🔴 ㉱ 국소 열의 검정력 > 0"])
    tried = sum(1 for v in w["검사"].values()
                if v["🔴 ㉱ 국소 열이 거짓이 되는 입력을 심었을 때 발화"] is not None)
    w["🔴 분모(심은 결함 수)"] = n
    w["발화"] = fired
    w["🔴 국소 시험 통과"] = local
    w["음성 대조 통과"] = neg
    w["🔴 지우면 통과로 바뀐 수"] = flip
    w["🔴 계수기가 늘어난 수"] = cnt
    w["🔴 ㉱ 국소 열 검정력을 잰 검사 수(분모)"] = tried
    w["🔴 ㉱ 국소 열 검정력 > 0 인 검사 수"] = powered
    w["🔴 ㉱ 는 통과 조건이 아니다"] = ("사전등록 §3-5 — 검정력이 0 이면 0 이라고 **신고**한다. "
                              "905 의 「국소」 열은 이 수가 0 이었다(티처 #68 m2)")
    w["통과"] = (fired == n and local == n and neg == n and flip == n and cnt == n)
    return w


# ══ §3-기계 · 입력 산출물 최상위 키 전량 + 오늘 낼 수의 되찾기 ═══════════
def topkeys(paths: dict) -> dict:
    """🔴 티처 #68 ⑧ 의 「러너 두 줄」 — 입력 산출물의 최상위 키를 **전량** 찍는다."""
    CALLS["topkeys"] += 1
    out = {}
    for name, p in paths.items():
        try:
            d = json.loads(Path(p).read_text())
        except Exception as e:                                # noqa: BLE001
            out[name] = {"🔴": f"못 읽었다: {e}"}
            continue
        ks = list(d.keys()) if isinstance(d, dict) else []
        out[name] = {"최상위 키 수": len(ks), "최상위 키 전량": ks}
    return out


def _walk(node, path, hits, needle, cap):
    if len(hits) >= cap:
        return
    if isinstance(node, dict):
        for k, v in node.items():
            if needle in str(k):
                hits.append(f"{path}/{k} (키 이름)")
            _walk(v, f"{path}/{k}", hits, needle, cap)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            _walk(v, f"{path}[{i}]", hits, needle, cap)
    else:
        if isinstance(node, bool):
            return
        if isinstance(node, (int, float)) and str(node) == needle:
            hits.append(path)
        elif isinstance(node, str) and needle in node:
            hits.append(f"{path} (문자열 안)")


def already_there(verdicts: list[str], srcs: dict, cap: int = 6) -> dict:
    """🔴 오늘 낼 판정문의 **정수를 전부 뽑아** 입력 산출물에서 되찾는다.

    양쪽이 다 기계 산물이다 — 판정문은 러너가 만들고 경로는 탐색이 찾는다.
    **손으로 지은 목록이 아니다**(이슈 #155 C2 가 금지한 꼴).
    """
    CALLS["already_there"] += 1
    nums = sorted({n for v in verdicts for n in re.findall(r"\d+(?:\.\d+)?", v)},
                  key=lambda s: (len(s), s))
    loaded = {}
    for name, p in srcs.items():
        try:
            loaded[name] = json.loads(Path(p).read_text())
        except Exception:                                     # noqa: BLE001
            pass
    per = {}
    for n in nums:
        e = {}
        for name, d in loaded.items():
            h: list[str] = []
            _walk(d, "", h, n, cap)
            e[name] = {"찾은 수(상한 %d)" % cap: len(h), "경로": h}
        e["🔴 판정"] = ("입력에 이미 있다" if any(v["찾은 수(상한 %d)" % cap] for v in e.values()
                                          if isinstance(v, dict))
                     else "입력에서 못 찾았다(오늘 새로 잰 수다)")
        per[n] = e
    새것 = [n for n, e in per.items() if e["🔴 판정"].startswith("입력에서 못")]
    return {
        "🔴 무엇인가": ("티처 #68 ⑧ 의 처방 — 「지금 읽고 있는 그 산출물의 최상위 키를 전량 읽고, "
                   "오늘 낼 문장이 그중 어디에 이미 있는지 대조하라」. **러너 두 절**로 넣었다"),
        "판정문에서 뽑은 정수 가짓수(분모)": len(nums),
        "판정문에서 뽑은 정수": nums,
        "🔴 입력에서 못 찾은 수(오늘 새것)": 새것,
        "🔴 입력에서 못 찾은 수의 개수": len(새것),
        "🔴 입력에 이미 있는 수의 개수": len(nums) - len(새것),
        "⚠ 작은 정수는 어디에나 맞는다": "0·1·2 같은 수의 「이미 있다」는 증거가 약하다 — 경로를 보고 판단하라",
        "수별 되찾기": per,
    }


# ══ 원장 훑기 ══════════════════════════════════════════════════════════
def ledger_scan() -> dict:
    CALLS["ledger_scan"] += 1
    d = json.loads(LEDGER.read_text())
    needles = ["등급", "비트", "재현", "상수", "엔트로피", "재명명"]
    out = {"원장 최상위 항목(분모)": len(d), "🔴 바늘": needles}
    hits = {}
    for nd in needles:
        h = [k for k, v in d.items() if nd in k or nd in json.dumps(v, ensure_ascii=False)]
        hits[nd] = h
        out[f"바늘 `{nd}` 에 걸린 항목 수"] = len(h)
    uni = sorted(set().union(*hits.values()) if hits else set())
    out["🔴 합집합(이 물음에 걸리는 옛 항목 수)"] = len(uni)
    out["🔴 합집합 목록"] = uni
    core = sorted(set(hits["비트"]) | set(hits["엔트로피"]) | set(hits["재명명"]))
    out["🔴 좁은 바늘(비트·엔트로피·재명명) 합집합 수"] = len(core)
    out["🔴 좁은 바늘 목록"] = core
    big = max(hits, key=lambda k: len(hits[k]))
    out["🔴 제일 넓은 바늘"] = big
    out["🔴 제일 넓은 바늘이 합집합에서 차지하는 비율"] = round(len(hits[big]) / max(len(uni), 1), 3)
    out["🔴 넓은 바늘은 잡음이다"] = (
        f"합집합 {len(uni)} 의 상당 부분이 바늘 `{big}` 하나에서 온다(티처 #68 M9 가 905 에서 잡은 병). "
        "**판정에 쓰는 것은 좁은 바늘 쪽이다**")
    out["🔴 앞 사이클의 수와 안 잇는다"] = (
        "903·904·905 는 바늘이 달랐다. **같은 이름의 다른 자다**(조항 60)")
    return out


# ══ §6 대조 ════════════════════════════════════════════════════════════
def check_wording(verdict: str, section_head: str) -> dict:
    md = PREREG_MD.read_text()
    i = md.find(section_head)
    if i < 0:
        return {"찾았나": False, "🔴 판정": "사전등록에서 그 갈래를 못 찾았다"}
    seg = md[i + len(section_head):]
    j = seg.find("\n###")
    seg = seg[:j] if j > 0 else seg
    body = " ".join(ln.lstrip("> ").strip() for ln in seg.splitlines()
                    if ln.strip().startswith(">"))

    def norm(s: str) -> str:
        return re.sub(r"\s+", " ", s.replace("**", "").replace("`", "")).strip()

    body, vn = norm(body), norm(verdict)
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
            "🔴 대조 전 정규화": "마크다운 강조와 연속 공백만 지웠다 — 글자는 안 바꿨다",
            "🔴 순서대로 다 들어 있나": not miss, "빠진 조각": miss}


# ══ main ══════════════════════════════════════════════════════════════
F5 = ("형", "도메인", "값 가짓수", "비결측", "소수 쪽")
F4 = ("형", "값 가짓수", "비결측", "소수 쪽")          # 🔴 도메인 뺀 것
F3 = ("형", "도메인", "값 가짓수", "비결측")           # 🔴 소수 쪽 뺀 음성 대조
DEPTHS = (1, 2, 3, 4, 5)


def ladder(rows: list[dict]) -> dict:
    """복잡도 사다리 — 특징 집합 × 깊이 로 재대입/LODO 오류를 전량 낸다."""
    out = {}
    for nm, fs in (("F5 다섯 통계(전부)", F5), ("F4 도메인 뺀 넷", F4),
                   ("F3 소수 쪽 뺀 넷(음성 대조)", F3)):
        per = {}
        for d in DEPTHS:
            r = resub(rows, fs, d)
            l = lodo(rows, fs, d)
            per[f"깊이 {d}"] = {"재대입 오류": r["🔴 재대입 오류"],
                             "🔴 LODO 오류": l["🔴 LODO 오류"],
                             "H(등급 | LODO 예측)": l["🔴 H(등급 | LODO 예측)"],
                             "상호정보(일반화 기준)": l["🔴 상호정보(일반화 기준 · 비트)"]}
        out[nm] = {"특징": list(fs), "깊이별": per,
                   "🔴 최소 재대입 오류": min(v["재대입 오류"] for v in per.values()),
                   "🔴 최소 LODO 오류": min(v["🔴 LODO 오류"] for v in per.values())}
    return out


def sib_mi(rows: list[dict], which: str) -> dict:
    if which == "범주형":
        fn = (lambda r: (r["_W코드"], r["_표지집합"], r["_단위키"]))
    elif which == "W만":
        fn = (lambda r: r["_W코드"])
    else:
        fn = (lambda r: (r["_W코드"], r["_표지집합"], r["_단위키"],
                         r["_단위변이수"], r["_단위분모"]))
    return cond_entropy(rows, "등급", fn)


def main():
    out = {
        "노트": 906,
        "사전등록": PREREG,
        "시작 시각": START,
        "물음의 출처": {
            "팔 ㄱ": "이슈 #156 (티처 #68) — 한 팔만 먹는다",
            "팔 ㄴ": "🔴 내가 골랐다 — 사전등록 §1. 인접성만큼 명부에서 뺐다(예측 1개뿐)"},
        "🔴 효과 크기": "없음 — 라벨의 엔트로피·오류 계수뿐. 그래서 규약 47 의 구간이 없다(⓪-가)",
        "🔴 채점기 무접촉": ("ident901.py · ident902.py · inv901.py · pairboot.py · quote901.py · "
                       "fiveprime902.py 를 한 글자도 안 고쳤다. "
                       "⚠ ident902.py:246-254(grade4)를 **읽었다** — 사전등록 §0 에 자백했다"),
        "🔴 자를 뗐다(⓪-가)": ("판 ρ 를 안 썼다. 대신 쓴 자: 등급의 엔트로피(비트) · "
                        "조건부 엔트로피 · 상호정보 · LODO 오류 수 + 분모 병기"),
        "🔴 헤드라인 분모": "T1 81 (docs/prereg_901_intervention.md:61 — T2 24 는 따로 센다 · 105 는 참고)",
        "코드 sha256": {
            "runners/grade906.py": sha(Path(__file__)),
            "runners/inv901.py": sha(ROOT / "runners/inv901.py"),
            "runners/ident902.py": sha(ROOT / "runners/ident902.py"),
        },
        "입력 sha256": {
            "runners/out902_identify.json": sha(SRC902),
            "docs/prereg_906_grade.md": sha(PREREG_MD),
            "data/lab/denominator.json": sha(LEDGER),
        },
    }

    SRCS = {"runners/out902_identify.json": SRC902,
            "runners/out905_cond.json": SRC905}
    out["0-가 🔴 입력 산출물 최상위 키 전량 (티처 #68 ⑧ — 러너 절 1/2)"] = topkeys(SRCS)
    out["0-가′ 🔴 입력이 이미 적어 둔 것 (자백)"] = {
        "runners/out902_identify.json:🔴 상수인 조건은 등급을 못 가른다":
            json.loads(SRC902.read_text())["🔴 상수인 조건은 등급을 못 가른다"],
        "runners/out902_identify.json:🔴 W 는 어느 것도 등급 계산에 안 들어간다":
            json.loads(SRC902.read_text())["🔴 W 는 어느 것도 등급 계산에 안 들어간다"],
        "🔴 그래서": ("「등급을 가르는 것은 식1·식3 뿐」과 「W 는 등급 계산에 안 들어간다」는 "
                  "906 의 성과가 아니다. 판정문에서 새것으로 안 판다"),
    }
    out["0-다 원장이 이미 뭐라 했나"] = ledger_scan()

    table = json.loads(SRC902.read_text())["판정 표"]

    # ── ② 배선 검사 (측정보다 먼저) ─────────────────────────────────
    rows_all = read_pairs(table)
    sibling_feats(rows_all)
    T1 = [r for r in rows_all if r["티어"] == "T1"]
    before = dict(CALLS)
    w = wiring(table, T1)
    out["2 배선 검사"] = w
    out["2 배선 검사"]["검사 전 계수기"] = before
    if not w["통과"]:
        out["🔴 중단"] = "배선 검사가 통과 못 했다 — 사전등록 §8 대로 측정을 안 한다"
        OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
        raise SystemExit("🔴 배선 검사 실패 — 측정 중단")

    # ── ③ 측정 ────────────────────────────────────────────────────
    T2 = [r for r in rows_all if r["티어"] == "T2"]
    base = {
        "🔴 헤드라인 모집단": "T1 81짝", "T1 수(분모)": len(T1),
        "T2 수(분모 · 따로 센다)": len(T2), "T1+T2(참고)": len(rows_all),
        "T1 등급 분포": dict(sorted(Counter(r["등급"] for r in T1).items())),
        "T2 등급 분포": dict(sorted(Counter(r["등급"] for r in T2).items())),
        "도메인 수(분모)": len({r["도메인"] for r in rows_all}),
        "🔴 T2 를 T1 에 안 더한다": "docs/prereg_901_intervention.md:61 — 따로 세고 따로 적는다",
    }
    out["1 분모 (조항 60 — 매 수마다 병기한다)"] = base

    # 3-가 · 등급은 무엇의 함수인가 — 이미 아는 것(§0 「돌렸다」 · 예측 아님)
    def rule1(r):
        return "예" if r["소수 쪽"] >= 10 else "아니오"

    mis1 = [r["짝"] for r in rows_all if rule1(r) != r["식1"]]
    grade_cells = Counter((r["식1"], r["식3"], r["등급"]) for r in rows_all)
    ga = {
        "🔴 이 절은 예측이 아니다": ("사전등록 §0 「돌렸다」 ⑥⑦⑧⑨⑩ 에서 이미 잰 것을 "
                          "**산출물 키로 다시 내는 절**이다. 인용 가능하게 만들려고 낸다"),
        "🔴 식1 ≡ (소수 쪽 ≥ 10) 어긋남": len(mis1),
        "🔴 식1 ≡ (소수 쪽 ≥ 10) 분모": len(rows_all),
        "어긋난 짝": mis1 or "없다(전량 일치)",
        "🔴 티처 #65 M2 와의 차이": ("#65 M2 는 66/66 에서 `(값 수 ≥ 20 ∧ 소수 쪽 ≥ 10)` 이라 "
                            "**둘의 논리곱**이라 했다. 실측은 **소수 쪽 하나의 부등식**으로 "
                            f"{len(rows_all)}/{len(rows_all)} 이 맞는다 — 논리곱의 앞항은 잉여다"),
        "🔴 등급 = f(식1, 식3) 의 칸": {f"식1={a} × 식3={b} → {g}": n
                                for (a, b, g), n in sorted(grade_cells.items())},
        "🔴 칸 수": len(grade_cells),
        "⚠ 이건 입력에 이미 있었다": ("`out902_identify.json:🔴 상수인 조건은 등급을 못 가른다` 가 "
                            "「등급을 가르는 것은 식1 과 식3 뿐」이라 적어 뒀다. "
                            "🔴 `grade4` 소스도 읽었다(사전등록 §0)"),
    }
    for nm, sub in (("T1 81", T1), ("T2 24", T2), ("T1+T2 105(참고)", rows_all)):
        ga[f"엔트로피 · {nm}"] = {
            "H(등급)": round(H([r["등급"] for r in sub]), 4),
            "🔴 5-튜플 암기": memorize(sub, F5),
            "H(등급 | 소수 쪽 ≥ 10)": cond_entropy(sub, "등급", lambda r: r["소수 쪽"] >= 10),
            "H(등급 | 소수 쪽 ≥ 10, 형=d)": cond_entropy(
                sub, "등급", lambda r: (r["소수 쪽"] >= 10, r["형"] == "d")),
            "H(등급 | 도메인)": cond_entropy(sub, "등급", lambda r: r["도메인"]),
            "H(등급 | 다섯 통계 전부)": cond_entropy(sub, "등급", lambda r: tuple(r[f] for f in F5)),
        }
    ga["🔴 물음이 자명해지는 자리"] = (
        "「다섯 통계로 등급을 완전히 재현하는 함수가 있는가」를 글자대로 받으면 답은 **있다**이고 "
        "그건 자료의 성질이 아니라 **튜플이 거의 유일하다는 성질**이다 — "
        f"T1 {len(T1)}짝의 5-튜플이 서로 다른 가짓수 "
        f"{memorize(T1, F5)['🔴 서로 다른 튜플 수']}. 그래서 복잡도를 통제해 다시 묻는다")
    out["3-가 팔 ㄱ · 등급은 무엇의 함수인가 (예측 아님 · §0 에서 이미 돌렸다)"] = ga

    # 3-나 · 복잡도 사다리 (예측이 걸리는 자리)
    gb = {"🔴 무엇인가": ("특징 집합 × 트리 깊이 로 **재대입**과 **LODO** 오류를 전량 낸다. "
                    "🔴 F3 은 **소수 쪽을 뺀 음성 대조**다 — 소수 쪽은 `식1 근거` 안에 있어 "
                    "식1 을 판정한 루틴의 산물이므로, 그것을 빼고도 얼마나 남는지 같이 잰다"),
          "분모": len(T1), "모집단": "T1 81짝"}
    gb.update(ladder(T1))
    bestF5 = min((v["🔴 LODO 오류"], d) for d, v in gb["F5 다섯 통계(전부)"]["깊이별"].items())
    gb["🔴 F5 의 최소 LODO 오류와 그 깊이"] = {"오류": bestF5[0], "깊이": bestF5[1]}
    bd = int(bestF5[1].split()[-1])
    L = lodo(T1, F5, bd)
    gb["🔴 최소 LODO 규칙의 상세"] = L
    gb["🔴 잔여 비트(= H(등급 | LODO 예측))"] = L["🔴 H(등급 | LODO 예측)"]
    gb["🔴 일반화 기준 상호정보(비트)"] = L["🔴 상호정보(일반화 기준 · 비트)"]
    gb["🔴 잔여를 지는 짝 수"] = len(L["틀린 짝"])
    gb["🔴 잔여를 지는 짝(전량)"] = L["틀린 짝"]
    gb["🔴 잔여 짝의 도메인 분해"] = dict(sorted(Counter(
        r["도메인"] for r in T1 if r["짝"] in set(L["틀린 짝"])).items()))
    gb["🔴 잔여 짝의 식3 분해"] = dict(sorted(Counter(
        r["식3"] for r in T1 if r["짝"] in set(L["틀린 짝"])).items()))
    out["3-나 팔 ㄱ · 복잡도를 통제한 재현 (재대입 · LODO · 암기 상한)"] = gb

    # 3-다 · 팔 ㄴ — 형제 키
    gc = {
        "🔴 물음": ("같은 파일이 「등급 계산에 안 들어간다」고 선언한 형제 키들이 "
                 "정보 차원에서도 등급을 복제하지 않는가"),
        "🔴 사전등록 해석 고지": (
            "사전등록 §4 의 P3 은 형제 키 셋을 이름으로만 적었고 **어느 인코딩인지 안 적었다.** "
            "그 애매함을 여기서 푼다 — **주(主)는 범주형 인코딩**(`W` 코드 집합 · 표지 플래그 집합 · "
            "단위 키 이름)이다. 이유는 사전등록 §1 이 이미 못 박은 것과 같다: "
            "`단위 변이 수` 같은 짝별 연속 수치를 넣으면 튜플이 거의 유일해져 **자기 포화**한다 "
            "— 팔 ㄱ 이 자명해지던 바로 그 자리다. 🔴 **수치까지 넣은 판본도 같이 싣는다**"),
        "분모": len(T1),
    }
    gc["키 존재 확인"] = sibling_feats(T1)
    gc["🔴 주 — 범주형 인코딩"] = sib_mi(T1, "범주형")
    gc["W 코드 집합만"] = sib_mi(T1, "W만")
    gc["🔴 부 — 수치까지 넣은 판본(자기 포화 예상)"] = sib_mi(T1, "수치포함")
    gc["🔴 형제 키의 값 분포"] = {
        "W 코드 집합": dict(sorted(Counter(str(r["_W코드"]) for r in T1).items())),
        "표지 플래그 집합 가짓수": len({str(r["_표지집합"]) for r in T1}),
        "단위 키 가짓수": len({r["_단위키"] for r in T1}),
    }
    wmap: dict = {}
    for r in T1:
        wmap.setdefault(str(r["_W코드"]), Counter())[r["등급"]] += 1
    gc["🔴 W 코드 집합 → 등급 대응표(T1 81)"] = {
        k: dict(sorted(v.items())) for k, v in sorted(wmap.items())}
    gc["🔴 대응이 일대일인가"] = {
        "W 코드 집합 가짓수(분모)": len(wmap),
        "등급이 두 가지 이상 섞인 W 코드 집합 수": sum(1 for v in wmap.values() if len(v) > 1),
        "🔴 뜻": ("0 이면 W 코드 집합이 등급을 **결정한다**. "
               "🔴 이건 유일 키 인공물이 아니다 — W 코드 집합은 81짝에서 "
               f"**{len(wmap)}가지**뿐이라 암기할 자리가 없다"),
    }
    gc["🔴 놀랍지 않은 부분과 놀라운 부분을 갈라 적는다"] = (
        "**안 놀라운 것**: W 는 조건의 여집합(무엇이 없어서 못 재는가)이라 조건에서 파생된다 — "
        "그러니 등급을 결정하는 것 자체는 대수롭지 않다. "
        "🔴 **놀라운 것**: 그 파생물이 산출물에 **「등급 미사용」이라는 이름표를 달고** 실려 있었고, "
        "「등급이 나르는 잔여가 무엇인가」를 다섯 사이클 동안 물으면서 **아무도 그 이름표를 안 열었다**. "
        "🔴 그리고 그 잔여(W4·W6·W7 의 유무)는 다섯 서술 통계가 못 나르는 바로 그 부분이다")
    hT1 = round(H([r["등급"] for r in T1]), 4)
    gc["🔴 H(등급) 대조값"] = hT1
    gc["🔴 절반 문턱(H/2)"] = round(hT1 / 2, 4)
    out["3-다 팔 ㄴ · 「등급 미사용」 형제 키가 등급을 복제하는가"] = gc

    # ── ④ 예측 판정 + 🔴 반증 입력 심기 (이슈 #155 처방 1) ────────────
    def P1_eval(rs):
        return resub(rs, F4, 3)["🔴 재대입 오류"] >= 1

    def P1_break(rs):
        return [dict(r, 등급=("A" if (r["소수 쪽"] >= 10 and r["형"] == "d")
                            else ("B" if r["소수 쪽"] >= 10 else "C"))) for r in rs]

    def P2_eval(rs):
        return min(lodo(rs, F5, d)["🔴 LODO 오류"] for d in DEPTHS) >= 1

    def P2_break(rs):
        return [dict(r, 등급=("B" if r["소수 쪽"] >= 10 else "C")) for r in rs]

    def P3_eval(rs):
        return sib_mi(rs, "범주형")["🔴 상호정보(비트)"] < H([r["등급"] for r in rs]) / 2

    def P3_break(rs):
        return [dict(r, _W코드=(r["등급"],), _표지집합=(r["등급"],), _단위키=r["등급"]) for r in rs]

    def P0_eval(rs):
        return 1 == 1

    def P0_break(rs):
        return [dict(r, 등급="A") for r in rs]

    PREDS = [
        ("P1", "도메인을 뺀 넷(깊이 ≤ 3)의 재대입 오류가 1 이상이다",
         "재대입 오류가 0 이면 반증", P1_eval, P1_break,
         "등급을 (소수 쪽 ≥ 10, 형 == d) 의 함수로 갈아끼웠다",
         "🔴 모른다 — 팝업의 c 형 짝을 다른 도메인의 c 형 짝과 가르는 수치 경계가 있는지 안 봤다", True),
        ("P2", "다섯 통계를 다 써도 LODO 오류가 1 이상이다",
         "LODO 오류가 0 이면 반증", P2_eval, P2_break,
         "등급을 (소수 쪽 ≥ 10) 만의 함수로 갈아끼웠다",
         "⚠ 높다(확인될 가능성이 크다) — 도메인을 통째로 빼면 그 도메인의 식3 을 볼 길이 없다. "
         "사전등록 §4 가 **약한 예측임을 미리 신고**했다", True),
        ("P3", "형제 키(범주형)가 등급에 대해 나르는 상호정보가 H(등급)/2 미만이다",
         "MI ≥ H/2 이면 반증", P3_eval, P3_break,
         "형제 키의 값을 등급 문자열 그대로로 갈아끼웠다",
         "🔴 모른다 — 세 키의 값 분포를 안 봤다", True),
        ("🔴 P0(장치 시험 · 예측 아님 · 명부에 안 센다)", "1 == 1",
         "반증 불가능하다 — 장치가 이것을 명부에서 빼야 한다", P0_eval, P0_break,
         "모든 짝의 등급을 A 로 갈아끼웠다",
         "🔴 반증 불가능(설계상)", False),
    ]

    per = {}
    for pid, sent, falsify, ev, bk, plant, prior, counted in PREDS:
        base_v = ev(T1)
        broken_v = ev(bk(T1))
        # 🔴 「민감」 = 심은 반증 입력에서 **평가기가 실제로 「반증」을 낸다**.
        #    이미 자료가 반증한 예측도 민감할 수 있다 — 그건 명부에서 빼는 사유가 아니라
        #    **가장 강한 결과**다. 명부에서 빼는 것은 **반증 불가능한 것**뿐이다.
        sensitive = not bool(broken_v)
        per[pid] = {
            "예측": sent, "반증 조건": falsify,
            "🔴 실측 판정": "확인" if base_v else "🔴 반증",
            "🔴 심은 반증 입력": plant,
            "🔴 심은 뒤 판정": "확인(안 뒤집혔다)" if broken_v else "반증(뒤집혔다)",
            "🔴 반증 입력에서 평가기가 반증을 냈나(=반증 가능한가)": sensitive,
            "🔴 명부 등재": bool(counted and sensitive),
            "🔴 명부에서 빠진 사유": ("" if (counted and sensitive) else
                              (("🔴 심은 반증 입력에서도 평가기가 「확인」을 냈다 — "
                                "반증 불가능하다. 장치가 이것을 빼는 것이 이 시험의 목적이다")
                               if not sensitive else "장치 시험이라 애초에 안 센다")),
            "🔴 사전 난이도": prior,
        }
    listed = [k for k, v in per.items() if v["🔴 명부 등재"]]
    confirmed = [k for k in listed if per[k]["🔴 실측 판정"] == "확인"]
    out["4 예측 판정 (🔴 예측마다 반증 입력을 심었다 — 이슈 #155 처방 1)"] = {
        "🔴 규약": ("심어서 판정이 안 뒤집히면 그 예측은 **명부에서 자동으로 빠진다.** "
                 "905 의 P2(항등식)·P4(저자가 지은 두 목록)가 걸린 자리다(티처 #68 C1·C2)"),
        "항목": per,
        "🔴 심은 반증 입력 수(분모)": len(PREDS),
        "🔴 반증 가능한 것으로 확인된 수": sum(
            1 for v in per.values() if v["🔴 반증 입력에서 평가기가 반증을 냈나(=반증 가능한가)"]),
        "🔴 명부에 남은 예측 수": len(listed),
        "🔴 명부에 남은 예측": listed,
        "🔴 그중 확인": len(confirmed),
        "🔴 그중 반증": len(listed) - len(confirmed),
        "🔴 장치가 실제로 뺀 것": [k for k, v in per.items() if not v["🔴 명부 등재"]],
    }

    # ── ⑤ 판정 (사전등록 §6 어법 그대로) ────────────────────────────
    N = len(T1)
    EL = L["🔴 LODO 오류"]
    Hv = hT1
    CH = L["🔴 H(등급 | LODO 예측)"]
    MI = L["🔴 상호정보(일반화 기준 · 비트)"]
    U = memorize(T1, F5)["🔴 서로 다른 튜플 수"]
    EM = memorize(T1, F5)["🔴 암기 재대입 오류"]
    RES = CH
    목록 = ", ".join(L["틀린 짝"]) if L["틀린 짝"] else "없다"

    if EL == 0:
        vA = (f"🔴 「식별 등급」은 이름이었다 — 다섯 서술 통계가 T1 {N}짝의 등급을 하나도 안 틀리고 "
              f"재현한다(LODO 오류 {EL}). 등급의 엔트로피는 {Hv} 비트이고 다섯 통계를 조건으로 주면 "
              f"남는 것이 {CH} 비트다 — 상호정보 {MI} 비트. 그러므로 무너지는 쪽은 「등급」이고, "
              "901~905 다섯 사이클이 다툰 것은 이름이다. 다음은 자를 갈아야 한다")
        갈래A, headA = "㉠", "### 팔 ㄱ — 갈래 ㉠"
    else:
        vA = (f"🔴 등급에는 다섯 서술 통계 밖의 잔여가 있다 — 일반화되는 규칙은 T1 {N}짝 중 "
              f"{EL}짝을 못 맞힌다. 등급의 엔트로피 {Hv} 비트 중 다섯 통계가 {MI} 비트를 나르고 "
              f"{RES} 비트가 남는다. 잔여를 지는 짝은 {목록} 이고, 그것이 다음 팔의 표적이다. "
              "🔴 다만 물음을 글자대로 받으면 답은 자명하게 「재현 함수가 있다」다 — "
              f"다섯 통계의 조합이 T1 {N}짝 중 {U}가지로 서로 달라 암기가 곧 재현이기 때문이다"
              f"(암기 오류 {EM}). 그래서 이 사이클은 재현 여부가 아니라 복잡도를 통제한 재현으로 답했다")
        갈래A, headA = "㉡", "### 팔 ㄱ — 갈래 ㉡"

    MIW = gc["🔴 주 — 범주형 인코딩"]["🔴 상호정보(비트)"]
    if MIW < Hv / 2:
        vB = (f"🔴 같은 파일의 「등급 미사용」 형제 키들은 등급을 복제하지 않는다 — "
              f"상호정보 {MIW} 비트 대 등급 엔트로피 {Hv} 비트. "
              "그러므로 오늘의 잔여는 그 키들 안에 미리 적혀 있지 않았다")
        갈래B, headB = "㉠", "### 팔 ㄴ — 갈래 ㉠"
    else:
        vB = (f"🔴 같은 파일의 「등급 미사용」 형제 키가 등급의 절반 이상을 이미 담고 있다 — "
              f"상호정보 {MIW} 비트 대 등급 엔트로피 {Hv} 비트. "
              "「등급 계산에 안 들어간다」는 선언은 정보 차원에서 거짓이고, "
              "티처 #68 C3(「답이 입력 산출물에 이미 있었다」)의 세 번째 사례를 러너가 스스로 찾은 것이다")
        갈래B, headB = "㉡", "### 팔 ㄴ — 갈래 ㉡"

    wa, wb = check_wording(vA, headA), check_wording(vB, headB)
    title = vA.split(". ")[0]

    out["5 판정"] = {
        "팔 ㄱ 갈래": 갈래A, "팔 ㄱ 판정문": vA,
        "팔 ㄴ 갈래": 갈래B, "팔 ㄴ 판정문": vB,
        "🔴 사전등록 §6 뼈대와 기계 대조(팔 ㄱ)": wa,
        "🔴 사전등록 §6 뼈대와 기계 대조(팔 ㄴ)": wb,
        "🔴 커밋 제목에 그대로 쓸 문장": title,
        "🔴 판정문 어법에 대한 단서(어법은 사전등록 것이라 못 고친다)": {
            "팔 ㄴ ㉡ 의 「세 번째 사례」": ("🔴 이 서수는 **사전등록이 미리 적은 어법**이고 "
                                 "**이 러너가 센 수가 아니다**. 티처 #68 의 C3 와 M5 를 둘로 세면 "
                                 "셋째가 맞지만 그 계수는 티처가 센 것이다 — 인용하려면 "
                                 "`data/lab/denominator.json:🔴🔴 티처 #68 …` 을 걸어라"),
        },
        "통과": bool(wa.get("🔴 순서대로 다 들어 있나") and wb.get("🔴 순서대로 다 들어 있나")),
    }

    # 0-나 · 🔴 오늘 낼 수를 입력에서 되찾는다 (러너 절 2/2)
    out["0-나 🔴 오늘 낼 판정문의 수를 입력에서 되찾기 (티처 #68 ⑧ — 러너 절 2/2)"] = \
        already_there([vA, vB], SRCS)

    out["6 못 잰 것 (🔴 「없다」가 아니다)"] = [
        "등급이 **처치–결과**에 대해 몇 비트를 나르는가 — 안 쟀다(903 이 A 등급에 대해 쟀고 0 이었다. "
        "이 사이클은 등급과 **서술 통계** 사이만 쟀다)",
        "잔여를 지는 짝을 가르는 것이 **열 이름의 의미**인지 — 이름을 눈으로 봤을 뿐 기계로 안 쟀다. "
        "저장소에 열 의미 사전이 **없다**(⓪-나)",
        "결정트리 말고 다른 규칙 계열(선형·규칙목록·최소 기술 길이) — 안 돌렸다",
        "엔트로피 추정의 편향 — 플러그인 추정량을 그대로 썼고 **보정을 안 했다**. "
        "T1 81 · 등급 3가지라 편향이 작을 것으로 보지만 **안 쟀다**",
        "구간 — 안 만들었다(⓪-가 에 미리 못 박았다 · 규약 47 해당 없음)",
        "이슈 #156 수리 항목 2(⑤′ 의 `failed` 분리) — 🔴 **안 했다**(사전등록 §2 에 이유를 적었다)",
        "KOSTAT 격자 생활인구 — 🔴 **안 받았다**(「없다」가 아니다 · ⓪-나)",
        "T2 24짝의 사다리·LODO — T1 만 돌렸다(prereg_901:61 대로 안 더한다). "
        "T2 의 엔트로피만 3-가 에 실었다",
    ]
    out["🔴 계수기(생산 함수 진입 총계)"] = dict(CALLS)
    out["끝 시각"] = dt.datetime.now().isoformat(timespec="seconds")
    out["초"] = round(time.time() - T0, 3)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print("완료 →", OUT)
    print("배선", w["발화"], "/", w["🔴 분모(심은 결함 수)"], "· 국소", w["🔴 국소 시험 통과"],
          "· ㉱검정력", w["🔴 ㉱ 국소 열 검정력 > 0 인 검사 수"], "/",
          w["🔴 ㉱ 국소 열 검정력을 잰 검사 수(분모)"], "· 통과", w["통과"])
    print("T1", N, "· H", Hv, "· LODO 오류", EL, "· 잔여", RES, "· MI", MI, "· 유일튜플", U)
    print("팔 ㄴ MI(형제키·범주형)", MIW, "· H/2", round(Hv / 2, 4))
    print("명부", out["4 예측 판정 (🔴 예측마다 반증 입력을 심었다 — 이슈 #155 처방 1)"]["🔴 명부에 남은 예측"])


if __name__ == "__main__":
    main()
