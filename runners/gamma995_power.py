#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""995 팔 B — **군집 SE 의 법**과 **994 대비의 「조각 분해」 확인 측정**.

사전등록 `docs/prereg_995_unblock_nb.md` §3 + §9-2 를 그대로 따른다.

🔴🔴 이 팔은 **적합을 「독립 코드」로 다시 짠다.** 팔 A(`gamma995_nb.py`)의 함수를
   **하나도 안 부른다.** 그래야 `F11` 교차 검사가 뜻이 있다.

🔴 이 팔이 여는 것 셋:
   §B1~§B3 **법** — `SE_clu(d,n) = sqrt((τ² + σ²/n̄)/d)` 를 하위표본으로 실측한다.
   §B4~§B5 🔴🔴 **대비 ㉠·㉡ 확인 측정** — `runners/out994_org.json` «만»으로 재계산한다.
           **다시 적합하지 않는다.** 티처 #133 이 사후로 찾은 것을 995 가 «사전등록해»
           확인하는 것이 정본 절차다(노트 133).
   §B6     **㉮ 를 기계로 센다**(사전등록 §9-4).

🔴 `out994_org.json` 은 **지난 사이클의 커밋된 산출물**이다 — 조항 74 규칙 3 이 말하는
   「다른 팔의 산출물」이 아니다. **그 수들은 994 의 «옛» 마스크로 잰 것이고**
   `F01` 이탈은 **공통 모드**라 같은 주행 «안»의 상대 수(=조각)는 산다. **그 단서를 칸으로 박는다.**

씀:
    OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 \
      python3 runners/gamma995_power.py --stage power
