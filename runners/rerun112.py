"""이슈 #112 — 정본 판 ρ 0.4710 을 씨앗 0~11 로 **내가 직접** 다시 잰다.

티처 #59 C1 이 잰 값과 대조한다. `runners/ff753.py` 는 **읽기만** 한다
(다른 에이전트가 만지는 중 · 씨앗만 12로 바꿔 같은 배선을 쓴다).

산출물: `runners/out112_board.json`
"""
import json
import sys
import time

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")

from lab.harness import evaluate
from runners import ff753 as FF

T = 2025.0
SEEDS = tuple(range(12))
OUT = "/Users/ax/world_model/runners/out112_board.json"


def main():
    t0 = time.time()
    d0 = FF.shell(FF.base())
    W = d0.weights(T)
    print(json.dumps({"유보 가중 합": int(sum(W.values())),
                      "도메인 수": len(W),
                      "도메인별 유보": {k: int(v) for k, v in sorted(W.items())}},
                     ensure_ascii=False), flush=True)

    vals, per = [], {}
    for s in SEEDS:
        sc = evaluate(lambda s=s: FF.CLS(seed=s), d0, T=T)
        v = float(d0.pooled(sc, T=T))
        vals.append(v)
        for k, x in sc.items():
            if np.isfinite(x):
                per.setdefault(k, []).append(float(x))
        print(f"  씨앗 {s}: {v!r}  ({time.time()-t0:.0f}s)", flush=True)

    a = np.array(vals, float)
    res = {
        "누가": "이슈 #112 수리 담당이 직접 실행",
        "배선": "runners/ff753.base()+shell() · F18_bagboost · lab.harness.evaluate · Data.pooled",
        "씨앗": list(SEEDS),
        "씨앗별 판(전정밀)": vals,
        "씨앗별 판(5자리)": [round(v, 5) for v in vals],
        "평균": float(a.mean()),
        "SD(ddof=1)": float(a.std(ddof=1)),
        "SE": float(a.std(ddof=1) / np.sqrt(len(a))),
        "유보 가중 합": int(sum(W.values())),
        "도메인 수": len(W),
        "도메인별 유보": {k: int(v) for k, v in sorted(W.items())},
        "도메인별 ρ(씨앗 평균)": {k: float(np.mean(v)) for k, v in sorted(per.items())},
        "씨앗0 단독": vals[0],
        "씨앗0~5 평균": float(a[:6].mean()),
        "초": round(time.time() - t0, 1),
    }
    print("=== 모아서 ===", flush=True)
    print(json.dumps(res, ensure_ascii=False, indent=1), flush=True)
    json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)
    print("완료", flush=True)


if __name__ == "__main__":
    main()
