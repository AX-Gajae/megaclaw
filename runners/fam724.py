"""노트 724 — **계열인가 크기인가.** 행수를 맞춘 팔로 가른다. 씨앗 4.

팔 셋(목표 도메인 d 마다):
    계열 안            d 의 형제만으로 학습
    계열 밖            계열이 다른 도메인만으로
    계열 밖 · 행수 맞춤  계열 밖에서 **계열 안과 같은 행수**만 뽑아

**셋째가 없으면 아무것도 못 가른다.**
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
#: **내 눈이 묶은 것이고 자료가 정한 것이 아니다**(노트 724 사전등록에 명시).
FAM = {"만화": "일본 만화·애니", "애니": "일본 만화·애니", "세계애니": "일본 만화·애니",
       "웹툰": "한국 IP", "시장팝업": "한국 IP", "팝업": "한국 IP", "아이돌": "한국 IP",
       "모바일": "앱·게임", "게임": "앱·게임",
       "펀딩": "그밖", "도서": "그밖"}


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
    print(json.dumps({"도메인": doms, "한 통 학습": int(fit_all.sum()),
                      "모수": sum(p.numel() for p in Net(len(doms)).parameters())},
                     ensure_ascii=False), flush=True)

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
    rng = np.random.default_rng(724)
    out = {}
    for d in doms:
        fam = FAM.get(d)
        sib = fit_all & (dom != d) & np.array([FAM.get(x) == fam for x in dom])
        out_f = fit_all & np.array([FAM.get(x) != fam for x in dom])
        n_sib = int(sib.sum())
        if n_sib < 40 or int(out_f.sum()) < 40:
            print(json.dumps({d: {"건너뜀": f"계열안 {n_sib} · 계열밖 {int(out_f.sum())}"}},
                             ensure_ascii=False), flush=True)
            continue
        arms = {"계열 안": [], "계열 밖": [], "계열 밖 · 행수 맞춤": []}
        for s in SEEDS:
            for tag, m in (("계열 안", sib), ("계열 밖", out_f)):
                v = score(train(m, s), d)
                if v is not None:
                    arms[tag].append(v)
            # **행수 맞춤** --- 씨앗마다 다시 뽑아 뽑기 운을 평균한다
            oi = np.flatnonzero(out_f)
            pick = rng.choice(oi, size=min(n_sib, len(oi)), replace=False)
            mm = np.zeros(len(dom), bool); mm[pick] = True
            v = score(train(mm, s), d)
            if v is not None:
                arms["계열 밖 · 행수 맞춤"].append(v)
        thr = 0.0045 * np.sqrt(3369 / max(W.get(d, 1), 1))
        r = {t: (round(float(np.mean(a)), 4) if a else None) for t, a in arms.items()}
        r["**계열 안 − 밖·맞춤**"] = (round(r["계열 안"] - r["계열 밖 · 행수 맞춤"], 4)
                                if r["계열 안"] is not None
                                and r["계열 밖 · 행수 맞춤"] is not None else None)
        r.update({"계열": fam, "형제 학습행": n_sib,
                  "계열밖 학습행": int(out_f.sum()),
                  "유보 채점": W.get(d, 0),
                  "그 도메인 문턱(노트 717)": round(float(thr), 4),
                  "씨앗SD(계열 안)": round(float(np.std(arms["계열 안"])), 4)})
        out[d] = r
        print(json.dumps({d: r}, ensure_ascii=False), flush=True)

    jp = [d for d in out if out[d]["계열"] == "일본 만화·애니"]
    other = [d for d in out if out[d]["계열"] != "일본 만화·애니"]
    def pos(ks):
        v = [out[k]["**계열 안 − 밖·맞춤**"] for k in ks
             if out[k]["**계열 안 − 밖·맞춤**"] is not None]
        return f"{sum(1 for x in v if x > 0)}/{len(v)}"
    def beat(ks):
        return f"{sum(1 for k in ks if (out[k]['**계열 안 − 밖·맞춤**'] or 0) > out[k]['그 도메인 문턱(노트 717)'])}/{len(ks)}"
    print("=== 모아서 ===", flush=True)
    print(json.dumps({
        "도메인별": out,
        "**JP 셋 (계열 안 − 밖·맞춤) 양수**": pos(jp),
        "**JP 셋 문턱 밖 양수**": beat(jp),
        "나머지 양수": pos(other), "나머지 문턱 밖 양수": beat(other),
        "판정": None,
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
