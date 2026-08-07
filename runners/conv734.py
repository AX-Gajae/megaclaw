"""노트 734 — **씨앗 분산인가 미수렴 분산인가.** 걸음 60·200·600·1500 으로 가른다.

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
CHECK = (60, 200, 600, 1500)
EPOCHS = max(CHECK)
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
    hi = np.flatnonzero(te)
    Yt = torch.tensor(ys, dtype=torch.float32)
    out = {}
    for ep in range(1, EPOCHS + 1):
        net.train(); opt.zero_grad()
        p = net(Xw[fit])
        loss = (((p - Yw[fit]) ** 2) * Mw[fit]).sum() / Mw[fit].sum().clamp(min=1)
        loss.backward(); opt.step()
        if ep in CHECK:
            net.eval()
            with torch.no_grad():
                # **유보는 섞지 않은 참목표로 채점한다**
                out[ep] = {"학습 손실": round(float(loss), 5),
                           "학습구간 검증 R2": round(r2(net(Xw[val]), Yw[val], Mw[val]), 4),
                           "**유보 R2**": round(r2(net(Xw[hi]), Yt[hi], Mw[hi]), 4)}
    out["창"] = {"학습 창": len(fit), "검증 창": len(val), "유보 창": len(hi),
                "유보 관측": int(Mw[hi].sum().item()),
                "모수": sum(p.numel() for p in net.parameters())}
    return out


def main():
    arms = {}
    for tag, hol, pla in (("① 진짜 · 공휴일 있음", True, False),
                          ("② 위약 · 공휴일 있음", True, True),
                          ("③ 진짜 · 공휴일 없음", False, False)):
        W = windows(hol)
        rows = [arm(hol, pla, s, W) for s in SEEDS]
        arms[tag] = rows
        print(f"[{tag}] " + json.dumps(
            {ep: [r[ep]["**유보 R2**"] for r in rows] for ep in CHECK},
            ensure_ascii=False), flush=True)

    def col(tag, ep, key="**유보 R2**"):
        return np.array([r[ep][key] for r in arms[tag]], float)

    per = {}
    for ep in CHECK:
        a1, a2, a3 = (col(t, ep) for t in arms)
        d_pl, d_hol = a1 - a2, a1 - a3
        per[ep] = {
            "진짜 유보 R2 평균": round(float(a1.mean()), 4),
            "**진짜 유보 씨앗SD**": round(float(a1.std(ddof=1)), 4),
            "위약 유보 R2 평균": round(float(a2.mean()), 4),
            "진짜 학습구간 검증 평균": round(float(col("① 진짜 · 공휴일 있음", ep,
                                              "학습구간 검증 R2").mean()), 4),
            "학습 손실 평균": round(float(col("① 진짜 · 공휴일 있음", ep,
                                        "학습 손실").mean()), 5),
            "**짝 차(진짜−위약) 평균**": round(float(d_pl.mean()), 4),
            "짝 차 씨앗SD": round(float(d_pl.std(ddof=1)), 4),
            "**짝 차 2σ 밖**": bool(abs(d_pl.mean()) > 2 * d_pl.std(ddof=1)),
            "공휴일 이득 평균": round(float(d_hol.mean()), 4),
            "공휴일 2σ 밖": bool(abs(d_hol.mean()) > 2 * d_hol.std(ddof=1)),
            "씨앗별 진짜 유보": [round(float(x), 4) for x in a1],
        }
    print("=== 모아서 ===", flush=True)
    print(json.dumps({
        "걸음별": per,
        "판정 (가) 1500 에서 씨앗SD<0.05 이고 진짜>0":
            per[1500]["**진짜 유보 씨앗SD**"] < 0.05 and per[1500]["진짜 유보 R2 평균"] > 0,
        "판정 (나) 씨앗SD 가 0.15 이상 남나": per[1500]["**진짜 유보 씨앗SD**"] >= 0.15,
        "판정 (다) 1500 에서도 음수인가": per[1500]["진짜 유보 R2 평균"] <= 0,
        "틀림 조건 · 유보가 학습구간보다 큰가":
            per[1500]["진짜 유보 R2 평균"] > per[1500]["진짜 학습구간 검증 평균"],
        "틀림 조건 · 걸음 늘려 SD 가 커졌나":
            per[1500]["**진짜 유보 씨앗SD**"] > per[60]["**진짜 유보 씨앗SD**"],
        "창": arms["① 진짜 · 공휴일 있음"][0]["창"],
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
