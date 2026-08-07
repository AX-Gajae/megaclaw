"""노트 728 — **소스 고르기를 누출 없이.** T5 의 마지막 문.

절차:
    앞(<2024)에서 소스별 트렁크 → 뒤(2024)에서 목표 채점 → **누출 없는 행렬**
    목표마다 양수 소스만 골라(자기 포함) 트렁크 적합
    목표 학습 행은 K겹(5) · 유보 행은 학습 전체로 예측(노트 645)
    그 열 하나를 판에 넣어 세 팔로 신호 몫

**유보는 소스 고르기에 한 번도 안 쓴다** --- 그것이 이 실험의 주제다.
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

from lab import forms, guards as G, loop as L, textnn as NN
from lab.harness import evaluate

T = 2025.0
SPLIT = 2024.0          # 앞 < SPLIT <= 뒤 < T
TRUNK_SEEDS = (0, 1, 2, 3)
BOARD_SEEDS = tuple(range(12))
FOLDS = 5
MIN_SRC = 40
MIN_BACK = 20           # 뒤 행이 이만큼은 있어야 행렬 칸을 만든다
CLS = forms.REGISTRY["F18_bagboost"]["cls"]
AX = "text_pick"


def base():
    from lab import genaxes, grpaxes
    e = {**L._trendsub(zero_is_data=True), **L._calsub(), **L._wikisub(),
         **L._tag(), **L._fund(), **L._rawsub(), **genaxes.build()}
    e.update(grpaxes.build())
    return e


def shell(extra):
    return L._idol(lambda: dict(extra), mode="cut", with_wiki=True,
                   with_trend=True, wide_post=True, wide_pop="grades")


class Net(nn.Module):
    def __init__(self, nd):
        super().__init__()
        self.emb = nn.Embedding(nd, NN.EMB_DIM)
        self.mlp = nn.Sequential(nn.Linear(NN.SVD_DIM + NN.EMB_DIM, NN.HID),
                                 nn.Tanh(), nn.Linear(NN.HID, 1))

    def forward(self, z, d):
        return self.mlp(torch.cat([z, self.emb(d)], -1)).squeeze(-1)


def board(data):
    vals, per = [], {}
    for s in BOARD_SEEDS:
        sc = evaluate(lambda s=s: CLS(seed=s), data, T=T)
        vals.append(float(data.pooled(sc, T=T)))
        for k, v in sc.items():
            if np.isfinite(v):
                per.setdefault(k, []).append(float(v))
    return {"판": round(float(np.mean(vals)), 4),
            "씨앗SD": round(float(np.std(vals, ddof=1)), 4),
            "도메인": {k: round(float(np.mean(a)), 4) for k, a in per.items()}}


def main():
    d0 = shell(base())
    txt, dom, y, is_tr, is_te, idx = NN._pool(d0, T)
    # 연도를 다시 얻는다 --- `_pool` 이 안 돌려주므로 도메인별로 맞춘다
    yr = np.full(len(dom), np.nan)
    pos = {d: 0 for d in set(dom.tolist())}
    for i, d in enumerate(dom):
        yr[i] = d0.yr[d][idx[i]]
    doms = sorted(set(dom.tolist()))
    dmap = {d: i for i, d in enumerate(doms)}
    di = np.array([dmap[d] for d in dom])

    front = is_tr & (yr < SPLIT)
    back = is_tr & (yr >= SPLIT)
    rk = np.full(len(y), np.nan)
    for d in doms:
        m = is_tr & (dom == d)
        if m.sum() >= 2:
            rk[m] = rankdata(y[m]) / m.sum()
    fit_all = is_tr & np.isfinite(rk)
    fit_front = front & np.isfinite(rk)

    V = TfidfVectorizer(analyzer="char_wb", ngram_range=NN.NG, min_df=3,
                        max_features=40000, sublinear_tf=True)
    V.fit([txt[i] for i in np.flatnonzero(fit_all)])
    svd = TruncatedSVD(n_components=NN.SVD_DIM, random_state=685)
    svd.fit(V.transform([txt[i] for i in np.flatnonzero(fit_all)]))
    Z = svd.transform(V.transform(txt)).astype(np.float32)
    Z = (Z - Z[fit_all].mean(0)) / (Z[fit_all].std(0) + 1e-6)
    print(json.dumps({"앞": int(fit_front.sum()), "뒤": int(back.sum()),
                      "유보": int(is_te.sum()),
                      "앞 도메인별": {d: int((fit_front & (dom == d)).sum()) for d in doms},
                      "뒤 도메인별": {d: int((back & (dom == d)).sum()) for d in doms}},
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

    def pred(net, m):
        with torch.no_grad():
            return net(torch.tensor(Z[m]), torch.tensor(di[m])).numpy()

    # ── ① 누출 없는 행렬: 앞에서 학습 · 뒤에서 채점
    print("=== ① 누출 없는 행렬(앞 → 뒤) ===", flush=True)
    srcs = [d for d in doms if (fit_front & (dom == d)).sum() >= MIN_SRC]
    MAT = {}
    for s_dom in srcs:
        m = fit_front & (dom == s_dom)
        acc = {t: [] for t in doms}
        for sd in TRUNK_SEEDS:
            net = train(m, sd)
            for t in doms:
                bm = back & (dom == t)
                if bm.sum() < MIN_BACK:
                    continue
                p = pred(net, bm)
                yy = y[bm]
                ok = np.isfinite(p) & np.isfinite(yy)
                if ok.sum() < MIN_BACK or len(np.unique(p[ok])) < 3:
                    continue
                acc[t].append(float(spearmanr(p[ok], yy[ok]).statistic))
        MAT[s_dom] = {t: round(float(np.mean(a)), 4) for t, a in acc.items() if a}
        print(f"  {s_dom} → " + json.dumps(MAT[s_dom], ensure_ascii=False), flush=True)

    # ── ② 목표마다 양수 소스 고르기(자기 포함)
    picks = {}
    for t in doms:
        good = [s for s in MAT if t in MAT[s] and s != t and MAT[s][t] > 0]
        picks[t] = sorted(set(good) | {t})
    print(json.dumps({"고른 소스": picks}, ensure_ascii=False, indent=1), flush=True)

    # ── ③ 축 만들기 --- 목표 학습 행은 K겹, 유보는 학습 전체
    print("=== ③ 축을 만든다 ===", flush=True)
    rng = np.random.default_rng(728)
    col = {}
    rep = {}
    for t in doms:
        pool = np.isin(dom, picks[t]) & fit_all
        own = fit_all & (dom == t)
        oi = np.flatnonzero(own)
        if len(oi) < 20 or pool.sum() < MIN_SRC:
            rep[t] = f"건너뜀(자기 {len(oi)} · 풀 {int(pool.sum())})"
            continue
        raw = np.full(len(y), np.nan)
        order = rng.permutation(len(oi))
        for f in range(FOLDS):
            hold = oi[order[f::FOLDS]]
            if len(hold) == 0:
                continue
            hm = np.zeros(len(y), bool); hm[hold] = True
            ps = []
            for sd in TRUNK_SEEDS:
                ps.append(pred(train(pool & ~hm, sd), hm))
            raw[hold] = np.mean(ps, axis=0)
        tm = is_te & (dom == t)
        if tm.sum():
            ps = [pred(train(pool, sd), tm) for sd in TRUNK_SEEDS]
            raw[tm] = np.mean(ps, axis=0)
        # 도메인 안 백분위로 넣는다(노트 646)
        n = len(d0.dom[t][2])
        c = np.full(n, np.nan)
        mm = np.isfinite(raw) & (dom == t)
        c[idx[mm]] = raw[mm]
        ok = np.isfinite(c)
        if ok.sum() < 30 or len(np.unique(c[ok])) < 3:
            rep[t] = f"열부족({int(ok.sum())})"
            continue
        col[t] = (NN._pct(c, ok), ok.astype(np.float32))
        rep[t] = {"관측": int(ok.sum()), "소스 수": len(picks[t])}
    print(json.dumps({"축 붙은 도메인": sorted(col), "보고": rep},
                     ensure_ascii=False), flush=True)

    # ── ④ 판 세 팔
    print("=== ④ 판 ===", flush=True)
    b0 = board(d0)
    print(json.dumps({"없이": b0["판"], "씨앗SD": b0["씨앗SD"]}, ensure_ascii=False), flush=True)
    d1 = shell({**base(), AX: col})
    b1 = board(d1)
    print(json.dumps({"진짜": b1["판"], "씨앗SD": b1["씨앗SD"]}, ensure_ascii=False), flush=True)
    plac = {}
    for dm, (v, m) in col.items():
        v2 = np.asarray(v, float).copy()
        ii = np.flatnonzero(np.asarray(m) > 0)
        if len(ii) > 1:
            sh = v2[ii].copy(); rng.shuffle(sh); v2[ii] = sh
        plac[dm] = (v2, m)
    d2 = shell({**base(), AX: plac})
    b2 = board(d2)
    print(json.dumps({"위약": b2["판"], "씨앗SD": b2["씨앗SD"]}, ensure_ascii=False), flush=True)

    sig = round(b1["판"] - b2["판"], 4)
    net_ = round(b1["판"] - b0["판"], 4)
    W = d0.weights(T); tot = sum(W.values())
    per = {}
    for dm in set(b1["도메인"]) & set(b2["도메인"]):
        per[dm] = {"신호 몫": round(b1["도메인"][dm] - b2["도메인"][dm], 4),
                   "유보": W.get(dm, 0),
                   "판 기여": round((b1["도메인"][dm] - b2["도메인"][dm])
                                 * W.get(dm, 0) / tot, 5)}
    def drop(dm):
        num = sum(per[d]["신호 몫"] * W[d] for d in per if d != dm and d in W)
        den = sum(W[d] for d in per if d != dm and d in W)
        return round(num / den, 4) if den else None
    # 누출 없는 행렬 대 노트 727 유보 행렬
    OLD = {"게임": {"도서": 0.198, "만화": -0.076, "애니": -0.282},
           "웹툰": {"애니": 0.207, "아이돌": -0.426}}
    print("=== 모아서 ===", flush=True)
    print(json.dumps({
        "없이": b0["판"], "진짜": b1["판"], "위약": b2["판"],
        "**신호 몫**": sig, "**순효과**": net_,
        "문턱": 0.0045, "노트 721 전부 공유": 0.0106, "노트 695 도메인별 축": 0.0119,
        "판정 (가) 721 초과": sig > 0.0106,
        "판정 (나) 문턱 밖": sig > 0.0045,
        "판정 (다) 시장팝업 뺀 판": drop("시장팝업"),
        "도메인별": dict(sorted(per.items(), key=lambda x: -abs(x[1]["판 기여"]))),
        "고른 소스 수": {t: len(picks[t]) for t in sorted(picks)},
        "누출없는 행렬 일부": {s: MAT[s] for s in list(MAT)[:3]},
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
