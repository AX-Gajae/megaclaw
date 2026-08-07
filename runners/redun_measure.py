"""진짜 겹말 둘을 뺀다 — 순수 중복은 공짜인가(노트 654).

노트 652 에서 대조가 무효였던 것(뺀 축이 애초에 없었다)을 고쳐 적용한다 ---
**기준선 팔에 그 축이 있었나**를 먼저 찍고, 뺀 팔에서 사라졌나를 찍는다.
"""
import json
import numpy as np
from lab import forms, loop as L
from lab.harness import evaluate

CLS = forms.REGISTRY["F18_bagboost"]["cls"]
SEEDS = 12
TARGETS = ("fund_cat", "mob_nlang")


def arm(drop=None):
    def mk():
        e = {**L._trendsub(zero_is_data=True), **L._calsub(), **L._wikisub(),
             **L._tag(), **L._fund(), **L._rawsub(), **L._grp(), **L._gen()}
        if drop:
            if drop not in e:
                raise SystemExit(f"뺄 축이 추가 축에 없다: {drop}")
            e.pop(drop)
        return e
    return L._idol(mk, mode="cut", with_wiki=True, with_trend=True,
                   wide_post=True, wide_pop="grades")


def where(data, name):
    """그 축이 **어느 도메인에 마스크>0 으로** 있나 --- 이름만 보면 안 된다(노트 568)."""
    out = {}
    for dom, (A, M, _y, _t) in data.dom.items():
        nm = data.names.get(dom, [])
        if name in nm:
            j = nm.index(name)
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


base = arm(None)
print(json.dumps({"기준선에 있었나": {t: where(base, t) for t in TARGETS}},
                 ensure_ascii=False), flush=True)
b0, p0 = per_seed(base)
print(json.dumps({"챔피언 판": round(float(b0.mean()), 4)}, ensure_ascii=False), flush=True)

out = {}
for t in TARGETS:
    d = arm(t)
    left = where(d, t)
    print(json.dumps({f"{t} 뺀 뒤 남은 곳": left}, ensure_ascii=False), flush=True)
    if left:
        print(f"**{t}: 안 빠졌다 — 건너뛴다**", flush=True)
        continue
    b1, p1 = per_seed(d)
    diff = b1 - b0
    out[t] = {"판": round(float(b1.mean()), 4), "차": round(float(diff.mean()), 4),
              "씨앗SE": round(float(diff.std(ddof=1) / np.sqrt(len(diff))), 4),
              "양수": f"{int((diff > 0).sum())}/{len(diff)}"}
    out[t + "·도메인"] = {k: round(float((p1[k] - p0[k]).mean()), 4)
                        for k in sorted(set(p0) & set(p1))
                        if len(p0[k]) == len(p1[k])}
    print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)
print(json.dumps({"문턱": 0.0045}, ensure_ascii=False), flush=True)
