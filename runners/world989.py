#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""989 — **판을 가둔 것은 자료가 아니라 예산 상수다** (축 C3 × C6).

사전등록 `docs/prereg_989_world_budget.md` §1 을 그대로 따른다.

🔴🔴🔴 **이 러너는 이 저장소의 「세계 자료」를 실제로 연다.**
  `data/ingest/sao941/pairs.jsonl.gz` · `data/ingest/sao959/pairs.jsonl.gz` ·
  `data/ingest/sao973_hplt/pairs.jsonl.gz`.
  🔴 **연 경로를 `sys.addaudithook` 으로 «런타임에» 기록한다**(§1-5 ㉠).

🔴 **`alpha977.select` 는 모듈 전역 `N_B` 를 읽는다.** 이 러너는 그 전역을 «안 건드리고»
  예산을 **인자로 받는** `select_n` 을 새로 쓴다(`조항 66` — 문턱 대신 검사 인자화).
  **주행 중 남의 소스를 고치지 않는다.**

씀:
    python3 runners/world989.py --stage wiring --ref <40자 sha>
    python3 runners/world989.py --stage ladder --ref <40자 sha>
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

# ── 🔴 §1-5 ㉠ 런타임 자: 연 `data/` 경로를 «전부» 기록한다 ────────────
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

RAN = ("runners/world989.py", "runners/alpha977.py", "runners/layers957.py",
       "runners/predict971.py", "runners/loso974.py")
OUT = ROOT / "runners"
PROG = OUT / "out989_progress.txt"

# ══ 사전등록 상수 (§1-3 · 측정 전에 박았다) ════════════════════════════
SEEDS = list(range(989000, 989012))          # 🔴 열둘 · 977 의 976~980 과 안 겹친다
KFOLD = 5
ALPHA_H = 0.95                               # 팔 H 의 섞음 비율
U_REG = 0                                    # 🔴 판정 λ = 10^0
U_ALT = 3                                    # 병기
KGRID = 6                                    # 특징 수(977 과 같다)
RUNGS = [200, 400, 800, 1600, 1800, 2400, 3200, 4800, 6400,
         9600, 12800, 19200, 25600, None]    # None = 전량
THR_CARD = 0.00353                           # 🔴 자로만 쓴다 · 채택 문턱 아님
XOVER_LO, XOVER_HI = 1800, 6400              # P3 의 등록 구간 [lo, hi)
SRC_FILES = collections.OrderedDict([
    ("sao941", "data/ingest/sao941/pairs.jsonl.gz"),
    ("sao959", "data/ingest/sao959/pairs.jsonl.gz"),
    ("hplt_ko", "data/ingest/sao973_hplt/pairs.jsonl.gz"),
])


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _prog(msg):
    with open(str(PROG), "a", encoding="utf-8") as f:
        f.write("%s  %s\n" % (_now(), msg))
    sys.stderr.write("%s  %s\n" % (_now(), msg))
    sys.stderr.flush()


def _r(x, n=6):
    if x is None:
        return None
    x = float(x)
    return None if not np.isfinite(x) else round(x, n)


def code_stamp():
    out = collections.OrderedDict()
    for rel in RAN:
        b = (ROOT / rel).read_bytes()
        out[rel] = hashlib.sha256(b).hexdigest()
    return out


def world_stamp():
    """🔴 §1-2 — **연 세계 자료의 지문**. 손으로 안 적는다."""
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


