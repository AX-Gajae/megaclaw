"""공유 인코더 + 도메인별 헤드 --- 프로크루스테스 정렬을 학습으로 대체한다.

현행 파이프라인은 도메인마다 주성분 둘을 뽑고 쌍마다 프로크루스테스로 회전을
맞춘다. 정렬이 **닫힌 해**로 계산되고 학습되지 않는다. 프론티어 쪽 다중 도메인
모델은 대신 **공유 인코더**를 둔다 --- 모든 도메인이 같은 인코더를 통과해 같은
잠재 공간에 놓이고, 도메인마다 얇은 헤드만 따로 둔다(Caruana 1997의 다중 과제
학습, Maurer 2016의 공유 표현 이론, 최근 표 형식 파운데이션 모델의 구성).

여기서는 그 구조를 현행과 **같은 규약**으로 겨루게 한다.

  · 입력은 다섯 축 값과 다섯 마스크(총 10차원). 마스크를 함께 넣어 결측을
    0으로 채운 것과 관측된 0을 구분하게 한다(노트 35·37의 교훈).
  · 잠재 차원을 2로 둔다. 현행이 성분 둘이므로 표현 용량을 맞춘다.
  · 라벨은 도메인 안에서 탈추세·표준화한 것. 현행과 같다.
  · 평가는 셀 (출처 s → 대상 t)마다 **s의 헤드를 t에 적용**하고 스피어만 순위
    상관을 잰다. 대상 라벨은 학습에 전혀 안 쓴다.

**두 변형을 잰다.**

    단독   인코더와 헤드를 s 하나로만 학습한다. 현행과 정보량이 같다.
    공유   인코더를 **대상 t를 뺀 다섯 도메인**으로 함께 학습하고 헤드는 s 것을
           쓴다. 파운데이션 모델이 하는 일이며, 여기서 이득이 나오면 그것이
           공유 표현의 값이다.

**씨앗 분산을 먼저 잰다.** 노트 14에서 신경망 씨앗 표준편차가 효과 크기의
4--5배라 아무것도 판정할 수 없었다. 씨앗 다섯 개로 돌리고 평균과 표준편차를
함께 적는다.

사용: python3 -m state.shared_encoder
"""
from __future__ import annotations

import json
from itertools import permutations
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

from .procrustes import align_pair, factor_space
from .rank_test import spearman
from .tri_domain import ALL5, detrend, load_all, z

OUT = Path("data/state/shared_encoder.json")
DEV = "cpu"


def prep(base):
    """도메인마다 (입력 10차원, 표준화 라벨)."""
    out = {}
    for k, (A, M, y, t) in base.items():
        cols = []
        for j in range(len(ALL5)):
            v = A[:, j].astype(float).copy()
            m = M[:, j].astype(float)
            v[m < .5] = 0.0
            keep = m > .5
            if keep.sum() > 10 and v[keep].std() > 1e-9:
                vv = np.zeros_like(v)
                vv[keep] = z(detrend(v[keep], t[keep]))
                v = vv
            cols.append(v)
            cols.append(m)
        X = np.column_stack(cols).astype(np.float32)
        yy = z(detrend(y, t)).astype(np.float32)
        out[k] = (torch.tensor(X), torch.tensor(yy))
    return out


class Model(nn.Module):
    def __init__(self, doms, d_in=10, d_lat=2, hidden=32):
        super().__init__()
        self.enc = nn.Sequential(nn.Linear(d_in, hidden), nn.Tanh(),
                                 nn.Linear(hidden, d_lat))
        self.heads = nn.ModuleDict({d: nn.Linear(d_lat, 1) for d in doms})

    def forward(self, x, dom):
        return self.heads[dom](self.enc(x)).squeeze(-1)


def train(data, doms, seed, epochs=400, lr=3e-3, wd=1e-3):
    torch.manual_seed(seed)
    m = Model(doms).to(DEV)
    opt = torch.optim.Adam(m.parameters(), lr=lr, weight_decay=wd)
    for _ in range(epochs):
        opt.zero_grad()
        loss = 0.0
        for d in doms:
            X, y = data[d]
            loss = loss + ((m(X, d) - y) ** 2).mean()
        (loss / len(doms)).backward()
        opt.step()
    return m


def run(seeds=(0, 1, 2, 3, 4)) -> dict:
    base, names = load_all(with_names=True)
    data = prep(base)
    doms = list(base)

    # 현행 선형 파이프라인
    F = {k: factor_space(*v, lam=1.0, names=names[k]) for k, v in base.items()}
    from sklearn.linear_model import Ridge
    lin = []
    for s, t in permutations(doms, 2):
        r = align_pair(F[s], F[t])
        if r is None:
            continue
        lin.append(spearman(Ridge(alpha=1.0).fit(r[0], F[s]["y"]).predict(F[t]["S"]),
                            F[t]["y"]))
    print(f"현행 선형(프로크루스테스)  {np.mean(lin):+.4f}\n")

    res = {}
    for mode in ("단독", "공유"):
        per_seed = []
        for sd in seeds:
            cells = []
            for s, t in permutations(doms, 2):
                tr = [s] if mode == "단독" else [d for d in doms if d != t]
                m = train(data, tr, seed=sd)
                with torch.no_grad():
                    p = m(data[t][0], s).numpy()
                cells.append(spearman(p, data[t][1].numpy()))
            per_seed.append(float(np.mean(cells)))
        res[mode] = {"mean": float(np.mean(per_seed)), "sd": float(np.std(per_seed)),
                     "seeds": per_seed}
        print(f"{mode:<6} 인코더  {np.mean(per_seed):+.4f} ± {np.std(per_seed):.4f}"
              f"   (씨앗 {len(seeds)}개, 범위 {min(per_seed):+.4f}~{max(per_seed):+.4f})")

    res["선형"] = {"mean": float(np.mean(lin))}
    print(f"\n씨앗 표준편차 대 선형과의 차이:")
    for mode in ("단독", "공유"):
        d = res[mode]["mean"] - res["선형"]["mean"]
        print(f"  {mode}: 차이 {d:+.4f}, 씨앗 SD {res[mode]['sd']:.4f}, "
              f"비 {abs(d)/max(res[mode]['sd'],1e-9):.2f}")
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    return res


if __name__ == "__main__":
    run()
