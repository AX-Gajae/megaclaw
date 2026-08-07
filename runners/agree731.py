"""노트 731 — **두 행렬이 같은 소스를 고르나.** 논문 144 가 단정한 것을 실측한다.

노트 727 은 `학습 전부 → 유보` 로 행렬을 만들었고, 노트 728 은 누출을 막으려
`앞(<2024) → 뒤(2024)` 로 만들었다. **고르기의 근거가 잡음이면 두 행렬이 다른
소스를 고른다.** 판을 안 적합하므로 트렁크 적합만 든다.
"""
import json
import sys

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
import torch
import torch.nn as nn
from scipy.stats import rankdata, spearmanr
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer

from lab import loop as L, textnn as NN

T = 2025.0
SPLIT = 2024.0
SEEDS = (0, 1, 2, 3)
MIN_SRC = 40
MIN_BACK = 20


def shell():
    from lab import genaxes, grpaxes

    def ex():
        e = {**L._trendsub(zero_is_data=True), **L._calsub(), **L._wikisub(),
             **L._tag(), **L._fund(), **L._rawsub(), **genaxes.build()}
        e.update(grpaxes.build())
        return e
    return L._idol(lambda: ex(), mode="cut", with_wiki=True, with_trend=True,
                   wide_post=True, wide_pop="grades")


class Net(nn.Module):
    def __init__(self, nd):
        super().__init__()
        self.emb = nn.Embedding(nd, NN.EMB_DIM)
        self.mlp = nn.Sequential(nn.Linear(NN.SVD_DIM + NN.EMB_DIM, NN.HID),
                                 nn.Tanh(), nn.Linear(NN.HID, 1))

    def forward(self, z, d):
        return self.mlp(torch.cat([z, self.emb(d)], -1)).squeeze(-1)


def main():
    data = shell()
    txt, dom, y, is_tr, is_te, idx = NN._pool(data, T)
    yr = np.array([data.yr[d][idx[i]] for i, d in enumerate(dom)], float)
    doms = sorted(set(dom.tolist()))
    dmap = {d: i for i, d in enumerate(doms)}
    di = np.array([dmap[d] for d in dom])
    rk = np.full(len(y), np.nan)
    for d in doms:
        m = is_tr & (dom == d)
        if m.sum() >= 2:
            rk[m] = rankdata(y[m]) / m.sum()
    fit_all = is_tr & np.isfinite(rk)
    fit_front = fit_all & (yr < SPLIT)
    back = fit_all & (yr >= SPLIT)

    V = TfidfVectorizer(analyzer="char_wb", ngram_range=NN.NG, min_df=3,
                        max_features=40000, sublinear_tf=True)
    V.fit([txt[i] for i in np.flatnonzero(fit_all)])
    svd = TruncatedSVD(n_components=NN.SVD_DIM, random_state=685)
    svd.fit(V.transform([txt[i] for i in np.flatnonzero(fit_all)]))
    Z = svd.transform(V.transform(txt)).astype(np.float32)
    Z = (Z - Z[fit_all].mean(0)) / (Z[fit_all].std(0) + 1e-6)

    def train(m, seed):
        torch.manual_seed(seed)
        net = Net(len(doms))
        opt = torch.optim.Adam(net.parameters(), lr=NN.LR)
        zf = torch.tensor(Z[m]); df = torch.tensor(di[m])
        tf = torch.tensor(rk[m], dtype=torch.float32)
        for _ in range(NN.EPOCHS):
            opt.zero_grad()
            ((net(zf, df) - tf) ** 2).mean().backward()
            opt.step()
        net.eval()
        return net

    def sc(net, m, floor):
        if m.sum() < floor:
            return None
        with torch.no_grad():
            p = net(torch.tensor(Z[m]), torch.tensor(di[m])).numpy()
        yy = y[m]
        ok = np.isfinite(p) & np.isfinite(yy)
        if ok.sum() < floor or len(np.unique(p[ok])) < 3:
            return None
        return float(spearmanr(p[ok], yy[ok]).statistic)

    def matrix(fitmask, scoremask, floor, tag):
        srcs = [d for d in doms if (fitmask & (dom == d)).sum() >= MIN_SRC]
        M = {}
        for s in srcs:
            acc = {t: [] for t in doms}
            for sd in SEEDS:
                net = train(fitmask & (dom == s), sd)
                for t in doms:
                    v = sc(net, scoremask & (dom == t), floor)
                    if v is not None:
                        acc[t].append(v)
            M[s] = {t: round(float(np.mean(a)), 4) for t, a in acc.items() if a}
            print(f"  [{tag}] {s} → {len(M[s])}칸", flush=True)
        return M

    print("=== ① 앞(<2024) → 뒤(2024) · 노트 728 이 쓴 것 ===", flush=True)
    A = matrix(fit_front, back, MIN_BACK, "앞→뒤")
    print("=== ② 학습 전부 → 유보 · 노트 727 이 쓴 것 ===", flush=True)
    B = matrix(fit_all, is_te, 20, "전부→유보")

    #: 목표마다 고르는 소스(자기 제외 · 양수인 것)
    def picks(M):
        out = {}
        for t in doms:
            out[t] = sorted(s for s in M if t in M[s] and s != t and M[s][t] > 0)
        return out
    pa, pb = picks(A), picks(B)
    common = [t for t in doms if (t in {x for r in A.values() for x in r}
                                  and t in {x for r in B.values() for x in r})]
    rows = {}
    for t in common:
        sa, sb = set(pa[t]), set(pb[t])
        cand = sorted({s for s in A if t in A[s] and s != t}
                      & {s for s in B if t in B[s] and s != t})
        if not cand:
            continue
        same = sum(1 for s in cand if (s in sa) == (s in sb))
        rows[t] = {"고를 수 있던 소스": len(cand),
                   "앞→뒤 가 고른 것": sorted(sa & set(cand)),
                   "전부→유보 가 고른 것": sorted(sb & set(cand)),
                   "부호 일치": f"{same}/{len(cand)}",
                   "자카드": round(len(sa & sb) / max(len(sa | sb), 1), 3)}
    #: 칸 값 자체의 상관
    cells = [(A[s][t], B[s][t]) for s in A if s in B
             for t in A[s] if t in B[s] and t != s]
    r = (round(float(spearmanr([c[0] for c in cells],
                               [c[1] for c in cells]).statistic), 3)
         if len(cells) > 3 else None)
    agree = sum(1 for a, b in cells if (a > 0) == (b > 0))
    print("=== 모아서 ===", flush=True)
    print(json.dumps({
        "겹치는 칸 수": len(cells),
        "**칸 값 스피어만(앞→뒤 대 전부→유보)**": r,
        "**부호 일치**": f"{agree}/{len(cells)}",
        "**부호 일치율**": round(agree / max(len(cells), 1), 3),
        "동전 던지기라면": 0.5,
        "목표별": rows,
        "고른 소스 수 앞→뒤": {t: len(pa[t]) for t in doms},
        "고른 소스 수 전부→유보": {t: len(pb[t]) for t in doms},
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
