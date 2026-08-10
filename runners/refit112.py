"""이슈 #112 — **837 이 쓴 적합 경로**(`guards._fit_on(..., seed=s)`)로 판을 다시 잰다.

🔴 **2026-08-10 정정(이슈 #117 · 티처 #60 C1 · 노트 898). 아래 문단의 원인 지목이 틀렸다.**
이 파일이 원래 적었던 것: *"`lab/guards.py:69-75` 가 `kw['random_state']` 를 s 로 갈아
끼우고 `BagBoost` 는 `random_state=0` 고정이라 두 경로는 씨앗 0 에서만 같다."*

**둘 다 틀렸다.**
① `lab/forms.py:702-703` 이 자루마다 `{**self.kw, "random_state": k}` 로 **자루 색인 k** 를
   덮으므로 `kw['random_state']` 는 GBM 에 **한 번도 안 닿는다**(898 실측: `kw=7` 로 주고
   자루를 찍으니 `[0,1,…,31]`). 조기중단 검증 분할도 자루 색인을 쓴다.
② 두 경로는 **씨앗 0 에서도 갈린다** --- 0.4724867181663707(챔피언) 대
   0.4738262345295442(837), Δ **+0.00133952** 로 12씨앗 중 **최대** 차이다.

**진짜 원인 둘**(씨앗 0 · 합이 비트 동일 · `runners/out898_wire.json`):
   ① 채점 배치(post 전체 대 post∩라벨)                       +0.00071993
   ② 스피어만 구현(`scipy` 동률 평균 대 `rank_test` 서수)     +0.00061958
아래 코드는 그대로 두 규약(kho 배치 + `scipy`)을 돌리므로 **측정 자체는 옳다.**
바뀐 것은 그 Δ 를 무엇 탓으로 돌리느냐다.

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
