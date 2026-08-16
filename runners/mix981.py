#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""981 — 🔴🔴 **C3 이득을 자에서 떼어 다시 잰다** (축 C3 · 곁 C4).

사전등록 `docs/prereg_981_pick.md` §3 를 그대로 따른다.

🔴 **왜.** 980 의 층화 이득이 **「자가 가장 무겁게 재는 도메인을 더 학습시킨 것」**과 안 갈렸다.
`mix980.quota()` 의 목표가 `pool.ho_mask[d].sum()` 이고 정본 자 가중이 `w ∝ n_d − 1` —
**같은 벡터다.**

그래서 이 러너는 둘을 뗀다.
    ① **목표 혼합을 격자로** 쓴다 — 🔴 **자와 무관한 목표를 둘 넣는다**(`T2 균등`·`T3 공급 몫`)
    ② 이득이 **자 여섯 전부에서 서는가**를 측정 전에 등록하고 잰다
    ③ 🔴 **위약 층화 팔** `㉱` 로 「공급 제약」과 「대조 팔의 혼합 수렴」을 가른다

🔴 **자는 1순위(`pick981.py`)에서 뽑은 것 하나만 쓴다.**
🔴 **예산 `N_B` 는 인자다** — `alpha977.py:60` 은 동결물이라 안 고치고 **등록 기본값**으로만 쓴다.

씀:
    python3 runners/mix981.py --stage target --ref <40자 sha>
    python3 runners/mix981.py --stage decomp --ref <40자 sha>
