#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""977 — **HPLT 를 넣는 게 나은가** (축 C3).

사전등록 `docs/prereg_977_alpha.md` 를 그대로 따른다.

🔴 티처 #115 가 976 산출물에서 두 가지를 실측으로 냈다.
  ① `hplt y` 전량(밑판 1,800 중 1,710 = 95%)을 부숴도 Δ = −0.023616 = 0.52 SE_이중.
  ② `α=0`(HPLT 를 학습에서 완전히 뺀다)이 976 격자 32 수준 중 **최대 개선**이다.

🔴 **그런데 976 의 R5 격자에서 λ 가 α 와 같이 움직였다.** 그래서 977 은
  §S1 **α × λ 격자**(λ 를 얼린다 · 겹 씨앗 다섯 평균 · 두 자 병기)
  §S2 **라벨 파괴 대조 D1~D4**(1,710 행 대 90 행 — 결정적 대조)
  §S3 **leave-one-source-out Δ**(C3 의 등록된 자)
  §S4 **두 자에서 부호가 뒤집히는 수준 전수**
  §S5 **사다리를 λ 와 겹에서 뗀다**(ρ∞ ≤ 1 제약 · 적합 SE)

🔴 **수리 1** — 이 러너는 모든 판정을 `통과` 키로 낸다. 976 의 측정 러너는
   `통과` 키가 0 개라 `meta965` 가 12 조합 전부에서 분모 0 이었다.
🔴 **수리 2** — 배선 W 마다 **변이체 대조**를 붙인다. 일부러 깨뜨린 판에서
   그 검사가 안 떨어지면 **구성상 참인 검사**이고 그것을 분자/분모로 적는다.

씀:
    python3 runners/alpha977.py --stage wiring  --ref <40자 sha>
    python3 runners/alpha977.py --stage grid    --ref <40자 sha>
    python3 runners/alpha977.py --stage destroy --ref <40자 sha>
    python3 runners/alpha977.py --stage ladder  --ref <40자 sha>
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

import runners.predict971 as P                    # noqa: E402
import runners.layers957 as L                     # noqa: E402
import loso974 as LO                              # noqa: E402
import ledger as LG                               # noqa: E402

RAN = ("runners/alpha977.py", "runners/ledger.py", "runners/layers957.py",
       "runners/predict971.py", "runners/loso974.py")
OUT = ROOT / "runners"
PROG = OUT / "out977_progress.txt"

# ── 사전등록 상수 (측정 전에 박았다) ────────────────────────────────────
SEEDS = [976, 977, 978, 979, 980]      # §2 겹 씨앗 다섯
KFOLD = 5
N_B = 1800                             # 예산
MIN_HO = 20
AGRID = [0.0, 0.2, 0.4, 0.6, 0.8, 0.95, 1.0]          # §S1 α
UGRID = [-2, -1, 0, 1, 2, 3, 4, 5, 6]                  # §S1 log10 λ
U_REG = [0, 3]                         # §S1 SE 를 내는 등록된 λ (10^0 · 10^3)
ALPHA_BASE = 0.95                      # 976 밑판 B
BOOT = 200                             # §S1 이중 붓스트랩 뽑기
BOOT_D = 200                           # §S2
N_WRECK = 5                            # §S2 섞기 씨앗 수
THR_CARD = 0.00353                     # 카드 문턱(진단값 · 976 과 같다)
LADDER = [200, 400, 800, 1600, 3200, 6400, 12800, 25600, None]
#: 🔴 α=0 팔은 base 행 수가 천장이라 사다리가 짧다 — **그것을 적는다**.
LADDER_A0 = [200, 400, 800, 1600, None]
C6_FIT_MAX = 1600
SRC_ARMS = collections.OrderedDict([
    ("ALL", ()),
    ("−hplt_ko", ("hplt_ko",)),
    ("−sao959", ("sao959",)),
    ("−sao941", ("sao941",)),
])


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _prog(msg):
    with open(str(PROG), "a", encoding="utf-8") as f:
        f.write("%s  %s\n" % (_now(), msg))


def _r(x, n=6):
    return None if x is None or not np.isfinite(x) else round(float(x), n)


# ══════════════════════════════════════════════════════════════════════
class Pool(object):
    """base(sao941+sao959) 는 **개체 묶음 5겹 OOF 유보** · HPLT 는 **언제나 학습**.

    🔴 976 의 `Pool` 과 다른 점은 하나다 — **겹 씨앗을 갈아 끼울 수 있다**(`reseed`).
    자료는 한 번만 읽는다.
    """

    def __init__(self):
        base = []
        for s in ("sao941", "sao959"):
            r, _d = LO.load(s)
            base += r
        hplt, _ = LO.load("hplt_ko")
        self.base, self.hplt = base, hplt
        self.doms = sorted({r["도메인"] for r in base + hplt})
        self.Xb, self.yb, self.db, self.tb, self.eb, self.pb, self.sb = self._arr(base)
        self.Xh, self.yh, self.dh, self.th, self.eh, self.ph, self.sh = self._arr(hplt)
        self.yh0 = self.yh.copy()
        self.Ob = self._onehot(self.db)
        self.Oh = self._onehot(self.dh)
        ents = sorted(set(self.eb.tolist()) | set(self.eh.tolist()))
        emap = {e: i for i, e in enumerate(ents)}
        self.ecb = np.asarray([emap[e] for e in self.eb], dtype=np.int64)
        self.ech = np.asarray([emap[e] for e in self.eh], dtype=np.int64)
        dmap = {d: i for i, d in enumerate(self.doms)}
        self.dcb = np.asarray([dmap[d] for d in self.db], dtype=np.int64)
        self.dch = np.asarray([dmap[d] for d in self.dh], dtype=np.int64)
        cnt = collections.Counter(self.db.tolist())
        self.gated = [d for d in self.doms if cnt.get(d, 0) >= MIN_HO]
        self.dom_ho = {d: int(cnt.get(d, 0)) for d in self.doms}
        self.ho_mask = {d: (self.db == d) for d in self.gated}
        self.seed = None
        self.reseed(SEEDS[0])

    def reseed(self, seed):
        """🔴 §2 — 겹 배정과 뽑기 차례를 **씨앗 하나로** 다시 만든다."""
        self.seed = int(seed)
        rng = np.random.RandomState(self.seed)
        gs = np.unique(self.eb)
        rng.shuffle(gs)
        fmap = {g: i % KFOLD for i, g in enumerate(gs)}
        self.fi = np.array([fmap[g] for g in self.eb])
        self.perm_b = np.random.RandomState(self.seed + 1).permutation(len(self.yb))
        self.perm_h = np.random.RandomState(self.seed + 2).permutation(len(self.yh))
        return self

    @staticmethod
    def _arr(rows):
        X = np.asarray([r["x"] for r in rows], float)
        y = np.asarray([r["y"] for r in rows], float)
        d = np.asarray([r["도메인"] for r in rows])
        t = np.asarray([dt.date.fromisoformat(r["언제"]).toordinal() for r in rows])
        e = np.asarray([r["개체"] for r in rows])
        p = np.asarray([r["쌍id"] for r in rows])
        s = np.asarray([r["원천"] for r in rows])
        return X, y, d, t, e, p, s

    def _onehot(self, d):
        O = np.zeros((len(d), len(self.doms)), float)
        for i, dd in enumerate(d):
            O[i, self.doms.index(dd)] = 1.0
        return O


# ══════════════════════════════════════════════════════════════════════
def select(pool, fold, alpha, drop_src=(), fill=True):
    """예산 `N_B` 를 α 로 갈라 (base 자리, hplt 자리)를 만든다.

    `drop_src` 가 있으면 그 원천의 행을 **뽑기 풀에서 통째로 빼고** 남은 원천으로
    예산을 채운다(§S3 leave-one-source-out — 행 수를 맞추려고).
    🔴 `fill=False` 면 **안 채운다** — 모자라면 모자란 채로 두고 그 수를 낸다.
    """
    avail_b = (pool.fi != fold)
    avail_h = np.ones(len(pool.yh), dtype=bool)
    for s in drop_src:
        if s == "hplt_ko":
            avail_h = np.zeros(len(pool.yh), dtype=bool)
        else:
            avail_b = avail_b & (pool.sb != s)
    nh = int(round(alpha * N_B))
    nb = N_B - nh
    selh = pool.perm_h[avail_h[pool.perm_h]][:nh]
    selb = pool.perm_b[avail_b[pool.perm_b]][:nb]
    if fill and (len(selh) < nh or len(selb) < nb):
        if len(selh) < nh:
            more = pool.perm_b[avail_b[pool.perm_b]]
            selb = more[:min(len(more), N_B - len(selh))]
        else:
            more = pool.perm_h[avail_h[pool.perm_h]]
            selh = more[:min(len(more), N_B - len(selb))]
    return selb, selh, int(N_B - len(selb) - len(selh))


