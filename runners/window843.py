# 노트 843 — 릿지 적응 곡선 n† (사전등록 후 측정 · 전이 기준선은 833 재사용)
# (세션 heredoc 실행분의 재구성 — 출력 out843.json · 5.1초)
import json, sys, time
import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold
sys.path.insert(0, "/Users/ax/world_model")
import ff753 as FF          # 스크래치 모듈(runners/ff753.py 로 보존)
from lab import pairs as PR

t0 = time.time()
def rho(p, yy):
    ok = np.isfinite(p) & np.isfinite(yy)
    return float(spearmanr(p[ok], yy[ok])[0])

data = FF.shell(FF.base())
BASE = {"KR 만화": 0.2969, "비게임 앱": 0.3081}   # 833 앙상블 전이(같은 평가 행)
NS = (5, 10, 20, 50, 100, 200, 400, 800)
OUT = {}
for pair, datefield, n_ev in (("KR 만화", "start_date", 322), ("비게임 앱", "release_date", 189)):
    src = PR.SRC_DOM[pair]
    names = list(data.names.get(src) or [])
    recs = PR.build(pair)
    A, M, y, t = PR.to_arrays(recs, names)
    X = np.nan_to_num(np.hstack([A, M, np.asarray(t, float)[:, None]]), nan=0.5)
    fin = np.isfinite(y)
    years = np.array([int(str((r.get(datefield) or "0000"))[:4] or 0) for r in recs.values()])
    ev = np.flatnonzero(fin & (years >= 2025))
    pool = np.flatnonzero(fin & (years < 2025) & (years > 0))
    assert len(ev) == n_ev, f"{pair} 배선 {len(ev)}"
    curve = {}
    for n in NS:
        vals = []
        for d in range(4):
            r2 = np.random.default_rng(8430 + 10 * n + d)
            pick = r2.choice(pool, size=min(n, len(pool)), replace=False)
            if n >= 25:      # 🔴 α CV 는 n>=25 부터 — 그 아래는 고정 α=1 폴백.
                best_a, best_s = 1.0, -9   # 곡선이 두 하이퍼 체제를 섞는다(티처 #10 추측 적중 — 경계 25)
                for a in (0.1, 1.0, 10.0, 100.0):
                    ss = []
                    for tr, te in KFold(min(5, n), shuffle=True, random_state=d).split(pick):
                        m = Ridge(alpha=a).fit(X[pick[tr]], y[pick[tr]])
                        ss.append(rho(m.predict(X[pick[te]]), y[pick[te]]))
                    s = float(np.nanmean(ss))
                    if s > best_s:
                        best_a, best_s = a, s
            else:
                best_a = 1.0
            m = Ridge(alpha=best_a).fit(X[pick], y[pick])
            vals.append(rho(m.predict(X[ev]), y[ev]))
        a_ = np.array(vals, float)
        curve[n] = {"평균": round(float(np.nanmean(a_)), 4), "SD": round(float(np.nanstd(a_, ddof=1)), 4)}
    tgt = BASE[pair]
    nstar = next((n for n in NS if curve[n]["평균"] >= tgt), None)
    OUT[pair] = {"평가": n_ev, "전이(833)": tgt, "곡선": curve, "n†": nstar}
print(json.dumps(OUT, ensure_ascii=False, indent=1))
