#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""990 — **굶긴 것과 더한 것을 가른다** (축 C3 × C6 × C2).

사전등록 `docs/prereg_990_arms_rulers.md` §1 을 그대로 따른다.

🔴🔴🔴 **이 러너는 세계 자료를 «실제로» 연다** ---
  `data/ingest/sao941` · `sao959` · `sao973_hplt` 셋 + 챔피언 판 껍질(`ff753`).
  🔴 **연 경로를 `sys.addaudithook` 으로 «런타임에» 기록한다**(`조항 73-나`).

🔴 **989 의 병 셋을 구조로 막는다.**
  ⓐ **팔을 셋으로 가른다** --- `Δ(N)` 은 증강과 대체의 «합»이라 해석이 안 된다.
  ⓑ **base 는 «각 씨앗·각 겹의 자기 천장»으로 채운다** --- 989 는 씨앗 976 의 `1879` 를
     열두 측정 씨앗 전부에 물렸는데 실제 천장은 `1876~1888` 이고 `1879` 는 어느 것도 아니다.
  ⓒ **세 자(`R_pool` · `R_eq` · `R_champ`)를 «모든» 눈금·팔·씨앗에서 «전부» 기록한다.**

🔴 **`alpha977.select` 는 모듈 전역 `N_B` 를 읽는다.** 이 러너는 그 전역을 «안 건드리고»
  base 자리와 hplt 자리를 **둘 다 인자로 받는** `pick` 을 쓴다(`조항 66` --- 문턱 대신
  검사 인자화). **주행 중 남의 소스를 고치지 않는다.**

씀:
    python3 runners/world990.py --stage wiring --ref <40자 sha>
    python3 runners/world990.py --stage arms   --ref <40자 sha>
