"""노트 722 — **도메인 하나씩 빼서 트렁크를 다시 적합한다.** LODO · 씨앗 4.

도메인 d 의 유보 스피어만을 셋으로 갈라 읽는다:
    전부   그 도메인이 지금 받는 예보 품질
    LODO   **자기 행이 하나도 안 든 트렁크**의 품질 → **순수 전이**
    Δ      자기 행이 보탠 몫

**판 적합은 안 한다** --- 축 품질을 직접 재므로 트렁크(2.4천 모수)만 돌린다.
`lab/textnn` 의 내부를 그대로 옮기지 않고 **같은 하이퍼로 여기서 다시 짠다** ---
노트 702 가 재구현으로 기제를 지운 자리이므로, **기제(SVD ⊕ 도메인 임베딩 → MLP)를
그대로 옮겼는지 파라미터 수로 확인한다.**
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
from lab.harness import Data

T = 2025.0
SEEDS = (0, 1, 2, 3)


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
    """**노트 721 과 같은 기제여야 한다** --- SVD ⊕ 도메인 임베딩 → MLP."""

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
    print(json.dumps({"도메인": doms, "한 통 학습": int(fit_all.sum()),
                      "한 통 유보": int(is_te.sum()),
                      "모수": sum(p.numel() for p in Net(len(doms)).parameters()),
                      "노트 721 모수와 같아야 한다": 2497},
                     ensure_ascii=False), flush=True)

    # 표현은 **전부 넣은 학습 행**으로 한 번만 만든다 --- LODO 는 *신경망 학습*
    # 에서 빼는 것이고 어휘·SVD 까지 빼면 두 가지가 섞인다.
    V = TfidfVectorizer(analyzer="char_wb", ngram_range=NN.NG, min_df=3,
                        max_features=40000, sublinear_tf=True)
    Xtr = V.fit_transform([txt[i] for i in np.flatnonzero(fit_all)])
    svd = TruncatedSVD(n_components=NN.SVD_DIM, random_state=685)
    svd.fit(Xtr)
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

    def score(net, dom_name):
        m = is_te & (dom == dom_name)
        if m.sum() < 20:
            return None, int(m.sum())
        with torch.no_grad():
            p = net(torch.tensor(Z[m]), torch.tensor(di[m])).numpy()
        yy = y[m]
        ok = np.isfinite(p) & np.isfinite(yy)
        if ok.sum() < 20 or len(np.unique(p[ok])) < 3:
            return None, int(ok.sum())
        return float(spearmanr(p[ok], yy[ok]).statistic), int(ok.sum())

    # ── 전부 넣은 트렁크
    full = {d: [] for d in doms}
    for s in SEEDS:
        net = train(fit_all, s)
        for d in doms:
            v, _n = score(net, d)
            if v is not None:
                full[d].append(v)
    print(json.dumps({"전부 넣은 트렁크":
                      {d: round(float(np.mean(v)), 4) for d, v in full.items() if v}},
                     ensure_ascii=False), flush=True)

    # ── 도메인 하나씩 빼기
    lodo = {}
    for d in doms:
        keep = fit_all & (dom != d)
        vals = []
        for s in SEEDS:
            net = train(keep, s)
            v, _n = score(net, d)
            if v is not None:
                vals.append(v)
        lodo[d] = vals
        print(f"  LODO {d}: 학습 {int(keep.sum())} · "
              f"{round(float(np.mean(vals)),4) if vals else None}", flush=True)

    # ── 곁 자들
    W = data.weights(T)
    labspan = {}
    for d in doms:
        m = is_tr & (dom == d)
        yy = y[m]
        labspan[d] = (round(float(np.nanmax(yy) - np.nanmin(yy)), 3)
                      if m.sum() > 2 else None)
    out = {}
    for d in doms:
        if not full.get(d) or not lodo.get(d):
            continue
        f = float(np.mean(full[d])); lo = float(np.mean(lodo[d]))
        ntr = int((is_tr & (dom == d)).sum())
        out[d] = {"전부": round(f, 4), "LODO": round(lo, 4),
                  "Δ(자기 행 몫)": round(f - lo, 4),
                  "LODO 유지율": round(lo / f, 3) if abs(f) > 1e-9 else None,
                  "학습 행": ntr, "유보 채점": W.get(d, 0),
                  "라벨 자리폭": labspan[d],
                  "씨앗SD(전부)": round(float(np.std(full[d])), 4)}
    ks = list(out)
    def sp(a, b):
        r = spearmanr([out[k][a] for k in ks], [out[k][b] for k in ks])
        return [round(float(r.statistic), 3), round(float(r.pvalue), 4)]
    print("=== 모아서 ===", flush=True)
    print(json.dumps({
        "도메인별": out,
        "**Δ ↔ 학습 행수 스피어만**(예측: 양수 정렬)": sp("Δ(자기 행 몫)", "학습 행"),
        "LODO ↔ 학습 행수": sp("LODO", "학습 행"),
        "Δ ↔ 라벨 자리폭": sp("Δ(자기 행 몫)", "라벨 자리폭"),
        "LODO 가 음수인 도메인": [k for k in ks if out[k]["LODO"] < 0],
        "시장팝업 유지율": out.get("시장팝업", {}).get("LODO 유지율"),
        "웹툰 Δ 대 시장팝업 Δ": [out.get("웹툰", {}).get("Δ(자기 행 몫)"),
                          out.get("시장팝업", {}).get("Δ(자기 행 몫)")],
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
