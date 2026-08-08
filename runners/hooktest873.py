# -*- coding: utf-8 -*-
# 훅 무영향 시험 정본(노트 873 · 티처 #38 중대 2 — out872 는 자기서술 불능·스크립트 미커밋).
# 논거의 순서(티처 #38 이의 1): **훅은 print 전용이라 적합 개입 경로가 없다(코드 성질)가 주 논거**,
# 이 스모크(씨앗 0·챔피언 구성·KR 만화 평가 322 예측 배열의 sha256)는 방증이다.
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/Users/ax/world_model/runners")

ROOT = Path("/Users/ax/world_model")


def one_fit(hook_on: bool) -> str:
    os.environ["ERA_HOOK"] = "1" if hook_on else "0"
    import ff753 as FF
    from lab import pairs as PR, guards as G
    from lab.forms import REGISTRY
    data = FF.shell(FF.base())
    f = G._fit_on(lambda: REGISTRY["F18_bagboost"]["cls"](seed=0), data, 2025.0, seed=0)
    src = PR.SRC_DOM["KR 만화"]
    names = list(data.names.get(src) or [])
    recs = PR.build("KR 만화")
    A, M, y, t = PR.to_arrays(recs, names)
    fin = np.isfinite(y)
    years = np.array([int(str((r.get("start_date") or "0000"))[:4] or 0) for r in recs.values()])
    ev = np.flatnonzero(fin & (years >= 2025))
    p = np.asarray(f.predict(src, A[ev], M[ev], np.asarray(t, float)[ev]), float)
    return hashlib.sha256(p.tobytes()).hexdigest()[:16]


def main():
    t0 = time.time()
    h_on, h_off = one_fit(True), one_fit(False)
    out = {"자기서술": {"모형": "F18_bagboost(seed=0)", "구성": "ff753.shell(base()) — 챔피언 축",
                     "해시 대상": "KR 만화 평가 322행 예측 배열(sha256[:16])",
                     "논거": "주 = 훅 print 전용(코드 성질) · 이 스모크는 방증"},
           "훅 on": h_on, "훅 off": h_off, "비트 동일": h_on == h_off,
           "초": round(time.time() - t0, 1)}
    import datetime as dt
    with open(ROOT / f"runners/out_hooktest_{dt.date.today()}.json", "x") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
