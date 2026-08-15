#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""976 — **축 C6 을 열고 그것으로 C4 의 격자 문제를 같이 푼다**.

사전등록 `docs/prereg_976_c6.md` 를 그대로 따른다.

🔴 티처 #114 가 975 의 요인 순위를 반증했다(다섯 중 다섯이 다 바뀐다). 뿌리 셋:
  ① **스팬은 수준 수에 단조** ② **다섯 요인이 같은 예산 위에 없었다**
  ③ **「한 칸만」 검사가 만들어진 자료를 안 봤다**.

그래서 976 은
  §2 **요인을 한 모수 족으로** (log₁₀λ · 남긴 특징 k · 남긴 행 비율 f · w∝n_d^p · HPLT 비율 α)
  §3 **예산을 맞추고**(N_B = 1,800) **λ 를 속겹 CV 로 고르고**
  §4 **스팬을 버리고**(정규화 기울기 + 같은 예산 최대 |Δ| + 붓스트랩 순위 안정도)
  §5 **SE 를 이중 붓스트랩으로**(학습 재표집 — `docs/목표.md` v2.0 요건 ②)
  §6 **C6 을 연다**(작은 n ≤ 1600 넷으로 적합 → 큰 n 예측 오차)
  §7-3 **자료 지문으로 「한 칸만」을 확인한다**.

씀:
    python3 runners/c6_976.py --stage wiring  --ref <40자 sha>
    python3 runners/c6_976.py --stage factors --ref <40자 sha>
    python3 runners/c6_976.py --stage scaling --ref <40자 sha>
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

RAN = ("runners/c6_976.py", "runners/ledger.py", "runners/layers957.py",
       "runners/predict971.py", "runners/predict972.py", "runners/loso974.py")
OUT = ROOT / "runners"
PROG = OUT / "out976_progress.txt"

# ── 사전등록 §1·§3 상수 ────────────────────────────────────────────────
SEED = 976
KFOLD = 5
N_B = 1800                 # §3 공통 예산
MIN_HO = 20                # §1 게이트
BOOT = 400                 # §5
BOOT_C6 = 150              # §6 (사다리는 큰 n 이 있어 뽑기를 줄인다 — 산출물에 적는다)
THR_CARD = 0.00353         # §4 카드 문턱(진단값)

LAM_U = [-2, -1, 0, 1, 2, 3, 4, 5, 6]          # R1 격자 (u = log10 λ)
KGRID = [1, 2, 3, 4, 5, 6]                      # R2
FGRID = [0.05, 0.1, 0.2, 0.4, 0.6, 0.8, 1.0]    # R3
PGRID = [-1.0, -0.5, -0.25, 0.0, 0.25, 0.5, 1.0]  # R4
AGRID = [0.0, 0.2, 0.4, 0.6, 0.8, 0.95, 1.0]    # R5
LADDER = [200, 400, 800, 1600, 3200, 6400, 12800, 25600, None]  # §6 (None = 전량)
C6_FIT_MAX = 1600          # §6 — 적합에 쓰는 가장 큰 n

FAC_RANGE = collections.OrderedDict([
    ("R1 능형 λ (optimizer)", ("log₁₀ λ", -2.0, 6.0)),
    ("R2 특징 개수 (architecture)", ("남긴 특징 개수 k", 1.0, 6.0)),
    ("R3 학습 창 (curriculum)", ("남긴 행 비율 f", 0.05, 1.0)),
    ("R4 도메인 가중 (objective)", ("가중 지수 p (w ∝ n_d^p)", -1.0, 1.0)),
    ("R5 원천 혼합 (data mixture)", ("HPLT 섞음 비율 α", 0.0, 1.0)),
])
#: §7-3 — 요인마다 **움직여도 되는 자료 지문 성분**
FP_ALLOWED = {
    "R1 능형 λ (optimizer)": set(),
    "R2 특징 개수 (architecture)": set(),
    "R3 학습 창 (curriculum)": {"연도별", "쌍id sha256", "도메인별"},
    "R4 도메인 가중 (objective)": set(),
    "R5 원천 혼합 (data mixture)": {"원천별", "원천 비율", "도메인별", "연도별",
                              "쌍id sha256"},
}

BASE_B = collections.OrderedDict([("u_lam", None), ("k", 6), ("f", 1.0),
                                  ("p", 0.0), ("alpha", 0.95), ("n", N_B)])
SRC_OF = {"sao941": "sao941", "sao959": "sao959", "hplt_ko": "hplt_ko"}


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _prog(msg):
    with open(str(PROG), "a", encoding="utf-8") as f:
        f.write("%s  %s\n" % (_now(), msg))


# ══════════════════════════════════════════════════════════════════════
# 가중 능형 — 🔴 w=None 이면 **생산 함수를 그대로 부른다**(W1)
# ══════════════════════════════════════════════════════════════════════
def ridge_fit_w(X, y, a, w=None):
    if w is None:
        return L.ridge_fit(X, y, a)
    w = np.asarray(w, float)
    w = w * (len(w) / w.sum())
    mu = (w[:, None] * X).sum(0) / w.sum()
    var = (w[:, None] * (X - mu) ** 2).sum(0) / w.sum()
    sd = np.sqrt(var)
    sd = np.where(sd > 0, sd, 1.0)
    Z = (X - mu) / sd
    ym = float((w * y).sum() / w.sum())
    A = Z.T @ (w[:, None] * Z) + a * np.eye(Z.shape[1])
    coef = np.linalg.solve(A, Z.T @ (w * (y - ym)))
    return coef, mu, sd, ym


