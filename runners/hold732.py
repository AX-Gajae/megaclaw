"""노트 732 — **정보 전이장을 진짜 유보로 굳힌다.** 씨앗 4 · 팔 셋.

노트 703 의 검증 R² 0.134 는 **학습 구간 안** 8:2 뒤쪽이다. 여기서는 목표 날짜가
`TRAIN_END` 이후인 창을 유보로 쓴다. **입력 창은 유보를 지나도 된다** --- 예보
시점에 관측 가능하므로. 새면 안 되는 것은 **목표**다.

`state.fieldmodel.pretrain` 을 재구현하지 않는다(노트 702 의 교훈 --- 재구현이
저계수 이웃 혼합을 지웠다). 대신 **같은 모듈의 `Enc` 구조와 같은 값**을 쓰되
유보 채점만 더한다. 구조가 갈리면 아래 `대조` 칸에서 드러난다.
"""
import json
import sys

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
import torch
import torch.nn as nn

from state import fieldmodel as F

SEEDS = (0, 1, 2, 3)
DIM = F.DIM
LOOKBACK = F.LOOKBACK
HORIZON = 30
EPOCHS = 60
K = 8


def windows(holiday: bool):
    """학습 창과 유보 창을 만든다. **목표 날짜로 가른다.**"""
    codes, days, X = F.field(stats_end=F.TRAIN_END, holiday=holiday)
    end = next((i for i, d in enumerate(days) if d > F.TRAIN_END), len(days))
    Z = np.nan_to_num(X, nan=0.0)
    obs = np.isfinite(X).astype(np.float32)
    xs, ys, ms, tgt_i = [], [], [], []
    for t in range(LOOKBACK, X.shape[1] - HORIZON):
        xs.append(Z[:, t - LOOKBACK:t])
        ys.append(Z[:, t + HORIZON] - Z[:, t])
        ms.append(obs[:, t + HORIZON] * obs[:, t])
        tgt_i.append(t + HORIZON)
    tgt_i = np.array(tgt_i)
    tr = tgt_i < end          # 목표가 학습 구간 안
    te = ~tr                  # **목표가 유보**
    return (codes, days, end, np.stack(xs), np.stack(ys), np.stack(ms), tr, te,
            [days[i] for i in tgt_i[te][:1]] + [days[i] for i in tgt_i[te][-1:]])


class Enc(nn.Module):
    """`state.fieldmodel.pretrain` 안의 `Enc` 와 같은 구조."""

    def __init__(self, D):
        super().__init__()
        self.emb = nn.Embedding(D, DIM)
        self.tconv = nn.Linear(LOOKBACK, DIM)
        self.down = nn.Linear(D, K, bias=False)
        self.up = nn.Linear(K, D, bias=False)
        self.mix = nn.Linear(DIM * 3, DIM)
        self.head = nn.Linear(DIM, 1)

    def rep(self, w):
        e = self.emb.weight.unsqueeze(0).expand(w.shape[0], -1, -1)
        h = torch.tanh(self.tconv(w))
        g = self.up(self.down(h.transpose(1, 2))).transpose(1, 2)
        return torch.tanh(self.mix(torch.cat([h, e, g], -1)))

    def forward(self, w):
        return self.head(self.rep(w)).squeeze(-1)


def r2(p, y, m):
    mse = (((p - y) ** 2) * m).sum() / m.sum().clamp(min=1)
    var = ((y ** 2) * m).sum() / m.sum().clamp(min=1)
    return float(1 - mse / var)


