"""빈 열 하나의 값 — 열값이 어디서 오나(노트 663).

노트 662: 신호 몫 +0.0064 > 문턱, 그런데 순효과 +0.0016. 열값 −0.0048 이
신호의 3/4 를 먹는다. `_idol` 은 추가 축을 **열한 도메인 전부**에 붙이므로
자료가 둘에만 있는 축은 **아홉 도메인이 빈 열을 받는다.**

팔 셋.
  없이 / 빈 열(어디에도 자료 없음) / 빈 열 둘(값이 행 수에 선형인가)
"""
import json
import numpy as np
from lab import forms, loop as L
from lab.harness import evaluate

CLS = forms.REGISTRY["F18_bagboost"]["cls"]
SEEDS = 12


def arm(n_null=0):
    def mk():
        e = {**L._trendsub(zero_is_data=True), **L._calsub(), **L._wikisub(),
             **L._tag(), **L._fund(), **L._rawsub(), **L._grp(), **L._gen()}
        # **빈 열**: 어느 도메인에도 자료를 주지 않는다. `_idol` 이 모든 도메인에
        # 0.5·마스크 0 열을 붙이므로, 이름만 있으면 빈 열이 된다.
        for i in range(n_null):
            e[f"null_{i}"] = {}
        return e
    return L._idol(mk, mode="cut", with_wiki=True, with_trend=True,
                   wide_post=True, wide_pop="grades")


def check(data, n_null):
    """빈 열이 **정말 비었나** — 전 도메인 마스크 합이 0 이어야 한다."""
    out = {}
    for i in range(n_null):
        nm_ = f"null_{i}"
        tot, doms = 0, 0
        for dom, (A, M, _y, _t) in data.dom.items():
            nm = data.names.get(dom, [])
            if nm_ in nm:
                doms += 1
                tot += int((M[:, nm.index(nm_)] > 0).sum())
        out[nm_] = {"붙은 도메인": doms, "마스크>0 합": tot}
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


b0, p0 = per_seed(arm(0))
print(json.dumps({"없이 판": round(float(b0.mean()), 4)}, ensure_ascii=False), flush=True)
out = {}
for n in (1, 2):
    d = arm(n)
    print(json.dumps({f"빈 열 {n}개 배선": check(d, n)}, ensure_ascii=False), flush=True)
    b1, p1 = per_seed(d)
    diff = b1 - b0
    out[f"빈 열 {n}"] = {"판": round(float(b1.mean()), 4),
                       "차": round(float(diff.mean()), 4),
                       "씨앗SE": round(float(diff.std(ddof=1) / np.sqrt(len(diff))), 4),
                       "양수": f"{int((diff > 0).sum())}/{len(diff)}"}
    out[f"빈 열 {n}·도메인"] = {k: round(float((p1[k] - p0[k]).mean()), 4)
                             for k in sorted(set(p0) & set(p1))
                             if len(p0[k]) == len(p1[k])}
    print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)
print(json.dumps({"기준": "노트 662 위약 −0.0048 · 순효과 +0.0016",
                  "문턱": 0.0045}, ensure_ascii=False), flush=True)
