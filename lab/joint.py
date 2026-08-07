"""F2 --- 결합 위계 잠재 모형. 노트 5부터 적어만 두고 한 번도 안 맞춘 식.

    min  Σ_d ‖M_d ⊙ (X_d − η_d Λ_dᵀ)‖²_F  +  τ⁻¹ Σ_d ‖Λ_d − Λ̄‖²_F
                                          +  w Σ_d ℓ(y_d, η_d β + b_d)

**왜 이게 다른가.** F1 은 도메인마다 따로 분해한 뒤 *사후에* 회전을 맞춘다.
그래서 정렬은 라벨을 못 보고, 라벨은 정렬을 못 고친다. 여기서는 적재
Λ_d 가 재구성과 예측 **양쪽**에서 동시에 정해지고, τ 가 도메인 간 거리를
조인다. τ→0 이면 전 도메인 같은 적재(완전 풀링), τ→∞ 면 F1 의 도메인별
분해에 가까워진다.

**공짜로 딸려오는 것.** 이력이 없는 도메인은 Λ_d 가 없으므로 Λ̄ 를 쓴다.
팝업은 2025년 이전 표본이 16건이라 학습 도메인에 못 들어가는데, 위계
모형에서는 그게 결측이 아니라 **완전 풀링**이다.

새 레코드의 η 는 관측된 축만으로 능형 최소제곱으로 푼다 --- 결측을 대입으로
메우지 않고 우도에서 뺀다(노트 85 의 표시자 대입보다 원칙적이다).
"""
from __future__ import annotations

import os

import numpy as np
import torch
from scipy.stats import rankdata

from state.tri_domain import ALL5

from .harness import Data

# MPS 는 배치 선형 풀이의 역전파(aten::linalg_lu_solve)가 아직 없다. 그리고
# 이 모형은 P=5, k<=5 라 GPU 로 갈 이유도 없다 --- 행렬이 5x5 다.
DEV = torch.device(os.environ.get("LAB_DEV", "cpu"))
torch.set_num_threads(int(os.environ.get("LAB_THREADS", "8")))
P = len(ALL5)


def _pack(A, M, names):
    """도메인마다 다른 축 이름을 공통 P 열로 옮긴다. 없는 축은 마스크 0."""
    nm = names or ALL5
    X = np.zeros((len(A), P), np.float32)
    Ms = np.zeros((len(A), P), np.float32)
    for j, a in enumerate(ALL5):
        if a in nm:
            c = nm.index(a)
            X[:, j] = A[:, c]
            Ms[:, j] = (M[:, c] > 0).astype(np.float32)
    return X, Ms


def _solve_eta(L, X, M, ridge: float):
    """관측된 축만으로 η 를 능형 최소제곱. 결측은 대입이 아니라 우도에서 뺀다.

    행마다  (Λᵀ diag(m) Λ + λI) η = Λᵀ diag(m) x  --- 미분 가능한 선형 풀이라
    적재까지 역전파가 흐른다."""
    k = L.shape[1]
    Lw = L.unsqueeze(0) * M.unsqueeze(2)                 # n×P×k
    G = torch.einsum("npk,pj->nkj", Lw, L)
    G = G + ridge * torch.eye(k, device=L.device).unsqueeze(0)
    b = torch.einsum("npk,np->nk", Lw, X)
    return torch.linalg.solve(G, b.unsqueeze(2)).squeeze(2)


