# -*- coding: utf-8 -*-
"""팔 935 — **원판(`cal_off=False` · `drop_first=False`)에서 200뽑기**.

사전등록: `docs/prereg_935_rawpanel.md` (티처 #76 의 **2순위** · 3순위를 판정 ② 로 붙였다).

🔴 이 모듈이 지키는 것
  · `state/interval918.py` · `state/perm922.py` · `state/gap925.py` · `state/paired928.py` ·
    `state/calpanel933.py` 를 **한 줄도 안 고친다.** 읽어 온다.
  · `rows_pair` 는 표를 **한 번만** 적합하고 두 팔(전체 · `b_prv=−1` 제외)을 같은 표에서 낸다.
    🔴 그 둘이 `paired928.improvement_rows` 의 (drop_first=False / True) 와 **비트로 같은 개선**을
    내야 하고, 러너가 그것을 검사한다(W2). 안 같으면 멈춘다.
  · 🔴 **오라클 천장은 LOO(자기 행 제외)로 낸다** — `docs/목표.md` 규율 4 ㉮ (티처 #76 C2·C3).
    자기 행 포함 값은 **진단으로만** 싣는다. 그리고 층마다 **식별 가능성**(㉯)을 같이 신고한다.
  · 분모 딱지(조항 60): 격자 ≠ 홀드아웃 격자 ≠ 간격이 있는 홀드아웃 격자 ≠ 행 ≠ 칸.
"""
from __future__ import annotations

import numpy as np

from state.interval918 import _bin, predict
from state.paired928 import BASE, TEST
from state.calpanel933 import fit_tables_x

#: 이 팔의 두 판(사전등록 §1). 🔴 이름을 코드와 산출물이 공유한다.
PANEL_ALL = "① 원판 전량"
PANEL_EXC = "② 원판 − b_prv=−1 칸"
PANEL_ONLY = "진단 b_prv=−1 칸만"


# ─────────────────────────────────────────────── 한 세계 · 한 번 적합 · 세 갈래


def _pack(gap, eb, et, gi, sub, T, back_t, *, label):
    imp = (eb - et)[sub]
    g = gi[sub]
    return {
        "판": label,
        "자": f"MAE({BASE}) − MAE({TEST})",
        "imp": imp, "gi": g,
        "행(간격) 수": int(sub.sum()),
        "군집(격자) 수": int(np.unique(g).size),
        "개선(일)": float(imp.mean()) if imp.size else float("nan"),
        "그 판의 기준 팔 MAE": float(eb[sub].mean()) if imp.size else float("nan"),
        "그 판의 시험 팔 MAE": float(et[sub].mean()) if imp.size else float("nan"),
        "prevmed 3분위 경계": list(T["prevmed 3분위 경계"]),
        "mag 3분위 경계": list(T["mag 3분위 경계"]),
        "전체 중앙값": T["전체 중앙값"],
        "학습 간격 수(분모)": T["학습 간격 수(분모)"],
        "🔴 3수준 셀 가짓수": T["🔴 3수준 셀 가짓수"],
        "🔴 달력 셀 가짓수": T["🔴 달력 셀 가짓수"],
        "후퇴 회계(시험 팔)": back_t,
        "_T": T, "_sub": sub,
        "_gap_panel": gap[sub],
    }


