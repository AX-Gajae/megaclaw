# -*- coding: utf-8 -*-
"""궤적 파운데이션 모델 v0 — 관심 궤적 자기지도 인코더 (사이클 1041).

**왜 텍스트가 아니라 궤적인가** — 자료가 그렇게 말한다.
1036~1040 이 텍스트를 «임베더 5 × 시각 3 × 정규화 2 × 풀링 5» 로 시험했고
텍스트 단독 AUC 가 전 조합에서 0.49~0.57 · 곡선 0.6307 을 한 번도 못 넘었다
(`docs/탐색/1040.md` §4). 곡선이 이 실험실에서 유일하게 서는 표현이다.

**왜 지금까지 안 했나** — 위키 일별 패널(991 개체 × 4,060일)은 여태 `(s,o)` 창
10,654개를 «잘라내는 데만» 쓰였다. 패널 전체로 자기지도 학습을 한 적이 없다.
잘라낸 10,654 창은 패널이 담은 정보의 일부다.

## 구조 (작다 — 자료가 정한다)
    입력  90일 로그 궤적 → 개체별 z 정규화(수준을 지운다: 1038 이 수준은 못 맞힌다고 판정)
    인코더 1D conv(다중 커널) → GRU → h ∈ R^d            d 는 기본 64
    헤드  ① 다음 30일 «모양» 예보 (자기지도 · 라벨 불필요)
          ② 마스킹 복원 (자기지도)
    🔴 파라미터를 창 수보다 «한참 아래»로 둔다. 패널 창은 수십만이지만 개체는 991 뿐이라
       실효 표본은 개체 수에 가깝다.

## 자기지도인 이유
    사건 라벨(3배 급등)은 «하류» 표적이다. 그걸로 학습하면 파운데이션이 아니라 그냥 분류기다.
    여기서는 라벨 없이 궤적 자체의 구조만 배우고, 평가는 «얼려서» 하류에 꽂아 본다.

## 🔴 이 모듈이 주장하지 않는 것
    · 인과 아님.
    · 「곡선 특징(ⓐ37)보다 낫다」는 **학습 후 1039/1040 정본 자로 재야 안다.** 이 파일은 학습기다.
    · 개체 분리 검증 — 학습/검증을 **개체**로 가른다(같은 개체의 창이 양쪽에 걸리면 누수).

씀:
    python3 -m pretrain.traj build      # 패널 → 창 텐서
    python3 -m pretrain.traj train --steps 3000
    python3 -m pretrain.traj encode     # 얼린 인코더로 h 뽑기 (하류 평가용)
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import argparse
import gzip
import hashlib
import json
import os
import time

import numpy as np

ART = os.environ.get("WM_FOUNDATION_DIR", "/Users/ax/wm_harvest/foundation")
OUT = os.path.join(ART, "traj")
PANEL = "/Users/ax/world_model/data/ingest/wiki_daily959"
DOMS = ("팝업", "시장팝업", "웹툰", "애니", "게임", "도서", "만화", "모바일",
        "아이돌", "세계애니", "펀딩")
CTX, HOR = 90, 30          # 문맥 90일 → 다음 30일 모양
STRIDE = 7
SEED = 1041


def sha16(p):
    if not os.path.exists(p):
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()[:16]


def load_panel():
    """개체 → 날짜순 조회수 배열. 결측은 «채우지 않는다»(조항 59) — 창에서 뺀다."""
    ser = {}
    for dom in DOMS:
        p = os.path.join(PANEL, "%s.jsonl.gz" % dom)
        if not os.path.exists(p):
            continue
        for line in gzip.open(p, "rt", encoding="utf-8"):
            r = json.loads(line)
            key = (dom, r["문서"])
            d = dict(zip([str(x) for x in r["날짜"]], r["조회수"]))
            ser.setdefault(key, {}).update(d)
    return ser


def build(out=OUT):
    os.makedirs(out, exist_ok=True)
    ser = load_panel()
    days = sorted({d for s in ser.values() for d in s})
    dix = {d: i for i, d in enumerate(days)}
    keys = sorted(ser)
    M = np.full((len(keys), len(days)), np.nan, dtype=np.float32)
    for i, k in enumerate(keys):
        for d, v in ser[k].items():
            M[i, dix[d]] = v
    X, Y, ENT, DOM = [], [], [], []
    for i, k in enumerate(keys):
        row = M[i]
        for t0 in range(0, len(days) - CTX - HOR, STRIDE):
            w = row[t0:t0 + CTX + HOR]
            if np.isnan(w).any():          # 🔴 결측 창은 «버린다». 0 채움 금지
                continue
            X.append(w[:CTX]); Y.append(w[CTX:]); ENT.append(i); DOM.append(k[0])
    X = np.asarray(X, np.float32); Y = np.asarray(Y, np.float32)
    ENT = np.asarray(ENT, np.int32)
    np.savez_compressed(os.path.join(out, "windows.npz"), X=X, Y=Y, ENT=ENT,
                        keys=np.array(["%s|%s" % k for k in keys]),
                        doms=np.array(DOM), days=np.array(days))
    rep = {"개체": len(keys), "날짜": len(days), "기간": [days[0], days[-1]],
           "창": int(len(X)), "CTX": CTX, "HOR": HOR, "STRIDE": STRIDE,
           "🔴 결측 창 버림": "0 채움 안 함(조항 59)",
           "창 보유 개체": int(len(set(ENT.tolist())))}
    json.dump(rep, open(os.path.join(out, "build.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps(rep, ensure_ascii=False))


def _norm(A):
    """🔴 개체별 수준을 지운다 — 1038 이 「수준은 못 맞힌다」고 판정했다. 모양만 배운다."""
    L = np.log1p(np.maximum(A, 0))
    m = L.mean(1, keepdims=True); s = L.std(1, keepdims=True) + 1e-6
    return (L - m) / s, m, s


def train(steps=3000, d=64, lr=3e-3, bs=256, out=OUT, device=None):
    import torch
    import torch.nn as nn
    z = np.load(os.path.join(out, "windows.npz"), allow_pickle=True)
    X, Y, ENT = z["X"], z["Y"], z["ENT"]
    Xn, m, s = _norm(X)
    Yn = (np.log1p(np.maximum(Y, 0)) - m) / s          # 같은 기준으로 — 예보는 «모양»이다
    rng = np.random.default_rng(SEED)
    ents = np.unique(ENT)
    va_e = set(rng.choice(ents, max(1, len(ents) // 5), replace=False).tolist())
    va = np.array([i for i in range(len(X)) if ENT[i] in va_e])
    tr = np.array([i for i in range(len(X)) if ENT[i] not in va_e])
    dev = device or ("mps" if torch.backends.mps.is_available() else "cpu")

    class Enc(nn.Module):
        def __init__(s_, d):
            super().__init__()
            s_.c = nn.ModuleList([nn.Conv1d(1, 16, k, padding=k // 2) for k in (3, 7, 15, 31)])
            s_.g = nn.GRU(64, d, batch_first=True)
            s_.head = nn.Linear(d, HOR)

        def enc(s_, x):
            h = torch.cat([torch.relu(c(x.unsqueeze(1))[:, :, :x.shape[1]]) for c in s_.c], 1)
            o, _ = s_.g(h.transpose(1, 2))
            return o[:, -1]

        def forward(s_, x):
            return s_.head(s_.enc(x))

    net = Enc(d).to(dev)
    npar = sum(p.numel() for p in net.parameters())
    opt = torch.optim.AdamW(net.parameters(), lr=lr, weight_decay=0.01)
    Xt = torch.tensor(Xn, dtype=torch.float32)
    Yt = torch.tensor(Yn, dtype=torch.float32)
    print("창 %d (train %d / val %d) · 개체 %d (val %d) · 파라미터 %d · %s"
          % (len(X), len(tr), len(va), len(ents), len(va_e), npar, dev))
    best = 9e9
    t0 = time.time()
    hist = []
    for step in range(1, steps + 1):
        b = rng.choice(tr, bs)
        xb, yb = Xt[b].to(dev), Yt[b].to(dev)
        loss = torch.nn.functional.l1_loss(net(xb), yb)
        opt.zero_grad(); loss.backward()
        torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
        opt.step()
        if step % 200 == 0 or step == steps:
            net.eval()
            with torch.no_grad():
                vb = rng.choice(va, min(4096, len(va)), replace=False)
                vl = torch.nn.functional.l1_loss(net(Xt[vb].to(dev)), Yt[vb].to(dev)).item()
                # 기준선: 모양 없음(전부 0 = 그 개체 평균)
                bl = Yt[vb].abs().mean().item()
            net.train()
            hist.append({"step": step, "train": round(loss.item(), 4),
                         "val": round(vl, 4), "기준선": round(bl, 4)})
            print("  step %5d  train %.4f  val %.4f  (모양없음 기준선 %.4f)  %.0fs"
                  % (step, loss.item(), vl, bl, time.time() - t0))
            if vl < best:
                best = vl
                torch.save({"sd": net.state_dict(), "d": d, "CTX": CTX, "HOR": HOR},
                           os.path.join(out, "traj_v0.pt"))
    rep = {"판": "궤적 파운데이션 v0", "창": int(len(X)), "train": int(len(tr)), "val": int(len(va)),
           "개체": int(len(ents)), "val개체": len(va_e), "파라미터": int(npar), "d": d,
           "steps": steps, "best_val_L1": round(best, 4),
           "기준선(모양없음)": round(hist[-1]["기준선"], 4) if hist else None,
           "이력": hist, "device": dev, "seed": SEED,
           "🔴 안 주장": ["인과 아님", "하류 우위는 1039/1040 정본 자로 따로 재야 안다"]}
    json.dump(rep, open(os.path.join(out, "train.json"), "w"), ensure_ascii=False, indent=1)
    print("\nbest val L1 %.4f  vs 기준선 %.4f  → %s"
          % (best, hist[-1]["기준선"], "개선" if best < hist[-1]["기준선"] else "🔴 못 넘음"))


def encode(out=OUT):
    """얼린 인코더로 1036 행 10,654 의 h 를 뽑는다 — 하류 평가용."""
    import torch
    import torch.nn as nn
    ck = torch.load(os.path.join(out, "traj_v0.pt"), map_location="cpu")
    d = ck["d"]

    class Enc(nn.Module):
        def __init__(s_, d):
            super().__init__()
            s_.c = nn.ModuleList([nn.Conv1d(1, 16, k, padding=k // 2) for k in (3, 7, 15, 31)])
            s_.g = nn.GRU(64, d, batch_first=True)
            s_.head = nn.Linear(d, HOR)

        def enc(s_, x):
            h = torch.cat([torch.relu(c(x.unsqueeze(1))[:, :, :x.shape[1]]) for c in s_.c], 1)
            o, _ = s_.g(h.transpose(1, 2))
            return o[:, -1]

    net = Enc(d); net.load_state_dict(ck["sd"]); net.eval()
    z = np.load(os.path.join(ART, "triples", "sao.npz"))
    S = z["S"].astype(np.float32)
    Xn, _, _ = _norm(S)
    with torch.no_grad():
        H = net.enc(torch.tensor(Xn, dtype=torch.float32)).numpy()
    np.savez_compressed(os.path.join(out, "h_sao.npz"), H=H.astype(np.float32))
    print(json.dumps({"h": list(H.shape), "ckpt.sha16": sha16(os.path.join(out, "traj_v0.pt"))},
                     ensure_ascii=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "train", "encode"])
    ap.add_argument("--steps", type=int, default=3000)
    ap.add_argument("--d", type=int, default=64)
    ap.add_argument("--device")
    a = ap.parse_args()
    if a.cmd == "build":
        build()
    elif a.cmd == "train":
        train(steps=a.steps, d=a.d, device=a.device)
    else:
        encode()
