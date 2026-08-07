# 노트 833 — 집 밖 짝 릿지 격차의 자 교체 (사전등록 후 측정)
import json, sys, time
import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad")
import ff753 as FF
from lab import pairs as PR, guards as G, pairboot as PB
from lab.forms import REGISTRY

t0 = time.time()
def rho(p, yy):
    ok = np.isfinite(p) & np.isfinite(yy)
    return float(spearmanr(p[ok], yy[ok])[0])

data = FF.shell(FF.base())
CLS = REGISTRY["F18_bagboost"]["cls"]
fits = [G._fit_on(lambda s=s: CLS(seed=s), data, 2025.0, seed=s) for s in (4, 5, 6, 7)]
print(f"적합 4회 {time.time()-t0:.0f}s", flush=True)

OUT = {}
for pair, datefield, n_ev_expect in (("KR 만화", "start_date", 322), ("비게임 앱", "release_date", 189)):
    src = PR.SRC_DOM[pair]
    names = list(data.names.get(src) or [])
    recs = PR.build(pair)
    A, M, y, t = PR.to_arrays(recs, names)
    X = np.nan_to_num(np.hstack([A, M, np.asarray(t, float)[:, None]]), nan=0.5)
    fin = np.isfinite(y)
    years = np.array([int(str((r.get(datefield) or "0000"))[:4] or 0) for r in recs.values()])
    ev = np.flatnonzero(fin & (years >= 2025))
    pool = np.flatnonzero(fin & (years < 2025) & (years > 0))
    assert len(ev) == n_ev_expect, f"{pair} 배선 — 평가 {len(ev)}"
    # 전이(씨앗 4~7 순위평균 앙상블)
    pj = [np.asarray(f.predict(src, A[ev], M[ev], np.asarray(t, float)[ev]), float) for f in fits]
    ens = PB.rank_ensemble(pj)
    # 릿지(821/822 설정)
    best_a, best_s = None, -9
    for a in (0.1, 1.0, 10.0, 100.0, 1000.0):
        ss = []
        for tr, te in KFold(5, shuffle=True, random_state=0).split(pool):
            m = Ridge(alpha=a).fit(X[pool[tr]], y[pool[tr]])
            ss.append(rho(m.predict(X[pool[te]]), y[pool[te]]))
        s = float(np.nanmean(ss))
        if s > best_s:
            best_a, best_s = a, s
    p_r = Ridge(alpha=best_a).fit(X[pool], y[pool]).predict(X[ev])
    titles = [r.get("title") for r in recs.values()]
    tl_ev = [titles[i] for i in ev]
    cl, wire = PB.clusters_of(tl_ev)
    yv = y[ev]
    def stat(idx, p_r=p_r, ens=ens, yv=yv):
        return rho(p_r[idx], yv[idx]) - rho(ens[idx], yv[idx])
    th, lo, hi, kind = PB.cluster_boot(stat, cl, seed=833)
    OUT[pair] = {"n": int(len(ev)), "군집": wire, "alpha": best_a,
                 "릿지": round(rho(p_r, yv), 4), "전이(앙상블)": round(rho(ens, yv), 4),
                 "Δ(릿지-전이)": round(th, 4), "CI95": [round(lo, 4), round(hi, 4)],
                 "종류": kind,
                 "판정": {"승": "릿지승", "패": "전이승"}.get(PB.verdict(lo, hi), "판정 불능")}
    print(json.dumps({pair: OUT[pair]}, ensure_ascii=False), flush=True)

kr, app = OUT["KR 만화"]["판정"], OUT["비게임 앱"]["판정"]
if kr == "릿지승" and app == "릿지승":
    OUT["갈래"] = "2.확정 유지"
elif app == "릿지승" and kr == "판정 불능":
    OUT["갈래"] = "3.부분 — 앱 확정 · KR 판정 불능(방향 일치·크기 미확정)"
elif app == "판정 불능":
    OUT["갈래"] = "4.재고"
else:
    OUT["갈래"] = f"그 외({kr}/{app})"
OUT["초"] = round(time.time() - t0, 1)
print(json.dumps({"갈래": OUT["갈래"], "초": OUT["초"]}, ensure_ascii=False), flush=True)
json.dump(OUT, open("/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad/out833.json", "w"), ensure_ascii=False, indent=1)
