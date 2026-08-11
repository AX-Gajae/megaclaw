# -*- coding: utf-8 -*-
"""908-ㄴ — **의미 토큰 주입.** `lab/textnn.py`(685b · 721) 의 구조를 그대로 두고
**토큰이 무엇을 담는지** 한 자리만 바꾼다.

사전등록: `docs/prereg_908b_semtoken.md` (측정 전에 파일로 남겼고 sha256 을 산출물에 박는다)

    제목 → 공유 TF-IDF(char_wb 2~4) → SVD(64) ─┐
                                                ├→ MLP(72 → Tanh(32) → 1) → 도메인 내 순위
    **토큰 원천** → nn.Embedding(K, 8) ─────────┘

🔴 **`lab/textnn.py` 를 고치지 않는다**(908 팔 제약 · 다른 에이전트가 같은 트리를 만진다).
그래서 `_pool` 을 여기 **복제**했다 — 복제는 노트 702 가 등록한 위험(재구현이 조용히
다른 물건이 된다)이므로 `wire_vs_textnn()` 로 **ㄱ 갈래가 textnn 과 같은 축을 내는지**
직접 대조한다.

갈래(`TOKENS`)
    ㄱ 도메인      dmap[도메인]                      K=11   721 재현 = 기준선
    ㄴ1 시점(월)   clip(int((yr-⌊yr⌋)*12),0,11)      K=12   계절 — 학습·유보 양쪽에 다 있다
    ㄴ2 시점(위치) 도메인 안 yr 백분위 → 8분위        K=8    지시서의 '라벨 창 위치'
    ㄷ 규모        도메인 학습행수 log10 → 4분위      K=4    888병 가중 천장
    ㄹ 결측 무늬   40축 마스크 패턴 상위 15 + 기타     K=16   899 의 빈칸

조작(팔)
    token_perm=True   토큰 색인을 행 전체에 걸쳐 순열(주변분포 보존)
    label_perm=True   학습 목표를 도메인 안에서 순열 후 재학습
    freeze_zero=True  🔴 **심은 결함** — 임베딩을 0 으로 얼린다(상수 토큰).
                      검출기(토큰 기여도 · 축 sha 대조)가 **발화해야** 한다
"""
from __future__ import annotations

import hashlib

import numpy as np

AX = "text_nn"                 # 판에 꽂는 축 이름 — 721 과 같은 자리
FOLDS = 5
NG = (2, 4)
SVD_DIM = 64
EMB_DIM = 8
HID = 32
EPOCHS = 40
LR = 3e-3
MIN_OBS = 30
MIN_LEN = 2
COLLAPSE = 0.95
N_TIMEPOS = 8                  # ㄴ2 분위 수
N_SCALE = 4                    # ㄷ 분위 수
#: ㄹ — 🔴 **상위 15개 자르기를 버리고 빈도 문턱으로 바꿨다**(측정 **전** · 사전등록 §3 정정).
#: 상위 15 로 자르면 큰 도메인의 무늬가 자리를 다 먹어 **게임·도서·시장팝업·아이돌·팝업 다섯이
#: 통째로 「기타」 한 칸**이 된다 — 즉 얇은 도메인에서 「무엇이 없는가」를 아예 못 묻는다.
#: 실측(학습 무늬 93가지 · 18,523행): 문턱 10 → K=47 · 덮음 0.9921 · **상수 도메인 0**.
MIN_PAT = 10                   # 학습 행 빈도가 이 이상인 무늬만 자기 토큰을 갖는다(+기타 1)

ARMS = ("ㄱ도메인", "ㄴ1시점월", "ㄴ2시점위치", "ㄷ규모", "ㄹ결측무늬")


# ── 자료 모으기 ────────────────────────────────────────────────────────────
def pool(data, T: float):
    """전 도메인 행을 한 통에.

    `lab/textnn.py:_pool` 의 복제 + **토큰 원천에 필요한 곁정보**(yr · 마스크 무늬).
    행 선택 규칙은 글자 그대로 같다 — 다르면 ㄱ 갈래가 721 재현이 아니게 된다.
    """
    from ingest.news_counts import titles
    uni = sorted({n for d in data.dom for n in (data.names.get(d) or [])})
    txt, dom, y, tr, te, idx, yrs, pat = [], [], [], [], [], [], [], []
    for d in data.dom:
        ts = titles(d)
        if ts is None:
            continue
        yy, yr = data.dom[d][2], data.yr[d]
        M = np.asarray(data.dom[d][1], float)
        nm = list(data.names.get(d) or [])
        col = {n: j for j, n in enumerate(nm)}
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
            tr.append(a); te.append(b); idx.append(i); yrs.append(float(yr[i]))
            pat.append(tuple(1 if (n2 in col and M[i, col[n2]] > 0) else 0
                             for n2 in uni))
    return dict(txt=txt, dom=np.array(dom), y=np.array(y, float),
                is_tr=np.array(tr), is_te=np.array(te), idx=np.array(idx),
                yr=np.array(yrs, float), pat=pat, uni=uni)


