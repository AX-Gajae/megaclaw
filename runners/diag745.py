"""노트 745 — **축이 날짜 대리변수인가.** 판을 안 적합하므로 싸다.

노트 744 에서 축이 순효과 −0.0434 로 해로웠다. 가장 그럴듯한 원인은
**축의 백분위가 날짜 순위와 거의 같아져서** 판이 그것을 시간 대리로 쓰고
유보(미래)에서 무너지는 것이다. 노트 646 이 경고한 *'수준이 아니라 편차'* 다.
"""
import json
import sys

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
from scipy.stats import rankdata, spearmanr

sys.path.insert(0, "/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad")
from field744 import spread_series
from lab import loop as L

T = 2025.0


def main():
    yrs, sd, days, ck = spread_series()
    # ① 원천 계열 자체에 추세가 있나
    r_t = spearmanr(yrs, sd)
    # 연도별 중앙값
    yint = np.floor(yrs).astype(int)
    byyear = {int(y): round(float(np.median(sd[yint == y])), 5)
              for y in sorted(set(yint.tolist()))}
    d0 = L._idol(lambda: {}, mode="cut", with_wiki=True, with_trend=True,
                 wide_post=True, wide_pop="grades")
    rows = {}
    for dm in sorted(d0.dom):
        y = np.asarray(d0.yr[dm], float)
        ok = np.isfinite(y) & (y >= yrs[0]) & (y <= yrs[-1])
        if ok.sum() < 10:
            continue
        j = np.clip(np.searchsorted(yrs, y[ok]), 0, len(sd) - 1)
        v = sd[j]
        pct = rankdata(v) / ok.sum()
        r = spearmanr(y[ok], pct)
        rows[dm] = {"관측": int(ok.sum()),
                    "**축 ↔ 날짜 스피어만**": round(float(r.statistic), 3),
                    "p": round(float(r.pvalue), 5),
                    "고유값": int(len(np.unique(v)))}
    ab = [abs(v["**축 ↔ 날짜 스피어만**"]) for v in rows.values()]
    print(json.dumps({
        "**원천 계열 ↔ 날짜 스피어만**": round(float(r_t.statistic), 3),
        "p": round(float(r_t.pvalue), 6),
        "연도별 SD 중앙값": byyear,
        "도메인별 축↔날짜": dict(sorted(rows.items(),
                                key=lambda x: -abs(x[1]["**축 ↔ 날짜 스피어만**"]))),
        "**|축↔날짜| 중앙값**": round(float(np.median(ab)), 3),
        "판정": ("날짜 대리변수다 --- |상관| 중앙값이 0.5 넘는다"
               if np.median(ab) > 0.5 else
               "날짜 대리변수가 아니다 --- 다른 원인을 찾아야 한다"),
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
