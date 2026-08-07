"""노트 670 — 합집합 대 갈래별평균. 학습 행만. **판을 안 돈다.**"""
import datetime, json
import numpy as np
from pathlib import Path
from scipy.stats import spearmanr
from lab import crowdaxes as C
from lab.guards import _drop_mode

WINS = (30, 90, 365)


def col_for(mode: str, win: int):
    """{도메인: (값, 관측, 갈래개수, 날짜)} — mode in {'합집합','평균'}."""
    rows = C._rows()
    pool = []
    for _dom, (ds, gs) in rows.items():
        for d, g in zip(ds, gs):
            if d is not None and g:
                pool.append((d, g))
    pool.sort(key=lambda x: x[0])
    pdates = np.array([x[0].toordinal() for x in pool])
    cum = {}
    if mode == "평균":
        for gn in {x for _d, gs in pool for x in gs}:
            c = np.zeros(len(pool) + 1, np.int32)
            for i, (_d, gs) in enumerate(pool):
                c[i + 1] = c[i] + (1 if gn in gs else 0)
            cum[gn] = c
    out = {}
    for dom, (ds, gs) in rows.items():
        n = len(ds)
        col = np.full(n, np.nan); ng = np.full(n, np.nan)
        for i, (d, g) in enumerate(zip(ds, gs)):
            if d is None or not g:
                continue
            ng[i] = len(g)
            hi = d.toordinal(); lo = hi - win
            j0, j1 = np.searchsorted(pdates, lo), np.searchsorted(pdates, hi)
            tot = j1 - j0
            if tot < C.MIN_TOT:
                continue
            if mode == "합집합":
                col[i] = sum(1 for k in range(j0, j1) if pool[k][1] & g) / tot
            else:
                sh = [(cum[x][j1] - cum[x][j0]) / tot for x in g if x in cum]
                if sh:
                    col[i] = float(np.mean(sh))
        out[dom] = (col, np.isfinite(col), ng, ds)
    return out


def labels_and_year():
    from lab import loop as L
    e = {**L._trendsub(zero_is_data=True), **L._calsub(), **L._wikisub(),
         **L._tag(), **L._fund(), **L._rawsub(), **L._grp(), **L._gen()}
    d = L._idol(lambda: e, mode="cut", with_wiki=True, with_trend=True,
                wide_post=True, wide_pop="grades")
    return d


def rep(mode):
    out = {}
    per = {w: col_for(mode, w) for w in WINS}
    data = labels_and_year()
    # ① 축 ↔ 갈래 개수
    cnt = {}
    for dom, (col, ok, ng, _ds) in per[90].items():
        k = ok & np.isfinite(ng)
        if k.sum() >= 30 and len(np.unique(ng[k])) >= 2:
            a, b = _drop_mode(col[k], ng[k])
            if a is not None and len(a) >= 30:
                cnt[dom] = round(abs(float(spearmanr(a, b).statistic)), 4)
    out["축↔갈래개수 |r|"] = cnt
    # ② 축 ↔ 라벨 (학습 행만) · 창별
    lab = {}
    for w in WINS:
        num = den = 0.0
        for dom, (col, ok, _ng, _ds) in per[w].items():
            if dom not in data.dom:
                continue
            y = data.dom[dom][2]
            yr = data.yr[dom]
            m = min(len(col), len(y), len(yr))
            k = ok[:m] & np.isfinite(y[:m]) & np.isfinite(yr[:m]) & (yr[:m] < 2025.0)
            if k.sum() < 30 or len(np.unique(col[:m][k])) < 3:
                continue
            r = abs(float(spearmanr(col[:m][k], y[:m][k]).statistic))
            num += r * k.sum(); den += k.sum()
        lab[w] = round(num / den, 4) if den else None
    v = [x for x in lab.values() if x]
    out["축↔라벨 |r| (학습, 가중)"] = lab
    out["창 최대/최소"] = round(max(v) / min(v), 3) if v else None
    # ③ 창 30 ↔ 365 자기상관
    ac = {}
    for dom in per[30]:
        a, oa, _n, _d = per[30][dom]; b, ob, _n2, _d2 = per[365][dom]
        k = oa & ob
        if k.sum() >= 30 and len(np.unique(a[k])) >= 3:
            ac[dom] = round(float(spearmanr(a[k], b[k]).statistic), 4)
    out["창30↔365 자기상관"] = ac
    return out


res = {}
for mode in ("합집합", "평균"):
    res[mode] = rep(mode)
    print(json.dumps({mode: res[mode]}, ensure_ascii=False, indent=1), flush=True)
Path('/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad/crowd670.json').write_text(
    json.dumps(res, ensure_ascii=False, indent=1))
