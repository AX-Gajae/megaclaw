"""노트 744 준비 — **장 시간축의 덮음률을 먼저 잰다.** 판을 안 적합하므로 싸다.

장은 2,349일(약 2020~2026)이고 판 행은 1989년까지 간다. **덮음이 얇으면 판이
못 움직이고 그것은 신호 없음이 아니라 자료 없음이다** --- 재기 전에 가른다.
"""
import json
import sys

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
from lab import loop as L
from state import fieldmodel as F

T = 2025.0


def main():
    codes, days, X = F.field(stats_end=F.TRAIN_END)
    yrs = np.array([int(d[:4]) + (int(d[4:6]) - 1) / 12 + (int(d[6:]) - 1) / 365
                    for d in days])
    lo, hi = float(yrs.min()), float(yrs.max())
    d0 = L._idol(lambda: {}, mode="cut", with_wiki=True, with_trend=True,
                 wide_post=True, wide_pop="grades")
    W = d0.weights(T)
    rep = {}
    tot = cov = 0
    tr_tot = tr_cov = te_tot = te_cov = 0
    for dm in sorted(d0.dom):
        y = np.asarray(d0.yr[dm], float)
        ok = np.isfinite(y) & (y >= lo) & (y <= hi)
        tr = np.isfinite(y) & (y < T)
        te = np.isfinite(y) & (y >= T)
        rep[dm] = {"행": int(len(y)), "덮음": int(ok.sum()),
                   "덮음률": round(float(ok.mean()), 3),
                   "학습 덮음률": round(float((ok & tr).sum() / max(tr.sum(), 1)), 3),
                   "유보 덮음률": round(float((ok & te).sum() / max(te.sum(), 1)), 3),
                   "유보 채점": W.get(dm, 0)}
        tot += len(y); cov += int(ok.sum())
        tr_tot += int(tr.sum()); tr_cov += int((ok & tr).sum())
        te_tot += int(te.sum()); te_cov += int((ok & te).sum())
    print(json.dumps({
        "장 날짜 범위": {"첫": days[0], "끝": days[-1], "날 수": len(days),
                    "소수연도": [round(lo, 2), round(hi, 2)]},
        "동네": len(codes),
        "**전체 덮음률**": round(cov / tot, 3),
        "**학습 덮음률**": round(tr_cov / max(tr_tot, 1), 3),
        "**유보 덮음률**": round(te_cov / max(te_tot, 1), 3),
        "도메인별": dict(sorted(rep.items(), key=lambda x: -x[1]["덮음률"])),
        "판정": ("유보 덮음률이 0.8 넘으면 시간축으로 쓸 수 있다"
               if te_cov / max(te_tot, 1) > 0.8 else
               "유보 덮음이 얇다 --- 못 움직이면 자료 없음과 신호 없음이 안 갈린다"),
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
