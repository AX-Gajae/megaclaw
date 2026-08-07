"""노트 746 — **결측 무늬가 비용을 정하나.** 값을 고정하고 마스크만 흔든다.

노트 745 의 부분관측 위약 1열이 −0.0302 이고 노트 742 의 완전관측 쓰레기 1열은
약 0.005 다. **6배 차이의 유일한 후보가 결측 무늬**다. 여기서는 난수 값을
고정하고 **덮음률만** 1.00 / 0.53 / 0.27 로 바꾼다. 마스크는 무작위가 아니라
**시기로 잘린 무늬**(장이 2020 부터라 오래된 행이 빠지는 그 모양)를 쓴다.

모든 팔이 위약이므로 신호 주장을 하지 않는다.
"""
import json
import sys
import time

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
from scipy.stats import rankdata

from lab import forms, loop as L
from lab.harness import evaluate

T = 2025.0
SEEDS = (0, 1, 2)
DRAWS = (7460, 7461, 7462)
#: (이름, 덮음 컷오프 소수연도) --- None 이면 전부 관측
COVS = [("덮음 1.00", None), ("덮음 0.53", 2020.15), ("덮음 0.27", 2023.2)]
CLS = forms.REGISTRY["F18_bagboost"]["cls"]
AX = "maskjunk"
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


def main():
    d0 = shell(base())
    doms = sorted(d0.dom)
    b0 = board(d0)
    print(json.dumps({"① 없이": b0["판"], "씨앗SD": b0["씨앗SD"]},
                     ensure_ascii=False), flush=True)
    if not (BASE_OK[0] <= b0["판"] <= BASE_OK[1]):
        print(json.dumps({"중단": f"기준선 {b0['판']}"}, ensure_ascii=False), flush=True)
        return

    out = {}
    for ds in DRAWS:
        rng = np.random.default_rng(ds)
        raw = {dm: rng.random(len(d0.dom[dm][2])) for dm in doms}
        for nm, cut in COVS:
            ax = {}
            for dm in doms:
                y = np.asarray(d0.yr[dm], float)
                m = np.isfinite(y) if cut is None else (np.isfinite(y) & (y >= cut))
                v = np.full(len(y), 0.5, np.float32)
                if m.sum() >= 3:
                    # **관측 행만으로 순위** --- 노트 745 축과 같은 변환
                    v[m] = (rankdata(raw[dm][m]) / m.sum()).astype(np.float32)
                ax[dm] = (v, m.astype(np.float32))
            wr = {dm: {"관측": int(ax[dm][1].sum()), "행": len(ax[dm][1]),
                       "덮음률": round(float(ax[dm][1].mean()), 3)} for dm in doms}
            covall = round(sum(wr[dm]["관측"] for dm in doms)
                           / sum(wr[dm]["행"] for dm in doms), 3)
            t0 = time.time()
            r = board(shell({**base(), AX: ax}))
            r["하락"] = round(b0["판"] - r["판"], 4)
            r["전체 덮음률"] = covall
            r["배선"] = wr
            out[f"{nm} · 뽑기 {ds}"] = r
            print(f"[{nm} · 뽑기 {ds}] " + json.dumps(
                {"판": r["판"], "하락": r["하락"], "덮음": covall,
                 "초": round(time.time() - t0, 1)}, ensure_ascii=False), flush=True)

    agg = {}
    for nm, _ in COVS:
        ds_vals = np.array([out[f"{nm} · 뽑기 {d}"]["하락"] for d in DRAWS])
        agg[nm] = {"하락 평균": round(float(ds_vals.mean()), 4),
                   "**뽑기 SD**": round(float(ds_vals.std(ddof=1)), 4),
                   "뽑기별": [round(float(v), 4) for v in ds_vals],
                   "전체 덮음률": out[f"{nm} · 뽑기 {DRAWS[0]}"]["전체 덮음률"]}
    full = agg["덮음 1.00"]["하락 평균"]
    half = agg["덮음 0.53"]["하락 평균"]
    thin = agg["덮음 0.27"]["하락 평균"]
    sdmax = max(agg[nm]["**뽑기 SD**"] for nm, _ in COVS)
    print("=== 모아서 ===", flush=True)
    print(json.dumps({
        "기준선(없이)": b0["판"],
        "**덮음률별 1열 비용**": agg,
        "**0.53 − 1.00**": round(half - full, 4),
        "**0.27 − 1.00**": round(thin - full, 4),
        "최대 뽑기 SD": sdmax,
        "판정 (가) 0.53 > 1.00 + 3×뽑기SD": bool(half > full + 3 * sdmax),
        "판정 (나) 셋이 비슷(폭 < 3×뽑기SD)":
            bool(max(full, half, thin) - min(full, half, thin) < 3 * sdmax),
        "판정 (다) 0.27 이 0.53 보다 싸다": bool(thin < half),
        "노트 742 완전관측 1열": 0.006,
        "노트 745 부분관측 위약 1열": 0.0302,
        "틀림 조건 · 1.00 팔이 노트 742 에서 3×뽑기SD 밖":
            bool(abs(full - 0.006) > 3 * sdmax),
        "팔별": out,
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
