"""노트 41을 철회한다 --- λ가 한 일은 전이 개선이 아니라 예측 축소였다.

노트 41은 출처 λ를 1.5로 키워 19/20을 얻고 ``정보량 손잡이''라고 설명했다.
노트 42가 그 설명의 반증 조건을 검정하다가 훨씬 나쁜 것을 찾았다.

아이돌을 출처로 쓰고 λ만 바꿔 가며 재니 **전이 상관이 꿈쩍하지 않는다.**

    λ        1.00    1.25    1.50    2.00
    →팝업   +0.458  +0.458  +0.457  +0.458
    →도서   +0.269  +0.269  +0.269  +0.269

움직인 것은 예측의 **퍼짐**이다.

    예측 SD ÷ 대상 y SD
    →팝업    0.67    0.59    0.51    0.38
    →도서    0.59    0.52    0.45    0.33

대상 라벨은 표준화돼 SD가 1이다. 상관이 $r$일 때 MAE를 최소화하는 예측 스케일은
$r$ 근처이므로(회귀 축소), 예측 SD가 0.67에서 0.38로 줄면 MAE가 좋아진다.
**λ를 키우면 출처 인자 공간의 분산이 커져 능형 계수가 작아지고, 그래서 우연히
축소가 걸렸다.** 순위는 그대로인데 눈금만 맞은 것이다.

그러면 λ로 돌려 맞출 것이 아니라 **축소를 직접 하면 된다.** 이 모듈은 예측을
표준화한 뒤 계수 $c$로 다시 펴서, $c$를 어떻게 정해야 하는지 검정한다.

**$c$는 대상 라벨 없이 정해야 한다.** 후보 셋:

    상수         모든 셀에 같은 $c$. 가장 단순하고 튜닝이 하나다.
    출처 자기상관 출처가 자기 라벨을 얼마나 맞히나(교차검증). 대상 라벨 불필요.
    대상 자기상관 노트 33·37의 법칙대로면 이것이 전이 상관의 추정치다.
                 **대상 라벨이 필요하므로 실전에서는 못 쓴다** --- 상한 참고용이다.

사용: python3 -m state.shrink
"""
from __future__ import annotations

import json
from itertools import permutations
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold

from .procrustes import align_pair, factor_space, lam_by_overlap
from .tri_domain import load_all

OUT = Path("data/state/shrink.json")
SEED = 20260729


def cv_r(X, y, seed=SEED):
    pr = np.zeros(len(y))
    for tr, te in KFold(5, shuffle=True, random_state=seed).split(X):
        pr[te] = Ridge(alpha=1.0).fit(X[tr], y[tr]).predict(X[te])
    return float(np.corrcoef(pr, y)[0, 1])


def shrink_cross(Ss, ys, St, yt, c, perm=3000, seed=SEED):
    """예측을 표준화한 뒤 c배로 편다. 순열 귀무분포도 같은 처리를 받는다."""
    def pred(m, S):
        p = m.predict(S)
        s = p.std()
        return (p - p.mean()) / (s + 1e-12) * c + np.median(yt)

    base = np.abs(np.median(yt) - yt).mean()
    obs = float(np.abs(pred(Ridge(alpha=1.0).fit(Ss, ys), St) - yt).mean() - base)
    rng = np.random.default_rng(seed)
    null = np.array([
        float(np.abs(pred(Ridge(alpha=1.0).fit(Ss, ys[rng.permutation(len(ys))]), St)
                     - yt).mean() - base) for _ in range(perm)])
    return round(obs, 4), round(float((null <= obs).mean()), 4)


def evaluate(base, mode, const=None, src_lam=1.0, perm=3000):
    lam0 = lam_by_overlap(base)
    Fs = {k: factor_space(*v, lam=src_lam) for k, v in base.items()}
    Ft = {k: factor_space(*v, lam=lam0.get(k, 0.75)) for k, v in base.items()}
    self_s = {k: cv_r(Fs[k]["S"], Fs[k]["y"]) for k in base}
    self_t = {k: cv_r(Ft[k]["S"], Ft[k]["y"]) for k in base}
    cells = {}
    for s, t in permutations(base, 2):
        r = align_pair(Fs[s], Ft[t])
        if r is None:
            continue
        c = {"상수": const, "출처 자기상관": max(self_s[s], 0.05),
             "대상 자기상관": max(self_t[t], 0.05)}[mode]
        o, p = shrink_cross(r[0], Fs[s]["y"], Ft[t]["S"], Ft[t]["y"], c, perm=perm)
        cells[f"{s}→{t}"] = {"obs": o, "p": p, "c": round(float(c), 3)}
    return {"cells": cells,
            "sig": sum(1 for x in cells.values() if x["p"] < 0.05),
            "gain": float(np.mean([-x["obs"] for x in cells.values()])),
            "self_src": self_s, "self_tgt": self_t}


def run() -> dict:
    base = load_all()
    out = {}
    print("=== 상수 축소 계수 c ===")
    print(f"  {'c':<8}{'유의':>8}{'평균이득':>10}")
    for c in (0.20, 0.25, 0.30, 0.35, 0.40, 0.50, 0.60):
        r = evaluate(base, "상수", const=c)
        out[f"상수 {c}"] = {k: v for k, v in r.items() if k != "cells"} | {"cells": r["cells"]}
        print(f"  {c:<8.2f}{r['sig']:>6}/20{r['gain']:>+10.4f}")

    print("\n=== 라벨 없는 규칙 ===")
    for mode in ("출처 자기상관", "대상 자기상관"):
        r = evaluate(base, mode)
        out[mode] = {k: v for k, v in r.items() if k != "cells"} | {"cells": r["cells"]}
        cs = sorted({v["c"] for v in r["cells"].values()})
        print(f"  {mode:<12}{r['sig']:>6}/20{r['gain']:>+10.4f}   c 범위 {cs[0]:.2f}~{cs[-1]:.2f}"
              + ("   ← 대상 라벨 필요, 상한 참고용" if mode.startswith("대상") else ""))
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    run()