def rows_pair(tab, tr_set, ho_set, *, cal_off: bool = False,
              force_prv_cuts=None, base: str = BASE, test: str = TEST) -> dict:
    """🔴 표를 **한 번만** 적합하고 세 갈래를 낸다 — 전체 · `b_prv=−1` 제외 · 그 칸만.

    `b_prv=−1` 은 `interval918._bin` 의 「모름」 칸이고, `prevmed` 가 NaN 인 행
    (= 그 격자의 **첫 간격**) 과 정확히 같다. 러너의 W3 이 그 동치를 검사한다.
    """
    trm = tr_set[tab["gi"]]
    hom = ho_set[tab["gi"]]
    T = fit_tables_x(tab, trm, plant_const_cal=cal_off, force_prv_cuts=force_prv_cuts)
    gap = tab["gap"][hom].astype(float)
    pb, back_b = predict(tab, hom, T, arm=base)
    pt, back_t = predict(tab, hom, T, arm=test)
    eb = np.abs(gap - pb)
    et = np.abs(gap - pt)
    gi = tab["gi"][hom]
    prv = tab["prevmed"][hom]
    bp = np.asarray([_bin(v, T["prevmed 3분위 경계"]) for v in prv], int)
    fin = np.isfinite(prv)
    all_m = np.ones(gap.size, bool)
    out = {
        PANEL_ALL: _pack(gap, eb, et, gi, all_m, T, back_t, label=PANEL_ALL),
        PANEL_EXC: _pack(gap, eb, et, gi, fin, T, back_t, label=PANEL_EXC),
        PANEL_ONLY: _pack(gap, eb, et, gi, ~fin, T, back_t, label=PANEL_ONLY),
        "🔴 b_prv=−1 과 prevmed 결측이 같은 행인가": bool(np.array_equal(bp == -1, ~fin)),
        "b_prv 칸별 행 수": {str(int(k)): int((bp == k).sum())
                        for k in (-1, 0, 1, 2)},
        "🔴 경계를 강제했나": force_prv_cuts is not None,
        "_hom": hom, "_trm": trm, "_tab": tab, "_bp": bp, "_gap_ho": gap,
    }
    return out


def multiset_same(a: dict, b: dict) -> dict:
    """🔴 **정답 다중집합 동일성**. 판 ① 에서는 참이어야 하고 판 ② 에서는 원리상 깨진다."""
    pa, pb = np.sort(a["_gap_panel"]), np.sort(b["_gap_panel"])
    return {
        "🔴 같은가": bool(pa.size == pb.size and np.array_equal(pa, pb)),
        "행 수": [int(pa.size), int(pb.size)],
        "정답 평균": [float(pa.mean()), float(pb.mean())] if pa.size and pb.size else None,
        "정답 중앙값": [float(np.median(pa)), float(np.median(pb))] if pa.size and pb.size else None,
    }


def cmp_pack(rows: dict, tab: dict) -> dict:
    """`perm922.comparability` 가 먹는 모양(933 의 `cmp_pack` 과 같은 열)."""
    return {
        "가 기후값": {"MAE": rows["그 판의 기준 팔 MAE"]},
        "🔴 사건 수(분모 A)": tab["🔴 사건 수(분모 A)"],
        "🔴 간격 수(분모 B)": tab["🔴 간격 수(분모 B)"],
        "홀드아웃 간격 수(분모)": rows["행(간격) 수"],
        "홀드아웃 격자(군집) 수": rows["군집(격자) 수"],
        "표(학습)": {"학습 간격 수(분모)": rows["학습 간격 수(분모)"],
                  "mag 3분위 경계": rows["mag 3분위 경계"]},
        "간격 중앙값": float(np.median(tab["gap"])),
        "간격 평균": float(tab["gap"].mean()),
    }


# ─────────────────────────────────────── 오라클 천장 — 🔴 LOO 로 (규율 4 ㉮)


def _loo_median_sorted(ys: np.ndarray) -> np.ndarray:
    """정렬 없이 쓰지 마라. 각 원소를 뺀 나머지의 중앙값을 **O(m log m)** 로 낸다."""
    m = ys.size
    order = np.argsort(ys, kind="stable")
    x = ys[order]
    k = m - 1
    res = np.empty(m, float)
    if k <= 0:
        res[:] = np.nan
        return res
    if k % 2 == 1:                       # 남는 수가 홀수
        t = (k - 1) // 2
        for j in range(m):
            res[j] = x[t] if t < j else x[t + 1]
    else:                                # 남는 수가 짝수 → 두 개의 평균
        t1, t2 = k // 2 - 1, k // 2
        for j in range(m):
            a = x[t1] if t1 < j else x[t1 + 1]
            b = x[t2] if t2 < j else x[t2 + 1]
            res[j] = 0.5 * (a + b)
    out = np.empty(m, float)
    out[order] = res
    return out


