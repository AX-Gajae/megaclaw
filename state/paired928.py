# -*- coding: utf-8 -*-
"""팔 928-ㄴㄴ — **짝지은 검정과 순열 200뽑기**.

사전등록: `docs/prereg_928_paired.md` (티처 #74 C1 · C3 · M3).

🔴 이 모듈이 지키는 것
  · `state/interval918.py` · `state/perm922.py` · `state/gap925.py` 를 **한 줄도 안 고친다**. 읽어 온다.
  · 빠른 경로(`improvement_rows`)가 `runners/gap925_run.world_pack` + `stat` 과
    **비트로 같은 수**를 내는지 러너의 S8 이 확인한다. 안 같으면 멈춘다.
  · 짝지음의 전제(두 세계의 `gi` 배열이 같다)를 **assert 로** 건다 — 조용히 안 넘어간다.
  · 분모 딱지(조항 60): 격자 ≠ 홀드아웃 격자 ≠ **간격이 있는 홀드아웃 격자** ≠ 행.
"""
from __future__ import annotations

import numpy as np

from state.interval918 import boot, fit_tables, predict
from state.gap925 import predict_grid_aware

#: 자의 두 팔 이름(925 §3 과 같다)
BASE = "가 기후값"
BASE_PRIME = "가′ 기후값+prevmed"
TEST = "나 조건부(주)"


def improvement_rows(tab, tr_set, ho_set, *, cal_off: bool, drop_first: bool,
                     base: str = BASE, test: str = TEST,
                     plant_no_drop: bool = False):
    """한 세계의 홀드아웃 **행별 개선 벡터**를 낸다(빠른 경로 — 두 팔만 계산).

    반환의 `imp` 는 `gap925_run.stat` 이 `boot` 에 넣는 것과 **같은 벡터**여야 한다.
    """
    trm = tr_set[tab["gi"]]
    hom = ho_set[tab["gi"]]
    T = fit_tables(tab, trm, plant_const_cal=cal_off)
    gap = tab["gap"][hom].astype(float)

    def arm_err(name):
        if name == BASE_PRIME:
            p, _ = predict_grid_aware(tab, hom, T)
        else:
            p, _ = predict(tab, hom, T, arm=name)
        return np.abs(gap - p)

    eb = arm_err(base)
    et = arm_err(test)
    sub = np.ones(gap.size, bool)
    if drop_first and not plant_no_drop:
        sub = np.isfinite(tab["prevmed"][hom])
    gi = tab["gi"][hom][sub]
    return {
        "자": f"MAE({base}) − MAE({test})",
        "imp": (eb - et)[sub],
        "gi": gi,
        "행(간격) 수": int(sub.sum()),
        "군집(격자) 수": int(np.unique(gi).size),
        "개선(일)": float((eb - et)[sub].mean()),
        "그 판의 기준 팔 MAE": float(eb[sub].mean()),
        "그 판의 시험 팔 MAE": float(et[sub].mean()),
        "_sub": sub, "_hom": hom, "_T": T,
    }


def paired(a: dict, b: dict, *, B: int = 2000, seed: int = 918,
           plant_roll: bool = False) -> dict:
    """🔴 **차이 자체를 군집 부트**한다 — 두 구간의 겹침을 보지 않는다.

    전제: 두 세계가 **같은 행 · 같은 격자 배열** 위에 있다. 아니면 `AssertionError`.
    `plant_roll=True` 는 심은 결함 W2 — 귀무 쪽 행을 한 칸 굴려 짝을 깬다.
    """
    assert a["imp"].size == b["imp"].size, (a["imp"].size, b["imp"].size)
    assert np.array_equal(a["gi"], b["gi"]), "🔴 두 세계의 행 격자 배열이 다르다 — 짝이 아니다"
    y = np.roll(b["imp"], 1) if plant_roll else b["imp"]
    d = a["imp"] - y
    bb = boot(d, a["gi"], B=B, seed=seed)
    return {
        "짝지은 차(일)": bb["점추정"], "BCa": [bb["lo"], bb["hi"]],
        "판정": bb["판정"], "구간 종류": bb["구간 종류"], "🔴 폴백 사유": bb["🔴 폴백 사유"],
        "반폭": bb["🔴 반폭(=MDE 자리)"], "B": bb["B"],
        "행(간격) 수": bb["행(간격) 수"], "군집(격자) 수": bb["군집(격자) 수"],
        "🔴 점추정 차 = 두 평균의 차인가(항등 확인)":
            bool(abs(bb["점추정"] - (a["개선(일)"] - b["개선(일)"])) < 1e-12) if not plant_roll else None,
        "🔴 효과 ÷ 반폭(티처 C3 이 요구한 형태)":
            (bb["점추정"] / bb["🔴 반폭(=MDE 자리)"]) if bb["🔴 반폭(=MDE 자리)"] else None,
    }


def perm_p(real: float, nulls) -> dict:
    """🔴 **진짜의 순위로** p 를 낸다. `p = (1 + #{귀무 ≥ 진짜}) / (1 + B)`."""
    x = np.asarray([v for v in nulls], float)
    fin = np.isfinite(x)
    b = int(fin.sum())
    ge = int((x[fin] >= real).sum())
    mu = float(x[fin].mean())
    sd0 = float(x[fin].std(ddof=0))
    sd1 = float(x[fin].std(ddof=1))
    return {
        "진짜": float(real),
        "🔴 뽑기 수 B(성공한 것만 · 분모)": b,
        "🔴 버려진 뽑기(NaN·예외)": int((~fin).sum()),
        "🔴 귀무 ≥ 진짜 인 뽑기 수 k": ge,
        "🔴 순열 p = (1+k)/(1+B)": (1.0 + ge) / (1.0 + b),
        "🔴 이 B 로 낼 수 있는 최소 p": 1.0 / (1.0 + b),
        "귀무 평균": mu, "귀무 SD(ddof=0)": sd0, "귀무 SD(ddof=1)": sd1,
        "귀무 최소": float(x[fin].min()), "귀무 최대": float(x[fin].max()),
        "귀무 분위(1·5·50·95·99%)": [float(np.percentile(x[fin], q))
                                 for q in (1, 5, 50, 95, 99)],
        "🔴 z = (진짜 − 귀무평균) ÷ 귀무SD(ddof=1)": (real - mu) / sd1 if sd1 else None,
        "🔴 효과(진짜 − 귀무평균 · 일)": real - mu,
        "🔴 효과(분)": (real - mu) * 24 * 60,
    }
