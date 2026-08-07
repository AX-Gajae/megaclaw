"""마스크를 입력으로 받는 인코더 --- 노트 60--62의 재대결.

노트 84가 병목을 구조로 지목했다. `factor_space` 는 **완전 케이스만** 쓰므로
덮개율이 낮은 축은 아무리 세도 못 쓴다 --- 직전작 성적은 단일 상관이 모바일에서
$+$0.709인데 `min_cov=0.6` 문턱에 걸려 통째로 버려졌다. 노트 85가 같은 레코드
집합에서 재니 그 축을 넣으면 $+$0.4501$\to+$0.4735다. **판에는 올라와 있는데
지금 구조가 못 집는다.**

마스크를 **입력으로** 받는 인코더는 완전 케이스를 요구하지 않는다. 노트 60--62가
정확히 그 구조(값 다섯 $+$ 마스크 다섯)를 만들었고 PCA$+$프로크루스테스에 졌다.
**그때는 못 쓸 축이 없었다.** 지금은 있다.

**설계.**

    입력   값 여섯 + 마스크 여섯 = 12차원. 결측은 0으로 두고 마스크가 알린다.
    인코더 공유 MLP 12→32→16→2. 잠재 차원을 인자 공간의 성분 수(k=2)에 맞춘다.
    복원   디코더 2→16→12. **마스크된 자리만** 빼고 값을 복원한다.
    지도   도메인별 선형 머리 2→1. 도메인 안 표준화 라벨을 맞힌다.
    손실   라벨 MSE + λ·복원 MSE

**공유 인코더라 정렬이 필요 없다.** 프로크루스테스가 하던 일을 인코더가 학습으로
대신한다 --- 노트 40의 쌍별 정렬이 사라진다.

**대상 라벨을 안 본다.** 대상 도메인 t 를 맞힐 때 **t 의 라벨 지도를 빼고**
학습한다(t 의 입력은 복원 손실에만 쓴다). 그다음 출처 잠재$\to$출처 라벨 능형
회귀를 적합해 대상 잠재에 적용한다 --- 지금 파이프라인과 같은 규약이다.

사용: python3 -m state.masked_encoder
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from scipy.stats import rankdata
from sklearn.linear_model import Ridge

from .audit import domains
from .rank_test import spearman
from .tri_domain import ALL5, detrend, z

SEED = 20260729
OUT = Path("data/state/masked_encoder.json")
SLOTS = list(ALL5) + ["prev_hit"]


class Net(nn.Module):
    def __init__(self, d_in: int, k: int = 2, h: int = 32):
        super().__init__()
        self.enc = nn.Sequential(nn.Linear(d_in, h), nn.GELU(),
                                 nn.Linear(h, h // 2), nn.GELU(),
                                 nn.Linear(h // 2, k))
        self.dec = nn.Sequential(nn.Linear(k, h // 2), nn.GELU(),
                                 nn.Linear(h // 2, d_in))

    def forward(self, x):
        zz = self.enc(x)
        return zz, self.dec(zz)


def prep(doms, names, prev_cols):
    """도메인마다 (값 6, 마스크 6, 라벨) 을 같은 슬롯 순서로 만든다.

    축은 도메인 안에서 탈추세 · 표준화한다 --- `factor_space` 와 같은 순서이며,
    다른 점은 **완전 케이스를 안 요구한다**는 것뿐이다."""
    out = {}
    for k, (A, M, y, t) in doms.items():
        nm = list(names.get(k) or ALL5)
        V = np.zeros((len(y), len(SLOTS)))
        Mk = np.zeros((len(y), len(SLOTS)))
        for j, s in enumerate(SLOTS):
            if s == "prev_hit":
                pv, pm = prev_cols.get(k, (None, None))
                if pv is None or len(pv) != len(y):
                    continue
                col, msk = pv, pm > 0
            elif s in nm:
                col, msk = A[:, nm.index(s)], M[:, nm.index(s)] > 0
            else:
                continue
            if msk.sum() < 10:
                continue
            v = np.zeros(len(y))
            d = detrend(col[msk], t[msk])
            v[msk] = (d - d.mean()) / (d.std() + 1e-9)
            V[:, j], Mk[:, j] = v, msk.astype(float)
        out[k] = (V, Mk, z(detrend(y, t)))
    return out


def encode(net, V, M):
    """학습된 인코더로 **아무 행이나** 투영한다. 정직한 교차검증에 필요하다 ---
    폴드마다 학습한 인코더로 그 폴드를 투영해야 하기 때문이다."""
    x = torch.tensor(np.hstack([V, M]), dtype=torch.float32)
    with torch.no_grad():
        return net(x)[0].numpy()


def train_one(data, holdout, k: int = 2, epochs: int = 400, lam: float = 0.5,
              seed: int = SEED, balance: bool = True, return_net: bool = False):
    """holdout 도메인의 **라벨 지도만** 빼고 학습한다.

    balance --- 도메인마다 손실 비중을 같게 둔다. 안 그러면 큰 도메인이 지배한다.
    웹툰·세계애니·애니·모바일 넷이 레코드의 76%라 아이돌(81건)은 0.6%다.
    **판정치가 도메인 평균이므로 손실도 도메인 평균이어야 한다.**"""
    torch.manual_seed(seed)
    net = Net(2 * len(SLOTS), k=k)
    heads = {d: nn.Linear(k, 1) for d in data}
    params = list(net.parameters())
    for h in heads.values():
        params += list(h.parameters())
    opt = torch.optim.Adam(params, lr=3e-3, weight_decay=1e-4)
    X = {d: torch.tensor(np.hstack([V, M]), dtype=torch.float32)
         for d, (V, M, _) in data.items()}
    Mt = {d: torch.tensor(M, dtype=torch.float32) for d, (_, M, _) in data.items()}
    Vt = {d: torch.tensor(V, dtype=torch.float32) for d, (V, _, _) in data.items()}
    Yt = {d: torch.tensor(y, dtype=torch.float32).unsqueeze(1)
          for d, (_, _, y) in data.items()}
    for _ in range(epochs):
        opt.zero_grad()
        loss = 0.0
        for d in data:
            zz, rec = net(X[d])
            m = Mt[d]
            # 복원은 **관측된 자리만** 센다. 마스크 자체도 복원 대상에 넣지 않는다.
            loss = loss + lam * (((rec[:, :len(SLOTS)] - Vt[d]) ** 2) * m).sum() / (m.sum() + 1)
            if d != holdout:
                w = 1.0 if balance else len(data[d][2]) / 1000.0
                loss = loss + w * ((heads[d](zz) - Yt[d]) ** 2).mean()
        loss.backward()
        opt.step()
    net.eval()
    with torch.no_grad():
        Z = {d: net(X[d])[0].numpy() for d in data}
    return (Z, net) if return_net else Z


def run(write: bool = True, epochs: int = 400, lam: float = 0.5,
        k: int = 2, balance: bool = True, quiet: bool = False) -> dict:
    import sys
    sys.path.insert(0, "/Users/ax/.claude/jobs/a5c89f96/tmp")
    from prior_hit import REC, cols
    doms, names = domains()
    prev = {}
    for dom in REC:          # k 는 잠재 차원 인자다. 반복 변수로 쓰면 가려진다.
        if dom not in doms:
            continue
        v1, m1, _, _ = cols(dom)
        if len(v1) == len(doms[dom][2]):
            prev[dom] = (v1, m1)
    data = prep(doms, names, prev)
    if not quiet:
        print(f"슬롯 {SLOTS}")
        for d, (V, M, y) in data.items():
            print(f"  {d:<7}n={len(y):>5}  덮개율 " +
                  " ".join(f"{M[:, j].mean():.2f}" for j in range(len(SLOTS))))
    res = {}
    for tgt in data:
        Z = train_one(data, tgt, epochs=epochs, lam=lam, k=k, balance=balance)
        ps = []
        for s in data:
            if s == tgt:
                continue
            ps.append(Ridge(alpha=1.0).fit(Z[s], data[s][2]).predict(Z[tgt]))
        e = np.column_stack([rankdata(p) / len(p) for p in ps]).mean(1)
        res[tgt] = round(float(spearman(e, data[tgt][2])), 4)
        if not quiet:
            print(f"  {tgt:<7}{res[tgt]:+.4f}", flush=True)
    m = float(np.mean(list(res.values())))
    print(f"\n마스크 인코더 판정치 {m:+.4f}   (현행 인자 공간 +0.4038)")
    o = {"per_target": res, "metric": round(m, 4), "epochs": epochs, "lam": lam,
         "k": k, "balance": balance}
    if write:
        OUT.write_text(json.dumps(o, ensure_ascii=False, indent=1))
        print(f"저장: {OUT}")
    return o


if __name__ == "__main__":
    run()


def loadings(Z, V, M, common_idx):
    """잠재 차원과 **공통 축**의 상관 --- 프로크루스테스가 맞출 적재.

    `factor_space` 는 주성분 고유벡터에서 적재를 얻는데, 인코더는 비선형이라
    고유벡터가 없다. 대신 **관측된 자리에서 잰 상관**을 적재로 쓴다. 둘 다
    ``이 성분이 그 축을 얼마나 담고 있나''를 재는 것이므로 같은 자리다."""
    L = np.zeros((len(common_idx), Z.shape[1]))
    for i, a in enumerate(common_idx):
        m = M[:, a] > 0
        if m.sum() < 20:
            continue
        for j in range(Z.shape[1]):
            s = np.std(Z[m, j])
            if s > 1e-9 and np.std(V[m, a]) > 1e-9:
                L[i, j] = float(np.corrcoef(Z[m, j], V[m, a])[0, 1])
    return L


def run_procrustes(write: bool = True, epochs: int = 400, lam: float = 0.5,
                   k: int = 2, quiet: bool = False) -> dict:
    """인코더로 표현을 만들고 **정렬은 쌍별 프로크루스테스**로 한다(노트 86).

    노트 85의 진단 --- 공유 인코더가 지는 것은 표현이 나빠서가 아니라 쌍별
    정렬 자유도를 잃어서다. 그렇다면 표현만 인코더로 바꾸고 정렬은 그대로
    두면 이겨야 한다. 이 함수가 그 검정이다."""
    import sys
    from .procrustes import COMMON, procrustes
    sys.path.insert(0, "/Users/ax/.claude/jobs/a5c89f96/tmp")
    from prior_hit import REC, cols
    doms, names = domains()
    prev = {}
    for dom in REC:
        if dom in doms:
            v1, m1, _, _ = cols(dom)
            if len(v1) == len(doms[dom][2]):
                prev[dom] = (v1, m1)
    data = prep(doms, names, prev)
    ci = [SLOTS.index(a) for a in COMMON if a in SLOTS]
    res = {}
    for tgt in data:
        Z = train_one(data, tgt, epochs=epochs, lam=lam, k=k)
        L = {d: loadings(Z[d], data[d][0], data[d][1], ci) for d in data}
        ps = []
        for s in data:
            if s == tgt:
                continue
            R = procrustes(L[s], L[tgt])
            ps.append(Ridge(alpha=1.0).fit(Z[s] @ R, data[s][2]).predict(Z[tgt]))
        e = np.column_stack([rankdata(p) / len(p) for p in ps]).mean(1)
        res[tgt] = round(float(spearman(e, data[tgt][2])), 4)
        if not quiet:
            print(f"  {tgt:<7}{res[tgt]:+.4f}", flush=True)
    m = float(np.mean(list(res.values())))
    print(f"\n인코더+프로크루스테스 판정치 {m:+.4f}   "
          f"(인코더만 +0.3575 · 인자 공간 +0.4038)")
    o = {"per_target": res, "metric": round(m, 4), "epochs": epochs,
         "lam": lam, "k": k}
    if write:
        Path("data/state/enc_procrustes.json").write_text(
            json.dumps(o, ensure_ascii=False, indent=1))
    return o


def honest_selfr(data, folds: int = 3, epochs: int = 250, lam: float = 0.5,
                 k: int = 2, seed: int = SEED, shared_head: bool = True) -> dict:
    """**정직한** 도메인 안 자기 상관 --- 노트 87·88의 규약.

    폴드마다 그 폴드의 라벨을 빼고 인코더를 학습한 뒤 학습된 인코더로 그 폴드를
    투영한다. 인코더가 평가 레코드의 라벨을 한 번도 안 본다.

    **낙관 절차를 쓰면 안 되는 이유가 둘이다**(노트 88).

        도메인별 머리  편향의 절반. 공유 머리로 바꾸면 +0.062→+0.030.
        학습 시간      팝업(75건) 편향이 100에폭 +0.010에서 700에폭 +0.570.
                       모바일(2,000건)은 +0.003→+0.011로 거의 안 는다.

    작은 도메인에서는 **학습 시간이 곧 편향**이므로 낙관 수치를 보고하면 안 된다.
    """
    from sklearn.model_selection import KFold
    out = {}
    for d in data:
        V, M, y = data[d]
        pr = np.zeros(len(y))
        for tr, te in KFold(folds, shuffle=True, random_state=seed).split(V):
            dd = dict(data)
            dd[d] = (V[tr], M[tr], y[tr])
            Z, net = train_one(dd, holdout=None, epochs=epochs, lam=lam, k=k,
                               return_net=True)
            pr[te] = Ridge(alpha=1.0).fit(Z[d], y[tr]).predict(
                encode(net, V[te], M[te]))
        out[d] = round(float(spearman(pr, y)), 4)
    return out
