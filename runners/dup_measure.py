"""겹말 축 하나를 뺀다 — 세 번째 관문을 챔피언에 거꾸로(노트 652).

스캔이 후보를 하나 냈다: `trend_level` ↔ `trend_volatility` 가 네 도메인에서
|r| ≥ 0.85(만화 +1.00 · 펀딩 +0.99 · 세계애니 +0.95 · 모바일 +0.93).
미리 정한 규칙대로 **라벨 상관이 작은 쪽**(volatility, 0.1267 대 0.1476)을 뺀다.

팔 둘. 열이 **줄어드는** 실험이라 위약은 뜻이 없다(뺄 값이 없다).
대신 **대조**를 둔다 — 겹말이 아닌 축을 같은 수만큼 빼면 얼마나 잃나.
그래야 '겹말이라 공짜' 인지 '아무 축이나 빼도 그만' 인지 갈린다.
"""
import json
import numpy as np
from lab import forms, loop as L
from lab.harness import evaluate

CLS = forms.REGISTRY["F18_bagboost"]["cls"]
SEEDS = 12


def arm(drop=None):
    def mk():
        e = {**L._trendsub(zero_is_data=True), **L._calsub(), **L._wikisub(),
             **L._tag(), **L._fund(), **L._rawsub(), **L._grp(), **L._gen()}
        if drop:
            e.pop(drop, None)
        return e
    return L._idol(mk, mode="cut", with_wiki=True, with_trend=True,
                   wide_post=True, wide_pop="grades")


def check(data, name):
    out = {}
    for dom, (A, M, _y, _t) in data.dom.items():
        nm = data.names.get(dom, [])
        out[dom] = ("있음" if name in nm else "없음")
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
print(json.dumps({"챔피언 판": round(float(b0.mean()), 4)}, ensure_ascii=False), flush=True)
out = {}
# 대조는 겹말이 아니면서 덮음이 비슷한 축 --- trend_peak_ratio
for lbl, drop in (("겹말뺌", "trend_volatility"), ("대조뺌", "trend_momentum")):
    d = arm(drop)
    print(json.dumps({f"{lbl}: {drop} 사라졌나": check(d, drop)}, ensure_ascii=False), flush=True)
    b1, p1 = per_seed(d)
    diff = b1 - b0
    out[lbl] = {"뺀 축": drop, "판": round(float(b1.mean()), 4),
                "차": round(float(diff.mean()), 4),
                "씨앗SE": round(float(diff.std(ddof=1) / np.sqrt(len(diff))), 4),
                "양수": f"{int((diff > 0).sum())}/{len(diff)}"}
    out[lbl + "·도메인"] = {k: round(float((p1[k] - p0[k]).mean()), 4)
                          for k in sorted(set(p0) & set(p1))
                          if len(p0[k]) == len(p1[k])}
    print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)
print(json.dumps({"문턱": 0.0045}, ensure_ascii=False), flush=True)
