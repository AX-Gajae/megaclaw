# 노트 826 — 아이돌 라우팅 확인 (사전등록: 대장 '사전등록 826' · 커밋 후 측정)
import json, sys, time
import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold

sys.path.insert(0, "/Users/ax/world_model")
from lab import sideaudit, guards as G
from lab.forms import REGISTRY

t0 = time.time()
D = "아이돌"

def rho(p, yy):
    ok = np.isfinite(p) & np.isfinite(yy)
    return float(spearmanr(p[ok], yy[ok])[0])

data = sideaudit.champion_data()
cls = REGISTRY["F18_bagboost"]["cls"]
yr = np.asarray(data.yr[D], float)
y_all = np.asarray(data.dom[D][2], float)
ktr = np.isfinite(yr) & (yr < 2025.0) & np.isfinite(y_all)
kho = np.isfinite(yr) & (yr >= 2025.0) & np.isfinite(y_all)
A, M, yv, tv = data.slice(D, kho)
Atr, Mtr, ytr, ttr = data.slice(D, ktr)
okr = np.isfinite(ytr)
n_ho = int(np.isfinite(yv).sum())
print(json.dumps({"배선": {"유보": n_ho, "학습": int(okr.sum())}}, ensure_ascii=False), flush=True)
assert n_ho == 51, "배선 — 유보 51 아님"

Xtr = np.nan_to_num(np.hstack([Atr, Mtr, np.asarray(ttr, float)[:, None]]), nan=0.5)[okr]
Xho = np.nan_to_num(np.hstack([A, M, np.asarray(tv, float)[:, None]]), nan=0.5)

def fit_ridge(rs):
    best_a, best_s = None, -9
    for a in (0.1, 1.0, 10.0, 100.0, 1000.0):
        ss = []
        for tr, te in KFold(5, shuffle=True, random_state=rs).split(Xtr):
            m = Ridge(alpha=a).fit(Xtr[tr], ytr[okr][tr])
            ss.append(rho(m.predict(Xtr[te]), ytr[okr][te]))
        s = float(np.nanmean(ss))
        if s > best_s:
            best_a, best_s = a, s
    return Ridge(alpha=best_a).fit(Xtr, ytr[okr]), best_a

mR, alpha = fit_ridge(rs=2)          # 822 는 rs=1 — 교체 재적합
p_ridge = mR.predict(Xho)
r_ridge = rho(p_ridge, yv)
plc = []
for d in range(6):
    r2 = np.random.default_rng(8260 + d)
    ysh = ytr[okr].copy(); r2.shuffle(ysh)
    plc.append(rho(Ridge(alpha=alpha).fit(Xtr, ysh).predict(Xho), yv))
print(json.dumps({"릿지": {"alpha": alpha, "ρ": round(r_ridge, 4),
    "위약 평균": round(float(np.mean(plc)), 4), "위약 최대": round(float(np.max(plc)), 4)}},
    ensure_ascii=False), flush=True)

deltas, joints, pj_list = [], [], []
for s in (1, 2, 3, 4):
    f = G._fit_on(lambda s=s: cls(seed=s), data, 2025.0, seed=s)
    pj = np.asarray(f.predict(D, A, M, tv), float)
    rj = rho(pj, yv)
    joints.append(rj); deltas.append(rj - r_ridge); pj_list.append(pj)
    print(f"  씨앗 {s}: 합동 {rj:+.4f} · Δ {rj - r_ridge:+.4f} ({time.time()-t0:.0f}s)", flush=True)

mean_d = float(np.mean(deltas))
all_neg = all(d < 0 for d in deltas)
SIG = 2 * 0.262 / np.sqrt(51)

# 병기 — 행 부트스트랩 1,000 (짝 설계: 같은 행에서 합동(씨앗 평균 순위)·릿지 채점)
pj_avg = np.mean([np.argsort(np.argsort(p)) for p in pj_list], axis=0)
rngb = np.random.default_rng(826)
bs = []
ok = np.isfinite(yv)
idx = np.flatnonzero(ok)
for _ in range(1000):
    pick = rngb.choice(idx, size=len(idx), replace=True)
    bs.append(rho(pj_avg[pick], yv[pick]) - rho(p_ridge[pick], yv[pick]))
lo, hi = np.percentile(bs, [2.5, 97.5])

OUT = {"배선": {"유보": n_ho}, "릿지": {"alpha": alpha, "ρ": round(r_ridge, 4),
        "위약 평균": round(float(np.mean(plc)), 4)},
       "합동(씨앗 1~4)": [round(x, 4) for x in joints],
       "Δ(씨앗별)": [round(x, 4) for x in deltas],
       "Δ 평균": round(mean_d, 4), "전부 음수": all_neg,
       "상수 2σ": round(SIG, 4),
       "부트스트랩 Δ 95%": [round(float(lo), 4), round(float(hi), 4)],
       "822 참조": {"Δ": -0.086, "합동(seed0)": 0.4421, "릿지(rs=1)": 0.5281}}
if float(np.mean(plc)) >= r_ridge:
    OUT["판정"] = "1.배선/위약"
elif all_neg and mean_d <= -SIG:
    OUT["판정"] = f"2.확인 — 라우팅 권고 발동 (Δ평균 {mean_d:+.4f} ≤ −{SIG:.4f} · 4/4 음수)"
else:
    OUT["판정"] = f"3.불확인 — 합동 유지 · 재측정 금지 3사이클 (Δ평균 {mean_d:+.4f} · 음수 {sum(d<0 for d in deltas)}/4)"
OUT["초"] = round(time.time() - t0, 1)
print(json.dumps(OUT, ensure_ascii=False, indent=1), flush=True)
json.dump(OUT, open("/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad/out826.json", "w"), ensure_ascii=False, indent=1)
