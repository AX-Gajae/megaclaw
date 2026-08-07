"""노트 753 — **마스크 구멍을 메우고 노트 744·745 를 다시 잰다.** 앞채움. 씨앗 6.

축: `enc.pt`(노트 736 의 검증-최선 가중)로 동네마다 30일 앞 Δ 를 예보하고
**그 날의 동네 간 SD** 를 낸다 --- *'앞으로 지역이 얼마나 갈릴 것인가'*.
전국 평균은 구성상 0 이므로 **수준이 아니라 산포**를 쓴다(노트 644). 1열.
도메인 안 백분위로 넣는다(노트 646).
"""
import json
import sys

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
import torch
import torch.nn as nn

from lab import forms, loop as L
from lab.harness import evaluate
from state import fieldmodel as F

T = 2025.0
SEEDS = tuple(range(6))
PLACEBO_DRAWS = (7440, 7441, 7442)
CLS = forms.REGISTRY["F18_bagboost"]["cls"]
AX = "field_spread_ff"
BASE_OK = (0.455, 0.485)


def base():
    from lab import genaxes, grpaxes
    e = {**L._trendsub(zero_is_data=True), **L._calsub(), **L._wikisub(),
         **L._tag(), **L._fund(), **L._rawsub(), **genaxes.build()}
    e.update(grpaxes.build())
    return e


def shell(extra):
    return L._idol(lambda: dict(extra), mode="cut", with_wiki=True,
                   with_trend=True, wide_post=True, wide_pop="grades")


def board(data):
    vals, per = [], {}
    for s in SEEDS:
        sc = evaluate(lambda s=s: CLS(seed=s), data, T=T)
        vals.append(float(data.pooled(sc, T=T)))
        for k, v in sc.items():
            if np.isfinite(v):
                per.setdefault(k, []).append(float(v))
    return {"판": round(float(np.mean(vals)), 4),
            "씨앗별": [round(v, 4) for v in vals],
            "씨앗SD": round(float(np.std(vals, ddof=1)), 4),
            "도메인": {k: round(float(np.mean(a)), 4) for k, a in per.items()}}


def spread_series():
    """날짜마다 **예보 Δ 의 동네 간 SD**. 창 [t-56, t) 만 본다(관측 가능)."""
    ck = torch.load(F.OUT / "enc.pt", map_location="cpu", weights_only=False)
    dim, lb, hz = ck["dim"], ck["lookback"], ck["horizon"]
    codes, days, X = F.field(stats_end=F.TRAIN_END)
    assert list(codes) == list(ck["codes"]), "동네 목록이 바뀌었다 --- 배선 중단"
    D = len(codes)
    K = 8

    class Enc(nn.Module):
        def __init__(self):
            super().__init__()
            self.emb = nn.Embedding(D, dim)
            self.tconv = nn.Linear(lb, dim)
            self.down = nn.Linear(D, K, bias=False)
            self.up = nn.Linear(K, D, bias=False)
            self.mix = nn.Linear(dim * 3, dim)
            self.head = nn.Linear(dim, 1)

        def forward(self, w):
            e = self.emb.weight.unsqueeze(0).expand(w.shape[0], -1, -1)
            h = torch.tanh(self.tconv(w))
            g = self.up(self.down(h.transpose(1, 2))).transpose(1, 2)
            return self.head(torch.tanh(self.mix(torch.cat([h, e, g], -1)))).squeeze(-1)

    net = Enc()
    net.load_state_dict(ck["state"])
    net.eval()
    Z = np.nan_to_num(X, nan=0.0)
    obs = np.isfinite(X)
    idx, sd = [], []
    with torch.no_grad():
        for t in range(lb, X.shape[1]):
            w = torch.tensor(Z[:, t - lb:t][None, ...], dtype=torch.float32)
            p = net(w).numpy()[0]
            m = obs[:, t]                      # 그 날 관측된 동네만
            if m.sum() < 30:
                continue
            idx.append(t); sd.append(float(np.std(p[m])))
    yrs = np.array([int(days[i][:4]) + (int(days[i][4:6]) - 1) / 12
                    + (int(days[i][6:]) - 1) / 365 for i in idx])
    return yrs, np.array(sd), days, ck