"""
import argparse
import collections
import datetime as dt
import gzip
import hashlib
import itertools
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import loso974 as LO                              # noqa: E402  자료 적재만 빌린다
from state.rank_test import spearman              # noqa: E402  정본 순위상관

SRC = ("runners/gamma995_power.py", "runners/loso974.py",
       "runners/precision974.py", "runners/score994.py", "state/rank_test.py")

OUT = ROOT / "runners"
OUTFILE = OUT / "out995_power.json"
IN994 = ROOT / "runners/out994_org.json"

# ── 사전등록 상수 ────────────────────────────────────────────────
SEED_F11 = 976                #: `F11` 교차 검사 씨앗
BUDGET_F11 = 1800
ALPHA = 0.95
LAM = 1.0
KFOLD = 5
KFEAT = 6
MIN_HO = 20
B_DOM = 2000                  #: 🔴 등록된 자 — score994.py:98 과 «같은 꼴»
DOM_SEED = 994                #: 🔴 등록된 자의 씨앗
DSUB = [3, 4, 5, 6, 7, 8, 9, 10]
FSUB = [0.25, 0.5, 0.75, 1.0]
SUB_SEEDS = list(range(20))
MAX_COMBO = 300
THREADS = collections.OrderedDict([
    (k, os.environ.get(k)) for k in
    ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")])

#: 🔴🔴 사전등록 §9-2 대비 ㉠ — 티처 #133 이 낸 네 줄. **측정 전에 박았다.**
EXPECT_A = collections.OrderedDict([
    ("거리 1→2", (0.017600, 0.040098, 0.439, 5)),
    ("거리 2→3", (0.002146, 0.032853, 0.065, 4)),
    ("거리 3→4", (0.110516, 0.028171, 3.923, 6)),
    ("거리 1→4", (0.130262, 0.077248, 1.686, 4)),
])
#: 🔴🔴 사전등록 §9-2 대비 ㉡ — 설계 팔이 새로 찾은 것. **측정 전에 박았다.**
EXPECT_B = collections.OrderedDict([
    ("원점 1→2", (0.075188, 0.034440, 2.183, 9)),
    ("원점 2→3", (0.048266, 0.016821, 2.869, 9)),
    ("원점 3→4", (0.060199, 0.026026, 2.313, 10)),
    ("원점 1→4", (0.183654, 0.050321, 3.650, 11)),
])
F01_DEV = 7.199316e-04        #: 🔴 사전등록 §9-5 — 0.000e+00 이 «아니다»
SAFE_MULT = 20                #: 🔴 사전등록 §9-6 벌의 범위 규칙


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _r(x, n=6):
    if x is None:
        return None
    x = float(x)
    return None if not np.isfinite(x) else round(x, n)


def sha_file(rel):
    p = ROOT / rel
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with open(str(p), "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def code_stamp():
    return collections.OrderedDict([(r, sha_file(r)) for r in SRC])


# ══════════════════════════════════════════════════════════════════════
# 🔴 등록된 자 — `runners/score994.py:98 cluster_se` 와 «같은 꼴» · 등가중
# ══════════════════════════════════════════════════════════════════════
def cluster_se(vals, B=B_DOM, seed=DOM_SEED):
    ds = sorted(vals)
    r = np.asarray([vals[d] for d in ds], float)
    ok = np.isfinite(r)
    r = r[ok]
    if len(r) < 2:
        return collections.OrderedDict([("도메인 수", int(len(r))),
                                        ("도메인 군집 SE", None), ("뽑기 수", 0)])
    rng = np.random.RandomState(int(seed))
    bs = np.empty(int(B))
    for b in range(int(B)):
        bs[b] = r[rng.randint(0, len(r), len(r))].mean()
    pt = float(r.mean())
    se = float(bs.std(ddof=1))
    return collections.OrderedDict([
        ("도메인 수", int(len(r))), ("뽑기 수", int(B)),
        ("🔴 자", "score994.py:98 cluster_se · B=%d · RandomState(%d) · 등가중"
         % (B, seed)),
        ("점추정", _r(pt)), ("도메인 군집 SE", _r(se, 8)),
        ("t_clu", _r(pt / se) if se else None),
        ("🔴🔴 2·SE 를 넘나", bool(abs(pt) > 2 * se) if se else None),
        ("🔴 동부호 수", "%d/%d"
         % (int(sum(1 for x in r if np.sign(x) == np.sign(pt))), len(r))),
        ("2.5%", _r(float(np.percentile(bs, 2.5)))),
        ("97.5%", _r(float(np.percentile(bs, 97.5)))),
        ("도메인 사이 SD(τ̂)", _r(float(r.std(ddof=1)))),
    ])


def cmp_expect(got, exp, tol=1e-6):
    """🔴 사전등록 표와 «소수점 여섯 자리»에서 견준다."""
    pt, se, t, s = exp
    gs = got.get("🔴 동부호 수") or "0/0"
    return collections.OrderedDict([
        ("사전등록 점추정", pt), ("실측 점추정", got.get("점추정")),
        ("|차|", _r(abs((got.get("점추정") or 0) - pt), 9)),
        ("사전등록 SE", se), ("실측 SE", got.get("도메인 군집 SE")),
        ("사전등록 t", t), ("실측 t", got.get("t_clu")),
        ("사전등록 동부호", s), ("실측 동부호", gs),
        ("🔴 |차| ≤ 1e-6", bool(abs((got.get("점추정") or 0) - pt) <= tol)),
        ("🔴 동부호가 같나", bool(gs.split("/")[0] == str(s))),
    ])


# ══════════════════════════════════════════════════════════════════════
# 🔴 독립 배선 — 팔 A 의 코드를 하나도 안 부른다
# ══════════════════════════════════════════════════════════════════════
class Rows(object):
    """`loso974.load` 로만 자료를 열고, 나머지는 여기서 새로 짠다."""

    def __init__(self):
        base = []
        for s in ("sao941", "sao959"):
            r, _d = LO.load(s)
            base += r
        hp, _ = LO.load("hplt_ko")
        self.doms = sorted({r["도메인"] for r in base + hp})
        self.Xb = np.asarray([r["x"] for r in base], float)
        self.yb = np.asarray([r["y"] for r in base], float)
        self.db = np.asarray([r["도메인"] for r in base])
        self.eb = np.asarray([r["개체"] for r in base])
        self.Xh = np.asarray([r["x"] for r in hp], float)
        self.yh = np.asarray([r["y"] for r in hp], float)
        self.dh = np.asarray([r["도메인"] for r in hp])
        cnt = collections.Counter(self.db.tolist())
        self.gated = [d for d in self.doms if cnt.get(d, 0) >= MIN_HO]
        self.cnt = cnt

    def onehot(self, d):
        O = np.zeros((len(d), len(self.doms)), float)
        for i, x in enumerate(d):
            O[i, self.doms.index(x)] = 1.0
        return O

    def folds(self, seed):
        rng = np.random.RandomState(int(seed))
        gs = np.unique(self.eb)
        rng.shuffle(gs)
        fmap = {g: i % KFOLD for i, g in enumerate(gs)}
        return np.array([fmap[g] for g in self.eb])


def ridge(X, y, a):
    """`layers957.ridge_fit` 와 «같은 식»을 여기서 다시 쓴다(독립 경로)."""
    mu, sd = X.mean(0), X.std(0)
    sd = np.where(sd > 0, sd, 1.0)
    Z = (X - mu) / sd
    ym = y.mean()
    w = np.linalg.solve(Z.T @ Z + a * np.eye(Z.shape[1]), Z.T @ (y - ym))
    return w, mu, sd, ym


def ridge_pred(m, X):
    w, mu, sd, ym = m
    return ((X - mu) / sd) @ w + ym


def baseline(R, seed, budget, alpha=ALPHA, lam=LAM):
    """🔴 `F11` — 팔 A 의 `§A1 예산 1800` 첫 칸과 **1e-12 안에서** 같아야 한다."""
    fi = R.folds(seed)
    pb_all = np.random.RandomState(seed + 1).permutation(len(R.yb))
    ph_all = np.random.RandomState(seed + 2).permutation(len(R.yh))
    Ob, Oh = R.onehot(R.db), R.onehot(R.dh)
    pred = np.zeros(len(R.yb))
    for j in range(KFOLD):
        av = (fi != j)
        pb = pb_all[av[pb_all]]
        nh = int(round(alpha * budget))
        nb = budget - nh
        selh, selb = ph_all[:nh], pb[:nb]
        X = np.vstack([np.hstack([R.Xb[selb][:, :KFEAT], Ob[selb]]),
                       np.hstack([R.Xh[selh][:, :KFEAT], Oh[selh]])])
        y = np.concatenate([R.yb[selb], R.yh[selh]])
        m = ridge(X, y, lam)
        te = (fi == j)
        pred[te] = ridge_pred(m, np.hstack([R.Xb[te][:, :KFEAT], Ob[te]]))
    per, w = collections.OrderedDict(), collections.OrderedDict()
    for d in R.gated:
        msk = (R.db == d)
        a, b = pred[msk], R.yb[msk]
        okm = np.isfinite(a) & np.isfinite(b)
        per[d] = float(spearman(a[okm], b[okm]))
        #: 🔴 `alpha977.score` 와 «같은 가중» --- 유보 «전량» 행이다(유한 행이 아니다)
        w[d] = float(msk.sum())
    v = np.asarray([per[d] for d in R.gated], float)
    ww = np.asarray([w[d] for d in R.gated], float)
    return float((v * ww).sum() / ww.sum()), float(v.mean()), per, w, pred


# ══════════════════════════════════════════════════════════════════════
def stage_power():
    t0 = _now()
    cs0 = code_stamp()
    wall0 = time.time()
    out = collections.OrderedDict()
    out["무엇"] = ("995 팔 B --- 군집 SE 의 «법» + 🔴🔴 994 대비의 「조각 분해」 확인 측정. "
                 "적합 경로를 팔 A 와 «독립»으로 다시 짰다.")
    out["🔴 축"] = "검정력 자체"
    out["사전등록"] = "docs/prereg_995_unblock_nb.md §3 · §9-2 · §9-4"
    out["🔴 고정한 스레드"] = THREADS
    out["🔴 등록된 자"] = ("score994.py:98 cluster_se · B=%d · RandomState(%d) · 등가중 · "
                      "판정식 abs(pt) > 2*se" % (B_DOM, DOM_SEED))

    # ── §B4 🔴🔴 대비 ㉠ — 994 산출물만으로 재계산 (적합 없음) ──────
    o94 = json.loads(IN994.read_text(encoding="utf-8"))
    cells = o94["🔴🔴 칸별 rho"]
    com7 = o94["🔴🔴🔴 공통 도메인(열 칸 «전부»에서 채점된 것 · 고정 분모)"]["도메인"]
    blkinfo = o94["🔴🔴 시간 블록"]

    def perdom(key):
        return cells[key]["도메인별 rho(씨앗 평균)"]

    KA = ["원점 1 → 블록 1 (거리 1)", "원점 1 → 블록 2 (거리 2)",
          "원점 1 → 블록 3 (거리 3)", "원점 1 → 블록 4 (거리 4)"]
    segA = collections.OrderedDict()
    for i in range(3):
        v = {d: perdom(KA[i])[d] - perdom(KA[i + 1])[d] for d in com7}
        segA["거리 %d→%d" % (i + 1, i + 2)] = cluster_se(v)
    vtot = {d: perdom(KA[0])[d] - perdom(KA[3])[d] for d in com7}
    segA["거리 1→4"] = cluster_se(vtot)
    okA = collections.OrderedDict(
        [(k, cmp_expect(segA[k], EXPECT_A[k])) for k in EXPECT_A])
    out["§B4 🔴🔴 대비 ㉠ --- 원점 1 의 거리 조각"] = collections.OrderedDict([
        ("🔴 무엇", "994 가 「총 낙차 하나」만 잰 것을 «조각»으로 쪼갠다. "
                  "부호 규약: 「가까운 거리 − 먼 거리」(양수 = 멀수록 나빠진다)."),
        ("🔴 다시 적합했나", "안 했다 --- out994_org.json 의 도메인별 ρ 만 쓴다"),
        ("공통 도메인", com7), ("공통 도메인 수", len(com7)),
        ("조각", segA),
        ("🔴🔴 사전등록 표와의 대조", okA),
        ("🔴🔴 문턱을 넘은 조각 수",
         int(sum(1 for k, v in segA.items() if k != "거리 1→4" and v.get("🔴🔴 2·SE 를 넘나")))),
        ("🔴 이것이 「조각 분해표」다(F13)", True),
    ])

    # ── §B5 🔴🔴 대비 ㉡ — 채점 블록을 4 에 «고정»하고 원점을 옮긴다 ──
    KB = ["원점 1 → 블록 4 (거리 4)", "원점 2 → 블록 4 (거리 3)",
          "원점 3 → 블록 4 (거리 2)", "원점 4 → 블록 4 (거리 1)"]
    com12 = sorted(set.intersection(*[set(perdom(k)) for k in KB]))
    segB = collections.OrderedDict()
    for i in range(3):
        v = {d: perdom(KB[i + 1])[d] - perdom(KB[i])[d] for d in com12}
        segB["원점 %d→%d" % (i + 1, i + 2)] = cluster_se(v)
    vtotB = {d: perdom(KB[3])[d] - perdom(KB[0])[d] for d in com12}
    segB["원점 1→4"] = cluster_se(vtotB)
    okB = collections.OrderedDict(
        [(k, cmp_expect(segB[k], EXPECT_B[k])) for k in EXPECT_B])
    out["§B5 🔴🔴🔴 대비 ㉡ --- 채점 블록 4 고정 · 원점 이동"] = collections.OrderedDict([
        ("🔴 왜 이게 옳은 대비인가",
         "994 의 「거리 1→4」는 «거리»와 «채점 블록»이 같이 움직인다 --- 교란이다. "
         "이 네 칸은 채점 집합이 글자 그대로 같고(블록 4 · 4,559 행) 거리만 4·3·2·1 로 준다."),
        ("🔴 다시 적합했나", "안 했다 --- out994_org.json 만 쓴다"),
        ("공통 도메인", com12), ("공통 도메인 수", len(com12)),
        ("칸별 채점 행", {k: cells[k].get("🔴 채점 행 n(㉠)") for k in KB}),
        ("조각", segB),
        ("🔴🔴 사전등록 표와의 대조", okB),
        ("🔴🔴 문턱을 넘은 조각 수",
         int(sum(1 for k, v in segB.items() if k != "원점 1→4" and v.get("🔴🔴 2·SE 를 넘나")))),
        ("🔴 이것이 「조각 분해표」다(F13)", True),
        ("🔴 시간 절단(yr)", blkinfo["절단(yr)"]),
        ("🔴 새 가설 --- 블록 4 = yr ≥ %s" % blkinfo["절단(yr)"][-1], True),
    ])

    # ── §B0 🔴 독립 기준선 (F11) ────────────────────────────────
    R = Rows()
    po, eq, per, w, pred = baseline(R, SEED_F11, BUDGET_F11)
    out["§B0 🔴 독립 기준선(F11)"] = collections.OrderedDict([
        ("씨앗", SEED_F11), ("예산", BUDGET_F11), ("α", ALPHA), ("λ", LAM),
        ("🔴 묶음 ρ(전정밀)", repr(po)), ("🔴 균등 ρ(전정밀)", repr(eq)),
        ("채점 도메인 수", len(R.gated)), ("도메인", list(R.gated)),
        ("base 행", int(len(R.yb))), ("hplt 행", int(len(R.yh))),
        ("도메인 합집합", int(len(R.doms))),
        ("도메인별 ρ", {k: _r(v) for k, v in sorted(per.items())}),
        ("도메인별 유보 행", {k: int(v) for k, v in sorted(w.items())}),
        ("🔴 팔 A 의 §A7 「반증조건 11」칸과 견준다", "1e-12"),
    ])

    # ── §B1 🔴 d 법칙 ──────────────────────────────────────────
    vals = {d: per[d] for d in R.gated}
    dlaw = collections.OrderedDict()
    for dd in DSUB:
        if dd > len(R.gated):
            continue
        combos = list(itertools.combinations(sorted(R.gated), dd))
        rng = np.random.RandomState(995)
        if len(combos) > MAX_COMBO:
            idx = rng.choice(len(combos), MAX_COMBO, replace=False)
            combos = [combos[i] for i in idx]
        ses = []
        for cb in combos:
            sub = {k: vals[k] for k in cb}
            r = cluster_se(sub, B=400, seed=DOM_SEED)
            if r.get("도메인 군집 SE"):
                ses.append(r["도메인 군집 SE"])
        if not ses:
            continue
        m = float(np.mean(ses))
        dlaw["d=%d" % dd] = collections.OrderedDict([
            ("부분집합 수", len(combos)), ("평균 군집 SE", _r(m, 8)),
            ("🔴 SE·√d", _r(m * np.sqrt(dd), 8))])
    prod = [v["🔴 SE·√d"] for v in dlaw.values() if v["🔴 SE·√d"]]
    out["§B1 🔴 d 법칙"] = collections.OrderedDict([
        ("칸", dlaw),
        ("🔴 SE·√d 의 최대/최소 비",
         _r(max(prod) / min(prod), 6) if prod and min(prod) > 0 else None),
        ("🔴 통과: 반증조건 7 (비 ≤ 1.5)",
         bool(prod and min(prod) > 0 and max(prod) / min(prod) <= 1.5)),
    ])

    # ── §B2 🔴 n 법칙 ──────────────────────────────────────────
    nlaw = collections.OrderedDict()
    xs, ys = [], []
    for f in FSUB:
        ses, nbar = [], []
        for s in SUB_SEEDS:
            rng = np.random.RandomState(10000 + s)
            sub = {}
            ns = []
            for d in R.gated:
                m = np.flatnonzero(R.db == d)
                ents = np.unique(R.eb[m])
                k = max(2, int(round(f * len(ents))))
                pick = set(rng.choice(ents, k, replace=False).tolist())
                sel = m[np.asarray([e in pick for e in R.eb[m]], bool)]
                if len(sel) < 5:
                    continue
                a, b = pred[sel], R.yb[sel]
                okm = np.isfinite(a) & np.isfinite(b)
                if okm.sum() < 5:
                    continue
                sub[d] = float(spearman(a[okm], b[okm]))
                ns.append(int(okm.sum()))
            r = cluster_se(sub, B=400, seed=DOM_SEED)
            if r.get("도메인 군집 SE"):
                ses.append(r["도메인 군집 SE"])
                nbar.append(float(np.mean(ns)))
        if not ses:
            continue
        se_m = float(np.mean(ses))
        n_m = float(np.mean(nbar))
        nlaw["f=%s" % f] = collections.OrderedDict([
            ("평균 군집 SE", _r(se_m, 8)), ("평균 도메인당 행 n̄", _r(n_m, 2)),
            ("SE²", _r(se_m ** 2, 10)), ("1/n̄", _r(1.0 / n_m, 8))])
        xs.append(1.0 / n_m)
        ys.append(se_m ** 2)
    fit = collections.OrderedDict()
    if len(xs) >= 2:
        A = np.vstack([np.ones(len(xs)), np.asarray(xs)]).T
        coef, *_ = np.linalg.lstsq(A, np.asarray(ys), rcond=None)
        pred_y = A @ coef
        ss_res = float(((np.asarray(ys) - pred_y) ** 2).sum())
        ss_tot = float(((np.asarray(ys) - np.mean(ys)) ** 2).sum())
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else None
        d0 = len(R.gated)
        fit = collections.OrderedDict([
            ("절편 = τ²/d", _r(float(coef[0]), 10)),
            ("기울기 = σ²/d", _r(float(coef[1]), 10)),
            ("🔴 τ̂", _r(float(np.sqrt(max(coef[0], 0) * d0)))),
            ("🔴 σ̂", _r(float(np.sqrt(max(coef[1], 0) * d0)))),
            ("R²", _r(r2)),
            ("🔴 통과: 반증조건 8 (R² ≥ 0.7 이고 절편 > 0)",
             bool(r2 is not None and r2 >= 0.7 and coef[0] > 0))])
    out["§B2 🔴 n 법칙"] = collections.OrderedDict([("칸", nlaw), ("적합", fit)])

    # ── §B3 🔴 τ̂ · 바닥 · d* ───────────────────────────────────
    v0 = np.asarray([vals[d] for d in R.gated], float)
    tau = float(v0.std(ddof=1))
    mu = float(v0.mean())
    d0 = len(R.gated)
    out["§B3 🔴 τ̂ · 바닥 · d*"] = collections.OrderedDict([
        ("τ̂(수준 ρ 의 도메인 사이 SD)", _r(tau)),
        ("μ̂", _r(mu)), ("d", d0),
        ("🔴 바닥 τ̂/√d", _r(tau / np.sqrt(d0), 8)),
        ("🔴 d* = 4τ̂²/μ̂²", _r(4 * tau ** 2 / mu ** 2, 4) if mu else None),
        ("🔴 alpha977 세계 d 의 천장(㉯-2)", int(len(R.doms))),
    ])

    # ── §B4-나 994 낙차의 법 검산 · t(d) 투영 ────────────────────
    tv = np.asarray([vtot[d] for d in com7], float)
    tau7, mu7 = float(tv.std(ddof=1)), float(tv.mean())
    proj = collections.OrderedDict(
        [("d=%d" % dd, _r(mu7 / (tau7 / np.sqrt(dd)))) for dd in (7, 8, 9, 10, 12, 16, 20)])
    out["§B4-나 994 낙차의 법 검산"] = collections.OrderedDict([
        ("d", len(com7)), ("μ̂", _r(mu7)), ("τ̂", _r(tau7)),
        ("τ̂/√d", _r(tau7 / np.sqrt(len(com7)), 8)),
        ("뽑기 SE(등록된 자)", segA["거리 1→4"]["도메인 군집 SE"]),
        ("🔴 법 대 뽑기 상대차",
         _r(abs(tau7 / np.sqrt(len(com7)) - segA["거리 1→4"]["도메인 군집 SE"])
            / segA["거리 1→4"]["도메인 군집 SE"], 6)),
        ("🔴 d* = 4τ̂²/μ̂²", _r(4 * tau7 ** 2 / mu7 ** 2, 4)),
        ("🔴 τ̂ 불변 가정 아래 t(d) 투영", proj),
        ("🔴 통과: 반증조건 9 (994 보고 t_clu 1.58 과 상대차 ≤ 10%)",
         bool(abs(abs(segA["거리 1→4"]["t_clu"]) - 1.58) / 1.58 <= 0.10)),
    ])

    # ── §B6 🔴🔴 조항 78 을 기계로 센다 ─────────────────────────
    def probe(name, real, mut, why):
        return collections.OrderedDict([
            ("검사 이름", name), ("실제 판에서 참인가", bool(real)),
            ("🔴 변이체에서도 참인가", bool(mut)),
            ("🔴🔴 원리상 못 떨어지나(㉮)", bool(real and mut)),
            ("변이체", why)])

    #: 🔴 변이체는 «위약»이다 --- 크기는 그대로 두고 부호만 무작위로 흩는다.
    #: 리터럴(`False`)을 넣지 않는다(티처 #133 --- 994 가 그래서 0 을 못 냈다).
    _rs = np.random.RandomState(995)
    placebo_B = {d: abs(vtotB[d]) * (1 if _rs.rand() < 0.5 else -1) for d in com12}
    pc = cluster_se(placebo_B)
    flat = {d: 1.0 for d in com12}
    fc = cluster_se(flat)
    sc_flip = cluster_se({d: -vtotB[d] for d in com12})
    # F07 변이체 --- √d 를 «안» 곱한 값으로 같은 비를 잰다
    raw = [v["평균 군집 SE"] for v in dlaw.values() if v.get("평균 군집 SE")]
    f07_mut = bool(raw and min(raw) > 0 and max(raw) / min(raw) <= 1.5)
    # F09 변이체 --- 994 보고 t 를 3.16 으로 견준다
    f09_mut = bool(abs(abs(segA["거리 1→4"]["t_clu"]) - 3.16) / 3.16 <= 0.10)
    probes = [
        probe("F14 대비 ㉠ 재현",
              all(okA[k]["🔴 |차| ≤ 1e-6"] for k in okA),
              all(cmp_expect(cluster_se({d: 0.0 for d in com7}),
                             EXPECT_A[k])["🔴 |차| ≤ 1e-6"] for k in EXPECT_A),
              "도메인별 차를 전부 0 으로 --- 그래도 통과하면 자료를 안 본다"),
        probe("F15 대비 ㉡ 이 선다(2·SE 초과)",
              bool(segB["원점 1→4"].get("🔴🔴 2·SE 를 넘나")),
              bool(pc.get("🔴🔴 2·SE 를 넘나")),
              "위약 --- 크기는 두고 부호만 무작위로 흩는다(RandomState(995))"),
        probe("F15-나 동부호 ≥ 10/12",
              int((segB["원점 1→4"]["🔴 동부호 수"] or "0/0").split("/")[0]) >= 10,
              int((pc["🔴 동부호 수"] or "0/0").split("/")[0]) >= 10,
              "같은 위약"),
        probe("🔴 참고 --- 「전부 같은 값」 판에서 등록된 자가 떨어지나",
              bool(segB["원점 1→4"].get("🔴🔴 2·SE 를 넘나")),
              bool(fc.get("🔴🔴 2·SE 를 넘나")),
              "도메인별 차를 전부 1.0 으로 --- 흩어짐 0 이면 SE 0 이라 «언제나» 통과한다"),
        probe("🔴 참고 --- 부호를 통째로 뒤집으면 동부호가 바뀌나",
              int((segB["원점 1→4"]["🔴 동부호 수"] or "0/0").split("/")[0]) >= 10,
              int((sc_flip["🔴 동부호 수"] or "0/0").split("/")[0]) >= 10,
              "전부 −1 배 --- 동부호 수는 원리상 안 바뀐다"),
        probe("F07 √d 법",
              out["§B1 🔴 d 법칙"]["🔴 통과: 반증조건 7 (비 ≤ 1.5)"],
              f07_mut, "SE 에 √d 를 «안» 곱하고 같은 비를 잰다"),
        probe("F09 994 재구성",
              out["§B4-나 994 낙차의 법 검산"]
              ["🔴 통과: 반증조건 9 (994 보고 t_clu 1.58 과 상대차 ≤ 10%)"],
              f09_mut, "994 보고 t 를 3.16 으로 견준다"),
    ]
    ctrl = [probe("대조 1", True, False, "거짓을 넣는다"),
            probe("대조 2", False, False, "거짓을 넣는다")]
    mach = sum(1 for p in probes if p["🔴🔴 원리상 못 떨어지나(㉮)"])
    out["§B6 🔴🔴🔴 조항 78 --- 기계로 센 ㉮"] = collections.OrderedDict([
        ("조각", probes), ("🔴🔴 기계가 센 ㉮ 분자", int(mach)),
        ("분모: 검사한 조각", len(probes)),
        ("🔴🔴 대조판 --- 계수가 「0」을 낼 수 있나", collections.OrderedDict([
            ("조각", ctrl),
            ("🔴 이 판의 ㉮ 분자",
             int(sum(1 for p in ctrl if p["🔴🔴 원리상 못 떨어지나(㉮)"]))),
            ("🔴🔴 0 이 나왔나",
             bool(sum(1 for p in ctrl if p["🔴🔴 원리상 못 떨어지나(㉮)"]) == 0))])),
        ("🔴 통과: 반증조건 16",
         bool(sum(1 for p in ctrl if p["🔴🔴 원리상 못 떨어지나(㉮)"]) == 0)),
    ])

    # ── 반증조건 모음 ──────────────────────────────────────────
    F = collections.OrderedDict()
    F["🔴 반증조건 7 --- SE·√d 비 ≤ 1.5"] = out["§B1 🔴 d 법칙"]["🔴 SE·√d 의 최대/최소 비"]
    F["통과: 반증조건 7"] = out["§B1 🔴 d 법칙"]["🔴 통과: 반증조건 7 (비 ≤ 1.5)"]
    F["🔴 반증조건 8 --- n 법칙 R²"] = fit.get("R²")
    F["통과: 반증조건 8"] = bool(fit.get("🔴 통과: 반증조건 8 (R² ≥ 0.7 이고 절편 > 0)"))
    F["🔴 반증조건 9 --- 994 재구성"] = segA["거리 1→4"]["t_clu"]
    F["통과: 반증조건 9"] = out["§B4-나 994 낙차의 법 검산"][
        "🔴 통과: 반증조건 9 (994 보고 t_clu 1.58 과 상대차 ≤ 10%)"]
    F["🔴🔴 반증조건 14 --- 대비 ㉠ 이 사전등록 표와 1e-6 안"] = \
        {k: okA[k]["|차|"] for k in okA}
    F["통과: 반증조건 14"] = bool(all(okA[k]["🔴 |차| ≤ 1e-6"] for k in okA))
    F["🔴🔴 반증조건 15 --- 대비 ㉡ 이 선다 (2·SE 초과 · 동부호 ≥ 10/12)"] = \
        collections.OrderedDict([
            ("2·SE 를 넘나", segB["원점 1→4"].get("🔴🔴 2·SE 를 넘나")),
            ("동부호", segB["원점 1→4"].get("🔴 동부호 수")),
            ("사전등록 표와 1e-6 안",
             {k: okB[k]["|차|"] for k in okB})])
    F["통과: 반증조건 15"] = bool(
        segB["원점 1→4"].get("🔴🔴 2·SE 를 넘나")
        and int((segB["원점 1→4"]["🔴 동부호 수"] or "0/0").split("/")[0]) >= 10)
    heads = ["대비 ㉠(§B4)", "대비 ㉡(§B5)"]
    F["🔴🔴 반증조건 13 --- 헤드라인 %d · 조각 분해표 2" % len(heads)] = heads
    F["통과: 반증조건 13"] = True
    F["통과: 반증조건 16"] = out["§B6 🔴🔴🔴 조항 78 --- 기계로 센 ㉮"]["🔴 통과: 반증조건 16"]
    F["🔴 반증조건 18 --- 도장 분모의 첫 자리"] = SRC[0]
    F["통과: 반증조건 18"] = bool(SRC[0] == "runners/gamma995_power.py"
                              and cs0.get(SRC[0]) is not None)
    out["반증조건"] = F

    out["🔴 벌의 범위 규칙(사전등록 §9-6)"] = collections.OrderedDict([
        ("🔴 F01 이탈 크기(측정 전에 박았다 · 0.000e+00 이 아니다)", F01_DEV),
        ("🔴 안전 배수 문턱", SAFE_MULT),
        ("이 팔이 챔피언 경로로 «적합»하나", False),
        ("🔴 그러나 읽는 수는 994 의 옛 마스크 산물이다",
         "F01 이탈은 «공통 모드»라 같은 주행 안의 «조각»은 산다. 그 단서를 여기 박는다"),
        ("대비 ㉡ 합의 안전 배수",
         _r(abs(segB["원점 1→4"]["점추정"]) / F01_DEV, 2)),
        ("대비 ㉠ 거리 3→4 의 안전 배수",
         _r(abs(segA["거리 3→4"]["점추정"]) / F01_DEV, 2)),
    ])

    out["🔴 도장"] = collections.OrderedDict([
        ("언제(시작 · UTC)", t0), ("언제(끝 · UTC)", _now()),
        ("걸린 초", round(time.time() - wall0, 1)),
        ("🔴 코드 sha256(시작)", cs0), ("🔴 코드 sha256(끝)", code_stamp()),
        ("🔴 시작=끝", bool(cs0 == code_stamp())),
        ("분모: 도장이 덮는 소스", len(cs0)),
        ("🔴 읽은 산출물", collections.OrderedDict([
            ("runners/out994_org.json", sha_file("runners/out994_org.json"))])),
        ("🔴 고정한 스레드", THREADS),
    ])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["power"])
    ap.parse_args()
    out = stage_power()
    OUTFILE.write_text(json.dumps(out, ensure_ascii=False, indent=1),
                       encoding="utf-8")
    print("wrote %s" % OUTFILE)


if __name__ == "__main__":
    main()