# ── 토큰 원천 ──────────────────────────────────────────────────────────────
def token_index(P: dict, arm: str) -> tuple[np.ndarray, int, dict]:
    """(행→토큰 색인, K, 배선 기록). **라벨을 안 본다**(ㄷ 의 학습행 수만 시간 분할을 본다)."""
    dom, yr, is_tr = P["dom"], P["yr"], P["is_tr"]
    doms = sorted(set(dom.tolist()))
    if arm == "ㄱ도메인":
        dmap = {d: i for i, d in enumerate(doms)}
        ti = np.array([dmap[d] for d in dom])
        return ti, len(doms), {"뜻": "도메인 하나당 토큰 하나", "사전": dmap}
    if arm == "ㄴ1시점월":
        ti = np.clip(((yr - np.floor(yr)) * 12).astype(int), 0, 11)
        return ti, 12, {"뜻": "관측 시각의 월(0~11)"}
    if arm == "ㄴ2시점위치":
        ti = np.zeros(len(yr), int)
        for d in doms:
            m = dom == d
            v = yr[m]
            # 라벨을 안 쓰는 **특성 수준** 변환(textnn._pct 와 같은 관행)
            r = v.argsort().argsort().astype(float)
            q = r / max(len(v) - 1, 1)
            ti[m] = np.clip((q * N_TIMEPOS).astype(int), 0, N_TIMEPOS - 1)
        return ti, N_TIMEPOS, {"뜻": f"도메인 안 시각 백분위를 {N_TIMEPOS} 분위"}
    if arm == "ㄷ규모":
        cnt = {d: int((is_tr & (dom == d)).sum()) for d in doms}
        lg = np.array([np.log10(max(cnt[d], 1)) for d in doms])
        edges = np.quantile(lg, np.linspace(0, 1, N_SCALE + 1)[1:-1])
        bk = {d: int(np.searchsorted(edges, lg[i], side="right"))
              for i, d in enumerate(doms)}
        ti = np.array([bk[d] for d in dom])
        return ti, N_SCALE, {"뜻": f"도메인 학습행 수 log10 을 {N_SCALE} 분위",
                             "도메인 학습행 수": cnt, "버킷": bk,
                             "경계(log10)": [float(x) for x in edges]}
    if arm == "ㄹ결측무늬":
        from collections import Counter
        c = Counter(p for p, t in zip(P["pat"], is_tr) if t)
        top = [p for p, n in sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))
               if n >= MIN_PAT]
        pmap = {p: i for i, p in enumerate(top)}
        K = len(top) + 1
        ti = np.array([pmap.get(p, K - 1) for p in P["pat"]])
        return ti, K, {
            "뜻": f"40축 마스크 무늬 · 학습 빈도 ≥ {MIN_PAT} 인 무늬마다 토큰 하나 + 기타",
            "학습 무늬 가짓수": len(c),
            "자기 토큰을 받은 무늬": len(top),
            "학습 덮음": round(sum(c[p] for p in top) / max(sum(c.values()), 1), 4),
            "기타로 간 행": int((ti == K - 1).sum())}
    raise ValueError(f"모르는 갈래: {arm}")


def sha_axis(ax: dict) -> str:
    """축 열(값·마스크)의 내용 sha256. **이름이 아니라 열을 해싱한다**(harness.fingerprint 규율)."""
    h = hashlib.sha256()
    for d in sorted(ax):
        v, m = ax[d]
        for a in (v, m):
            a = np.ascontiguousarray(np.asarray(a, np.float64))
            h.update(np.nan_to_num(a, nan=-9.87e18).tobytes())
        h.update(d.encode())
    return h.hexdigest()


def _pct(v: np.ndarray, ok: np.ndarray) -> np.ndarray:
    from .pairboot import safe_rank
    out = np.zeros(len(v), np.float32)
    if ok.sum() < 3:
        return out
    r = safe_rank(v[ok], where="semtoken908._pct") - 1.0
    out[ok] = (r / max(ok.sum() - 1, 1)).astype(np.float32)
    return out


def _to_axis(data, P, pred):
    """예측 벡터 → {도메인: (백분위값, 표시자)} + 빠진 도메인 사유."""
    out, rep = {}, {}
    dom, idx = P["dom"], P["idx"]
    for d in data.dom:
        col = np.full(len(data.dom[d][2]), np.nan)
        m = dom == d
        if m.any():
            col[idx[m]] = pred[m]
        ok = np.isfinite(col)
        if ok.sum() < MIN_OBS or len(np.unique(col[ok])) < 3:
            rep[d] = f"관측 {int(ok.sum())} · 고유값 {int(len(np.unique(col[ok])))}"
            continue
        out[d] = (_pct(col, ok), ok.astype(np.float32))
    return out, rep


