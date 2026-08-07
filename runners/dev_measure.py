"""수준이 아니라 편차 — 상태 축의 형태 규칙(노트 649).

세 팔을 같은 저울로. **팔마다 열 하나**(노트 641 의 열 예산).
  없이 / nat_mom(이미 차분) / nat_dev(365일 후행 이동평균을 뺀 것)
"""
import json
import numpy as np
from lab import forms, loop as L
from lab.harness import evaluate

CLS = forms.REGISTRY["F18_bagboost"]["cls"]
SEEDS = 12


def arm(axes):
    def mk():
        e = {**L._trendsub(zero_is_data=True), **L._calsub(), **L._wikisub(),
             **L._tag(), **L._fund(), **L._rawsub(), **L._grp(), **L._gen()}
        if axes:
            from lab.natsaxes import build as nb
            w = nb(axes=axes)
            if not w:
                raise SystemExit(f"{axes} 축이 비었다")
            e.update(w)
        return e
    return L._idol(mk, mode="cut", with_wiki=True, with_trend=True,
                   wide_post=True, wide_pop="grades")


def check(data, axes):
    out = {}
    for dom, (A, M, _y, _t) in data.dom.items():
        nm = data.names.get(dom, [])
        for w in axes:
            if w in nm:
                j = nm.index(w)
                out.setdefault(w, {})[dom] = int((M[:, j] > 0).sum())
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


b0, p0 = per_seed(arm(None))
print(json.dumps({"없이 판": round(float(b0.mean()), 4)}, ensure_ascii=False), flush=True)
out = {}
for lbl, axes in (("nat_mom", ("nat_mom",)), ("nat_dev", ("nat_dev",))):
    d = arm(axes)
    ch = check(d, axes)
    print(json.dumps({f"{lbl} 붙었나": ch}, ensure_ascii=False), flush=True)
    b1, p1 = per_seed(d)
    diff = b1 - b0
    out[lbl] = {"없이": round(float(b0.mean()), 4), "있고": round(float(b1.mean()), 4),
                "차": round(float(diff.mean()), 4),
                "씨앗SE": round(float(diff.std(ddof=1) / np.sqrt(len(diff))), 4),
                "양수": f"{int((diff > 0).sum())}/{len(diff)}"}
    dom = {}
    for k in sorted(set(p0) & set(p1)):
        if len(p0[k]) == len(p1[k]):
            dd = p1[k] - p0[k]
            dom[k] = round(float(dd.mean()), 4)
    out[lbl + "·도메인"] = dom
    print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)
print(json.dumps({"기준": "노트 646 의 nat_flow+nat_mom 2열 = −0.0211",
                  "문턱": 0.0045}, ensure_ascii=False), flush=True)