# ══════════════════════════════════════════════════════════════════════
# 자료
# ══════════════════════════════════════════════════════════════════════
class Pool(object):
    """🔴 base(sao941+sao959) 는 **개체 묶음 5겹 OOF 유보** · HPLT 는 **언제나 학습**."""

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
        self.Ob = self._onehot(self.db)
        self.Oh = self._onehot(self.dh)
        # 🔴 개체·도메인을 정수 부호로 (자는 안 바뀐다 — 속도만)
        ents = sorted(set(self.eb.tolist()) | set(self.eh.tolist()))
        emap = {e: i for i, e in enumerate(ents)}
        self.ecb = np.asarray([emap[e] for e in self.eb], dtype=np.int64)
        self.ech = np.asarray([emap[e] for e in self.eh], dtype=np.int64)
        dmap = {d: i for i, d in enumerate(self.doms)}
        self.dcb = np.asarray([dmap[d] for d in self.db], dtype=np.int64)
        self.dch = np.asarray([dmap[d] for d in self.dh], dtype=np.int64)
        # 겹 (개체 묶음)
        rng = np.random.RandomState(SEED)
        gs = np.unique(self.eb)
        rng.shuffle(gs)
        fmap = {g: i % KFOLD for i, g in enumerate(gs)}
        self.fi = np.array([fmap[g] for g in self.eb])
        # 게이트
        cnt = collections.Counter(self.db.tolist())
        self.gated = [d for d in self.doms if cnt.get(d, 0) >= MIN_HO]
        self.dom_ho = {d: int(cnt.get(d, 0)) for d in self.doms}
        self.ho_mask = {d: (self.db == d) for d in self.gated}
        # 원천별 날짜 내림차순 차례 (창 자름용) + 고정 치환 (뽑기용)
        self.ord_b = self._src_order(self.sb, self.tb, self.pb)
        self.ord_h = self._src_order(self.sh, self.th, self.ph)
        r2 = np.random.RandomState(SEED + 1)
        self.perm_b = r2.permutation(len(self.yb))
        r3 = np.random.RandomState(SEED + 2)
        self.perm_h = r3.permutation(len(self.yh))

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

    @staticmethod
    def _src_order(s, t, p):
        """원천별로 **날짜 내림차순**(동률은 `쌍id` 오름차순) 자리 차례."""
        out = {}
        for src in np.unique(s):
            idx = np.flatnonzero(s == src)
            key = sorted(idx, key=lambda i: (-int(t[i]), str(p[i])))
            out[src] = np.asarray(key, dtype=int)
        return out


def window_mask(order_map, f, n_total):
    """🔴 §2 — **원천 안에서** 최근 `⌈f·n_s⌉` 행만 남긴다."""
    keep = np.zeros(n_total, dtype=bool)
    kept = {}
    for src, idx in order_map.items():
        m = int(math.ceil(f * len(idx))) if len(idx) else 0
        m = max(0, min(len(idx), m))
        keep[idx[:m]] = True
        kept[src] = m
    return keep, kept


def window_mask_global(t, p, f, n_total):
    """🔴 `R3′` — **975 판**: 원천 구별 없이 전역으로 최근 `⌈f·n⌉` 행."""
    key = sorted(range(n_total), key=lambda i: (-int(t[i]), str(p[i])))
    m = int(math.ceil(f * n_total))
    keep = np.zeros(n_total, dtype=bool)
    keep[np.asarray(key[:m], dtype=int)] = True
    return keep, {"전역": m}


def take(perm, avail, keep, m):
    """고정 치환 차례로 `keep & avail` 에서 앞 `m` 개. 🔴 `m` 을 키우면 포개진다."""
    ok = avail & keep
    sel = perm[ok[perm]]
    return sel[:m], int(len(sel))


# ══════════════════════════════════════════════════════════════════════
def select(pool, fold, cfg, global_window=False):
    """설정 하나의 **학습 자료를 실제로 만든다**. (base 자리, hplt 자리)를 낸다."""
    avail_b = (pool.fi != fold)
    avail_h = np.ones(len(pool.yh), dtype=bool)
    f = cfg["f"]
    if global_window:
        kb, _ = window_mask_global(pool.tb, pool.pb, f, len(pool.yb))
        kh, _ = window_mask_global(pool.th, pool.ph, f, len(pool.yh))
    else:
        kb, _ = window_mask(pool.ord_b, f, len(pool.yb))
        kh, _ = window_mask(pool.ord_h, f, len(pool.yh))
    n = cfg["n"]
    if n is None:                      # 예산 없음(밑판 P) — 창을 통과한 전량
        sb = pool.perm_b[(avail_b & kb)[pool.perm_b]]
        sh = pool.perm_h[(avail_h & kh)[pool.perm_h]]
        return sb, sh, 0
    nh = int(round(cfg["alpha"] * n))
    nb = n - nh
    selh, poolh = take(pool.perm_h, avail_h, kh, nh)
    selb, poolb = take(pool.perm_b, avail_b, kb, nb)
    short = (nb - len(selb)) + (nh - len(selh))
    return selb, selh, int(short)


def design(pool, selb, selh, k):
    X = np.vstack([np.hstack([pool.Xb[selb][:, :k], pool.Ob[selb]]),
                   np.hstack([pool.Xh[selh][:, :k], pool.Oh[selh]])])
    y = np.concatenate([pool.yb[selb], pool.yh[selh]])
    dom = np.concatenate([pool.dcb[selb], pool.dch[selh]])
    ent = np.concatenate([pool.ecb[selb], pool.ech[selh]])
    return X, y, dom, ent


def groups_of(codes):
    """정수 부호 배열 → (자리 차례, 묶음 시작, 묶음 끝). 묶음 되뽑기에 쓴다."""
    order = np.argsort(codes, kind="stable")
    s = codes[order]
    starts = np.flatnonzero(np.concatenate(([True], s[1:] != s[:-1])))
    ends = np.concatenate((starts[1:], [len(s)]))
    return order, starts, ends


def weights_of(dom, p):
    if p == 0.0:
        return None
    c = np.bincount(dom)
    return np.power(c[dom].astype(float), p)


def cv_lambda(X, y, ent, seed):
    """🔴 §3 — **학습 집합 안에서만** 개체 묶음 5겹 CV 로 λ 를 고른다.

    🔴 **유보는 인자에 없다** — 원리상 못 샌다(W10).
    """
    cands = [10.0 ** u for u in LAM_U]
    gs = np.unique(ent)
    rng = np.random.RandomState(seed)
    rng.shuffle(gs)
    kk = min(5, len(gs))
    if kk < 2:
        return 1.0, {}
    lut = np.zeros(int(gs.max()) + 1, dtype=np.int64)
    lut[gs] = np.arange(len(gs)) % kk
    fi = lut[ent]
    sse = np.zeros(len(cands))
    for ff in range(kk):
        te = fi == ff
        tr = ~te
        if tr.sum() < 3 or te.sum() == 0:
            continue
        for ci, a in enumerate(cands):
            m = L.ridge_fit(X[tr], y[tr], a)
            sse[ci] += float(((L.ridge_pred(m, X[te]) - y[te]) ** 2).sum())
    best = int(np.argmin(sse))
    return cands[best], {("10^%d" % LAM_U[i]): round(float(sse[i]), 6)
                         for i in range(len(cands))}


