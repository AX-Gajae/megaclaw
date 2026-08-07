"""출시 혼잡도 — (시간 × 대상) 형태의 첫 무료 축(노트 650).

팔 셋. **열은 하나**(노트 641).
  없이 / crowd_share / **위약**(갈래만 섞고 관측 무늬는 유지, 노트 335)

위약을 이번엔 **같이** 돌린다 — 노트 640 이 가르쳤듯 위약이 진짜보다 나쁘지
않으면 신호가 아니라 차원 비용이다. 나중에 따로 돌리면 사이클이 갈린다.
"""
import json
import numpy as np
from lab import forms, loop as L
from lab.harness import evaluate

CLS = forms.REGISTRY["F18_bagboost"]["cls"]
SEEDS = 12


def arm(mode):
    def mk():
        e = {**L._trendsub(zero_is_data=True), **L._calsub(), **L._wikisub(),
             **L._tag(), **L._fund(), **L._rawsub(), **L._grp(), **L._gen()}
        if mode != "없이":
            from lab.crowdaxes import build as cb
            w = cb()
            if not w:
                raise SystemExit("혼잡도 축이 비었다")
            if mode == "위약":
                rng = np.random.default_rng(650)
                w = {k: {d: (_shuf(v[0], v[1], rng), v[1])
                         for d, v in byd.items()} for k, byd in w.items()}
            e.update(w)
        return e
    return L._idol(mk, mode="cut", with_wiki=True, with_trend=True,
                   wide_post=True, wide_pop="grades")


def _shuf(v, m, rng):
    v = np.asarray(v, float).copy()
    idx = np.flatnonzero(np.asarray(m) > 0)
    v[idx] = v[rng.permutation(idx)]
    return v


def check(data):
    out = {}
    for dom, (A, M, _y, _t) in data.dom.items():
        nm = data.names.get(dom, [])
        if "crowd_share" in nm:
            j = nm.index("crowd_share")
            out[dom] = int((M[:, j] > 0).sum())
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
for lbl in ("혼잡도", "위약"):
    d = arm(lbl)
    print(json.dumps({f"{lbl} 붙었나": check(d)}, ensure_ascii=False), flush=True)
    b1, p1 = per_seed(d)
    diff = b1 - b0
    out[lbl] = {"없이": round(float(b0.mean()), 4), "있고": round(float(b1.mean()), 4),
                "차": round(float(diff.mean()), 4),
                "씨앗SE": round(float(diff.std(ddof=1) / np.sqrt(len(diff))), 4),
                "양수": f"{int((diff > 0).sum())}/{len(diff)}"}
    out[lbl + "·도메인"] = {k: round(float((p1[k] - p0[k]).mean()), 4)
                          for k in sorted(set(p0) & set(p1))
                          if len(p0[k]) == len(p1[k])}
    print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)
print(json.dumps({"문턱": 0.0045}, ensure_ascii=False), flush=True)
