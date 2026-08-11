# -*- coding: utf-8 -*-
"""팔 933 — **[달력제거] 판에서 200뽑기를 다시 돌린다** + **경계 강제 판**.

사전등록: `docs/prereg_933_calpanel.md` (티처 #75 C1·C2·C4·M1 · `docs/목표.md` 규율 4).

🔴 이 모듈이 지키는 것
  · `state/interval918.py` · `state/perm922.py` · `state/gap925.py` · `state/paired928.py` 를
    **한 줄도 안 고친다.** 읽어 온다.
  · `fit_tables_x` 는 `interval918.fit_tables` 의 **복사본에 주입 인자 하나**를 더한 것이다.
    🔴 주입을 안 하면(`force_prv_cuts=None`) 원본과 **비트로 같은 표**를 내야 하고,
    그것을 `fit_identity()` 가 검사한다. 안 같으면 러너가 멈춘다.
  · `rows_x(..., force_prv_cuts=None)` 은 `paired928.improvement_rows` 와 **비트로 같은 개선**을
    내야 하고, 그것도 러너가 검사한다.
  · 분모 딱지(조항 60): 격자 ≠ 홀드아웃 격자 ≠ 간격이 있는 홀드아웃 격자 ≠ 행.
"""
from __future__ import annotations

import numpy as np

from state.interval918 import CELL_MIN, _bin, _terciles, fit_tables, predict
from state.paired928 import BASE, TEST

# ─────────────────────────────────────────────── 표 적합 (경계 주입 가능)


def fit_tables_x(tab, tr_mask, *, plant_const_cal: bool = False,
                 force_prv_cuts=None, force_mag_cuts=None):
    """🔴 `interval918.fit_tables` 의 복사본 + **3분위 경계 주입**.

    `force_prv_cuts=None` 이면 원본과 같은 표를 낸다(러너의 항등 검사가 확인한다).
    """
    gap = tab["gap"][tr_mask]
    dow = tab["dow"][tr_mask].astype(int)
    qtr = tab["quarter"][tr_mask].astype(int)
    if plant_const_cal:
        dow = np.zeros_like(dow)
        qtr = np.zeros_like(qtr)
    mag = tab["mag"][tr_mask]
    prv = tab["prevmed"][tr_mask]
    cuts_mag = _terciles(mag) if force_mag_cuts is None else tuple(force_mag_cuts)
    cuts_prv = _terciles(prv) if force_prv_cuts is None else tuple(force_prv_cuts)
    gmed = float(np.median(gap)) if gap.size else np.nan

    cal = {}
    for d in range(7):
        for q in range(4):
            m = (dow == d) & (qtr == q)
            if m.sum() >= CELL_MIN:
                cal[(d, q)] = float(np.median(gap[m]))
    b_mag = np.asarray([_bin(v, cuts_mag) for v in mag], int)
    b_prv = np.asarray([_bin(v, cuts_prv) for v in prv], int)
    lvl2, lvl3 = {}, {}
    for d in range(7):
        for q in range(4):
            base_m = (dow == d) & (qtr == q)
            if not base_m.any():
                continue
            for bp in (-1, 0, 1, 2):
                m2 = base_m & (b_prv == bp)
                if m2.sum() >= CELL_MIN:
                    lvl2[(d, q, bp)] = float(np.median(gap[m2]))
                for bm in (-1, 0, 1, 2):
                    m3 = m2 & (b_mag == bm)
                    if m3.sum() >= CELL_MIN:
                        lvl3[(d, q, bp, bm)] = float(np.median(gap[m3]))
    q10, q90 = (float(np.percentile(gap, 10)), float(np.percentile(gap, 90))) \
        if gap.size else (np.nan, np.nan)
    cal_iv, cond_iv = {}, {}
    for d in range(7):
        for q in range(4):
            m = (dow == d) & (qtr == q)
            if m.sum() >= CELL_MIN:
                cal_iv[(d, q)] = (float(np.percentile(gap[m], 10)),
                                  float(np.percentile(gap[m], 90)), int(m.sum()))
            for bp in (-1, 0, 1, 2):
                for bm in (-1, 0, 1, 2):
                    m3 = m & (b_prv == bp) & (b_mag == bm)
                    if m3.sum() >= CELL_MIN:
                        cond_iv[(d, q, bp, bm)] = (float(np.percentile(gap[m3], 10)),
                                                   float(np.percentile(gap[m3], 90)),
                                                   int(m3.sum()))
    return {"전체 중앙값": gmed, "달력 셀": cal, "2수준": lvl2, "3수준": lvl3,
            "mag 3분위 경계": cuts_mag, "prevmed 3분위 경계": cuts_prv,
            "학습 간격 수(분모)": int(gap.size),
            "🔴 달력 셀 가짓수": len(cal),
            "🔴 3수준 셀 가짓수": len(lvl3),
            "전체 10~90분위": (q10, q90),
            "달력 구간": cal_iv, "조건부 구간": cond_iv,
            "_plant_const_cal": bool(plant_const_cal)}


