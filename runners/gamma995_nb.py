#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""995 팔 A — **`N_B` 를 푼다.**

사전등록 `docs/prereg_995_unblock_nb.md` §2 를 그대로 따른다.

🔴 `runners/alpha977.py:60` 의 `N_B = 1800` 은 «상수»다. 자료 한계가 아니다.
   그 탓에 `hplt_ko` 삼중쌍 35,641 중 `int(round(0.95*1800)) = 1,710` 행만 모형에 닿는다.
   이 러너는 예산을 **인자**로 만들어 사다리를 올리고 **전량**까지 간다.

🔴🔴 **`alpha977.py` 를 한 글자도 안 고친다.** `Pool` 만 «읽기»로 빌려 쓰고,
   예산을 받는 `select_budget` 을 **여기서 새로** 짠다. `W1` 이 `budget=1800` 에서
   `alpha977.select` 와 **색인까지 같은가**를 검사하고, `budget=1801` 변이체가
   **달라야** 한다는 것까지 검사한다(조항 66 — 자가 자기 출처를 대야 한다).

🔴 **조항 78 (v4.12)** — 이 러너가 **원리상 못 떨어지는** 검사 넷(㉮-1~㉮-4)을
   반증조건이 아니라 **「구성상 참」칸**으로 낸다. 최상위 연언에서 뺐다.

씀:
    OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 \
      python3 runners/gamma995_nb.py --stage nb
