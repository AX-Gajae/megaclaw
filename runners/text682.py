"""노트 681 — 텍스트 열 하나의 **증분**. 세 팔 · T=2025 · 씨앗 12."""
import json
import numpy as np
from lab import forms, loop as L, guards as G, textaxes as TX
from lab.harness import evaluate

CLS = forms.REGISTRY["F18_bagboost"]["cls"]
SEEDS = 40
T = 2025.0
AX = TX.AX


def base():
    return {**L._trendsub(zero_is_data=True), **L._calsub(), **L._wikisub(),
            **L._tag(), **L._fund(), **L._rawsub(), **L._grp(), **L._gen()}


def _shuf(v, m, rng):
    v = np.asarray(v, float).copy()
    idx = np.flatnonzero(np.asarray(m) > 0)
    v[idx] = v[rng.permutation(idx)]
    return v


# 축은 `data` 를 필요로 하므로 **없이 팔의 data 로 한 번 만들어** 세 팔에 같이 쓴다.
d0 = L._idol(lambda: base(), mode="cut", with_wiki=True, with_trend=True,
             wide_post=True, wide_pop="grades")
W = TX.build(d0, T=T, report=True)
if not W:
    raise SystemExit("텍스트 축이 비었다")


def arm(mode):
    def mk():
        e = base()
        if mode == "없이":
            return e
        w = W
        if mode == "위약":
            rng = np.random.default_rng(681)
            w = {k: {dm: (_shuf(v[0], v[1], rng), v[1]) for dm, v in byd.items()}
                 for k, byd in W.items()}
        e.update(w)
        return e
    return L._idol(mk, mode="cut", with_wiki=True, with_trend=True,
                   wide_post=True, wide_pop="grades")


def where(data):
    o = {}
    for dm, (A, M, _y, _t) in data.dom.items():
        nm = data.names.get(dm, [])
        if AX in nm:
            n = int((M[:, nm.index(AX)] > 0).sum())
            if n:
                o[dm] = n
    return o


def gate3(data):
    from scipy.stats import spearmanr
    o = {}
    for dm in data.dom:
        nm = list(data.names.get(dm) or [])
        if AX not in nm:
            continue
        A, M = data.dom[dm][0], data.dom[dm][1]
        j = nm.index(AX)
        mine, ok = A[:, j], M[:, j] > 0
        best = {}
        for other in nm:
            if other == AX or not (other.startswith(("gen", "grp", "trend_", "wiki_"))
                                   or other.startswith("meta_")):
                continue
            jo = nm.index(other)
            kk = ok & (M[:, jo] > 0)
            if kk.sum() < 50:
                continue
            a, b = G._drop_mode(mine[kk], A[:, jo][kk])
            if a is None or len(a) < 50:
                continue
            r = abs(float(spearmanr(a, b).statistic))
            if np.isfinite(r):
                best[other] = round(r, 3)
        if best:
            o[dm] = sorted(best.items(), key=lambda x: -x[1])[:4]
    return o


def per_seed(data):
    b, per = [], {}
    for s in range(SEEDS):
        sc = evaluate(lambda s=s: CLS(seed=s), data, T=T)
        b.append(float(data.pooled(sc, T=T)))
        for k, v in sc.items():
            if np.isfinite(v):
                per.setdefault(k, []).append(float(v))
    return np.array(b), {k: np.array(v) for k, v in per.items()}


b0, p0 = per_seed(d0)
print(json.dumps({"없이 판": round(float(b0.mean()), 4),
                  "씨앗SD": round(float(b0.std(ddof=1)), 4)}, ensure_ascii=False), flush=True)
out = {}
for mode in ("진짜", "위약"):
    d = arm(mode)
    print(json.dumps({f"{mode} 붙은 곳": where(d)}, ensure_ascii=False), flush=True)
    if mode == "진짜":
        print(json.dumps({"관문③": gate3(d)}, ensure_ascii=False), flush=True)
    b1, p1 = per_seed(d)
    diff = b1 - b0
    out[mode] = {"판": round(float(b1.mean()), 4), "차": round(float(diff.mean()), 4),
                 "씨앗SE": round(float(diff.std(ddof=1) / np.sqrt(len(diff))), 4),
                 "양수": f"{int((diff > 0).sum())}/{len(diff)}"}
    out[mode + "·도메인"] = {k: round(float((p1[k] - p0[k]).mean()), 4)
                           for k in p0 if k in p1 and len(p0[k]) == len(p1[k])}
    print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)
sig = out["진짜"]["차"] - out["위약"]["차"]
print(json.dumps({"**신호 몫**": round(sig, 4), "**순효과**": out["진짜"]["차"],
                  "문턱": 0.0045,
                  "DOMDROP 걸린 도메인(따로 읽는다)": ["만화", "애니"]},
                 ensure_ascii=False), flush=True)