def select_full(pool, fold, base_only=False):
    """예산 없음(전량). `base_only` 면 **HPLT 를 0 행**으로 둔다(α=0 팔의 천장)."""
    avail_b = (pool.fi != fold)
    selb = pool.perm_b[avail_b[pool.perm_b]]
    selh = (np.zeros(0, dtype=int) if base_only else
            pool.perm_h[np.ones(len(pool.yh), dtype=bool)[pool.perm_h]])
    return selb, selh, 0


def design(pool, selb, selh, k=6):
    X = np.vstack([np.hstack([pool.Xb[selb][:, :k], pool.Ob[selb]]),
                   np.hstack([pool.Xh[selh][:, :k], pool.Oh[selh]])])
    y = np.concatenate([pool.yb[selb], pool.yh[selh]])
    ent = np.concatenate([pool.ecb[selb], pool.ech[selh]])
    return X, y, ent, len(selb)


def groups_of(codes):
    order = np.argsort(codes, kind="stable")
    s = codes[order]
    starts = np.flatnonzero(np.concatenate(([True], s[1:] != s[:-1])))
    ends = np.concatenate((starts[1:], [len(s)]))
    return order, starts, ends


def wreck_y(y, nb_rows, kind, seed, n=None):
    """🔴 §S2 — **학습 라벨만** 부순다. 유보는 인자에 없다(원리상 못 만진다).

    `y` 앞 `nb_rows` 개가 base, 나머지가 hplt 다(`design` 이 그 차례로 쌓는다).
    """
    y = y.copy()
    rng = np.random.RandomState(seed)
    segs = {"base": (0, nb_rows), "hplt": (nb_rows, len(y)),
            "both": (0, len(y))}
    a, b = segs[kind]
    idx = np.arange(a, b)
    if n is not None and n < len(idx):
        idx = rng.choice(idx, size=n, replace=False)
    if len(idx) > 1:
        y[idx] = y[rng.permutation(idx)]
    return y, int(len(idx))


def oof(pool, alpha, lam, k=6, drop_src=(), full=False, fill=True,
        wreck=None, tr_boot=None):
    """다섯 겹의 OOF 예측. 🔴 **λ 는 인자로 받는다 — 이 러너는 속겹 CV 를 안 돈다.**"""
    pred = np.zeros(len(pool.yb))
    ntr, wrecked = [], 0
    for j in range(KFOLD):
        if full:
            selb, selh, _s = select_full(pool, j, base_only=(alpha == 0.0))
        else:
            selb, selh, _s = select(pool, j, alpha, drop_src, fill=fill)
        X, y, ent, nb = design(pool, selb, selh, k)
        if wreck is not None:
            y, wrecked = wreck_y(y, nb, wreck["kind"], wreck["seed"] + j,
                                 wreck.get("n"))
        if tr_boot is not None:
            rng = np.random.RandomState(tr_boot * 1000 + j + 977 * 100000)
            order, st, en = groups_of(ent)
            pick = rng.randint(0, len(st), len(st))
            idx = np.concatenate([order[st[g]:en[g]] for g in pick])
            X, y = X[idx], y[idx]
        m = L.ridge_fit(X, y, lam)
        te = pool.fi == j
        pred[te] = L.ridge_pred(m, np.hstack([pool.Xb[te][:, :k], pool.Ob[te]]))
        ntr.append(int(len(y)))
    return {"예측": pred, "겹별 학습 행": ntr, "부순 라벨 행(겹당)": wrecked}


def score(pool, pred, ho_idx=None):
    """도메인별 스피어만 → **묶음(유보 행 가중)** 과 **도메인 균등** 둘 다."""
    per, wts = collections.OrderedDict(), []
    for d in pool.gated:
        if ho_idx is None:
            m = pool.ho_mask[d]
            a, b = pred[m], pool.yb[m]
        else:
            idx = ho_idx[d]
            a, b = pred[idx], pool.yb[idx]
        per[d] = float(P.spear(a, b))
        wts.append(float(len(a)))
    vals = np.asarray([per[d] for d in pool.gated], float)
    w = np.asarray(wts, float)
    ok = np.isfinite(vals)
    pooled = float((vals[ok] * w[ok]).sum() / w[ok].sum()) if ok.any() else float("nan")
    eq = float(np.mean(vals[ok])) if ok.any() else float("nan")
    return pooled, eq, per


def ho_draw(pool, b):
    rng = np.random.RandomState(977 * 1000 + b + pool.seed)
    out = {}
    for d in pool.gated:
        m = np.flatnonzero(pool.ho_mask[d])
        order, st, en = groups_of(pool.ecb[m])
        pick = rng.randint(0, len(st), len(st))
        out[d] = m[np.concatenate([order[st[g]:en[g]] for g in pick])]
    return out


def src_fingerprint(pool, alpha, drop_src=()):
    """🔴 반증조건 8 — **만들어진 학습 자료**의 원천·도메인 구성."""
    srcs, doms, rows = [], [], 0
    for j in range(KFOLD):
        selb, selh, _s = select(pool, j, alpha, drop_src)
        srcs += list(pool.sb[selb]) + list(pool.sh[selh])
        doms += list(pool.db[selb]) + list(pool.dh[selh])
        rows += len(selb) + len(selh)
    c = collections.Counter(srcs)
    return collections.OrderedDict([
        ("행", rows),
        ("원천별", dict(sorted(c.items()))),
        ("원천 비율", {kk: round(v / float(rows), 6) for kk, v in sorted(c.items())}),
        ("도메인 가짓수", len(set(doms))),
    ])


def over_seeds(pool, fn):
    """🔴 §2 — 겹 씨앗 다섯에서 재고 **평균과 SD** 를 낸다."""
    ps, es, pers = [], [], []
    for s in SEEDS:
        pool.reseed(s)
        po, eq, per = fn()
        ps.append(po)
        es.append(eq)
        pers.append(per)
    dom = collections.OrderedDict()
    for d in pool.gated:
        dom[d] = _r(float(np.mean([p[d] for p in pers if np.isfinite(p[d])]))
                    if any(np.isfinite(p[d]) for p in pers) else float("nan"))
    return {"묶음 ρ": _r(np.mean(ps)), "묶음 씨앗 SD": _r(np.std(ps, ddof=1)),
            "균등 ρ": _r(np.mean(es)), "균등 씨앗 SD": _r(np.std(es, ddof=1)),
            "씨앗별 묶음 ρ": [_r(x) for x in ps],
            "씨앗별 균등 ρ": [_r(x) for x in es],
            "도메인별 묶음 ρ(씨앗 평균)": dom,
            "🔴 씨앗 수": len(SEEDS)}


