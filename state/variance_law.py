"""축 분산과 예측력의 관계 --- 노트 11의 반증 조건.

노트 11은 굿즈 규모 축 하나에서 이렇게 관측했다. 2019~2021년 데뷔 앨범은 거의 모두
1~2종이라 축 표준편차가 0.154였고 그 구간에서 전이가 무효였다. 버전 경쟁이 벌어진
2025년 이후에는 표준편차가 0.231로 늘고 전이가 강해졌다.

그 노트의 반증 조건은 이렇다.

    다른 축에서도 같은 패턴이 보여야 한다. 축의 구간 내 표준편차와 그 구간의 전이
    성적이 상관되지 않으면 이 설명은 이 축 하나에만 해당하는 우연이다.

설계. 두 도메인 × 세 축 × 여러 부분모집단으로 셀을 만들고, 각 셀에서
  (a) 그 셀 안에서 축이 얼마나 변하는가 (표준편차)
  (b) 그 셀에서 축이 결과를 얼마나 예측하는가 (상수 대비 MAE 차이)
를 재서 (a)와 (b)의 상관을 본다. 음의 상관이면 원리가 일반화된다.

부분모집단은 도메인마다 자연스러운 축으로 나눈다.
  · 아이돌 --- 데뷔 연도 구간
  · 팝업   --- 개최 시기 구간

축이 상수에 가까운 셀에서는 계수가 옳아도 예측이 되지 않는다는 것이 주장이므로,
셀 안에서 학습하지 않고 **다른 도메인에서 배운 계수를 그대로 적용**한다.
셀 안에서 학습하면 분산이 작을 때 과적합으로 오히려 좋아 보일 수 있다.

사용: python3 -m state.variance_law
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge

import state.transfer_axes as T
from .slots import load_popup

SEED = 20260728
AXES3 = ["target_breadth", "media_push", "goods_scale"]
KO = {"target_breadth": "타깃 폭", "media_push": "미디어 투입", "goods_scale": "굿즈 규모"}
ALL = ["target_breadth", "venue_prominence", "entry_friction", "media_push", "goods_scale"]


def z(v):
    v = np.asarray(v, float)
    return (v - v.mean()) / (v.std() + 1e-9)


def popup_axis(ax: str):
    X, y, w, A, M, g, t, cols = load_popup()
    j = ALL.index(ax)
    keep = M[:, j] > 0.5
    yr = np.array([int(s[:4]) if s and s[:4].isdigit() else 0 for s in t[keep]])
    return z(A[keep][:, j]), z(y[keep]), yr


def idol_axis(ax: str):
    d = json.loads(Path("data/state/idol_axes.json").read_text())
    rows = [v for v in d.values() if v["mask"][ax]]
    a = np.array([v["axes"][ax] for v in rows])
    y = np.array([v["y"] for v in rows])
    yr = np.array([int((v["debut_date"] or "0")[:4]) if (v["debut_date"] or "")[:4].isdigit()
                   else 0 for v in rows])
    return z(a), z(y), yr


def cells(bins=((0, 2021), (2022, 2024), (2025, 9999)), min_n: int = 10):
    """(도메인, 축, 구간) 셀마다 축 표준편차와 교차 적용 성적을 낸다."""
    out = []
    for ax in AXES3:
        ap, yp, tp = popup_axis(ax)
        ai, yi, ti = idol_axis(ax)
        if len(ap) < 20 or len(ai) < 20:
            continue
        # 각 방향의 계수는 **상대 도메인 전체**에서 배운다 (셀 안에서 학습하지 않는다)
        cp = Ridge(alpha=1.0).fit(ap.reshape(-1, 1), yp)
        ci = Ridge(alpha=1.0).fit(ai.reshape(-1, 1), yi)
        for dom, a, y, t, model in (("팝업", ap, yp, tp, ci), ("아이돌", ai, yi, ti, cp)):
            for lo, hi in bins:
                s = (t >= lo) & (t <= hi)
                if s.sum() < min_n:
                    continue
                base = np.abs(np.median(y[s]) - y[s]).mean()
                d = float(np.abs(model.predict(a[s].reshape(-1, 1)) - y[s]).mean() - base)
                out.append({"도메인": dom, "축": KO[ax], "구간": f"{lo}-{hi}",
                            "n": int(s.sum()), "축_SD": round(float(a[s].std()), 3),
                            "차이": round(d, 4)})
    return out


def run() -> dict:
    rows = cells()
    print(f"셀 {len(rows)}개 (도메인 × 축 × 구간)\n")
    print(f"{'도메인':<7}{'축':<11}{'구간':<12}{'n':>4}{'축 SD':>8}{'차이':>10}")
    for r in sorted(rows, key=lambda x: (x["축"], x["도메인"], x["구간"])):
        print(f"{r['도메인']:<7}{r['축']:<11}{r['구간']:<12}{r['n']:>4}"
              f"{r['축_SD']:>8.3f}{r['차이']:>+10.4f}")

    sd = np.array([r["축_SD"] for r in rows])
    df = np.array([r["차이"] for r in rows])
    rho = float(np.corrcoef(sd, df)[0, 1])
    # 순위 상관도 함께 --- 셀이 적어 이상치에 민감하다
    from scipy.stats import spearmanr
    sr, sp = spearmanr(sd, df)
    print(f"\n축 SD × 차이   피어슨 r={rho:+.3f}   스피어만 ρ={sr:+.3f} (p={sp:.3f})")
    print("  음수면 '분산이 클수록 잘 예측한다' --- 노트 11의 원리가 일반화된다")

    out = {"cells": rows, "pearson": round(rho, 3),
           "spearman": round(float(sr), 3), "p": round(float(sp), 4)}
    Path("data/state/variance_law.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    run()