def cell_oracle(y: np.ndarray, cell: np.ndarray, *, mode: str = "LOO",
                seed: int = 935, kfold: int = 5) -> dict:
    """칸 오라클. `mode` 는 **자기행포함 · LOO · 교차적합**.

    🔴 `자기행포함` 은 **암기다**(티처 #76 C2). 판정에는 `LOO` 를 쓴다.
    칸 하나에 행이 하나뿐이면 그 행은 **전체 LOO 중앙값**으로 물러선다(그 수를 신고한다).
    """
    y = np.asarray(y, float)
    cell = np.asarray(cell)
    pred = np.empty(y.size, float)
    uq, inv = np.unique(cell, return_inverse=True)
    singleton = 0
    if mode == "자기행포함":
        for c in range(uq.size):
            m = inv == c
            pred[m] = np.median(y[m])
    elif mode == "LOO":
        gl = _loo_median_sorted(y)       # 전체 LOO 중앙값(칸 크기 1 의 후퇴처)
        for c in range(uq.size):
            m = inv == c
            ys = y[m]
            if ys.size < 2:
                pred[m] = gl[m]
                singleton += int(ys.size)
                continue
            pred[m] = _loo_median_sorted(ys)
    elif mode == "교차적합":
        rng = np.random.default_rng(seed)
        fold = rng.integers(0, kfold, size=y.size)
        gmed_all = float(np.median(y))
        for f in range(kfold):
            te = fold == f
            tr = ~te
            for c in range(uq.size):
                m_te = te & (inv == c)
                if not m_te.any():
                    continue
                m_tr = tr & (inv == c)
                if not m_tr.any():
                    pred[m_te] = float(np.median(y[tr])) if tr.any() else gmed_all
                    singleton += int(m_te.sum())
                    continue
                pred[m_te] = float(np.median(y[m_tr]))
    else:
        raise ValueError(mode)
    return {"MAE": float(np.abs(y - pred).mean()), "칸 수": int(uq.size),
            "칸당 평균 행": float(y.size / uq.size),
            "🔴 후퇴한 행(칸에 자기 말고 없다)": int(singleton),
            "모드": mode}


def identifiability(cell_ho: np.ndarray, cell_tr: np.ndarray) -> dict:
    """🔴 규율 4 ㉯ — **그 층의 모수가 학습에서 식별 가능한가**.

    격자 층은 분할이 격자 기준 70/30 이라 **원리상 0** 이다(티처 #76 C2).
    """
    ho_u = np.unique(cell_ho)
    tr_u = np.unique(cell_tr)
    seen = np.isin(cell_ho, tr_u)
    return {
        "홀드아웃 칸 수": int(ho_u.size),
        "학습 칸 수": int(tr_u.size),
        "🔴 학습에도 있는 홀드아웃 칸 수": int(np.isin(ho_u, tr_u).sum()),
        "🔴 학습에 있는 칸에 속한 홀드아웃 행 비율": float(seen.mean()),
        "🔴 식별 가능한가(행 비율 ≥ 0.5)": bool(seen.mean() >= 0.5),
    }


def _cells(tab, mask, T, *, cal_off: bool):
    """층마다 쓸 칸 id 를 한 자리에서 만든다 — 🔴 학습·홀드아웃이 **같은 규칙**이어야 한다."""
    dow = tab["dow"][mask].astype(int)
    qtr = tab["quarter"][mask].astype(int)
    if cal_off:
        dow = np.zeros_like(dow)
        qtr = np.zeros_like(qtr)
    prv = tab["prevmed"][mask]
    mag = tab["mag"][mask]
    bp = np.asarray([_bin(v, T["prevmed 3분위 경계"]) for v in prv], int)
    bm = np.asarray([_bin(v, T["mag 3분위 경계"]) for v in mag], int)
    return {
        "① 시험 팔의 칸 구조(dow·quarter·b_prv·b_mag)":
            (dow * 4 + qtr) * 100 + (bp + 1) * 10 + (bm + 1),
        "② prevmed 실수값": np.where(np.isfinite(prv), prv, -1.0),
        "③ 격자 정체": tab["gi"][mask].astype(np.int64),
    }


