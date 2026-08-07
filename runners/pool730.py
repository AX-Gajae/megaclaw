"""노트 730 — **풀 크기만 잰다.** 논문 144 의 중심 주장(풀 축소 비용)이 정확한
행수를 요구한다. 판을 적합하지 않으므로 싸다 --- 껍데기 한 번 + 순위만.
"""
import json
import sys

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
from scipy.stats import rankdata

from lab import loop as L, textnn as NN

T = 2025.0
#: 노트 729 가 고른 소스(그 노트에 적힌 수와 맞아야 한다)
PICKS = {"세계애니": 8, "애니": 7, "모바일": 6, "펀딩": 6, "게임": 5, "만화": 4,
         "시장팝업": 4, "웹툰": 3, "도서": 1, "아이돌": 1, "팝업": 1}


def main():
    from lab import genaxes, grpaxes

    def ex():
        e = {**L._trendsub(zero_is_data=True), **L._calsub(), **L._wikisub(),
             **L._tag(), **L._fund(), **L._rawsub(), **genaxes.build()}
        e.update(grpaxes.build())
        return e
    data = L._idol(lambda: ex(), mode="cut", with_wiki=True, with_trend=True,
                   wide_post=True, wide_pop="grades")
    txt, dom, y, is_tr, is_te, idx = NN._pool(data, T)
    doms = sorted(set(dom.tolist()))
    rk = np.full(len(y), np.nan)
    for d in doms:
        m = is_tr & (dom == d)
        if m.sum() >= 2:
            rk[m] = rankdata(y[m]) / m.sum()
    fit = is_tr & np.isfinite(rk)
    per = {d: int((fit & (dom == d)).sum()) for d in doms}
    tot = int(fit.sum())
    W = data.weights(T)
    print(json.dumps({
        "**한 통 학습행**": tot,
        "도메인별 학습행": dict(sorted(per.items(), key=lambda x: -x[1])),
        "유보 채점": {d: W.get(d, 0) for d in doms},
        "**자기만 고른 셋의 풀**": {d: per[d] for d in ("도서", "아이돌", "팝업")},
        "**풀 축소 배수(전부/자기)**": {
            d: round(tot / max(per[d], 1), 1) for d in ("도서", "아이돌", "팝업")},
        "**그때 잡음 배수(√)**": {
            d: round(float(np.sqrt(tot / max(per[d], 1))), 1)
            for d in ("도서", "아이돌", "팝업")},
        "노트 729 고른 소스 수": PICKS,
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