# ══════════════════════════════════════════════════════════════════════
# §S1 — α × λ 격자
# ══════════════════════════════════════════════════════════════════════
def stage_grid(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    _prog("grid 시작")
    pool = Pool()
    _prog("자료: base %d · hplt %d · 게이트 %d" %
          (len(pool.yb), len(pool.yh), len(pool.gated)))

    cells = collections.OrderedDict()
    budget_ok = 0
    n_cell = 0
    for u in UGRID:
        lam = 10.0 ** u
        for a in AGRID:
            r = over_seeds(pool, lambda a=a, lam=lam: score(pool, oof(pool, a, lam)["예측"]))
            pool.reseed(SEEDS[0])
            rows = oof(pool, a, lam)["겹별 학습 행"]
            fp = src_fingerprint(pool, a)
            ok_b = all(x == N_B for x in rows)
            budget_ok += 1 if ok_b else 0
            n_cell += 1
            cells["u=%d|α=%g" % (u, a)] = dict(
                r, **{"log₁₀λ": u, "α": a, "학습 행(겹별)": rows,
                      "🔴 학습 행이 예산과 같은가": bool(ok_b),
                      "원천 비율": fp["원천 비율"]})
            _prog("  u=%d α=%g  묶음 %.6f  균등 %.6f" % (u, a, r["묶음 ρ"], r["균등 ρ"]))

    # 🔴 반증조건 8 — α 말고 다른 성분이 움직였나.
    #   🔴 「α 는 base:hplt 비율만 바꾸기로 했다」의 실측 검사는
    #   **base 안의 두 원천 비율이 α 를 따라 움직이나** 다. 안 움직여야 한다.
    pool.reseed(SEEDS[0])
    fp8 = collections.OrderedDict()
    ref_ratio = None
    n_drift = 0
    for a in AGRID:
        fp = src_fingerprint(pool, a)
        n941 = fp["원천별"].get("sao941", 0)
        n959 = fp["원천별"].get("sao959", 0)
        rr = (n941 / float(n941 + n959)) if (n941 + n959) else float("nan")
        if a == ALPHA_BASE:
            ref_ratio = rr
        fp8["α=%g" % a] = {"원천별": fp["원천별"], "base 안 sao941 몫": _r(rr),
                           "도메인 가짓수": fp["도메인 가짓수"]}
    for a in AGRID:
        rr = fp8["α=%g" % a]["base 안 sao941 몫"]
        drift = (rr is not None and ref_ratio is not None
                 and np.isfinite(ref_ratio) and abs(rr - ref_ratio) > 0.02)
        fp8["α=%g" % a]["🔴 밑판과 0.02 넘게 다른가"] = bool(drift)
        n_drift += 1 if drift else 0

    # ── Q1 · Q2 · Q3 ──────────────────────────────────────────
    def cell(u, a, key="묶음 ρ"):
        return cells["u=%d|α=%g" % (u, a)][key]

    best = collections.OrderedDict()
    for a in AGRID:
        bu = max(UGRID, key=lambda u, a=a: cell(u, a))
        be = max(UGRID, key=lambda u, a=a: cell(u, a, "균등 ρ"))
        best["α=%g" % a] = {
            "🔴 λ 를 최적화한 묶음 ρ": cell(bu, a), "그 λ": "10^%d" % bu,
            "🔴 λ 를 최적화한 균등 ρ": cell(be, a, "균등 ρ"), "그 λ(균등)": "10^%d" % be}
    a0 = best["α=0"]["🔴 λ 를 최적화한 묶음 ρ"]
    a_others = [best["α=%g" % a]["🔴 λ 를 최적화한 묶음 ρ"] for a in AGRID if a > 0]
    q1 = a0 - max(a_others)
    e0 = best["α=0"]["🔴 λ 를 최적화한 균등 ρ"]
    e_others = [best["α=%g" % a]["🔴 λ 를 최적화한 균등 ρ"] for a in AGRID if a > 0]
    q1e = e0 - max(e_others)

    matched = collections.OrderedDict()
    n_pos = n_pos_eq = 0
    for u in UGRID:
        d = cell(u, 0.0) - cell(u, ALPHA_BASE)
        de = cell(u, 0.0, "균등 ρ") - cell(u, ALPHA_BASE, "균등 ρ")
        matched["10^%d" % u] = {"묶음 Δ(α=0 − α=0.95)": _r(d),
                                "균등 Δ(α=0 − α=0.95)": _r(de),
                                "α=0 묶음 ρ": cell(u, 0.0),
                                "α=0.95 묶음 ρ": cell(u, ALPHA_BASE),
                                "α=0 균등 ρ": cell(u, 0.0, "균등 ρ"),
                                "α=0.95 균등 ρ": cell(u, ALPHA_BASE, "균등 ρ"),
                                "🔴 두 자의 부호가 같은가": bool(d * de >= 0)}
        n_pos += 1 if d > 0 else 0
        n_pos_eq += 1 if de > 0 else 0
    n_a1_neg = sum(1 for u in UGRID
                   if cell(u, 1.0) - cell(u, ALPHA_BASE) < 0)

    # ── §S4 부호 뒤집힘 전수 (이 격자) ─────────────────────────
    flips_own = []
    for kk, v in cells.items():
        if v["α"] == ALPHA_BASE:
            continue
        db = v["묶음 ρ"] - cell(v["log₁₀λ"], ALPHA_BASE)
        de = v["균등 ρ"] - cell(v["log₁₀λ"], ALPHA_BASE, "균등 ρ")
        if db * de < 0:
            flips_own.append({"칸": kk, "묶음 Δ": _r(db), "균등 Δ": _r(de)})

    # ── §S4 부호 뒤집힘 전수 (976 산출물 · 재주행 없이) ──────────
    flips_976, n976 = [], 0
    f976 = OUT / "out976_factors.json"
    if f976.is_file():
        d976 = json.loads(f976.read_text(encoding="utf-8"))
        bb = d976["🔴 밑판 B (예산 맞춤 · 요인 Δ 의 기준)"]
        eq_b = bb["도메인 균등 ρ"]
        for fac, fv in d976["🔴🔴🔴 요인별"].items():
            for nm, row in fv["수준별"].items():
                if row.get("밑판인가"):
                    continue
                n976 += 1
                db = row["🔴🔴 Δ(수준 − 밑판 B)"]
                de = row["도메인 균등 ρ"] - eq_b
                if db * de < 0:
                    flips_976.append({"요인": fac.split(" ", 1)[0], "수준": nm,
                                      "묶음 Δ": _r(db), "균등 Δ": _r(de),
                                      "🔴 976 이 채택했나":
                                          bool(row["🔴🔴 채택(둘 다 · 밑판 제외)"])})

    # ── 도메인 몫 · 기여 분해 ─────────────────────────────────
    pool.reseed(SEEDS[0])
    tot_ho = sum(pool.dom_ho[d] for d in pool.gated)
    share = {d: _r(pool.dom_ho[d] / float(tot_ho)) for d in pool.gated}
    top_dom = max(pool.gated, key=lambda d: pool.dom_ho[d])
    base_cell = cells["u=%d|α=%g" % (U_REG[1], ALPHA_BASE)]
    contrib = {}
    for d in pool.gated:
        v = base_cell["도메인별 묶음 ρ(씨앗 평균)"][d]
        contrib[d] = _r((v or 0.0) * pool.dom_ho[d] / float(tot_ho))
    csum = sum(v for v in contrib.values() if v is not None)
    contrib_pct = {d: _r((contrib[d] / csum * 100.0) if csum else float("nan"), 4)
                   for d in contrib}

    # ── SE (등록된 λ 둘 · 겹 씨앗 다섯 · 이중 붓스트랩) ──────────
    _prog("SE 시작 (등록 λ %s · 뽑기 %d · 씨앗 %d)" % (U_REG, BOOT, len(SEEDS)))
    se, se_eq = collections.OrderedDict(), collections.OrderedDict()
    t_b = time.time()
    for u in U_REG:
        lam = 10.0 ** u
        acc = {a: [] for a in AGRID}
        acc_e = {a: [] for a in AGRID}
        for s in SEEDS:
            pool.reseed(s)
            for b in range(BOOT):
                hi = ho_draw(pool, b)
                vals, vals_e = {}, {}
                for a in AGRID:
                    pr = oof(pool, a, lam, tr_boot=b)["예측"]
                    vals[a], vals_e[a], _p = score(pool, pr, hi)
                for a in AGRID:
                    acc[a].append(vals[a] - vals[ALPHA_BASE])
                    acc_e[a].append(vals_e[a] - vals_e[ALPHA_BASE])
            _prog("  SE u=%d 씨앗 %d 끝 (%.0fs)" % (u, s, time.time() - t_b))
        for a in AGRID:
            se["u=%d|α=%g" % (u, a)] = _r(float(np.std(acc[a], ddof=1)))
            se_eq["u=%d|α=%g" % (u, a)] = _r(float(np.std(acc_e[a], ddof=1)))

    # ── 채택 판정 (등록된 λ 둘에서 · 🔴 두 자에서 다) ────────────
    adopt = collections.OrderedDict()
    n_adopt = n_adopt_eq = n_lev = 0
    for u in U_REG:
        for a in AGRID:
            if a == ALPHA_BASE:
                continue
            kk = "u=%d|α=%g" % (u, a)
            d = cells[kk]["묶음 ρ"] - cell(u, ALPHA_BASE)
            de = cells[kk]["균등 ρ"] - cell(u, ALPHA_BASE, "균등 ρ")
            s_ = se.get(kk) or 0.0
            se_ = se_eq.get(kk) or 0.0
            ok = bool(s_ > 0 and abs(d) >= 2 * s_ and abs(d) >= THR_CARD)
            ok_e = bool(se_ > 0 and abs(de) >= 2 * se_ and abs(de) >= THR_CARD)
            n_lev += 1
            n_adopt += 1 if ok else 0
            n_adopt_eq += 1 if ok_e else 0
            adopt[kk] = {"묶음 Δ": _r(d), "균등 Δ": _r(de),
                         "SE_이중(묶음)": s_, "SE_이중(균등)": se_,
                         "|Δ|/SE(묶음)": _r(abs(d) / s_, 4) if s_ else None,
                         "|Δ|/SE(균등)": _r(abs(de) / se_, 4) if se_ else None,
                         "🔴 문턱 ① |Δ| ≥ 2·SE": bool(s_ > 0 and abs(d) >= 2 * s_),
                         "🔴 문턱 ② |Δ| ≥ 0.00353": bool(abs(d) >= THR_CARD),
                         "🔴🔴 채택(묶음 자)": ok,
                         "🔴🔴 채택(균등 자)": ok_e,
                         "🔴 두 자가 같은 답을 내나": bool(ok == ok_e)}

    out = collections.OrderedDict()
    out["무엇"] = "977 §S1 — α × λ 격자. 🔴 **HPLT 를 넣는 게 나은가**를 정면으로 묻는다"
    out["🔴 축"] = "C3 (data spec · mixture · filtering) — 등록된 자는 leave-one-source-out Δ"
    out["사전등록"] = "docs/prereg_977_alpha.md §S1 · §S4"
    out["🔴 정본 자"] = "유보 예측 성능(개체 묶음 5겹 OOF · 도메인별 스피어만)"
    out["🔴 자료"] = {
        "base 행(= 유보 전량)": len(pool.yb), "hplt 행(= 학습에만)": len(pool.yh),
        "게이트 도메인": pool.gated, "게이트 유보 행 합": tot_ho,
        "도메인별 유보 몫": share, "🔴 가장 큰 도메인": top_dom,
        "🔴 가장 큰 도메인의 몫": share[top_dom],
        "겹 씨앗": SEEDS, "예산 N": N_B}
    out["🔴🔴🔴 격자(칸별)"] = cells
    out["🔴🔴🔴 α 별 최적 λ"] = best
    out["🔴🔴🔴 Q1 — HPLT 를 넣는 게 나은가"] = {
        "🔴 정의": "max_λ ρ(α=0) − max over α>0 of max_λ ρ(α)",
        "α=0 의 최적 묶음 ρ": _r(a0),
        "α>0 중 최고 묶음 ρ": _r(max(a_others)),
        "🔴🔴 Δ": _r(q1),
        "🔴🔴 통과": bool(q1 > 0),
        "α=0 의 최적 균등 ρ": _r(e0),
        "α>0 중 최고 균등 ρ": _r(max(e_others)),
        "🔴🔴 균등 자에서의 Δ": _r(q1e),
        "🔴🔴 두 자가 같은 부호를 내나": bool(q1 * q1e >= 0),
        "🔴 뜻": ("통과 = 참이면 **HPLT 를 학습에서 완전히 빼는 쪽이 낫다**. "
                "🔴 크기 판정은 아래 채택 절이 한다 — 이 절은 부호만 낸다"),
    }
    out["🔴🔴 Q2 — λ 를 맞춘 비교(α=0 vs α=0.95)"] = {
        "λ 별": matched,
        "🔴 양수인 λ 칸": "%d / %d" % (n_pos, len(UGRID)),
        "🔴🔴 균등 자에서 양수인 λ 칸": "%d / %d" % (n_pos_eq, len(UGRID)),
        "🔴🔴 두 자의 부호가 같은 λ 칸": "%d / %d" % (
            sum(1 for v in matched.values() if v["🔴 두 자의 부호가 같은가"]), len(UGRID)),
        "🔴 예측 P2(9 칸 중 5 이상 양수)": bool(n_pos >= 5),
        "통과": bool(n_pos >= 5),
    }
    out["🔴 Q3 — α=1 은 어느 λ 에서도 파괴인가"] = {
        "음수인 λ 칸": "%d / %d" % (n_a1_neg, len(UGRID)),
        "통과": bool(n_a1_neg == len(UGRID)),
    }
    #: 🔴 규칙 D — 976 의 수를 **손으로 옮기지 않는다**. 976 산출물에서 읽는다.
    d976_a0 = None
    if f976.is_file():
        d976_a0 = json.loads(f976.read_text(encoding="utf-8"))[
            "🔴🔴🔴 요인별"]["R5 원천 혼합 (data mixture)"]["수준별"]["α=0"][
            "🔴🔴 Δ(수준 − 밑판 B)"]
    out["🔴🔴 976 이 본 α=0 의 Δ 중 얼마가 λ 선택인가"] = {
        "🔴 976 의 Δ(α=0 − α=0.95 · λ 는 속겹 CV 가 골랐다)": d976_a0,
        "🔴 977 의 Δ(u=0 으로 맞춤)": matched["10^0"]["묶음 Δ(α=0 − α=0.95)"],
        "🔴 977 의 Δ(u=3 으로 맞춤)": matched["10^3"]["묶음 Δ(α=0 − α=0.95)"],
        "🔴 출처": ("이 수는 runners/out976_factors.json 의 R5 α=0 행에서 **읽었다** — "
                 "손 전사가 아니다"),
    }
    out["🔴🔴 §S4 두 자에서 부호가 뒤집히는 수준 — 전수"] = {
        "🔴 976 격자에서": flips_976,
        "🔴 976 분자/분모": "%d / %d" % (len(flips_976), n976),
        "🔴 그중 976 이 「채택」으로 적은 것":
            [f for f in flips_976 if f["🔴 976 이 채택했나"]],
        "🔴 이 사이클 격자에서": flips_own,
        "🔴 이 사이클 분자/분모": "%d / %d" % (len(flips_own), n_cell - len(UGRID)),
        "통과": bool(len(flips_976) > 0),
        "🔴 이 절의 통과가 뜻하는 것": "부호가 뒤집히는 수준이 **실제로 있다**",
    }
    out["🔴🔴 §S4 도메인 몫과 묶음 ρ 기여 분해"] = {
        "밑판 칸": "u=%d|α=%g" % (U_REG[1], ALPHA_BASE),
        "도메인별 묶음 ρ": base_cell["도메인별 묶음 ρ(씨앗 평균)"],
        "도메인별 유보 몫": share,
        "🔴 묶음 ρ 에 대한 기여(%)": contrib_pct,
        "🔴 가장 큰 도메인의 기여(%)": contrib_pct[top_dom],
        "🔴 한 도메인이 절반 이상인가(유보 몫)": bool(share[top_dom] >= 0.5),
        "통과": bool(share[top_dom] >= 0.5),
        "🔴 이 절의 통과가 뜻하는 것": "**한 도메인이 묶음 자의 절반 이상을 정한다**",
    }
    out["🔴 SE(이중 붓스트랩 · 등록 λ 둘 · 겹 씨앗 다섯 · 묶음 자)"] = se
    out["🔴 SE(이중 붓스트랩 · 균등 자)"] = se_eq
    out["🔴🔴 채택(문턱 둘)"] = adopt
    out["🔴 채택 분자/분모"] = "%d / %d" % (n_adopt, n_lev)
    out["🔴🔴 채택 분자/분모(균등 자)"] = "%d / %d" % (n_adopt_eq, n_lev)
    out["🔴🔴 두 자가 같은 채택 답을 내는 칸"] = "%d / %d" % (
        sum(1 for v in adopt.values() if v["🔴 두 자가 같은 답을 내나"]), n_lev)
    out["🔴 반증조건 7 — 학습 행이 예산과 같은 칸"] = "%d / %d" % (budget_ok, n_cell)
    out["통과: 반증조건 7"] = bool(budget_ok == n_cell)
    out["🔴🔴 반증조건 8 — α 말고 다른 성분이 움직였나"] = {
        "🔴 무엇을 재나": "base 안의 sao941 : sao959 비율이 α 를 따라 움직이나",
        "α 별": fp8,
        "🔴 밑판과 0.02 넘게 다른 α": "%d / %d" % (n_drift, len(AGRID)),
        "통과": bool(n_drift == 0),
    }
    out["통과: 반증조건 8"] = bool(n_drift == 0)
    out["🔴 반증조건 1 — 이 격자에 속겹 CV 가 있나"] = False
    out["통과: 반증조건 1(λ 를 얼렸다)"] = True
    out["🔴 반증조건 2 — 씨앗 하나로만 잰 수가 있나"] = False
    out["통과: 반증조건 2(씨앗 다섯 평균)"] = bool(len(SEEDS) >= 5)
    out["🔴 반증조건 4 — 두 자를 같이 냈나"] = True
    out["통과: 반증조건 4"] = True
    out["붓스트랩 뽑기"] = BOOT
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LO.SRC)
    (OUT / "out977_grid.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    _prog("grid 끝")
    return out


# ══════════════════════════════════════════════════════════════════════
# §S2 라벨 파괴 + §S3 leave-one-source-out
# ══════════════════════════════════════════════════════════════════════
WRECKS = collections.OrderedDict([
    ("D1 hplt y 전량", {"kind": "hplt", "n": None}),
    ("D2 base 학습 y 전량", {"kind": "base", "n": None}),
    ("D3 hplt y 중 무작위 90 행", {"kind": "hplt", "n": 90}),
    ("D4 학습 y 전량(둘 다)", {"kind": "both", "n": None}),
])


def stage_destroy(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    _prog("destroy 시작")
    pool = Pool()
    res = collections.OrderedDict()
    for u in U_REG:
        lam = 10.0 ** u
        for alpha in (ALPHA_BASE, 0.0):
            arm = "u=%d · α=%g" % (u, alpha)
            base = over_seeds(pool, lambda alpha=alpha, lam=lam:
                              score(pool, oof(pool, alpha, lam)["예측"]))
            pool.reseed(SEEDS[0])
            nb0 = len(select(pool, 0, alpha)[0])
            rows = collections.OrderedDict()
            for nm, w in WRECKS.items():
                ps, es, nwr = [], [], []
                for s in SEEDS:
                    pool.reseed(s)
                    for ws in range(N_WRECK):
                        r = oof(pool, alpha, lam,
                                wreck={"kind": w["kind"], "n": w["n"],
                                       "seed": 977000 + ws * 97})
                        po, eq, _p = score(pool, r["예측"])
                        ps.append(po)
                        es.append(eq)
                        nwr.append(r["부순 라벨 행(겹당)"])
                rows[nm] = {
                    "🔴 부순 라벨 행(겹당)": int(np.mean(nwr)),
                    "🔴 부순 몫": _r(np.mean(nwr) / float(N_B)),
                    "묶음 ρ": _r(np.mean(ps)), "묶음 SD(씨앗×섞기)": _r(np.std(ps, ddof=1)),
                    "균등 ρ": _r(np.mean(es)),
                    "🔴🔴 묶음 Δ(부순 것 − 밑판)": _r(np.mean(ps) - base["묶음 ρ"]),
                    "🔴 균등 Δ": _r(np.mean(es) - base["균등 ρ"]),
                    "🔴 벌 수(씨앗 × 섞기)": len(ps),
                }
                _prog("  %s / %s  Δ=%.6f" % (arm, nm, rows[nm]["🔴🔴 묶음 Δ(부순 것 − 밑판)"]))
            res[arm] = {"밑판": base, "밑판 base 학습 행(겹당)": nb0,
                        "밑판 hplt 학습 행(겹당)": N_B - nb0, "파괴별": rows}

    # ── SE (이중 붓스트랩 · 밑판 팔에서) ────────────────────────
    _prog("destroy SE 시작")
    se, se_e = collections.OrderedDict(), collections.OrderedDict()
    for u in U_REG:
        lam = 10.0 ** u
        acc = {nm: [] for nm in WRECKS}
        acce = {nm: [] for nm in WRECKS}
        for s in SEEDS:
            pool.reseed(s)
            for b in range(BOOT_D):
                hi = ho_draw(pool, b)
                v0, e0, _p = score(pool, oof(pool, ALPHA_BASE, lam,
                                             tr_boot=b)["예측"], hi)
                for nm, w in WRECKS.items():
                    pr = oof(pool, ALPHA_BASE, lam, tr_boot=b,
                             wreck={"kind": w["kind"], "n": w["n"],
                                    "seed": 977000})["예측"]
                    v, e, _p = score(pool, pr, hi)
                    acc[nm].append(v - v0)
                    acce[nm].append(e - e0)
        for nm in WRECKS:
            se["u=%d|%s" % (u, nm)] = _r(float(np.std(acc[nm], ddof=1)))
            se_e["u=%d|%s" % (u, nm)] = _r(float(np.std(acce[nm], ddof=1)))
        _prog("  destroy SE u=%d 끝" % u)

    # ── 판정 (사전등록 §4 의 규칙 그대로) ──────────────────────
    verdict = collections.OrderedDict()
    for u in U_REG:
        arm = "u=%d · α=%g" % (u, ALPHA_BASE)
        r = res[arm]["파괴별"]
        d1 = abs(r["D1 hplt y 전량"]["🔴🔴 묶음 Δ(부순 것 − 밑판)"])
        d2 = abs(r["D2 base 학습 y 전량"]["🔴🔴 묶음 Δ(부순 것 − 밑판)"])
        d3 = abs(r["D3 hplt y 중 무작위 90 행"]["🔴🔴 묶음 Δ(부순 것 − 밑판)"])
        d4 = abs(r["D4 학습 y 전량(둘 다)"]["🔴🔴 묶음 Δ(부순 것 − 밑판)"])
        s4 = se["u=%d|D4 학습 y 전량(둘 다)" % u] or 0.0
        s1 = se["u=%d|D1 hplt y 전량" % u] or 0.0
        s2 = se["u=%d|D2 base 학습 y 전량" % u] or 0.0
        verdict["u=%d" % u] = {
            "|Δ(D1)| — 1,710 행": _r(d1), "SE(D1)": s1,
            "|Δ(D1)|/SE": _r(d1 / s1, 4) if s1 else None,
            "|Δ(D2)| — 90 행": _r(d2), "SE(D2)": s2,
            "|Δ(D2)|/SE": _r(d2 / s2, 4) if s2 else None,
            "|Δ(D3)| — hplt 90 행": _r(d3),
            "|Δ(D4)| — 1,800 행": _r(d4), "SE(D4)": s4,
            "🔴🔴🔴 |Δ(D2)| ≥ |Δ(D1)| 인가": bool(d2 >= d1),
            "🔴 행당 효과 배율 (Δ2/90) / (Δ1/1710)":
                _r((d2 / 90.0) / (d1 / 1710.0), 4) if d1 > 0 else None,
            "🔴🔴 D4 가 문턱 둘을 넘나": bool(s4 > 0 and d4 >= 2 * s4 and d4 >= THR_CARD),
            "🔴 균등 자 D4 Δ": r["D4 학습 y 전량(둘 다)"]["🔴 균등 Δ"],
            "🔴 균등 자 D4 SE": se_e["u=%d|D4 학습 y 전량(둘 다)" % u],
            "🔴🔴 균등 자 D4 가 문턱 둘을 넘나": bool(
                (se_e["u=%d|D4 학습 y 전량(둘 다)" % u] or 0) > 0
                and abs(r["D4 학습 y 전량(둘 다)"]["🔴 균등 Δ"])
                >= 2 * se_e["u=%d|D4 학습 y 전량(둘 다)" % u]
                and abs(r["D4 학습 y 전량(둘 다)"]["🔴 균등 Δ"]) >= THR_CARD),
            "🔴 균등 자 D4 Δ 가 음수인가": bool(
                r["D4 학습 y 전량(둘 다)"]["🔴 균등 Δ"] < 0),
            "통과": bool(d2 >= d1),
            "🔴 이 절의 통과가 뜻하는 것":
                "**모형은 base 90 행 위에 서 있다** — 90 행이 1,710 행보다 자를 더 움직인다",
        }

    # ── §S3 leave-one-source-out ──────────────────────────────
    _prog("LOSO 시작")
    loso = collections.OrderedDict()
    for u in U_REG:
        lam = 10.0 ** u
        arms = collections.OrderedDict()
        for nm, drop in SRC_ARMS.items():
            r = over_seeds(pool, lambda drop=drop, lam=lam:
                           score(pool, oof(pool, ALPHA_BASE, lam,
                                           drop_src=drop)["예측"]))
            pool.reseed(SEEDS[0])
            fp = src_fingerprint(pool, ALPHA_BASE, drop)
            arms[nm] = dict(r, **{"원천 비율": fp["원천 비율"], "학습 행": fp["행"] // KFOLD})
            _prog("  LOSO %s / λ=10^%d  묶음 %.6f" % (nm, u, r["묶음 ρ"]))
        base = arms["ALL"]
        for nm in arms:
            arms[nm]["🔴🔴 묶음 Δ(그 원천을 뺀 것 − ALL)"] = _r(
                arms[nm]["묶음 ρ"] - base["묶음 ρ"])
            arms[nm]["🔴 균등 Δ"] = _r(arms[nm]["균등 ρ"] - base["균등 ρ"])
        loso["u=%d" % u] = {
            "팔별": arms,
            "🔴🔴 −hplt_ko 의 Δ 가 양수인가": bool(
                arms["−hplt_ko"]["🔴🔴 묶음 Δ(그 원천을 뺀 것 − ALL)"] > 0),
            "🔴🔴 −hplt_ko 의 균등 Δ 가 양수인가": bool(
                arms["−hplt_ko"]["🔴 균등 Δ"] > 0),
            "🔴🔴 두 자가 같은 답을 내나": bool(
                arms["−hplt_ko"]["🔴🔴 묶음 Δ(그 원천을 뺀 것 − ALL)"]
                * arms["−hplt_ko"]["🔴 균등 Δ"] >= 0),
            "통과": bool(arms["−hplt_ko"]["🔴🔴 묶음 Δ(그 원천을 뺀 것 − ALL)"] > 0),
            "🔴 이 절의 통과가 뜻하는 것":
                "C3 의 등록된 자(leave-one-source-out Δ)에서 **HPLT 를 빼는 게 낫다**",
        }

    # ── §S4 결정 — 🔴 도메인 균등을 정본으로 올릴까 (사전등록 §6 의 규칙 그대로) ──
    g = OUT / "out977_grid.json"
    cond1 = cond2 = None
    if g.is_file():
        dg = json.loads(g.read_text(encoding="utf-8"))
        cond1 = bool(dg["🔴🔴 §S4 도메인 몫과 묶음 ρ 기여 분해"]["🔴 한 도메인이 절반 이상인가(유보 몫)"])
        nflip = dg["🔴🔴 §S4 두 자에서 부호가 뒤집히는 수준 — 전수"]["🔴 976 분자/분모"]
        cond2 = int(nflip.split("/")[0].strip()) >= 1
    u_ = U_REG[1]
    d4eq = res["u=%d · α=%g" % (u_, ALPHA_BASE)]["파괴별"][
        "D4 학습 y 전량(둘 다)"]["🔴 균등 Δ"]
    cond3 = bool(d4eq < 0)
    promote = bool(cond1 and cond2 and cond3)
    decision = collections.OrderedDict([
        ("🔴 사전등록 §6 의 결정 규칙", "셋이 모두 참이면 도메인 균등을 정본으로 올린다"),
        ("조건 1 — 한 도메인이 묶음 자 가중의 50% 이상인가", cond1),
        ("조건 2 — 두 자에서 부호가 뒤집히는 수준이 1 개 이상인가", cond2),
        ("🔴🔴 조건 3 — 균등 자가 D4(라벨 전량 파괴)에서 죽나(Δ < 0)", cond3),
        ("🔴 D4 에서의 균등 Δ", d4eq),
        ("🔴🔴🔴 도메인 균등을 정본으로 올리나", promote),
        ("🔴🔴 올린 뒤 헤드라인이 어떻게 읽히나", {
            "묶음 자에서 −hplt_ko 의 Δ (u=3)":
                loso["u=%d" % U_REG[1]]["팔별"]["−hplt_ko"][
                    "🔴🔴 묶음 Δ(그 원천을 뺀 것 − ALL)"],
            "🔴 균등 자에서 −hplt_ko 의 Δ (u=3)":
                loso["u=%d" % U_REG[1]]["팔별"]["−hplt_ko"]["🔴 균등 Δ"],
            "묶음 자에서 −hplt_ko 의 Δ (u=0)":
                loso["u=%d" % U_REG[0]]["팔별"]["−hplt_ko"][
                    "🔴🔴 묶음 Δ(그 원천을 뺀 것 − ALL)"],
            "🔴 균등 자에서 −hplt_ko 의 Δ (u=0)":
                loso["u=%d" % U_REG[0]]["팔별"]["−hplt_ko"]["🔴 균등 Δ"],
            "🔴🔴 두 u 에서 균등 자의 부호가 같은가": bool(
                loso["u=%d" % U_REG[1]]["팔별"]["−hplt_ko"]["🔴 균등 Δ"]
                * loso["u=%d" % U_REG[0]]["팔별"]["−hplt_ko"]["🔴 균등 Δ"] > 0),
        }),
        ("통과", bool(cond1 is not None and cond2 is not None)),
        ("🔴🔴 왜 이렇게 정했나",
         "조건 3 이 없으면 「덜 편향된 자」와 「자료를 안 보는 자」를 못 가른다. "
         "라벨을 전부 부숴도 안 내려가는 자는 자가 아니다"),
    ])

    out = collections.OrderedDict()
    out["무엇"] = ("977 §S2·§S3·§S4 — 🔴 **학습 라벨을 부수는 대조 넷** · "
                 "**leave-one-source-out Δ**(C3 의 등록된 자) · **정본 자 결정**")
    out["🔴 축"] = "C3"
    out["사전등록"] = "docs/prereg_977_alpha.md §S2 · §S3"
    out["🔴 유보는 한 줄도 안 만졌다"] = True
    out["🔴 왜 이 대조인가"] = (
        "티처 #115 가 「hplt y 전량(95%)을 부숴도 0.52 SE」를 냈다. "
        "그 뜻을 가르려면 **크기가 90 행인 대조**가 필요하다 — D2 와 D3 이 그것이다")
    out["🔴🔴🔴 파괴 대조"] = res
    out["🔴 파괴 대조 SE(이중 붓스트랩 · 묶음 자)"] = se
    out["🔴 파괴 대조 SE(이중 붓스트랩 · 균등 자)"] = se_e
    out["🔴🔴🔴 판정 — 90 행이 1,710 행보다 자를 더 움직이나"] = verdict
    out["🔴🔴🔴 §S3 leave-one-source-out"] = loso
    out["🔴🔴🔴 §S4 결정 — 도메인 균등을 정본으로 올릴까"] = decision
    out["붓스트랩 뽑기"] = BOOT_D
    out["섞기 씨앗 수"] = N_WRECK
    out["겹 씨앗"] = SEEDS
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LO.SRC)
    (OUT / "out977_destroy.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    _prog("destroy 끝")
    return out


# ══════════════════════════════════════════════════════════════════════
# §S5 사다리
# ══════════════════════════════════════════════════════════════════════
def fit_loglin(ns, rs):
    x = np.log10(np.asarray(ns, float))
    y = np.asarray(rs, float)
    xx = x - x.mean()
    b = float((xx * (y - y.mean())).sum() / (xx * xx).sum())
    a = float(y.mean() - b * x.mean())
    return {"a": _r(a), "b": _r(b)}, (lambda n, a=a, b=b: a + b * math.log10(n))


def fit_power(ns, rs, cap=True):
    """`ρ(n) = ρ∞ − c·n^(−γ)` · 🔴 `cap` 이면 **ρ∞ ≤ 1 을 제약으로 건다**."""
    x = np.asarray(ns, float)
    y = np.asarray(rs, float)
    best = None
    g = 0.05
    while g <= 1.5001:
        z = x ** (-g)
        zz = z - z.mean()
        if (zz * zz).sum() > 0:
            c = -float((zz * (y - y.mean())).sum() / (zz * zz).sum())
            r_inf = float(y.mean() + c * z.mean())
            if cap and r_inf > 1.0:
                # 🔴 ρ∞ = 1 로 고정하고 c 만 최소제곱 (제약이 무는 자리)
                r_inf = 1.0
                den = float((z * z).sum())
                c = float(((r_inf - y) * z).sum() / den) if den > 0 else 0.0
            sse = float(((r_inf - c * z - y) ** 2).sum())
            if best is None or sse < best[0]:
                best = (sse, r_inf, c, g)
        g += 0.01
    _sse, r_inf, c, g = best
    return ({"ρ∞": _r(r_inf), "c": _r(c), "γ": _r(g),
             "🔴 ρ∞ ≤ 1 제약을 걸었나": bool(cap),
             "🔴 ρ∞ 가 1 을 넘나": bool(r_inf > 1.0),
             "🔴 γ 가 훑은 범위 끝에 붙었나": bool(g <= 0.0501 or g >= 1.4999)},
            (lambda n, r=r_inf, cc=c, gg=g: r - cc * (n ** (-gg))))


def stage_ladder(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    _prog("ladder 시작")
    pool = Pool()
    arms = collections.OrderedDict()
    for u in U_REG:
        lam = 10.0 ** u
        for alpha in (ALPHA_BASE, 0.0):
            key = "u=%d · α=%g" % (u, alpha)
            rungs, ns, rs = collections.OrderedDict(), [], []
            for n in (LADDER_A0 if alpha == 0.0 else LADDER):
                def one(n=n, alpha=alpha, lam=lam):
                    if n is None:
                        r = oof(pool, alpha, lam, full=True)
                    else:
                        g = globals()
                        old = g["N_B"]
                        g["N_B"] = n
                        try:
                            r = oof(pool, alpha, lam, fill=False)
                        finally:
                            g["N_B"] = old
                    one.rows = r["겹별 학습 행"]
                    return score(pool, r["예측"])
                v = over_seeds(pool, one)
                nn = int(np.mean(one.rows))
                kk = ("base 전량" if (n is None and alpha == 0.0)
                      else "전량" if n is None else str(n))
                rungs[kk] = dict(v, **{
                    "요청 n": ("전량" if n is None else n),
                    "실제 학습 행(겹 평균)": nn,
                    "겹별 학습 행": one.rows,
                    "🔴 예산 미달": (0 if n is None else max(0, n - nn))})
                ns.append(nn)
                rs.append(v["묶음 ρ"])
                _prog("  사다리 %s n=%s (실제 %d) ρ=%.6f (씨앗 SD %.6f)"
                      % (key, kk, nn, v["묶음 ρ"], v["묶음 씨앗 SD"]))
            keys = list(rungs)
            fit_i = [i for i, n in enumerate(ns) if n <= C6_FIT_MAX]
            pre_i = [i for i in range(len(ns)) if i not in fit_i]
            p1, f1 = fit_loglin([ns[i] for i in fit_i], [rs[i] for i in fit_i])
            p2, f2 = fit_power([ns[i] for i in fit_i], [rs[i] for i in fit_i], cap=True)
            p2u, f2u = fit_power([ns[i] for i in fit_i], [rs[i] for i in fit_i], cap=False)

            # 🔴 적합의 SE — 적합점 하나 빼기(LOO)
            loo1, loo2 = collections.defaultdict(list), collections.defaultdict(list)
            for drop in fit_i:
                sub = [i for i in fit_i if i != drop]
                _q1, g1 = fit_loglin([ns[i] for i in sub], [rs[i] for i in sub])
                _q2, g2 = fit_power([ns[i] for i in sub], [rs[i] for i in sub], cap=True)
                for i in pre_i:
                    loo1[i].append(g1(ns[i]))
                    loo2[i].append(g2(ns[i]))

            rows = collections.OrderedDict()
            for i in pre_i:
                kk = keys[i]
                se_obs = rungs[kk]["묶음 씨앗 SD"] / math.sqrt(len(SEEDS))
                se_f1 = float(np.std(loo1[i], ddof=1))
                se_f2 = float(np.std(loo2[i], ddof=1))
                e1 = abs(f1(ns[i]) - rs[i])
                e2 = abs(f2(ns[i]) - rs[i])
                t1 = math.sqrt(se_obs ** 2 + se_f1 ** 2)
                t2 = math.sqrt(se_obs ** 2 + se_f2 ** 2)
                rows[kk] = {
                    "실제 학습 행": ns[i], "🔴 실측 ρ": rs[i],
                    "형태 ① 예측": _r(f1(ns[i])), "🔴 형태 ① 오차": _r(e1),
                    "형태 ② 예측(ρ∞≤1)": _r(f2(ns[i])), "🔴 형태 ② 오차": _r(e2),
                    "🔴 SE_관측(씨앗 SD/√5)": _r(se_obs),
                    "🔴 SE_적합 ①(LOO)": _r(se_f1), "🔴 SE_적합 ②(LOO)": _r(se_f2),
                    "🔴 √(SE_관측²+SE_적합²) ①": _r(t1),
                    "🔴 √(SE_관측²+SE_적합²) ②": _r(t2),
                    "🔴🔴 형태 ① 오차 > 잡음인가": bool(e1 > t1),
                    "🔴🔴 형태 ② 오차 > 잡음인가": bool(e2 > t2),
                }
            mono = all(rs[i] <= rs[i + 1] for i in range(len(rs) - 1))
            worst = max((rs[i] - rs[i + 1]) for i in range(len(rs) - 1))
            arms[key] = {
                "사다리": rungs,
                "🔴 사다리가 단조인가": bool(mono),
                "🔴 최대 하락": _r(worst),
                "🔴 최대 하락 / 평균 씨앗 SE": _r(
                    worst / (float(np.mean([rungs[k]["묶음 씨앗 SD"] for k in rungs]))
                             / math.sqrt(len(SEEDS))), 4),
                "🔴 적합에 쓴 자리": [keys[i] for i in fit_i],
                "🔴 예측한 자리": [keys[i] for i in pre_i],
                "형태 ① 로그선형 모수": p1,
                "🔴🔴 형태 ② 포화 멱법칙 모수(ρ∞ ≤ 1 제약)": p2,
                "⚠ 형태 ② 제약 없는 적합(쓰지 않는다 · 대조용)": p2u,
                "🔴🔴🔴 예측 오차": rows,
                "통과": bool(mono),
                "🔴 이 절의 통과가 뜻하는 것": "λ 를 얼리고 씨앗 다섯을 평균하면 사다리가 단조다",
            }

    out = collections.OrderedDict()
    out["무엇"] = "977 §S5 — 🔴 사다리를 **λ 와 겹에서 뗀다**(ρ∞ ≤ 1 제약 · 적합 SE)"
    out["🔴 축"] = "C6 (scaling) — 곁으로 다시 연다"
    out["사전등록"] = "docs/prereg_977_alpha.md §S5"
    out["🔴 976 과 무엇이 다른가"] = (
        "① λ 를 자리마다 속겹 CV 로 고르지 않고 **등록된 값으로 얼렸다** "
        "② 자리마다 **겹 씨앗 다섯**을 평균했다 "
        "③ 형태 ② 에 **ρ∞ ≤ 1** 제약을 걸었다 "
        "④ 판정을 **√(SE_관측² + SE_적합²)** 로 한다")
    out["🔴🔴🔴 팔별"] = arms
    #: 🔴 규칙 D — 976 의 사다리 값을 **손으로 옮기지 않고 그 산출물에서 읽는다**.
    f976s = OUT / "out976_scaling.json"
    if f976s.is_file():
        rg = json.loads(f976s.read_text(encoding="utf-8"))[
            "🔴 사다리(밑판 P 구성 · 학습 행 수만 바꾼다)"]
        vs = [rg[k]["🔴 묶음 유보 ρ"] for k in rg]
        out["🔴🔴 976 이 잰 사다리(속겹 CV · 씨앗 하나)"] = {
            "최대 하락": _r(max(vs[i] - vs[i + 1] for i in range(len(vs) - 1))),
            "단조인가": bool(all(vs[i] <= vs[i + 1] for i in range(len(vs) - 1))),
            "🔴 출처": "runners/out976_scaling.json 에서 읽었다(손 전사가 아니다)",
        }
    out["🔴 반증조건 1 — 사다리에서 λ 가 자리마다 다른가"] = False
    out["통과: 반증조건 1"] = True
    out["🔴 반증조건 3 — ρ∞ > 1 인 적합을 판정에 썼나"] = False
    out["통과: 반증조건 3"] = True
    out["겹 씨앗"] = SEEDS
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LO.SRC)
    (OUT / "out977_ladder.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    _prog("ladder 끝")
    return out


# ══════════════════════════════════════════════════════════════════════
# 배선 W — 🔴 수리 2: 검사마다 **변이체 대조**를 붙인다
# ══════════════════════════════════════════════════════════════════════
def stage_wiring(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    _prog("wiring 시작")
    pool = Pool()
    W = collections.OrderedDict()

    def add(name, ok, mutant_ok, why):
        """🔴 `ok` = 참인 판에서의 결과 · `mutant_ok` = **일부러 깨뜨린 판**에서의 결과.

        `mutant_ok` 가 **참이면 그 검사는 자료로 반증될 수 없다** = 구성상 참.
        """
        W[name] = {"통과": bool(ok), "🔴 변이체에서도 통과하나": bool(mutant_ok),
                   "🔴🔴 구성상 참인 검사인가": bool(mutant_ok),
                   "🔴 변이체가 무엇인가": why}

    # W1 — α 가 만들어진 학습 집합의 HPLT 비율이다
    ok = all(abs(len(select(pool, 0, a)[1]) / float(N_B) - a) <= 1.0 / N_B
             for a in AGRID)
    mut = all(abs(len(select(pool, 0, a)[1]) / float(N_B) - 0.5) <= 1.0 / N_B
              for a in AGRID)
    add("W1 α 가 만들어진 학습 집합의 HPLT 비율이다", ok, mut,
        "α 대신 상수 0.5 와 견준다 — 참이면 이 검사는 α 를 안 본다")

    # W2 — 예산이 모든 α 에서 정확히 N_B
    rows = [len(select(pool, 0, a)[0]) + len(select(pool, 0, a)[1]) for a in AGRID]
    add("W2 모든 α 에서 학습 행이 정확히 예산이다", all(x == N_B for x in rows),
        all(x == N_B + 1 for x in rows),
        "예산을 N_B+1 로 견준다 — 참이면 검사가 자료를 안 본다")

    # W3 — 🔴 976 의 W3 은 자기가 만든 식을 자기가 다시 계산해 견줬다.
    #      여기서는 **독립 경로**로 센다: 실제 뽑힌 행의 원천 이름을 세어 α 와 맞춘다.
    selb, selh, _s = select(pool, 0, 0.4)
    n_h = int((pool.sh[selh] == "hplt_ko").sum())
    n_b = int(np.isin(pool.sb[selb], ["sao941", "sao959"]).sum())
    mb, mh, _s = select(pool, 0, 0.8)          # 🔴 변이체 — 다른 α 로 만든 자료
    mn_h = int((pool.sh[mh] == "hplt_ko").sum())
    mn_b = int(np.isin(pool.sb[mb], ["sao941", "sao959"]).sum())
    add("W3 뽑힌 행의 원천 이름을 직접 세면 α 와 맞는다",
        (n_h == len(selh) and n_b == len(selb)
         and abs(n_h / float(n_h + n_b) - 0.4) <= 1.0 / N_B),
        bool(mn_h == len(mh) and mn_b == len(mb)
             and abs(mn_h / float(mn_h + mn_b) - 0.4) <= 1.0 / N_B),
        "α=0.8 로 만든 자료를 α=0.4 의 기대값과 견준다 — 참이면 검사가 자료를 안 본다")

    # W4 — 학습 선택에 그 겹의 유보 행이 0 줄이다
    leak = sum(int((pool.fi[select(pool, j, a)[0]] == j).sum())
               for a in AGRID for j in range(KFOLD))
    #: 🔴 변이체 — `avail_b` 를 전량 참으로 두면 새는지 본다(진짜 변이체다)
    def leaky_select(fold, alpha):
        nh = int(round(alpha * N_B))
        nb = N_B - nh
        return pool.perm_b[:nb]
    leak_mut = sum(int((pool.fi[leaky_select(j, a)] == j).sum())
                   for a in AGRID for j in range(KFOLD))
    add("W4 학습 선택에 그 겹의 유보 행이 0 줄이다", leak == 0, leak_mut == 0,
        "겹 제외를 뺀 뽑기로 견준다 — 그때도 0 이면 이 검사는 아무것도 안 본다")

    # W5 — 🔴 겹 씨앗을 바꾸면 겹 배정이 실제로 바뀐다(976 의 W8 이 못 한 것)
    fis = []
    for s in SEEDS:
        pool.reseed(s)
        fis.append(hashlib.sha256(pool.fi.tobytes()).hexdigest())
    add("W5 겹 씨앗 다섯이 서로 다른 겹 배정을 만든다", len(set(fis)) == len(SEEDS),
        len({hashlib.sha256(pool.fi.tobytes()).hexdigest() for _s in SEEDS}) == len(SEEDS),
        "루프 변수를 안 쓰고 같은 값을 다섯 번 넣어 본다 — 976 의 W8 이 이 꼴이었다")
    pool.reseed(SEEDS[0])

    # W6 — 라벨을 부수면 학습 y 가 실제로 바뀐다(그리고 유보 y 는 안 바뀐다)
    yb0 = pool.yb.copy()
    selb, selh, _s = select(pool, 0, ALPHA_BASE)
    _X, y, _e, nb = design(pool, selb, selh)
    y1, cnt = wreck_y(y, nb, "hplt", 11)
    y0, cnt0 = wreck_y(y, nb, "hplt", 11, n=0)     # 🔴 변이체 — 0 행만 부순다
    add("W6 라벨 파괴가 학습 y 를 바꾸고 유보 y 는 안 바꾼다",
        bool((y1 != y).any() and np.array_equal(pool.yb, yb0) and cnt == len(y) - nb),
        bool((y0 != y).any() and np.array_equal(pool.yb, yb0) and cnt0 == len(y) - nb),
        "0 행만 부순 판으로 견준다 — 그때도 통과하면 검사가 파괴를 안 본다")

    # W7 — 원천을 빼면 그 원천 행이 학습에서 0 이다
    okz, mutz = [], []
    for nm, drop in SRC_ARMS.items():
        if not drop:
            continue
        sb, sh, _s = select(pool, 0, ALPHA_BASE, drop)
        got = set(pool.sb[sb].tolist()) | set(pool.sh[sh].tolist())
        okz.append(all(d not in got for d in drop))
        sb2, sh2, _s = select(pool, 0, ALPHA_BASE, ())   # 🔴 변이체 — 안 뺀 자료
        got2 = set(pool.sb[sb2].tolist()) | set(pool.sh[sh2].tolist())
        mutz.append(all(d not in got2 for d in drop))
    add("W7 원천을 빼면 만들어진 학습 자료에 그 원천이 0 행이다", all(okz), all(mutz),
        "원천을 **안 뺀** 자료에 같은 검사를 건다 — 그때도 통과하면 검사가 자료를 안 본다")

    # W8 — 976 의 밑판 B 를 이 러너로 재현한다(배관 동일 증거)
    pool.reseed(976)
    p976, _e, _p = score(pool, oof(pool, ALPHA_BASE, 1000.0)["예측"])
    p_mut, _e, _p = score(pool, oof(pool, ALPHA_BASE, 1.0)["예측"])
    tgt = 0.242961
    add("W8 밑판 B(alpha=0.95 · u=3 · 겹 씨앗은 앞 사이클 것)를 소수 여섯 자리까지 재현한다",
        round(p976, 6) == tgt, round(p_mut, 6) == tgt,
        "같은 검사를 λ=10⁰ 로 만든 판에 건다 — 그때도 맞으면 검사가 설정을 안 본다")
    W["W8 밑판 B(alpha=0.95 · u=3 · 겹 씨앗은 앞 사이클 것)를 소수 여섯 자리까지 재현한다"].update(
        {"🔴 실측": _r(p976), "🔴 976 산출물이 적은 값": tgt,
         "🔴 변이체(λ=10⁰) 실측": _r(p_mut)})
    pool.reseed(SEEDS[0])

    n_ok = sum(1 for v in W.values() if v["통과"])
    n_const = sum(1 for v in W.values() if v["🔴🔴 구성상 참인 검사인가"])

    # ── 파괴 대조 E (두 자에서 다 낸다 — 반증조건 4) ─────────────
    E = collections.OrderedDict()
    lam = 10.0 ** U_REG[1]
    base = oof(pool, ALPHA_BASE, lam)
    pb, eb, _p = score(pool, base["예측"])
    for nm, w in WRECKS.items():
        r = oof(pool, ALPHA_BASE, lam,
                wreck={"kind": w["kind"], "n": w["n"], "seed": 4242})
        po, eq, _p = score(pool, r["예측"])
        E["E %s" % nm] = {"묶음 ρ": _r(po), "균등 ρ": _r(eq),
                          "묶음 Δ": _r(po - pb), "균등 Δ": _r(eq - eb),
                          "🔴 두 자에서 부호가 같은가": bool((po - pb) * (eq - eb) >= 0),
                          "통과": bool(po < pb)}
    shuf = np.random.RandomState(12).permutation(len(pool.yb))
    p_sh, e_sh, _p = score(pool, base["예측"][shuf])
    E["E 유보 y 를 섞으면 상관이 죽는다"] = {
        "묶음 ρ": _r(p_sh), "균등 ρ": _r(e_sh), "통과": bool(abs(p_sh) < 0.1)}
    E["E α=1 은 파괴다"] = {}
    r1 = oof(pool, 1.0, lam)
    p1_, e1_, _p = score(pool, r1["예측"])
    E["E α=1 은 파괴다"] = {"묶음 ρ": _r(p1_), "균등 ρ": _r(e1_),
                       "묶음 Δ": _r(p1_ - pb), "균등 Δ": _r(e1_ - eb),
                       "통과": bool(p1_ < pb)}
    n_e = sum(1 for v in E.values() if v.get("통과") is True)
    #: 🔴 **진짜 파괴 대조**는 넷이다 — D2(base 90 행) · D4(전량) · 유보 y 섞기 · α=1.
    #: D1·D3 은 **대조가 아니라 이 사이클의 측정 대상**이다. 떨어져도 배선 실패가 아니라
    #: **그것이 헤드라인**이다. 🔴 분모를 갈라서 둘 다 적는다(조항: 계수를 부풀리지 않는다).
    TRUE_E = ["E D2 base 학습 y 전량", "E D4 학습 y 전량(둘 다)",
              "E 유보 y 를 섞으면 상관이 죽는다", "E α=1 은 파괴다"]
    n_te = sum(1 for k in TRUE_E if E[k].get("통과") is True)

    out = collections.OrderedDict()
    out["무엇"] = "977 — 배선 W1~W8(🔴 **변이체 대조를 붙였다**) · 파괴 대조 E"
    out["🔴 축"] = "C3 (+ C6)"
    out["🔴 수리 2 가 무엇인가"] = (
        "검사마다 **일부러 깨뜨린 판**을 같이 돌린다. 깨뜨린 판에서도 통과하면 "
        "그 검사는 **자료로 반증될 수 없다** = 구성상 참. 976 은 W 를 10/10 이라 적었는데 "
        "티처 #115 가 손으로 세니 정직한 수는 6/10 이었다")
    out["W"] = W
    out["🔴 W 분자/분모(통과)"] = "%d / %d" % (n_ok, len(W))
    out["🔴🔴🔴 W 구성상 참인 검사 분자/분모"] = "%d / %d" % (n_const, len(W))
    out["🔴🔴 정직한 W 분자/분모(구성상 참을 뺀다)"] = "%d / %d" % (
        sum(1 for v in W.values() if v["통과"] and not v["🔴🔴 구성상 참인 검사인가"]),
        len(W) - n_const)
    out["통과: 배선"] = bool(n_ok == len(W))
    out["E"] = E
    out["🔴 E 분자/분모(전부)"] = "%d / %d" % (n_e, len(E))
    out["🔴🔴 진짜 파괴 대조 분자/분모"] = "%d / %d" % (n_te, len(TRUE_E))
    out["🔴 진짜 파괴 대조가 무엇인가"] = TRUE_E
    out["🔴🔴 D1·D3 이 떨어지는 것은 배선 실패가 아니다"] = (
        "D1(hplt y 전량 1,710 행)·D3(hplt y 90 행)은 **대조가 아니라 이 사이클의 측정 대상**이다. "
        "「학습 라벨을 부수면 자가 내려간다」가 hplt 쪽에서 **거짓**인 것이 헤드라인이다")
    out["🔴 E 에서 두 자의 부호가 같은 것"] = "%d / %d" % (
        sum(1 for v in E.values() if v.get("🔴 두 자에서 부호가 같은가")), len(WRECKS))
    out["🔴🔴 균등 자가 파괴 대조에서 죽나(D4 균등 Δ < 0)"] = bool(
        E["E D4 학습 y 전량(둘 다)"]["균등 Δ"] < 0)
    out["통과: 파괴 대조"] = bool(n_te == len(TRUE_E))
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LO.SRC)
    (OUT / "out977_wiring.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    _prog("wiring 끝")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    choices=["wiring", "grid", "destroy", "ladder"])
    ap.add_argument("--ref", default="")
    a = ap.parse_args()
    r = {"wiring": stage_wiring, "grid": stage_grid,
         "destroy": stage_destroy, "ladder": stage_ladder}[a.stage](a.ref)
    print(json.dumps({k: v for k, v in r.items()
                      if k not in ("🔴🔴🔴 격자(칸별)", "🔴🔴🔴 팔별",
                                   "🔴🔴🔴 파괴 대조")},
                     ensure_ascii=False, indent=1, default=str)[:6000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