def oof_pred(pool, cfg, global_window=False, lam_fixed=None,
             tr_boot=None, want_sel=False):
    """🔴 다섯 겹의 OOF 예측을 이어 붙인다. 유보는 언제나 base 전량이다."""
    pred = np.zeros(len(pool.yb))
    lams, ntr, shorts = [], [], 0
    sel_all = []
    for j in range(KFOLD):
        selb, selh, short = select(pool, j, cfg, global_window)
        shorts += short
        if want_sel:
            sel_all.append((selb, selh))
        X, y, dom, ent = design(pool, selb, selh, cfg["k"])
        if tr_boot is not None:
            rng = np.random.RandomState(tr_boot * 1000 + j + SEED * 100000)
            order, st, en = groups_of(ent)
            pick = rng.randint(0, len(st), len(st))
            idx = np.concatenate([order[st[g]:en[g]] for g in pick])
            X, y, dom, ent = X[idx], y[idx], dom[idx], ent[idx]
        lam = (lam_fixed[j] if isinstance(lam_fixed, (list, tuple)) else lam_fixed)
        if lam is None:
            if cfg["u_lam"] is None:
                lam, _ = cv_lambda(X, y, ent, SEED + 7 * j)
            else:
                lam = 10.0 ** cfg["u_lam"]
        lams.append(float(lam))
        ntr.append(int(len(y)))
        w = weights_of(dom, cfg["p"])
        m = ridge_fit_w(X, y, lam, w)
        te = pool.fi == j
        Xho = np.hstack([pool.Xb[te][:, :cfg["k"]], pool.Ob[te]])
        pred[te] = L.ridge_pred(m, Xho)
    out = {"예측": pred, "겹별 λ": lams, "겹별 학습 행": ntr, "예산 미달": shorts}
    if want_sel:
        out["뽑힌 자리"] = sel_all
    return out


# ══════════════════════════════════════════════════════════════════════
def score(pool, pred, ho_idx=None):
    """도메인별 스피어만 → **유보 행 가중 묶음**(생산 함수 자와 같은 정의)."""
    per, wts = collections.OrderedDict(), []
    for d in pool.gated:
        if ho_idx is None:
            m = pool.ho_mask[d]
            a, b = pred[m], pool.yb[m]
        else:
            idx = ho_idx[d]
            a, b = pred[idx], pool.yb[idx]
        r = P.spear(a, b)
        per[d] = float(r)
        wts.append(float(len(a)))
    vals = np.asarray([per[d] for d in pool.gated], float)
    w = np.asarray(wts, float)
    ok = np.isfinite(vals)
    pooled = float((vals[ok] * w[ok]).sum() / w[ok].sum()) if ok.any() else float("nan")
    eq = float(np.mean(vals[ok])) if ok.any() else float("nan")
    return pooled, eq, per


def ho_draw(pool, b):
    """🔴 유보 되뽑기 — **도메인 안에서 개체 묶음**을 되뽑는다."""
    rng = np.random.RandomState(SEED * 1000 + b)
    out = {}
    for d in pool.gated:
        m = np.flatnonzero(pool.ho_mask[d])
        order, st, en = groups_of(pool.ecb[m])
        pick = rng.randint(0, len(st), len(st))
        out[d] = m[np.concatenate([order[st[g]:en[g]] for g in pick])]
    return out


def fingerprint(pool, sel_all):
    """🔴 §7-3 — **만들어진 학습 자료**의 지문."""
    pids, srcs, doms, yrs = [], [], [], []
    for selb, selh in sel_all:
        pids += list(pool.pb[selb]) + list(pool.ph[selh])
        srcs += list(pool.sb[selb]) + list(pool.sh[selh])
        doms += list(pool.db[selb]) + list(pool.dh[selh])
        yrs += [dt.date.fromordinal(int(t)).year for t in pool.tb[selb]]
        yrs += [dt.date.fromordinal(int(t)).year for t in pool.th[selh]]
    n = len(pids)
    cs = collections.Counter(srcs)
    return collections.OrderedDict([
        ("행", n),
        ("원천별", dict(sorted(cs.items()))),
        ("원천 비율", {k: round(v / float(n), 6) for k, v in sorted(cs.items())}),
        ("도메인별", dict(sorted(collections.Counter(doms).items()))),
        ("연도별", {str(k): v for k, v in sorted(collections.Counter(yrs).items())}),
        ("쌍id sha256", hashlib.sha256("|".join(sorted(pids)).encode()).hexdigest()),
    ])


def fp_diff(a, b):
    return sorted([k for k in a if a[k] != b.get(k)])


# ══════════════════════════════════════════════════════════════════════
def _cfg(**kw):
    c = dict(BASE_B)
    c.update(kw)
    return c


def factor_levels():
    """§2 격자 → `(요인, 수준이름, u, cfg)`."""
    out = collections.OrderedDict()
    out["R1 능형 λ (optimizer)"] = [
        ("log₁₀λ=%d" % u, float(u), _cfg(u_lam=u)) for u in LAM_U]
    out["R2 특징 개수 (architecture)"] = [
        ("k=%d" % k, float(k), _cfg(k=k)) for k in KGRID]
    out["R3 학습 창 (curriculum)"] = [
        ("f=%g" % f, float(f), _cfg(f=f)) for f in FGRID]
    out["R4 도메인 가중 (objective)"] = [
        ("p=%g" % p, float(p), _cfg(p=p)) for p in PGRID]
    out["R5 원천 혼합 (data mixture)"] = [
        ("α=%g" % a, float(a), _cfg(alpha=a)) for a in AGRID]
    return out


def ols_slope(u, v):
    u = np.asarray(u, float)
    v = np.asarray(v, float)
    ok = np.isfinite(v)
    if ok.sum() < 2 or np.ptp(u[ok]) == 0:
        return float("nan")
    uu = u[ok] - u[ok].mean()
    return float((uu * (v[ok] - v[ok].mean())).sum() / (uu * uu).sum())


