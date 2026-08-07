"""노트 702 — **정보 전이장이 잘 학습되고 있나.** 공휴일 뺀 g 로 다시 잰다.

노트 690 이 `fieldmodel.field` 에 공휴일 항을 넣어 **g 자체가 바뀌었다.** 그러니
노트 669 의 검증 R² 0.1098(위약 −0.0074)은 낡았고, 대장에 "다시 재기 전까지
쓰지 않는다" 를 결정 규칙으로 달아 뒀다. 그 재측정이다.

재는 것 넷:
  ① 새 g 의 지속성 표(`horizons`) --- 장이 얼마나 오래 자기를 기억하나
  ② 새 g 의 **사전학습 검증 R²** --- 지속성 잔차 위에서 이길 수 있나
  ③ **위약** --- 목표를 동네 안에서 시간축으로 섞는다(노트 669 가 정의한 설계)
  ④ **옛 g 와 견줌** --- `holiday=False` 로 같은 씨앗에 돌려 공휴일 항이
     학습을 돕나 해치나 가른다

판정(미리 적는다): **위약이 진짜보다 안 나쁘면 장은 아무것도 안 배운 것이다**
(노트 335). 그리고 R² 가 옛 g 보다 **떨어지면** 공휴일 항이 학습에 해로운
것이고, **오르면** 명절이 잡음이었다는 뜻이다.
"""
import json
import sys

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
import state.fieldmodel as F

SEED = 0
EPOCHS = 60


def horizons_of(holiday: bool):
    """지속성 표 --- g(t) 가 g(t+h) 를 얼마나 설명하나."""
    codes, days, X = F.field(stats_end=F.TRAIN_END, holiday=holiday)
    out = {}
    for h in (1, 7, 30, 90, 180):
        a, b = X[:, :-h].ravel(), X[:, h:].ravel()
        ok = np.isfinite(a) & np.isfinite(b)
        if ok.sum() < 100:
            continue
        out[h] = round(float(np.corrcoef(a[ok], b[ok])[0, 1] ** 2), 4)
    return {"동네": len(codes), "날": len(days), "지속성 R2": out}


def pretrain_placebo(holiday: bool, seed: int = SEED):
    """위약 --- **목표를 동네 안에서 시간축으로 섞는다.**

    `pretrain` 을 그대로 못 쓰므로(위약 손잡이가 없다) 같은 뼈대를 여기 옮긴다.
    관측 무늬(결측)는 그대로 두고 값만 섞는다(노트 335).
    """
    import torch
    import torch.nn as nn
    torch.manual_seed(seed)
    codes, days, X = F.field(stats_end=F.TRAIN_END, holiday=holiday)
    end = next((i for i, d in enumerate(days) if d > F.TRAIN_END), len(days))
    Xtr = X[:, :end]
    D, T = Xtr.shape
    LB, H, DIM = F.LOOKBACK, 30, F.DIM

    def windows(mat):
        xs, ys, ms, ds = [], [], [], []
        for i in range(D):
            row = mat[i]
            for t in range(LB, T - H):
                w = row[t - LB:t]
                y = row[t + H] - row[t]              # 지속성 잔차
                if not np.isfinite(w).all() or not np.isfinite(y):
                    continue
                xs.append(w); ys.append(y); ms.append(1.0); ds.append(i)
        return (np.array(xs, np.float32), np.array(ys, np.float32),
                np.array(ms, np.float32), np.array(ds, np.int64))

    Xw, Yw, Mw, Dw = windows(Xtr)
    if len(Yw) < 500:
        return {"오류": f"표본 부족({len(Yw)})"}
    cut = int(len(Yw) * 0.8)

    class Net(nn.Module):
        def __init__(self):
            super().__init__()
            self.emb = nn.Embedding(D, DIM)
            self.lin = nn.Linear(LB + DIM, 1)

        def forward(self, x, d):
            return self.lin(torch.cat([x, self.emb(d)], 1)).squeeze(-1)

    def run(y):
        torch.manual_seed(seed)
        net = Net()
        opt = torch.optim.Adam(net.parameters(), lr=1e-3)
        xt = torch.tensor(Xw); yt = torch.tensor(y); dt = torch.tensor(Dw)
        for ep in range(EPOCHS):
            net.train(); opt.zero_grad()
            loss = ((net(xt[:cut], dt[:cut]) - yt[:cut]) ** 2).mean()
            loss.backward(); opt.step()
        net.eval()
        with torch.no_grad():
            pv = net(xt[cut:], dt[cut:])
            mse = float(((pv - yt[cut:]) ** 2).mean())
            var = float((yt[cut:] ** 2).mean())
        return round(1 - mse / max(var, 1e-9), 4)

    real = run(Yw)
    rng = np.random.default_rng(702 + seed)
    Yp = Yw.copy()
    for i in range(D):                                # **동네 안에서만 섞는다**
        m = Dw == i
        if m.sum() > 1:
            v = Yp[m]; rng.shuffle(v); Yp[m] = v
    plac = run(Yp)
    return {"표본": int(len(Yw)), "학습": cut, "검증": int(len(Yw) - cut),
            "동네": D, "검증 R2": real, "위약 R2": plac,
            "**신호 몫**": round(real - plac, 4)}


def main():
    out = {}
    for hol, tag in ((True, "공휴일 뺀 g (지금 · 노트 690)"),
                     (False, "옛 g (holiday=False · 노트 669 설정)")):
        h = horizons_of(hol)
        print(json.dumps({tag: h}, ensure_ascii=False), flush=True)
        p = pretrain_placebo(hol)
        print(json.dumps({tag: p}, ensure_ascii=False), flush=True)
        out[tag] = {"지속성": h, "사전학습": p}
    a = out["공휴일 뺀 g (지금 · 노트 690)"]["사전학습"]
    b = out["옛 g (holiday=False · 노트 669 설정)"]["사전학습"]
    if "검증 R2" in a and "검증 R2" in b:
        out["판정"] = {
            "장이 배우나": ("**배운다**" if a["**신호 몫**"] > 0.02
                        else "**안 배운다 --- 위약과 구분 안 됨**"),
            "공휴일 항이 학습에": ("도움" if a["검증 R2"] > b["검증 R2"] else "해로움"),
            "새 g 신호 몫": a["**신호 몫**"], "옛 g 신호 몫": b["**신호 몫**"],
        }
    print("=== 모아서 ===", flush=True)
    print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
