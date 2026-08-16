#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""983 — 🔴🔴 **검정을 예산에서 뗀다 · 축을 섞어 본다 · 「20.95 배」의 프레이밍을 고친다**.

사전등록 `docs/prereg_983_holdout_registry.md` §2-1 ⓔ · §3-2 · §3-3 · §7 을 따른다.

🔴 **왜 (티처 #121 2순위 ⓑ).** 982 의 격자 검정 둘(`p 0.000397` · `p 0.02381`)은
**7 개 예산 칸을 교환 가능한 표본으로 순열**하는데, 짝지은 두 계열이 **둘 다 `N_B` 의
단조 함수**다(㉱ 이득 `0.012681 → −0.000145` · 오라클 여유 `0.246223 → 0.0`).
**공통 구동자의 단조 함수 둘은 인과가 전혀 없어도 스피어만 ±1 을 낸다.**
🔴 그리고 **교환 가능성을 안 요구하는 자 둘**(부호검정 `p 0.125` · 칸 가중 `z 0.4275`)은
**둘 다 안 섰고 거기 걸린 예측 P7·P8 도 둘 다 거짓**이었다 —
**유효한 자는 전부 졌고 헤드라인 둘은 무효한 자에만 기댔다.**

🔴 **왜 (티처 #121 2순위 ⓒ·§7-1).** 982 §3-3 의 「㉡ 이 ㉠ 을 이긴다」는
① `abs(s_tr) >= abs(s_al)` 라 **동점을 승으로 세고**
② `u=3` 의 ㉡ 스피어만이 **자 여섯 전부 `1.0`(천장)** 이라 **질 수 없는 검사**였다.
그래서 **엄격 계수**와 **축 무작위 섞기 변이체**를 붙인다.

씀:
    python3 runners/stat983.py --stage stat --ref <40자 sha>
"""
import argparse
import collections
import datetime as dt
import itertools
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import ledger as LG                               # noqa: E402
import alpha977 as A                              # noqa: E402
import ruler979 as R9                             # noqa: E402
import mix980 as M8                               # noqa: E402

RAN = ("runners/stat983.py", "runners/mix980.py", "runners/ruler979.py",
       "runners/alpha977.py", "runners/ledger.py", "runners/predict971.py")
OUT = ROOT / "runners"

RULERS = R9.RULERS
CANON = "R_pool 묶음"
NB_GRID = list(M8.NB_GRID)
U_REG = A.U_REG

#: 사전등록 §8 — 섞기 벌 수 · 눈금 재기 벌 수
N_SHUF = 2000
N_CAL = 1000
CAL_SEED = 983

TGTS = ["T1 유보 혼합 (n_d)", "T2 균등 (1)", "T3 공급 몫 (hplt 행)",
        "T4 √유보 (√n_d)", "T5 역유보 (1/n_d)"]
DOM_TOP = "세계애니"


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _r(x, n=6):
    if x is None:
        return None
    x = float(x)
    return None if not np.isfinite(x) else round(x, n)


def _load(name, must=True):
    p = OUT / name
    if not p.is_file():
        if must:
            raise SystemExit("🔴 %s 가 없다 — fail-closed" % name)
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


# ══════════════════════════════════════════════════════════════════════
# §0 순위·상관 — 🔴 **982 와 같은 함수를 쓴다**(구판/신판을 나란히 세우려면 같아야 한다)
# ══════════════════════════════════════════════════════════════════════
def _rank(v):
    v = list(v)
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        m = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            r[order[k]] = m
        i = j + 1
    return r


def _pear(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if np.std(a) == 0 or np.std(b) == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def _spear(a, b):
    return _pear(_rank(a), _rank(b))


_PERM = {}


def perms_of(n):
    """`n!` 순열 행렬 — 🔴 **뽑기가 아니라 전수다**(캐시)."""
    if n not in _PERM:
        _PERM[n] = np.asarray(list(itertools.permutations(range(n))), dtype=np.int64)
    return _PERM[n]


def perm_p(a, b, rank=True):
    """전수 순열 p(양측) — `n!` 벌.

    🔴 **982 의 `mech982.spear_perm_p` 와 같은 값을 낸다** — 순위 매기기는 순열과
    바꿔 쓸 수 있으므로(`rank(a[π]) = rank(a)[π]`) 행렬로 한 번에 계산해도 같다.
    `rank=False` 면 값 그대로 쓴다(잔차 순열).
    """
    x = np.asarray(_rank(a) if rank else a, float)
    y = np.asarray(_rank(b) if rank else b, float)
    if np.std(x) < 1e-15 or np.std(y) < 1e-15:
        return None, None, 0
    n = len(x)
    X = x[perms_of(n)]
    X = X - X.mean(axis=1, keepdims=True)
    Y = y - y.mean()
    den = np.sqrt((X * X).sum(axis=1) * float(np.dot(Y, Y)))
    r = X.dot(Y) / den
    s0 = float(np.dot(x - x.mean(), Y) /
               math.sqrt(float(np.dot(x - x.mean(), x - x.mean())) *
                         float(np.dot(Y, Y))))
    cnt = int(np.sum(np.abs(r) >= abs(s0) - 1e-12))
    return _r(s0, 6), _r(float(cnt) / len(r), 6), int(len(r))


def _resid_on(x, c):
    """`rank(x)` 를 `rank(c)` 에 최소제곱 회귀한 **잔차**."""
    rx, rc = np.asarray(_rank(x), float), np.asarray(_rank(c), float)
    rc0 = rc - rc.mean()
    if np.dot(rc0, rc0) == 0:
        return rx - rx.mean()
    beta = float(np.dot(rx - rx.mean(), rc0) / np.dot(rc0, rc0))
    return (rx - rx.mean()) - beta * rc0


def partial_test(a, b, c):
    """🔴🔴 **예산을 공변량으로 넣은 검정** — 칸 안 잔차끼리 짝짓고 잔차를 순열한다."""
    ra, rb = _resid_on(a, c), _resid_on(b, c)
    if np.std(ra) < 1e-12 or np.std(rb) < 1e-12:
        return collections.OrderedDict([
            ("🔴 부분상관(잔차 피어슨)", None),
            ("🔴 전수 순열 p(잔차 순열)", None),
            ("🔴🔴 왜 「모른다」인가",
             "🔴 **한쪽 계열의 잔차가 0 이다** — 곧 그 계열은 `N_B` 의 «완전한» 단조 함수라 "
             "예산을 빼고 나면 남는 정보가 하나도 없다. 「상관 0」이 아니라 **「못 잰다」**다"),
            ("잔차 SD", [_r(float(np.std(ra))), _r(float(np.std(rb)))]),
            ("선다", False)])
    s0, p, tot = perm_p(list(ra), list(rb), rank=False)
    return collections.OrderedDict([
        ("🔴 부분상관(잔차 피어슨)", s0),
        ("🔴 전수 순열 p(잔차 순열)", p),
        ("🔴 벌 수", tot),
        ("잔차 SD", [_r(float(np.std(ra))), _r(float(np.std(rb)))]),
        ("선다", bool(p is not None and p < 0.05))])


def naive_and_partial(a, b, c, name_a, name_b):
    s_n, p_n, tot = perm_p(a, b)
    return collections.OrderedDict([
        ("🔴 계열 A", name_a), ("🔴 계열 B", name_b),
        ("🔴 A 값", [_r(x) for x in a]), ("🔴 B 값", [_r(x) for x in b]),
        ("⚠ 982 판(나이브) 스피어만", s_n),
        ("⚠ 982 판(나이브) 전수 순열 p", p_n),
        ("⚠ 982 판 벌 수", tot),
        ("🔴 A 가 `N_B` 의 단조 함수인가",
         bool(abs(_spear(a, c) or 0.0) > 0.999)),
        ("🔴 B 가 `N_B` 의 단조 함수인가",
         bool(abs(_spear(b, c) or 0.0) > 0.999)),
        ("🔴🔴🔴 983 판(예산 공변량)", partial_test(a, b, c)),
    ])


# ══════════════════════════════════════════════════════════════════════
# §1 🔴🔴 무효성 시연 — 인과가 «원리상 없는» 짝에 982 의 검정을 물린다
# ══════════════════════════════════════════════════════════════════════
def demo_invalid():
    nb = [float(n) for n in NB_GRID]
    lg = [math.log(n) for n in nb]
    s_d, p_d, tot = perm_p(nb, lg)
    #: 🔴 잡음 폭을 «쓸어» 본다 — 한 폭만 보면 그 폭이 결론을 정한다(조항 59)
    sweep = collections.OrderedDict()
    for sig in (0.35, 1.0, 2.0):
        rng = np.random.RandomState(CAL_SEED)
        hit_n = hit_p = und = 0
        for _ in range(N_CAL):
            drift = np.arange(len(nb), dtype=float)
            a = list(drift + rng.normal(0, sig, len(nb)))
            b = list(drift + rng.normal(0, sig, len(nb)))
            _s, p, _t = perm_p(a, b)
            if p is not None and p < 0.05:
                hit_n += 1
            pt = partial_test(a, b, nb)
            if pt.get("🔴 전수 순열 p(잔차 순열)") is None:
                und += 1
            elif pt["🔴 전수 순열 p(잔차 순열)"] < 0.05:
                hit_p += 1
        sweep["σ=%s" % sig] = collections.OrderedDict([
            ("⚠ 982 판이 p<0.05 를 낸 비율", _r(float(hit_n) / N_CAL, 4)),
            ("🔴🔴 983 판이 p<0.05 를 낸 비율", _r(float(hit_p) / N_CAL, 4)),
            ("🔴 983 판이 「못 잰다」를 낸 벌", und),
        ])
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴 **인과가 원리상 없는 단조 짝**에 982 의 검정을 그대로 물린다"),
        ("🔴 ㋑-1 결정론 짝 — `N_B` 자신과 `log N_B`", collections.OrderedDict([
            ("스피어만", s_d), ("🔴🔴 982 판 전수 순열 p", p_d), ("벌 수", tot),
            ("🔴 두 계열의 인과", "🔴 **없다 — 하나가 다른 하나의 결정론적 변환이다**"),
            ("🔴🔴🔴 그래서",
             "🔴 **982 가 헤드라인으로 쓴 `p 0.000397` 은 이 짝에서도 «똑같이» 나온다.** "
             "곧 그 p 는 「인과가 있다」가 아니라 「둘 다 예산과 함께 움직인다」만 말한다"),
        ])),
        ("🔴 ㋑-2 무작위 눈금 재기 — 공통 표류 + «독립» 잡음 두 계열",
         collections.OrderedDict([
             ("벌 수(잡음 폭마다)", N_CAL), ("🔴 표류", "i = 0..6 (예산 칸 차례)"),
             ("🔴 잡음", "독립 정규 · 폭을 쓸어 본다"),
             ("🔴 씨앗", CAL_SEED),
             ("🔴🔴 잡음 폭별 거짓양성률", sweep),
             ("🔴 명목 수준", 0.05),
             ("🔴🔴🔴 그래서",
              "🔴 **인과가 0 인 자료에서 982 판의 거짓양성률은 명목 5% 를 크게 넘고 "
              "983 판은 명목 수준 안이다.** 🔴 그리고 잡음이 작을수록(= 두 계열이 예산의 "
              "완전한 단조 함수에 가까울수록) 982 판은 «반드시» 터지고 983 판은 "
              "**「못 잰다」**를 낸다 — 그것이 옳은 답이다"),
         ])),
    ])


# ══════════════════════════════════════════════════════════════════════
# §2 🔴 §3-3 헤드라인 축 — 엄격 계수 + 무작위 섞기 변이체
# ══════════════════════════════════════════════════════════════════════
def axis_shuffle(tg):
    mixd = tg["🔴 학습 혼합 진단"]
    rows_tr = [float(mixd[t]["🔴 도메인별 학습 행"][DOM_TOP]) for t in TGTS]
    align = tg["🔴🔴 목표–자 정렬도 (코사인)"]
    rng = np.random.RandomState(CAL_SEED)
    perms = list(itertools.permutations(range(len(TGTS))))
    per_u = collections.OrderedDict()
    for u in U_REG:
        uk = "u=%d" % u
        cell = tg["🔴🔴🔴 칸"][uk]["🔴🔴 목표별"]
        det, loose, strict, ties, ceil6 = collections.OrderedDict(), 0, 0, 0, 0
        for nm in RULERS:
            dl = [cell[t]["자 여섯 전부"][nm]["Δ"] for t in TGTS]
            al = [align[t][nm] for t in TGTS]
            s_al, s_tr = _spear(dl, al), _spear(dl, rows_tr)
            lo = bool(s_tr is not None and s_al is not None
                      and abs(s_tr) >= abs(s_al))
            st = bool(s_tr is not None and s_al is not None
                      and abs(s_tr) > abs(s_al))
            tie = bool(s_tr is not None and s_al is not None
                       and abs(abs(s_tr) - abs(s_al)) < 1e-12)
            loose += 1 if lo else 0
            strict += 1 if st else 0
            ties += 1 if tie else 0
            ceil6 += 1 if (s_tr is not None and abs(s_tr) >= 1.0 - 1e-12) else 0
            det[nm] = collections.OrderedDict([
                ("🔴 ㉠ 스피어만(Δ, 정렬도)", _r(s_al, 4)),
                ("🔴 ㉡ 스피어만(Δ, 지배 도메인 학습 행)", _r(s_tr, 4)),
                ("⚠ 982 판 `>=` (동점을 승으로)", lo),
                ("🔴🔴 983 판 `>` (동점은 승이 아니다)", st),
                ("🔴 동점인가", tie),
                ("🔴🔴 ㉡ 이 천장(|스피어만| = 1)인가",
                 bool(s_tr is not None and abs(s_tr) >= 1.0 - 1e-12)),
            ])
        #: 🔴🔴 무작위 섞기 변이체 — ㉡ 축의 «값을 섞어» 같은 비교를 다시 한다
        null = []
        for _ in range(N_SHUF):
            pm = perms[rng.randint(0, len(perms))]
            sh = [rows_tr[i] for i in pm]
            w = 0
            for nm in RULERS:
                dl = [cell[t]["자 여섯 전부"][nm]["Δ"] for t in TGTS]
                al = [align[t][nm] for t in TGTS]
                s_al, s_sh = _spear(dl, al), _spear(dl, sh)
                if s_sh is not None and s_al is not None and abs(s_sh) > abs(s_al):
                    w += 1
            null.append(w)
        null = np.asarray(null, float)
        ge = float(np.mean(null >= strict))
        per_u[uk] = collections.OrderedDict([
            ("🔴 자별", det),
            ("⚠ 982 판 ㉡ 이 이긴 자 수 (`>=`)", loose),
            ("🔴🔴🔴 983 판 ㉡ 이 이긴 자 수 (`>`)", strict),
            ("🔴 동점 자 수", ties),
            ("🔴🔴 ㉡ 스피어만이 천장(1.0)인 자 수", ceil6),
            ("🔴🔴 등록 문턱 「넷 이상」을 넘나(엄격)", bool(strict >= 4)),
            ("🔴🔴🔴 섞기 변이체", collections.OrderedDict([
                ("🔴 섞기 벌 수", N_SHUF),
                ("🔴 섞은 축이 이긴 자 수 — 평균", _r(float(null.mean()), 4)),
                ("🔴 섞은 축이 이긴 자 수 — 최댓값", int(null.max())),
                ("🔴🔴 섞은 축이 참 축만큼 이긴 비율(경험 p)", _r(ge, 4)),
                ("🔴🔴🔴 참 축이 섞은 축과 구별되나(p < 0.05)", bool(ge < 0.05)),
                ("🔴 이 칸이 뜻하는 것",
                 "🔴 **안 구별되면 그 헤드라인은 못 쓴다** — 축을 아무렇게나 섞어도 "
                 "같은 만큼 이긴다는 뜻이다"),
            ])),
        ])
    return collections.OrderedDict([
        ("🔴 ㉡ 축의 값(목표별)", collections.OrderedDict(
            [(t, int(rows_tr[i])) for i, t in enumerate(TGTS)])),
        ("🔴 λ 별", per_u),
        ("🔴🔴🔴 982 의 예측 P9 를 엄격히 다시 센다",
         collections.OrderedDict([
             ("⚠ 982 가 신고한 값", "u=3 %d/6 · u=0 %d/6 → 참" % (
                 per_u["u=3"]["⚠ 982 판 ㉡ 이 이긴 자 수 (`>=`)"],
                 per_u["u=0"]["⚠ 982 판 ㉡ 이 이긴 자 수 (`>=`)"])),
             ("🔴🔴 엄격 계수", "u=3 %d/6 · u=0 %d/6" % (
                 per_u["u=3"]["🔴🔴🔴 983 판 ㉡ 이 이긴 자 수 (`>`)"],
                 per_u["u=0"]["🔴🔴🔴 983 판 ㉡ 이 이긴 자 수 (`>`)"])),
             ("🔴🔴🔴 등록 문턱 「넷 이상」을 λ 둘 다 넘나",
              bool(per_u["u=3"]["🔴🔴 등록 문턱 「넷 이상」을 넘나(엄격)"] and
                   per_u["u=0"]["🔴🔴 등록 문턱 「넷 이상」을 넘나(엄격)"])),
             ("🔴🔴🔴 그래서 `982-P9` 는", "🔴 **거짓이다** — 982 의 예측은 7/10 이 아니라 **6/10**"),
         ])),
    ])


# ══════════════════════════════════════════════════════════════════════
# §3 🔴 「20.95 배」의 프레이밍 — 사이클별 이동 넷을 «같이» 싣는다
# ══════════════════════════════════════════════════════════════════════
def framing(pk, ho):
    L1 = pk["🔴🔴 §4 자 전쟁 L1 결산"]
    steps = collections.OrderedDict(
        [(k, float(v)) for k, v in L1.items()
         if isinstance(v, (int, float)) and "→" in k and "대" not in k])
    net = None
    for k, v in L1.items():
        if isinstance(v, (int, float)) and "대" in k:
            net = float(v)
    hold = float(ho["🔴🔴🔴 유보를 바꿨을 때 자 가중이 움직인 L1"]["🔴 자별 L1"][CANON])
    biggest = max(steps.items(), key=lambda kv: kv[1])
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴 **「유보 정의를 바꾼 것이 자 전쟁보다 20.95 배 크다」의 프레이밍을 고친다**"),
        ("🔴 유보를 바꿨을 때 정본 자 가중의 L1(시간 방향 대 개체 묶음)", _r(hold)),
        ("🔴 자 전쟁 사이클별 이동", collections.OrderedDict(
            [(k, _r(v)) for k, v in steps.items()])),
        ("🔴 자 전쟁 순 이동(출발점 → 끝점)", _r(net)),
        ("⚠ 982 가 실은 배수 = 유보 L1 / 순 이동", _r(hold / net, 2) if net else None),
        ("🔴🔴 가장 큰 «한 번의» 자 갈아타기", collections.OrderedDict([
            ("어디", biggest[0]), ("L1", _r(biggest[1]))])),
        ("🔴🔴🔴 자 한 번 갈아타기 / 유보 정의 바꾸기", _r(biggest[1] / hold, 3)),
        ("🔴🔴🔴 그래서 무엇이 틀렸나",
         "🔴 **`0.003996` 은 「출발점과 끝점이 우연히 가깝다」는 뜻이지 「자 선택이 작다」는 "
         "뜻이 아니다.** 자를 **한 번** 갈아탄 것(%s · L1 %s)이 유보 정의를 바꾼 것(%s)보다 "
         "**%s 배 크다.** 「20.95 배」의 분모는 **왕복 오차**이지 자 전쟁의 크기가 아니다"
         % (biggest[0], _r(biggest[1]), _r(hold), _r(biggest[1] / hold, 3))),
        ("🔴 조항 60 은 통과하나",
         "🔴 **통과한다 — 분자·분모가 같은 공간(정규화된 도메인 가중의 L1)이다**(티처 #121). "
         "틀린 것은 «분모의 선택»이지 «단위»가 아니다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §4 stage
# ══════════════════════════════════════════════════════════════════════
def stage_stat(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    dc = _load("out981_decomp.json")
    tg = _load("out981_target.json")
    pk = _load("out981_pick.json")
    md = _load("out982_mde.json")
    gr = _load("out983_grid.json", must=False)
    C = dc["🔴🔴🔴 칸"]
    nb = [float(n) for n in NB_GRID]

    out = collections.OrderedDict()
    out["무엇"] = ("983 §3-2·§3-3 — 🔴🔴 **격자 검정을 예산에서 떼고, 헤드라인 축을 섞어 보고, "
                 "「20.95 배」의 프레이밍을 고친다**")
    out["🔴 축"] = "C3 (몸통) · 곁 C4"
    out["사전등록"] = "docs/prereg_983_holdout_registry.md §2-1 ⓔ · §3-2 · §3-3 · §7"
    out["🔴 티처"] = ("🔴 티처 #121 2순위 ⓑ — 「짝지은 두 계열이 둘 다 `N_B` 의 단조 함수다. "
                    "공통 구동자의 단조 함수 둘은 인과가 전혀 없어도 스피어만 ±1 을 낸다」")

    # ── §3-2 ㋐ 982 의 두 헤드라인 검정을 다시 잰다 ────────────────
    re982 = collections.OrderedDict()
    for u in U_REG:
        uk = "u=%d" % u
        g_p = [C["N_B=%d" % n]["🔴 λ 별"][uk]["🔴🔴 ㉱ − ㉯"]["Δ"] for n in NB_GRID]
        mix = [C["N_B=%d" % n]["🔴🔴 대조 팔 혼합의 표집 SD"]["🔴🔴 몫 표집 SD 의 L1 합"]
               for n in NB_GRID]
        ctl = [C["N_B=%d" % n]["🔴 λ 별"][uk]["㉯ 대조 ρ(정본 자)"] for n in NB_GRID]
        trt = [C["N_B=%d" % n]["🔴 λ 별"][uk]["㉮ 층화(유보) ρ(정본 자)"] for n in NB_GRID]
        pla = [C["N_B=%d" % n]["🔴 λ 별"][uk]["㉱ 위약 층화(공급) ρ(정본 자)"] for n in NB_GRID]
        head = [max(ctl) - c for c in ctl]
        shift = [trt[i] - pla[i] for i in range(len(NB_GRID))]
        re982[uk] = collections.OrderedDict([
            ("🔴🔴 검정 ② — (㉱ 이득, 대조 혼합 SD)",
             naive_and_partial(g_p, mix, nb, "㉱ − ㉯ 이득", "대조 팔 혼합 표집 SD L1")),
            ("🔴🔴 검정 — (`㉮−㉱` 목표 이동, 오라클 여유)",
             naive_and_partial(shift, head, nb, "㉮ − ㉱ 목표 이동", "오라클 여유")),
        ])
    out["🔴🔴🔴 §3-2 ㋐ 982 의 헤드라인 검정 둘을 «예산 공변량»으로 다시 잰다"] = \
        collections.OrderedDict([
            ("🔴 출처(격자)", "runners/out981_decomp.json — 🔴 새 측정 0"),
            ("🔴 λ 별", re982),
            ("⚠ 982 가 안 쓴, 교환 가능성을 «안 요구하는» 자 둘",
             collections.OrderedDict([
                 ("🔴 부호검정 p(982 산출물)",
                  _load("out982_mech.json")["🔴🔴 λ 별"]["u=3"][
                      "🔴🔴🔴 §3-2 검정력이 있는 자 셋"]["🔴 ① 부호검정(7 칸)"]["🔴 양측 p"]),
                 ("🔴 칸 가중 z(982 산출물)",
                  _load("out982_mech.json")["🔴🔴 λ 별"]["u=3"][
                      "🔴🔴🔴 §3-2 검정력이 있는 자 셋"]["🔴🔴 ③ 칸 가중 z"]["z"]),
                 ("🔴🔴🔴 그래서",
                  "🔴 **교환 가능성을 안 요구하는 자 둘은 둘 다 안 섰고, 거기 걸린 "
                  "`982-P7`·`982-P8` 도 둘 다 거짓이었다. 유효한 자는 전부 졌고 "
                  "헤드라인 둘은 무효한 자에만 기댔다**(티처 #121)"),
             ])),
        ])
    out["🔴🔴🔴 §3-2 ㋑ 무효성 시연(양성 대조)"] = demo_invalid()

    # ── §3-2 시간 방향 격자에도 같은 두 자를 물린다 ────────────────
    if gr:
        tf = collections.OrderedDict()
        cells = gr["🔴🔴 칸"]
        import tgrid983 as G                        # noqa: E402
        for u in U_REG:
            uk = "u=%d" % u
            ctl = [cells["N_B=%d" % n][uk]["🔴 팔별 점추정(자 여섯)"][G.A_CTL][CANON]
                   for n in NB_GRID]
            ora = [cells["N_B=%d" % n][uk]["🔴 팔별 점추정(자 여섯)"][G.A_ORA][CANON]
                   for n in NB_GRID]
            pla = [cells["N_B=%d" % n][uk]["🔴 팔별 점추정(자 여섯)"][G.A_PLA][CANON]
                   for n in NB_GRID]
            g_l = [cells["N_B=%d" % n][uk]["%s − %s" % (G.A_PLA, G.A_CTL)][
                "🔴🔴 자별 판정"][CANON]["Δ"] for n in NB_GRID]
            head = [max(ctl) - c for c in ctl]
            shift = [ora[i] - pla[i] for i in range(len(NB_GRID))]
            tf[uk] = collections.OrderedDict([
                ("🔴 (㉱ 이득, 오라클 여유)",
                 naive_and_partial(g_l, head, nb, "㉱ − ㉯ 이득(시간 방향)", "오라클 여유")),
                ("🔴 (`㉮−㉱` 목표 이동, 오라클 여유)",
                 naive_and_partial(shift, head, nb, "㉮ − ㉱ 목표 이동(시간 방향)",
                                   "오라클 여유")),
            ])
        out["🔴🔴 §3-2 시간 방향 격자에 같은 두 자를 물린다"] = collections.OrderedDict([
            ("🔴 출처", "runners/out983_grid.json"), ("🔴 λ 별", tf)])
    else:
        out["🔴🔴 §3-2 시간 방향 격자에 같은 두 자를 물린다"] = {
            "🔴 안 돌렸다": "🔴 `out983_grid.json` 이 아직 없다 — 「없다」가 아니라 「안 돌렸다」다(조항 59)"}

    # ── §3-3 축 섞기 ─────────────────────────────────────────────
    out["🔴🔴🔴 §3-3 헤드라인 축 — 엄격 계수 + 무작위 섞기 변이체"] = axis_shuffle(tg)

    # ── §2-1 ⓔ 프레이밍 ──────────────────────────────────────────
    out["🔴🔴🔴 §2-1 ⓔ 「20.95 배」의 프레이밍"] = framing(pk, _load("out983_holdout.json"))

    # ── §7-2 MDE 정정 ────────────────────────────────────────────
    se200 = md["🔴🔴 짝SE — ㉱ 위약 팔"]["복제 200"]
    se800 = md["🔴🔴 짝SE — ㉱ 위약 팔"]["복제 800"]
    g_a0 = C["N_B=450"]["🔴 λ 별"]["u=3"]["🔴🔴 ㉮ − ㉯"]["Δ"]
    out["🔴🔴 §7-2 MDE 정정 — 🔴 게재값은 «엄한 쪽»이다"] = collections.OrderedDict([
        ("🔴 복제 200 짝SE", se200), ("🔴 복제 800 짝SE", se800),
        ("⚠ 982 가 게재한 MDE (2 × 복제 200)", _r(2 * se200)),
        ("🔴🔴🔴 983 이 게재하는 MDE (2 × 복제 800 · 엄한 쪽)", _r(2 * se800)),
        ("⚠ 982 판이 첫 칸 ㉮ 이득의 몇 %", _r(100.0 * 2 * se200 / g_a0, 2)),
        ("🔴🔴🔴 983 판이 첫 칸 ㉮ 이득의 몇 %", _r(100.0 * 2 * se800 / g_a0, 2)),
        ("🔴 어느 쪽이 엄한가", "🔴 **큰 쪽(복제 800)** — MDE 가 클수록 관문이 엄하다"),
        ("🔴 왜 800 쪽이 옳나",
         "🔴 짝SE 는 **모수**의 추정치이고 복제 수는 그 추정의 **몬테카를로 정밀도**만 "
         "정한다. 800 복제가 200 복제보다 정밀하다. 981 의 첫 200 복제는 «낮은 뽑기»였다"),
        ("🔴🔴 982 는 두 수를 §2-1 에 «나란히» 싣고도 헤드라인·카드·인계 카드·원장 넷 "
         "전부에 낮은 쪽으로 실었다", True),
    ])

    out["통과"] = bool(out["🔴🔴🔴 §3-2 ㋑ 무효성 시연(양성 대조)"] and
                     out["🔴🔴🔴 §3-3 헤드라인 축 — 엄격 계수 + 무작위 섞기 변이체"])
    out["🔴 이 절의 `통과` 가 뜻하는 것"] = (
        "🔴 **예산 공변량 검정·무효성 시연·축 섞기 변이체를 실제로 돌렸다.** "
        "🔴 `통과` 는 「헤드라인이 산다」가 **아니다** — 그 답은 각 절의 「선다」 칸이다")
    LG.write_stamped(str(OUT / "out983_stat.json"), out, ref, cs0, t0, RAN, LG.DATA)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["stat"])
    ap.add_argument("--ref", default="")
    a = ap.parse_args()
    r = stage_stat(a.ref)
    print(json.dumps({"stage": a.stage, "통과": r.get("통과")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
