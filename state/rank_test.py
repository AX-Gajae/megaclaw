"""눈금에 둔감한 판정 --- 순위 기준 순열 검정, 그리고 과거 채택 결정 재감사.

노트 42가 판정 도구의 결함을 드러냈다. 지금까지 쓴 순열 검정은 통계량이
**MAE**였다. 그래서 예측의 눈금만 바꾸는 조작(λ, 축소)이 성적을 움직였고,
노트 41은 그것을 전이 개선으로 읽었다가 철회했다.

여기서는 통계량을 **스피어만 순위 상관**으로 바꾼다.

  · 단조 변환에 완전히 불변이다. 예측에 무엇을 곱하든 더하든 값이 같다.
  · 제품 목적과 맞는다. 팝업 기획 여럿의 반응 **순위**를 알고 싶은 것이지
    절대 방문자 수를 맞히려는 것이 아니다(절대값은 노트 26·32의 눈금 보정이
    따로 담당한다).
  · 이상치에 강하다. 라벨이 로그 스케일이어도 꼬리가 남아 있다.

귀무가설은 그대로다 --- ``출처에서 배운 계수가 대상에서 무작위 라벨로 배운 것보다
낫지 않다.'' 출처 라벨을 섞어 다시 적합하고 같은 순위 상관을 계산한다.

**과거 채택 결정을 이 기준으로 다시 감사한다.** 유의 개수로 고른 것이 넷이다.

    노트 37  공통 축 둘 → 셋
    노트 39  이중 배선(역할별)
    노트 40  쌍별 정렬
    노트 41  출처 λ=1.5   ← 이미 철회

사용: python3 -m state.rank_test
"""
from __future__ import annotations

import json
from itertools import permutations
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge

from .procrustes import align, align_pair, factor_space, lam_by_overlap
from .tri_domain import load_all

OUT = Path("data/state/rank_test.json")
SEED = 20260729


def ranks(v):
    o = np.argsort(np.argsort(np.asarray(v, float)))
    return o.astype(float)


def spearman(a, b):
    ra, rb = ranks(a), ranks(b)
    ra = (ra - ra.mean()) / (ra.std() + 1e-12)
    rb = (rb - rb.mean()) / (rb.std() + 1e-12)
    return float((ra * rb).mean())


def rank_cross(Ss, ys, St, yt, perm=3000, seed=SEED):
    """순위 상관 기준 순열 검정. 예측의 눈금에 완전히 불변이다."""
    obs = spearman(Ridge(alpha=1.0).fit(Ss, ys).predict(St), yt)
    rng = np.random.default_rng(seed)
    null = np.array([spearman(Ridge(alpha=1.0)
                              .fit(Ss, ys[rng.permutation(len(ys))]).predict(St), yt)
                     for _ in range(perm)])
    return round(obs, 4), round(float((null >= obs).mean()), 4)


def cells_pair(base, src_lam=None, tgt_lam=None, perm=3000, wiring=None):
    """쌍별 정렬. wiring 이 있으면 셀마다 출처 배선을 갈아 끼운다."""
    lam0 = lam_by_overlap(base)
    S = base if wiring is None else wiring
    Fs = {k: factor_space(*v, lam=(lam0.get(k, 0.75) if src_lam is None else src_lam))
          for k, v in S.items()}
    Ft = {k: factor_space(*v, lam=(lam0.get(k, 0.75) if tgt_lam is None else tgt_lam))
          for k, v in base.items()}
    out = {}
    for s, t in permutations(base, 2):
        r = align_pair(Fs[s], Ft[t])
        if r is None:
            continue
        o, p = rank_cross(r[0], Fs[s]["y"], Ft[t]["S"], Ft[t]["y"], perm=perm)
        out[f"{s}→{t}"] = {"rho": o, "p": p}
    return out


def cells_ref(base, ref="팝업", perm=3000):
    """전역 기준 정렬(노트 39까지의 방식)."""
    lam = lam_by_overlap(base)
    F = {k: factor_space(*v, lam=lam.get(k, 0.75)) for k, v in base.items()}
    G = align(F, ref)
    out = {}
    for s, t in permutations(base, 2):
        o, p = rank_cross(G[s]["S"], G[s]["y"], G[t]["S"], G[t]["y"], perm=perm)
        out[f"{s}→{t}"] = {"rho": o, "p": p}
    return out


def summ(c):
    return {"sig": sum(1 for v in c.values() if v["p"] < 0.05),
            "rho": float(np.mean([v["rho"] for v in c.values()])), "n": len(c),
            "cells": c}


def run() -> dict:
    base = load_all()
    out = {}

    print("=== 1. 새 검정이 눈금에 둔감한지 확인 ===")
    print(f"  {'설정':<16}{'유의':>9}{'평균 ρ':>10}")
    for lab, sl in (("유도값", None), ("출처 λ=1.5", 1.5), ("출처 λ=3.0", 3.0)):
        r = summ(cells_pair(base, src_lam=sl))
        out[f"λ:{lab}"] = r
        print(f"  {lab:<16}{r['sig']:>6}/{r['n']}{r['rho']:>+10.4f}")
    print("  → 세 줄이 같으면 검정이 눈금에 불변이다(노트 42의 요구)")

    print("\n=== 2. 정렬 방식 (노트 40 재감사) ===")
    # 전역 기준 정렬은 모든 도메인이 같은 공통 축 집합을 관측해야 한다.
    # 펀딩은 둘만 관측하므로 애초에 넣을 수 없다 --- 쌍별 정렬이 필요한 이유가
    # 성능이 아니라 **적용 가능성**이었음이 여기서 드러난다.
    four = {k: v for k, v in base.items() if k != "펀딩"}
    for lab, fn in (("전역 기준 정렬", cells_ref), ("쌍별 정렬", cells_pair)):
        r = summ(fn(four))
        out[f"정렬:{lab}"] = r
        print(f"  {lab:<16}{r['sig']:>6}/{r['n']}{r['rho']:>+10.4f}")
    print("  (펀딩 제외 --- 전역 정렬은 공통 축 집합이 같아야 한다)")

    print("\n=== 3. 이중 배선 (노트 39 재감사) ===")
    from .dual import SRC_WIRING, wire
    W = wire(base, SRC_WIRING)
    for lab, w in (("단일 배선", None), ("이중 배선(출처만)", W)):
        r = summ(cells_pair(base, wiring=w))
        out[f"배선:{lab}"] = r
        print(f"  {lab:<16}{r['sig']:>6}/{r['n']}{r['rho']:>+10.4f}")

    print("\n=== 4. 현재 상태 셀별 ===")
    cur = out["λ:유도값"]["cells"]
    for k, v in cur.items():
        m = "✅" if v["p"] < 0.05 else ("△" if v["rho"] > 0.1 else "✗")
        print(f"  {k:<14}ρ={v['rho']:+.3f}  p={v['p']:.4f}  {m}")

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    run()