def arm(holiday: bool, placebo: bool, seed: int, W):
    codes, days, end, xs, ys, ms, tr, te, _ = W
    D = len(codes)
    Y = ys.copy()
    if placebo:
        # **학습 목표만 섞는다.** 유보 목표를 섞으면 채점 대상이 바뀌어
        # 위약과 진짜가 다른 문제를 푸는 것이 된다.
        rng = np.random.default_rng(702 + seed)
        idx = np.flatnonzero(tr)
        for j in range(Y.shape[1]):
            v = Y[idx, j].copy(); rng.shuffle(v); Y[idx, j] = v
    torch.manual_seed(seed)
    net = Enc(D)
    opt = torch.optim.Adam(net.parameters(), lr=3e-3)
    Xw = torch.tensor(xs, dtype=torch.float32)
    Yw = torch.tensor(Y, dtype=torch.float32)
    Mw = torch.tensor(ms, dtype=torch.float32)
    ti = np.flatnonzero(tr)
    cut = int(len(ti) * 0.8)
    fit, val = ti[:cut], ti[cut:]
    for _ in range(EPOCHS):
        net.train(); opt.zero_grad()
        p = net(Xw[fit])
        loss = (((p - Yw[fit]) ** 2) * Mw[fit]).sum() / Mw[fit].sum().clamp(min=1)
        loss.backward(); opt.step()
    net.eval()
    hi = np.flatnonzero(te)
    with torch.no_grad():
        rv = r2(net(Xw[val]), Yw[val], Mw[val])
        # **유보는 섞지 않은 참목표로 채점한다**
        Yt = torch.tensor(ys, dtype=torch.float32)
        rh = r2(net(Xw[hi]), Yt[hi], Mw[hi])
    return {"학습구간 검증 R2": round(rv, 4), "**유보 R2**": round(rh, 4),
            "학습 창": len(fit), "검증 창": len(val), "유보 창": len(hi),
            "유보 관측": int(Mw[hi].sum().item()),
            "모수": sum(p.numel() for p in net.parameters())}


def main():
    out = {}
    for tag, hol, pla in (("① 진짜 · 공휴일 있음", True, False),
                          ("② 위약 · 공휴일 있음", True, True),
                          ("③ 진짜 · 공휴일 없음", False, False)):
        W = windows(hol)
        rows = [arm(hol, pla, s, W) for s in SEEDS]
        print(f"[{tag}] " + json.dumps(rows, ensure_ascii=False), flush=True)
        out[tag] = {
            "씨앗별": rows,
            "학습구간 검증 R2 평균": round(float(np.mean([r["학습구간 검증 R2"] for r in rows])), 4),
            "**유보 R2 평균**": round(float(np.mean([r["**유보 R2**"] for r in rows])), 4),
            "유보 씨앗SD": round(float(np.std([r["**유보 R2**"] for r in rows], ddof=1)), 4),
            "창": {k: rows[0][k] for k in ("학습 창", "검증 창", "유보 창", "유보 관측")},
        }
        if tag.startswith("①"):
            _, days, end, *_ , span = W
            out["유보 구간"] = {"첫 목표일": span[0], "끝 목표일": span[-1],
                            "학습 구간 끝": F.TRAIN_END, "날 수": len(days)}
    # ── 짝 차(씨앗마다) --- 노트 712 의 상관 경고를 지킨다
    a = [r["**유보 R2**"] for r in out["① 진짜 · 공휴일 있음"]["씨앗별"]]
    b = [r["**유보 R2**"] for r in out["② 위약 · 공휴일 있음"]["씨앗별"]]
    c = [r["**유보 R2**"] for r in out["③ 진짜 · 공휴일 없음"]["씨앗별"]]
    d_pl = np.array(a) - np.array(b)
    d_hol = np.array(a) - np.array(c)
    def judge(d, name):
        sd = float(np.std(d, ddof=1)); m = float(np.mean(d))
        return {"짝 차 평균": round(m, 4), "짝 차 씨앗SD": round(sd, 4),
                "**문턱 2σ**": round(2 * sd, 4),
                "**2σ 밖**": bool(abs(m) > 2 * sd),
                "씨앗별 차": [round(float(x), 4) for x in d], "무엇": name}
    print("=== 모아서 ===", flush=True)
    print(json.dumps({
        **out,
        "**(가) 장이 유보에서 서나 — 진짜 대 위약**": judge(d_pl, "진짜 − 위약"),
        "**(라) 공휴일 항 이득**": judge(d_hol, "공휴일 있음 − 없음"),
        "노트 703 학습구간 검증": 0.134,
        "노트 703 위약": -0.0136,
        "틀림 조건 검사 · 유보가 학습구간보다 큰가":
            out["① 진짜 · 공휴일 있음"]["**유보 R2 평균**"]
            > out["① 진짜 · 공휴일 있음"]["학습구간 검증 R2 평균"],
        "틀림 조건 검사 · 위약 유보가 0 에서 0.05 밖인가":
            abs(out["② 위약 · 공휴일 있음"]["**유보 R2 평균**"]) > 0.05,
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
