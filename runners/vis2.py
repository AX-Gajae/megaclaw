"""방문자 축을 시장팝업에도 붙인다 — 행을 늘리면 넘나(노트 660).

팔 넷. **열은 하나**(`vis_out`).
  없이 / 팝업만(노트 641 재현) / 팝업+시장팝업 / 위약(팝업+시장팝업, 값만 섞음)

②와 ③의 차가 **행을 늘린 몫**이다. ③과 ④의 차가 **신호 몫**이다.
"""
import json
import numpy as np
from lab import forms, loop as L
from lab.harness import evaluate

CLS = forms.REGISTRY["F18_bagboost"]["cls"]
SEEDS = 12
AX = "vis_out"


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
        from lab import visitoraxes as V
        old = V.DOMS
        V.DOMS = ("팝업",) if mode == "팝업만" else ("팝업", "시장팝업")
        try:
            w = V.build(axes=(AX,))
        finally:
            V.DOMS = old
        if not w:
            raise SystemExit(f"{mode}: 축이 비었다")
        if mode == "위약":
            rng = np.random.default_rng(660)
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
            j = nm.index(AX)
            n = int((M[:, j] > 0).sum())
            if n:
                out[dom] = n
    return out


def per_seed(data):
    b, per = [], {}
    for s in range(SEEDS):
        sc = evaluate(lambda s=s: CLS(seed=s), data)
        b.append(float(data.pooled(sc)))
        for k, v in sc.items():
            if np.isfinite(v):
                per.setdefault(k, []).append(float(v))
    return np.array(b), {k: np.array(v) for k, v in per.items()}


b0, p0 = per_seed(arm("없이"))
print(json.dumps({"없이 판": round(float(b0.mean()), 4)}, ensure_ascii=False), flush=True)
out = {}
for mode in ("팝업만", "팝업+시장", "위약"):
    d = arm(mode)
    print(json.dumps({f"{mode} 붙은 곳": where(d)}, ensure_ascii=False), flush=True)
    b1, p1 = per_seed(d)
    diff = b1 - b0
    out[mode] = {"판": round(float(b1.mean()), 4), "차": round(float(diff.mean()), 4),
                 "씨앗SE": round(float(diff.std(ddof=1) / np.sqrt(len(diff))), 4),
                 "양수": f"{int((diff > 0).sum())}/{len(diff)}"}
    out[mode + "·도메인"] = {k: round(float((p1[k] - p0[k]).mean()), 4)
                           for k in ("팝업", "시장팝업") if k in p0 and k in p1
                           and len(p0[k]) == len(p1[k])}
    print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)
print(json.dumps({"문턱": 0.0045}, ensure_ascii=False), flush=True)