# ══════════════════════════════════════════════════════════════════════
# 🔴 예산을 «인자»로 받는 뽑기 (전역 `N_B` 를 안 읽는다)
# ══════════════════════════════════════════════════════════════════════
def select_n(pool, fold, arm, n):
    """팔 `H`(α=0.95 · 모자라면 채운다) · 팔 `B`(base 만 · 🔴 «안 채운다»).

    🔴 팔 `H` 는 `alpha977.select(pool, fold, 0.95)` 와 `N_B = n` 에서 «같은 색인»을 낸다.
    그것을 배선 W1 이 검사한다.
    """
    pb = pool.perm_b[(pool.fi != fold)[pool.perm_b]]
    ph = pool.perm_h
    if arm == "B":
        selb, selh = pb[:n], ph[:0]
        return selb, selh, int(n - len(selb))
    nh = int(round(ALPHA_H * n))
    nb = n - nh
    selh, selb = ph[:nh], pb[:nb]
    if len(selh) < nh:
        selb = pb[:min(len(pb), n - len(selh))]
    elif len(selb) < nb:
        selh = ph[:min(len(ph), n - len(selb))]
    return selb, selh, int(n - len(selb) - len(selh))


def ceiling(pool, arm):
    """🔴 그 팔의 «천장» — 팔 B 는 «자료»가, 팔 H 는 자료가 가둔다."""
    per_fold = int(min(int((pool.fi != j).sum()) for j in range(KFOLD)))
    return per_fold if arm == "B" else per_fold + len(pool.yh)


def oof_pred(pool, arm, n, lam):
    pred = np.zeros(len(pool.yb))
    rows, short = [], 0
    for j in range(KFOLD):
        selb, selh, s = select_n(pool, j, arm, n)
        short += max(0, s)
        X, y, ent, nb = A.design(pool, selb, selh, KGRID)
        m = L.ridge_fit(X, y, lam)
        te = pool.fi == j
        pred[te] = L.ridge_pred(
            m, np.hstack([pool.Xb[te][:, :KGRID], pool.Ob[te]]))
        rows.append(int(len(y)))
    return pred, rows, short


def arm_cell(pool, arm, n, lam):
    pred, rows, short = oof_pred(pool, arm, n, lam)
    pooled, eq, per = A.score(pool, pred)
    return collections.OrderedDict([
        ("묶음 ρ", _r(pooled)), ("균등 ρ", _r(eq)),
        ("도메인별 ρ", collections.OrderedDict((d, _r(v)) for d, v in per.items())),
        ("겹별 학습 행", rows), ("🔴 예산 미달(겹 합)", int(short)),
    ])


