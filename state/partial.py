"""부분 계수 전이 --- 도메인 고유 축을 통제하되 공유 기하는 건드리지 않는다.

노트 28이 남긴 문제. 게임에 매장 노출도를 넣으면 그 도메인의 인자 공간이 회전해
다른 도메인에서 온 계수가 맞지 않는다. 축 자체는 유용한데(게임이 출처일 때 개선)
정렬을 해친다.

원인은 프로크루스테스 방식의 구조에 있다. 인자 공간을 **관측된 축 전부**로 만들고
그 공간을 회전으로 맞추므로, 축이 하나 늘면 공간 전체가 달라진다.

여기서는 공유 기하를 고정한다.

    공유 축      세 도메인 공통(타깃 폭, 굿즈 규모). 회전도 인자화도 하지 않는다.
    고유 축      출처 도메인에서 **교란 통제**로만 쓴다. 계수는 옮기지 않는다.

즉 출처에서 y ~ 공유 축 + 고유 축 을 적합하고 **공유 축의 부분 계수만** 대상에
적용한다. 고유 축은 공유 축 계수를 더 정확히 추정하는 데 기여하고, 공유 공간의
모양은 바꾸지 않는다.

이 방식의 장점은 축을 늘려도 정렬이 흔들리지 않는다는 것이고, 단점은 고유 축이
담은 정보가 대상 예측에 직접 쓰이지 못한다는 것이다. 둘 중 무엇이 큰지가 검정
대상이다.

사용: python3 -m state.partial
"""
from __future__ import annotations

import json
from itertools import permutations
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge

import state.procrustes as P
from .tri_domain import ALL5, detrend, load_all, z

SEED = 20260728
SHARED = ["target_breadth", "goods_scale"]


def domain_axes(A, M, y, t, min_cov: float = 0.6):
    """공유 축과 고유 축을 나눠 낸다. 둘 다 탈추세 + 표준화."""
    ka = [j for j in range(len(ALL5)) if M[:, j].mean() >= min_cov]
    rows = M[:, ka].all(1)
    sh = [ALL5.index(a) for a in SHARED]
    if not all(j in ka for j in sh):
        return None
    own = [j for j in ka if j not in sh]
    S = np.column_stack([z(detrend(A[rows][:, j], t[rows])) for j in sh])
    O = (np.column_stack([z(detrend(A[rows][:, j], t[rows])) for j in own])
         if own else np.zeros((int(rows.sum()), 0)))
    return {"S": S, "O": O, "y": z(detrend(y[rows], t[rows])),
            "own": [ALL5[j] for j in own], "n": int(rows.sum())}


def partial_coef(d, alpha: float = 1.0):
    """공유 축 + 고유 축으로 적합하고 공유 축 계수만 낸다."""
    X = np.column_stack([d["S"], d["O"]]) if d["O"].shape[1] else d["S"]
    m = Ridge(alpha=alpha).fit(X, d["y"])
    return m.coef_[:d["S"].shape[1]], float(m.intercept_)


def cross(src, tgt, use_own: bool, perm: int = 3000):
    b, c = (partial_coef(src) if use_own
            else (Ridge(alpha=1.0).fit(src["S"], src["y"]).coef_,
                  float(Ridge(alpha=1.0).fit(src["S"], src["y"]).intercept_)))
    yt = tgt["y"]
    base = float(np.abs(np.median(yt) - yt).mean())
    obs = float(np.abs(tgt["S"] @ b + c - yt).mean() - base)
    rng = np.random.default_rng(SEED)
    null = []
    for _ in range(perm):
        ys = src["y"][rng.permutation(len(src["y"]))]
        s2 = {**src, "y": ys}
        bb, cc = (partial_coef(s2) if use_own
                  else (Ridge(alpha=1.0).fit(src["S"], ys).coef_,
                        float(Ridge(alpha=1.0).fit(src["S"], ys).intercept_)))
        null.append(float(np.abs(tgt["S"] @ bb + cc - yt).mean() - base))
    return round(obs, 4), round(float((np.array(null) <= obs).mean()), 4)


def run(with_game_venue: bool = False) -> dict:
    doms = load_all()
    if with_game_venue:
        A, M, y, t = doms["게임"]
        M2 = M.copy()
        M2[:, ALL5.index("venue_prominence")] = 1.0
        doms["게임"] = (A, M2, y, t)
    D = {k: domain_axes(*v) for k, v in doms.items()}
    for k, v in D.items():
        print(f"  {k:<6} n={v['n']:>3}  공유 2축 + 고유 {len(v['own'])}축 {v['own']}")

    out = {"with_game_venue": with_game_venue, "교차": {}}
    for use_own in (False, True):
        lab = "고유 축 통제" if use_own else "공유 축만"
        sig = 0
        rows = {}
        for s, t in permutations(D, 2):
            o, p = cross(D[s], D[t], use_own)
            rows[f"{s}→{t}"] = [o, p]
            sig += p < 0.05
        out["교차"][lab] = rows
        print(f"\n[{lab}] 유의 {sig}  평균Δ "
              f"{np.mean([v[0] for v in rows.values()]):+.4f}")
        for k, v in rows.items():
            print(f"  {k:<14}Δ{v[0]:+.4f}  p={v[1]:.4f}  "
                  f"{'✅' if v[1] < 0.05 else ('△' if v[0] < 0 else '✗')}")
    return out


if __name__ == "__main__":
    r1 = run(False)
    print("\n" + "=" * 46)
    print("게임 매장 노출도를 켠 경우")
    r2 = run(True)
    Path("data/state/partial.json").write_text(
        json.dumps({"off": r1, "on": r2}, ensure_ascii=False, indent=1))
