"""685b — **학습된 도메인 토큰**. 사용자 제안의 핵심 부분(노트 685).

노트 685 가 제안을 두 단계로 갈랐다.

  685a  `textaxes.build_shared` --- 어휘와 가중을 **공유**한다. 도메인 토큰은 없다.
  685b  **여기.** 도메인 임베딩을 학습해 **텍스트 표현을 도메인이 조절**하게 한다.

**왜 비선형이어야 하나.** 선형에서 도메인 원핫은 도메인별 **절편**만 움직이고,
목표가 **도메인 내 순위**라 순위는 상수 이동에 불변이다 --- 즉 원핫이 예측을
하나도 안 바꾼다. 토큰이 일을 하려면 텍스트 가중을 도메인이 조절해야 하고
선형에서 그것은 `특성 ⊗ 도메인` 이며 그러면 다시 도메인별 모형이다(공유가
사라진다). **그래서 여기서만 '도메인 토큰' 이라는 말이 뜻을 갖는다.**

설계는 작게 간다 --- `state/fieldmodel` 의 설계 ④(파라미터 10만 이하)를 따른다.

    제목 → 공유 TF-IDF → SVD(64) ─┐
                                   ├→ MLP(72→32→1) → 도메인 내 순위
    도메인 → 임베딩(8) ────────────┘

파라미터 약 **2.4천** 이다(64·32 + 32 + 11·8 + 32·1).

**누출 차단** --- 벡터화와 SVD 를 **학습 행에서만** 적합한다(노트 645). 학습 행의
예보는 K겹으로 만들고(자기 라벨을 안 본다) 유보 행은 학습 전체로 적합한 모형이
낸다. `_pct` 는 관측 행 전체에서 매기는데 그것은 이 판의 기존 관행과 같다
(라벨을 안 보는 특성 수준 변환이다).

**시험 (다) --- 임베딩이 붕괴하나.** 도메인 임베딩끼리 코사인이 **0.95 이상**이면
토큰이 아무 일도 안 하는 것이므로 뺀다. 노트 589 가 *'이름표 열은 부호로
채점하지 않는다'* 를 쟀는데, 여기서는 **임베딩이 이름표인지 눈금인지**를 본다.
"""
from __future__ import annotations

import json

import numpy as np

AX = "text_nn"
FOLDS = 5
NG = (2, 4)
SVD_DIM = 64
EMB_DIM = 8
HID = 32
EPOCHS = 40
LR = 3e-3
MIN_OBS = 30
MIN_LEN = 2
COLLAPSE = 0.95      # 임베딩 코사인이 이보다 크면 붕괴로 본다

#: **마지막 `build` 의 곁정보.** 붕괴 검사를 `report` 로만 인쇄하면 부르는 쪽이
#: 그것을 판정에 쓸 수 없다(노트 720 에서 걸렸다) --- 축 사전에 넣으면
#: `harness.load` 가 축으로 오해하므로 여기 남긴다.
LAST: dict = {}


def _pct(v: np.ndarray, ok: np.ndarray) -> np.ndarray:
    from scipy.stats import rankdata
    out = np.zeros(len(v), np.float32)
    if ok.sum() < 3:
        return out
    r = rankdata(v[ok]) - 1.0
    out[ok] = (r / max(ok.sum() - 1, 1)).astype(np.float32)
    return out


def _pool(data, T: float):
    """전 도메인 행을 한 통에. (텍스트, 도메인, 라벨, 학습?, 유보?, 도메인내 위치)"""
    from ingest.news_counts import titles
    txt, dom, y, tr, te, idx = [], [], [], [], [], []
    for d in data.dom:
        ts = titles(d)
        if ts is None:
            continue
        yy, yr = data.dom[d][2], data.yr[d]
        n = min(len(ts), len(yy), len(yr))
        for i in range(n):
            t0 = str(ts[i]).strip()
            if len(t0) < MIN_LEN or not np.isfinite(yr[i]):
                continue
            a = bool(np.isfinite(yy[i]) and yr[i] < T)
            b = bool(yr[i] >= T)
            if not (a or b):
                continue
            txt.append(t0); dom.append(d); y.append(yy[i])
            tr.append(a); te.append(b); idx.append(i)
    return (txt, np.array(dom), np.array(y, float),
            np.array(tr), np.array(te), np.array(idx))