def oracle_layers(rows: dict, sub_key: str, *, cal_off: bool, label: str,
                  size_x: float = 1.0) -> dict:
    """🔴 **층마다** 오라클 천장을 LOO 로 내고 식별 가능성을 붙인다 (규율 4 ㉮·㉯).

    반환의 `🔴 판정용 Y` 는 **① 층의 LOO** 다 — 시험 팔이 실제로 쓰는 칸 구조.
    """
    r = rows[sub_key]
    tab = rows["_tab"]
    hom = rows["_hom"]
    sub = r["_sub"]
    T = r["_T"]
    y = r["_gap_panel"]
    base_mae = r["그 판의 기준 팔 MAE"]

    ho_mask = np.zeros(tab["gi"].size, bool)
    ho_mask[np.flatnonzero(hom)[sub]] = True
    tr_mask = rows["_trm"]

    ho_cells = _cells(tab, ho_mask, T, cal_off=cal_off)
    tr_cells = _cells(tab, tr_mask, T, cal_off=cal_off)

    med = float(np.median(y))
    grid_int = np.arange(1, 61, dtype=float)
    maes = np.abs(y[None, :] - grid_int[:, None]).mean(axis=1)
    kb = int(np.argmin(maes))

    layers = {}
    for name in ho_cells:
        c_ho = ho_cells[name]
        c_tr = tr_cells[name]
        o_self = cell_oracle(y, c_ho, mode="자기행포함")
        o_loo = cell_oracle(y, c_ho, mode="LOO")
        o_cf = cell_oracle(y, c_ho, mode="교차적합")
        ident = identifiability(c_ho, c_tr)
        layers[name] = {
            "칸 수": o_self["칸 수"], "칸당 평균 행": o_self["칸당 평균 행"],
            "🔴 층으로 셀 자격이 있나(칸당 행 ≥ 10 · 규율 4 개정문)":
                bool(o_self["칸당 평균 행"] >= 10.0),
            "자기행포함 개선(일) — 🔴 암기 · 진단으로만": base_mae - o_self["MAE"],
            "🔴 LOO 개선(일) — 판정용": base_mae - o_loo["MAE"],
            "교차적합(5겹) 개선(일)": base_mae - o_cf["MAE"],
            "LOO 후퇴한 행": o_loo["🔴 후퇴한 행(칸에 자기 말고 없다)"],
            "🔴 식별 가능성(규율 4 ㉯)": ident,
            "🔴 이 층을 천장으로 쓸 수 있나":
                bool(ident["🔴 식별 가능한가(행 비율 ≥ 0.5)"]
                     and o_self["칸당 평균 행"] >= 10.0),
        }
    Y = layers["① 시험 팔의 칸 구조(dow·quarter·b_prv·b_mag)"]["🔴 LOO 개선(일) — 판정용"]
    usable = {k: v["🔴 LOO 개선(일) — 판정용"] for k, v in layers.items()
              if v["🔴 이 층을 천장으로 쓸 수 있나"]}
    return {
        "판": label,
        "행(분모)": int(y.size),
        "군집(격자) 수": r["군집(격자) 수"],
        "기준 팔 MAE(실제로 쓰는 팔)": base_mae,
        "시험 팔 MAE": r["그 판의 시험 팔 MAE"],
        "진짜 개선(일)": r["개선(일)"],
        "🔴 홀드아웃 최적 상수(중앙값)": med,
        "그 상수의 MAE": float(np.abs(y - med).mean()),
        "🔴 기준 팔이 이미 홀드아웃 최적 상수인가":
            bool(abs(float(np.abs(y - med).mean()) - base_mae) < 1e-12),
        "정수 1~60 전수 탐색 최적": float(grid_int[kb]), "그 MAE": float(maes[kb]),
        "층": layers,
        "④ 완전 오라클(행마다 답) — 🔴 층이 아니다(분할 단조성의 반례)": base_mae,
        "🔴 판정용 Y(= ① 층의 LOO)": Y,
        "🔴 쓸 수 있는 층 중 최고 천장": (max(usable.values()) if usable else None),
        "🔴🔴 규율 4": {
            "채택 크기 X(일 · 개선 눈금 · docs/목표.md ③ — 이 사이클이 고르지 않았다)": size_x,
            "오라클 천장 Y(일 · 개선 눈금 · LOO)": Y,
            "🔴 X/Y = Z": (size_x / Y) if Y and Y > 0 else None,
            "🔴 Z > 1 인가(= 이 자로는 원리상 못 넘는다)":
                bool(Y is None or Y <= 0 or size_x / Y > 1.0),
        },
        "🔴 못 넘는 것": "LOO 는 상한의 추정이지 상한 자체가 아니다(티처 #76 의 자기 딱지) — "
                   "자기행포함 값과 LOO 값 사이에 참값이 있다. 판정은 보수적인 쪽(LOO)으로 낸다",
    }