"""
import argparse
import collections
import datetime as dt
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
import alpha977 as A                              # noqa: E402
import ruler979 as R9                             # noqa: E402
import mix980 as M8                               # noqa: E402

RAN = ("runners/mix981.py", "runners/pick981.py", "runners/mix980.py",
       "runners/ruler979.py", "runners/ruler978.py", "runners/alpha977.py",
       "runners/ledger.py", "runners/layers957.py", "runners/predict971.py",
       "runners/loso974.py")
OUT = ROOT / "runners"
PROG = OUT / "out981_progress.txt"

RULERS = R9.RULERS
SEEDS = A.SEEDS
KFOLD = A.KFOLD
U_REG = A.U_REG
ALPHA_BASE = A.ALPHA_BASE
K_FEAT = M8.K_FEAT

#: 🔴 등록 기본 예산 — `alpha977.N_B` 를 **이름으로** 인용만 한다(상수 자리에서 뺐다)
NB_DEFAULT = A.N_B
NB_GRID = list(M8.NB_GRID)
BOOT_T = 200                       # 사전등록 §8 — 목표 격자 복제 수
BOOT_D = 200                       # 사전등록 §8 — 분해 격자 복제 수
MIXDRAW = 200                      # 대조 팔 혼합 표집 SD 진단 뽑기 수

ARM_C = M8.ARM_C                   # ㉯ 대조(순열 앞머리)
ARM_S = M8.ARM_S                   # ㉮/㉱ 층화(할당량)
ARM_PLACEBO = "㉱ 위약 층화(목표=공급 몫)"


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _prog(msg):
    with open(str(PROG), "a", encoding="utf-8") as f:
        f.write("%s  %s\n" % (_now(), msg))
    sys.stderr.write("%s  %s\n" % (_now(), msg))
    sys.stderr.flush()


def _r(x, n=6):
    return None if x is None or not np.isfinite(float(x)) else round(float(x), n)


# ══════════════════════════════════════════════════════════════════════
# §1 목표 혼합 격자 — 🔴 자와 무관한 목표를 «둘» 넣는다 (반증조건 11)
# ══════════════════════════════════════════════════════════════════════
def targets(pool):
    doms = list(pool.gated)
    nho = {d: float(pool.ho_mask[d].sum()) for d in doms}
    sup = collections.Counter(pool.dh.tolist())
    T = collections.OrderedDict()
    T["T1 유보 혼합 (n_d)"] = dict(nho)
    T["T2 균등 (1)"] = {d: 1.0 for d in doms}
    T["T3 공급 몫 (hplt 행)"] = {d: float(max(sup.get(d, 0), 0)) for d in doms}
    T["T4 √유보 (√n_d)"] = {d: math.sqrt(nho[d]) for d in doms}
    T["T5 역유보 (1/n_d)"] = {d: 1.0 / nho[d] for d in doms}
    return T


#: 🔴 목표가 정본 자와 «같은 벡터»인가 — 측정 전에 못박은 딱지
TGT_ALIGNED = {
    "T1 유보 혼합 (n_d)": True,
    "T2 균등 (1)": False,
    "T3 공급 몫 (hplt 행)": False,
    "T4 √유보 (√n_d)": None,
    "T5 역유보 (1/n_d)": False,
}


def _nor(v, doms):
    s = float(sum(v[d] for d in doms))
    return np.asarray([v[d] / s for d in doms], float)


def cos_align(a, b):
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(a.dot(b) / (na * nb)) if na > 0 and nb > 0 else None


# ══════════════════════════════════════════════════════════════════════
# §2 배관 — 🔴 `mix980` 의 선택기를 그대로 쓰되 **목표를 인자로 넘긴다**
# ══════════════════════════════════════════════════════════════════════
def oof981(pool, alpha, lam, n_b, arm, tgt=None, k=K_FEAT, tr_boot=None):
    """`mix980.oof980` 과 같은 배관이고 **목표만 인자로 더 뺐다**."""
    pred = np.zeros(len(pool.yb))
    ntr, nsel_h = [], []
    for j in range(KFOLD):
        selb, selh, _q, _bd, _sh = M8.select980(pool, j, alpha, n_b, arm, tgt)
        X, y, ent, _nb = A.design(pool, selb, selh, k)
        if tr_boot is not None:
            rng = np.random.RandomState(tr_boot * 1000 + j + 977 * 100000)
            order, st, en = A.groups_of(ent)
            pick = rng.randint(0, len(st), len(st))
            idx = np.concatenate([order[st[g]:en[g]] for g in pick])
            X, y = X[idx], y[idx]
        m = L.ridge_fit(X, y, lam)
        te = pool.fi == j
        pred[te] = L.ridge_pred(m, np.hstack([pool.Xb[te][:, :k], pool.Ob[te]]))
        ntr.append(int(len(y)))
        nsel_h.append(int(len(selh)))
    return {"예측": pred, "겹별 학습 행": ntr, "겹별 hplt 행": nsel_h}


def point5(pool, R, alpha, lam, n_b, arm, tgt=None):
    """🔴 **5 벌**(겹 씨앗 다섯) 평균 — 짝 SE 와 벌 수가 같다."""
    acc = {nm: [] for nm in RULERS}
    nh, ntr = [], []
    for s in SEEDS:
        pool.reseed(s)
        r = oof981(pool, alpha, lam, n_b, arm, tgt)
        v, _p = R9.score6(pool, R, r["예측"])
        for nm in RULERS:
            acc[nm].append(v[nm])
        nh.append(r["겹별 hplt 행"][0])
        ntr.append(r["겹별 학습 행"][0])
    out = collections.OrderedDict()
    for nm in RULERS:
        out[nm] = _r(float(np.mean(acc[nm])))
        out[nm + " 벌 SD"] = _r(float(np.std(acc[nm], ddof=1)))
    out["🔴 벌 수"] = len(acc[RULERS[0]])
    out["🔴 겹당 hplt 학습 행"] = int(np.mean(nh))
    out["🔴 겹당 학습 행 전량"] = int(np.mean(ntr))
    return out


def se_multi(pool, R, alpha, lam, n_b, arms, boot, tag=""):
    """🔴🔴 **짝 SE** — 복제마다 겹 다섯의 Δ 를 평균하고 그 평균의 SD.

    `arms` = OrderedDict[팔 이름] -> tgt (None 이면 대조 팔)
    🔴 **대조 팔은 복제 하나 안에서 한 번만 돌고 모든 처리 팔이 그것과 짝을 이룬다**
    (같은 복제·같은 겹·같은 붓스트랩 → 진짜 짝이다).
    """
    names = [k for k in arms if arms[k] is not None]
    dd = {a: {nm: [] for nm in RULERS} for a in names}
    ctl = {nm: [] for nm in RULERS}
    trt = {a: {nm: [] for nm in RULERS} for a in names}
    t0 = time.time()
    for b in range(boot):
        bc = {nm: [] for nm in RULERS}
        bt = {a: {nm: [] for nm in RULERS} for a in names}
        for s in SEEDS:
            pool.reseed(s)
            pc = oof981(pool, alpha, lam, n_b, ARM_C, None, tr_boot=b)["예측"]
            vc, _ = R9.score6(pool, R, pc)
            for nm in RULERS:
                bc[nm].append(vc[nm])
            for a in names:
                pa = oof981(pool, alpha, lam, n_b, ARM_S, arms[a],
                            tr_boot=b)["예측"]
                va, _ = R9.score6(pool, R, pa)
                for nm in RULERS:
                    bt[a][nm].append(va[nm] - vc[nm])
        for nm in RULERS:
            ctl[nm].append(float(np.mean(bc[nm])))
        for a in names:
            for nm in RULERS:
                dd[a][nm].append(float(np.mean(bt[a][nm])))
        if (b + 1) % 50 == 0:
            _prog("    %s 짝SE 뽑기 %d/%d (%.0fs)" % (tag, b + 1, boot,
                                                   time.time() - t0))
    out = collections.OrderedDict()
    for a in names:
        out[a] = collections.OrderedDict(
            [(nm, _r(float(np.std(dd[a][nm], ddof=1)))) for nm in RULERS])
    out["🔴 대조 팔 SE"] = collections.OrderedDict(
        [(nm, _r(float(np.std(ctl[nm], ddof=1)))) for nm in RULERS])
    out["🔴 복제 수"] = boot
    out["🔴 벌 수(복제 하나 안에서)"] = len(SEEDS)
    out["🔴 이 SE 가 무엇의 SE 인가"] = (
        "복제마다 겹 씨앗 다섯의 Δ(= 처리 팔 − 대조 팔)를 평균한 뒤 그 평균의 SD. "
        "🔴 점추정과 벌 수가 같다(둘 다 5 벌) · 🔴 대조 팔은 복제 하나 안에서 한 번만 돈다")
    return out, trt


def gate2(delta, se):
    return collections.OrderedDict([
        ("Δ", _r(delta)),
        ("🔴 짝 SE", se),
        ("🔴🔴 |Δ|/짝SE", _r(abs(delta) / se, 4) if (se and delta is not None) else None),
        ("🔴 Δ > 0", bool(delta is not None and delta > 0)),
        ("🔴🔴 Δ > 0 그리고 |Δ| ≥ 2·짝SE",
         bool(se and delta is not None and delta > 0 and abs(delta) >= 2 * se)),
    ])


def _spear(a, b):
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    if len(a) < 3 or np.std(a) == 0 or np.std(b) == 0:
        return None
    return float(P.spear(a, b))


# ══════════════════════════════════════════════════════════════════════
# S1 `target` — 🔴🔴 목표 혼합 격자 × 자 여섯
# ══════════════════════════════════════════════════════════════════════
def stage_target(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    _prog("target 시작")
    pool = A.Pool()
    h0 = R9.ho_stamp(pool)
    R = R9.Rulers6(pool)
    doms = list(pool.gated)
    T = targets(pool)

    pk = json.loads((OUT / "out981_pick.json").read_text(encoding="utf-8"))
    canon = pk["🔴🔴🔴 §3 정본 자 (등록 판정 = 체제 B)"]
    if canon not in RULERS:
        raise SystemExit("🔴 정본 자를 못 읽었다 — fail-closed")

    # ── 정렬도 ────────────────────────────────────────────────────
    wall = R.all_w()
    align = collections.OrderedDict()
    for tn in T:
        tv = _nor(T[tn], doms)
        align[tn] = collections.OrderedDict(
            [(nm, _r(cos_align(tv, _nor(wall[nm], doms)), 4)) for nm in RULERS])

    # ── 실제 학습 혼합 진단 ────────────────────────────────────────
    nh = int(round(ALPHA_BASE * NB_DEFAULT))
    mixdiag = collections.OrderedDict()
    pool.reseed(SEEDS[0])
    for tn in [None] + list(T.keys()):
        selh, q, bound, short = M8._selh(pool, ALPHA_BASE, NB_DEFAULT,
                                         ARM_C if tn is None else ARM_S,
                                         None if tn is None else T[tn])
        r, a, b = M8.mix_r(pool, selh)
        cnt = collections.Counter(pool.dh[selh].tolist())
        mixdiag["㉯ 대조" if tn is None else tn] = collections.OrderedDict([
            ("🔴 학습 hplt 행", int(len(selh))),
            ("🔴 도메인별 학습 행", {d: int(cnt.get(d, 0)) for d in doms}),
            ("🔴 유보 혼합과의 피어슨 r", _r(r, 4)),
            ("🔴 공급에 묶인 도메인 수", len(bound or {})),
            ("🔴 못 채운 자리", int(short)),
        ])

    # ── 본 측정 ────────────────────────────────────────────────────
    cells = collections.OrderedDict()
    for u in U_REG:
        lam = 10.0 ** u
        key = "u=%d" % u
        _prog("  λ %s 점추정" % key)
        pt = collections.OrderedDict()
        pt["㉯ 대조"] = point5(pool, R, ALPHA_BASE, lam, NB_DEFAULT, ARM_C, None)
        for tn in T:
            pt[tn] = point5(pool, R, ALPHA_BASE, lam, NB_DEFAULT, ARM_S, T[tn])
        arms = collections.OrderedDict([(tn, T[tn]) for tn in T])
        se, _ = se_multi(pool, R, ALPHA_BASE, lam, NB_DEFAULT, arms, BOOT_T,
                         tag="λ %s" % key)
        per = collections.OrderedDict()
        for tn in T:
            g = collections.OrderedDict()
            for nm in RULERS:
                d = pt[tn][nm] - pt["㉯ 대조"][nm]
                g[nm] = gate2(d, se[tn][nm])
            nsign = sum(1 for nm in RULERS if g[nm]["🔴 Δ > 0"])
            nsize = sum(1 for nm in RULERS if g[nm]["🔴🔴 Δ > 0 그리고 |Δ| ≥ 2·짝SE"])
            per[tn] = collections.OrderedDict([
                ("🔴 자와 정렬된 목표인가(측정 전 딱지)", TGT_ALIGNED[tn]),
                ("🔴 정본 자에서의 판정", g[canon]),
                ("자 여섯 전부", g),
                ("🔴 부호 서는 자 수 (0~6)", nsign),
                ("🔴🔴 크기 서는 자 수 (0~6)", nsize),
                ("🔴 목표–자 정렬도", align[tn]),
                ("🔴🔴 정렬도와 Δ 의 스피어만",
                 _r(_spear([align[tn][nm] for nm in RULERS],
                           [g[nm]["Δ"] for nm in RULERS]), 4)),
            ])
        cells[key] = collections.OrderedDict([
            ("🔴 점추정(5 벌)", pt),
            ("🔴 짝 SE", se),
            ("🔴🔴 목표별", per),
        ])

    # ── 등록 판정 ─────────────────────────────────────────────────
    verdict = collections.OrderedDict()
    for tn in T:
        both = all(cells["u=%d" % u]["🔴🔴 목표별"][tn]["🔴🔴 크기 서는 자 수 (0~6)"] == 6
                   for u in U_REG)
        verdict[tn] = collections.OrderedDict([
            ("🔴🔴🔴 이득이 자 여섯 전부에서 λ 둘 다에서 서나", bool(both)),
            ("λ 별 크기 서는 자 수",
             {"u=%d" % u: cells["u=%d" % u]["🔴🔴 목표별"][tn]["🔴🔴 크기 서는 자 수 (0~6)"]
              for u in U_REG}),
            ("λ 별 정본 자 Δ",
             {"u=%d" % u: cells["u=%d" % u]["🔴🔴 목표별"][tn]["🔴 정본 자에서의 판정"]["Δ"]
              for u in U_REG}),
            ("λ 별 정본 자 |Δ|/짝SE",
             {"u=%d" % u: cells["u=%d" % u]["🔴🔴 목표별"][tn]["🔴 정본 자에서의 판정"]["🔴🔴 |Δ|/짝SE"]
              for u in U_REG}),
        ])

    # ── 예측 채점 ─────────────────────────────────────────────────
    T1, T2 = "T1 유보 혼합 (n_d)", "T2 균등 (1)"
    T5 = "T5 역유보 (1/n_d)"
    sp = [cells["u=%d" % u]["🔴🔴 목표별"][tn]["🔴🔴 정렬도와 Δ 의 스피어만"]
          for u in U_REG for tn in T]
    sp = [x for x in sp if x is not None]
    pred = collections.OrderedDict([
        ("P4 — 정렬도와 Δ 의 스피어만이 양수(칸 평균)",
         bool(np.mean(sp) > 0) if sp else None),
        ("P4 · 칸별 스피어만 평균", _r(float(np.mean(sp)), 4) if sp else None),
        ("P4 · 양수인 칸 / 전체", "%d / %d" % (sum(1 for x in sp if x > 0), len(sp))),
        ("P5 — T1 에서 「자 전부에서 선다」가 거짓",
         bool(not verdict[T1]["🔴🔴🔴 이득이 자 여섯 전부에서 λ 둘 다에서 서나"])),
        ("P6 — T2 의 R_eq Δ 가 T1 의 R_eq Δ 보다 크다(λ 둘 다)",
         bool(all(cells["u=%d" % u]["🔴🔴 목표별"][T2]["자 여섯 전부"][R9.R2]["Δ"]
                  > cells["u=%d" % u]["🔴🔴 목표별"][T1]["자 여섯 전부"][R9.R2]["Δ"]
                  for u in U_REG))),
        ("P9 — T5 역유보에서 정본 자의 Δ 가 음수(λ 둘 다)",
         bool(all(cells["u=%d" % u]["🔴🔴 목표별"][T5]["🔴 정본 자에서의 판정"]["Δ"] < 0
                  for u in U_REG))),
    ])

    out = collections.OrderedDict()
    out["무엇"] = ("981 §3 — 🔴🔴 **C3 이득을 자에서 떼어 다시 잰다.** "
                 "목표 혼합 격자 다섯 × λ 둘 × 자 여섯")
    out["🔴 축"] = "C3 (곁 C4)"
    out["사전등록"] = "docs/prereg_981_pick.md §3"
    out["🔴🔴 정본 자(1순위에서 뽑은 것 하나)"] = canon
    out["🔴 정본 자의 출처"] = "runners/out981_pick.json → §3 체제 B 의 pick() 산출물"
    out["🔴 예산 N_B (등록 기본값 · alpha977.N_B 를 이름으로 인용)"] = NB_DEFAULT
    out["🔴 예산이 상수 자리에 있나"] = False
    out["🔴 α"] = ALPHA_BASE
    out["🔴🔴 목표 격자"] = collections.OrderedDict(
        [(tn, {"목표 몫": {d: _r(_nor(T[tn], doms)[i]) for i, d in enumerate(doms)},
               "🔴 자와 정렬된 목표인가": TGT_ALIGNED[tn]}) for tn in T])
    out["🔴 자와 무관한 목표 수"] = sum(1 for tn in T if TGT_ALIGNED[tn] is False)
    out["🔴🔴 목표–자 정렬도 (코사인)"] = align
    out["🔴 학습 혼합 진단"] = mixdiag
    out["🔴🔴🔴 칸"] = cells
    out["🔴🔴🔴 등록 판정 — 이득이 자 여섯 전부에서 서는가"] = verdict
    out["🔴 예측 채점"] = pred
    out["통과"] = bool(len(cells) == len(U_REG) and len(verdict) == len(T)
                     and out["🔴 자와 무관한 목표 수"] >= 1)
    out["🔴 이 절의 `통과` 가 뜻하는 것"] = (
        "λ 둘 × 목표 다섯 칸이 전부 돌았고 자와 무관한 목표가 최소 하나 격자에 있다"
        "(반증조건 11). 🔴 이 값은 이득이 섰는지와 무관하다")
    out["🔴 유보 지문"] = R9.ho_verdict(h0, R9.ho_stamp(pool))
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LO.SRC)
    (OUT / "out981_target.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    _prog("target 끝")
    return out


# ══════════════════════════════════════════════════════════════════════
# S2 `decomp` — 🔴🔴 공급 제약 대 대조 팔의 혼합 수렴
# ══════════════════════════════════════════════════════════════════════
def ctl_mix_sd(pool, n_b, draws=MIXDRAW, seed=981):
    """🔴 대조 팔(순열 앞머리)이 뽑는 도메인 «몫 벡터»의 표집 SD.

    팔을 안 바꾸고 **같은 뽑기 규약**(앞머리 nh 행)을 `draws` 번 되풀이해 잰다.
    🔴 이것이 「층화가 없앨 수 있는 잡음」의 크기다.
    """
    doms = list(pool.gated)
    nh = int(round(ALPHA_BASE * n_b))
    N = len(pool.dh)
    rng = np.random.RandomState(seed + n_b)
    idx = {d: i for i, d in enumerate(doms)}
    codes = np.asarray([idx.get(d, -1) for d in pool.dh], np.int64)
    S = np.zeros((draws, len(doms)), float)
    for b in range(draws):
        pick = rng.choice(N, size=min(nh, N), replace=False)
        c = codes[pick]
        c = c[c >= 0]
        cnt = np.bincount(c, minlength=len(doms)).astype(float)
        S[b] = cnt / max(cnt.sum(), 1.0)
    sd = S.std(axis=0, ddof=1)
    mean = S.mean(axis=0)
    return collections.OrderedDict([
        ("🔴 도메인별 몫 표집 SD", {d: _r(sd[i], 6) for i, d in enumerate(doms)}),
        ("🔴🔴 몫 표집 SD 의 L1 합", _r(float(sd.sum()))),
        ("🔴 몫 평균", {d: _r(mean[i]) for i, d in enumerate(doms)}),
        ("🔴 뽑기 수", int(draws)),
    ])


def stage_decomp(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    _prog("decomp 시작")
    pool = A.Pool()
    h0 = R9.ho_stamp(pool)
    R = R9.Rulers6(pool)
    doms = list(pool.gated)
    T = targets(pool)
    T1, T3 = "T1 유보 혼합 (n_d)", "T3 공급 몫 (hplt 행)"

    pk = json.loads((OUT / "out981_pick.json").read_text(encoding="utf-8"))
    canon = pk["🔴🔴🔴 §3 정본 자 (등록 판정 = 체제 B)"]

    cells = collections.OrderedDict()
    for n_b in NB_GRID:
        key = "N_B=%d" % n_b
        _prog("  %s" % key)
        pool.reseed(SEEDS[0])
        _sh1, q1, bd1, sh1 = M8._selh(pool, ALPHA_BASE, n_b, ARM_S, T[T1])
        _sh3, q3, bd3, sh3 = M8._selh(pool, ALPHA_BASE, n_b, ARM_S, T[T3])
        per_u = collections.OrderedDict()
        for u in U_REG:
            lam = 10.0 ** u
            pc = point5(pool, R, ALPHA_BASE, lam, n_b, ARM_C, None)
            p1 = point5(pool, R, ALPHA_BASE, lam, n_b, ARM_S, T[T1])
            p3 = point5(pool, R, ALPHA_BASE, lam, n_b, ARM_S, T[T3])
            arms = collections.OrderedDict([("㉮ 층화(유보)", T[T1]),
                                            (ARM_PLACEBO, T[T3])])
            se, _ = se_multi(pool, R, ALPHA_BASE, lam, n_b, arms, BOOT_D,
                             tag="%s λ u=%d" % (key, u))
            per_u["u=%d" % u] = collections.OrderedDict([
                ("㉯ 대조 ρ(정본 자)", pc[canon]),
                ("㉮ 층화(유보) ρ(정본 자)", p1[canon]),
                ("㉱ 위약 층화(공급) ρ(정본 자)", p3[canon]),
                ("🔴🔴 ㉮ − ㉯", gate2(p1[canon] - pc[canon], se["㉮ 층화(유보)"][canon])),
                ("🔴🔴 ㉱ − ㉯", gate2(p3[canon] - pc[canon], se[ARM_PLACEBO][canon])),
                ("🔴 자 여섯 ㉮ − ㉯",
                 collections.OrderedDict([(nm, _r(p1[nm] - pc[nm])) for nm in RULERS])),
                ("🔴 자 여섯 ㉱ − ㉯",
                 collections.OrderedDict([(nm, _r(p3[nm] - pc[nm])) for nm in RULERS])),
                ("🔴 복제 수", se["🔴 복제 수"]),
            ])
        cells[key] = collections.OrderedDict([
            ("🔴 예산", n_b),
            ("🔴 hplt 자리", int(round(ALPHA_BASE * n_b))),
            ("🔴🔴 공급에 묶인 도메인 수 (㉮ 유보 목표)", len(bd1 or {})),
            ("🔴 묶인 도메인 (㉮)", list((bd1 or {}).keys())),
            ("🔴 공급에 묶인 도메인 수 (㉱ 공급 목표)", len(bd3 or {})),
            ("🔴🔴 대조 팔 혼합의 표집 SD", ctl_mix_sd(pool, n_b)),
            ("🔴 λ 별", per_u),
        ])

    # ── 분해 ──────────────────────────────────────────────────────
    dec = collections.OrderedDict()
    for u in U_REG:
        uk = "u=%d" % u
        g1 = [cells["N_B=%d" % n]["🔴 λ 별"][uk]["🔴🔴 ㉮ − ㉯"]["Δ"] for n in NB_GRID]
        g3 = [cells["N_B=%d" % n]["🔴 λ 별"][uk]["🔴🔴 ㉱ − ㉯"]["Δ"] for n in NB_GRID]
        nb0 = [cells["N_B=%d" % n]["🔴🔴 공급에 묶인 도메인 수 (㉮ 유보 목표)"]
               for n in NB_GRID]
        sdl = [cells["N_B=%d" % n]["🔴🔴 대조 팔 혼합의 표집 SD"]["🔴🔴 몫 표집 SD 의 L1 합"]
               for n in NB_GRID]
        tot = g1[0] - g1[-1]
        #: 🔴 묶인 도메인이 «아직 0» 인 구간에서 일어난 감소
        last0 = max([i for i, v in enumerate(nb0) if v == 0] or [0])
        pre = g1[0] - g1[last0]
        dec[uk] = collections.OrderedDict([
            ("🔴 ㉮ 이득 격자", collections.OrderedDict(
                [("N_B=%d" % n, g1[i]) for i, n in enumerate(NB_GRID)])),
            ("🔴🔴 ㉱ 위약 이득 격자", collections.OrderedDict(
                [("N_B=%d" % n, g3[i]) for i, n in enumerate(NB_GRID)])),
            ("🔴 묶인 도메인 수 격자", collections.OrderedDict(
                [("N_B=%d" % n, nb0[i]) for i, n in enumerate(NB_GRID)])),
            ("🔴 대조 혼합 표집 SD L1 격자", collections.OrderedDict(
                [("N_B=%d" % n, sdl[i]) for i, n in enumerate(NB_GRID)])),
            ("🔴🔴 총 감소(첫 칸 − 끝 칸)", _r(tot)),
            ("🔴 묶임 0 인 구간(N_B=%d → %d)에서의 감소" % (NB_GRID[0], NB_GRID[last0]),
             _r(pre)),
            ("🔴🔴🔴 묶임 0 구간이 총 감소의 몇 %",
             _r(100.0 * pre / tot, 2) if tot else None),
            ("🔴🔴 위약 팔이 2·짝SE 를 넘는 예산 칸",
             [("N_B=%d" % n) for i, n in enumerate(NB_GRID)
              if cells["N_B=%d" % n]["🔴 λ 별"][uk]["🔴🔴 ㉱ − ㉯"]
              ["🔴🔴 Δ > 0 그리고 |Δ| ≥ 2·짝SE"]]),
            ("🔴🔴 위약 이득과 대조 혼합 SD 의 스피어만", _r(_spear(g3, sdl), 4)),
            ("🔴 ㉮ 이득과 대조 혼합 SD 의 스피어만", _r(_spear(g1, sdl), 4)),
            ("🔴🔴 ㉮ 이득 중 위약이 설명하는 몫(첫 칸)",
             _r(g3[0] / g1[0], 4) if g1[0] else None),
        ])

    pred = collections.OrderedDict([
        ("P7 — 위약 팔 ㉱ 의 이득이 작은 예산에서 2·짝SE 를 넘는다",
         bool(any(cells["N_B=%d" % NB_GRID[0]]["🔴 λ 별"]["u=%d" % u]["🔴🔴 ㉱ − ㉯"]
                  ["🔴🔴 Δ > 0 그리고 |Δ| ≥ 2·짝SE"] for u in U_REG))),
    ])

    out = collections.OrderedDict()
    out["무엇"] = ("981 §3-4 — 🔴🔴 **「공급 제약」과 「대조 팔의 혼합 수렴」을 가른다.** "
                 "위약 층화 팔 ㉱ 는 목표를 안 옮기고 혼합 잡음만 없앤다")
    out["🔴 축"] = "C3"
    out["사전등록"] = "docs/prereg_981_pick.md §3-4"
    out["🔴🔴 정본 자"] = canon
    out["🔴 격자"] = NB_GRID
    out["🔴 복제 수(BOOT_D · 사전등록 §8)"] = BOOT_D
    out["🔴 팔 셋"] = [ARM_C, "㉮ 층화(유보 목표)", ARM_PLACEBO]
    out["🔴🔴 가르는 논리"] = (
        "㉱ 는 대조 팔이 «기댓값에서 이미 맞추고 있는» 공급 혼합을 목표로 하므로 "
        "목표 이동이 0 이고 «혼합 표집 잡음»만 없앤다. "
        "㉱ 의 이득이 작은 예산에서 크고 큰 예산에서 죽으면 수렴 설명이 산다. "
        "어느 예산에서도 0 근처면 수렴 설명이 죽고 남는 것은 목표 이동이다")
    out["🔴🔴🔴 칸"] = cells
    out["🔴🔴🔴 분해"] = dec
    out["🔴 예측 채점"] = pred
    out["통과"] = bool(len(cells) == len(NB_GRID))
    out["🔴 이 절의 `통과` 가 뜻하는 것"] = (
        "예산 격자 전 칸에서 팔 셋이 돌았다. 🔴 이 값은 어느 설명이 이겼는지와 무관하다")
    out["🔴 유보 지문"] = R9.ho_verdict(h0, R9.ho_stamp(pool))
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LO.SRC)
    (OUT / "out981_decomp.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    _prog("decomp 끝")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["target", "decomp"])
    ap.add_argument("--ref", required=True)
    a = ap.parse_args()
    r = {"target": stage_target, "decomp": stage_decomp}[a.stage](a.ref)
    print(json.dumps({"stage": a.stage, "통과": r.get("통과")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
