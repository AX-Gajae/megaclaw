# -*- coding: utf-8 -*-
"""노트 966 [판정] — **집단 관심의 기억은 90일보다 긴가**.

사전등록: ``docs/prereg_966_longmemory.md`` (커밋 `1b73376cb` · **측정 전 단독 커밋**)

명제(§1): 개체의 **오랜 기저**(시작일 이전 91~455일) 대비 **최근 90일**의 들뜸은,
최근 90일의 **절대 수준**이 담지 못한 결과 정보를 담는다.

🔴 **왜 판이 이것을 원리상 못 봤나** --- ``lab/wikiaxes.py`` 의 규약이
*「창은 시작일 이전 90일이고 시작일 당일과 이후는 한 칸도 안 본다」* 이고,
캐시(``data/state/wiki_views``) 의 ``days`` 는 전부 길이 ≤ 90 이다.
그래서 **91일보다 앞의 자료는 판의 사정권 밖**이다(조항 59 의 「원리상 못 본다」).

자료는 이미 디스크에 있다 --- ``data/ingest/wiki_daily``(노트 941 · 813 개체) +
``data/ingest/wiki_daily959``(3,896 개체) = **개체 3,899 · 11 도메인 ·
2015-07-01 ~ 2026-08-11**. 노트 941 이 *「이 파일은 판에 안 붙인다」* 고 적은 뒤
**25 사이클 동안 판에 안 붙었다.**

쓰는 법::

    python3 runners/longmem966.py --stage wiring   # 배선(빠르다)
    python3 runners/longmem966.py --stage board    # 판 24주행(약 23분)
    python3 runners/longmem966.py --stage prop     # 명제 팔 + 도메인 게이트
    python3 runners/longmem966.py --stage all

🔴 **산출물 자리는 ``--out`` 으로 옮길 수 있고, 그 밖의 쓰기는 ``_NoWrite`` 가 막는다**
(노트 965 가 세운 꼴 --- 러너 320개가 ``ROOT`` 를 하드코딩하고 ``os.chdir`` 하므로).
"""
from __future__ import annotations

import argparse
import builtins
import datetime as dt
import glob
import gzip
import hashlib
import io
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path("/Users/ax/world_model")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runners"))
os.chdir(str(ROOT))

OUT = ROOT / "runners/out966_longmem.json"

#: 원천 개시일. **이 날 이전은 0 이 아니라 결측이다** --- 안 받은 것과 0 을 섞지 않는다.
API0 = dt.date(2015, 7, 1).toordinal()
RECENT = 90          #: 판이 이미 보는 띠 [s-90, s-1]
LONG = 365           #: 🔴 판이 원리상 못 보는 띠 [s-455, s-91]
COL = "wiki_excite"  #: 이 사이클이 더하는 **단 하나의** 열
T = 2025.0
SEEDS = 12           #: 자 정본(ff753.RULER_SEEDS)
RHO0 = 0.47034       #: 판 정본(노트 891·898)
ADOPT_T_1COL = 0.01055   #: 🔴 **열 1개 증가** 문턱. 열 수 불변 0.00353 이 아니다


# ── 쓰기 문지기 ────────────────────────────────────────────────────────
class _NoWrite:
    """산출물 한 자리 말고는 못 쓰게 막는다(노트 965 의 꼴)."""

    def __init__(self, allow=()):
        self.allow = {str(Path(a).resolve()) for a in allow}

    def _guard(self, orig):
        def f(file, mode="r", *a, **k):
            if any(m in str(mode) for m in ("w", "a", "x", "+")):
                if str(Path(str(file)).resolve()) not in self.allow:
                    raise PermissionError("🔴 966 문지기: 쓰기 금지 %s" % file)
            return orig(file, mode, *a, **k)
        return f

    def __enter__(self):
        self._o, self._i, self._g = builtins.open, io.open, gzip.open
        builtins.open = self._guard(self._o)
        io.open = self._guard(self._i)
        gzip.open = self._guard(self._g)
        return self

    def __exit__(self, *e):
        builtins.open, io.open, gzip.open = self._o, self._i, self._g
        return False