def main():
    yrs, sd, days, ck = spread_series()
    print(json.dumps({"축 원천": {"날 수": len(sd), "첫": round(float(yrs[0]), 2),
                              "끝": round(float(yrs[-1]), 2),
                              "SD 범위": [round(float(sd.min()), 4),
                                       round(float(sd.max()), 4)],
                              "SD 중앙": round(float(np.median(sd)), 4),
                              "최선 걸음(저장물)": ck.get("epoch", "안 적힘")}},
                     ensure_ascii=False), flush=True)

    d0 = shell(base())
    doms = sorted(d0.dom)

    def build(vals):
        """도메인 안 백분위 1열. **위쪽은 앞채움**(노트 753).

        노트 744 는 `y <= yrs[-1]` 을 마스크에 넣어 **유보 안에 구멍**을 만들었고
        노트 752 가 그것이 판 비용을 4.2배로 만드는 것을 쟀다. 여기서는 장의 끝을
        넘는 행에 **마지막 관측값**을 쓴다 --- 예보 시점에 관측 가능하므로 시간
        게이트를 통과하고, 배포에서 실제로 하는 일이다.
        """
        ax = {}
        for dm in doms:
            y = np.asarray(d0.yr[dm], float)
            v = np.full(len(y), np.nan)
            ok = np.isfinite(y) & (y >= yrs[0])          # **위쪽 경계를 없앤다**
            if ok.sum():
                j = np.searchsorted(yrs, y[ok])
                j = np.clip(j, 0, len(vals) - 1)          # 끝을 넘으면 마지막 값
                v[ok] = vals[j]
            m = np.isfinite(v)
            r = np.full(len(y), 0.5, np.float32)
            if m.sum() >= 3:
                from scipy.stats import rankdata
                r[m] = (rankdata(v[m]) / m.sum()).astype(np.float32)
            ax[dm] = (r, m.astype(np.float32))
        return ax

    def wiring(ax):
        out = {}
        for dm in doms:
            y = np.asarray(d0.yr[dm], float)
            te = np.isfinite(y) & (y >= T)
            m = np.asarray(ax[dm][1]) > 0
            out[dm] = {"관측": int(m.sum()), "행": len(m),
                       "덮음률": round(float(m.mean()), 3),
                       "**유보 덮음률**": round(float((te & m).sum()
                                                / max(int(te.sum()), 1)), 3),
                       "고유": int(len(np.unique(ax[dm][0][m])))}
        return out

    real = build(sd)
    wr = wiring(real)
    print(json.dumps({"배선": wr}, ensure_ascii=False), flush=True)
    bad = [dm for dm in doms if wr[dm]["관측"] == 0 or wr[dm]["고유"] < 3]
    hole = [dm for dm in doms if wr[dm]["**유보 덮음률**"] < 0.999]
    if bad or hole:
        print(json.dumps({"중단": f"중립화 의심 {bad} · 유보 구멍 {hole}"},
                         ensure_ascii=False), flush=True)
        return

    b0 = board(d0)
    print(json.dumps({"① 없이": b0["판"], "씨앗SD": b0["씨앗SD"]},
                     ensure_ascii=False), flush=True)
    if not (BASE_OK[0] <= b0["판"] <= BASE_OK[1]):
        print(json.dumps({"중단": f"기준선 {b0['판']} 이 {BASE_OK} 밖"},
                         ensure_ascii=False), flush=True)
        return
    b1 = board(shell({**base(), AX: real}))
    print(json.dumps({"② 진짜": b1["판"], "씨앗SD": b1["씨앗SD"]},
                     ensure_ascii=False), flush=True)

    plac = {}
    for ds in PLACEBO_DRAWS:
        rng = np.random.default_rng(ds)
        ax = {}
        for dm in doms:
            v, m = real[dm]
            v2 = np.asarray(v, np.float32).copy()
            ii = np.flatnonzero(np.asarray(m) > 0)
            if len(ii) > 1:
                sh = v2[ii].copy(); rng.shuffle(sh); v2[ii] = sh
            ax[dm] = (v2, m)
        r = board(shell({**base(), AX: ax}))
        plac[f"위약 {ds}"] = r
        print(json.dumps({f"위약 {ds}": r["판"], "씨앗SD": r["씨앗SD"]},
                         ensure_ascii=False), flush=True)

    pv = np.array([plac[t]["판"] for t in plac])
    bb = np.array(b0["씨앗별"]); r1 = np.array(b1["씨앗별"])
    d_net = bb - r1
    sig = round(float(b1["판"] - pv.mean()), 4)
    net_ = round(float(b1["판"] - b0["판"]), 4)
    W = d0.weights(T); tot = sum(W.values())
    per = {}
    for dm in set(b1["도메인"]) & set(b0["도메인"]):
        pm = float(np.mean([plac[t]["도메인"].get(dm, np.nan) for t in plac]))
        per[dm] = {"신호 몫": round(b1["도메인"][dm] - pm, 4),
                   "순효과": round(b1["도메인"][dm] - b0["도메인"][dm], 4),
                   "유보": W.get(dm, 0), "덮음률": wr[dm]["덮음률"],
                   "판 기여": round((b1["도메인"][dm] - pm) * W.get(dm, 0) / tot, 5)}
    print("=== 모아서 ===", flush=True)
    print(json.dumps({
        "없이": b0["판"], "진짜": b1["판"],
        "위약 셋": {t: plac[t]["판"] for t in plac},
        "위약 평균": round(float(pv.mean()), 4),
        "**위약 뽑기 SD**": round(float(pv.std(ddof=1)), 4),
        "**위약 폭(최대−최소)**": round(float(pv.max() - pv.min()), 4),
        "**신호 몫(진짜 − 위약평균)**": sig,
        "**순효과(진짜 − 없이)**": net_,
        "순효과 짝SD": round(float(d_net.std(ddof=1)), 4),
        "문턱 판 2σ": 0.0045,
        "판정 (가) 신호 몫 > 0.0045 이고 위약 셋 전부보다 큼":
            bool(sig > 0.0045 and b1["판"] > pv.max()),
        "판정 (나) 문턱 안": bool(abs(sig) <= 0.0045),
        "판정 (다) 순효과 음수 · 신호 몫 양수": bool(net_ < 0 < sig),
        "판정 (라) 위약 폭 > 신호 몫": bool((pv.max() - pv.min()) > abs(sig)),
        "도메인별": dict(sorted(per.items(), key=lambda x: -abs(x[1]["판 기여"]))),
        "팝업·시장팝업 뺀 신호 몫":
            round(sum(per[d]["신호 몫"] * W[d] for d in per
                      if d not in ("팝업", "시장팝업") and d in W)
                  / max(sum(W[d] for d in per
                            if d not in ("팝업", "시장팝업") and d in W), 1e-9), 4),
        "배선": wr,
        "노트 745 신호 몫": -0.0132, "노트 745 순효과": -0.0434,
        "노트 745 위약 비용": 0.0302,
        "**위약 비용(없이 − 위약평균)**": round(float(b0["판"] - pv.mean()), 4),
        "판정 (가) 신호 몫 < −0.0045": bool(sig < -0.0045),
        "판정 (나) 문턱 안": bool(abs(sig) <= 0.0045),
        "판정 (다) 신호 몫 > +0.0045 → 노트 745 철회": bool(sig > 0.0045),
        "판정 (라) 위약 비용 > 0.020 → 앞채움 실패":
            bool(b0["판"] - pv.mean() > 0.020),
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