def _eqv(a, b) -> bool:
    """중첩 자료구조의 **비트 동일**(nan 은 nan 과 같다고 본다)."""
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_eqv(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(_eqv(x, y) for x, y in zip(a, b))
    if isinstance(a, float) and isinstance(b, float):
        return (a == b) or (np.isnan(a) and np.isnan(b))
    return bool(a == b)


def fit_identity(tab, tr_mask, *, plant_const_cal: bool) -> dict:
    """🔴 주입을 안 한 `fit_tables_x` 가 원본 `fit_tables` 와 같은 표를 내는가."""
    t0 = fit_tables(tab, tr_mask, plant_const_cal=plant_const_cal)
    t1 = fit_tables_x(tab, tr_mask, plant_const_cal=plant_const_cal)
    return {"🔴 같은가": _eqv(t0, t1),
            "원본 prevmed 경계": list(t0["prevmed 3분위 경계"]),
            "복사본 prevmed 경계": list(t1["prevmed 3분위 경계"]),
            "원본 3수준 셀 가짓수": t0["🔴 3수준 셀 가짓수"],
            "복사본 3수준 셀 가짓수": t1["🔴 3수준 셀 가짓수"]}


# ─────────────────────────────────────────────── 한 세계의 개선 + 진단


def rows_x(tab, tr_set, ho_set, *, cal_off: bool, drop_first: bool,
           force_prv_cuts=None, base: str = BASE, test: str = TEST) -> dict:
    """한 세계의 홀드아웃 개선 벡터 + 🔴 **뽑기마다 적으라고 한 진단 전량**.

    `force_prv_cuts=None` 이면 `paired928.improvement_rows` 와 비트로 같은 개선을 낸다.
    """
    trm = tr_set[tab["gi"]]
    hom = ho_set[tab["gi"]]
    T = fit_tables_x(tab, trm, plant_const_cal=cal_off, force_prv_cuts=force_prv_cuts)
    gap = tab["gap"][hom].astype(float)

    def arm_err(name):
        p, back = predict(tab, hom, T, arm=name)
        return np.abs(gap - p), back

    eb, back_b = arm_err(base)
    et, back_t = arm_err(test)
    sub = np.ones(gap.size, bool)
    if drop_first:
        sub = np.isfinite(tab["prevmed"][hom])
    gi = tab["gi"][hom][sub]
    imp = (eb - et)[sub]
    return {
        "자": f"MAE({base}) − MAE({test})",
        "imp": imp, "gi": gi,
        "행(간격) 수": int(sub.sum()),
        "군집(격자) 수": int(np.unique(gi).size),
        "개선(일)": float(imp.mean()),
        "그 판의 기준 팔 MAE": float(eb[sub].mean()),
        "그 판의 시험 팔 MAE": float(et[sub].mean()),
        # 🔴 티처 #75 C1 이 요구한 세 진단
        "prevmed 3분위 경계": list(T["prevmed 3분위 경계"]),
        "mag 3분위 경계": list(T["mag 3분위 경계"]),
        "전체 중앙값": T["전체 중앙값"],
        "🔴 경계를 강제했나": force_prv_cuts is not None,
        "학습 간격 수(분모)": T["학습 간격 수(분모)"],
        "🔴 3수준 셀 가짓수": T["🔴 3수준 셀 가짓수"],
        "🔴 달력 셀 가짓수": T["🔴 달력 셀 가짓수"],
        "후퇴 회계(시험 팔)": back_t,
        "_T": T, "_hom": hom, "_sub": sub,
        "_gap_panel": gap[sub], "_gap_ho": gap,
        "_tab": tab,
    }


def multiset_same(a: dict, b: dict) -> dict:
    """🔴 **정답 다중집합 동일성** — 티처 #75 C4 가 [달력제거]에서 True 라고 증명한 것."""
    pa, pb = np.sort(a["_gap_panel"]), np.sort(b["_gap_panel"])
    ha, hb = np.sort(a["_gap_ho"]), np.sort(b["_gap_ho"])
    return {
        "🔴 판 행의 정답 다중집합이 같은가": bool(pa.size == pb.size and np.array_equal(pa, pb)),
        "🔴 홀드아웃 전량의 정답 다중집합이 같은가": bool(ha.size == hb.size and np.array_equal(ha, hb)),
        "행 수": [int(pa.size), int(pb.size)],
        "정답 평균": [float(pa.mean()), float(pb.mean())],
        "정답 중앙값": [float(np.median(pa)), float(np.median(pb))],
    }


def cmp_pack(rows: dict, tab: dict) -> dict:
    """`perm922.comparability` 가 먹는 모양으로 싼다 — 🔴 **관문을 실제로 부르려고**."""
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


# ─────────────────────────────────────────────── 오라클 천장 (규율 4)


def _best_const(y: np.ndarray) -> tuple:
    """MAE 를 최소로 하는 상수 = 중앙값. 정수 1~60 전수 탐색도 같이 낸다."""
    med = float(np.median(y))
    grid = np.arange(1, 61, dtype=float)
    maes = np.abs(y[None, :] - grid[:, None]).mean(axis=1)
    k = int(np.argmin(maes))
    return med, float(np.abs(y - med).mean()), float(grid[k]), float(maes[k])


def _cell_oracle(y: np.ndarray, cell: np.ndarray) -> dict:
    """칸마다 **홀드아웃 답의 중앙값**을 쓴다(= 그 칸 구조의 MAE 하한)."""
    pred = np.empty(y.size, float)
    uq = np.unique(cell)
    for c in uq:
        m = cell == c
        pred[m] = np.median(y[m])
    return {"MAE": float(np.abs(y - pred).mean()), "칸 수": int(uq.size)}


def oracle_ceiling(rows: dict, *, label: str) -> dict:
    """🔴 **이 자의 오라클 천장** — 규율 4 (`docs/목표.md` · 티처 #75 C3).

    조건 열을 알고 **홀드아웃 답으로** 최적 적합했을 때의 개선. 층을 넷으로 낸다.
    """
    T = rows["_T"]
    hom, sub = rows["_hom"], rows["_sub"]
    tab = rows["_tab"]
    y = rows["_gap_panel"]
    prv = tab["prevmed"][hom][sub]
    mag = tab["mag"][hom][sub]
    gi = rows["gi"]
    dow = tab["dow"][hom][sub].astype(int)
    qtr = tab["quarter"][hom][sub].astype(int)
    if T.get("_plant_const_cal"):
        dow = np.zeros_like(dow)
        qtr = np.zeros_like(qtr)
    bp = np.asarray([_bin(v, T["prevmed 3분위 경계"]) for v in prv], int)
    bm = np.asarray([_bin(v, T["mag 3분위 경계"]) for v in mag], int)

    base_mae = rows["그 판의 기준 팔 MAE"]
    med, med_mae, kbest, kbest_mae = _best_const(y)
    cell1 = (dow * 4 + qtr) * 100 + (bp + 1) * 10 + (bm + 1)      # 시험 팔의 칸 구조
    o1 = _cell_oracle(y, cell1)
    prv_i = np.where(np.isfinite(prv), prv, -1.0)
    o2 = _cell_oracle(y, np.unique(prv_i, return_inverse=True)[1])
    o3 = _cell_oracle(y, gi)
    return {
        "판": label,
        "행(분모)": int(y.size),
        "기준 팔 MAE(실제로 쓰는 팔)": base_mae,
        "🔴 홀드아웃 최적 상수(중앙값)": med,
        "그 상수의 MAE": med_mae,
        "🔴 기준 팔이 이미 홀드아웃 최적 상수인가": bool(abs(med_mae - base_mae) < 1e-12),
        "정수 1~60 전수 탐색 최적": kbest, "그 MAE": kbest_mae,
        "① 시험 팔의 칸 구조(dow·quarter·b_prv·b_mag) 오라클": {
            **o1, "🔴 개선(일) = 기준 MAE − 오라클 MAE": base_mae - o1["MAE"]},
        "② prevmed 실수값 칸 오라클": {
            **o2, "개선(일)": base_mae - o2["MAE"]},
        "③ 격자 정체 칸 오라클": {
            **o3, "개선(일)": base_mae - o3["MAE"]},
        "④ 완전 오라클(행마다 답)": {"MAE": 0.0, "개선(일)": base_mae},
        "🔴 이 자의 오라클 천장 Y(= ①)": base_mae - o1["MAE"],
        "🔴 못 넘는 것": "오라클은 홀드아웃 답을 보고 적합한다 — 실제 팔은 이 수를 원리상 못 넘는다",
    }


# ─────────────────────────────────────────────── 검출력 (🔴 정규 근사 금지)


def empirical_power(pilot: np.ndarray, real: float, shape: np.ndarray,
                    *, ndraw: int, alpha: float = 0.01) -> dict:
    """🔴 **경험분포로** 검출력을 낸다 (928 자기적발 ① · 이슈 #180).

    ① 파일럿 뽑기로 이 판 귀무의 **위치·폭**만 잰다(정규 가정 없음).
    ② 앞선 사이클의 200뽑기(`shape`)를 표준화한 **경험 분포**로 꼬리확률 q 를 읽는다.
    ③ p<0.01 은 200뽑기에서 **k=0** 과 동치이므로 검출력 = (1−q)^ndraw.
    """
    pilot = np.asarray(pilot, float)
    shape = np.asarray(shape, float)
    mu, sd = float(pilot.mean()), float(pilot.std(ddof=1))
    D = (real - mu) / sd if sd else float("inf")
    zs = (shape - shape.mean()) / shape.std(ddof=1)
    n_ge = int((zs >= D).sum())
    q_hat = (1.0 + n_ge) / (1.0 + zs.size)          # 🔴 순위식 — 0 이 안 나온다
    min_p = 1.0 / (1.0 + ndraw)
    return {
        "🔴 방법": "파일럿으로 위치·폭 · 앞선 200뽑기의 표준화 경험분포로 꼬리확률. 정규 근사 안 씀",
        "파일럿 수": int(pilot.size), "파일럿 평균": mu, "파일럿 SD(ddof=1)": sd,
        "파일럿 최소": float(pilot.min()), "파일럿 최대": float(pilot.max()),
        "진짜": float(real),
        "🔴 표준화 거리 D = (진짜 − 파일럿평균) ÷ 파일럿SD": D,
        "shape 표본 수": int(zs.size),
        "shape 표준화 최대": float(zs.max()),
        "🔴 shape 에서 D 이상인 개수": n_ge,
        "🔴 꼬리확률 q̂ = (1+개수)/(1+n)": q_hat,
        "🔴 이 뽑기 수로 낼 수 있는 최소 p": min_p,
        "🔴 p<%.2f 는 k=0 과 동치인가" % alpha: bool(min_p < alpha <= 2 * min_p),
        "🔴 검출력 = (1−q̂)^%d" % ndraw: float((1.0 - q_hat) ** ndraw),
        "🔴 못 넘는 것": "파일럿 %d개는 q 를 아래로 못 묶는다 — shape 을 빌려 왔다는 것이 이 계산의 전제다"
                    % int(pilot.size),
    }
