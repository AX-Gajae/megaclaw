"""공유 IP 상태 인코더 + 도메인 헤드 — 설계 확정본(2026-07-27)의 구현.

구조:
    IP 상태 피처 (7) ──► SharedEncoder ──► 상태 벡터 z (d=8)
                                            │
                            ┌───────────────┴───────────────┐
                     [z ‖ 팝업 개입피처]              [z ‖ 아이돌 개입피처]
                            │                               │
                       PopupHead                        IdolHead
                     log10(방문)                      log10(초동)

**상태는 하나, 결과 헤드는 도메인별.** 같은 팬덤이 무대만 바꿔 관측된다는 전제.

계획된 3단계(사용자 확정):
  ① 라벨이 풍부한 아이돌에서 Encoder+IdolHead 학습
  ② Encoder 고정 → PopupHead만 학습 → **전이 이득을 페어드로 측정**
  ③ 이득이 실증되면 공동 학습으로 확장 (부정 전이는 절제로 감시)

사용:
  python3 -m state.encoder --train popup            # 팝업 단독 베이스라인
  python3 -m state.encoder --train idol             # 아이돌 사전학습(데이터 도착 후)
  python3 -m state.encoder --transfer               # ②단계 전이 측정
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

CKPT = Path("data/state/ckpt")
STATE_DIM = 7          # dataset.py 의 IP 상태 피처 수 (앞 7개 공통)
LATENT = 8
SEED = 20260727


class SharedEncoder(nn.Module):
    def __init__(self, in_dim: int = STATE_DIM, latent: int = LATENT):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(in_dim, 16), nn.ReLU(), nn.Linear(16, latent), nn.Tanh())

    def forward(self, s):
        return self.net(s)


class DomainHead(nn.Module):
    def __init__(self, act_dim: int, latent: int = LATENT):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(latent + act_dim, 24), nn.ReLU(),
                                 nn.Dropout(0.1), nn.Linear(24, 1))

    def forward(self, z, a):
        return self.net(torch.cat([z, a], dim=1)).squeeze(1)


def _load(domain: str, text: bool = True):
    """구조화 피처 + (선택) 개입 텍스트 임베딩. 텍스트는 개입 피처 쪽(헤드 입력)에 붙는다 —
    '무엇을 하는가'는 도메인 고유 개입이지 IP 상태가 아니기 때문."""
    d = np.load(f"data/state/{domain}_table.npz")
    X, y, w = d["X"], d["y"], d["w"]
    if text:
        tp = Path(f"data/state/text_emb_{domain}.npz")
        if tp.exists():
            Z = np.load(tp, allow_pickle=True)["Z"]
            if len(Z) == len(X):
                X = np.hstack([X, Z])
            else:
                print(f"  [경고] 텍스트 임베딩 행수 불일치 ({len(Z)} vs {len(X)}) — 텍스트 제외")
    mu, sd = X.mean(0), X.std(0) + 1e-6
    Xn = (X - mu) / sd
    return (torch.tensor(Xn, dtype=torch.float32), torch.tensor(y, dtype=torch.float32),
            torch.tensor(w, dtype=torch.float32), (mu, sd))


def _split(n: int, folds: int = 5):
    g = torch.Generator().manual_seed(SEED)
    perm = torch.randperm(n, generator=g)
    return [perm[i::folds] for i in range(folds)]


def train(domain: str, encoder: SharedEncoder | None = None, freeze: bool = False,
          epochs: int = 400, verbose: bool = True, text: bool = True) -> dict:
    X, y, w, norm_ = _load(domain, text=text)
    n, dim = X.shape
    act_dim = dim - STATE_DIM
    folds = _split(n)
    maes, r2s = [], []
    for k, te in enumerate(folds):
        tr = torch.cat([f for i, f in enumerate(folds) if i != k])
        torch.manual_seed(SEED + k)
        enc = SharedEncoder() if encoder is None else encoder
        if encoder is not None and freeze:
            for p in enc.parameters():
                p.requires_grad = False
        head = DomainHead(act_dim)
        params = list(head.parameters()) + ([] if freeze else list(enc.parameters()))
        opt = torch.optim.Adam(params, lr=0.01, weight_decay=1e-3)
        for _ in range(epochs):
            opt.zero_grad()
            z = enc(X[tr, :STATE_DIM])
            pred = head(z, X[tr, STATE_DIM:])
            loss = (w[tr] * (pred - y[tr]) ** 2).mean()
            loss.backward()
            opt.step()
        with torch.no_grad():
            p = head(enc(X[te, :STATE_DIM]), X[te, STATE_DIM:])
            mae = (p - y[te]).abs().mean().item()
            ss = ((y[te] - y[te].mean()) ** 2).sum().item()
            r2 = 1 - ((p - y[te]) ** 2).sum().item() / max(ss, 1e-9)
        maes.append(mae); r2s.append(r2)
    out = {"domain": domain, "n": n, "folds": len(folds),
           "mae_log10": round(float(np.mean(maes)), 4),
           "mae_std": round(float(np.std(maes)), 4),
           "r2": round(float(np.mean(r2s)), 3),
           "배수오차": round(10 ** float(np.mean(maes)), 2),
           "frozen_encoder": freeze}
    if verbose:
        print(json.dumps(out, ensure_ascii=False))
    return out


def pretrain_and_save(domain: str = "idol", epochs: int = 500) -> Path:
    """전체 데이터로 인코더 사전학습 후 저장 (①단계)."""
    X, y, w, norm_ = _load(domain)
    act_dim = X.shape[1] - STATE_DIM
    torch.manual_seed(SEED)
    enc, head = SharedEncoder(), DomainHead(act_dim)
    opt = torch.optim.Adam(list(enc.parameters()) + list(head.parameters()), lr=0.01, weight_decay=1e-3)
    for _ in range(epochs):
        opt.zero_grad()
        loss = (w * (head(enc(X[:, :STATE_DIM]), X[:, STATE_DIM:]) - y) ** 2).mean()
        loss.backward(); opt.step()
    CKPT.mkdir(parents=True, exist_ok=True)
    p = CKPT / f"encoder_{domain}.pt"
    torch.save(enc.state_dict(), p)
    print(f"인코더 저장: {p} (사전학습 도메인 {domain}, n={len(y)})")
    return p


def transfer_eval() -> dict:
    """②단계 — 팝업 단독 vs 아이돌 사전학습 인코더 전이, 같은 폴드로 페어드 비교."""
    base = train("popup", verbose=False)
    p = CKPT / "encoder_idol.pt"
    if not p.exists():
        print(json.dumps({"상태": "아이돌 인코더 없음 — ①단계(pretrain) 선행 필요",
                           "팝업 단독 베이스라인": base}, ensure_ascii=False))
        return {"baseline": base, "transfer": None}
    enc = SharedEncoder()
    enc.load_state_dict(torch.load(p))
    tr = train("popup", encoder=enc, freeze=True, verbose=False)
    gain = round(base["mae_log10"] - tr["mae_log10"], 4)
    out = {"팝업 단독": base["mae_log10"], "아이돌 전이(동결)": tr["mae_log10"],
           "전이 이득(log10 MAE 감소)": gain,
           "판정": "전이 양성" if gain > 0.01 else ("중립" if gain > -0.01 else "부정 전이"),
           "baseline": base, "transfer": tr}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", choices=["popup", "idol"])
    ap.add_argument("--pretrain", choices=["popup", "idol"])
    ap.add_argument("--transfer", action="store_true")
    args = ap.parse_args()
    if args.train:
        train(args.train)
    if args.pretrain:
        pretrain_and_save(args.pretrain)
    if args.transfer:
        transfer_eval()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
