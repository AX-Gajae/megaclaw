"""법칙에서 나오는 예측을 검정한다 --- 출처 역할에서는 고유 축을 일부러 줄인다.

노트 40이 다섯 도메인에서 상충을 법칙 수준으로 확인했다.

    자기 상관 vs 대상 전이   r = +0.992
    자기 상관 vs 출처 전이   r = -0.992

지금까지는 이 법칙을 **관찰**했다. 배선을 바꾸면 자기 상관이 따라 움직이고
두 역할이 반대로 갔다. 이 노트는 법칙을 **조종 손잡이**로 쓴다.

인자 공간은 공유 블록과 고유 블록을 $\\lambda$로 섞어 만든다. 고유 축은 그
도메인에만 있는 축이므로, 고유 블록의 비중이 클수록 인자 공간이 그 도메인에
특수해진다. 법칙이 맞다면:

    대상 역할  $\\lambda$를 키운다 --- 특수해도 좋다. 자기 라벨만 맞히면 된다.
    출처 역할  $\\lambda$를 줄인다 --- 일반적이어야 한다. $\\lambda=0$이면
               공유 축만으로 인자 공간을 만든다.

**이것은 탐색이 아니라 예측이다.** 후보를 훑어 최댓값을 고르는 것이 아니라,
법칙이 시키는 방향으로 손잡이 하나를 돌려 보고 예측대로 움직이는지 본다.
그래서 선택 편향이 없다.

사용: python3 -m state.source_lambda
"""
from __future__ import annotations

import json
from itertools import permutations
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge

from .procrustes import align_pair, cross, factor_space, lam_by_overlap
from .tri_domain import load_all

OUT = Path("data/state/source_lambda.json")
SWEEP = (0.0, 0.25, 0.5, 0.75, 1.0, 1.5)


def evaluate(base, src_lam, tgt_lam=None, perm=3000):
    """셀마다 출처는 src_lam, 대상은 tgt_lam(없으면 유도값)으로 인자 공간을 만든다."""
    lam0 = lam_by_overlap(base)
    Fs = {k: factor_space(*v, lam=(lam0.get(k, 0.75) if src_lam is None else src_lam))
          for k, v in base.items()}
    Ft = {k: factor_space(*v, lam=(lam0.get(k, 0.75) if tgt_lam is None else tgt_lam))
          for k, v in base.items()}
    cells, rs = {}, {}
    for s, t in permutations(base, 2):
        r = align_pair(Fs[s], Ft[t])
        if r is None:
            continue
        o, p = cross(r[0], Fs[s]["y"], Ft[t]["S"], Ft[t]["y"], perm=perm)
        m = Ridge(alpha=1.0).fit(r[0], Fs[s]["y"])
        rr = float(np.corrcoef(m.predict(Ft[t]["S"]), Ft[t]["y"])[0, 1])
        cells[f"{s}→{t}"] = {"obs": o, "p": p, "r": rr}
        rs.setdefault(s, []).append(rr)
    return {"cells": cells,
            "sig": sum(1 for c in cells.values() if c["p"] < 0.05),
            "gain": float(np.mean([-c["obs"] for c in cells.values()])),
            "by_src": {k: float(np.mean(v)) for k, v in rs.items()}}


def run() -> dict:
    base = load_all()
    out = {}
    print("=== 출처 쪽 λ 만 바꾼다 (대상은 유도값 유지) ===")
    print(f"  {'출처 λ':<10}{'유의':>8}{'평균이득':>10}   출처별 평균 전이 r")
    ref = evaluate(base, None)
    out["유도값(현행)"] = ref
    print(f"  {'유도값':<10}{ref['sig']:>6}/20{ref['gain']:>+10.4f}   " +
          "  ".join(f"{k} {v:+.3f}" for k, v in ref["by_src"].items()))
    for lam in SWEEP:
        r = evaluate(base, lam)
        out[f"λ={lam}"] = r
        print(f"  λ={lam:<8.2f}{r['sig']:>6}/20{r['gain']:>+10.4f}   " +
              "  ".join(f"{k} {v:+.3f}" for k, v in r["by_src"].items()))

    print("\n=== 대상 쪽 λ 도 함께 (출처는 최선값 고정) ===")
    best_src = max((k for k in out if k.startswith("λ")),
                   key=lambda k: (out[k]["sig"], out[k]["gain"]))
    sl = float(best_src.split("=")[1])
    print(f"  출처 λ={sl} 고정")
    for lam in SWEEP:
        r = evaluate(base, sl, lam)
        out[f"src{sl}_tgt{lam}"] = r
        print(f"  대상 λ={lam:<6.2f}{r['sig']:>6}/20{r['gain']:>+10.4f}")

    OUT.write_text(json.dumps(
        {k: {kk: vv for kk, vv in v.items() if kk != "cells"} | {"cells": v["cells"]}
         for k, v in out.items()}, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    run()
