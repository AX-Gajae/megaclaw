"""노트 41이 적은 반증 조건을 검정한다 --- λ는 정말 정보량 손잡이인가.

노트 41은 출처 역할의 λ를 1.5로 키워 19/20을 얻고, 그것을 이렇게 설명했다.

    ``λ는 특수성 손잡이가 아니라 정보량 손잡이다. 출처는 회귀 계수를 학습하는
    쪽이라 인자 공간이 많이 담을수록 계수가 안정된다.''

그리고 반증 조건을 같이 적었다.

    ``λ가 정보량이라면 표본이 큰 도메인일수록 큰 λ가 좋아야 한다. 도메인별
    λ를 나눠 재면 그 예측을 검정할 수 있고, 관계가 없으면 이 설명이 틀린 것이다.''

여기서 그대로 한다. 도메인마다 자기 출처 λ만 훑고 나머지는 1.5에 고정한 채,
그 도메인이 **출처인 셀들**의 평균 전이 상관을 본다.

**게임은 제외한다.** 공통 축 셋만 관측해 고유 축이 없으므로 λ에 반응하지 않는다
(노트 41에서 네 셀 값이 소수점 넷째 자리까지 같았다). 손잡이가 없는 도메인을
회귀에 넣으면 관계가 희석된다.

경쟁 설명도 함께 잰다.

    표본 크기   정보량 설명이 예측하는 것.
    고유 축 수  블록 분산이 λ²×(축 수)이므로, 축이 많으면 작은 λ로 충분하다는
                반대 예측이 나온다.

사용: python3 -m state.lambda_law
"""
from __future__ import annotations

import json
from itertools import permutations
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge

from .procrustes import COMMON, SRC_LAM, align_pair, factor_space, lam_by_overlap
from .tri_domain import ALL5, load_all

OUT = Path("data/state/lambda_law.json")
SWEEP = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0)


def src_r(base, dom, lam, others=SRC_LAM):
    """dom 이 출처인 셀들의 평균 전이 상관. dom 만 lam, 나머지는 others."""
    lam0 = lam_by_overlap(base)
    Fs = {k: factor_space(*v, lam=(lam if k == dom else others))
          for k, v in base.items()}
    Ft = {k: factor_space(*v, lam=lam0.get(k, 0.75)) for k, v in base.items()}
    rs = []
    for t in base:
        if t == dom:
            continue
        r = align_pair(Fs[dom], Ft[t])
        if r is None:
            continue
        m = Ridge(alpha=1.0).fit(r[0], Fs[dom]["y"])
        rs.append(float(np.corrcoef(m.predict(Ft[t]["S"]), Ft[t]["y"])[0, 1]))
    return float(np.mean(rs)) if rs else float("nan")


def own_count(A, M, min_cov=0.6) -> int:
    ka = [j for j in range(len(ALL5)) if M[:, j].mean() >= min_cov]
    sh = [ALL5.index(a) for a in COMMON if ALL5.index(a) in ka]
    return len([j for j in ka if j not in sh])


def run() -> dict:
    base = load_all()
    info = {k: {"n": int(factor_space(*v, lam=SRC_LAM)["n"]),
                "own": own_count(v[0], v[1])} for k, v in base.items()}
    print("도메인 정보:", {k: f"n={v['n']} 고유축={v['own']}" for k, v in info.items()})

    doms = [k for k in base if info[k]["own"] > 0]
    print(f"\n손잡이가 있는 도메인: {doms}  (게임은 고유 축 0이라 제외)")
    print(f"\n  {'도메인':<7}" + "".join(f"{l:>8.2f}" for l in SWEEP) + "   최선")
    out = {}
    for d in doms:
        rs = [src_r(base, d, l) for l in SWEEP]
        b = SWEEP[int(np.argmax(rs))]
        out[d] = {"sweep": [round(x, 4) for x in rs], "best": b, **info[d]}
        print(f"  {d:<7}" + "".join(f"{x:>8.3f}" for x in rs) + f"   λ={b}")

    n = np.array([info[d]["n"] for d in doms], float)
    ow = np.array([info[d]["own"] for d in doms], float)
    bl = np.array([out[d]["best"] for d in doms], float)
    print(f"\n=== 반증 검정 ({len(doms)}점) ===")
    if len(doms) >= 3:
        rn = float(np.corrcoef(np.log10(n), bl)[0, 1])
        ro = float(np.corrcoef(ow, bl)[0, 1]) if ow.std() > 0 else float("nan")
        print(f"  log10(표본 크기) vs 최선 λ   r = {rn:+.3f}   ← 정보량 설명의 예측")
        print(f"  고유 축 수      vs 최선 λ   r = {ro:+.3f}   ← 경쟁 설명")
        out["_test"] = {"r_n": rn, "r_own": ro,
                        "doms": doms, "n": n.tolist(), "own": ow.tolist(),
                        "best": bl.tolist()}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    run()
