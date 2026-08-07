"""날씨 축 만들기 — 좌표 내려받기 → 격자 기상 → 축 + 덮음 보고."""
import json
import sys

from ingest import weather as W

# ① 좌표 (BQ SELECT 만)
if not W.GEO.exists():
    W.pull_geo()
g = W.geo()
print(json.dumps({"단계": "좌표", "spot": len(g),
                  "격자": len({W.gridkey(*v) for v in g.values()})},
                 ensure_ascii=False), flush=True)

# ② 격자별 일별 시계열
W.pull_all(sleep=0.6)

# ③ 축 — 등급을 챔피언(wide_pop="grades") 과 맞춘 뒤에 만든다.
#    노트 359 의 갈라진 거름망을 그대로 밟지 않으려면 순서가 중요하다.
from lab import trendaxes as ta          # noqa: E402
ta.set_wide(False)
ta.set_grades(("A", "B", "C", "D", "E"))

from lab import weatheraxes as wx        # noqa: E402
ax = wx.build(report=True)
print(json.dumps({"단계": "축", "만든 축": list(ax)}, ensure_ascii=False), flush=True)

# ④ 기존 축과 얼마나 다른 것을 재나 — 이게 노트 638 의 부수 목적이다.
if ax:
    import numpy as np
    from scipy.stats import spearmanr
    from lab import calaxes, loop as L
    cal = L._calsub()
    others = {}
    for nm, byd in list(cal.items()) + list(L._trendsub(zero_is_data=True).items()) \
            + list(L._wikisub().items()):
        if "팝업" in byd:
            others[nm] = byd["팝업"]
    rows = []
    for a, byd in ax.items():
        v, m = byd["팝업"]
        for b, (v2, m2) in others.items():
            both = (m > 0) & (m2 > 0)
            if both.sum() < 25:
                continue
            r = spearmanr(v[both], v2[both]).statistic
            if np.isfinite(r):
                rows.append((a, b, round(float(r), 3), int(both.sum())))
    rows.sort(key=lambda x: -abs(x[2]))
    print(json.dumps({"단계": "겹침", "견준 짝": len(rows), "상위": rows[:12],
                      "|r|>0.5": [x for x in rows if abs(x[2]) > 0.5][:12]},
                     ensure_ascii=False), flush=True)
    # 날씨 축끼리도 본다 --- 겹말 가드는 새 축 사이에도 건다(노트 276)
    inner = []
    names = list(ax)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            (v1, m1), (v2, m2) = ax[names[i]]["팝업"], ax[names[j]]["팝업"]
            b = (m1 > 0) & (m2 > 0)
            if b.sum() >= 25:
                inner.append((names[i], names[j],
                              round(float(spearmanr(v1[b], v2[b]).statistic), 3),
                              int(b.sum())))
    print(json.dumps({"단계": "날씨 축끼리", "짝": inner}, ensure_ascii=False),
          flush=True)
