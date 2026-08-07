"""순위를 절대 방문자 수로 --- 눈금 보정을 여섯 도메인에서 다시 잰다.

노트 58이 제품 수치를 냈다. 팝업 라벨을 전혀 쓰지 않고 예측 상위 20\\%가 860명,
하위 20\\%가 157명으로 5.5배 갈린다. 그런데 그것은 **순위**다. 예측값에는 눈금이
없어서 ``이 기획은 몇 명''을 말하지 못한다.

노트 26과 32에서 절차를 세웠다 --- 대상 도메인 몇 건을 실제로 재서 중심과
산포를 맞춘다. 도메인이 셋일 때 8건이면 눈금이 잡히고 50건이 있어야 문턱 판정이
된다고 했다. 여섯 도메인에서 다시 잰다.

**절차**

  1. 팝업에서 보정용 k건을 뽑는다(층화 무작위).
  2. 나머지에서 예측 순위를 낸다 --- 여기에는 팝업 라벨이 전혀 안 들어간다.
  3. 보정용 k건의 실제 라벨로 중심(중앙값)과 산포(MAD×1.4826)를 잡는다.
  4. 예측을 표준화한 뒤 그 중심·산포로 편다.
  5. 남은 건에서 절대 오차를 잰다.

**기울기 축소.** 예측과 실제의 상관이 $\\rho$면 최적 산포는 $\\rho\\times$실제 산포
근처다(회귀 축소, 노트 42). k건에서 상관을 추정해 곱한다. k가 작으면 추정이
튀므로 1로 축소한다 --- $w=k/(k+\\lambda)$, $\\lambda=6$(노트 32).

**비교 기준**은 ``보정용 k건의 중앙값을 전부에 쓴다''이다. 그것이 모델 없이
같은 k건으로 할 수 있는 최선이다.

사용: python3 -m state.calibrate6
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge

from .own_axes import extend
from .procrustes import align_pair, factor_space
from .rank_test import spearman
from .slots import load_popup
from .tri_domain import load_all

OUT = Path("data/state/calibrate6.json")
SEED = 20260729
LAM = 6.0


def popup_pred():
    """다섯 도메인에서 배운 팝업 예측(표준화). 팝업 라벨 미사용."""
    base, names = load_all(with_names=True)
    F = {k: factor_space(*v, lam=1.0, names=names[k]) for k, v in base.items()}
    ps = []
    for s in base:
        if s == "팝업":
            continue
        r = align_pair(F[s], F["팝업"])
        if r is None:
            continue
        p = Ridge(alpha=1.0).fit(r[0], F[s]["y"]).predict(F["팝업"]["S"])
        ps.append((p - p.mean()) / (p.std() + 1e-9))
    z = np.mean(np.column_stack(ps), axis=1)
    return (z - z.mean()) / (z.std() + 1e-9)


def run(reps: int = 400) -> dict:
    pred = popup_pred()
    X, yp, w, Ap, Mp, gp, tp, cols = load_popup()
    raw = np.asarray(yp, float)
    n = len(raw)
    assert len(pred) == n
    rng = np.random.default_rng(SEED)

    print(f"팝업 {n}건 · log10(일평균 방문자) 평균 {raw.mean():.2f} "
          f"SD {raw.std():.2f}\n")
    print(f"  {'보정 k':<8}{'모델+보정':>12}{'중앙값만':>11}{'개선':>9}"
          f"{'배수 오차':>11}")
    out = {}
    for k in (5, 8, 12, 20, 30):
        me, mb = [], []
        for _ in range(reps):
            idx = rng.permutation(n)
            cal, test = idx[:k], idx[k:]
            c = float(np.median(raw[cal]))
            s = float(np.median(np.abs(raw[cal] - c)) * 1.4826)
            if s < 1e-6:
                continue
            # k건에서 상관을 추정해 축소
            if k >= 4 and np.std(pred[cal]) > 1e-9:
                rho = abs(spearman(pred[cal], raw[cal]))
            else:
                rho = 0.0
            wgt = k / (k + LAM)
            g = wgt * rho + (1 - wgt) * 0.45      # 사전값은 노트 58의 관측 ρ
            p = pred[test] * s * g + c
            me.append(float(np.abs(p - raw[test]).mean()))
            mb.append(float(np.abs(c - raw[test]).mean()))
        a, b = float(np.mean(me)), float(np.mean(mb))
        out[k] = {"model": a, "median": b, "gain": b - a, "fold": float(10 ** a)}
        print(f"  {k:<8}{a:>12.4f}{b:>11.4f}{b-a:>+9.4f}"
              f"{10**a:>10.2f}배")
    print(f"\n  (오차는 log10 평균절대오차 --- '배수 오차'는 10^오차)")
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    run()