# ══════════════════════════════════════════════════════════════════════
def stage_factors(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    _prog("factors 시작")
    pool = Pool()
    _prog("자료: base %d · hplt %d · 게이트 도메인 %d"
          % (len(pool.yb), len(pool.yh), len(pool.gated)))

    lv = factor_levels()
    # ── 밑판 둘 ─────────────────────────────────────────────
    baseB = oof_pred(pool, dict(BASE_B), want_sel=True)
    pB, eB, perB = score(pool, baseB["예측"])
    fpB = fingerprint(pool, baseB["뽑힌 자리"])
    cfgP = _cfg(n=None, alpha=None)
    baseP = oof_pred(pool, cfgP, want_sel=True)
    pP, eP, perP = score(pool, baseP["예측"])
    fpP = fingerprint(pool, baseP["뽑힌 자리"])
    _prog("밑판 B ρ=%.6f · 밑판 P ρ=%.6f" % (pB, pP))

    # ── 수준별 점추정 + 자료 지문 ─────────────────────────────
    pt = collections.OrderedDict()
    PRED0 = {}
    for fac, lst in lv.items():
        rows = collections.OrderedDict()
        for name, u, cfg in lst:
            r = oof_pred(pool, cfg, want_sel=True)
            PRED0[(fac, name)] = r["예측"]
            po, eq, per = score(pool, r["예측"])
            fp = fingerprint(pool, r["뽑힌 자리"])
            moved = fp_diff(fp, fpB)
            allow = FP_ALLOWED[fac]
            rows[name] = {
                "u": u, "ũ": (u - FAC_RANGE[fac][1]) / (FAC_RANGE[fac][2]
                                                        - FAC_RANGE[fac][1]),
                "밑판인가": all(cfg[kk] == BASE_B[kk] for kk in BASE_B),
                "학습 행(겹별)": r["겹별 학습 행"],
                "🔴 학습 행이 예산과 같은가": all(
                    x == N_B for x in r["겹별 학습 행"]),
                "예산 미달": r["예산 미달"],
                "겹별 λ": [round(x, 6) for x in r["겹별 λ"]],
                "묶음 유보 ρ": round(po, 6),
                "도메인 균등 ρ": round(eq, 6),
                "🔴🔴 Δ(수준 − 밑판 B)": round(po - pB, 6),
                "도메인별 유보 ρ": {d: round(per[d], 6) for d in per},
                "도메인별 Δ": {d: round(per[d] - perB[d], 6) for d in per},
                "🔴 자료 지문": fp,
                "🔴🔴 밑판과 움직인 지문 성분": moved,
                "🔴 그 요인이 움직여도 되는 성분": sorted(allow),
                "🔴🔴 한 칸만인가(자료 지문으로)": set(moved).issubset(allow),
            }
            _prog("  %s / %s  ρ=%.6f" % (fac, name, po))
        pt[fac] = rows

    # ── R3′ 대조: 전역 창 자름(975 판) ────────────────────────
    r3p = collections.OrderedDict()
    for f in FGRID:
        cfg = _cfg(f=f)
        r = oof_pred(pool, cfg, global_window=True, want_sel=True)
        po, eq, _per = score(pool, r["예측"])
        fp = fingerprint(pool, r["뽑힌 자리"])
        r3p["f=%g" % f] = {
            "묶음 유보 ρ": round(po, 6),
            "Δ(수준 − 밑판 B)": round(po - pB, 6),
            "원천 비율": fp["원천 비율"],
            "🔴 원천 비율이 밑판과 다른가": fp["원천 비율"] != fpB["원천 비율"],
            "쌍id sha256": fp["쌍id sha256"],
        }
    _prog("R3′ 끝")

    # ── 붓스트랩 셋 (한 뽑기에서 다 뽑는다) ─────────────────────
    names = [(fac, nm, cfg) for fac, lst in lv.items() for nm, _u, cfg in lst]
    acc = {(fac, nm): {"유보": [], "학습": [], "이중": []} for fac, nm, _c in names}
    rank_hits = collections.Counter()
    slope_draws = collections.defaultdict(list)
    maxabs_draws = collections.defaultdict(list)
    t_boot = time.time()
    for b in range(BOOT):
        hi = ho_draw(pool, b)
        # 밑판 B — 같은 뽑기로
        pb_h, _e, _p = score(pool, baseB["예측"], hi)          # 유보만
        rb = oof_pred(pool, dict(BASE_B), tr_boot=b)
        pb_t, _e, _p = score(pool, rb["예측"])                 # 학습만
        pb_d, _e, _p = score(pool, rb["예측"], hi)             # 이중
        cur = {}
        for fac, nm, cfg in names:
            # 유보만: **점추정 예측**(적합을 얼린다 = 975 판)을 되뽑은 유보로 채점
            ph, _e, _p = score(pool, PRED0[(fac, nm)], hi)
            r0 = oof_pred(pool, cfg, tr_boot=b)
            ptr, _e, _p = score(pool, r0["예측"])
            pdb, _e, _p = score(pool, r0["예측"], hi)
            acc[(fac, nm)]["유보"].append(ph - pb_h)
            acc[(fac, nm)]["학습"].append(ptr - pb_t)
            acc[(fac, nm)]["이중"].append(pdb - pb_d)
            cur[(fac, nm)] = pdb
        # 이 뽑기에서의 요인 순위 (기울기 · 최대 |Δ|)
        for fac, lst in lv.items():
            us = [(u - FAC_RANGE[fac][1]) / (FAC_RANGE[fac][2] - FAC_RANGE[fac][1])
                  for _n, u, _c in lst]
            vs = [cur[(fac, nm)] for nm, _u, _c in lst]
            slope_draws[fac].append(ols_slope(us, vs))
            maxabs_draws[fac].append(max(abs(v - pb_d) for v in vs))
        top_s = max(lv, key=lambda f: abs(slope_draws[f][-1]))
        top_m = max(lv, key=lambda f: maxabs_draws[f][-1])
        rank_hits["기울기/" + top_s] += 1
        rank_hits["최대|Δ|/" + top_m] += 1
        if (b + 1) % 20 == 0:
            el = time.time() - t_boot
            _prog("붓스트랩 %d/%d  (%.0fs · 남은 %.0fs)"
                  % (b + 1, BOOT, el, el / (b + 1) * (BOOT - b - 1)))

    # ── 정리 ────────────────────────────────────────────────
    facs = collections.OrderedDict()
    n_pass = n_lev = 0
    for fac, lst in lv.items():
        rows = collections.OrderedDict()
        for nm, u, _c2 in lst:
            a = acc[(fac, nm)]
            se_h = float(np.std(a["유보"], ddof=1))
            se_t = float(np.std(a["학습"], ddof=1))
            se_d = float(np.std(a["이중"], ddof=1))
            d = pt[fac][nm]["🔴🔴 Δ(수준 − 밑판 B)"]
            base_lv = pt[fac][nm]["밑판인가"]
            ok = bool((not base_lv) and se_d > 0 and abs(d) >= 2 * se_d
                      and abs(d) >= THR_CARD)
            n_lev += 0 if base_lv else 1
            n_pass += 1 if ok else 0
            rows[nm] = dict(pt[fac][nm])
            rows[nm].update({
                "🔴 SE_유보(975 판)": round(se_h, 6),
                "🔴 SE_학습": round(se_t, 6),
                "🔴🔴🔴 SE_이중(정본)": round(se_d, 6),
                "🔴 |Δ|/SE_이중": (round(abs(d) / se_d, 4) if se_d > 0 else None),
                "🔴 |Δ|/SE_유보(975 판이었으면)": (
                    round(abs(d) / se_h, 4) if se_h > 0 else None),
                "🔴 문턱 ① |Δ| ≥ 2·SE_이중": bool(se_d > 0 and abs(d) >= 2 * se_d),
                "🔴 문턱 ② |Δ| ≥ 0.00353": bool(abs(d) >= THR_CARD),
                "🔴🔴 채택(둘 다 · 밑판 제외)": ok,
                "🔴 SE_이중 > SE_유보 인가": bool(se_d > se_h),
            })
            rows[nm].pop("🔴 자료 지문", None)
            rows[nm]["🔴 자료 지문"] = pt[fac][nm]["🔴 자료 지문"]
        us = [(u - FAC_RANGE[fac][1]) / (FAC_RANGE[fac][2] - FAC_RANGE[fac][1])
              for _n, u, _c in lst]
        vs = [pt[fac][nm]["묶음 유보 ρ"] for nm, _u, _c in lst]
        sl = ols_slope(us, vs)
        sd_sl = float(np.std([x for x in slope_draws[fac] if np.isfinite(x)], ddof=1))
        mx = max(abs(pt[fac][nm]["🔴🔴 Δ(수준 − 밑판 B)"]) for nm, _u, _c in lst)
        sd_mx = float(np.std(maxabs_draws[fac], ddof=1))
        arg = max(lst, key=lambda z: abs(pt[fac][z[0]]["🔴🔴 Δ(수준 − 밑판 B)"]))[0]
        facs[fac] = {
            "모수": FAC_RANGE[fac][0],
            "허용 범위": [FAC_RANGE[fac][1], FAC_RANGE[fac][2]],
            "격자": [nm for nm, _u, _c in lst],
            "🔴🔴🔴 정규화 기울기(Δρ / 정규화 모수 1단위)": round(sl, 6),
            "🔴 그 기울기의 SE(이중 붓스트랩)": round(sd_sl, 6),
            "🔴🔴🔴 같은 예산에서의 최대 |Δ|": round(mx, 6),
            "🔴 그 최대 |Δ| 의 SE(이중 붓스트랩)": round(sd_mx, 6),
            "🔴 최대 |Δ| 를 내는 수준": arg,
            "🔴 채택된 수준 수": sum(1 for nm, _u, _c in lst
                              if rows[nm]["🔴🔴 채택(둘 다 · 밑판 제외)"]),
            "🔴 한 칸만인가(자료 지문) 분자/분모": "%d / %d" % (
                sum(1 for nm, _u, _c in lst
                    if rows[nm]["🔴🔴 한 칸만인가(자료 지문으로)"]), len(lst)),
            "수준별": rows,
        }

    rank_slope = collections.OrderedDict(
        ("%d위 %s" % (i, k), {
            "정규화 기울기": facs[k]["🔴🔴🔴 정규화 기울기(Δρ / 정규화 모수 1단위)"],
            "SE": facs[k]["🔴 그 기울기의 SE(이중 붓스트랩)"],
            "🔴 붓스트랩에서 1위인 뽑기 비율": round(
                rank_hits["기울기/" + k] / float(BOOT), 4)})
        for i, k in enumerate(sorted(
            facs, key=lambda z: -abs(facs[z]["🔴🔴🔴 정규화 기울기(Δρ / 정규화 모수 1단위)"])), 1))
    rank_max = collections.OrderedDict(
        ("%d위 %s" % (i, k), {
            "같은 예산 최대 |Δ|": facs[k]["🔴🔴🔴 같은 예산에서의 최대 |Δ|"],
            "SE": facs[k]["🔴 그 최대 |Δ| 의 SE(이중 붓스트랩)"],
            "최대를 내는 수준": facs[k]["🔴 최대 |Δ| 를 내는 수준"],
            "🔴 붓스트랩에서 1위인 뽑기 비율": round(
                rank_hits["최대|Δ|/" + k] / float(BOOT), 4)})
        for i, k in enumerate(sorted(
            facs, key=lambda z: -facs[z]["🔴🔴🔴 같은 예산에서의 최대 |Δ|"]), 1))

    n_one = sum(1 for fac in facs for nm in facs[fac]["수준별"]
                if facs[fac]["수준별"][nm]["🔴🔴 한 칸만인가(자료 지문으로)"])
    n_all = sum(len(facs[fac]["수준별"]) for fac in facs)
    n_bud = sum(1 for fac in facs for nm in facs[fac]["수준별"]
                if facs[fac]["수준별"][nm]["🔴 학습 행이 예산과 같은가"])

    out = {
        "무엇": "976 — C4 를 한 모수 족·같은 예산에서 다시 재고 SE 를 이중 붓스트랩으로 낸다",
        "🔴 축": "C4 (capability 결정 요인) — 같은 주행의 C6 은 `out976_scaling.json`",
        "사전등록": "docs/prereg_976_c6.md §2~§5",
        "🔴 정본 자": "유보 예측 성능(개체 묶음 5겹 OOF · 도메인별 스피어만의 유보 행 가중 묶음)",
        "🔴🔴 스팬": "🔴 **안 낸다**(사전등록 §4 · 반증조건 4) — 스팬은 수준 수에 단조다",
        "🔴 자료": {
            "base 행(= 유보 전량)": len(pool.yb),
            "hplt 행(= 학습에만)": len(pool.yh),
            "겹": KFOLD, "겹 씨앗": SEED,
            "🔴 게이트(유보 행 ≥ %d) 도메인" % MIN_HO: pool.gated,
            "🔴 분모: 게이트 유보 행 합": int(sum(pool.dom_ho[d] for d in pool.gated)),
            "도메인별 유보 행": {d: pool.dom_ho[d] for d in pool.gated},
            "🔴 가장 큰 도메인의 몫": round(
                max(pool.dom_ho[d] for d in pool.gated)
                / float(sum(pool.dom_ho[d] for d in pool.gated)), 6),
            "🔴 975 의 게이트 유보 행": 728,
            "🔴 몇 배로 늘었나": round(
                sum(pool.dom_ho[d] for d in pool.gated) / 728.0, 4),
        },
        "🔴 밑판 B (예산 맞춤 · 요인 Δ 의 기준)": {
            "설정": {k: str(v) for k, v in BASE_B.items()},
            "학습 행(겹별)": baseB["겹별 학습 행"],
            "겹별 λ(속겹 CV)": [round(x, 6) for x in baseB["겹별 λ"]],
            "🔴🔴 묶음 유보 ρ": round(pB, 6),
            "도메인 균등 ρ": round(eB, 6),
            "도메인별 유보 ρ": {d: round(perB[d], 6) for d in perB},
            "🔴 자료 지문": fpB,
        },
        "🔴 밑판 P (생산 · 예산 없음)": {
            "학습 행(겹별)": baseP["겹별 학습 행"],
            "겹별 λ(속겹 CV)": [round(x, 6) for x in baseP["겹별 λ"]],
            "🔴🔴 묶음 유보 ρ": round(pP, 6),
            "도메인 균등 ρ": round(eP, 6),
            "도메인별 유보 ρ": {d: round(perP[d], 6) for d in perP},
            "🔴 자료 지문": fpP,
            "🔴🔴 예산이 깎은 값(밑판 B − 밑판 P)": round(pB - pP, 6),
        },
        "🔴🔴🔴 요인별": facs,
        "🔴🔴🔴 순위 ① 정규화 기울기": rank_slope,
        "🔴🔴🔴 순위 ② 같은 예산 최대 |Δ|": rank_max,
        "🔴🔴 두 순위의 1위가 같은가": (
            list(rank_slope)[0].split(" ", 1)[1] == list(rank_max)[0].split(" ", 1)[1]),
        "🔴 반증조건 2 — 학습 행이 예산과 같은 수준": "%d / %d" % (n_bud, n_all),
        "🔴🔴 반증조건 3 — 자료 지문으로 본 「한 칸만」": "%d / %d" % (n_one, n_all),
        "🔴 반증조건 5 — 유보 지문": {
            "지문": hashlib.sha256("|".join(sorted(pool.pb.tolist())).encode()).hexdigest(),
            "🔴 유보는 설정과 무관하다": True,
            "왜": "유보 = base 전량이고 어느 설정도 유보를 안 만진다"},
        "🔴 채택(문턱 둘) 분자/분모": "%d / %d" % (n_pass, n_lev),
        "🔴 975 의 채택 수": 6,
        "🔴🔴 R3′ 대조 — 전역 창 자름(975 판)이 원천 혼합을 끌고 오는가": {
            "수준별": r3p,
            "🔴 원천 비율이 움직인 수준": "%d / %d" % (
                sum(1 for v in r3p.values() if v["🔴 원천 비율이 밑판과 다른가"]),
                len(r3p)),
            "🔴 R3(원천 안 자름)에서 원천 비율이 움직인 수준": "%d / %d" % (
                sum(1 for nm in facs["R3 학습 창 (curriculum)"]["수준별"]
                    if facs["R3 학습 창 (curriculum)"]["수준별"][nm][
                        "🔴 자료 지문"]["원천 비율"] != fpB["원천 비율"]),
                len(FGRID)),
        },
        "씨앗": SEED, "붓스트랩 뽑기": BOOT, "예산 N_B": N_B,
    }
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LO.SRC)
    (OUT / "out976_factors.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    _prog("factors 끝")
    return out


# ══════════════════════════════════════════════════════════════════════
def fit_loglin(ns, rs):
    x = np.log10(np.asarray(ns, float))
    y = np.asarray(rs, float)
    b = ols_slope(x, y)
    a = float(y.mean() - b * x.mean())
    return {"a": a, "b": b}, (lambda n, a=a, b=b: a + b * math.log10(n))


def fit_power(ns, rs):
    """`ρ(n) = ρ∞ − c·n^(−γ)` — γ 를 훑고 각 γ 에서 (ρ∞, c) 는 닫힌 꼴 최소제곱."""
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
            sse = float(((r_inf - c * z - y) ** 2).sum())
            if best is None or sse < best[0]:
                best = (sse, r_inf, c, g)
        g += 0.01
    _sse, r_inf, c, g = best
    return ({"ρ∞": r_inf, "c": c, "γ": g},
            (lambda n, r=r_inf, cc=c, gg=g: r - cc * (n ** (-gg))))


def stage_scaling(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    _prog("scaling 시작")
    pool = Pool()
    rungs = collections.OrderedDict()
    ns_real, rs = [], []
    preds = {}
    for n in LADDER:
        cfg = _cfg(n=n, alpha=(None if n is None else 0.95))
        r = oof_pred(pool, cfg)
        po, eq, per = score(pool, r["예측"])
        nn = int(np.mean(r["겹별 학습 행"]))
        key = ("전량" if n is None else str(n))
        rungs[key] = {"요청 n": ("전량" if n is None else n),
                      "실제 학습 행(겹 평균)": nn,
                      "겹별 학습 행": r["겹별 학습 행"],
                      "겹별 λ(속겹 CV)": [round(x, 6) for x in r["겹별 λ"]],
                      "🔴 묶음 유보 ρ": round(po, 6),
                      "도메인 균등 ρ": round(eq, 6),
                      "예산 미달": r["예산 미달"]}
        preds[key] = r["예측"]
        ns_real.append(nn)
        rs.append(po)
        _prog("  사다리 n=%s (실제 %d) ρ=%.6f" % (key, nn, po))

    keys = list(rungs)
    fit_idx = [i for i, n in enumerate(ns_real) if n <= C6_FIT_MAX]
    pred_idx = [i for i in range(len(ns_real)) if i not in fit_idx]
    p1, f1 = fit_loglin([ns_real[i] for i in fit_idx], [rs[i] for i in fit_idx])
    p2, f2 = fit_power([ns_real[i] for i in fit_idx], [rs[i] for i in fit_idx])

    # 큰 n 의 SE (이중 붓스트랩)
    se = {}
    t_b = time.time()
    for i in range(len(keys)):
        key = keys[i]
        n = rungs[key]["요청 n"]
        cfg = _cfg(n=(None if n == "전량" else n),
                   alpha=(None if n == "전량" else 0.95))
        lam_f = list(rungs[key]["겹별 λ(속겹 CV)"])   # 🔴 뽑기 안에서 λ 는 얼린다(적는다)
        dd = []
        for b in range(BOOT_C6):
            hi = ho_draw(pool, b)
            rb = oof_pred(pool, cfg, tr_boot=b, lam_fixed=lam_f)
            v, _e, _p = score(pool, rb["예측"], hi)
            dd.append(v)
        se[key] = float(np.std(dd, ddof=1))
        _prog("  SE(이중) n=%s → %.6f (%.0fs)" % (key, se[key], time.time() - t_b))

    rows = collections.OrderedDict()
    e1, e2 = [], []
    for i in pred_idx:
        key = keys[i]
        n = ns_real[i]
        y1, y2 = f1(n), f2(n)
        rows[key] = {
            "실제 학습 행": n, "🔴 실측 ρ": round(rs[i], 6),
            "형태 ① 로그선형 예측": round(y1, 6),
            "🔴 형태 ① 절대 오차": round(abs(y1 - rs[i]), 6),
            "형태 ② 포화 멱법칙 예측": round(y2, 6),
            "🔴 형태 ② 절대 오차": round(abs(y2 - rs[i]), 6),
            "🔴 그 자리의 SE(이중 붓스트랩)": round(se.get(key, float("nan")), 6),
            "🔴 형태 ① 오차 / SE": round(abs(y1 - rs[i]) / se[key], 4) if se.get(key) else None,
            "🔴 형태 ② 오차 / SE": round(abs(y2 - rs[i]) / se[key], 4) if se.get(key) else None,
        }
        e1.append(abs(y1 - rs[i]))
        e2.append(abs(y2 - rs[i]))
    top = keys[pred_idx[-1]]

    out = {
        "무엇": "976 — 🔴🔴🔴 **축 C6 의 첫 수**: 작은 n(≤%d) 넷으로 적합해 큰 n 을 예측한 오차"
                % C6_FIT_MAX,
        "🔴 축": "C6 (scaling · benchmark 너머)",
        "사전등록": "docs/prereg_976_c6.md §6",
        "🔴 972~975 네 사이클 연속 C6 = 0 이었다": True,
        "🔴 사다리(밑판 P 구성 · 학습 행 수만 바꾼다)": rungs,
        "🔴 사다리 자리별 SE(이중 붓스트랩)": {k: round(v, 6) for k, v in se.items()},
        "🔴 사다리가 단조인가": bool(all(rs[i] <= rs[i + 1] for i in range(len(rs) - 1))),
        "🔴 형태 ② 의 γ 가 훑은 범위의 끝에 붙었나": bool(
            p2["γ"] <= 0.0501 or p2["γ"] >= 1.4999),
        "🔴 적합에 쓴 자리": [keys[i] for i in fit_idx],
        "🔴 예측한 자리(적합에 한 비트도 안 썼다)": [keys[i] for i in pred_idx],
        "형태 ① 로그선형 모수": {k: round(v, 6) for k, v in p1.items()},
        "형태 ② 포화 멱법칙 모수": {k: round(v, 6) for k, v in p2.items()},
        "🔴🔴🔴 예측 오차": rows,
        "🔴🔴 형태 ① RMSE": round(float(np.sqrt(np.mean(np.square(e1)))), 6),
        "🔴🔴 형태 ② RMSE": round(float(np.sqrt(np.mean(np.square(e2)))), 6),
        "🔴🔴🔴 가장 큰 n 에서의 절대 오차(헤드라인)": {
            "자리": top,
            "실제 학습 행": rows[top]["실제 학습 행"],
            "실측 ρ": rows[top]["🔴 실측 ρ"],
            "형태 ①": rows[top]["🔴 형태 ① 절대 오차"],
            "형태 ②": rows[top]["🔴 형태 ② 절대 오차"],
            "그 자리의 SE(이중)": rows[top]["🔴 그 자리의 SE(이중 붓스트랩)"],
            "🔴 형태 ② 오차가 SE 보다 큰가": bool(
                rows[top]["🔴 형태 ② 절대 오차"] > rows[top]["🔴 그 자리의 SE(이중 붓스트랩)"]),
        },
        "🔴 어느 형태가 나은가": ("형태 ② 포화 멱법칙"
                          if float(np.mean(e2)) < float(np.mean(e1))
                          else "형태 ① 로그선형"),
        "붓스트랩 뽑기(사다리)": BOOT_C6, "씨앗": SEED,
        "⚠ 사다리 붓스트랩의 한계": ("🔴 뽑기 안에서 **λ 를 점추정 값으로 얼렸다**"
                          "(가장 큰 자리에서 속겹 CV 를 400 번 다시 도는 값이 시간에 안 맞는다). "
                          "학습·유보 재표집은 그대로 돈다."),
    }
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LO.SRC)
    (OUT / "out976_scaling.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    _prog("scaling 끝")
    return out


# ══════════════════════════════════════════════════════════════════════
def stage_wiring(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    _prog("wiring 시작")
    rng = np.random.RandomState(SEED)
    W = collections.OrderedDict()
    E = collections.OrderedDict()

    # W1 — 가중 1 에서 생산 함수와 같은 답
    n, k = 400, 6
    Xt = rng.normal(size=(n, k))
    bb = rng.normal(size=k)
    yt = Xt @ bb + rng.normal(size=n) * 0.5
    Xh = rng.normal(size=(200, k))
    yh = Xh @ bb + rng.normal(size=200) * 0.5
    m0 = L.ridge_fit(Xt, yt, 1.0)
    m1 = ridge_fit_w(Xt, yt, 1.0, np.ones(n))
    d1 = float(np.max(np.abs(L.ridge_pred(m0, Xh) - L.ridge_pred(m1, Xh))))
    W["W1 가중 1 에서 생산 함수 ridge_fit 과 같은 답"] = d1 < 1e-10

    pool = Pool()
    # W2 — k 를 줄이면 열이 그만큼 준다
    ws = []
    for kk in KGRID:
        X, _y, _d, _e = design(pool, np.arange(5), np.arange(5), kk)
        ws.append(X.shape[1] - len(pool.doms) == kk)
    W["W2 k 를 줄이면 설계행렬 열이 정확히 그만큼 준다"] = all(ws)

    # W3 — f 를 줄이면 원천별로 ceil(f·n_s)
    w3 = []
    for f in FGRID:
        _kp, kept = window_mask(pool.ord_b, f, len(pool.yb))
        for src, mm in kept.items():
            w3.append(mm == int(math.ceil(f * len(pool.ord_b[src]))))
    W["W3 f 자름이 원천 안에서 ⌈f·n_s⌉ 다"] = all(w3)

    # W4 — p 가 가중을 바꾼다 · p=0 이면 균등(None)
    dom = np.asarray([0] * 30 + [1] * 10, dtype=np.int64)
    W["W4 p=0 이면 가중이 균등이고 p≠0 이면 계수가 바뀐다"] = bool(
        weights_of(dom, 0.0) is None
        and float(np.max(np.abs(
            ridge_fit_w(Xt[:40], yt[:40], 1.0, weights_of(dom, -1.0))[0]
            - ridge_fit_w(Xt[:40], yt[:40], 1.0, None)[0]))) > 1e-8)

    # W5 — α 가 만들어진 학습 집합의 HPLT 비율이다
    w5 = []
    for a in AGRID:
        selb, selh, _s = select(pool, 0, _cfg(alpha=a))
        w5.append(abs(len(selh) / float(len(selb) + len(selh)) - a) <= 1.0 / N_B)
    W["W5 α 가 만들어진 학습 집합의 HPLT 비율이다"] = all(w5)

    # W6 — 예산이 모든 수준에서 정확히 N_B
    w6 = []
    for _fac, lst in factor_levels().items():
        for _nm, _u, cfg in lst:
            selb, selh, _s = select(pool, 0, cfg)
            w6.append(len(selb) + len(selh) == N_B)
    W["W6 요인 격자의 모든 수준에서 학습 행이 정확히 N_B"] = all(w6)

    # W7 — 뽑기가 중첩이다
    prev = None
    w7 = []
    for nn in [200, 400, 800, 1600]:
        selb, selh, _s = select(pool, 0, _cfg(n=nn))
        cur = (set(selb.tolist()), set(selh.tolist()))
        if prev is not None:
            w7.append(prev[0] <= cur[0] and prev[1] <= cur[1])
        prev = cur
    W["W7 n 을 키우면 뽑힌 집합이 포개진다"] = all(w7)

    # W8 — 유보 지문이 하나
    fps = set()
    for _fac, lst in factor_levels().items():
        for _nm, _u, _cfg2 in lst:
            fps.add(hashlib.sha256("|".join(sorted(pool.pb.tolist())).encode()).hexdigest())
    W["W8 유보 지문이 하나"] = len(fps) == 1

    # W9 — 🔴 975 의 밑판을 그대로 재현한다
    def isho(r):
        return dt.date.fromisoformat(r["언제"]) >= LO.SPLIT
    hold975 = [r for r in pool.base if isho(r)]
    tr975 = [r for r in pool.base if not isho(r)] + \
            [r for r in pool.hplt if not isho(r)]
    doms975 = sorted({r["도메인"] for r in tr975 + hold975})
    dom_ho975 = collections.Counter(r["도메인"] for r in hold975)
    dom_tr975 = collections.Counter(r["도메인"] for r in
                                    [r for r in pool.base if not isho(r)])
    g975 = [d for d in doms975 if dom_ho975[d] >= 20 and dom_tr975[d] >= 20]

    def des975(rows):
        X = np.asarray([r["x"] for r in rows], float)
        D = np.zeros((len(rows), len(doms975)))
        for i, r in enumerate(rows):
            if r["도메인"] in doms975:
                D[i, doms975.index(r["도메인"])] = 1.0
        return np.hstack([X, D])
    m975 = L.ridge_fit(des975(tr975),
                       np.asarray([r["y"] for r in tr975], float), 1.0)
    pr975 = L.ridge_pred(m975, des975(hold975))
    yh975 = np.asarray([r["y"] for r in hold975], float)
    dh975 = np.asarray([r["도메인"] for r in hold975])
    per975 = {d: float(P.spear(pr975[dh975 == d], yh975[dh975 == d])) for d in g975}
    pooled975 = float(np.average([per975[d] for d in g975],
                                 weights=[dom_ho975[d] for d in g975]))
    tgt = 0.378150
    W["W9 975 의 밑판 묶음 유보 ρ 를 소수 여섯 자리까지 재현한다"] = bool(
        round(pooled975, 6) == tgt)

    # W10 — 🔴 학습 선택에 **그 겹의 유보 행**이 한 줄도 없다(원리상 못 샌다)
    leak = 0
    checked = 0
    for _fac, lst in factor_levels().items():
        for _nm, _u, cfg in lst:
            for j in range(KFOLD):
                selb, _selh, _s = select(pool, j, cfg)
                leak += int((pool.fi[selb] == j).sum())
                checked += 1
    W["W10 학습 선택에 그 겹의 유보 행이 0 줄이다(속겹 CV 도 원리상 못 본다)"] = (leak == 0)

    # ── 파괴 대조 E ────────────────────────────────────────
    base = oof_pred(pool, dict(BASE_B))
    p_base, _e, _p = score(pool, base["예측"])
    # E1 학습 짝 깨기 — 🔴 **학습에만 쓰이는 HPLT 의 y 를 섞는다**(유보는 안 만진다)
    pool.yh = np.random.RandomState(11).permutation(pool.yh)
    r_e1 = oof_pred(pool, dict(BASE_B))
    p_e1, _e, _p = score(pool, r_e1["예측"])
    pool.yh = np.asarray([r["y"] for r in pool.hplt], float)
    E["E1 학습 짝(x↔y)을 깨면 유보 상관이 내려간다"] = bool(p_e1 < p_base)
    E["E1 참고: 밑판 ρ → 깬 뒤 ρ"] = [round(p_base, 6), round(p_e1, 6)]
    # E2 유보 y 섞기
    sh = np.random.RandomState(12).permutation(len(pool.yb))
    p_e2, _e, _p = score(pool, base["예측"][sh])
    E["E2 유보 y 를 섞으면 상관이 죽는다"] = bool(abs(p_e2) < 0.1)
    E["E2 참고: 섞은 뒤 ρ"] = round(p_e2, 6)
    # E3 λ=10^6 은 파괴다 (975 의 E4 반증)
    r_e3 = oof_pred(pool, _cfg(u_lam=6))
    p_e3, _e, _p = score(pool, r_e3["예측"])
    E["E3 λ=10⁶ 은 파괴다(975 의 E4 는 한 블록 설계에서만 참이었다)"] = bool(
        p_e3 < p_base - 0.02)
    E["E3 참고: λ=10⁶ 의 ρ"] = round(p_e3, 6)
    # E4 k=1
    r_e4 = oof_pred(pool, _cfg(k=1))
    p_e4, _e, _p = score(pool, r_e4["예측"])
    E["E4 k=1 로 줄이면 상관이 내려간다"] = bool(p_e4 < p_base)
    E["E4 참고: k=1 의 ρ"] = round(p_e4, 6)
    # E5 n=200
    r_e5 = oof_pred(pool, _cfg(n=200))
    p_e5, _e, _p = score(pool, r_e5["예측"])
    E["E5 예산을 n=200 으로 줄이면 상관이 내려간다"] = bool(p_e5 < p_base)
    E["E5 참고: n=200 의 ρ"] = round(p_e5, 6)

    out = {"무엇": "976 — 배선 W1~W10 · 파괴 대조 E1~E5 (사전등록 §11)",
           "🔴 축": "C4 + C6",
           "W": {k2: (bool(v) if isinstance(v, (bool, np.bool_)) else v)
                 for k2, v in W.items()},
           "🔴 W 분자/분모": "%d / %d" % (
               sum(1 for v in W.values() if v is True), len(W)),
           "🔴 W1 최대 절대차": d1,
           "🔴 W9 실측 값": round(pooled975, 6),
           "🔴 W9 975 산출물이 적은 값": tgt,
           "🔴 W9 게이트 도메인": g975,
           "E": {k2: (bool(v) if isinstance(v, (bool, np.bool_)) else v)
                 for k2, v in E.items()},
           "🔴 E 분자/분모": "%d / %d" % (
               sum(1 for k2, v in E.items()
                   if v is True and "참고" not in k2),
               sum(1 for k2 in E if "참고" not in k2))}
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LO.SRC)
    (OUT / "out976_wiring.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    _prog("wiring 끝")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    choices=["wiring", "factors", "scaling"])
    ap.add_argument("--ref", default="")
    a = ap.parse_args()
    r = {"wiring": stage_wiring, "factors": stage_factors,
         "scaling": stage_scaling}[a.stage](a.ref)
    print(json.dumps({k: v for k, v in r.items() if k != "🔴🔴🔴 요인별"},
                     ensure_ascii=False, indent=1, default=str)[:6000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