class Joint:
    name = "F2_joint"
    idea = "결합 위계 잠재 모형 — 적재를 재구성과 예측이 같이 정하고 τ 로 도메인을 조인다"

    TAUS = (0.03, 0.3, 1.0, 3.0, 10.0, 100.0)

    def __init__(self, k: int = 2, tau=("auto"), w: float = 8.0,
                 steps: int = 900, lr: float = 0.05, ridge: float = 0.5,
                 seed: int = 0, inner: float = 2023.0):
        self.k, self.tau, self.w = k, tau, w
        self.steps, self.lr, self.ridge, self.seed = steps, lr, ridge, seed
        self.inner = inner

    # ── τ 를 학습 기간 안에서 고른다 ──────────────────────────────────
    INNER = (2022.0, 2022.5, 2023.0, 2023.5, 2024.0)

    def _pick_tau(self, train: Data) -> float:
        """**밖에서 고르면 그건 채점 자료를 본 것이다.** 학습 기간을 다시 갈라
        고른다. 다만 최댓값을 그냥 집으면 안 된다 --- 안쪽 곡면이 거의 평평한데
        (0.445~0.479) 바깥에는 tau=3 과 10 사이에 절벽이 있어서, 한 분할의
        argmax 는 다섯 중 세 번 절벽 너머를 집는다.

        그래서 분할 다섯을 평균하고 **짝지은 1 표준오차 규칙**을 쓴다 ---
        최고와 짝지은 차이가 1 SE 안이면 같다고 보고 그중 **가장 많이 풀링된
        (tau 가 작은) 것**을 고른다. 노트 125 가 치환 귀무로 배운 것과 같은
        선택이다: 같은 점수면 자유도가 적은 쪽."""
        from scipy.stats import spearmanr
        S = {t: [] for t in self.TAUS}
        for inner in self.INNER:
            tr, va, yr = {}, {}, {}
            for d, (A, M, y, t) in train.dom.items():
                u = train.yr[d]
                a = np.isfinite(u) & (u < inner)
                b = np.isfinite(u) & (u >= inner)
                if a.sum() >= 40:
                    tr[d] = (A[a], M[a], y[a], t[a]); yr[d] = u[a]
                if b.sum() >= 20:
                    va[d] = (A[b], M[b], y[b], t[b])
            if len(tr) < 3 or not va:
                continue
            for tau in self.TAUS:
                m = Joint(k=self.k, tau=tau, w=self.w, steps=self.steps,
                          lr=self.lr, ridge=self.ridge, seed=self.seed)
                try:
                    m.fit(Data(tr, train.names, yr))
                except Exception:
                    S[tau].append(np.nan); continue
                num = den = 0.0
                for d, (A, M, y, t) in va.items():
                    p = m.predict(d, A, M, t)
                    ok = np.isfinite(p)
                    if ok.sum() < 20:
                        continue
                    r = spearmanr(p[ok], y[ok]).correlation
                    if np.isfinite(r):
                        num += r * ok.sum(); den += ok.sum()
                S[tau].append(num / den if den else np.nan)
        good = {t: np.array(v) for t, v in S.items()
                if len(v) and np.isfinite(v).sum() >= 3}
        if not good:
            return 3.0
        mean = {t: float(np.nanmean(v)) for t, v in good.items()}
        top = max(mean, key=lambda t: mean[t])
        pick = top
        for t in sorted(good):                      # tau 오름차순 = 풀링 강한 순
            dif = good[t] - good[top]
            ok = np.isfinite(dif)
            if ok.sum() < 3:
                continue
            se = float(np.nanstd(dif[ok], ddof=1) / np.sqrt(ok.sum()))
            if float(np.nanmean(dif[ok])) >= -max(se, 1e-9):
                pick = t; break
        self.tau_table = mean
        self.tau_top, self.tau_picked = top, pick
        self.tau_score = mean[pick]
        return pick

    # ── 적합 ───────────────────────────────────────────────────────────
    def fit(self, train: Data) -> None:
        if self.tau == "auto":
            self.tau = self._pick_tau(train)
        g = torch.Generator(device="cpu").manual_seed(self.seed)
        self.doms = sorted(train.dom)
        D, k = len(self.doms), self.k
        X, Ms, Y = [], [], []
        for d in self.doms:
            A, M, y, t = train.dom[d]
            x, m = _pack(A, M, train.names.get(d))
            X.append(torch.tensor(x, device=DEV))
            Ms.append(torch.tensor(m, device=DEV))
            r = rankdata(y) / len(y)
            Y.append(torch.tensor((r - r.mean()).astype(np.float32), device=DEV))

        Lb = (torch.randn(P, k, generator=g) * .3).to(DEV).requires_grad_()
        Dl = (torch.randn(D, P, k, generator=g) * .05).to(DEV).requires_grad_()
        be = (torch.randn(k, generator=g) * .3).to(DEV).requires_grad_()
        bi = torch.zeros(D, device=DEV).requires_grad_()
        opt = torch.optim.Adam([Lb, Dl, be, bi], lr=self.lr)

        # η 를 자유 모수로 두면 학습 때와 예측 때가 다른 규칙으로 정해진다
        # (상각 격차). 여기서는 **양쪽 다** 관측 축에서 능형으로 푼다.
        self.curve = []
        for s in range(self.steps):
            opt.zero_grad()
            rec = pen = fit = 0.0
            for i in range(D):
                L = Lb + Dl[i]                                # P×k
                e = _solve_eta(L, X[i], Ms[i], self.ridge)     # n×k
                r = (X[i] - e @ L.T) * Ms[i]
                rec = rec + (r ** 2).sum() / Ms[i].sum()
                pen = pen + (Dl[i] ** 2).sum()
                p = e @ be + bi[i]
                fit = fit + ((Y[i] - p) ** 2).mean()
            loss = rec + pen / self.tau + self.w * fit
            loss.backward()
            opt.step()
            if s % 60 == 0 or s == self.steps - 1:
                self.curve.append((s, float(rec), float(fit), float(loss)))

        self.Lb = Lb.detach()
        self.Dl = {d: Dl[i].detach() for i, d in enumerate(self.doms)}
        self.be = be.detach()
        self.bi = {d: float(bi[i]) for i, d in enumerate(self.doms)}
        self.names = train.names

    # ── 예측 ───────────────────────────────────────────────────────────
    def predict(self, d, A, M, t):
        """관측된 축만으로 η 를 능형 최소제곱으로 푼다. 결측은 우도에서 뺀다.

        학습에 없던 도메인이면 Λ̄ 를 쓴다 --- 위계 모형이라 결측이 아니라
        완전 풀링이다(팝업이 정확히 이 경우다)."""
        L = self.Lb + self.Dl[d] if d in self.Dl else self.Lb    # P×k
        x, m = _pack(A, M, self.names.get(d))
        X = torch.tensor(x, device=DEV)
        Mt = torch.tensor(m, device=DEV)
        eta = _solve_eta(L, X, Mt, self.ridge)                   # 학습과 같은 규칙
        s = (eta @ self.be).cpu().numpy()
        s[m.sum(1) == 0] = np.nan            # 축이 하나도 없으면 못 매긴다
        return s
