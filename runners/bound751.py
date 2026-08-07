"""노트 751 — **마스크 경계가 유보 안을 가르면 비싼가.** 그것 하나만 바꾼다.

노트 748 의 ① 동률 없음 팔(0.0074)과 모든 것이 같고 **마스크만** 양쪽 경계
(`2020.15 ≤ y ≤ 2026.51`)로 바꾼다. 장이 2026.51 에 끝나므로 **유보 3,473행 중
201행(5.8%)이 마스크 0** 이 된다.
"""
import json
import sys

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
from scipy.stats import rankdata

from lab import forms, loop as L
from lab.harness import evaluate

T = 2025.0
SEEDS = (0, 1, 2)
DRAWS = (7510, 7511)
LO, HI = 2020.15, 2026.51
CLS = forms.REGISTRY["F18_bagboost"]["cls"]
AX = "boundjunk"


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
    vals = []
    for s in SEEDS:
        sc = evaluate(lambda s=s: CLS(seed=s), data, T=T)
        vals.append(float(data.pooled(sc, T=T)))
    return {"판": round(float(np.mean(vals)), 4),
            "씨앗별": [round(v, 4) for v in vals],
            "씨앗SD": round(float(np.std(vals, ddof=1)), 4)}


def main():
    d0 = shell(base())
    doms = sorted(d0.dom)
    b0 = board(d0)
    print(json.dumps({"없이": b0["판"]}, ensure_ascii=False), flush=True)
    out = {}
    for ds in DRAWS:
        rng = np.random.default_rng(ds)
        ax = {}
        te_tot = te_cov = 0
        for dm in doms:
            y = np.asarray(d0.yr[dm], float)
            m = np.isfinite(y) & (y >= LO) & (y <= HI)   # **양쪽 경계**
            v = np.full(len(y), 0.5, np.float32)
            if m.sum() >= 3:
                v[m] = (rankdata(rng.random(int(m.sum()))) / m.sum()).astype(np.float32)
            ax[dm] = (v, m.astype(np.float32))
            te = np.isfinite(y) & (y >= T)
            te_tot += int(te.sum()); te_cov += int((te & m).sum())
        r = board(shell({**base(), AX: ax}))
        r["하락"] = round(b0["판"] - r["판"], 4)
        r["유보 마스크0"] = te_tot - te_cov
        r["유보 덮음률"] = round(te_cov / max(te_tot, 1), 3)
        out[f"뽑기 {ds}"] = r
        print(f"[뽑기 {ds}] " + json.dumps(
            {"판": r["판"], "하락": r["하락"], "유보 마스크0": r["유보 마스크0"]},
            ensure_ascii=False), flush=True)
    v = np.array([out[t]["하락"] for t in out])
    print("=== 모아서 ===", flush=True)
    print(json.dumps({
        "없이": b0["판"],
        "**양쪽 경계 마스크 비용**": round(float(v.mean()), 4),
        "뽑기별": [round(float(x), 4) for x in v],
        "노트 748 ① 아래경계만": 0.0074, "그 SD": 0.0017,
        "노트 745·750 위약": [0.0302, 0.0326, 0.0288],
        "**차 (양쪽 − 아래만)**": round(float(v.mean() - 0.0074), 4),
        "판정 (가) 0.018 넘음": bool(v.mean() > 0.018),
        "판정 (나) 0.012 안": bool(v.mean() <= 0.012),
        "판정 (다) 그 사이": bool(0.012 < v.mean() <= 0.018),
        "유보 마스크0 행": out[f"뽑기 {DRAWS[0]}"]["유보 마스크0"],
        "팔별": out,
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
