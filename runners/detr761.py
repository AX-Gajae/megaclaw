"""노트 761 준비 — **처방이 겹침을 회복하나.** 판 적합 없이 먼저 본다.

노트 760 이 원천 계열이 **U 자**(2023 최저 · 2026 최고)라 학습·유보 백분위가
겹침 0.074 로 갈리는 것을 쟀다. 처방 후보 둘을 **겹침으로만** 견준다:
  ① **직전 365일 중앙값을 뺀 편차**(추세를 지운다 · 그 시점 과거만 쓴다)
  ② 창 안 백분위(학습은 학습 안 · 유보는 유보 안) --- 구성상 맞지만 전이적이다
"""
import json
import sys

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad")
from scipy.stats import rankdata

import ff753 as FF

T = 2025.0
WIN = 365


def overlap(pct, tr, te):
    q1 = np.percentile(pct[tr], [25, 50, 75])
    q2 = np.percentile(pct[te], [25, 50, 75])
    lo, hi = max(q1[0], q2[0]), min(q1[2], q2[2])
    return (max(0.0, hi - lo) / max(q2[2] - q2[0], 1e-9),
            round(float(q2[1] - q1[1]), 3))


def main():
    yrs, sd, days, ck = FF.spread_series()
    # ── ① 직전 365일 중앙값을 뺀 편차. **그 시점 과거만** 쓴다.
    dev = np.full(len(sd), np.nan)
    for i in range(len(sd)):
        m = (yrs > yrs[i] - WIN / 365.0) & (yrs <= yrs[i])
        if m.sum() >= 60:
            dev[i] = sd[i] - float(np.median(sd[m]))
    ok0 = np.isfinite(dev)
    yint = np.floor(yrs).astype(int)
    d0 = FF.shell({})
    rep = {}
    for dm in sorted(d0.dom):
        y = np.asarray(d0.yr[dm], float)
        base = np.isfinite(y) & (y >= yrs[0])
        if base.sum() < 20:
            continue
        j = np.clip(np.searchsorted(yrs, y[base]), 0, len(sd) - 1)
        yy = y[base]
        tr, te = yy < T, yy >= T
        if tr.sum() < 10 or te.sum() < 10:
            continue
        row = {}
        # 원본(노트 753)
        p0 = rankdata(sd[j]) / base.sum()
        o0, d0m = overlap(p0, tr, te)
        row["원본 겹침"] = round(float(o0), 3)
        row["원본 유보중앙차"] = d0m
        # ① 편차
        v1 = dev[j]
        m1 = np.isfinite(v1)
        p1 = np.full(len(v1), np.nan)
        p1[m1] = rankdata(v1[m1]) / m1.sum()
        if (tr & m1).sum() >= 10 and (te & m1).sum() >= 10:
            o1, d1 = overlap(p1[m1], tr[m1], te[m1])
            row["**편차 겹침**"] = round(float(o1), 3)
            row["편차 유보중앙차"] = d1
            row["편차 관측"] = int(m1.sum())
        # ② 창 안 백분위
        p2 = np.zeros(len(yy))
        p2[tr] = rankdata(sd[j][tr]) / max(tr.sum(), 1)
        p2[te] = rankdata(sd[j][te]) / max(te.sum(), 1)
        o2, d2 = overlap(p2, tr, te)
        row["창안 겹침"] = round(float(o2), 3)
        row["창안 유보중앙차"] = d2
        rep[dm] = row
    def med(k):
        v = [r[k] for r in rep.values() if k in r]
        return round(float(np.median(v)), 3) if v else None
    print(json.dumps({
        "편차 계열": {"관측 날": int(ok0.sum()),
                  "연도별 중앙값": {int(y): round(float(np.median(dev[ok0 & (yint == y)])), 5)
                              for y in sorted(set(yint[ok0].tolist()))}},
        "도메인별": rep,
        "**겹침 중앙값**": {"원본": med("원본 겹침"), "**편차**": med("**편차 겹침**"),
                     "창안": med("창안 겹침")},
        "**유보중앙차 중앙값**": {"원본": med("원본 유보중앙차"),
                          "**편차**": med("편차 유보중앙차"),
                          "창안": med("창안 유보중앙차")},
        "판정": "편차 겹침 중앙값이 0.5 넘으면 처방으로 쓸 수 있다",
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