"""
import argparse
import collections
import datetime as dt
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── 🔴 §1-9 런타임 자: 연 `data/` 경로를 «전부» 기록한다 ─────────────────
_OPENED = collections.OrderedDict()


def _audit(event, args):
    if event != "open":
        return
    try:
        p = args[0]
    except Exception:                                              # noqa: BLE001
        return
    if not isinstance(p, str):
        try:
            p = os.fspath(p)
        except Exception:                                          # noqa: BLE001
            return
    if not isinstance(p, str):
        return
    try:
        rel = os.path.relpath(os.path.abspath(p), str(ROOT))
    except Exception:                                              # noqa: BLE001
        return
    if rel.startswith("data" + os.sep):
        _OPENED[rel] = _OPENED.get(rel, 0) + 1


sys.addaudithook(_audit)

import runners.alpha977 as A                       # noqa: E402
import runners.layers957 as L                      # noqa: E402
import runners.predict971 as P                     # noqa: E402
import loso974 as LO                               # noqa: E402
import ff753 as FF                                 # noqa: E402

RAN = ("runners/world990.py", "runners/alpha977.py", "runners/layers957.py",
       "runners/predict971.py", "runners/loso974.py", "runners/ff753.py")
OUT = ROOT / "runners"
PROG = OUT / "out990_progress.txt"

# ══ 사전등록 상수 (§1-4 · §7 · 측정 «전»에 박았다) ══════════════════════
SEEDS = list(range(989000, 989012))     # 🔴 989 와 «같은 씨앗»(짝 재현을 위해)
KFOLD = 5
ALPHA_H = 0.95
U_REG = 0                               # 🔴 판정 λ = 10^0
U_ALT = 3                               # 병기
KGRID = 6
THR_CARD = 0.00353                      # 🔴 자로만 쓴다 · 채택 문턱 아님
XOVER_LO, XOVER_HI = 1800, 6400         # 등록 구간 [lo, hi)
T_SPLIT = 2025.0                        # 챔피언 판 나눔

# (ㄱ) 증강 — base 고정 · hplt 사다리 11
H_RUNGS = [0, 200, 400, 800, 1710, 1800, 3200, 6080, 12800, 25600, 35641]
BASE_FIX = ("천장", 1800)               # base 고정 수준 둘
# (ㄴ) 대체 — 총량 고정 · α 사다리 8
A_RUNGS = [0.0, 0.05, 0.2, 0.4, 0.6, 0.8, 0.95, 1.0]
N_FIX = (1800, "천장")
# (ㄷ) 혼합 — 989 의 예산 사다리 14
N_RUNGS = [200, 400, 800, 1600, 1800, 2400, 3200, 4800, 6400,
           9600, 12800, 19200, 25600, None]      # None = 전량

BOOT = 2000
BOOT_SEED = 990

# 🔴🔴 **사전등록 «밖» 탐색 팔**(`docs/루프.md` ⓪ 방향 설계 — 탐색 팔).
#   🔴 **채점 분모에 «안» 든다.** 예측·반증조건 어디서도 이 칸을 «안» 읽는다.
#   (ㄴ) 대체 팔이 `α = 0.8` 과 `0.95` 사이에서 «절벽»을 보여서, 총량 1800 을 고정한 채
#   **base 행 수를 직접 흔들어** 그 절벽이 어디인지만 본다.
EXPLORE_N = 1800
EXPLORE_BASE = [0, 45, 90, 135, 180, 270, 360, 450, 540, 720, 900, 1200, 1800]

SRC_FILES = collections.OrderedDict([
    ("sao941", "data/ingest/sao941/pairs.jsonl.gz"),
    ("sao959", "data/ingest/sao959/pairs.jsonl.gz"),
    ("hplt_ko", "data/ingest/sao973_hplt/pairs.jsonl.gz"),
])


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _prog(msg):
    with open(str(PROG), "a", encoding="utf-8") as f:
        f.write("%s  [world] %s\n" % (_now(), msg))
    sys.stderr.write("%s  [world] %s\n" % (_now(), msg))
    sys.stderr.flush()


def _r(x, n=6):
    if x is None:
        return None
    x = float(x)
    return None if not np.isfinite(x) else round(x, n)


def _rl(a, n=6):
    return [_r(x, n) for x in (a.tolist() if hasattr(a, "tolist") else a)]


def code_stamp():
    out = collections.OrderedDict()
    for rel in RAN:
        p = ROOT / rel
        if p.is_file():
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def world_stamp():
    """🔴 §1-9 — **연 세계 자료의 지문**. 손으로 안 적는다."""
    out = collections.OrderedDict()
    for name, rel in SRC_FILES.items():
        p = ROOT / rel
        h = hashlib.sha256()
        with open(str(p), "rb") as f:
            while True:
                b = f.read(1 << 20)
                if not b:
                    break
                h.update(b)
        out[name] = collections.OrderedDict([
            ("경로", rel), ("바이트", int(p.stat().st_size)),
            ("sha256", h.hexdigest())])
    return out


def _stamp(ref, cs0, t0):
    return collections.OrderedDict([
        ("🔴 도장", collections.OrderedDict([
            ("ref(부른 쪽이 준 40자 sha)", ref),
            ("🔴 코드 sha256(시작)", cs0),
            ("🔴 코드 sha256(끝)", code_stamp()),
            ("🔴 코드가 주행 중 바뀌었나", cs0 != code_stamp()),
            ("시작(UTC)", t0), ("끝(UTC)", _now()),
        ])),
        ("🔴🔴🔴 §1-9 이 러너가 «연» `data/` 경로",
         collections.OrderedDict([
             ("🔴 연 `data/` 경로 수", len(_OPENED)),
             ("🔴 처음 스무 경로", list(_OPENED)[:20])])),
    ])


# ══════════════════════════════════════════════════════════════════════
# 🔴 뽑기 — base 자리와 hplt 자리를 «둘 다 인자로» 받는다. 안 채운다.
# ══════════════════════════════════════════════════════════════════════
def avail_b(pool, fold):
    """🔴 그 씨앗·그 겹의 «자기 천장»(989 는 씨앗 976 의 한 수를 열둘에 물렸다)."""
    return int((pool.fi != fold).sum())


def pick(pool, fold, nb, nh):
    """base `nb` 자리 · hplt `nh` 자리. 🔴 **모자라면 «안 채운다»** --- 모자란 수를 낸다."""
    pb = pool.perm_b[(pool.fi != fold)[pool.perm_b]]
    ph = pool.perm_h
    selb, selh = pb[:max(0, int(nb))], ph[:max(0, int(nh))]
    return selb, selh, int(max(0, nb) - len(selb)), int(max(0, nh) - len(selh))


def cell(pool, plan, lam, wmaps):
    """🔴 **모든 팔이 이 «한» 함수로 지어진다**(`조항 67`).

    `plan(fold, avail) -> (nb, nh)` 가 팔을 정한다. 반환은 «세 자» 전부.
    """
    pred = np.zeros(len(pool.yb))
    rows, sb, sh = [], 0, 0
    for j in range(KFOLD):
        nb, nh = plan(j, avail_b(pool, j))
        selb, selh, s1, s2 = pick(pool, j, nb, nh)
        sb += s1
        sh += s2
        X, y, ent, _nb = A.design(pool, selb, selh, KGRID)
        m = L.ridge_fit(X, y, lam)
        te = pool.fi == j
        pred[te] = L.ridge_pred(
            m, np.hstack([pool.Xb[te][:, :KGRID], pool.Ob[te]]))
        rows.append(int(len(y)))
    per = collections.OrderedDict()
    for d in pool.gated:
        m = pool.ho_mask[d]
        per[d] = float(P.spear(pred[m], pool.yb[m]))
    return {"per": per, "rulers": rulers(per, pool.gated, wmaps),
            "rows": rows, "부족.base": int(sb), "부족.hplt": int(sh)}


def rulers(per, doms, wmaps):
    """🔴 §1-5 — **세 자를 «전부» 낸다.** 하나라도 빠지면 `F03` 이다."""
    out = collections.OrderedDict()
    for name, w in wmaps.items():
        num = den = 0.0
        for d in doms:
            v = per[d]
            if np.isfinite(v):
                num += v * w[d]
                den += w[d]
        out[name] = float(num / den) if den > 0 else float("nan")
    return out


def build_wmaps(pool):
    """🔴 세 자의 가중을 «런타임에» 만든다 --- 손으로 안 적는다.

    `R_champ` 는 챔피언 판(898)의 도메인 유보 가중을 **공유 도메인으로 제한**한 것이다.
    """
    champ = FF.shell(FF.base()).weights(T_SPLIT)
    doms = list(pool.gated)
    miss = [d for d in doms if d not in champ]
    if miss:
        raise SystemExit("🔴 챔피언 판에 없는 게이트 도메인: %s" % miss)
    return collections.OrderedDict([
        ("R_pool 묶음", {d: float(pool.dom_ho[d]) for d in doms}),
        ("R_eq 균등", {d: 1.0 for d in doms}),
        ("R_champ 챔피언가중", {d: float(champ[d]) for d in doms}),
    ]), collections.OrderedDict((d, int(champ[d])) for d in doms)


RULER_JUDGE = "R_pool 묶음"          # 🔴🔴🔴 §1-5 ㉠ — 측정 «전»에 못 박았다
RULER_ALT = ("R_eq 균등", "R_champ 챔피언가중")


# ══ 팔 셋의 `plan` ═════════════════════════════════════════════════════
def plan_mix_H(n):
    def f(j, av):
        nh = int(round(ALPHA_H * n))
        return min(n - nh, av), nh
    return f


def plan_mix_B(n, cap=None):
    def f(j, av):
        c = av if cap is None else int(cap)
        return min(n, c), 0
    return f


def plan_fixed(nb, nh):
    def f(j, av):
        return (av if nb == "천장" else min(int(nb), av)), int(nh)
    return f


def plan_sub(n, alpha):
    def f(j, av):
        nh = int(round(alpha * n))
        return min(n - nh, av), nh
    return f


# ══ 자 ════════════════════════════════════════════════════════════════
def cluster_se(dd, w):
    """🔴 §1-6 — **도메인 군집 SE**. 식을 사전등록에 «측정 전에» 박았다.

    `Δ = Σ_d w_d Δ_d` (`Σ w_d = 1`) 일 때
    **`SE² = (G/(G−1)) · Σ_d w_d² (Δ_d − Δ)²`**.
    """
    ks = list(dd)
    G = len(ks)
    tw = sum(w[d] for d in ks)
    ws = {d: w[d] / tw for d in ks}
    delta = sum(ws[d] * dd[d] for d in ks)
    v = (G / float(G - 1)) * sum(ws[d] ** 2 * (dd[d] - delta) ** 2 for d in ks)
    return float(delta), float(math.sqrt(v))


def lodo(dd, w):
    """🔴 §1-8 — **도메인 하나를 빼고** 남은 것의 가중으로 다시 낸다."""
    out = collections.OrderedDict()
    for drop in dd:
        ks = [d for d in dd if d != drop]
        tw = sum(w[d] for d in ks)
        out[drop] = float(sum(w[d] * dd[d] for d in ks) / tw)
    return out


def crossover(xs, ds):
    """음 → 양으로 «처음» 바뀌는 두 눈금 사이의 로그 선형 보간."""
    for i in range(1, len(xs)):
        a_, b_ = ds[i - 1], ds[i]
        if a_ is None or b_ is None:
            continue
        if a_ < 0 <= b_:
            la, lb = math.log(xs[i - 1]), math.log(xs[i])
            t = (0.0 - a_) / (b_ - a_)
            return math.exp(la + t * (lb - la)), xs[i - 1], xs[i]
    return None, None, None


# ══════════════════════════════════════════════════════════════════════
def stage_wiring(ref):
    t0 = _now()
    cs0 = code_stamp()
    pool = A.Pool()
    wmaps, champ_w = build_wmaps(pool)
    checks = collections.OrderedDict()

    def add(name, ok, mut_ok, hits, why):
        checks[name] = collections.OrderedDict([
            ("통과", bool(ok)),
            ("🔴 변이체(일부러 깨뜨린 판)에서도 통과하나", bool(mut_ok)),
            ("🔴 구성상 참인가(변이체가 «안» 떨어졌다)", bool(mut_ok)),
            ("🔴 걸린 자리(= 이 검사가 «비교»를 «수행»한 회수)", int(hits)),
            ("왜", why)])

    # ── W1 (ㄷ) 팔 H 의 뽑기가 `alpha977.select`(N_B=1800)와 색인까지 같은가 ──
    same, mut, hits = [], [], 0
    for s in SEEDS[:3]:
        pool.reseed(s)
        for j in range(KFOLD):
            b0, h0, _ = A.select(pool, j, ALPHA_H)          # 977 전역 N_B = 1800
            nb, nh = plan_mix_H(1800)(j, avail_b(pool, j))
            b1, h1, _s1, _s2 = pick(pool, j, nb, nh)
            nb2, nh2 = plan_mix_H(1801)(j, avail_b(pool, j))
            b2, h2, _s3, _s4 = pick(pool, j, nb2, nh2)
            same.append(np.array_equal(b0, b1) and np.array_equal(h0, h1))
            mut.append(np.array_equal(b0, b2) and np.array_equal(h0, h2))
            hits += 2
    add("W1 (ㄷ) 팔 H 의 뽑기가 `alpha977.select`(N_B=1800)와 «색인까지» 같다",
        all(same), all(mut), hits,
        "🔴 변이체 = 예산 1801 — 참이면 이 검사가 예산을 «안 본다»")

    # ── W2 🔴 팔 B 는 «안 채운다» · 🔴 구판/신판 전후(조항 66-⑥) ────────
    okB, mutB, hits = [], [], 0
    pool.reseed(A.SEEDS[0])                        # 씨앗 976 = 989 가 쓴 천장의 출처
    cap976 = int(min(avail_b(pool, j) for j in range(KFOLD)))
    ceil_by_seed = collections.OrderedDict()
    for s in SEEDS:
        pool.reseed(s)
        per_fold = [avail_b(pool, j) for j in range(KFOLD)]
        ceil_by_seed[str(s)] = {"겹별": per_fold, "최소": int(min(per_fold))}
        for j in range(KFOLD):
            av = avail_b(pool, j)
            b_hi, h_hi, s1, _s2 = pick(pool, j, 25600, 0)
            okB.append(len(h_hi) == 0 and len(b_hi) == av and s1 == 25600 - av)
            # 🔴 변이체 = **채우는** 뽑기(base 가 모자란 만큼 hplt 로 메운다).
            #    989 의 변이체(`alpha977.select(alpha=0)`)는 `nh = 0` 이라 «채울 것이 없어»
            #    원리상 안 떨어진다 --- 990 이 그것을 실측하고 자를 고쳤다.
            bm, hm, sm, _sm2 = pick(pool, j, 25600, 0)
            if sm > 0:
                hm = pool.perm_h[:sm]
            mutB.append(len(hm) == 0)
            hits += 2
    # 🔴 989 판 변이체가 «원리상» 안 떨어지는 것을 실측으로 남긴다(조항 66-⑥ 구판/신판)
    old_mut = []
    for j in range(KFOLD):
        _bf, hf, _s = A.select(pool, j, 0.0)        # 989 가 쓴 변이체
        old_mut.append(len(hf) == 0)
    w2_ba = collections.OrderedDict([
        ("🔴 989 판 변이체(`alpha977.select(alpha=0)`)가 «안 떨어지나»", bool(all(old_mut))),
        ("🔴 왜", "🔴 `alpha=0` 이면 `nh = 0` 이라 «채울 hplt 자리 자체가 없다» — "
                "그 변이체는 «어떤 구현으로도 안 떨어진다»(공허한 변이체)"),
        ("🔴 990 판 변이체(base 모자람을 hplt 로 메운다)가 «안 떨어지나»", bool(all(mutB))),
        ("🔴 구판/신판이 갈리나", bool(all(old_mut) != all(mutB))),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", int(len(old_mut) + len(mutB))),
        ("통과", bool(all(old_mut) != all(mutB))),
    ])
    add("W2 (ㄷ) 팔 B 는 «각 겹의 자기 천장»에서 멈춘다(HPLT 로 «안» 채운다)",
        all(okB), all(mutB), hits,
        "🔴 변이체 = **채우는 뽑기**(base 모자람을 hplt 로 메운다) — 떨어져야 한다. "
        "🔴 989 는 이 자를 「겹 최소」와 견줘 «구판이 떨어졌고» 자를 고쳤는데 «구판 실측값을 안 남겼다»")

    # ── W3 🔴 유보는 어떤 예산에서도 학습에 «안 닿는다» ─────────────────
    tr_hit, mut_hit, hits = 0, 0, 0
    for s in SEEDS[:3]:
        pool.reseed(s)
        for j in range(KFOLD):
            b, _h, _s1, _s2 = pick(pool, j, 37531, 35641)
            tr_hit += int((pool.fi[b] == j).sum())
            # 🔴 변이체 = 「새는」 뽑기(겹을 안 걸러 base 전량에서 뽑는다)
            bm = pool.perm_b[:37531]
            mut_hit += int((pool.fi[bm] == j).sum())
            hits += len(b)
    add("W3 어떤 예산에서도 학습이 «그 겹의 유보 행»을 안 쓴다",
        tr_hit == 0, mut_hit == 0, hits,
        "🔴 겹 j 의 학습 색인 중 `fi == j` 인 것의 수를 «전수» 센다 — 0 이어야 한다. "
        "🔴 변이체 = 겹을 «안 거른» 뽑기(`perm_b[:N]`) — 유보를 %d 자리 밟는다" % mut_hit)

    # ── W4 🔴 977 재현 — 🔴 «독립» 재현이 아니다. 그렇게 적는다 ─────────
    rep_vals = []
    for seed in A.SEEDS:
        pool.reseed(seed)
        r = A.oof(pool, 0.95, 10.0 ** U_REG, KGRID)
        p_, _e, _pr = A.score(pool, r["예측"])
        rep_vals.append(float(p_))
    got = float(np.mean(rep_vals))
    want = 0.3596                    # `out977_grid.json` 의 `u=0|α=0.95` 묶음 ρ(공표 4자리)
    add("W4 977 의 `u=0|α=0.95` 묶음 ρ 를 «977 자기 씨앗·자기 함수»로 다시 내면 공표값과 같다",
        abs(got - want) <= 5e-4, abs(got - 0.4596) <= 5e-4, len(A.SEEDS),
        "🔴 변이체 = 공표값 + 0.1. 🔴🔴 **이것은 «독립» 재현이 «아니다»** — 977 자기 함수를 "
        "977 자기 씨앗으로 돌린 것이고, 공표값이 «4자리»라 그보다 촘촘한 차이는 원리상 주장 못 한다")

    # ── W5 🔴 자료 지문 ────────────────────────────────────────────────
    ws = world_stamp()
    # 🔴 변이체 = 없는 경로 하나를 원천 목록에 끼운 판 — 떨어져야 한다
    mut_ws = dict(ws)
    mut_ws["🔴 없는 경로"] = {"바이트": 0}
    add("W5 세 세계 자료 파일이 «전부» 열렸고 지문이 났다",
        len(ws) == 3 and all(v["바이트"] > 0 for v in ws.values()),
        len(mut_ws) == 3 and all(v["바이트"] > 0 for v in mut_ws.values()),
        len(ws) * 2,
        "🔴 바이트 0 이면 못 읽은 것이다. 🔴 변이체 = 없는 경로를 하나 끼운 원천 목록")

    # ── W6 🔴🔴🔴 §1-1 분해 항등식 `A(N) + S(N) ≡ Δ(N)` ────────────────
    pool.reseed(SEEDS[0])
    resid, hits = [], 0
    for n in (1800, 3200, 6400):
        nh = int(round(ALPHA_H * n))
        c_HB = cell(pool, plan_mix_H(n), 1.0, wmaps)          # base n−nh + hplt nh
        c_B = cell(pool, plan_mix_B(n), 1.0, wmaps)           # base min(n, av)
        c_M = cell(pool, plan_fixed(n, nh), 1.0, wmaps)       # base min(n, av) + hplt nh
        for rn in wmaps:
            aug = c_M["rulers"][rn] - c_B["rulers"][rn]
            sta = c_HB["rulers"][rn] - c_M["rulers"][rn]
            dlt = c_HB["rulers"][rn] - c_B["rulers"][rn]
            resid.append(abs((aug + sta) - dlt))
            hits += 1
    add("W6 🔴🔴🔴 분해 항등식 — 증강 `A(N)` + 굶김 `S(N)` == `Δ(N)`",
        max(resid) < 1e-12, max(resid) > 1e-3, hits,
        "🔴 세 눈금 × 세 자 아홉 자리에서 잔차를 «전수» 잰다. 🔴 변이체 = 잔차 문턱 1e-3 "
        "(참이면 이 검사가 «어떤 값으로도 안 떨어진다»)")

    # ── W7 🔴🔴 세 자가 «서로 다른» 자인가 ─────────────────────────────
    pool.reseed(SEEDS[0])
    c = cell(pool, plan_mix_H(1800), 1.0, wmaps)
    vals = [c["rulers"][k] for k in wmaps]
    pairs = [abs(vals[i] - vals[k]) for i in range(3) for k in range(i + 1, 3)]
    # 🔴 변이체 = 세 자에 «같은» 가중을 물린 판 — 떨어져야 한다
    same_w = collections.OrderedDict((k, wmaps[RULER_JUDGE]) for k in wmaps)
    mv = list(rulers(c["per"], pool.gated, same_w).values())
    mpairs = [abs(mv[i] - mv[k]) for i in range(3) for k in range(i + 1, 3)]
    add("W7 🔴🔴 세 자가 «서로 다른 값»을 낸다(병기가 무의미하지 않다)",
        min(pairs) > 1e-9, min(mpairs) > 1e-9, len(pairs) + len(mpairs),
        "🔴 같은 도메인별 ρ 에 세 가중을 물려 세 쌍의 차를 «전수» 잰다 — "
        "🔴 셋이 같으면 「세 자를 병기했다」가 «공허»하다. "
        "🔴 변이체 = 세 자에 «같은» 가중을 물린 판")

    n_ok = len([1 for v in checks.values() if v["통과"]])
    n_const = len([1 for v in checks.values()
                   if v["🔴 구성상 참인가(변이체가 «안» 떨어졌다)"]])
    res = collections.OrderedDict([
        ("무엇", "990 §1 배선 — 🔴 **세 팔·세 자의 배선**"),
        ("🔴 축", "C3 × C6 × C2"),
        ("사전등록", "docs/prereg_990_arms_rulers.md §1"),
        ("🔴🔴🔴 세계 자료(런타임 지문)", ws),
        ("🔴 자료 행", collections.OrderedDict([
            ("base 행(= 유보 전량)", int(len(pool.yb))),
            ("🔴 게이트 유보 행 합",
             int(sum(int(pool.ho_mask[d].sum()) for d in pool.gated))),
            ("🔴 게이트 밖 base 행",
             int(len(pool.yb)) - int(sum(int(pool.ho_mask[d].sum())
                                         for d in pool.gated))),
            ("hplt 행(= 학습에만)", int(len(pool.yh))),
            ("게이트 도메인", list(pool.gated)),
            ("🔴 977 의 예산 상수 N_B", int(A.N_B)),
            ("🔴 그 상수가 만든 hplt 학습 행", int(round(ALPHA_H * A.N_B))),
            ("🔴 그 상수가 남긴 base 학습 행", int(A.N_B - round(ALPHA_H * A.N_B))),
        ])),
        ("🔴🔴🔴 ⓑ 씨앗별 base 천장(989 는 «한 수»를 열둘에 물렸다)",
         collections.OrderedDict([
             ("씨앗별", ceil_by_seed),
             ("🔴 씨앗 976 의 겹 최소(= 989 가 쓴 수)", cap976),
             ("🔴 측정 씨앗 열둘의 겹 최소 범위",
              [int(min(v["최소"] for v in ceil_by_seed.values())),
               int(max(v["최소"] for v in ceil_by_seed.values()))]),
             ("🔴🔴🔴 989 가 쓴 수가 측정 씨앗 «어느» 천장인가",
              [s for s, v in ceil_by_seed.items() if v["최소"] == cap976] or
              "🔴 **어느 씨앗의 천장도 아니다**"),
         ])),
        ("🔴 세 자의 가중(런타임)", collections.OrderedDict([
            ("R_pool 묶음", {d: int(pool.dom_ho[d]) for d in pool.gated}),
            ("R_eq 균등", {d: 1 for d in pool.gated}),
            ("R_champ 챔피언가중", champ_w),
            ("🔴 판정 자", RULER_JUDGE),
            ("🔴 병기 자", list(RULER_ALT)),
        ])),
        ("🔴 W2 변이체의 구판/신판(조항 66-⑥) — 989 의 변이체는 «공허»했다", w2_ba),
        ("배선 검사", checks),
        ("🔴 배선 검사 수", len(checks)),
        ("🔴 통과 수", n_ok),
        ("🔴 구성상 참인 검사 수(변이체가 안 떨어진 것)", n_const),
        ("🔴 걸린 자리 합",
         int(sum(v["🔴 걸린 자리(= 이 검사가 «비교»를 «수행»한 회수)"]
                 for v in checks.values()))),
        ("통과", bool(n_ok == len(checks))),
        ("🔴 이 절의 통과가 뜻하는 것",
         "🔴 세 팔이 «한» 함수로 지어졌고, base 가 «자기 천장»으로 차고, "
         "유보가 학습에 안 닿고, 분해가 항등식이고, 세 자가 «서로 다르다»"),
    ])
    res.update(_stamp(ref, cs0, t0))
    return res


# ══════════════════════════════════════════════════════════════════════
def stage_arms(ref):
    t0 = _now()
    cs0 = code_stamp()
    pool = A.Pool()
    wmaps, champ_w = build_wmaps(pool)
    RN = list(wmaps)
    lams = ((U_REG, 10.0 ** U_REG), (U_ALT, 10.0 ** U_ALT))
    doms = list(pool.gated)
    t_start = time.time()

    # 🔴 raw[u][key] = {"ruler": {자: [씨앗]}, "per": {도메인: [씨앗]}, ...}
    raw = {u: collections.OrderedDict() for u, _ in lams}

    def put(u, key, c):
        slot = raw[u].setdefault(key, {"ruler": {k: [] for k in RN},
                                       "per": {d: [] for d in doms},
                                       "rows": None, "부족.base": [],
                                       "부족.hplt": []})
        for k in RN:
            slot["ruler"][k].append(c["rulers"][k])
        for d in doms:
            slot["per"][d].append(c["per"][d])
        slot["rows"] = c["rows"]
        slot["부족.base"].append(c["부족.base"])
        slot["부족.hplt"].append(c["부족.hplt"])

    # 🔴 씨앗 976 의 천장 — 989 의 «구판»을 재현하기 위해서만 쓴다
    pool.reseed(A.SEEDS[0])
    cap976 = int(min(avail_b(pool, j) for j in range(KFOLD)))

    ncell = 0
    nexplore_cell = [0]
    for si, seed in enumerate(SEEDS):
        pool.reseed(seed)
        cap_seed = int(min(avail_b(pool, j) for j in range(KFOLD)))
        for u, lam in lams:
            # (ㄷ) 혼합
            for n in N_RUNGS:
                nn = 37531 if n is None else n
                put(u, ("혼합.H", nn), cell(pool, plan_mix_H(nn), lam, wmaps))
                put(u, ("혼합.B", nn), cell(pool, plan_mix_B(nn), lam, wmaps))
                put(u, ("혼합.B구판976", nn),
                    cell(pool, plan_mix_B(nn, cap976), lam, wmaps))
                nh = int(round(ALPHA_H * nn))
                put(u, ("혼합.M", nn), cell(pool, plan_fixed(nn, nh), lam, wmaps))
                ncell += 4
            # (ㄱ) 증강
            for bf in BASE_FIX:
                for h in H_RUNGS:
                    put(u, ("증강.%s" % bf, h),
                        cell(pool, plan_fixed(bf, h), lam, wmaps))
                    ncell += 1
            # (ㄴ) 대체
            for nf in N_FIX:
                nn = cap_seed if nf == "천장" else nf
                for al in A_RUNGS:
                    put(u, ("대체.%s" % nf, al),
                        cell(pool, plan_sub(nn, al), lam, wmaps))
                    ncell += 1
        # 🔴 탐색 팔 — 판정 λ 에서만 · 채점 분모 «밖»
        for nb in EXPLORE_BASE:
            put(U_REG, ("탐색.base", nb),
                cell(pool, plan_fixed(nb, EXPLORE_N - nb), 10.0 ** U_REG, wmaps))
            nexplore_cell[0] += 1
        _prog("씨앗 %d/%d (%d · 천장 %d) — 칸 %d · %.1fs"
              % (si + 1, len(SEEDS), seed, cap_seed, ncell, time.time() - t_start))

    # ══ 집계 ══════════════════════════════════════════════════════════
    def arr(u, key, rn):
        return np.asarray(raw[u][key]["ruler"][rn], float)

    def perarr(u, key, d):
        return np.asarray(raw[u][key]["per"][d], float)

    def delta_block(u, ka, kb, rn, w):
        """🔴 두 칸의 «짝» Δ — 씨앗 SE · 도메인 군집 SE · LODO 를 «전부» 낸다."""
        a, b = arr(u, ka, rn), arr(u, kb, rn)
        d = a - b
        se_seed = float(np.std(d, ddof=1) / math.sqrt(len(d)))
        dd = collections.OrderedDict(
            (x, float(np.mean(perarr(u, ka, x) - perarr(u, kb, x)))) for x in doms)
        delta, se_clu = cluster_se(dd, w)
        lo = lodo(dd, w)
        flip = [x for x, v in lo.items() if (v > 0) != (delta > 0)]
        return collections.OrderedDict([
            ("🔴 팔 앞 ρ", _r(float(a.mean()))),
            ("🔴 팔 뒤 ρ", _r(float(b.mean()))),
            ("🔴🔴🔴 Δ", _r(float(d.mean()))),
            ("🔴 Δ(도메인 가중 합 · 항등식 확인)", _r(delta)),
            ("🔴 씨앗 SE", _r(se_seed)),
            ("🔴 Δ / 씨앗 SE", _r(float(d.mean() / se_seed)) if se_seed else None),
            ("🔴🔴🔴 도메인 군집 SE", _r(se_clu)),
            ("🔴🔴🔴 t_clu = Δ / 군집 SE", _r(delta / se_clu) if se_clu else None),
            ("🔴🔴 |t_clu| >= 2 인가", bool(se_clu and abs(delta / se_clu) >= 2.0)),
            ("🔴 씨앗별 Δ", _rl(d)),
            ("🔴 도메인별 Δ_d", collections.OrderedDict((k, _r(v)) for k, v in dd.items())),
            ("🔴🔴 LODO — 도메인 하나를 빼고 다시 낸 Δ",
             collections.OrderedDict((k, _r(v)) for k, v in lo.items())),
            ("🔴🔴🔴 LODO 에서 부호가 뒤집히는 도메인", flip or "없음"),
            ("🔴🔴🔴 LODO 부호 뒤집힌 도메인 수", len(flip)),
        ])

    W = {rn: wmaps[rn] for rn in RN}

    # ── §1 (ㄷ) 혼합 사다리 ────────────────────────────────────────────
    mix = collections.OrderedDict()
    for u, _l in lams:
        per_rn = collections.OrderedDict()
        for rn in RN:
            per_n = collections.OrderedDict()
            for n in N_RUNGS:
                nn = 37531 if n is None else n
                blk = delta_block(u, ("혼합.H", nn), ("혼합.B", nn), rn, W[rn])
                blk["🔴 팔 B 구판(씨앗 976 천장 %d)으로 잰 Δ" % cap976] = _r(float(
                    (arr(u, ("혼합.H", nn), rn)
                     - arr(u, ("혼합.B구판976", nn), rn)).mean()))
                blk["🔴 구판−신판 차"] = _r(
                    blk["🔴 팔 B 구판(씨앗 976 천장 %d)으로 잰 Δ" % cap976]
                    - blk["🔴🔴🔴 Δ"])
                blk["🔴 팔 B 예산 미달(씨앗 최대 · = 자료 천장에 닿았다)"] = int(
                    max(raw[u][("혼합.B", nn)]["부족.base"]))
                blk["🔴 팔 H 겹별 학습 행"] = raw[u][("혼합.H", nn)]["rows"]
                blk["🔴 팔 B 겹별 학습 행"] = raw[u][("혼합.B", nn)]["rows"]
                per_n[str(nn)] = blk
            per_rn[rn] = per_n
        mix[str(u)] = per_rn

    # ── §2 (ㄱ) 증강 사다리 ────────────────────────────────────────────
    aug = collections.OrderedDict()
    for u, _l in lams:
        per_rn = collections.OrderedDict()
        for rn in RN:
            per_bf = collections.OrderedDict()
            for bf in BASE_FIX:
                per_h = collections.OrderedDict()
                for h in H_RUNGS:
                    if h == 0:
                        continue
                    per_h[str(h)] = delta_block(
                        u, ("증강.%s" % bf, h), ("증강.%s" % bf, 0), rn, W[rn])
                per_bf[str(bf)] = collections.OrderedDict([
                    ("🔴 눈금별 Δ(= hplt 를 «더한» 효과)", per_h),
                    ("🔴 눈금별 ρ", collections.OrderedDict(
                        (str(h), _r(float(arr(u, ("증강.%s" % bf, h), rn).mean())))
                        for h in H_RUNGS)),
                    ("🔴🔴🔴 ρ 가 h 에 «단조 증가»인가", bool(all(
                        arr(u, ("증강.%s" % bf, H_RUNGS[i]), rn).mean()
                        <= arr(u, ("증강.%s" % bf, H_RUNGS[i + 1]), rn).mean() + 1e-15
                        for i in range(len(H_RUNGS) - 1)))),
                    ("🔴🔴🔴 h = 0 보다 «나쁜» 눈금", [
                        h for h in H_RUNGS[1:]
                        if arr(u, ("증강.%s" % bf, h), rn).mean()
                        < arr(u, ("증강.%s" % bf, 0), rn).mean()] or "없음"),
                    ("🔴🔴 2·SE_clu 를 넘은 눈금",
                     [h for h in H_RUNGS[1:]
                      if per_h[str(h)]["🔴🔴 |t_clu| >= 2 인가"]] or "없음"),
                    ("🔴🔴 2·SE_clu 를 넘은 눈금 수",
                     len([h for h in H_RUNGS[1:]
                          if per_h[str(h)]["🔴🔴 |t_clu| >= 2 인가"]])),
                ])
            per_rn[rn] = per_bf
        aug[str(u)] = per_rn

    # ── §3 (ㄴ) 대체 사다리 ────────────────────────────────────────────
    sub = collections.OrderedDict()
    for u, _l in lams:
        per_rn = collections.OrderedDict()
        for rn in RN:
            per_nf = collections.OrderedDict()
            for nf in N_FIX:
                rs = [float(arr(u, ("대체.%s" % nf, al), rn).mean()) for al in A_RUNGS]
                per_nf[str(nf)] = collections.OrderedDict([
                    ("🔴 α 별 ρ", collections.OrderedDict(
                        (str(al), _r(v)) for al, v in zip(A_RUNGS, rs))),
                    ("🔴🔴🔴 ρ 가 α 에 «단조 감소»인가",
                     bool(all(rs[i] >= rs[i + 1] - 1e-15 for i in range(len(rs) - 1)))),
                    ("🔴 α=0 대비 α=0.95 의 Δ",
                     _r(float((arr(u, ("대체.%s" % nf, 0.95), rn)
                               - arr(u, ("대체.%s" % nf, 0.0), rn)).mean()))),
                    ("🔴 그 Δ 의 블록",
                     delta_block(u, ("대체.%s" % nf, 0.95),
                                 ("대체.%s" % nf, 0.0), rn, W[rn])),
                    ("🔴 α 별 겹별 학습 행", collections.OrderedDict(
                        (str(al), raw[u][("대체.%s" % nf, al)]["rows"])
                        for al in A_RUNGS)),
                ])
            per_rn[rn] = per_nf
        sub[str(u)] = per_rn

    # ── §4 🔴🔴🔴 분해 — 989 의 `Δ(1800)` 을 두 성분으로 가른다 ─────────
    decomp = collections.OrderedDict()
    for rn in RN:
        per_n = collections.OrderedDict()
        for n in N_RUNGS:
            nn = 37531 if n is None else n
            hh = arr(U_REG, ("혼합.H", nn), rn)
            bb = arr(U_REG, ("혼합.B", nn), rn)
            mm = arr(U_REG, ("혼합.M", nn), rn)
            a_ = float((mm - bb).mean())          # 증강
            s_ = float((hh - mm).mean())          # 굶김
            d_ = float((hh - bb).mean())
            per_n[str(nn)] = collections.OrderedDict([
                ("🔴🔴🔴 Δ(N)", _r(d_)),
                ("🔴 ① 증강 A(N) = ρ(base N + hplt αN) − ρ(base N)", _r(a_, 8)),
                ("🔴 ② 굶김 S(N) = ρ(base (1−α)N + hplt αN) − ρ(base N + hplt αN)",
                 _r(s_, 8)),
                ("🔴 A + S", _r(a_ + s_, 8)),
                ("🔴 잔차 |A + S − Δ|", _r(abs(a_ + s_ - d_), 12)),
                ("🔴🔴🔴 굶김이 차지하는 몫",
                 _r(abs(s_) / (abs(a_) + abs(s_)), 4) if (abs(a_) + abs(s_)) > 0 else None),
                ("🔴🔴🔴 증강이 차지하는 몫",
                 _r(abs(a_) / (abs(a_) + abs(s_)), 4) if (abs(a_) + abs(s_)) > 0 else None),
                ("🔴 base 학습 행(팔 H)", int(nn - round(ALPHA_H * nn))),
                ("🔴 hplt 학습 행(팔 H)", int(round(ALPHA_H * nn))),
            ])
        decomp[rn] = per_n

    # ── §5 🔴🔴🔴 판정 ────────────────────────────────────────────────
    xs = [float(37531 if n is None else n) for n in N_RUNGS]

    def dser(u, rn):
        return [mix[str(u)][rn][str(int(x))]["🔴🔴🔴 Δ"] for x in xs]

    nstar = {}
    for rn in RN:
        v, lo_, hi_ = crossover(xs, dser(U_REG, rn))
        nstar[rn] = (v, lo_, hi_)

    # 🔴 §1-7 — 씨앗별 N* 와 붓스트랩 구간
    def seed_nstar(rn):
        out = []
        mats = np.asarray([
            (arr(U_REG, ("혼합.H", int(x)), rn) - arr(U_REG, ("혼합.B", int(x)), rn))
            for x in xs], float)                      # (눈금, 씨앗)
        for si in range(len(SEEDS)):
            v, _l, _h = crossover(xs, [float(mats[i, si]) for i in range(len(xs))])
            out.append(v)
        return out, mats

    ns_seed, mats_pool = seed_nstar(RULER_JUDGE)
    rng = np.random.RandomState(BOOT_SEED)
    boot = []
    for _b in range(BOOT):
        idx = rng.randint(0, len(SEEDS), len(SEEDS))
        v, _l, _h = crossover(xs, [float(mats_pool[i, idx].mean())
                                   for i in range(len(xs))])
        if v is not None:
            boot.append(v)
    bootarr = np.asarray(boot, float) if boot else np.asarray([np.nan])

    top = str(int(xs[-1]))
    judge = collections.OrderedDict()
    judge["🔴🔴🔴 판정 자(측정 «전»에 못 박았다)"] = RULER_JUDGE
    judge["🔴 판정 자의 근거"] = "docs/목표.md:164 — 981~ 정본 자는 `R_pool 묶음`(w ∝ n_d)"
    judge["🔴 판정 λ"] = "u = %d (10^%d)" % (U_REG, U_REG)
    judge["🔴 판정 SE"] = "도메인 군집 SE(사전등록 §1-6 식)"
    for rn in RN:
        m1800 = mix[str(U_REG)][rn]["1800"]
        mtop = mix[str(U_REG)][rn][top]
        judge["🔴 %s Δ(1800)" % rn] = m1800["🔴🔴🔴 Δ"]
        judge["🔴 %s Δ(1800) > 0" % rn] = bool(m1800["🔴🔴🔴 Δ"] > 0)
        judge["🔴 %s Δ(1800) t_clu" % rn] = m1800["🔴🔴🔴 t_clu = Δ / 군집 SE"]
        judge["🔴 %s Δ(1800) 씨앗 SE 비" % rn] = m1800["🔴 Δ / 씨앗 SE"]
        judge["🔴 %s Δ(천장)" % rn] = mtop["🔴🔴🔴 Δ"]
        judge["🔴 %s Δ(천장) 군집 SE" % rn] = mtop["🔴🔴🔴 도메인 군집 SE"]
        judge["🔴 %s Δ(천장) t_clu" % rn] = mtop["🔴🔴🔴 t_clu = Δ / 군집 SE"]
        judge["🔴 %s Δ(천장) 씨앗 SE 비" % rn] = mtop["🔴 Δ / 씨앗 SE"]
        judge["🔴 %s N*" % rn] = _r(nstar[rn][0], 1) if nstar[rn][0] else None
        judge["🔴 %s N* 를 낀 두 눈금" % rn] = [nstar[rn][1], nstar[rn][2]]
        judge["🔴 %s LODO 부호 뒤집힌 도메인(천장)" % rn] = \
            mtop["🔴🔴🔴 LODO 에서 부호가 뒤집히는 도메인"]

    # 🔴🔴🔴 자 전쟁 — 판정 자와 병기 자가 «갈리나»
    sg = {rn: bool(mix[str(U_REG)][rn]["1800"]["🔴🔴🔴 Δ"] > 0) for rn in RN}
    sgt = {rn: bool(mix[str(U_REG)][rn][top]["🔴🔴🔴 Δ"] > 0) for rn in RN}
    split1800 = [rn for rn in RULER_ALT if sg[rn] != sg[RULER_JUDGE]]
    splittop = [rn for rn in RULER_ALT if sgt[rn] != sgt[RULER_JUDGE]]
    judge["🔴🔴🔴 1800 에서 판정 자와 «부호가 갈린» 병기 자"] = split1800 or "없음"
    judge["🔴🔴🔴 천장에서 판정 자와 «부호가 갈린» 병기 자"] = splittop or "없음"
    judge["🔴🔴🔴 자에 따라 답이 «뒤집히나»"] = bool(split1800 or splittop)
    judge["🔴🔴🔴 판정문 «맨 위»에 실어야 하는 한 줄"] = (
        "🔴 **판정 자(`%s`)와 병기 자(%s)가 «반대 부호»를 낸다 — "
        "「HPLT 가 손해다」는 자료의 사실이 아니라 «자의 도메인 가중»의 사실이다.**"
        % (RULER_JUDGE, " · ".join(split1800 or splittop))
        if (split1800 or splittop) else "🔴 세 자가 «같은 부호»다 — 자 전쟁은 없다")

    # 🔴 예측이 읽는 칸
    judge["🔴 R_champ Δ(1800) > 0"] = bool(
        mix[str(U_REG)]["R_champ 챔피언가중"]["1800"]["🔴🔴🔴 Δ"] > 0)
    judge["🔴 (ㄱ) 천장base — 2·SE_clu 를 넘은 눈금 수"] = \
        aug[str(U_REG)][RULER_JUDGE]["천장"]["🔴🔴 2·SE_clu 를 넘은 눈금 수"]
    judge["🔴 (ㄴ) N=1800 묶음 ρ 가 α 에 단조 감소인가"] = \
        sub[str(U_REG)][RULER_JUDGE]["1800"]["🔴🔴🔴 ρ 가 α 에 «단조 감소»인가"]
    judge["🔴 (ㄱ) LODO 부호 뒤집힌 도메인 수"] = \
        aug[str(U_REG)][RULER_JUDGE]["천장"][
            "🔴 눈금별 Δ(= hplt 를 «더한» 효과)"]["35641"]["🔴🔴🔴 LODO 부호 뒤집힌 도메인 수"]

    # 🔴 §1-7 N* 는 «구간»으로
    nsv = [x for x in ns_seed if x is not None]
    judge["🔴🔴🔴 N* — 점이 아니라 구간"] = collections.OrderedDict([
        ("🔴 판정 자 평균 Δ 사다리의 N*", _r(nstar[RULER_JUDGE][0], 1)
         if nstar[RULER_JUDGE][0] else None),
        ("🔴 씨앗별 N*", [(_r(x, 1) if x is not None else None) for x in ns_seed]),
        ("🔴 씨앗별 N* 가 «있는» 씨앗 수", len(nsv)),
        ("🔴🔴 씨앗별 N* 최소", _r(min(nsv), 1) if nsv else None),
        ("🔴🔴 씨앗별 N* 최대", _r(max(nsv), 1) if nsv else None),
        ("🔴 씨앗 붓스트랩 B", BOOT),
        ("🔴 붓스트랩에서 교차가 «있었던» 뽑기 수", int(len(boot))),
        ("🔴🔴🔴 붓스트랩 2.5% ~ 97.5%",
         [_r(float(np.percentile(bootarr, 2.5)), 1),
          _r(float(np.percentile(bootarr, 97.5)), 1)] if boot else "없음"),
        ("🔴 등록 구간", [XOVER_LO, XOVER_HI]),
        ("🔴🔴 붓스트랩 구간이 등록 구간 «안»에 다 드나",
         bool(boot and np.percentile(bootarr, 2.5) >= XOVER_LO
              and np.percentile(bootarr, 97.5) < XOVER_HI)),
    ])

    # 🔴 §1-1 W1 의 한 줄
    d1800 = decomp[RULER_JUDGE]["1800"]
    judge["🔴🔴🔴 W1 — Δ(1800) 의 기전"] = collections.OrderedDict([
        ("Δ(1800)", d1800["🔴🔴🔴 Δ(N)"]),
        ("증강분", d1800["🔴 ① 증강 A(N) = ρ(base N + hplt αN) − ρ(base N)"]),
        ("굶김분",
         d1800["🔴 ② 굶김 S(N) = ρ(base (1−α)N + hplt αN) − ρ(base N + hplt αN)"]),
        ("🔴🔴🔴 굶김이 차지하는 몫", d1800["🔴🔴🔴 굶김이 차지하는 몫"]),
        ("🔴 잔차", d1800["🔴 잔차 |A + S − Δ|"]),
    ])
    judge["🔴 문턱 0.00353 — Δ(천장)이 이 «자»를 넘었나"] = bool(
        mix[str(U_REG)][RULER_JUDGE][top]["🔴🔴🔴 Δ"] > THR_CARD)
    judge["🔴🔴 노트 133 — 「채택」이라 적나"] = (
        "🔴 «안» 적는다 — 채택 문턱은 「못 정했다」(968 재정정). 이 수는 «자»로만 쓴다")
    judge["🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)"] = int(ncell)

    # ── §6 🔴🔴 탐색 팔 — 사전등록 «밖». 채점 분모에 «안» 든다 ──────────
    explore = collections.OrderedDict()
    for rn in RN:
        rs = [float(arr(U_REG, ("탐색.base", nb), rn).mean()) for nb in EXPLORE_BASE]
        best = int(EXPLORE_BASE[int(np.argmax(rs))])
        base_only = float(arr(U_REG, ("대체.1800", 0.0), rn).mean())
        explore[rn] = collections.OrderedDict([
            ("🔴 base 행별 ρ(총량 %d 고정 · hplt = %d − base)"
             % (EXPLORE_N, EXPLORE_N), collections.OrderedDict(
                 (str(nb), _r(v)) for nb, v in zip(EXPLORE_BASE, rs))),
            ("🔴🔴🔴 ρ 가 «가장 높은» base 행 수", best),
            ("🔴🔴🔴 그 값", _r(max(rs))),
            ("🔴 977 이 쓴 base 행 수(α=0.95 · N=1800)",
             int(A.N_B - round(ALPHA_H * A.N_B))),
            ("🔴 그 자리의 ρ", _r(rs[EXPLORE_BASE.index(90)])),
            ("🔴 base 전량(1800)의 ρ", _r(rs[-1])),
            ("🔴🔴🔴 최적 대비 977 자리의 손실", _r(max(rs) - rs[EXPLORE_BASE.index(90)])),
            ("🔴🔴🔴 base 전량 대비 최적의 이득", _r(max(rs) - rs[-1])),
            ("🔴🔴🔴 977 자리가 «최적 오른쪽 절벽»인가",
             bool(best > 90 and rs[EXPLORE_BASE.index(90)] < rs[-1])),
        ])
    explore["🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)"] = int(nexplore_cell[0])
    explore["🔴🔴🔴 이 절은 «사전등록 밖»이다"] = (
        "🔴 **채점 분모에 «안» 든다. 예측·반증조건 어디서도 이 칸을 «안» 읽는다.** "
        "`docs/루프.md` ⓪ 방향 설계의 «탐색 팔»로만 싣는다 — (ㄴ) 대체 팔이 "
        "`α = 0.8` 과 `0.95` 사이에서 절벽을 보여서 그 자리만 봤다")
    explore["통과"] = None

    res = collections.OrderedDict([
        ("무엇", "990 §1 — 🔴🔴🔴 **굶긴 것과 더한 것을 가르고, 세 자를 나란히 잰다**"),
        ("🔴 축", "C3 (mixture) × C6 (scaling) × C2 (도메인 가중)"),
        ("사전등록", "docs/prereg_990_arms_rulers.md §1"),
        ("🔴🔴🔴 세계 자료(런타임 지문)", world_stamp()),
        ("🔴 자", collections.OrderedDict([
            ("겹", "개체 묶음 %d겹 OOF" % KFOLD),
            ("상관", "도메인별 유보 스피어만(동률 평균)"),
            ("🔴 판정 자", RULER_JUDGE), ("🔴 병기 자", list(RULER_ALT)),
            ("씨앗", SEEDS), ("게이트 도메인", doms),
            ("게이트 유보 행 합",
             int(sum(int(pool.ho_mask[d].sum()) for d in doms))),
            ("(ㄱ) 증강 눈금", H_RUNGS), ("(ㄱ) base 고정 수준", list(BASE_FIX)),
            ("(ㄴ) 대체 눈금", A_RUNGS), ("(ㄴ) 총량 고정 수준", list(N_FIX)),
            ("(ㄷ) 혼합 눈금", [37531 if n is None else n for n in N_RUNGS]),
            ("🔴 잰 칸 수", ncell),
        ])),
        ("🔴 깔때기", collections.OrderedDict([
            ("① 삼중쌍으로 산 hplt 행", int(len(pool.yh))),
            ("② base 삼중쌍 행(= 유보 전량)", int(len(pool.yb))),
            ("③ 게이트 유보 행",
             int(sum(int(pool.ho_mask[d].sum()) for d in doms))),
            ("④ 977 예산 상수가 학습에 넣은 hplt 행", int(round(ALPHA_H * A.N_B))),
            ("⑤ 🔴 그 상수가 «남긴» base 학습 행", int(A.N_B - round(ALPHA_H * A.N_B))),
            ("🔴 ④ 는 자료 한계인가", False),
            ("🔴 ⑤ 는 자료 한계인가", False),
            ("🔴 ④·⑤ 를 만든 것", "runners/alpha977.py:60 의 `N_B = 1800`"),
            ("🔴 base 의 «자기» 천장(씨앗 %d)" % SEEDS[0], int(cap976)),
            ("⚠ ① 앞의 「디스크 행」은 이 러너가 «안 셌다»",
             "🔴 989 는 `38866835` 를 «손으로» 세계 명제 절에 실었다 — 990 은 «안 싣는다»"),
        ])),
        ("§1 🔴🔴🔴 (ㄷ) 혼합 사다리 — 989 의 팔(자·λ 전량)", mix),
        ("§2 🔴🔴🔴 (ㄱ) 증강 사다리 — base 고정 · hplt 만 흔든다", aug),
        ("§3 🔴🔴🔴 (ㄴ) 대체 사다리 — 총량 고정 · α 만 흔든다", sub),
        ("§4 🔴🔴🔴 분해 — `Δ(N) = 증강 + 굶김`", decomp),
        ("§5 🔴🔴🔴 판정", judge),
        ("§6 🔴🔴 탐색 팔 — 🔴 **사전등록 «밖» · 채점 분모에 «안» 든다**", explore),
        # 🔴 잔차가 «전 눈금 · 전 자»에서 0 인가 --- 한 자리라도 None 이면 통과가 아니다
        ("🔴 분해 잔차 — 전 눈금 · 전 자", collections.OrderedDict([
            ("🔴 잰 자리 수", int(sum(len(v) for v in decomp.values()))),
            ("🔴 잔차 최대", _r(max(
                (x["🔴 잔차 |A + S − Δ|"] for v in decomp.values()
                 for x in v.values()
                 if x["🔴 잔차 |A + S − Δ|"] is not None), default=None), 12)),
            ("🔴 잔차가 None 인 자리 수", int(sum(
                1 for v in decomp.values() for x in v.values()
                if x["🔴 잔차 |A + S − Δ|"] is None))),
        ])),
        ("통과", bool(
            all(x["🔴 잔차 |A + S − Δ|"] is not None
                and x["🔴 잔차 |A + S − Δ|"] < 1e-9
                for v in decomp.values() for x in v.values()))),
        ("🔴 이 절의 통과가 뜻하는 것",
         "🔴 분해가 «전 눈금 · 전 자»에서 항등식으로 닫혔다 — "
         "「증강」과 「굶김」이 «정의상» Δ 를 다 설명한다"),
    ])
    res.update(_stamp(ref, cs0, t0))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=("wiring", "arms"))
    ap.add_argument("--ref", required=True)
    a = ap.parse_args()
    if len(a.ref) != 40:
        raise SystemExit("🔴 --ref 는 40자 sha 여야 한다")
    fn = {"wiring": stage_wiring, "arms": stage_arms}[a.stage]
    _prog("시작 %s" % a.stage)
    res = fn(a.ref)
    p = OUT / ("out990_wiring.json" if a.stage == "wiring" else "out990_arms.json")
    p.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    _prog("끝 %s → %s" % (a.stage, p.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