# ─────────────────────────────────────── 판정 문턱의 동치 조건 (🔴 러너가 계산한다)


def p_equivalence(alpha: float, ndraw: int) -> dict:
    """🔴 `p < alpha` 의 **k 동치 조건을 손으로 안 적는다**(933 자기적발 ①).

    `p = (1+k)/(1+B)` 이므로 조건은 `k < alpha*(1+B) − 1`.
    """
    b = int(ndraw)
    kmax = -1
    for k in range(0, b + 1):
        if (1.0 + k) / (1.0 + b) < alpha:
            kmax = k
        else:
            break
    return {
        "α": alpha, "B": b,
        "🔴 이 B 로 낼 수 있는 최소 p": 1.0 / (1.0 + b),
        "🔴 p < α 의 동치 조건": ("k ≤ %d" % kmax) if kmax >= 0 else "🔴 없다 — 어떤 k 로도 못 넘는다",
        "k 최대": kmax,
        "그 k 에서의 p": (1.0 + kmax) / (1.0 + b) if kmax >= 0 else None,
        "다음 k 에서의 p": (2.0 + kmax) / (1.0 + b) if kmax >= 0 else None,
    }


def empirical_power_k(pilot: np.ndarray, real: float, shape: np.ndarray,
                      *, ndraw: int, alpha: float = 0.01) -> dict:
    """🔴 경험분포 검출력 (정규 근사 금지 · 이슈 #180) — **k ≤ kmax 를 그대로 쓴다**.

    933 은 `k=0` 만 셌고(자기적발 ①) 그래서 신고값이 **하한**이었다. 여기서는
    `p_equivalence` 가 낸 `kmax` 로 이항 꼬리를 그대로 더한다.
    """
    from math import comb
    pilot = np.asarray(pilot, float)
    shape = np.asarray(shape, float)
    mu, sd = float(pilot.mean()), float(pilot.std(ddof=1))
    D = (real - mu) / sd if sd else float("inf")
    zs = (shape - shape.mean()) / shape.std(ddof=1)
    n_ge = int((zs >= D).sum())
    q = (1.0 + n_ge) / (1.0 + zs.size)
    eq = p_equivalence(alpha, ndraw)
    kmax = eq["k 최대"]
    pw = 0.0
    if kmax >= 0:
        for k in range(0, kmax + 1):
            pw += comb(ndraw, k) * (q ** k) * ((1.0 - q) ** (ndraw - k))
    return {
        "🔴 방법": "파일럿으로 위치·폭 · 앞선 200뽑기의 표준화 경험분포로 꼬리확률 q̂ · "
                "그 뒤 이항 꼬리 P(k ≤ kmax). 정규 근사 안 씀",
        "파일럿 수": int(pilot.size), "파일럿 평균": mu, "파일럿 SD(ddof=1)": sd,
        "파일럿 최소": float(pilot.min()), "파일럿 최대": float(pilot.max()),
        "진짜": float(real),
        "🔴 표준화 거리 D": D,
        "shape 표본 수": int(zs.size), "shape 표준화 최대": float(zs.max()),
        "🔴 shape 에서 D 이상인 개수": n_ge,
        "🔴 꼬리확률 q̂ = (1+개수)/(1+n)": q,
        "🔴 동치 조건(러너가 계산)": eq,
        "🔴 검출력 = P(k ≤ %d)" % kmax: float(pw),
        "🔴 추정 해상도의 천장(q̂ 가 바닥일 때)": float(sum(
            comb(ndraw, k) * ((1.0 / (1.0 + shape.size)) ** k)
            * ((1.0 - 1.0 / (1.0 + shape.size)) ** (ndraw - k))
            for k in range(0, max(kmax, 0) + 1))),
        "🔴 못 넘는 것": "파일럿 %d개는 q 를 아래로 못 묶는다 — shape 을 빌려 왔다는 것이 이 계산의 전제다"
                    % int(pilot.size),
    }
