# -*- coding: utf-8 -*-
"""전이 모형 v0 — p(뒤 91일 곡선 | 앞 90일 상태, 도메인, 시기[, 텍스트]).

이게 「이 웹툰 90일 뒤 조회수는?」의 «직답» 모형이다:
  · 출력이 일별 «분위수 5 개»(q05·q25·q50·q75·q95) — 구간이 원생으로 나온다
  · 분위수 꼬임 방지: q50 을 예측하고 바깥 분위수는 softplus «간격»으로 —
    q05 ≤ q25 ≤ q50 ≤ q75 ≤ q95 가 구조로 보장된다
  · 텍스트 임베딩 «자리»(--text-emb)가 예약돼 있다 — LM 이 준비되면 꽂는다.
    지금은 0 차원(상태+조건만)으로도 학습·평가가 온전히 선다
  · 기준선 둘(persistence · last7)과 «반드시» 나란히 채점한다 — 기준선을 못 이기면
    모형이 아니라 장식이다

학습:  python3 pretrain/transition.py train --steps 3000
평가:  (train 끝에 자동) — val 은 «개체 분리» 분할이라 같은 IP 가 안 샌다
질의:  python3 pretrain/transition.py demo --i 5   # val 표본으로 «그 질답» 모양을 시연
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import argparse
import json
import math
import os
import time

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

ART = os.environ.get("WM_FOUNDATION_DIR", "/Users/ax/wm_harvest/foundation")
TRI = os.path.join(ART, "triples")
OUT = os.path.join(ART, "transition")
QS = [0.05, 0.25, 0.50, 0.75, 0.95]


# ── 자료 ──────────────────────────────────────────────────────────────
class SAO:
    def __init__(self, npz=os.path.join(TRI, "sao.npz"), text_emb=None):
        z = np.load(npz)
        self.S = np.log1p(z["S"].astype(np.float64)).astype(np.float32)   # (N,90)
        self.O = np.log1p(z["O"].astype(np.float64)).astype(np.float32)   # (N,91)
        self.base = self.S.mean(axis=1, keepdims=True)                    # 개체 수준
        self.Sc = self.S - self.base
        self.R = self.O - self.base                                       # 목표(잔차)
        n_dom = int(z["dom_id"].max()) + 1
        dom = np.zeros((len(self.S), n_dom), dtype=np.float32)
        dom[np.arange(len(self.S)), z["dom_id"]] = 1.0
        doy = z["doy"].astype(np.float32)
        cond = [dom,
                np.sin(2 * np.pi * doy / 365.0)[:, None],
                np.cos(2 * np.pi * doy / 365.0)[:, None],
                ((z["year"].astype(np.float32) - 2013.0) / 10.0)[:, None],
                self.base.astype(np.float32)]
        self.E = None
        if text_emb:
            self.E = np.load(text_emb)["E"].astype(np.float32)
            assert len(self.E) == len(self.S), "🔴 텍스트 임베딩 행 수 불일치"
            cond.append(self.E)
        self.C = np.concatenate(cond, axis=1).astype(np.float32)
        self.split = z["split"]
        self.tr = np.where(self.split == 0)[0]
        self.va = np.where(self.split == 1)[0]
        self.d_in = self.Sc.shape[1] + self.C.shape[1]

    def batch(self, idx_pool, bs, step, seed=997):
        rng = np.random.default_rng([seed, int(step)])
        ii = idx_pool[rng.integers(0, len(idx_pool), size=bs)]
        x = np.concatenate([self.Sc[ii], self.C[ii]], axis=1)
        return (torch.from_numpy(x), torch.from_numpy(self.R[ii]),
                torch.from_numpy(self.base[ii]))


# ── 모형 ──────────────────────────────────────────────────────────────
class Transition(nn.Module):
    def __init__(self, d_in, hidden=512, horizon=91):
        super().__init__()
        self.horizon = horizon
        self.net = nn.Sequential(
            nn.Linear(d_in, hidden), nn.GELU(),
            nn.Linear(hidden, hidden), nn.GELU(),
            nn.Linear(hidden, hidden), nn.GELU(),
            nn.Linear(hidden, horizon * 5))

    def forward(self, x):
        raw = self.net(x).view(-1, self.horizon, 5)
        q50 = raw[..., 0]
        g = F.softplus(raw[..., 1:5]) + 1e-4
        q25, q05 = q50 - g[..., 0], q50 - g[..., 0] - g[..., 1]
        q75, q95 = q50 + g[..., 2], q50 + g[..., 2] + g[..., 3]
        return torch.stack([q05, q25, q50, q75, q95], dim=-1)   # (B,91,5)


def pinball(pred, target):
    t = target.unsqueeze(-1)
    losses = []
    for j, q in enumerate(QS):
        e = t[..., 0] - pred[..., j]
        losses.append(torch.maximum(q * e, (q - 1) * e).mean())
    return sum(losses) / len(QS)


# ── 평가(기준선과 나란히) ─────────────────────────────────────────────
def evaluate(model, data, device):
    model.eval()
    ii = data.va
    with torch.no_grad():
        x = torch.from_numpy(np.concatenate([data.Sc[ii], data.C[ii]], axis=1)).to(device)
        pred = model(x).cpu().numpy()                     # (n,91,5) 잔차 눈금
    R = data.R[ii]
    # 기준선 — persistence(잔차 0) · last7(마지막 7일 평균을 유지)
    last7 = data.Sc[ii][:, -7:].mean(axis=1, keepdims=True) * np.ones_like(R)
    def mae(p):
        return float(np.abs(p - R).mean())
    cover = float(((R >= pred[..., 0]) & (R <= pred[..., 4])).mean())
    piw = float((pred[..., 4] - pred[..., 0]).mean())
    # 누적 90일 상대 오차(원 눈금) — 「몇 회가 될까」의 눈금
    base = data.base[ii]
    cum_true = np.expm1(R + base).sum(axis=1)
    cum_q50 = np.expm1(pred[..., 2] + base).sum(axis=1)
    cum_pers = np.expm1(0 * R + base).sum(axis=1)
    mdape = float(np.median(np.abs(cum_q50 - cum_true) / np.maximum(cum_true, 1)))
    mdape_pers = float(np.median(np.abs(cum_pers - cum_true) / np.maximum(cum_true, 1)))
    model.train()
    return {"val_n": int(len(ii)),
            "q50_MAE(log)": round(mae(pred[..., 2]), 4),
            "기준선 persistence MAE": round(mae(np.zeros_like(R)), 4),
            "기준선 last7 MAE": round(mae(last7), 4),
            "90% 구간 덮개율(목표 0.90)": round(cover, 4),
            "구간 평균 폭(log)": round(piw, 4),
            "누적90일 MdAPE": round(mdape, 4),
            "누적90일 MdAPE(persistence)": round(mdape_pers, 4)}


# ── 학습 ──────────────────────────────────────────────────────────────
def train(a):
    os.makedirs(OUT, exist_ok=True)
    data = SAO(text_emb=a.text_emb or None)
    device = a.device if a.device != "auto" else "cpu"    # 0.9M MLP — CPU 가 충분
    torch.manual_seed(997)
    model = Transition(data.d_in, hidden=a.hidden).to(device)
    n_par = sum(p.numel() for p in model.parameters())
    opt = torch.optim.Adam(model.parameters(), lr=a.lr)
    mf = open(os.path.join(OUT, "metrics.jsonl"), "a", encoding="utf-8")
    t0 = time.time()
    for step in range(a.steps):
        x, r, _ = data.batch(data.tr, a.batch, step)
        x, r = x.to(device), r.to(device)
        opt.zero_grad(set_to_none=True)
        loss = pinball(model(x), r)
        loss.backward()
        opt.step()
        if (step + 1) % a.log_every == 0 or step + 1 == a.steps:
            mf.write(json.dumps({"step": step + 1, "pinball": round(loss.item(), 5)}) + "\n")
            mf.flush()
    ev = evaluate(model, data, device)
    torch.save({"model": model.state_dict(), "d_in": data.d_in, "hidden": a.hidden,
                "text_emb": a.text_emb or None}, os.path.join(OUT, "model.pt"))
    rep = {"표본": {"train": int(len(data.tr)), "val(개체 분리)": int(len(data.va))},
           "d_in": data.d_in, "params": n_par, "steps": a.steps,
           "seconds": round(time.time() - t0, 1), "최종 pinball(train)": round(loss.item(), 5),
           "평가": ev,
           "🔴 정직": "「언제」가 크롤 시각이라(탐색 995) 이 수는 «조건부 예측»이다 — "
                    "「언급의 인과 효과」 주장은 이 자료로 못 세운다"}
    with open(os.path.join(OUT, "report.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    print(json.dumps(rep, ensure_ascii=False))


# ── 질의 시연 — 「이 개체, 90일 뒤?」 의 실제 모양 ────────────────────
def demo(a):
    ck = torch.load(os.path.join(OUT, "model.pt"), map_location="cpu", weights_only=False)
    data = SAO(text_emb=ck.get("text_emb"))
    model = Transition(ck["d_in"], hidden=ck["hidden"])
    model.load_state_dict(ck["model"])
    model.eval()
    i = data.va[a.i % len(data.va)]
    meta = None
    with open(os.path.join(TRI, "meta.jsonl"), encoding="utf-8") as f:
        for k, line in enumerate(f):
            if k == i:
                meta = json.loads(line)
                break
    x = torch.from_numpy(np.concatenate([data.Sc[i:i+1], data.C[i:i+1]], axis=1))
    with torch.no_grad():
        q = model(x).numpy()[0] + data.base[i]            # (91,5) log 눈금
    cum = np.expm1(q).cumsum(axis=0)                      # 누적, 원 눈금
    true_cum = np.expm1(data.O[i]).cumsum()
    out = {"개체": meta["개체"], "도메인": meta["도메인"], "기준일": meta["언제"],
           "직전 90일 일평균": round(float(np.expm1(data.S[i]).mean()), 1),
           "예측(누적)": {
               "30일": {"q05": int(cum[29, 0]), "q50": int(cum[29, 2]), "q95": int(cum[29, 4])},
               "90일": {"q05": int(cum[90, 0]), "q50": int(cum[90, 2]), "q95": int(cum[90, 4])}},
           "실제(누적)": {"30일": int(true_cum[29]), "90일": int(true_cum[90])}}
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    tp = sub.add_parser("train")
    tp.add_argument("--steps", type=int, default=3000)
    tp.add_argument("--batch", type=int, default=256)
    tp.add_argument("--hidden", type=int, default=512)
    tp.add_argument("--lr", type=float, default=1e-3)
    tp.add_argument("--log-every", type=int, default=100)
    tp.add_argument("--device", default="auto")
    tp.add_argument("--text-emb", default="", help="npz(E=(N,d)) — LM 임베딩 자리")
    dp = sub.add_parser("demo")
    dp.add_argument("--i", type=int, default=0)
    a = ap.parse_args()
    train(a) if a.cmd == "train" else demo(a)