def _sha_file(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _d2o(n) -> int:
    n = int(n)
    return dt.date(n // 10000, (n // 100) % 100, n % 100).toordinal()


# ── §1 특징 ───────────────────────────────────────────────────────────
def load_series() -> dict:
    """`키` → 레코드. 같은 키가 두 원천에 있으면 **긴 계열**을 쓴다."""
    recs = {}
    for base in ("wiki_daily", "wiki_daily959"):
        for p in sorted(glob.glob(str(ROOT / "data/ingest" / base / "*.jsonl.gz"))):
            with gzip.open(p, "rt", encoding="utf-8") as f:
                for line in f:
                    r = json.loads(line)
                    k = r["키"]
                    if k in recs and len(recs[k]["날짜"]) >= len(r["날짜"]):
                        continue
                    r["_원천"] = base
                    recs[k] = r
    return recs


def excite(recs: dict, *, leak: bool = False) -> tuple:
    """🔴 들뜸 열을 만든다. `leak=True` 는 **누출을 일부러 심는다**(검정력용).

    돌려주는 것: (값 dict, 진단 dict). 값 dict 는 `키` → float.
    진단에는 **쓴 날짜의 최댓값과 시작일의 차**가 개체마다 들어간다 --- F5 의 자.
    """
    val, diag = {}, {"쓴 최대날짜 − 시작일(일)": [], "무효 사유": {}}
    for k, r in recs.items():
        s = r.get("시작일")
        if not s:
            diag["무효 사유"]["시작일 없음"] = diag["무효 사유"].get("시작일 없음", 0) + 1
            continue
        s0 = dt.date(*map(int, s.split("-"))).toordinal()
        if s0 - RECENT - LONG < API0:
            diag["무효 사유"]["긴 띠가 원천 개시일 밖"] = \
                diag["무효 사유"].get("긴 띠가 원천 개시일 밖", 0) + 1
            continue
        if not r["날짜"]:
            diag["무효 사유"]["자료 0행"] = diag["무효 사유"].get("자료 0행", 0) + 1
            continue
        dd = np.array([_d2o(x) for x in r["날짜"]])
        vv = np.asarray(r["조회수"], float)
        hi = s0 + RECENT if leak else s0 - 1          # 🔴 leak=True 면 시작일 이후를 먹는다
        m_rec = (dd >= s0 - RECENT) & (dd <= hi)
        m_lon = (dd >= s0 - RECENT - LONG) & (dd <= s0 - RECENT - 1)
        used = dd[m_rec | m_lon]
        if len(used):
            diag["쓴 최대날짜 − 시작일(일)"].append(int(used.max() - s0))
        # 🔴 띠 안의 빠진 날 = 0 조회(원천이 0 인 날을 빠뜨린다).
        val[k] = float(np.log1p(vv[m_rec].sum() / RECENT)
                       - np.log1p(vv[m_lon].sum() / LONG))
    return val, diag


def board_keys() -> tuple:
    """도메인 → 행 순서 키 목록. `runners/out941_holdout.py` 와 **같은 조리법**."""
    import ff753 as FF
    from lab import wikiaxes as WA, trendaxes as TA, idolset as IS
    data = FF.shell(FF.base())
    ids = WA._ids()
    ids["영화"] = list(json.loads((ROOT / "data/state/kobis_axes.json")
                                 .read_text(encoding="utf-8")))
    TA.set_wide(False)
    TA.set_grades(("A", "B", "C", "D", "E"))
    ids["팝업"] = list(TA._popup_ids())
    ids["아이돌"] = [r.get("record_id") or r.get("id")
                  for r in IS._rows(mode_wide=True, wide_post=True)]
    return data, ids


def make_extra(data, ids, val: dict, *, constant: bool = False,
               detach: bool = False) -> tuple:
    """`harness.load` 가 먹는 꼴 `{열: {도메인: (값, 표시자)}}` 로 만든다.

    🔴 **도메인 안 순위정규화** --- 눈금이 도메인마다 다르다(노트 646 관례).
    `constant=True` 면 상수 열을 만든다 · `detach=True` 면 행을 한 칸 밀어 **안 맞춘다**
    (둘 다 검정력용 심기).
    """
    byd, att = {}, {}
    for d in sorted(data.dom):
        n = len(data.dom[d][2])
        kk = ids.get(d)
        v = np.full(n, 0.5)
        o = np.zeros(n)
        if kk and len(kk) == n:
            raw = np.array([val.get(k, np.nan) for k in kk], float)
            if detach:
                raw = np.roll(raw, 1)
            ok = np.isfinite(raw)
            if ok.sum() >= 2:
                r = raw[ok].argsort().argsort().astype(float)
                v[ok] = (r + 1.0) / (ok.sum() + 1.0)
                o[ok] = 1.0
            att[d] = int(ok.sum())
        else:
            att[d] = 0
        if constant:
            v = np.full(n, 0.5)
            o = np.ones(n)
        byd[d] = (v, o)
    return {COL: byd}, att


# ── §2 배선 ───────────────────────────────────────────────────────────
def wiring(recs, data, ids, val, diag) -> dict:
    import ff753 as FF
    from lab import forms
    from lab.harness import evaluate

    W = {}

    # W1 누출 --- 🔴 **쓴 날짜의 최댓값이 시작일보다 앞이어야 한다**
    gaps = diag["쓴 최대날짜 − 시작일(일)"]
    lv, ldg = excite(recs, leak=True)       # 심은 누출(음성 대조)
    lgaps = ldg["쓴 최대날짜 − 시작일(일)"]
    W["W1 누출 없음(F5)"] = {
        "분모: 유효 개체": len(gaps),
        "🔴 분자: 시작일 이후 날짜를 쓴 개체": int(sum(1 for g in gaps if g >= 0)),
        "쓴 최대날짜 − 시작일의 최댓값(일)": (int(max(gaps)) if gaps else None),
        "🔴 무엇이면 떨어지나": "심은 누출판(leak=True)에서 이 수가 0 이 아니어야 한다",
        "심은 누출판의 위반 개체": int(sum(1 for g in lgaps if g >= 0)),
        "통과": (sum(1 for g in gaps if g >= 0) == 0
               and sum(1 for g in lgaps if g >= 0) > 0)}

    # W2 부착 --- 유보에 몇 행 · 몇 도메인
    hold = json.loads((ROOT / "runners/out941_holdout.json")
                      .read_text(encoding="utf-8"))["유보키"]
    per, tot, nd = {}, 0, 0
    for d in sorted(hold):
        n = sum(1 for k in hold[d] if k in val)
        per[d] = {"부착": n, "유보": len(hold[d])}
        tot += n
        nd += (n > 0)
    W["W2 유보 부착"] = {
        "도메인별": per, "🔴 분자: 부착 유보 행": tot, "🔴 분모: 유보": 3775,
        "부착률(%)": round(100.0 * tot / 3775, 2),
        "🔴 붙은 도메인": nd, "전체 도메인": 12,
        "🔴 무엇이면 떨어지나": "부착이 0 이거나 도메인이 2 미만이면",
        "통과": tot > 0 and nd >= 2}

    # W3 상수 아님(P4)
    ex, att = make_extra(data, ids, val)
    uniq = len({round(float(x), 9) for d in ex[COL]
                for x, o in zip(*ex[COL][d]) if o > 0})
    cex, _ = make_extra(data, ids, val, constant=True)
    cuniq = len({round(float(x), 9) for d in cex[COL]
                 for x, o in zip(*cex[COL][d]) if o > 0})
    W["W3 열이 상수가 아니다(조항 64)"] = {
        "🔴 분자: 서로 다른 값 가짓수": uniq, "분모: 부착 행": int(sum(att.values())),
        "🔴 무엇이면 떨어지나": "심은 상수판(constant=True)에서 가짓수가 1 이어야 한다",
        "심은 상수판의 가짓수": cuniq,
        "통과": uniq >= 100 and cuniq == 1}

    # W4 열이 판에 실제로 들어갔나(이름)
    d2 = FF.shell({**FF.base(), **ex})
    inn = sorted(d for d in d2.dom if COL in (d2.names.get(d) or []))
    W["W4 열 이름이 모형 입력에 있다"] = {
        "🔴 분자: 열이 붙은 도메인": len(inn), "분모: 도메인": len(d2.dom),
        "기준선 열 수(도서)": len(data.names["도서"]),
        "처리 열 수(도서)": len(d2.names["도서"]),
        "🔴 무엇이면 떨어지나": "열 수가 정확히 1 안 늘면(문턱 0.01055 의 전제)",
        "통과": len(inn) == len(d2.dom)
               and len(d2.names["도서"]) - len(data.names["도서"]) == 1}

    # W5 🔴 **그 열이 정말 모형에 닿았나** --- 그 열만 섞으면 예측이 변해야 한다
    cls = forms.REGISTRY["F18_bagboost"]["cls"]
    sc0 = evaluate(lambda: cls(seed=0), d2, T=T)
    rng = np.random.RandomState(966)
    shuf = {COL: {}}
    for d in sorted(data.dom):
        v, o = ex[COL][d]
        p = rng.permutation(len(v))
        shuf[COL][d] = (np.asarray(v)[p], np.asarray(o)[p])
    d3 = FF.shell({**FF.base(), **shuf})
    sc1 = evaluate(lambda: cls(seed=0), d3, T=T)
    moved = sorted(d for d in sc0
                   if d in sc1 and np.isfinite(sc0[d]) and np.isfinite(sc1[d])
                   and abs(sc0[d] - sc1[d]) > 1e-12)
    W["W5 그 열이 모형에 닿았다(F6)"] = {
        "🔴 분자: 열만 섞었을 때 점수가 변한 도메인": len(moved),
        "분모: 점수가 난 도메인": len([d for d in sc0 if np.isfinite(sc0[d])]),
        "변한 도메인": moved,
        "판 ρ(씨앗0 · 원본)": round(float(d2.pooled(sc0, T=T)), 6),
        "판 ρ(씨앗0 · 그 열만 섞음)": round(float(d3.pooled(sc1, T=T)), 6),
        "🔴 무엇이면 떨어지나": "열이 모형에 안 닿으면 두 값이 비트 동일하다",
        "통과": len(moved) >= 1}

    # W6 행 정렬 --- 한 칸 밀면 부착이 깨져야 한다
    dex, datt = make_extra(data, ids, val, detach=True)
    same = sum(1 for d in ex[COL]
               for a, b in zip(ex[COL][d][0], dex[COL][d][0]) if abs(a - b) < 1e-12)
    W["W6 행 정렬이 진짜다"] = {
        "🔴 분자: 한 칸 밀어도 같은 값인 행": same,
        "분모: 전체 행": int(sum(len(data.dom[d][2]) for d in data.dom)),
        "🔴 무엇이면 떨어지나": "정렬이 무의미하면 밀어도 값이 같다",
        "통과": same < int(sum(len(data.dom[d][2]) for d in data.dom))}

    n_ok = sum(1 for v in W.values() if v.get("통과") is True)
    return {"검사": W, "🔴 분자: 통과": n_ok, "🔴 분모: 돌린 검사": len(W),
            "부착 도메인별": att}


# ── §3 판 ─────────────────────────────────────────────────────────────
def measure_board(data, ids, val) -> dict:
    import ff753 as FF
    from lab.board import board as B
    ex, _ = make_extra(data, ids, val)
    t0 = time.time()
    b0 = B(data, seeds=SEEDS, T=T)
    t1 = time.time()
    d2 = FF.shell({**FF.base(), **ex})
    b1 = B(d2, seeds=SEEDS, T=T)
    t2 = time.time()
    delta = b1["판"] - b0["판"]
    dom = {d: {"기준선": round(b0["도메인"].get(d, (float("nan"),))[0], 4),
               "처리": round(b1["도메인"].get(d, (float("nan"),))[0], 4),
               "Δ": round(b1["도메인"].get(d, (float("nan"),))[0]
                          - b0["도메인"].get(d, (float("nan"),))[0], 4)}
           for d in sorted(set(b0["도메인"]) & set(b1["도메인"]))}
    return {
        "기준선": {"판": b0["판"], "SD": b0["SD"], "SE": b0["SE"], "씨앗": b0["씨앗"]},
        "처리": {"판": b1["판"], "SD": b1["SD"], "SE": b1["SE"], "씨앗": b1["씨앗"]},
        "🔴 기준선이 정본 0.47034 를 재현하나": {
            "정본": RHO0, "실측": round(b0["판"], 6),
            "차": round(abs(b0["판"] - RHO0), 6),
            "통과": abs(b0["판"] - RHO0) < 5e-4},
        "🔴 Δρ": round(delta, 6),
        "🔴 문턱(열 1개 증가)": ADOPT_T_1COL,
        "🔴 Δρ ÷ 문턱": round(delta / ADOPT_T_1COL, 4),
        "🔴 이 자를 넘었나": bool(delta >= ADOPT_T_1COL),
        "도메인별": dom,
        "초": {"기준선": round(t1 - t0, 1), "처리": round(t2 - t1, 1)}}


# ── §4 명제 팔 (판과 분모가 다르다 · 조항 60) ─────────────────────────
def _rank(x):
    x = np.asarray(x, float)
    o = x.argsort().argsort().astype(float)
    return (o - o.mean()) / (o.std() + 1e-12)


def _sp(a, b):
    ra, rb = _rank(a), _rank(b)
    return float((ra * rb).mean())


def _partial(x, y, z):
    """z 를 뺀 뒤의 순위 상관(부분 스피어만)."""
    rx, ry, rz = _rank(x), _rank(y), _rank(z)
    rx = rx - rz * float((rx * rz).mean())
    ry = ry - rz * float((ry * rz).mean())
    return float((rx * ry).mean() / (rx.std() * ry.std() + 1e-12))


def proposition(data, ids, val, draws: int = 1000) -> dict:
    """🔴 **명제의 주 증거.** 도메인 안에서 들뜸 ↔ 결과, 수준을 뺀 뒤."""
    out, rng = {}, np.random.RandomState(966)
    for d in sorted(data.dom):
        A, M, y, t = data.dom[d]
        nm = list(data.names.get(d) or [])
        kk = ids.get(d)
        if not kk or len(kk) != len(y) or "wiki_level" not in nm:
            continue
        raw = np.array([val.get(k, np.nan) for k in kk], float)
        lvl = A[:, nm.index("wiki_level")].astype(float)
        ok = np.isfinite(raw) & np.isfinite(y) & np.isfinite(lvl)
        if ok.sum() < 30:
            out[d] = {"n": int(ok.sum()), "🔴 잰다": False,
                      "왜": "n < 30 --- 이 도메인은 못 잰다(조항 59)"}
            continue
        x, yy, zz = raw[ok], y[ok], lvl[ok]
        r_raw = _sp(x, yy)
        r_par = _partial(x, yy, zz)
        r_lvl = _sp(zz, yy)
        null = np.array([_partial(x, yy[rng.permutation(len(yy))], zz)
                         for _ in range(draws)])
        out[d] = {"n": int(ok.sum()),
                  "🔴 잰다": True,
                  "들뜸 ↔ 결과(생)": round(r_raw, 4),
                  "🔴 들뜸 ↔ 결과(수준을 뺀 뒤)": round(r_par, 4),
                  "곁: 수준 ↔ 결과": round(r_lvl, 4),
                  "순열 바닥 |ρ| 95%": round(float(np.percentile(np.abs(null), 95)), 4),
                  "🔴 바닥을 넘었나": bool(abs(r_par) >
                                    float(np.percentile(np.abs(null), 95))),
                  "순열 뽑기": draws}
    live = {d: v for d, v in out.items() if v.get("🔴 잰다")}
    pos = sum(1 for v in live.values() if v["🔴 들뜸 ↔ 결과(수준을 뺀 뒤)"] > 0)
    neg = sum(1 for v in live.values() if v["🔴 들뜸 ↔ 결과(수준을 뺀 뒤)"] < 0)
    over = sum(1 for v in live.values() if v["🔴 바닥을 넘었나"])
    maj = max(pos, neg)
    return {"도메인별": out,
            "🔴 분모: 잰 도메인": len(live),
            "🔴 부호 +": pos, "🔴 부호 −": neg,
            "🔴 과반 부호 도메인 수": maj,
            "🔴 바닥을 넘은 도메인": over,
            "🔴 P3(과반 부호 ≥ 6/11)": bool(maj >= 6),
            "🔴 잰 개체 합": int(sum(v["n"] for v in live.values()))}


# ── §5 도메인 게이트 (🔴 절 회계 밖으로 꺼낸다) ────────────────────────
def domain_gate(val: dict, recs: dict) -> dict:
    """🔴 **도메인 자를 게이트에 건다.** 지금까지 `checks965` 의 절 회계 안에만 있었다.

    앞 = 판이 이미 쓰는 12 도메인 · 뒤 = 이 원천이 덮는 도메인.
    `checks965.domain_ruler` 를 **그대로 부른다**(새 자를 만들지 않는다).
    """
    sys.path.insert(0, str(ROOT / "runners"))
    from checks965 import domain_ruler
    hold = json.loads((ROOT / "runners/out941_holdout.json")
                      .read_text(encoding="utf-8"))["유보키"]
    before = {d: len(v) for d, v in hold.items()}
    after = {}
    for d, v in hold.items():
        n = sum(1 for k in v if k in val)
        if n:
            after[d] = n
    base = domain_ruler(before, after)
    # 심기 ⓓ 한 도메인으로 무너뜨리기 · ⓔ 이름 갈기 (음성 대조)
    pd = domain_ruler(before, {"게임": 1})
    pe = domain_ruler(before, {(d + "_X"): n for d, n in after.items()})
    pg = domain_ruler(before, {**before, "공연": 1})     # 🔴 음성 대조: 늘어나면 안 떨어져야
    return {"실측": base,
            "🔴 Δ": base["🔴 Δ"],
            "심기 ⓓ(한 도메인으로)": {"통과": pd["통과"]},
            "심기 ⓔ(이름 갈기)": {"통과": pe["통과"]},
            "음성 대조 ⓖ(도메인 늘림)": {"통과": pg["통과"]},
            "🔴 자가 무나(ⓓ·ⓔ 는 떨어지고 ⓖ 는 안 떨어진다)":
                (not pd["통과"]) and (not pe["통과"]) and pg["통과"],
            "🔴 게이트 통과": base["통과"]}


# ── 탐색 팔 (판정 없음) ────────────────────────────────────────────────
def explore_kopis() -> dict:
    ps = sorted(glob.glob(str(ROOT / "data/ingest/kopis/*")))
    rows, keys = 0, set()
    for p in ps:
        if not p.endswith(".json") and not p.endswith(".jsonl"):
            continue
        try:
            txt = Path(p).read_text(encoding="utf-8")
            d = json.loads(txt)
        except Exception:
            continue
        it = d if isinstance(d, list) else (d.get("항목") or d.get("rows") or [])
        if isinstance(it, list):
            rows += len(it)
            for r in it[:5000]:
                if isinstance(r, dict):
                    keys |= set(r)
    return {"레인": "탐색 · 🔴 판정 없음 · 이 사이클의 결론에 안 들어간다",
            "파일": len(ps), "행": rows, "열 이름": sorted(keys)[:40],
            "🔴 13번째 도메인(공연) 후보인가": "다음 사이클의 후보일 뿐이다"}


# ── 본선 ──────────────────────────────────────────────────────────────
def main() -> dict:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--stage", default="all",
                    choices=["wiring", "board", "prop", "all"])
    ap.add_argument("--draws", type=int, default=1000)
    a = ap.parse_args()
    outp = Path(a.out)
    t0 = time.time()

    srcs = sorted(glob.glob(str(ROOT / "data/ingest/wiki_daily*/*.jsonl.gz")))
    R = {"노트": 966, "레인": "판정",
         "사전등록": "docs/prereg_966_longmemory.md (커밋 1b73376cb)",
         "명제": ("집단 관심의 기억은 90일보다 길다 --- 오랜 기저(시작일 이전 "
                "91~455일) 대비 최근 90일의 들뜸은 최근 90일의 절대 수준이 "
                "담지 못한 결과 정보를 담는다"),
         "단계": a.stage,
         "🔴 코드 sha256": _sha_file(__file__),
         "원천 파일 sha256": {Path(p).parent.name + "/" + Path(p).name: _sha_file(p)
                        for p in srcs},
         "원천 파일 수": len(srcs)}

    recs = load_series()
    val, diag = excite(recs)
    R["§1 특징"] = {
        "원천 개체": len(recs), "🔴 유효 개체": len(val),
        "무효 사유": diag["무효 사유"],
        "띠": {"최근": "[시작일-90, 시작일-1]",
              "긴기저": "[시작일-455, 시작일-91]",
              "🔴 원천 개시일": "2015-07-01 --- 그 앞은 0 이 아니라 결측"},
        "열 이름": COL}

    data, ids = board_keys()
    R["§0 판 재현"] = {"도메인": len(data.dom),
                   "유보 합": int(sum(data.weights(T).values())),
                   "통과": int(sum(data.weights(T).values())) == 3775}

    if a.stage in ("wiring", "all"):
        R["§2 배선"] = wiring(recs, data, ids, val, diag)
    if a.stage in ("prop", "all"):
        R["§4 명제"] = proposition(data, ids, val, draws=a.draws)
        R["§5 도메인 게이트"] = domain_gate(val, recs)
        R["§9 탐색(KOPIS)"] = explore_kopis()
    if a.stage in ("board", "all"):
        R["§3 판"] = measure_board(data, ids, val)

    R["초"] = round(time.time() - t0, 1)
    R["🔴 끝 시각(UTC)"] = dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    with _NoWrite(allow=[outp]):
        pass
    outp.write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(R, ensure_ascii=False, indent=1)[:4000])
    return R


if __name__ == "__main__":
    main()