# ── 본체 ───────────────────────────────────────────────────────────────────
def build(data, arm: str, T: float = 2025.0, seed: int = 685,
          folds: int = FOLDS, token_perm: bool = False,
          label_perm: bool = False, freeze_zero: bool = False,
          P: dict | None = None) -> tuple[dict, dict]:
    """({"text_nn": {도메인: (값, 표시자)}}, 배선·진단 기록)."""
    import torch
    import torch.nn as nn
    from .pairboot import safe_rank

    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer

    P = P or pool(data, T)
    txt, dom, y = P["txt"], P["dom"], P["y"]
    is_tr, is_te = P["is_tr"], P["is_te"]
    doms = sorted(set(dom.tolist()))

    ti, K, tinfo = token_index(P, arm)
    if token_perm:
        rng = np.random.default_rng(90800 + seed)
        ti = ti[rng.permutation(len(ti))]

    # 목표: **도메인 안 순위**(노트 646)
    rk = np.full(len(y), np.nan)
    for d in doms:
        m = is_tr & (dom == d)
        if m.sum() >= 2:
            rk[m] = safe_rank(y[m], where=f"semtoken908.build:{d}") / m.sum()
    if label_perm:
        rng = np.random.default_rng(90900 + seed)
        for d in doms:
            m = is_tr & (dom == d) & np.isfinite(rk)
            i = np.flatnonzero(m)
            if len(i) > 1:
                rk[i] = rk[i][rng.permutation(len(i))]
    fit_all = is_tr & np.isfinite(rk)

    # 표현은 **학습 행에서만** 적합한다(노트 645)
    V = TfidfVectorizer(analyzer="char_wb", ngram_range=NG, min_df=3,
                        max_features=40000, sublinear_tf=True)
    Xtr = V.fit_transform([txt[i] for i in np.flatnonzero(fit_all)])
    svd = TruncatedSVD(n_components=SVD_DIM, random_state=seed)
    svd.fit(Xtr)
    Z = svd.transform(V.transform(txt)).astype(np.float32)
    Z = (Z - Z[fit_all].mean(0)) / (Z[fit_all].std(0) + 1e-6)

    class Net(nn.Module):
        def __init__(self, k):
            super().__init__()
            self.emb = nn.Embedding(k, EMB_DIM)
            self.mlp = nn.Sequential(nn.Linear(SVD_DIM + EMB_DIM, HID),
                                     nn.Tanh(), nn.Linear(HID, 1))

        def forward(self, z, t, kill: bool = False):
            e = self.emb(t)
            if kill:                      # 🔴 '입력 지우기'(아키텍처.md §9.1 ⑥)
                e = torch.zeros_like(e)
            return self.mlp(torch.cat([z, e], -1)).squeeze(-1)

    def train_predict(fit_m, pred_m):
        torch.manual_seed(seed)
        net = Net(K)
        if freeze_zero:                   # 🔴 심은 결함 — 상수(0) 토큰
            with torch.no_grad():
                net.emb.weight.zero_()
            net.emb.weight.requires_grad_(False)
        opt = torch.optim.Adam([p for p in net.parameters() if p.requires_grad], lr=LR)
        zf = torch.tensor(Z[fit_m]); tf_ = torch.tensor(ti[fit_m])
        yf = torch.tensor(rk[fit_m], dtype=torch.float32)
        for _ in range(EPOCHS):
            opt.zero_grad()
            ((net(zf, tf_) - yf) ** 2).mean().backward()
            opt.step()
        net.eval()
        with torch.no_grad():
            zp = torch.tensor(Z[pred_m]); tp = torch.tensor(ti[pred_m])
            p = net(zp, tp).numpy()
            p0 = net(zp, tp, kill=True).numpy()
        return p, p0, net

    pred = np.full(len(y), np.nan)
    pred0 = np.full(len(y), np.nan)
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
        pred[hold], pred0[hold], _ = train_predict(km, hm)
    ite = np.flatnonzero(is_te)
    net_full = None
    if len(ite):
        hm = np.zeros(len(y), bool); hm[ite] = True
        pred[ite], pred0[ite], net_full = train_predict(fit_all, hm)

    ax, rep = _to_axis(data, P, pred)
    ax0, _ = _to_axis(data, P, pred0)

    # ── 붕괴 검사(721 의 (다)) — **쓰인 토큰만** 본다
    coll = None
    if net_full is not None and K > 1:
        used = sorted(set(ti.tolist()))
        E = net_full.emb.weight.detach().numpy()[used]
        nrm = np.linalg.norm(E, axis=1, keepdims=True)
        if len(used) > 1 and float(nrm.min()) > 0:
            n2 = E / (nrm + 1e-9)
            C = n2 @ n2.T
            off = C[~np.eye(len(used), dtype=bool)]
            coll = {"쓰인 토큰": len(used), "코사인 평균": round(float(off.mean()), 3),
                    "코사인 최대": round(float(off.max()), 3), "붕괴 문턱": COLLAPSE,
                    "**붕괴?**": bool(off.mean() >= COLLAPSE)}
        else:
            coll = {"쓰인 토큰": len(used), "🔴": "노름 0 또는 토큰 1개 — 못 잰다"}

    # ── 토큰 기여도(입력 지우기)
    pm = np.isfinite(pred) & np.isfinite(pred0)
    den = float(np.linalg.norm(pred[pm]))
    contrib = float(np.linalg.norm(pred[pm] - pred0[pm]) / den) if den > 0 else float("nan")

    # ── 도메인별 토큰 가짓수(퇴화 진단)
    var = {d: int(len(set(ti[dom == d].tolist()))) for d in doms}

    npar = sum(p.numel() for p in Net(K).parameters())
    info = {
        "갈래": arm, "K": K, "토큰 뜻": tinfo, "EMB_DIM": EMB_DIM,
        "파라미터": int(npar),
        "조작": {"token_perm": token_perm, "label_perm": label_perm,
                "freeze_zero": freeze_zero, "seed": seed},
        "한 통 학습": int(fit_all.sum()), "한 통 유보": int(is_te.sum()),
        "붙은 도메인": sorted(ax), "🔴 빠진 도메인": rep,
        "임베딩 붕괴": coll,
        "토큰 기여도 ‖p−p(토큰0)‖/‖p‖": round(contrib, 6),
        "축 sha256": sha_axis(ax),
        "축 sha256(토큰 0)": sha_axis(ax0),
        "🔴 sha 가 갈리나(토큰이 출력에 닿나)": sha_axis(ax) != sha_axis(ax0),
        "도메인별 토큰 가짓수": var,
        "도메인 안에서 토큰이 상수인 도메인": sorted([d for d, v in var.items() if v <= 1]),
        "⚠ 설계상 도메인당 토큰 하나인 갈래인가": arm in ("ㄱ도메인", "ㄷ규모"),
        "🔴 설계에 없는 퇴화": (sorted([d for d, v in var.items() if v <= 1])
                          if arm not in ("ㄱ도메인", "ㄷ규모") else []),
    }
    return ({AX: ax} if ax else {}), info


