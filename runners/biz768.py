"""노트 768 — **R² 0.1200 이 사업 물음으로 번역되나.** 어디에 · 언제 열면 좋나.

🔴 **판 주장이 아니다** --- 노트 767 이 장을 독립 산출물로 확정했고, 이 실험은
그 산출물이 **운영자가 이미 하는 선택보다 나은가**를 잰다. 장은 동네 평균 · 요일 ·
전국 · 공휴일을 다 뺀 잔차이므로, **운영자가 아는 것을 전부 제거한 뒤**의 예보다.
"""
import datetime
import json
import sys

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
import torch
import torch.nn as nn
from scipy.stats import spearmanr

from state import fieldmodel as F

T_END = F.TRAIN_END        # '20241231'
HZ = 30
BOOT = 200
RNG = np.random.default_rng(768)


def load_enc(D):
    ck = torch.load(F.OUT / "enc.pt", map_location="cpu", weights_only=False)
    dim, lb = ck["dim"], ck["lookback"]
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

    net = Enc(); net.load_state_dict(ck["state"]); net.eval()
    return net, lb, ck


def main():
    from ingest.visitors import series
    ser = series("2")
    codes, days, Xres = F.field(stats_end=T_END)        # 잔차(장)
    di = {d: i for i, d in enumerate(days)}
    # ── 원천 로그 수준
    M = np.full((len(codes), len(days)), np.nan)
    for r, c in enumerate(codes):
        for d, v in ser[c].items():
            if d in di and v and v > 0:
                M[r, di[d]] = np.log10(v)
    fit = np.array([d <= T_END for d in days])
    lvl = np.nanmean(M[:, fit], axis=1)                 # 동네 학습 평균 수준
    dow = np.array([datetime.date(int(d[:4]), int(d[4:6]), int(d[6:8])).weekday()
                    for d in days])
    mon = np.array([int(d[4:6]) for d in days])
    # 요일·월 효과(학습 구간 · 동네마다)
    dow_e = np.zeros((len(codes), 7)); mon_e = np.zeros((len(codes), 13))
    for w in range(7):
        m = fit & (dow == w)
        dow_e[:, w] = np.nan_to_num(np.nanmean(M[:, m], axis=1) - lvl)
    for mo in range(1, 13):
        m = fit & (mon == mo)
        with np.errstate(all="ignore"):
            mon_e[:, mo] = np.nan_to_num(np.nanmean(M[:, m], axis=1) - lvl)

    net, lb, ck = load_enc(len(codes))
    assert list(ck["codes"]) == list(codes), "동네 목록 불일치 --- 배선 중단"
    Z = np.nan_to_num(Xres, nan=0.0)
    end = next((i for i, d in enumerate(days) if d > T_END), len(days))

    # ── 예보: 날짜 t 에서 창 [t-lb, t) 로 t+HZ 의 잔차 변화 Δ
    ts = [t for t in range(max(lb, end), len(days) - HZ)]
    dhat = {}
    with torch.no_grad():
        for t in ts:
            w = torch.tensor(Z[:, t - lb:t][None, ...], dtype=torch.float32)
            dhat[t] = net(w).numpy()[0]
    sp = np.array([np.std(dhat[t]) for t in ts])
    raw_sd = float(np.nanstd(Xres[:, end:]))
    print(json.dumps({"유보 날짜 수": len(ts), "동네": len(codes),
                      "첫 t": days[ts[0]], "끝 t": days[ts[-1]],
                      "예보 동네간 SD 중앙": round(float(np.median(sp)), 5),
                      "원천 잔차 SD": round(raw_sd, 5),
                      "틀림조건 · 예보 SD < 원천 10%":
                          bool(np.median(sp) < 0.1 * raw_sd),
                      "최선 걸음(저장물)": ck.get("epoch", "안 적힘")},
                     ensure_ascii=False), flush=True)

    # ── ① 어디 --- 날짜 고정, 동네 순위
    where = {"소박": [], "소박+장": [], "top10_소박": [], "top10_장": []}
    for t in ts:
        tt = t + HZ
        act = M[:, tt]
        ok = np.isfinite(act) & np.isfinite(lvl)
        if ok.sum() < 30:
            continue
        a = lvl[ok] + dow_e[ok, dow[tt]] + mon_e[ok, mon[tt]]
        b = a + dhat[t][ok]
        where["소박"].append(float(spearmanr(a, act[ok]).statistic))
        where["소박+장"].append(float(spearmanr(b, act[ok]).statistic))
        k = 10
        top_act = set(np.argsort(-act[ok])[:k].tolist())
        where["top10_소박"].append(len(top_act & set(np.argsort(-a)[:k].tolist())))
        where["top10_장"].append(len(top_act & set(np.argsort(-b)[:k].tolist())))

    # ── ② 언제 --- 동네 고정, 날짜 순위
    when = {"소박": [], "소박+장": []}
    for r in range(len(codes)):
        aa, bb, yy = [], [], []
        for t in ts:
            tt = t + HZ
            if not np.isfinite(M[r, tt]):
                continue
            base = lvl[r] + dow_e[r, dow[tt]] + mon_e[r, mon[tt]]
            aa.append(base); bb.append(base + dhat[t][r]); yy.append(M[r, tt])
        if len(yy) < 40:
            continue
        when["소박"].append(float(spearmanr(aa, yy).statistic))
        when["소박+장"].append(float(spearmanr(bb, yy).statistic))

    def boot(a, b):
        """짝지은 차의 부트스트랩 2σ(노트 683 --- 배율 어림 금지)."""
        a, b = np.array(a), np.array(b)
        d = b - a
        n = len(d)
        vs = [float(d[RNG.integers(0, n, n)].mean()) for _ in range(BOOT)]
        return {"소박": round(float(a.mean()), 4), "소박+장": round(float(b.mean()), 4),
                "**Δ**": round(float(d.mean()), 4),
                "부트 SD": round(float(np.std(vs, ddof=1)), 4),
                "**2σ**": round(2 * float(np.std(vs, ddof=1)), 4),
                "**2σ 밖**": bool(abs(d.mean()) > 2 * np.std(vs, ddof=1)),
                "n": n}
    w1 = boot(where["소박"], where["소박+장"])
    w2 = boot(when["소박"], when["소박+장"])
    t10 = boot(where["top10_소박"], where["top10_장"])
    print("=== 모아서 ===", flush=True)
    print(json.dumps({
        "🔴 판 주장 아님": "노트 767 이 장을 독립 산출물로 확정 --- 이것은 결정 지표다",
        "**① 어디(동네 순위)**": w1,
        "**② 언제(날짜 순위)**": w2,
        "**top-10 적중(어디 · 10 중 몇)**": t10,
        "판정 (가) 어디 또는 언제 Δ 가 2σ 밖 양수":
            bool((w1["**2σ 밖**"] and w1["**Δ**"] > 0)
                 or (w2["**2σ 밖**"] and w2["**Δ**"] > 0)),
        "판정 (나) 둘 다 2σ 안":
            bool(not w1["**2σ 밖**"] and not w2["**2σ 밖**"]),
        "판정 (다) 2σ 밖 음수":
            bool((w1["**2σ 밖**"] and w1["**Δ**"] < 0)
                 or (w2["**2σ 밖**"] and w2["**Δ**"] < 0)),
        "틀림조건 · 어디 소박 < 0.5": bool(w1["소박"] < 0.5),
        "노트 736 유보 R2": 0.1200,
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