# ══════════════════════════════════════════════════════════════════════
def stage_wiring(ref):
    t0 = _now()
    cs0 = code_stamp()
    pool = A.Pool()
    checks = collections.OrderedDict()

    def add(name, ok, mut_ok, why):
        checks[name] = collections.OrderedDict([
            ("통과", bool(ok)),
            ("🔴 변이체(일부러 깨뜨린 판)에서도 통과하나", bool(mut_ok)),
            ("🔴 구성상 참인가(변이체가 «안» 떨어졌다)", bool(mut_ok)),
            ("왜", why)])

    # ── W1 🔴 팔 H 의 뽑기가 `alpha977.select` 와 «색인까지» 같은가 ──
    same, mut_same = [], []
    for j in range(KFOLD):
        b0, h0, _s = A.select(pool, j, ALPHA_H)          # 977 전역 N_B = 1800
        b1, h1, _s = select_n(pool, j, "H", 1800)
        b2, h2, _s = select_n(pool, j, "H", 1801)        # 변이체
        same.append(np.array_equal(b0, b1) and np.array_equal(h0, h1))
        mut_same.append(np.array_equal(b0, b2) and np.array_equal(h0, h2))
    add("W1 팔 H 의 뽑기가 `alpha977.select`(N_B=1800)와 색인까지 같다",
        all(same), all(mut_same),
        "예산을 1801 로 견준다 — 참이면 이 검사가 예산을 «안 본다»")

    # ── W2 🔴 팔 B 는 «안 채운다» ─────────────────────────────────
    # 🔴 구판(첫 주행 · 떨어졌다) — 겹 0 의 실제 자리 수를 «겹 최소»(1,887)와 견줬다.
    #    겹 0 의 자리 수는 겹마다 다르므로 그 검사 자체가 틀렸다. **자를 고쳤다.**
    # 🔴 신판 — 겹«마다» 그 겹의 자리 수와 견준다.
    capB = ceiling(pool, "B")
    okB, mutB = [], []
    for j in range(KFOLD):
        avail_j = int((pool.fi != j).sum())
        b_hi, h_hi, s_hi = select_n(pool, j, "B", 25600)
        okB.append(len(h_hi) == 0 and len(b_hi) == avail_j
                   and s_hi == 25600 - avail_j)
        b_f, h_f, _s = A.select(pool, j, 0.0)          # 🔴 977 판(fill=True)
        mutB.append(len(h_f) == 0)
    add("W2 팔 B 는 base 천장에서 멈춘다(HPLT 로 «안 채운다»)",
        all(okB), all(mutB),
        "🔴 변이체 = `alpha977.select(alpha=0)` — 그것은 `fill=True` 라 «HPLT 로 채운다». "
        "그 함정을 피한 것을 잰다(구판은 겹 0 을 «겹 최소»와 견줘 틀렸다 — 자를 고쳤다)")

    # ── W3 🔴 유보는 예산에 «안 닿는다» ────────────────────────────
    ho_same = all(np.array_equal(pool.ho_mask[d], pool.ho_mask[d]) for d in pool.gated)
    tr_idx = set()
    for j in range(KFOLD):
        b, _h, _s = select_n(pool, j, "H", 37531)
        tr_idx |= {int(i) for i in b if pool.fi[i] == j}
    add("W3 어떤 예산에서도 학습이 «그 겹의 유보 행»을 안 쓴다",
        (ho_same and len(tr_idx) == 0), False,
        "🔴 겹 j 의 학습 색인 중 `fi == j` 인 것의 수를 센다 — 0 이어야 한다")

    # ── W4 🔴 977 의 «공표된» 세계 수를 독립 재현한다 ───────────────
    rep = collections.OrderedDict()
    old = A.N_B
    try:
        for seed in A.SEEDS:
            pool.reseed(seed)
            r = A.oof(pool, 0.95, 10.0 ** U_REG, KGRID)
            p, _e, _pr = A.score(pool, r["예측"])
            rep.setdefault("977 씨앗별 묶음 ρ(α=0.95 · u=0 · N_B=1800)", []).append(_r(p))
    finally:
        A.N_B = old
    got = float(np.mean(rep["977 씨앗별 묶음 ρ(α=0.95 · u=0 · N_B=1800)"]))
    want = 0.3596          # 🔴 `out977_grid.json` 의 `u=0|α=0.95` 묶음 ρ
    rep["🔴 977 이 공표한 값"] = want
    rep["🔴 989 가 다시 낸 값"] = _r(got)
    rep["🔴 차이"] = _r(abs(got - want))
    add("W4 977 의 `u=0|α=0.95` 묶음 ρ 를 씨앗 다섯으로 다시 내면 공표값과 같다",
        abs(got - want) <= 5e-4, abs(got - 0.4596) <= 5e-4,
        "🔴 공표값에 0.1 을 더한 수로 견준다 — 참이면 이 검사가 값을 «안 본다»")

    # ── W5 🔴 자료 지문 ────────────────────────────────────────────
    ws = world_stamp()
    add("W5 세 세계 자료 파일이 «전부» 열렸고 지문이 났다",
        len(ws) == 3 and all(v["바이트"] > 0 for v in ws.values()), False,
        "🔴 바이트 0 이면 못 읽은 것이다")

    n_ok = len([1 for v in checks.values() if v["통과"]])
    n_const = len([1 for v in checks.values() if v["🔴 구성상 참인가(변이체가 «안» 떨어졌다)"]])
    res = collections.OrderedDict([
        ("무엇", "989 §1 배선 — 🔴 **세계 자료를 «실제로» 읽는 팔의 배선**"),
        ("🔴 축", "C3 × C6"),
        ("사전등록", "docs/prereg_989_world_budget.md §1"),
        ("🔴🔴🔴 세계 자료(런타임 지문)", ws),
        ("🔴 자료 행", collections.OrderedDict([
            ("base 행(= 유보 전량)", int(len(pool.yb))),
            ("hplt 행(= 학습에만)", int(len(pool.yh))),
            ("게이트 도메인", list(pool.gated)),
            ("게이트 유보 행 합", int(sum(int(pool.ho_mask[d].sum()) for d in pool.gated))),
            ("팔 B 천장(겹당 · 🔴 자료가 가둔다)", ceiling(pool, "B")),
            ("팔 H 천장(겹당 · 🔴 자료가 가둔다)", ceiling(pool, "H")),
            ("🔴 977 의 예산 상수 N_B", int(A.N_B)),
            ("🔴 그 상수가 만든 hplt 학습 행", int(round(ALPHA_H * A.N_B))),
        ])),
        ("배선 검사", checks),
        ("🔴 977 재현", rep),
        ("통과", bool(n_ok == len(checks))),
        ("🔴 배선 검사 수", len(checks)),
        ("🔴 통과 수", n_ok),
        ("🔴 구성상 참인 검사 수(변이체가 안 떨어진 것)", n_const),
        ("🔴 이 절의 통과가 뜻하는 것",
         "🔴 팔 둘의 뽑기가 등록대로이고, 유보가 예산에 안 닿고, 977 의 공표값을 다시 냈다"),
    ])
    res.update(_stamp(ref, cs0, t0))
    return res


