"""전이 검정 — SFS-1 Stage 2 ②. 정직한 눈금(IP-그룹 ∩ 시간순 + 페어드 CI)으로 측정.

state/encoder.py 의 --transfer 는 랜덤 분할을 쓰므로 Stage 0에서 무효 판정한 문제를 그대로
안고 있다. 이 모듈은 evaluate.py 와 같은 폴드 규약을 쓰고, 모델-프리 하한을 항상 병기한다.

측정하는 것:
  A 상수 중앙값        — 모델-프리 하한
  B 팝업 단독 학습      — 인코더를 팝업에서 처음부터
  C 아이돌 전이(동결)   — 아이돌에서 사전학습한 인코더를 얼리고 팝업 헤드만
  D 아이돌 전이(미세조정) — 사전학습 후 함께 미세조정
판정: (B−C)의 페어드 부트스트랩 CI가 0을 제외하면 '전이 실재'.

사용: python3 -m state.transfer_eval
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch

from .encoder import STATE_DIM, DomainHead, SharedEncoder, _load
from .evaluate import group_time_folds, paired_bootstrap

SEED = 20260727
CKPT = Path("data/state/ckpt/encoder_idol.pt")


def _folds_for(domain: str, n: int):
    """도메인 메타에서 IP·시간을 읽어 그룹·시간 폴드 구성 (없으면 인덱스 순)."""
    mp = Path(f"data/state/{domain}_meta.json")
    if mp.exists():
        meta = json.loads(mp.read_text())
        if len(meta) == n:
            g = np.array([m.get("ip") or m.get("id") or str(i) for i, m in enumerate(meta)])
            t = np.array([m.get("date") or "9999" for m in meta])
            if not (t == "9999").all():
                return group_time_folds(g, t, n_folds=5, min_train_frac=0.35)
    idx = np.arange(n)
    return [(idx[: int(n * 0.35) + i * (n // 8)], idx[int(n * 0.35) + i * (n // 8):
                                                       int(n * 0.35) + (i + 1) * (n // 8)])
            for i in range(4)]


def lane(domain: str, folds, encoder_path: Path | None, freeze: bool, epochs: int = 300):
    X, y, w, _ = _load(domain, text=False)     # 텍스트는 소표본 과적합으로 제외(실측)
    act_dim = X.shape[1] - STATE_DIM
    errs = []
    for k, (tr, te) in enumerate(folds):
        tr_t, te_t = torch.tensor(tr), torch.tensor(te)
        # 폴드 내부 표준화 (누출 차단)
        mu, sd = X[tr_t].mean(0), X[tr_t].std(0) + 1e-6
        Xn = (X - mu) / sd
        torch.manual_seed(SEED + k)
        enc = SharedEncoder()
        if encoder_path and encoder_path.exists():
            enc.load_state_dict(torch.load(encoder_path))
        if freeze:
            for p in enc.parameters():
                p.requires_grad = False
        head = DomainHead(act_dim)
        params = list(head.parameters()) + ([] if freeze else list(enc.parameters()))
        opt = torch.optim.Adam(params, lr=0.01, weight_decay=1e-3)
        for _ in range(epochs):
            opt.zero_grad()
            p = head(enc(Xn[tr_t, :STATE_DIM]), Xn[tr_t, STATE_DIM:])
            ((w[tr_t] * (p - y[tr_t]) ** 2).mean()).backward()
            opt.step()
        with torch.no_grad():
            pr = head(enc(Xn[te_t, :STATE_DIM]), Xn[te_t, STATE_DIM:])
            errs.append((pr - y[te_t]).abs().numpy())
    return np.concatenate(errs)


def const_lane(domain: str, folds):
    _, y, _, _ = _load(domain, text=False)
    return np.concatenate([np.abs(np.median(y[torch.tensor(tr)].numpy()) - y[torch.tensor(te)].numpy())
                            for tr, te in folds])


def main() -> int:
    X, y, _, _ = _load("popup", text=False)
    folds = _folds_for("popup", len(y))
    print(f"팝업 n={len(y)} / 폴드 {len(folds)} (IP-그룹 ∩ 시간순)")
    A = const_lane("popup", folds)
    B = lane("popup", folds, None, False)
    C = lane("popup", folds, CKPT, True) if CKPT.exists() else None
    D = lane("popup", folds, CKPT, False) if CKPT.exists() else None
    out = {"상수 중앙값": round(float(A.mean()), 4),
           "팝업 단독": round(float(B.mean()), 4)}
    if C is not None:
        out["아이돌전이(동결)"] = round(float(C.mean()), 4)
        out["아이돌전이(미세조정)"] = round(float(D.mean()), 4)
    for nm, e in (("팝업단독", B),) + ((("전이동결", C), ("전이미세", D)) if C is not None else ()):
        d = paired_bootstrap(e, A)
        out[f"{nm} vs 상수"] = {"diff": round(d[0], 4), "ci95": [round(d[1], 4), round(d[2], 4)],
                                 "유의": bool(d[2] < 0)}
    if C is not None:
        d = paired_bootstrap(C, B)
        out["전이 이득(동결 vs 단독)"] = {"diff": round(d[0], 4),
                                          "ci95": [round(d[1], 4), round(d[2], 4)],
                                          "유의": bool(d[2] < 0)}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
