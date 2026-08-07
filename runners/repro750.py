"""노트 750 — **노트 745 의 0.0302 를 재현한다.** 축 만들기를 한 글자도 안 고친다.

`field744` 의 `spread_series` 와 축 만들기를 그대로 부른다. 다른 것은 모형 씨앗
3(원래 6)뿐이다. **설명을 쫓기 전에 재현한다**(노트 749 의 규율).
"""
import json
import sys

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad")
from scipy.stats import rankdata

import field744 as F744
from lab import forms, loop as L
from lab.harness import evaluate

T = 2025.0
SEEDS = (0, 1, 2)
CLS = forms.REGISTRY["F18_bagboost"]["cls"]
AX = "field_spread"


def board(data):
    vals = []
    for s in SEEDS:
        sc = evaluate(lambda s=s: CLS(seed=s), data, T=T)
        vals.append(float(data.pooled(sc, T=T)))
    return {"판": round(float(np.mean(vals)), 4),
            "씨앗별": [round(v, 4) for v in vals],
            "씨앗SD": round(float(np.std(vals, ddof=1)), 4)}


def main():
    yrs, sd, days, ck = F744.spread_series()
    d0 = F744.shell(F744.base())
    doms = sorted(d0.dom)

    #: **노트 745 의 build() 를 그대로 옮긴다**
    def build(vals):
        ax = {}
        for dm in doms:
            y = np.asarray(d0.yr[dm], float)
            v = np.full(len(y), np.nan)
            ok = np.isfinite(y) & (y >= yrs[0]) & (y <= yrs[-1])
            if ok.sum():
                j = np.searchsorted(yrs, y[ok])
                j = np.clip(j, 0, len(vals) - 1)
                v[ok] = vals[j]
            m = np.isfinite(v)
            r = np.full(len(y), 0.5, np.float32)
            if m.sum() >= 3:
                r[m] = (rankdata(v[m]) / m.sum()).astype(np.float32)
            ax[dm] = (r, m.astype(np.float32))
        return ax

    real = build(sd)
    cov = round(sum(int(real[d][1].sum()) for d in doms)
                / sum(len(real[d][1]) for d in doms), 3)
    b0 = board(d0)
    print(json.dumps({"없이": b0["판"], "전체 덮음률": cov}, ensure_ascii=False), flush=True)
    out = {}
    for ds in (7440, 7441, 7442):
        rng = np.random.default_rng(ds)
        ax = {}
        for dm in doms:
            v, m = real[dm]
            v2 = np.asarray(v, np.float32).copy()
            ii = np.flatnonzero(np.asarray(m) > 0)
            if len(ii) > 1:
                sh = v2[ii].copy(); rng.shuffle(sh); v2[ii] = sh
            ax[dm] = (v2, m)
        r = board(F744.shell({**F744.base(), AX: ax}))
        r["하락"] = round(b0["판"] - r["판"], 4)
        out[f"위약 {ds}"] = r
        print(f"[위약 {ds}] " + json.dumps({"판": r["판"], "하락": r["하락"]},
                                        ensure_ascii=False), flush=True)
    v = np.array([out[t]["하락"] for t in out])
    print("=== 모아서 ===", flush=True)
    print(json.dumps({
        "없이(씨앗3)": b0["판"], "노트 745 없이(씨앗6)": 0.4685,
        "**위약 하락 평균**": round(float(v.mean()), 4),
        "**뽑기 SD**": round(float(v.std(ddof=1)), 4),
        "뽑기별": [round(float(x), 4) for x in v],
        "노트 745 위약 하락": 0.0302,
        "부분관측 1열 여섯 측정": [0.0068, 0.0074, 0.0107, 0.0042, 0.0061, 0.0157],
        "판정 (가) 0.020 넘게 재현": bool(v.mean() > 0.020),
        "판정 (나) 0.004~0.012 로 안 재현": bool(0.004 <= v.mean() <= 0.012),
        "판정 (다) 그 사이": bool(0.012 < v.mean() <= 0.020),
        "팔별": out,
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