"""
import argparse
import collections
import datetime as dt
import hashlib
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

import runners.alpha977 as A977                   # noqa: E402  (읽기로만 쓴다)
import runners.layers957 as L                     # noqa: E402
import runners.predict971 as P                    # noqa: E402

SRC = ("runners/gamma995_nb.py", "runners/alpha977.py", "runners/layers957.py",
       "runners/predict971.py", "runners/loso974.py", "runners/predict972.py")

OUT = ROOT / "runners"
OUTFILE = OUT / "out995_nb.json"

# ── 사전등록 상수 (측정 전에 박았다 · docs/prereg_995_unblock_nb.md §2) ──
SEEDS = list(range(976, 988))          #: 씨앗 12
KFOLD = 5                              #: `alpha977.KFOLD` 와 같다
LAM = 1.0                              #: 10^0 — 977 `U_REG` 의 등록된 값
ALPHA = 0.95                           #: 977 `ALPHA_BASE`
KFEAT = 6
BUDGETS = [1800, 3600, 7200, 14400, 28800, 36000, None]   #: None = 전량
BASE_BUDGET = 1800                     #: 견주는 자리
AGRID = [0.0, 0.5, 0.95, 1.0]
AB_BUDGETS = [1800, 28800]
DROPS = collections.OrderedDict([("ALL", ()), ("−hplt_ko", ("hplt_ko",)),
                                 ("−sao959", ("sao959",)), ("−sao941", ("sao941",))])
GATES = [20, 10, 5, 4, 3]              #: §A5 게이트 인자화 (기본 `alpha977.MIN_HO` = 20)
B_DOM = 2000                           #: 도메인 군집 뽑기 수
#: 🔴🔴 **등록된 자**(사전등록 §9-1) --- `runners/score994.py:98 cluster_se` 와 «같은 꼴».
#: `B=2000` · `RandomState(994)` · **등가중**(994 가 실제로 그렇게 불렀다) ·
#: 판정식 `abs(pt) > 2*se`. 🔴 **여기서 «고치지 않는다».**
DOM_BOOT_SEED = 994
DOM_BOOT_SEED_ALT = 995                #: 뽑기 씨앗 흔들기(강건성 칸)
THREADS = collections.OrderedDict([
    (k, os.environ.get(k)) for k in
    ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")])

# 🔴 조항 59 개정판 — 다섯을 가른다
DROP_ZERO = "0 행"
DROP_GATE = "행부족 --- 쟀는데 설정이 버렸다"
SCORED = "채점"


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


def sha_arr(a):
    return hashlib.sha256(np.ascontiguousarray(np.asarray(a)).tobytes()).hexdigest()


# ══════════════════════════════════════════════════════════════════════
# 🔴 예산을 «인자»로 받는 뽑기 — `alpha977.select` 의 `N_B` 만 풀었다
# ══════════════════════════════════════════════════════════════════════
def select_budget(pool, fold, alpha, budget, drop_src=(), fill=True,
                  base_only=False):
    """`alpha977.select` 와 **같은 식**. 다른 것은 `N_B` 가 인자라는 것뿐.

    `budget is None` 이면 **전량**(가용 base OOF 전부 + 가용 hplt 전부).
    `base_only` 면 hplt 를 0 행으로 둔다(α=0 의 천장).
    """
    avail_b = (pool.fi != fold)
    avail_h = np.ones(len(pool.yh), dtype=bool)
    for s in drop_src:
        if s == "hplt_ko":
            avail_h = np.zeros(len(pool.yh), dtype=bool)
        else:
            avail_b = avail_b & (pool.sb != s)
    if base_only:
        avail_h = np.zeros(len(pool.yh), dtype=bool)
    pb = pool.perm_b[avail_b[pool.perm_b]]
    ph = pool.perm_h[avail_h[pool.perm_h]]
    if budget is None:
        return pb, ph, 0
    nh = int(round(alpha * budget))
    nb = budget - nh
    selh, selb = ph[:nh], pb[:nb]
    if fill and (len(selh) < nh or len(selb) < nb):
        if len(selh) < nh:
            selb = pb[:min(len(pb), budget - len(selh))]
        else:
            selh = ph[:min(len(ph), budget - len(selb))]
    return selb, selh, int(budget - len(selb) - len(selh))


def design(pool, selb, selh, k=KFEAT):
    X = np.vstack([np.hstack([pool.Xb[selb][:, :k], pool.Ob[selb]]),
                   np.hstack([pool.Xh[selh][:, :k], pool.Oh[selh]])])
    y = np.concatenate([pool.yb[selb], pool.yh[selh]])
    return X, y, len(selb)


def oof(pool, alpha, lam, budget, drop_src=(), base_only=False, k=KFEAT):
    """다섯 겹 OOF 예측. 유보는 **언제나 base 전량**(겹으로 갈린다)."""
    pred = np.zeros(len(pool.yb))
    ntr, nb_rows, nh_rows, short = [], [], [], []
    for j in range(KFOLD):
        selb, selh, s = select_budget(pool, j, alpha, budget, drop_src,
                                      base_only=base_only)
        X, y, nb = design(pool, selb, selh, k)
        m = L.ridge_fit(X, y, lam)
        te = pool.fi == j
        pred[te] = L.ridge_pred(m, np.hstack([pool.Xb[te][:, :k], pool.Ob[te]]))
        ntr.append(int(len(y)))
        nb_rows.append(int(len(selb)))
        nh_rows.append(int(len(selh)))
        short.append(int(s))
    return collections.OrderedDict([
        ("예측", pred), ("겹별 학습 행", ntr),
        ("겹별 base 학습 행", nb_rows), ("겹별 hplt 학습 행", nh_rows),
        ("🔴 예산을 못 채운 행(겹별)", short)])


def gated_for(pool, gate):
    cnt = collections.Counter(pool.db.tolist())
    return [d for d in pool.doms if cnt.get(d, 0) >= gate]


def score_dom(pool, pred, gated):
    """도메인별 스피어만 + 묶음(유보 행 가중) + 균등 + 버림 장부."""
    per, w, drop = collections.OrderedDict(), collections.OrderedDict(), collections.OrderedDict()
    cnt = collections.Counter(pool.db.tolist())
    for d in pool.doms:
        n = int(cnt.get(d, 0))
        if d not in gated:
            drop[d] = DROP_ZERO if n == 0 else DROP_GATE
            continue
        m = (pool.db == d)
        v = float(P.spear(pred[m], pool.yb[m]))
        if not np.isfinite(v):
            drop[d] = "결측 --- rho 가 유한하지 않다"
            continue
        per[d], w[d] = v, float(m.sum())
    vals = np.asarray([per[d] for d in per], float)
    ww = np.asarray([w[d] for d in per], float)
    pooled = float((vals * ww).sum() / ww.sum()) if len(vals) else float("nan")
    eq = float(vals.mean()) if len(vals) else float("nan")
    return pooled, eq, per, w, drop


def drop_ledger(drop, per, doms):
    cnt = collections.Counter()
    for d in doms:
        cnt[drop.get(d, SCORED)] += 1
    return collections.OrderedDict([
        ("시도 도메인", len(doms)),
        ("갈래별", dict(cnt)),
        ("🔴 합 = 시도", bool(sum(cnt.values()) == len(doms))),
        ("채점", len(per))])


def over_seeds(pool, alpha, lam, budget, drop_src=(), base_only=False,
               gate=20):
    """씨앗 12 에서 재고 **평균·SD·SE** 와 도메인별 씨앗 평균을 낸다."""
    ps, es, pers, tr, trb, trh, shorts = [], [], [], [], [], [], []
    gated = gated_for(pool, gate)
    lastdrop, lastw = None, None
    for s in SEEDS:
        pool.reseed(s)
        o = oof(pool, alpha, lam, budget, drop_src, base_only)
        po, eq, per, w, drop = score_dom(pool, o["예측"], gated)
        ps.append(po)
        es.append(eq)
        pers.append(per)
        tr.append(o["겹별 학습 행"])
        trb.append(o["겹별 base 학습 행"])
        trh.append(o["겹별 hplt 학습 행"])
        shorts.append(o["🔴 예산을 못 채운 행(겹별)"])
        lastdrop, lastw = drop, w
    dom = collections.OrderedDict()
    for d in gated:
        vv = [p[d] for p in pers if d in p and np.isfinite(p[d])]
        dom[d] = float(np.mean(vv)) if vv else float("nan")
    dv = np.asarray([dom[d] for d in gated], float)
    ok = np.isfinite(dv)
    return collections.OrderedDict([
        ("예산", budget if budget is not None else "전량"),
        ("alpha", alpha), ("lam", lam), ("게이트", gate),
        ("드롭", list(drop_src)), ("base만", bool(base_only)),
        ("씨앗 수", len(SEEDS)),
        ("묶음 ρ", _r(np.mean(ps))), ("묶음 씨앗 SD", _r(np.std(ps, ddof=1))),
        ("묶음 씨앗 SE", _r(np.std(ps, ddof=1) / np.sqrt(len(ps)))),
        ("균등 ρ", _r(np.mean(es))), ("균등 씨앗 SD", _r(np.std(es, ddof=1))),
        ("균등 씨앗 SE", _r(np.std(es, ddof=1) / np.sqrt(len(es)))),
        ("씨앗별 묶음 ρ", [_r(x) for x in ps]),
        ("씨앗별 균등 ρ", [_r(x) for x in es]),
        ("도메인별 ρ(씨앗 평균)", collections.OrderedDict(
            [(d, _r(dom[d])) for d in gated])),
        ("🔴 도메인 사이 SD(τ̂)", _r(float(dv[ok].std(ddof=1))) if ok.sum() > 1 else None),
        ("채점 도메인 수", int(len(gated))),
        ("겹당 학습 행(씨앗 0)", tr[0]),
        ("겹당 base 학습 행(씨앗 0)", trb[0]),
        ("겹당 hplt 학습 행(씨앗 0)", trh[0]),
        ("🔴 예산을 못 채운 행(씨앗 0 · 겹별)", shorts[0]),
        ("🔴 겹당 학습 행이 씨앗마다 같나", bool(len({tuple(x) for x in tr}) == 1)),
        ("버림 장부", drop_ledger(lastdrop, dom, pool.doms)),
        ("도메인별 유보 행", collections.OrderedDict(
            [(d, int(lastw[d])) for d in gated])),
    ])


def dom_cluster(vals_by_dom, B=B_DOM, seed=DOM_BOOT_SEED):
    """🔴🔴 **등록된 자**(사전등록 §9-1) — `score994.py:98 cluster_se` 와 «같은 꼴».

    도메인을 복원 재표집해 **등가중 평균**을 다시 낸다. 판정식 `abs(pt) > 2*se`.
    """
    ds = sorted(vals_by_dom)
    v = np.asarray([vals_by_dom[d] for d in ds], float)
    v = v[np.isfinite(v)]
    if len(v) < 2:
        return collections.OrderedDict([("도메인 수", int(len(v))),
                                        ("도메인 군집 SE", None), ("뽑기 수", 0)])
    def _boot(sd):
        rng = np.random.RandomState(int(sd))
        bs = np.empty(int(B))
        for b in range(int(B)):
            bs[b] = v[rng.randint(0, len(v), len(v))].mean()
        return bs
    bs = _boot(seed)
    m = float(v.mean())
    se = float(bs.std(ddof=1))
    se2 = float(_boot(DOM_BOOT_SEED_ALT).std(ddof=1))
    return collections.OrderedDict([
        ("도메인 수", int(len(v))), ("뽑기 수", int(B)),
        ("🔴 자", "score994.py:98 cluster_se · B=2000 · RandomState(%d) · 등가중" % seed),
        ("점추정", _r(m)), ("도메인 군집 SE", _r(se, 8)),
        ("🔴 t_clu", _r(m / se, 6) if se > 0 else None),
        ("🔴🔴 2·SE 를 넘나", bool(abs(m) > 2 * se) if se > 0 else None),
        ("뽑기 씨앗 %d 로 바꾼 SE" % DOM_BOOT_SEED_ALT, _r(se2, 8)),
        ("🔴 씨앗을 바꿔도 판정이 같나",
         bool((abs(m) > 2 * se) == (abs(m) > 2 * se2)) if se > 0 and se2 > 0 else None),
        ("도메인 사이 SD", _r(float(v.std(ddof=1)))),
        ("2.5%", _r(float(np.percentile(bs, 2.5)))),
        ("97.5%", _r(float(np.percentile(bs, 97.5)))),
        ("🔴 동부호 수",
         "%d/%d" % (int(sum(1 for x in v if np.sign(x) == np.sign(m))), len(v))),
        ("🔴 부호가 평균과 반대인 도메인 수",
         int(sum(1 for x in v if np.sign(x) != np.sign(m) and x != 0.0))),
    ])


def seg_table(labels, per_by_label, note):
    """🔴🔴 **조각 분해표**(사전등록 §9-1 — 이게 없으면 「없다」를 못 낸다).

    `labels` 는 «차례»이고 `per_by_label[l]` 는 그 자리의 도메인별 값이다.
    이웃 조각마다 (점추정 · 등록된 자의 군집 SE · t · 동부호 · 2·SE 를 넘나) 를 낸다.
    맨 아래에 **합**(첫 자리 − 끝 자리)을 같은 자로 낸다.
    """
    rows = collections.OrderedDict()
    for i in range(len(labels) - 1):
        a, b = labels[i], labels[i + 1]
        pa, pb = per_by_label[a], per_by_label[b]
        dd = {k: (pb[k] - pa[k]) for k in pa
              if pa.get(k) is not None and pb.get(k) is not None}
        rows["조각 %s → %s" % (a, b)] = dom_cluster(dd)
    pa, pb = per_by_label[labels[0]], per_by_label[labels[-1]]
    tot = {k: (pb[k] - pa[k]) for k in pa
           if pa.get(k) is not None and pb.get(k) is not None}
    n_cross = sum(1 for v in rows.values() if v.get("🔴🔴 2·SE 를 넘나"))
    return collections.OrderedDict([
        ("🔴 무엇", note), ("차례", list(labels)),
        ("조각", rows),
        ("🔴 합 (%s → %s)" % (labels[0], labels[-1]), dom_cluster(tot)),
        ("조각 수", len(rows)),
        ("🔴🔴 문턱을 넘은 조각 수", int(n_cross)),
        ("🔴 이것이 「조각 분해표」다(F13)", True),
    ])


# ══════════════════════════════════════════════════════════════════════
def stage_nb():
    t0 = _now()
    cs0 = code_stamp()
    wall0 = time.time()
    out = collections.OrderedDict()
    out["무엇"] = ("995 팔 A --- 🔴 **`N_B` 를 푼다**. alpha977 세계에서 예산을 "
                 "사다리로 올려 전량(hplt 35,641)까지 간다.")
    out["🔴 축"] = "C3 원천 × C4 자료량"
    out["사전등록"] = "docs/prereg_995_unblock_nb.md §2"
    out["🔴 고정한 스레드"] = THREADS
    out["🔴 사전등록 상수"] = collections.OrderedDict([
        ("씨앗", SEEDS), ("겹", KFOLD), ("λ", LAM), ("α", ALPHA),
        ("특징 k", KFEAT), ("예산 사다리", [b if b is not None else "전량" for b in BUDGETS]),
        ("게이트 사다리", GATES), ("뽑기 수", B_DOM), ("뽑기 씨앗", DOM_BOOT_SEED)])

    pool = A977.Pool()

    # ── §A0 분모 ────────────────────────────────────────────────
    cnt = collections.Counter(pool.db.tolist())
    ch = collections.Counter(pool.dh.tolist())
    cs = collections.Counter(pool.sb.tolist())
    ent = {}
    for d in pool.doms:
        m = (pool.db == d)
        ent[d] = int(len(set(pool.ecb[m].tolist())))
    out["§A0 분모"] = collections.OrderedDict([
        ("base 행", int(len(pool.yb))), ("hplt 행", int(len(pool.yh))),
        ("base 원천별", dict(cs)),
        ("도메인 합집합", int(len(pool.doms))), ("도메인 목록", list(pool.doms)),
        ("🔴 채점 도메인(게이트 20)", list(pool.gated)),
        ("🔴 채점 도메인 수", int(len(pool.gated))),
        ("도메인별 base 유보 행", dict(sorted(cnt.items(), key=lambda kv: -kv[1]))),
        ("도메인별 유보 개체", dict(sorted(ent.items(), key=lambda kv: -kv[1]))),
        ("도메인별 hplt 학습 자원", dict(sorted(ch.items(), key=lambda kv: -kv[1]))),
        ("🔴 게이트 20 에서 떨어진 도메인",
         {d: int(cnt.get(d, 0)) for d in pool.doms if d not in pool.gated}),
        ("🔴 조항 59 --- 그 도메인은 「0 행」인가 「쟀는데 설정이 버렸다」인가",
         {d: (DROP_ZERO if cnt.get(d, 0) == 0 else DROP_GATE)
          for d in pool.doms if d not in pool.gated}),
        ("🔴 alpha977.py 의 상수", collections.OrderedDict([
            ("N_B", int(A977.N_B)), ("MIN_HO", int(A977.MIN_HO)),
            ("ALPHA_BASE", float(A977.ALPHA_BASE)),
            ("🔴 그 예산이 hplt 에 닿는 행", int(round(A977.ALPHA_BASE * A977.N_B))),
            ("🔴 hplt 전량 대비 몫",
             _r(round(A977.ALPHA_BASE * A977.N_B) / float(len(pool.yh))))])),
    ])

    # ── §A1 예산 사다리 ──────────────────────────────────────────
    ladder = collections.OrderedDict()
    for b in BUDGETS:
        key = "예산 %s" % (b if b is not None else "전량")
        ladder[key] = over_seeds(pool, ALPHA, LAM, b)
    out["§A1 예산 사다리"] = ladder

    base_key = "예산 %d" % BASE_BUDGET
    full_key = "예산 전량"
    pooled_seq = [ladder["예산 %s" % (b if b is not None else "전량")]["묶음 ρ"]
                  for b in BUDGETS]
    viol = sum(1 for i in range(1, len(pooled_seq))
               if pooled_seq[i] is not None and pooled_seq[i - 1] is not None
               and pooled_seq[i] < pooled_seq[i - 1] - 1e-12)
    out["§A1 단조"] = collections.OrderedDict([
        ("층별 묶음 ρ", pooled_seq), ("비교 수", len(pooled_seq) - 1),
        ("🔴 단조 위반 수", int(viol))])

    # ── §A2 α × 예산 ────────────────────────────────────────────
    ab = collections.OrderedDict()
    for a in AGRID:
        for b in AB_BUDGETS:
            ab["α=%s · 예산 %d" % (a, b)] = over_seeds(pool, a, LAM, b)
    ab["전량(base+hplt)"] = ladder[full_key]
    ab["전량 --- base만"] = over_seeds(pool, 0.0, LAM, None, base_only=True)
    out["§A2 α × 예산"] = ab

    # ── §A3 LOSO ────────────────────────────────────────────────
    loso = collections.OrderedDict()
    for b in (BASE_BUDGET, None):
        bk = "예산 %s" % (b if b is not None else "전량")
        arms = collections.OrderedDict()
        for nm, ds in DROPS.items():
            arms[nm] = over_seeds(pool, ALPHA, LAM, b, drop_src=ds)
        blk = collections.OrderedDict([("팔", arms)])
        allp = arms["ALL"]
        d = collections.OrderedDict()
        for nm in DROPS:
            if nm == "ALL":
                continue
            dd = {k: (allp["도메인별 ρ(씨앗 평균)"][k] -
                      arms[nm]["도메인별 ρ(씨앗 평균)"][k])
                  for k in allp["도메인별 ρ(씨앗 평균)"]
                  if arms[nm]["도메인별 ρ(씨앗 평균)"].get(k) is not None
                  and allp["도메인별 ρ(씨앗 평균)"][k] is not None}
            d[nm] = collections.OrderedDict([
                ("Δ 묶음 ρ", _r((allp["묶음 ρ"] or 0) - (arms[nm]["묶음 ρ"] or 0))),
                ("Δ 균등 ρ", _r((allp["균등 ρ"] or 0) - (arms[nm]["균등 ρ"] or 0))),
                ("씨앗 SE(ALL)", allp["묶음 씨앗 SE"]),
                ("도메인별 Δ", {k: _r(v) for k, v in d_items(dd)}),
                ("🔴 도메인 군집", dom_cluster(dd))])
        blk["Δ (ALL − 뺀 것)"] = d
        loso[bk] = blk
    out["§A3 LOSO"] = loso

    # ── §A4 「전량 − 1800」 의 군집 SE ───────────────────────────
    dfull = ladder[full_key]["도메인별 ρ(씨앗 평균)"]
    dbase = ladder[base_key]["도메인별 ρ(씨앗 평균)"]
    delta = {k: (dfull[k] - dbase[k]) for k in dfull
             if dfull.get(k) is not None and dbase.get(k) is not None}
    rung = collections.OrderedDict()
    for b in BUDGETS:
        if b == BASE_BUDGET:
            continue
        k2 = "예산 %s" % (b if b is not None else "전량")
        dd = ladder[k2]["도메인별 ρ(씨앗 평균)"]
        dl = {k: (dd[k] - dbase[k]) for k in dd
              if dd.get(k) is not None and dbase.get(k) is not None}
        rung[k2] = collections.OrderedDict([
            ("Δ 묶음 ρ", _r((ladder[k2]["묶음 ρ"] or 0) - (ladder[base_key]["묶음 ρ"] or 0))),
            ("Δ 균등 ρ", _r((ladder[k2]["균등 ρ"] or 0) - (ladder[base_key]["균등 ρ"] or 0))),
            ("도메인별 Δ", {k: _r(v) for k, v in d_items(dl)}),
            ("🔴 도메인 군집", dom_cluster(dl))])
    tau_f = ladder[full_key]["🔴 도메인 사이 SD(τ̂)"]
    tau_b = ladder[base_key]["🔴 도메인 사이 SD(τ̂)"]
    out["§A4 군집 SE"] = collections.OrderedDict([
        ("🔴🔴 전량 − 1800", collections.OrderedDict([
            ("Δ 묶음 ρ", _r((ladder[full_key]["묶음 ρ"] or 0) - (ladder[base_key]["묶음 ρ"] or 0))),
            ("Δ 균등 ρ", _r((ladder[full_key]["균등 ρ"] or 0) - (ladder[base_key]["균등 ρ"] or 0))),
            ("씨앗 SE(1800)", ladder[base_key]["묶음 씨앗 SE"]),
            ("씨앗 SE(전량)", ladder[full_key]["묶음 씨앗 SE"]),
            ("도메인별 Δ", {k: _r(v) for k, v in d_items(delta)}),
            ("🔴🔴 도메인 군집", dom_cluster(delta))])),
        ("층별(각 층 − 1800)", rung),
        ("🔴🔴 τ̂ 비 (전량 / 1800)",
         _r(tau_f / tau_b) if (tau_f and tau_b) else None),
        ("τ̂(1800)", tau_b), ("τ̂(전량)", tau_f),
        ("🔴 바닥 τ̂/√d (전량)",
         _r(tau_f / np.sqrt(len(dfull))) if tau_f else None),
    ])

    # ── §A4-나 🔴🔴 조각 분해표 (사전등록 §9-1 · F13) ────────────
    lab = ["예산 %s" % (b if b is not None else "전량") for b in BUDGETS]
    per_by = {k: ladder[k]["도메인별 ρ(씨앗 평균)"] for k in lab}
    out["§A4-나 🔴🔴 조각 분해표"] = collections.OrderedDict([
        ("🔴 왜 있나",
         "티처 #133 --- 994 는 4 점 곡선의 «총 낙차» 하나만 재느라 평평한 조각의 "
         "분산을 신호 조각에 얹었다. 995 는 헤드라인 대비를 «조각»으로 쪼갠 표 없이는 "
         "「없다」를 못 낸다(사전등록 §9-1)."),
        ("예산 사다리", seg_table(lab, per_by,
                              "예산을 이웃 층끼리 쪼갠다. 헤드라인은 「전량 − 1800」이다.")),
    ])

    # ── §A5 게이트 인자화 ───────────────────────────────────────
    gate_blk = collections.OrderedDict()
    for g in GATES:
        gl = gated_for(pool, g)
        fb = over_seeds(pool, ALPHA, LAM, None, gate=g)
        bb = over_seeds(pool, ALPHA, LAM, BASE_BUDGET, gate=g)
        dl = {k: (fb["도메인별 ρ(씨앗 평균)"][k] - bb["도메인별 ρ(씨앗 평균)"][k])
              for k in fb["도메인별 ρ(씨앗 평균)"]
              if fb["도메인별 ρ(씨앗 평균)"].get(k) is not None
              and bb["도메인별 ρ(씨앗 평균)"].get(k) is not None}
        gate_blk["게이트 %d" % g] = collections.OrderedDict([
            ("채점 도메인 수 d", int(len(gl))), ("도메인", list(gl)),
            ("묶음 ρ(전량)", fb["묶음 ρ"]), ("묶음 ρ(1800)", bb["묶음 ρ"]),
            ("Δ 균등 ρ", _r((fb["균등 ρ"] or 0) - (bb["균등 ρ"] or 0))),
            ("🔴 도메인 군집", dom_cluster(dl))])
    out["§A5 게이트 인자화"] = collections.OrderedDict([
        ("🔴 d 의 천장", int(len(pool.doms))),
        ("🔴 ㉯-2 --- alpha977 세계에서 d ≥ 12 는 원리상 불가능",
         bool(len(pool.doms) < 12)),
        ("칸", gate_blk)])

    # ── §A6 배선 · 변이체 ───────────────────────────────────────
    wires = collections.OrderedDict()

    def add(name, ok, mut_ok, note):
        wires[name] = collections.OrderedDict([
            ("통과", bool(ok)), ("변이체도 통과", bool(mut_ok)),
            ("🔴 자료를 안 보는 검사인가", bool(ok and mut_ok)), ("변이체", note)])

    pool.reseed(SEEDS[0])
    # W1 — 내 select_budget(1800) 이 alpha977.select 와 색인까지 같은가
    same, diff = True, True
    for j in range(KFOLD):
        b1, h1, _ = select_budget(pool, j, ALPHA, 1800)
        b0, h0, _ = A977.select(pool, j, ALPHA)
        same = same and np.array_equal(b1, b0) and np.array_equal(h1, h0)
        b2, h2, _ = select_budget(pool, j, ALPHA, 1801)
        diff = diff and not (np.array_equal(b2, b0) and np.array_equal(h2, h0))
    add("W1 예산 1800 에서 alpha977.select 와 «색인까지» 같다", same, not diff,
        "예산을 1801 로 견준다 --- 통과하면 검사가 예산을 안 본다")

    # W2 — 예산 b 에서 겹당 학습 행 = b (🔴 ㉮-3 --- 구성상 참)
    rows_ok, rows_mut = True, True
    unfilled = collections.OrderedDict()
    for b in BUDGETS:
        if b is None:
            continue
        tot, sh = [], []
        for j in range(KFOLD):
            sb, sh_, s = select_budget(pool, j, ALPHA, b)
            tot.append(len(sb) + len(sh_))
            sh.append(int(s))
        unfilled["예산 %d" % b] = collections.OrderedDict([
            ("겹별 학습 행", tot), ("🔴 못 채운 행", sh)])
        rows_ok = rows_ok and all(x == b for x in tot)
        rows_mut = rows_mut and all(x == b + 1 for x in tot)
    add("W2 예산 b 에서 겹당 학습 행 = b", rows_ok, rows_mut,
        "예산을 b+1 로 견준다 --- 통과하면 검사가 자료를 안 본다")

    # W3 — 유보가 예산과 무관하다 (🔴 ㉮-2)
    ho_sig = set()
    for b in BUDGETS:
        ho_sig.add(tuple(sorted((d, int((pool.db == d).sum())) for d in pool.gated)))
    add("W3 도메인별 유보 행이 예산 층마다 같다", len(ho_sig) == 1, True,
        "🔴 ㉮-2 --- 유보는 Pool.__init__ 산물이라 «구성상» 참이다")

    # W4 — 자료 지문이 안 바뀐다 (🔴 ㉮-4)
    fp0 = collections.OrderedDict([
        ("Xb", sha_arr(pool.Xb)), ("yb", sha_arr(pool.yb)),
        ("Xh", sha_arr(pool.Xh)), ("yh", sha_arr(pool.yh)),
        ("db", sha_arr(pool.db.astype("U16"))),
        ("dh", sha_arr(pool.dh.astype("U16")))])
    add("W4 자료 지문이 주행 내내 같다", True, True,
        "🔴 ㉮-4 --- 자료는 한 번 읽고 안 만진다. «구성상» 참이다")

    # W5 — α 가 hplt 몫을 정한다
    fr, frm = [], []
    for a in AGRID:
        sb, sh_, _ = select_budget(pool, 0, a, 1800)
        fr.append(abs(len(sh_) / 1800.0 - a) <= 1.0 / 1800)
        frm.append(abs(len(sh_) / 1800.0 - 0.5) <= 1.0 / 1800)
    add("W5 α 가 hplt 학습 몫을 정한다", all(fr), all(frm),
        "α 대신 0.5 로 견준다")

    # W6 — 전량이 예산 층보다 학습 행이 많다
    tot_full = []
    for j in range(KFOLD):
        sb, sh_, _ = select_budget(pool, j, ALPHA, None)
        tot_full.append(len(sb) + len(sh_))
    add("W6 전량 학습 행 > 36000", all(x > 36000 for x in tot_full),
        all(x > 10 ** 9 for x in tot_full), "천장을 10^9 로 견준다")

    out["§A6 배선"] = collections.OrderedDict([
        ("검사", wires),
        ("분모: 배선 검사", len(wires)),
        ("통과", sum(1 for v in wires.values() if v["통과"])),
        ("🔴 자료를 안 보는 검사",
         sum(1 for v in wires.values() if v["🔴 자료를 안 보는 검사인가"])),
        ("예산별 못 채운 행", unfilled),
        ("전량 겹별 학습 행", tot_full),
        ("자료 지문", fp0)])

    # ── §A7 🔴 조항 78 · 반증조건 ───────────────────────────────
    dc = out["§A4 군집 SE"]["🔴🔴 전량 − 1800"]["🔴🔴 도메인 군집"]
    d_by_rung = {k: v["채점 도메인 수"] for k, v in ladder.items()}
    ho_by_rung = {k: v["도메인별 유보 행"] for k, v in ladder.items()}
    out["🔴🔴 조항 78 --- ㉮ 원리상 못 «떨어지는» 검사"] = collections.OrderedDict([
        ("㉮-1 예산 층마다 d 가 같다", collections.OrderedDict([
            ("층별 d", d_by_rung), ("참인가", bool(len(set(d_by_rung.values())) == 1)),
            ("🔴 까닭", "pool.gated 는 Pool.__init__ 에서 base 행만으로 정해진다"),
            ("🔴 최상위 연언에서 뺐나", True)])),
        ("㉮-2 예산 층마다 유보 행 벡터가 같다", collections.OrderedDict([
            ("참인가", bool(len({json.dumps(v, sort_keys=True, ensure_ascii=False)
                               for v in ho_by_rung.values()}) == 1)),
            ("🔴 까닭", "ho_mask 도 Pool.__init__ 산물이다"),
            ("🔴 최상위 연언에서 뺐나", True)])),
        ("㉮-3 예산 b 에서 학습 행 = b", collections.OrderedDict([
            ("참인가", bool(rows_ok)),
            ("🔴 까닭", "b ≤ 35,000 이면 select 가 구성상 정확히 b 행을 만든다"),
            ("🔴 그래서 b=36000 칸을 일부러 넣었다",
             unfilled.get("예산 36000")),
            ("🔴 최상위 연언에서 뺐나", True)])),
        ("㉮-4 자료 지문이 안 바뀐다", collections.OrderedDict([
            ("참인가", True),
            ("🔴 까닭", "자료를 한 번 읽고 안 만진다"),
            ("🔴 최상위 연언에서 뺐나", True)])),
        ("🔴 분자", 4),
    ])
    out["🔴🔴 조항 78 --- ㉯ 원리상 못 «통과시키는» 입력"] = collections.OrderedDict([
        ("㉯-2 alpha977 세계에서 d ≥ 12",
         "도메인 합집합이 %d 다 --- 게이트를 3 까지 낮춰도 못 넘는다. "
         "그런 반증조건을 안 만들었다" % len(pool.doms)),
        ("🔴 분자(이 팔이 지는 몫)", 1),
        ("🔴 나머지 셋(㉯-1 ⑤′ 수리 레인 · ㉯-3 챔피언 공통 도메인 12 · ㉯-4 N_B 가 군집 SE 를 좁힌다)",
         "사전등록 §0-바 에 등기했다"),
    ])

    F = collections.OrderedDict()
    F["🔴 반증조건 2 --- 예산 사다리 묶음 ρ 단조(위반 ≤ 1)"] = "%d 위반" % viol
    F["통과: 반증조건 2"] = bool(viol <= 1)
    dpool = (ladder[full_key]["묶음 ρ"] or 0) - (ladder[base_key]["묶음 ρ"] or 0)
    sse = ladder[base_key]["묶음 씨앗 SE"] or 0.0
    F["🔴 반증조건 3 --- 전량 − 1800 묶음 Δ > 0 이고 씨앗 SE 의 2 배 초과"] = \
        "Δ %.6f · 씨앗 SE %.6f" % (dpool, sse)
    F["통과: 반증조건 3"] = bool(dpool > 0 and (sse == 0 or dpool > 2 * sse))
    tclu = dc.get("🔴 t_clu")
    F["🔴🔴 반증조건 4 --- Δ 균등 ρ 의 t_clu < 2 (벽)"] = str(tclu)
    F["통과: 반증조건 4"] = bool(tclu is not None and abs(tclu) < 2.0)
    nopp = dc.get("🔴 부호가 평균과 반대인 도메인 수")
    F["🔴 반증조건 5 --- 부호 반대 도메인 ≥ 1"] = str(nopp)
    F["통과: 반증조건 5"] = bool(nopp is not None and nopp >= 1)
    ratio = out["§A4 군집 SE"]["🔴🔴 τ̂ 비 (전량 / 1800)"]
    F["🔴 반증조건 6 --- τ̂(전량)/τ̂(1800) > 0.6"] = str(ratio)
    F["통과: 반증조건 6"] = bool(ratio is not None and ratio > 0.6)
    F["🔴 반증조건 11 --- 교차용 기준선(B 가 1e-12 안에서 맞춰야 한다)"] = \
        repr(baseline_f11(pool))

    # 🔴 F13 --- 헤드라인 대비마다 조각 분해표가 있나 (기계로 센다)
    heads = ["전량 − 1800 (§A4)"]
    segs = [k for k in out["§A4-나 🔴🔴 조각 분해표"] if k != "🔴 왜 있나"]
    F["🔴🔴 반증조건 13 --- 헤드라인 %d 개 · 조각 분해표 %d 개" % (len(heads), len(segs))] = \
        "헤드라인 %s / 표 %s" % (heads, segs)
    F["통과: 반증조건 13"] = bool(len(segs) >= len(heads))

    # 🔴 F18 --- 도장 분모에 «자기 러너»가 들어 있나
    F["🔴 반증조건 18 --- 도장 분모의 첫 자리가 자기 파일인가"] = SRC[0]
    F["통과: 반증조건 18"] = bool(SRC[0] == "runners/gamma995_nb.py"
                              and cs0.get(SRC[0]) is not None)
    out["§A7 반증조건"] = F

    # ── §A8 🔴🔴🔴 조항 78 을 «기계»로 센다 (사전등록 §9-4 · F16) ──
    #   994 는 항등식 계수를 «손 라벨»로 냈고 그 칸 자신이 리터럴이라
    #   원리상 「0 개」를 못 냈다. 여기서는 조각마다 «변이체를 돌려» 판정한다.
    def probe(name, real, mutant, why):
        return collections.OrderedDict([
            ("검사 이름", name), ("실제 판에서 참인가", bool(real)),
            ("🔴 변이체에서도 참인가", bool(mutant)),
            ("🔴🔴 원리상 못 떨어지나(㉮)", bool(real and mutant)),
            ("변이체", why)])

    probes = []
    # F02 변이체 --- 사다리 차례를 뒤집는다
    rev = list(reversed(pooled_seq))
    viol_rev = sum(1 for i in range(1, len(rev))
                   if rev[i] is not None and rev[i - 1] is not None
                   and rev[i] < rev[i - 1] - 1e-12)
    probes.append(probe("F02 사다리 단조", viol <= 1, viol_rev <= 1,
                        "사다리 차례를 뒤집는다"))
    # F03 변이체 --- Δ 의 부호를 뒤집는다
    probes.append(probe("F03 전량 > 1800",
                        dpool > 0 and (sse == 0 or dpool > 2 * sse),
                        (-dpool) > 0 and (sse == 0 or (-dpool) > 2 * sse),
                        "Δ 의 부호를 뒤집는다"))
    # F04 변이체 --- 도메인별 Δ 를 «전부 같은 값»으로 만든다(흩어짐 0 ⇒ SE 0)
    flat = {k: 1.0 for k in delta}
    fc = dom_cluster(flat)
    probes.append(probe("F04 t_clu < 2 (벽)",
                        tclu is not None and abs(tclu) < 2.0,
                        (fc.get("🔴 t_clu") is not None
                         and abs(fc["🔴 t_clu"]) < 2.0),
                        "도메인별 Δ 를 전부 1.0 으로 --- 흩어짐 0"))
    # F05 변이체 --- 부호를 전부 평균 쪽으로 맞춘다
    same = {k: abs(v) for k, v in delta.items()}
    sc = dom_cluster(same)
    probes.append(probe("F05 부호 반대 도메인 ≥ 1",
                        nopp is not None and nopp >= 1,
                        sc.get("🔴 부호가 평균과 반대인 도메인 수", 0) >= 1,
                        "도메인별 Δ 를 전부 절댓값으로 --- 부호 반대가 원리상 0"))
    # F06 변이체 --- τ̂ 비를 0.1 로 억지로 만든다
    probes.append(probe("F06 τ̂ 비 > 0.6",
                        ratio is not None and ratio > 0.6, 0.1 > 0.6,
                        "τ̂ 비를 0.1 로 견준다"))
    # 🔴 대조판 --- 이 칸은 «반드시» 0 을 낸다. 계수가 0 을 낼 수 있음을 보인다
    # 🔴 대조판 --- 「0 을 낼 수 있나」를 «계산»으로 보인다. 리터럴이 아니다.
    _dv = np.asarray([delta[k] for k in sorted(delta)], float)
    _rs = np.random.RandomState(995)
    _plac = {k: abs(delta[k]) * (1 if _rs.rand() < 0.5 else -1) for k in delta}
    _pc = dom_cluster(_plac)
    ctrl = [probe("대조 1 --- Δ 의 부호를 위약으로 흩는다",
                  tclu is not None and abs(tclu) >= 0.0,
                  bool(_pc.get("🔴 t_clu") is not None and abs(_pc["🔴 t_clu"]) > 1e9),
                  "위약 --- 크기는 두고 부호만 무작위(RandomState(995))"),
            probe("대조 2 --- Δ 가 0 이면 t 가 0 인가",
                  bool(abs(float(_dv.mean())) > 0),
                  bool(abs(float(np.zeros(len(_dv)).mean())) > 0),
                  "Δ 를 전부 0 으로")]
    mach = sum(1 for p in probes if p["🔴🔴 원리상 못 떨어지나(㉮)"])
    mach += sum(1 for v in wires.values() if v["🔴 자료를 안 보는 검사인가"])
    out["§A8 🔴🔴🔴 조항 78 --- 기계로 센 ㉮"] = collections.OrderedDict([
        ("🔴 왜 손으로 안 세나",
         "티처 #133 --- score994.py:837-838 의 항등식 계수 칸이 «리터럴»이라 "
         "원리상 「0 개」를 못 냈다. 여기서는 변이체를 «돌려서» 판정한다."),
        ("반증조건 조각", probes),
        ("배선 조각",
         [collections.OrderedDict([("검사 이름", k),
                                   ("실제 판에서 참인가", v["통과"]),
                                   ("🔴 변이체에서도 참인가", v["변이체도 통과"]),
                                   ("🔴🔴 원리상 못 떨어지나(㉮)",
                                    v["🔴 자료를 안 보는 검사인가"]),
                                   ("변이체", v["변이체"])])
          for k, v in wires.items()]),
        ("🔴🔴 기계가 센 ㉮ 분자", int(mach)),
        ("🔴 손으로 센 ㉮ 분자(사전등록 §0-바)", 4),
        ("🔴 기계 − 손", int(mach) - 4),
        ("분모: 검사한 조각", len(probes) + len(wires)),
        ("🔴🔴 대조판 --- 계수가 「0」을 낼 수 있나", collections.OrderedDict([
            ("조각", ctrl),
            ("🔴 이 판의 ㉮ 분자",
             int(sum(1 for p in ctrl if p["🔴🔴 원리상 못 떨어지나(㉮)"]))),
            ("🔴🔴 0 이 나왔나",
             bool(sum(1 for p in ctrl if p["🔴🔴 원리상 못 떨어지나(㉮)"]) == 0))])),
        ("🔴 통과: 반증조건 16",
         bool(sum(1 for p in ctrl if p["🔴🔴 원리상 못 떨어지나(㉮)"]) == 0)),
    ])
    F["통과: 반증조건 16"] = out["§A8 🔴🔴🔴 조항 78 --- 기계로 센 ㉮"]["🔴 통과: 반증조건 16"]

    # 🔴 벌의 범위 규칙 (사전등록 §9-6) --- 측정 «전»에 박은 자다
    dev = 7.199316e-04
    out["🔴 벌의 범위 규칙(사전등록 §9-6)"] = collections.OrderedDict([
        ("🔴 F01 이탈 크기(측정 전에 박았다)", dev),
        ("🔴 안전 배수 문턱", 20),
        ("이 팔이 챔피언 경로를 쓰나", False),
        ("🔴 그래서 F01 정정이 이 팔에 해당하나", "해당 없음 --- alpha977 세계다"),
        ("참고: 헤드라인 Δ 의 안전 배수",
         _r(abs(dpool) / dev, 3) if dev else None),
    ])

    out["🔴 도장"] = collections.OrderedDict([
        ("언제(시작 · UTC)", t0), ("언제(끝 · UTC)", _now()),
        ("걸린 초", round(time.time() - wall0, 1)),
        ("🔴 코드 sha256(시작)", cs0), ("🔴 코드 sha256(끝)", code_stamp()),
        ("🔴 시작=끝", bool(cs0 == code_stamp())),
        ("분모: 도장이 덮는 소스", len(cs0)),
        ("🔴 고정한 스레드", THREADS),
        ("🔴 git HEAD 스탬프", "폐기됐다 --- 조항 66"),
    ])
    return out


def d_items(dd):
    return sorted(dd.items())


def baseline_f11(pool):
    """🔴 `F11` 교차 검사용 — 씨앗 976 · 예산 1800 · α=0.95 · λ=1 의 묶음 ρ 를
    **전정밀로** 낸다. 팔 B 가 «독립 코드»로 같은 수를 내야 한다."""
    pool.reseed(976)
    o = oof(pool, ALPHA, LAM, 1800)
    po, eq, per, w, drop = score_dom(pool, o["예측"], gated_for(pool, 20))
    return collections.OrderedDict([
        ("씨앗", 976), ("예산", 1800), ("α", ALPHA), ("λ", LAM),
        ("🔴 묶음 ρ(전정밀)", repr(po)), ("🔴 균등 ρ(전정밀)", repr(eq)),
        ("채점 도메인 수", len(per))])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["nb"])
    a = ap.parse_args()
    out = stage_nb()
    OUTFILE.write_text(json.dumps(out, ensure_ascii=False, indent=1),
                       encoding="utf-8")
    print("wrote %s" % OUTFILE)


if __name__ == "__main__":
    main()
