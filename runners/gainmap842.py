# 노트 842 — 합동 이득 지도의 제3 변수 (사전등록 '842' · 841 기계 재사용)
import json, sys, time
import numpy as np
from scipy.stats import spearmanr, rankdata
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold
sys.path.insert(0, "/Users/ax/world_model")
from lab import sideaudit, guards as G
from lab.forms import REGISTRY

t0 = time.time()
NPERM = 6
data = sideaudit.champion_data()
cls = REGISTRY["F18_bagboost"]["cls"]
f = G._fit_on(lambda: cls(seed=0), data, 2025.0)
L = len(f.order)
print(f"적합 {time.time()-t0:.0f}s", flush=True)

# 841 과 동일한 상관 무리
tr_rows = []
for d in data.dom:
    yr = np.asarray(data.yr[d], float)
    y = np.asarray(data.dom[d][2], float)
    k = np.isfinite(yr) & (yr < 2025.0) & np.isfinite(y)
    A, M, _, tt = data.slice(d, k)
    tr_rows.append(f._design(d, A, M, tt)[:, :2 * L:2])
V = np.vstack(tr_rows)
corr = np.abs(spearmanr(V).statistic)
np.fill_diagonal(corr, 0)
parent = list(range(L))
def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]; i = parent[i]
    return i
for i in range(L):
    for j in range(i + 1, L):
        if corr[i, j] >= 0.5:
            parent[find(i)] = find(j)
groups = {}
for i in range(L):
    groups.setdefault(find(i), []).append(i)
GROUPS = [sorted(g) for g in groups.values()]
gi_venue = next(i for i, g in enumerate(GROUPS) if f.order.index("venue_prominence") in g)
gi_tb = next(i for i, g in enumerate(GROUPS) if f.order.index("target_breadth") in g)
n_season = 2 if getattr(f, "SEASON", False) else 0
n_spec = 2 if getattr(f, "SPEC", False) else 0
blocks = [[c for i in g for c in (2 * i, 2 * i + 1)] for g in GROUPS]
p = 2 * L
if n_season:
    blocks.append([p, p + 1]); p += 2
if n_spec:
    blocks.append([p, p + 1]); p += 2
NBT = len(blocks)

def rho(a, b):
    return float(spearmanr(a, b)[0])

def imp_vector(X0, y, seed):
    r2 = np.random.default_rng(seed)
    n = len(y)
    acc0 = np.zeros(n)
    for m in f.ms:
        acc0 += rankdata(m.predict(X0))
    base = rho(acc0, y)
    big = np.tile(X0, (NBT * NPERM, 1))
    for bi, cols in enumerate(blocks):
        for k in range(NPERM):
            off = (bi * NPERM + k) * n
            pi = r2.permutation(n)
            for c in cols:
                big[off:off + n, c] = X0[pi, c]
    acc = np.zeros((NBT * NPERM, n))
    for m in f.ms:
        raw = m.predict(big)
        for c in range(NBT * NPERM):
            acc[c] += rankdata(raw[c * n:(c + 1) * n])
    v = np.zeros(NBT)
    for bi in range(NBT):
        v[bi] = base - float(np.mean([rho(acc[bi * NPERM + k], y) for k in range(NPERM)]))
    return base, v

DELTA828 = {"게임": 0.1957, "도서": 0.3012, "만화": -0.0071, "모바일": -0.0085,
            "세계애니": 0.1241, "시장팝업": 0.0347, "아이돌": -0.0663,
            "애니": 0.1444, "웹툰": 0.0218, "펀딩": 0.2291}

shares_v, shares_t, nrows, deltas = {}, {}, {}, {}
mv_ridge = None
for d in sorted(data.dom):
    yr = np.asarray(data.yr[d], float)
    y_all = np.asarray(data.dom[d][2], float)
    ktr = np.isfinite(yr) & (yr < 2025.0) & np.isfinite(y_all)
    kho = np.isfinite(yr) & (yr >= 2025.0) & np.isfinite(y_all)
    if kho.sum() < 20:
        continue
    A, M, yv, tv = data.slice(d, kho)
    ok = np.isfinite(yv)
    A, M, yv, tv = A[ok], M[ok], yv[ok], tv[ok]
    X0 = f._design(d, A, M, tv)
    base, v = imp_vector(X0, yv, sum(map(ord, d)))
    tot = float(v @ v) or 1.0
    shares_v[d] = float(v[gi_venue] ** 2 / tot)
    shares_t[d] = float(v[gi_tb] ** 2 / tot)
    nrows[d] = int(len(yv))
    if d in DELTA828:
        deltas[d] = DELTA828[d]
    elif d == "영화":
        Atr, Mtr, ytr, ttr = data.slice(d, ktr)
        okr = np.isfinite(ytr)
        Xtr = np.nan_to_num(np.hstack([Atr, Mtr, np.asarray(ttr, float)[:, None]]), nan=0.5)[okr]
        Xho = np.nan_to_num(np.hstack([A, M, np.asarray(tv, float)[:, None]]), nan=0.5)
        best_a, best_s = None, -9
        for a in (0.1, 1.0, 10.0, 100.0, 1000.0):
            ss = []
            for tr, te in KFold(5, shuffle=True, random_state=1).split(Xtr):
                m = Ridge(alpha=a).fit(Xtr[tr], ytr[okr][tr])
                ss.append(rho(m.predict(Xtr[te]), ytr[okr][te]))
            s = float(np.nanmean(ss))
            if s > best_s:
                best_a, best_s = a, s
        p_r = Ridge(alpha=best_a).fit(Xtr, ytr[okr]).predict(Xho)
        mv_ridge = rho(p_r, yv)
        deltas[d] = base - mv_ridge
    print(f"  {d}: venue몫 {shares_v[d]:.3f} · t_b몫 {shares_t[d]:.3f} · Δ {deltas.get(d)} ({time.time()-t0:.0f}s)", flush=True)

doms = sorted(deltas)
n = len(doms)
y_ = [deltas[d] for d in doms]
cands = {"venue 몫": [shares_v[d] for d in doms],
         "t_b 몫": [shares_t[d] for d in doms],
         "log 유보행": [float(np.log(nrows[d])) for d in doms]}
rs = {k: round(float(spearmanr(x, y_)[0]), 3) for k, x in cands.items()}
OUT = {"n": n, "영화": {"챔피언": round([v for d, v in deltas.items() if d == '영화'][0] + (mv_ridge or 0), 4) if mv_ridge else None,
                        "릿지": round(mv_ridge, 4) if mv_ridge else None,
                        "Δ": round(deltas.get("영화", float('nan')), 4)},
       "표": {d: {"Δ": round(deltas[d], 4), "venue몫": round(shares_v[d], 3),
                  "t_b몫": round(shares_t[d], 3), "유보": nrows[d]} for d in doms},
       "상관": rs}
big = {k: r for k, r in rs.items() if abs(r) >= 0.75}
if big:
    OUT["판정"] = f"2.좋 — {big}(채택 아님 · 확인 등록)"
else:
    OUT["판정"] = f"3.없 — 전부 |r|<0.75 {rs} → 지도 미설명으로 문패 종결(문패 6건 전량 완결)"
OUT["초"] = round(time.time() - t0, 1)
print(json.dumps({k: OUT[k] for k in ("n", "영화", "상관", "판정", "초")}, ensure_ascii=False, indent=1), flush=True)
json.dump(OUT, open("/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad/out842.json", "w"), ensure_ascii=False, indent=1)
