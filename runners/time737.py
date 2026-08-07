"""판 한 팔 적합에 얼마 드나 --- 팔 수를 정하려고 먼저 잰다."""
import sys, time, json
sys.path.insert(0, "/Users/ax/world_model")
import numpy as np
from lab import forms, loop as L
from lab.harness import evaluate

T = 2025.0
CLS = forms.REGISTRY["F18_bagboost"]["cls"]


def base():
    from lab import genaxes, grpaxes
    e = {**L._trendsub(zero_is_data=True), **L._calsub(), **L._wikisub(),
         **L._tag(), **L._fund(), **L._rawsub(), **genaxes.build()}
    e.update(grpaxes.build())
    return e


t0 = time.time()
d = L._idol(lambda: base(), mode="cut", with_wiki=True, with_trend=True,
            wide_post=True, wide_pop="grades")
t1 = time.time()
vals = []
for s in range(3):
    sc = evaluate(lambda s=s: CLS(seed=s), d, T=T)
    vals.append(float(d.pooled(sc, T=T)))
t2 = time.time()
print(json.dumps({"자료 짓기(초)": round(t1 - t0, 1),
                  "씨앗 3(초)": round(t2 - t1, 1),
                  "씨앗 1당(초)": round((t2 - t1) / 3, 1),
                  "씨앗 12 예상(초)": round((t2 - t1) / 3 * 12, 1),
                  "판(씨앗3)": round(float(np.mean(vals)), 4),
                  "도메인": len(d.dom)}, ensure_ascii=False))
