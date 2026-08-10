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
from scipy.stats import rankdata, spearmanr
from sklearn.linear_model import Ridge

from .procrustes import align, align_pair, factor_space, lam_by_overlap
from .tri_domain import load_all

OUT = Path("data/state/rank_test.json")
SEED = 20260729


def ranks(v):
    """**동률 평균(midrank)** 순위.

    🔴 **2026-08-10 · 이슈 #117(티처 #60 C1·C2) · 노트 898 에서 바뀌었다.**
    옛 구현은 ``o = np.argsort(np.argsort(v))`` --- **서수 순위**였고 동률을
    **배열 순서**로 깼다. 그러면 통계량이 **자료의 정렬에 의존한다.**

    898 이 잰 것(사전등록 R-1 · `runners/out898_board.json`): 같은 (예측, 라벨) 짝을
    스무 번 섞기만 해도 옛 함수는 **12/12 도메인에서** ρ 가 갈렸고 최대 폭이
    **0.1562** 였다. 새 함수는 **0/12 · 폭 0.0** 이다. 통계량이 아니라 정렬의
    함수였던 것이다.

    **동률은 예외가 아니었다.** ``BagBoost.predict`` 는 자루 순위 평균이라
    같은 값이 흔하다 --- 시장팝업 126행에 예측 고유값 **15**(동률 0.881) ·
    영화 406행에 **139**(0.658).

    그리고 저장소의 **자**(``runners/ruler890.sp`` · ``runners/thresh891`` 전량)는
    처음부터 동률 평균을 썼다. **판과 자가 서로 다른 스피어만을 쓰고 있었다.**
    여기서 통일한다 --- 자를 판에 맞추지 않고 판을 자에 맞춘 이유는 크기가 아니라
    원칙이다(순서 불변 · 표준 정의).

    판 정본은 이 한 줄로 **0.46982 → 0.47034** 로 옮겨간다(12씨앗 짝 Δ
    +0.00051922 · BCa [+0.00044404,+0.00059359] · 12/12 양수). **개선이 아니라
    편의 제거다** --- 서수는 동률에서 순위를 무작위로 갈라 상관을 아래로 끈다.

    🔴 **비유한 값은 막는다**(이슈 #115). 옛 ``argsort`` 는 NaN 을 맨 뒤로 밀어
    **조용히 숫자를 냈다** --- 887형 중립화의 거울상이다. 부르는 쪽이 마스크를
    씌워야 한다. 챔피언 경로에서 그 자리는 ``lab/harness.py:265`` 의 ``ok`` 다.
    """
    a = np.asarray(v, float)
    fin = np.isfinite(a)
    if not fin.all():
        raise ValueError(
            f"rank_test.ranks: {a.size} 개 중 {int((~fin).sum())} 개가 비유한 --- "
            "부르는 쪽에서 isfinite 마스크를 씌워라(이슈 #115 · #117 · 노트 898). "
            "옛 argsort 구현은 여기서 조용히 숫자를 냈다.")
    return np.asarray(rankdata(a), float)


def spearman(a, b):
    """동률 평균 스피어만. **`scipy.stats.spearmanr` 과 부동소수 동일**하다.

    🔴 노트 898 --- 옛 구현은 `ranks()` 뒤에 손으로 표준화하면서 분모에 `+1e-12` 를
    넣었다. 그 눈금 보정 때문에 같은 정의인데도 `scipy` 와 **소수 12자리에서 갈렸고**,
    그래서 「판과 자가 같은 함수를 쓴다」를 **부동소수로는 확인할 수 없었다**.
    (자기 손으로 짠 표준화 대신 `scipy` 를 부르면 이 물음이 아예 안 생긴다.)
    `ranks()` 가 이미 비유한 값을 막으므로 여기서 다시 안 막는다.

    예측이 **전부 동률**이면 순위가 상수라 상관이 정의되지 않고 `nan` 이 나온다 ---
    옛 서수 구현에서는 순위가 언제나 0..n-1 이라 **일어날 수 없던 일**이다.
    `harness.pooled` 는 비유한 도메인을 건너뛰므로 그 도메인이 **조용히 빠진다**.
    가짓수가 1인 예측을 채점하는 자리가 생기면 그때는 '없다'가 아니라 '모른다'로
    적어야 한다(조항 59 · 노트 887 병기 의무).
    """
    ranks(a), ranks(b)                      # 비유한 값 가드(#115)를 여기서도 태운다
    return float(spearmanr(a, b)[0])


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
