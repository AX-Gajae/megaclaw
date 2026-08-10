"""이슈 #112 — **837 이 쓴 적합 경로**(`guards._fit_on(..., seed=s)`)로 판을 다시 잰다.

🔴 이것이 원인 후보다. `rebase837.py:80-83` 은 `G._fit_on(lambda: cls(seed=s),
data, T, seed=s)` 를 부르는데, `lab/guards.py:69-75` 가 그때 **정식화의 `kw`
안 `random_state` 까지 s 로 갈아 끼운다**:

    if isinstance(kw, dict) and "random_state" in kw:
        f.kw = {**kw, "random_state": seed}

`BagBoost` 는 `Boost.__init__` 에서 `random_state=0` 을 **고정**으로 갖는다
(`lab/forms.py:287`). 챔피언 채점 경로(`harness.evaluate`)는 `make()` 만 부르므로
**`random_state` 가 언제나 0** 이고 씨앗은 `BagBoost` 자체 뽑기에만 든다.
n≈22,000 이라 `HistGradientBoostingRegressor` 의 조기중단이 켜지고 그 검증 분할이
`random_state` 를 쓴다 --- 그래서 **두 경로는 씨앗 0 에서만 같고 s>=1 에서 갈린다.**

여기서는 오늘 자료·오늘 코드로 **837 경로**를 그대로 돌린다. 평균이 0.4710 으로
가면 원인이 특정된 것이다.

산출물: `runners/out112_refit837.json`
"""
import json
import sys
import time

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, "/Users/ax/world_model")

from lab import guards as G
from runners import ff753 as FF

T = 2025.0
SEEDS = tuple(range(12))
OUT = "/Users/ax/world_model/runners/out112_refit837.json"


def score(f, data, doms):
    """rebase837.py:60-74 를 글자 그대로."""
    out = {}
    for d in doms:
        yrv = np.asarray(data.yr[d], float)
        yv_all = np.asarray(data.dom[d][2], float)
        kho = np.isfinite(yrv) & (yrv >= T) & np.isfinite(yv_all)
        if kho.sum() < 20:
            continue
        Ah, Mh, yh, th = data.slice(d, kho)
        p = np.asarray(f.predict(d, Ah, Mh, th), float)
        ok = np.isfinite(p) & np.isfinite(yh)
        out[d] = float(spearmanr(p[ok], yh[ok])[0])
    return out


def main():
    t0 = time.time()
    d0 = FF.shell(FF.base())
    doms = list(d0.dom)
    W = d0.weights(T)
    print(json.dumps({"유보 가중 합": int(sum(W.values()))}, ensure_ascii=False),
          flush=True)

    vals, per = [], {}
    for s in SEEDS:
        f = G._fit_on(lambda s=s: FF.CLS(seed=s), d0, T, seed=s)
        sc = score(f, d0, doms)
        v = float(np.average([sc[d] for d in sc],
                             weights=[W[d] for d in sc]))
        vals.append(v)
        for k, x in sc.items():
            if np.isfinite(x):
                per.setdefault(k, []).append(float(x))
        print(f"  씨앗 {s}: {v!r}  (random_state={s}) ({time.time()-t0:.0f}s)",
              flush=True)

    a = np.array(vals, float)
    res = {"무엇": "837 적합 경로(guards._fit_on(seed=s) → kw['random_state']=s)",
           "씨앗별 판(전정밀)": vals,
           "평균": float(a.mean()),
           "SD(ddof=1)": float(a.std(ddof=1)),
           "SE": float(a.std(ddof=1) / np.sqrt(len(a))),
           "837 인쇄값": 0.4710,
           "도메인별 ρ(씨앗 평균)": {k: float(np.mean(v)) for k, v in sorted(per.items())},
           "유보 가중 합": int(sum(W.values())),
           "초": round(time.time() - t0, 1)}
    print("=== 모아서 ===", flush=True)
    print(json.dumps(res, ensure_ascii=False, indent=1), flush=True)
    json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)
    print("완료", flush=True)


if __name__ == "__main__":
    main()