def build(data, T: float = 2025.0, folds: int = FOLDS, seed: int = 685,
          report: bool = False) -> dict:
    """{"text_nn": {도메인: (백분위값, 표시자)}} + 임베딩 붕괴 검사."""
    try:
        import torch
        import torch.nn as nn
    except ImportError:
        return {"오류": "torch 없음"}
    from scipy.stats import rankdata
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer

    txt, dom, y, is_tr, is_te, idx = _pool(data, T)
    if is_tr.sum() < 200:
        return {}
    doms = sorted(set(dom.tolist()))
    dmap = {d: i for i, d in enumerate(doms)}
    di = np.array([dmap[d] for d in dom])

    # 목표: **도메인 안 순위** --- 라벨 눈금이 도메인 지시자가 되지 않게(노트 646)
    rk = np.full(len(y), np.nan)
    for d in doms:
        m = is_tr & (dom == d)
        if m.sum() >= 2:
            rk[m] = rankdata(y[m]) / m.sum()
    fit_all = is_tr & np.isfinite(rk)

    # 표현은 **학습 행에서만** 적합한다(노트 645)
    V = TfidfVectorizer(analyzer="char_wb", ngram_range=NG, min_df=3,
                        max_features=40000, sublinear_tf=True)
    Xtr_raw = V.fit_transform([txt[i] for i in np.flatnonzero(fit_all)])
    svd = TruncatedSVD(n_components=SVD_DIM, random_state=seed)
    svd.fit(Xtr_raw)
    Z = svd.transform(V.transform(txt)).astype(np.float32)
    Z = (Z - Z[fit_all].mean(0)) / (Z[fit_all].std(0) + 1e-6)   # 학습 통계로만

    class Net(nn.Module):
        def __init__(self, nd):
            super().__init__()
            self.emb = nn.Embedding(nd, EMB_DIM)
            self.mlp = nn.Sequential(nn.Linear(SVD_DIM + EMB_DIM, HID),
                                     nn.Tanh(), nn.Linear(HID, 1))

        def forward(self, z, d):
            return self.mlp(torch.cat([z, self.emb(d)], -1)).squeeze(-1)

    def train_predict(fit_m, pred_m):
        torch.manual_seed(seed)
        net = Net(len(doms))
        opt = torch.optim.Adam(net.parameters(), lr=LR)
        zf = torch.tensor(Z[fit_m]); df = torch.tensor(di[fit_m])
        tf = torch.tensor(rk[fit_m], dtype=torch.float32)
        for _ in range(EPOCHS):
            opt.zero_grad()
            loss = ((net(zf, df) - tf) ** 2).mean()
            loss.backward(); opt.step()
        net.eval()
        with torch.no_grad():
            p = net(torch.tensor(Z[pred_m]), torch.tensor(di[pred_m])).numpy()
        return p, net

    pred = np.full(len(y), np.nan)
    itr = np.flatnonzero(fit_all)
    rng = np.random.default_rng(seed)
    order = rng.permutation(len(itr))
    for f in range(folds):
        hold = itr[order[f::folds]]
        keep = np.setdiff1d(itr, hold)
        if len(keep) < 50 or len(hold) == 0:
            continue
        km = np.zeros(len(y), bool); km[keep] = True
        hm = np.zeros(len(y), bool); hm[hold] = True
        pred[hold], _ = train_predict(km, hm)
    ite = np.flatnonzero(is_te)
    net_full = None
    if len(ite):
        hm = np.zeros(len(y), bool); hm[ite] = True
        pred[ite], net_full = train_predict(fit_all, hm)

    # 시험 (다) --- 임베딩 붕괴
    coll = None
    if net_full is not None:
        E = net_full.emb.weight.detach().numpy()
        n = E / (np.linalg.norm(E, axis=1, keepdims=True) + 1e-9)
        C = n @ n.T
        off = C[~np.eye(len(doms), dtype=bool)]
        coll = {"코사인 평균": round(float(off.mean()), 3),
                "코사인 최대": round(float(off.max()), 3),
                "붕괴 문턱": COLLAPSE,
                "**붕괴?**": bool(off.mean() >= COLLAPSE)}

    out, rep = {}, {}
    for d in data.dom:
        col = np.full(len(data.dom[d][2]), np.nan)
        m = dom == d
        if m.any():
            col[idx[m]] = pred[m]
        ok = np.isfinite(col)
        if ok.sum() < MIN_OBS or len(np.unique(col[ok])) < 3:
            rep[d] = f"관측 {int(ok.sum())}"
            continue
        out[d] = (_pct(col, ok), ok.astype(np.float32))
        rep[d] = {"관측": int(ok.sum()),
                  "예보 평균": round(float(np.nanmean(col[ok])), 4),
                  "예보 SD": round(float(np.nanstd(col[ok])), 4)}
    res = {AX: out} if out else {}
    LAST.clear()
    LAST.update({"붕괴": coll, "도메인": doms, "붙은 도메인": sorted(out),
                 "한 통 학습": int(fit_all.sum()), "한 통 유보": int(is_te.sum()),
                 "도메인별": rep})
    if report:
        npar = sum(p.numel() for p in Net(len(doms)).parameters())
        print(json.dumps({"축": list(res), "붙은 도메인": sorted(out),
                          "파라미터": npar, "한 통 학습": int(fit_all.sum()),
                          "한 통 유보": int(is_te.sum()),
                          "**임베딩 붕괴 검사**": coll, "도메인별": rep},
                         ensure_ascii=False, indent=1), flush=True)
    return res
