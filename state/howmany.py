"""출처가 몇 개면 되는가 --- 앙상블의 학습 곡선.

노트 82가 출처 하나를 빼는 것이 무해함을 보였다($|\\Delta|\\le$0.0023). 그러면
자연스러운 질문이 남는다 --- **몇 개까지 빼도 되나.** 그 답이 곧 ``도메인을
더 모아야 하나''의 답이다.

대상마다 쓸 수 있는 출처가 아홉이다. $m=1..9$에 대해 아홉 중 $m$개를 무작위로
골라 앙상블하고, 그 성적을 여러 조합에 대해 평균한다. 대상 집합은 열 개
그대로이므로 분모가 안 바뀐다(노트 82의 규약).

**곡선의 모양이 답을 준다.** 이미 평평하면 더 모아도 소용없고, 아직 오르고
있으면 몇 개 더 모을 값이 있다.

사용: python3 -m state.howmany
"""
from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path

import numpy as np
from scipy.stats import rankdata

from .audit import domains
from .ensemble import blend, cells
from .rank_test import spearman

SEED = 20260729
OUT = Path("data/state/howmany.json")


def curve(reps: int = 60, seed: int = SEED) -> dict:
    doms, names = domains()
    C = cells(doms, names)
    rng = np.random.default_rng(seed)
    per_m = {}
    per_target = {}
    for t, (rows, F) in C.items():
        ps = [p for _, p in rows]
        y = F["y"]
        n = len(ps)
        per_target[t] = {}
        for m in range(1, n + 1):
            combos = list(combinations(range(n), m))
            if len(combos) > reps:
                combos = [tuple(rng.choice(n, m, replace=False)) for _ in range(reps)]
            vs = [spearman(blend([ps[i] for i in cb]), y) for cb in combos]
            vs = [v for v in vs if np.isfinite(v)]
            if vs:
                per_target[t][m] = float(np.mean(vs))
                per_m.setdefault(m, []).append(float(np.mean(vs)))
    # **대상마다 쓸 수 있는 출처 수가 다르다**(정렬이 안 되는 쌍이 있어 여덟인
    # 대상이 있다). m 별 평균을 그냥 내면 큰 m 이 출처 아홉인 대상만으로 계산돼
    # 위로 튄다. 그래서 **모든 대상이 도달하는 m 까지만** 평균한다.
    mmax = min(len(d) for d in per_target.values())
    mean = {m: round(float(np.mean([per_target[t][m] for t in per_target])), 4)
            for m in range(1, mmax + 1)}
    return {"mean": mean, "mmax": mmax,
            "per_target": {t: {m: round(v, 4) for m, v in d.items()}
                           for t, d in per_target.items()}}


def run(write: bool = True) -> dict:
    r = curve()
    mm = r["mean"]
    print("출처 m개로 앙상블할 때의 열 대상 평균 ρ\n")
    print(f"{'m':>3}{'평균 ρ':>10}{'직전 대비':>11}")
    prev = None
    for m, v in mm.items():
        d = "" if prev is None else f"{v - prev:+.4f}"
        print(f"{m:>3}{v:>+10.4f}{d:>11}")
        prev = v
    ks = sorted(mm)
    # 로그 곡선 적합 --- ρ(m) = a + b·log(m)
    x = np.log(np.array(ks, float))
    y = np.array([mm[k] for k in ks])
    b, a = np.polyfit(x, y, 1)
    print(f"\n적합  ρ(m) = {a:+.4f} {b:+.4f}·ln(m)")
    for tgt in (12, 15, 20, 30):
        print(f"  출처 {tgt:>2}개면 {a + b * np.log(tgt):+.4f} "
              f"(지금 9개 {mm[max(ks)]:+.4f})")
    r["fit"] = {"a": round(float(a), 4), "b": round(float(b), 4),
                "pred": {str(k): round(float(a + b * np.log(k)), 4)
                         for k in (12, 15, 20, 30)}}
    if write:
        OUT.write_text(json.dumps(r, ensure_ascii=False, indent=1))
        print(f"\n저장: {OUT}")
    return r


if __name__ == "__main__":
    run()
