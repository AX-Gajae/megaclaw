"""노트 726 — **짝별 전이 행렬 11×11.** 누가 누구를 돕나. 씨앗 4.

소스 도메인 하나만으로 트렁크를 적합하고 **다른 열 도메인의 유보 예보**를 잰다.
대각선은 자기 학습이므로 참고값이다(누출 아님 --- 학습 행과 유보 행이 시간으로
갈려 있다).

**판정**: 행렬이 대칭이면 '비슷한 도메인끼리' 이고, 비대칭이면 **'주는 도메인' 과
'받는 도메인' 이 따로 있다.**
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
SEEDS = (0, 1, 2, 3)
MIN_SRC = 40          # 소스 학습 행이 이만큼은 있어야 트렁크를 적합한다


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
    doms = sorted(set(dom.tolist()))
    dmap = {d: i for i, d in enumerate(doms)}
    di = np.array([dmap[d] for d in dom])
    rk = np.full(len(y), np.nan)
    for d in doms:
        m = is_tr & (dom == d)
        if m.sum() >= 2:
            rk[m] = rankdata(y[m]) / m.sum()
    fit_all = is_tr & np.isfinite(rk)

    V = TfidfVectorizer(analyzer="char_wb", ngram_range=NN.NG, min_df=3,
                        max_features=40000, sublinear_tf=True)
    V.fit([txt[i] for i in np.flatnonzero(fit_all)])
    svd = TruncatedSVD(n_components=NN.SVD_DIM, random_state=685)
    svd.fit(V.transform([txt[i] for i in np.flatnonzero(fit_all)]))
    Z = svd.transform(V.transform(txt)).astype(np.float32)
    Z = (Z - Z[fit_all].mean(0)) / (Z[fit_all].std(0) + 1e-6)

    def train(fit_m, seed):
        torch.manual_seed(seed)
        net = Net(len(doms))
        opt = torch.optim.Adam(net.parameters(), lr=NN.LR)
        zf = torch.tensor(Z[fit_m]); df = torch.tensor(di[fit_m])
        tf = torch.tensor(rk[fit_m], dtype=torch.float32)
        for _ in range(NN.EPOCHS):
            opt.zero_grad()
            ((net(zf, df) - tf) ** 2).mean().backward()
            opt.step()
        net.eval()
        return net

    def score(net, d):
        m = is_te & (dom == d)
        with torch.no_grad():
            p = net(torch.tensor(Z[m]), torch.tensor(di[m])).numpy()
        yy = y[m]
        ok = np.isfinite(p) & np.isfinite(yy)
        if ok.sum() < 20 or len(np.unique(p[ok])) < 3:
            return None
        return float(spearmanr(p[ok], yy[ok]).statistic)

    W = data.weights(T)
    ntr = {d: int((fit_all & (dom == d)).sum()) for d in doms}
    srcs = [d for d in doms if ntr[d] >= MIN_SRC]
    print(json.dumps({"소스 가능": {d: ntr[d] for d in srcs},
                      "제외": {d: ntr[d] for d in doms if d not in srcs}},
                     ensure_ascii=False), flush=True)

    M = {}
    for s_dom in srcs:
        m = fit_all & (dom == s_dom)
        row = {}
        acc = {t: [] for t in doms}
        for sd in SEEDS:
            net = train(m, sd)
            for t in doms:
                v = score(net, t)
                if v is not None:
                    acc[t].append(v)
        for t in doms:
            if acc[t]:
                row[t] = round(float(np.mean(acc[t])), 4)
        M[s_dom] = row
        print(f"  소스 {s_dom} ({ntr[s_dom]}행) → " +
              json.dumps({k: v for k, v in row.items() if k != s_dom},
                         ensure_ascii=False), flush=True)

    tgts = sorted({t for r in M.values() for t in r})
    give = {s: round(float(np.mean([v for t, v in M[s].items() if t != s])), 4)
            for s in M}
    take = {t: round(float(np.mean([M[s][t] for s in M
                                    if t in M[s] and s != t])), 4)
            for t in tgts}
    thr = {t: round(0.0045 * np.sqrt(3369 / max(W.get(t, 1), 1)), 4) for t in tgts}
    # 비대칭: M[a][b] 대 M[b][a]
    asym = []
    for a in M:
        for b in M:
            if a >= b or b not in M[a] or a not in M.get(b, {}):
                continue
            asym.append({"짝": f"{a}↔{b}", f"{a}→{b}": M[a][b],
                         f"{b}→{a}": M[b][a],
                         "차": round(M[a][b] - M[b][a], 4)})
    asym.sort(key=lambda x: -abs(x["차"]))
    pairs = [(M[a][b], M[b][a]) for a in M for b in M
             if a < b and b in M[a] and a in M.get(b, {})]
    sym_r = (round(float(spearmanr([p[0] for p in pairs],
                                   [p[1] for p in pairs]).statistic), 3)
             if len(pairs) > 3 else None)
    print("=== 모아서 ===", flush=True)
    print(json.dumps({
        "행렬": M,
        "**주는 힘**(행 평균 · 자기 제외)": dict(sorted(give.items(), key=lambda x: -x[1])),
        "**받는 힘**(열 평균 · 자기 제외)": dict(sorted(take.items(), key=lambda x: -x[1])),
        "도메인 문턱(노트 717)": thr,
        "**대칭성** --- a→b 대 b→a 스피어만": sym_r,
        "가장 비대칭인 짝 여섯": asym[:6],
        "소스 학습행": {d: ntr[d] for d in srcs},
        "유보 채점": {t: W.get(t, 0) for t in tgts},
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