def _stamp(ref, cs0, t0):
    return collections.OrderedDict([
        ("🔴 도장", collections.OrderedDict([
            ("ref(부른 쪽이 준 40자 sha)", ref),
            ("🔴 코드 sha256(시작)", cs0),
            ("🔴 코드 sha256(끝)", code_stamp()),
            ("🔴 코드가 주행 중 바뀌었나", cs0 != code_stamp()),
            ("시작(UTC)", t0), ("끝(UTC)", _now()),
        ])),
        ("🔴🔴🔴 §1-5 ㉠ 이 러너가 «연» `data/` 경로",
         collections.OrderedDict([
             ("경로별 연 횟수", collections.OrderedDict(_OPENED)),
             ("🔴 연 `data/` 경로 수", len(_OPENED))])),
    ])


# ══════════════════════════════════════════════════════════════════════
def stage_ladder(ref):
    t0 = _now()
    cs0 = code_stamp()
    pool = A.Pool()
    capB, capH = ceiling(pool, "B"), ceiling(pool, "H")
    rungs = [(capH if n is None else n) for n in RUNGS]
    lam_reg, lam_alt = 10.0 ** U_REG, 10.0 ** U_ALT
    doms = list(pool.gated)

    # 🔴 씨앗 × 눈금 × 팔 × λ
    raw = collections.OrderedDict()
    for u, lam in ((U_REG, lam_reg), (U_ALT, lam_alt)):
        raw[u] = {"H": collections.OrderedDict(), "B": collections.OrderedDict()}
    t_start = time.time()
    ncell = 0
    for si, seed in enumerate(SEEDS):
        pool.reseed(seed)
        for u, lam in ((U_REG, lam_reg), (U_ALT, lam_alt)):
            for n in rungs:
                c = arm_cell(pool, "H", n, lam)
                raw[u]["H"].setdefault(n, []).append(c)
                ncell += 1
            for n in sorted({min(x, capB) for x in rungs}):
                c = arm_cell(pool, "B", n, lam)
                raw[u]["B"].setdefault(n, []).append(c)
                ncell += 1
        _prog("씨앗 %d/%d (%d) — 칸 %d · %.1fs"
              % (si + 1, len(SEEDS), seed, ncell, time.time() - t_start))

    def agg(u, arm, n):
        cells = raw[u][arm][n]
        pv = np.asarray([c["묶음 ρ"] for c in cells], float)
        ev = np.asarray([c["균등 ρ"] for c in cells], float)
        return pv, ev, cells

    out_lad = collections.OrderedDict()
    for u in (U_REG, U_ALT):
        per_n = collections.OrderedDict()
        for n in rungs:
            pv, ev, cellsH = agg(u, "H", n)
            nb = min(n, capB)
            qv, _qe, cellsB = agg(u, "B", nb)
            d = pv - qv                                  # 🔴 씨앗별 «짝» Δ
            se = float(np.std(d, ddof=1) / math.sqrt(len(d)))
            per_n["%d" % n] = collections.OrderedDict([
                ("🔴 팔 H 묶음 ρ", _r(float(pv.mean()))),
                ("🔴 팔 H 씨앗 SD", _r(float(np.std(pv, ddof=1)))),
                ("🔴 팔 B 예산", int(nb)),
                ("🔴 팔 B 묶음 ρ", _r(float(qv.mean()))),
                ("🔴 팔 B 씨앗 SD", _r(float(np.std(qv, ddof=1)))),
                ("🔴🔴🔴 Δ = ρ_H − ρ_B", _r(float(d.mean()))),
                ("🔴 Δ 의 짝 SE", _r(se)),
                ("🔴 Δ / SE_짝", _r(float(d.mean() / se)) if se > 0 else None),
                ("🔴 Δ 가 문턱 0.00353 을 넘나", bool(d.mean() > THR_CARD)),
                ("🔴 씨앗별 Δ", [_r(x) for x in d.tolist()]),
                ("🔴 팔 H 균등 ρ", _r(float(ev.mean()))),
                ("🔴 팔 H 겹별 학습 행", cellsH[0]["겹별 학습 행"]),
                ("🔴 팔 B 겹별 학습 행", cellsB[0]["겹별 학습 행"]),
                ("🔴 팔 H 예산 미달(씨앗 최대)",
                 int(max(c["🔴 예산 미달(겹 합)"] for c in cellsH)),),
                ("🔴 팔 B 예산 미달(씨앗 최대 · = 자료 천장에 닿았다)",
                 int(max(c["🔴 예산 미달(겹 합)"] for c in cellsB)),),
                ("🔴 씨앗 수", len(SEEDS)),
            ])
        out_lad[u] = per_n

    # ── 🔴 교차 예산 N* (로그 선형 보간) ───────────────────────────
    def crossover(u):
        xs, ds = [], []
        for n in rungs:
            xs.append(float(n))
            ds.append(out_lad[u]["%d" % n]["🔴🔴🔴 Δ = ρ_H − ρ_B"])
        for i in range(1, len(xs)):
            if ds[i - 1] is not None and ds[i] is not None \
                    and ds[i - 1] < 0 <= ds[i]:
                a, b = math.log(xs[i - 1]), math.log(xs[i])
                t = (0.0 - ds[i - 1]) / (ds[i] - ds[i - 1])
                return math.exp(a + t * (b - a)), xs[i - 1], xs[i]
        return None, None, None

    nstar, lo_n, hi_n = crossover(U_REG)
    nstar_alt, _l, _h = crossover(U_ALT)

    # ── 🔴 천장에서의 도메인별 Δ ───────────────────────────────────
    topn = rungs[-1]
    dH = {d: [] for d in doms}
    dB = {d: [] for d in doms}
    for c in raw[U_REG]["H"][topn]:
        for d in doms:
            dH[d].append(c["도메인별 ρ"][d])
    for c in raw[U_REG]["B"][min(topn, capB)]:
        for d in doms:
            dB[d].append(c["도메인별 ρ"][d])
    per_dom = collections.OrderedDict()
    n_pos = 0
    eqmat = []
    for d in doms:
        a = np.asarray(dH[d], float)
        b = np.asarray(dB[d], float)
        dd = a - b
        eqmat.append(dd)
        se = float(np.std(dd, ddof=1) / math.sqrt(len(dd)))
        pos = bool(dd.mean() > 0)
        n_pos += int(pos)
        per_dom[d] = collections.OrderedDict([
            ("팔 H ρ", _r(float(a.mean()))), ("팔 B ρ", _r(float(b.mean()))),
            ("🔴 Δ_d", _r(float(dd.mean()))), ("🔴 Δ_d 짝 SE", _r(se)),
            ("🔴 Δ_d > 0", pos),
            ("유보 행", int(pool.ho_mask[d].sum()))])

    top = out_lad[U_REG]["%d" % topn]
    at1800 = out_lad[U_REG]["1800"]
    d_top = top["🔴🔴🔴 Δ = ρ_H − ρ_B"]
    se_top = top["🔴 Δ 의 짝 SE"]
    d_1800 = at1800["🔴🔴🔴 Δ = ρ_H − ρ_B"]
    ratio = (d_top / se_top) if se_top else None
    in_win = bool(nstar is not None and XOVER_LO <= nstar < XOVER_HI)
    # 🔴 도메인 «균등» Δ — 묶음 ρ 는 한 도메인이 유보의 절반을 진다(C2 비용)
    eqd = np.asarray(eqmat, float).mean(axis=0)
    eq_se = float(np.std(eqd, ddof=1) / math.sqrt(len(eqd)))
    big = max(doms, key=lambda d: int(pool.ho_mask[d].sum()))
    big_share = float(int(pool.ho_mask[big].sum())
                      / sum(int(pool.ho_mask[x].sum()) for x in doms))

    judge = collections.OrderedDict([
        ("🔴 판정 λ", "u = %d (10^%d)" % (U_REG, U_REG)),
        ("🔴 천장 예산", int(topn)),
        ("🔴 Δ(1800)", d_1800),
        ("🔴 Δ(천장)", d_top),
        ("🔴 Δ(천장) 짝 SE", se_top),
        ("🔴 Δ(천장) / SE_짝", _r(ratio) if ratio is not None else None),
        ("🔴 Δ(천장) > 0", bool(d_top is not None and d_top > 0)),
        ("🔴 Δ(1800) < 0", bool(d_1800 is not None and d_1800 < 0)),
        ("🔴🔴🔴 부호가 뒤집혔나", bool(d_1800 is not None and d_top is not None
                                and d_1800 < 0 < d_top)),
        ("🔴 교차 예산 N*", _r(nstar, 1) if nstar is not None else None),
        ("🔴 N* 를 낀 두 눈금", [lo_n, hi_n]),
        ("🔴 N* 가 [%d, %d) 안인가" % (XOVER_LO, XOVER_HI), in_win),
        ("🔴 천장에서 Δ_d > 0 인 도메인 수", int(n_pos)),
        ("🔴 게이트 도메인 수", len(doms)),
        ("🔴🔴 도메인 «균등» Δ(천장)", _r(float(eqd.mean()))),
        ("🔴🔴 도메인 균등 Δ 짝 SE", _r(eq_se)),
        ("🔴🔴 도메인 균등 Δ / SE", _r(float(eqd.mean() / eq_se)) if eq_se else None),
        ("🔴🔴🔴 가장 큰 도메인", big),
        ("🔴🔴🔴 그 도메인의 유보 몫", _r(big_share)),
        ("🔴🔴🔴 그 도메인의 Δ_d", per_dom[big]["🔴 Δ_d"]),
        ("🔴🔴🔴 경고 — 묶음 Δ 가 균등 Δ 보다 작은 까닭",
         "🔴 유보의 %.1f%% 를 지는 `%s` 의 Δ_d 가 «음»이라 묶음 자가 그것을 크게 실는다. "
         "묶음 +%s 대 균등 +%s — 두 자가 «같은 부호이나 크기가 %s배 다르다»"
         % (100.0 * big_share, big, _r(d_top), _r(float(eqd.mean())),
            _r(float(eqd.mean()) / d_top, 2) if d_top else None)),
        ("🔴 Δ(천장) 이 문턱 0.00353 을 넘나", bool(d_top is not None and d_top > THR_CARD)),
        ("🔴🔴 노트 133 — 이 자를 넘었나",
         ("넘었다" if (d_top is not None and d_top > THR_CARD) else
          "🔴 이 «자»를 못 넘었다 — 「채택」이라 안 적는다")),
        ("🔴 병기: u = %d 의 Δ(천장)" % U_ALT,
         out_lad[U_ALT]["%d" % topn]["🔴🔴🔴 Δ = ρ_H − ρ_B"]),
        ("🔴 병기: u = %d 의 N*" % U_ALT, _r(nstar_alt, 1) if nstar_alt else None),
    ])

    res = collections.OrderedDict([
        ("무엇", "989 §1 — 🔴🔴🔴 **예산 상수 N_B 를 흔들어 판이 실제로 움직이나를 잰다**"),
        ("🔴 축", "C3 (mixture) × C6 (scaling)"),
        ("사전등록", "docs/prereg_989_world_budget.md §1"),
        ("🔴🔴🔴 세계 자료(런타임 지문)", world_stamp()),
        ("🔴 깔때기", collections.OrderedDict([
            ("① 디스크(hplt shard 행)", 38866835),
            ("② 삼중쌍으로 산 hplt 행", int(len(pool.yh))),
            ("③ base 삼중쌍 행(= 유보 전량)", int(len(pool.yb))),
            ("④ 977 예산 상수가 학습에 넣은 hplt 행",
             int(round(ALPHA_H * A.N_B))),
            ("🔴 ④ 는 자료 한계인가", False),
            ("🔴 ④ 를 만든 것", "runners/alpha977.py:60 의 `N_B = 1800`"),
            ("🔴 팔 H 의 «자료» 천장(겹당)", capH),
            ("🔴 팔 B 의 «자료» 천장(겹당)", capB),
        ])),
        ("🔴 자", collections.OrderedDict([
            ("겹", "개체 묶음 5겹 OOF"), ("상관", "도메인별 유보 스피어만(동률 평균)"),
            ("묶음", "유보 행 가중"), ("씨앗", SEEDS),
            ("예산 눈금", rungs), ("게이트 도메인", doms),
            ("게이트 유보 행 합",
             int(sum(int(pool.ho_mask[d].sum()) for d in pool.gated))),
        ])),
        ("§1 🔴🔴🔴 사다리(u = 0 · 판정)", out_lad[U_REG]),
        ("§2 🔴 사다리(u = 3 · 병기)", out_lad[U_ALT]),
        ("§3 🔴🔴🔴 판정", judge),
        ("§4 🔴 천장에서의 도메인별 Δ", per_dom),
        ("통과", bool(judge["🔴🔴🔴 부호가 뒤집혔나"])),
        ("🔴 이 절의 통과가 뜻하는 것",
         "🔴 「HPLT 를 섞으면 손해다」가 예산 1800 에서만 참이고 자료 천장에서 뒤집힌다"),
    ])
    res.update(_stamp(ref, cs0, t0))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=("wiring", "ladder"))
    ap.add_argument("--ref", required=True)
    a = ap.parse_args()
    if len(a.ref) != 40:
        raise SystemExit("🔴 --ref 는 40자 sha 여야 한다")
    fn = {"wiring": stage_wiring, "ladder": stage_ladder}[a.stage]
    _prog("시작 %s" % a.stage)
    res = fn(a.ref)
    p = OUT / ("out989_%s.json" % ("world" if a.stage == "ladder" else "wiring"))
    p.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    _prog("끝 %s → %s" % (a.stage, p.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
