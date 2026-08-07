"""노트 675 — 고친 `crowd_share` 로 판을 돈다. 세 팔 · 열 하나 · T=2025."""
import json
import numpy as np
from lab import forms, loop as L, guards as G
from lab.harness import evaluate

CLS = forms.REGISTRY["F18_bagboost"]["cls"]
SEEDS = 12
AX = "crowd_share"
T = 2025.0


def _shuf(v, m, rng):
    v = np.asarray(v, float).copy()
    idx = np.flatnonzero(np.asarray(m) > 0)
    v[idx] = v[rng.permutation(idx)]
    return v


def arm(mode):
    def mk():
        e = {**L._trendsub(zero_is_data=True), **L._calsub(), **L._wikisub(),
             **L._tag(), **L._fund(), **L._rawsub(), **L._grp(), **L._gen()}
        if mode == "없이":
            return e
        from lab import crowdaxes as C
        w = C.build()
        if not w:
            raise SystemExit("축이 비었다")
        if mode == "위약":
            rng = np.random.default_rng(675)
            w = {k: {d: (_shuf(v[0], v[1], rng), v[1]) for d, v in byd.items()}
                 for k, byd in w.items()}
        e.update(w)
        return e
    return L._idol(mk, mode="cut", with_wiki=True, with_trend=True,
                   wide_post=True, wide_pop="grades")


def where(data):
    out = {}
    for dom, (A, M, _y, _t) in data.dom.items():
        nm = data.names.get(dom, [])
        if AX in nm:
            n = int((M[:, nm.index(AX)] > 0).sum())
            if n:
                out[dom] = n
    return out


def per_seed(data):
    b, per = [], {}
    for s in range(SEEDS):
        sc = evaluate(lambda s=s: CLS(seed=s), data, T=T)
        b.append(float(data.pooled(sc, T=T)))
        for k, v in sc.items():
            if np.isfinite(v):
                per.setdefault(k, []).append(float(v))
    return np.array(b), {k: np.array(v) for k, v in per.items()}


def gate3(data):
    """관문 ③ — 기존 축과의 상관. `_drop_mode` 를 걸어 잰다(노트 653)."""
    from scipy.stats import spearmanr
    out = {}
    for dom in data.dom:
        nm = list(data.names.get(dom) or [])
        if AX not in nm:
            continue
        A, M = data.dom[dom][0], data.dom[dom][1]
        j = nm.index(AX)
        mine = A[:, j]; ok = M[:, j] > 0
        best = {}
        for other in nm:
            if other == AX or not (other.startswith(("gen", "trend_", "grp"))
                                   or other in ("wiki_level", "wiki_momentum")):
                continue
            jo = nm.index(other)
            k = ok & (M[:, jo] > 0)
            if k.sum() < 50:
                continue
            a, b = G._drop_mode(mine[k], A[:, jo][k])
            if a is None or len(a) < 50:
                continue
            r = abs(float(spearmanr(a, b).statistic))
            if np.isfinite(r):
                best[other] = round(r, 3)
        if best:
            top = sorted(best.items(), key=lambda x: -x[1])[:4]
            out[dom] = {"최대": top[0], "상위": top}
    return out


d0 = arm("없이")
b0, p0 = per_seed(d0)
print(json.dumps({"없이 판": round(float(b0.mean()), 4),
                  "씨앗SD": round(float(b0.std(ddof=1)), 4)}, ensure_ascii=False), flush=True)
out = {}
for mode in ("진짜", "위약"):
    d = arm(mode)
    print(json.dumps({f"{mode} 붙은 곳": where(d)}, ensure_ascii=False), flush=True)
    if mode == "진짜":
        print(json.dumps({"관문③ 기존축 상관": gate3(d)}, ensure_ascii=False), flush=True)
    b1, p1 = per_seed(d)
    diff = b1 - b0
    out[mode] = {"판": round(float(b1.mean()), 4), "차": round(float(diff.mean()), 4),
                 "씨앗SE": round(float(diff.std(ddof=1) / np.sqrt(len(diff))), 4),
                 "양수": f"{int((diff > 0).sum())}/{len(diff)}"}
    out[mode + "·도메인"] = {k: round(float((p1[k] - p0[k]).mean()), 4)
                           for k in p0 if k in p1 and len(p0[k]) == len(p1[k])}
    print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)
sig = out["진짜"]["차"] - out["위약"]["차"]
print(json.dumps({"**신호 몫(②−③)**": round(sig, 4), "**순효과(②−①)**": out["진짜"]["차"],
                  "문턱": 0.0045}, ensure_ascii=False), flush=True)