# ── 배선: ㄱ 갈래가 `lab/textnn` 과 같은 물건인가 ──────────────────────────
def wire_vs_textnn(data, T: float = 2025.0, seed: int = 685) -> dict:
    """🔴 `pool` 복제가 조용히 다른 물건이 되지 않았는지 **직접 대조**한다(노트 702).

    `lab/textnn.build` 는 `nn.Embedding(도메인)` 이고 이 파일의 ㄱ 갈래와 **같은 구조**다.
    같은 씨앗이면 축 sha256 이 **비트 동일**해야 한다.
    """
    from . import textnn as NN
    r = NN.build(data, T=T, seed=seed)
    mine, _ = build(data, "ㄱ도메인", T=T, seed=seed)
    a = r.get(NN.AX, {})
    b = mine.get(AX, {})
    return {"textnn 축 sha256": sha_axis(a) if a else None,
            "semtoken908 ㄱ 축 sha256": sha_axis(b) if b else None,
            "**비트 동일**": bool(a and b and sha_axis(a) == sha_axis(b)),
            "textnn 붙은 도메인": sorted(a), "ㄱ 붙은 도메인": sorted(b)}


def abs_time_degeneracy(P: dict, T: float, n_bucket: int = 8) -> dict:
    """🔴 **재지 않기로 한 갈래(ㄴ0 절대시각)의 퇴화를 실측으로 기록한다.**

    학습 분위로 버킷을 만들면 유보(전부 `yr≥T`)가 몇 개 버킷에 들어가나.
    """
    yr, is_tr, is_te = P["yr"], P["is_tr"], P["is_te"]
    edges = np.quantile(yr[is_tr], np.linspace(0, 1, n_bucket + 1)[1:-1])
    b_tr = np.searchsorted(edges, yr[is_tr], side="right")
    b_te = np.searchsorted(edges, yr[is_te], side="right")
    return {"버킷 수": n_bucket,
            "학습 버킷 점유": {int(k): int(v) for k, v in
                          zip(*np.unique(b_tr, return_counts=True))},
            "유보 버킷 점유": {int(k): int(v) for k, v in
                          zip(*np.unique(b_te, return_counts=True))},
            "유보가 차지한 버킷 수": int(len(np.unique(b_te))),
            "🔴 구성상 퇴화인가": bool(len(np.unique(b_te)) <= 1)}
