# -*- coding: utf-8 -*-
# 노트 854 — 이름 격자 × 릿지 대칭 재판정 (사전등록 '854')
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import rankdata, spearmanr
from sklearn.linear_model import Ridge

sys.path.insert(0, "/Users/ax/world_model")
from lab import guards as G, pairs as PR, sideaudit  # noqa: E402
from lab.forms import REGISTRY  # noqa: E402

t0 = time.time()
T = 2025.0
SEEDS = list(range(12))
ROOT = Path("/Users/ax/world_model")

data12 = sideaudit.champion_data()
DOMS = sorted(data12.dom)
cls = REGISTRY["F18_bagboost"]["cls"]

PAIRS = {"KR 만화": "start_date", "비게임 앱": "release_date", "CN 만화": "start_date"}
raw_pairs = {}
for pname, df in PAIRS.items():
    recs = PR.build(pname)
    years = np.array([int(str((r.get(df) or r.get("start_date") or r.get("release_date") or "0000"))[:4] or 0)
                      for r in recs.values()])
    raw_pairs[pname] = (recs, years)

# 무정체용 이름 등록(만화 이름 기준 — 열은 정체별 to_arrays 로 재구성하므로 임의)
for pname in PAIRS:
    data12.names[f"NL_{pname}"] = list(data12.names[PR.SRC_DOM[pname]])

fits = []
for s in SEEDS:
    fits.append(G._fit_on(lambda s=s: cls(seed=s), data12, T, seed=s))
    print(f"  씨앗 {s} ({time.time()-t0:.0f}s)", flush=True)

# ── ⓐ 이름 격자: 3짝 × (12도메인 + 무정체) ──────────────────────
grid = {}
hashes = {}
for pname, df in PAIRS.items():
    recs, years = raw_pairs[pname]
    grid[pname] = {}
    hashes[pname] = {}
    for ident in DOMS + [f"NL_{pname}"]:
        names_i = list(data12.names[ident if ident in DOMS else PR.SRC_DOM[pname]])
        A, M, y, t = PR.to_arrays(recs, names_i)
        A = np.asarray(A, float); M = np.asarray(M, float)
        y = np.asarray(y, float); t = np.asarray(t, float)
        fin = np.isfinite(y)
        ev = np.flatnonzero(fin & (years >= 2025))
        pe = np.nanmean([np.asarray(f.predict(ident, A[ev], M[ev], t[ev]), float) for f in fits], axis=0)
        ok = np.isfinite(pe) & np.isfinite(y[ev])
        lab = "무정체" if ident.startswith("NL_") else ident
        grid[pname][lab] = round(float(spearmanr(pe[ok], y[ev][ok])[0]), 4)
        hashes[pname][lab] = hashlib.sha256(rankdata(pe[ok]).tobytes()).hexdigest()[:12]
    print(f"격자 {pname}: {grid[pname]}", flush=True)

kr = grid["KR 만화"]
app = grid["비게임 앱"]
d_kr_mob = kr["무정체"] - kr["모바일"]
d_kr_man = kr["무정체"] - kr["만화"]
d_app_man = app["무정체"] - app["만화"]
same_hash_app = hashes["비게임 앱"]["무정체"] == hashes["비게임 앱"]["모바일"]

# ── ⓑ 릿지 대칭 재판정 ───────────────────────────────────────────
def build_xr(pname):
    recs, years = raw_pairs[pname]
    names = list(data12.names[PR.SRC_DOM[pname]])
    A, M, y, t = PR.to_arrays(recs, names)
    A = np.asarray(A, float); M = np.asarray(M, float)
    y = np.asarray(y, float); t = np.asarray(t, float)
    fin = np.isfinite(y)
    ev = np.flatnonzero(fin & (years >= 2025))
    pool = np.flatnonzero(fin & (years < 2025) & (years > 0))
    X = np.nan_to_num(np.hstack([A, M, t[:, None]]), nan=0.5)
    fp_y = hashlib.sha256(np.round(y[ev], 6).tobytes()).hexdigest()[:12]
    fp_pool = hashlib.sha256(np.round(y[pool], 6).tobytes() + pool.astype(np.int64).tobytes()).hexdigest()[:12]
    return X, y, ev, pool, fp_y, fp_pool


RIDGE = {}
for pname in ("KR 만화", "비게임 앱"):
    X, y, ev, pool, fp_y, fp_pool = build_xr(pname)
    cur = {"지문": {"y": fp_y, "pool": fp_pool}}
    for n in (10, 20, 50, 100, 200, 400, 800):
        vals = {"raw": [], "rank": [], "rawz": []}
        for dd in range(12):
            r2 = np.random.default_rng(8540 + 100 * n + dd)
            pick = r2.choice(pool, size=min(n, len(pool)), replace=False)
            for tgt in vals:
                if tgt == "raw":
                    yy = y[pick]
                elif tgt == "rank":
                    yy = rankdata(y[pick]) / len(pick)
                else:
                    mu, sd = y[pick].mean(), y[pick].std() or 1.0
                    yy = (y[pick] - mu) / sd
                m = Ridge(alpha=1.0).fit(X[pick], yy)
                pr_ = m.predict(X[ev])
                ok = np.isfinite(pr_) & np.isfinite(y[ev])
                vals[tgt].append(float(spearmanr(pr_[ok], y[ev][ok])[0]))
        cur[n] = {tgt: {"평균": round(float(np.mean(v)), 4),
                        "SE": round(float(np.std(v, ddof=1) / np.sqrt(12)), 4)} for tgt, v in vals.items()}
    RIDGE[pname] = cur
    print(f"릿지 {pname}: n10 raw {cur[10]['raw']} · rank {cur[10]['rank']}", flush=True)

# 843 RNG 재현 팔(KR · raw · 4뽑기 · n=10)
Xk, yk, evk, poolk, _, _ = build_xr("KR 만화")
rep = []
for dd in range(4):
    r2 = np.random.default_rng(8430 + 10 * 10 + dd)
    pick = r2.choice(poolk, size=10, replace=False)
    m = Ridge(alpha=1.0).fit(Xk[pick], yk[pick])
    pr_ = m.predict(Xk[evk])
    ok = np.isfinite(pr_) & np.isfinite(yk[evk])
    rep.append(float(spearmanr(pr_[ok], yk[evk][ok])[0]))
rep_mean = float(np.mean(rep))
print(f"843 RNG 재현 팔(n10·raw·4뽑기): {round(rep_mean,4)} (843 기록 0.3826)", flush=True)

# ── 갈래 판정 ────────────────────────────────────────────────────
B_KR, B_APP = 0.3919, 0.3123
branches = []
if abs(d_kr_mob) < 0.02:
    branches.append("ⓐ1.법칙 기각 — 해로움은 '틀린 이름'이 아니라 학습된 원핫의 오적용(강도)")
elif abs(d_kr_mob) >= 0.5 * abs(d_kr_man):
    branches.append("ⓐ2.법칙 생존")
else:
    branches.append("ⓐ중간 — 표 그대로")
branches.append(f"ⓐ3.양성 대조 앱×만화 해로움 {d_app_man:+.4f}")
# 앱 최강팔 n†
best_app = {n: max(RIDGE["비게임 앱"][n][t]["평균"] - 2 * RIDGE["비게임 앱"][n][t]["SE"] for t in ("raw", "rank", "rawz"))
            for n in (10, 20, 50, 100, 200, 400, 800)}
napp = next((n for n in sorted(best_app) if best_app[n] > B_APP), None)
branches.append(f"ⓑ앱 n†(최강팔·평균-2SE>{B_APP}) = {napp}")
kr_raw10 = RIDGE["KR 만화"][10]["raw"]
if kr_raw10["평균"] - 2 * kr_raw10["SE"] >= B_KR:
    branches.append("ⓑ3.KR 자 한정 — raw n10 이 B 위 분리 → '800건까지 전이 왕' 철회")
else:
    kr_best_all = max(RIDGE["KR 만화"][n][t]["평균"] for n in (10, 20, 50, 100, 200, 400, 800) for t in ("raw", "rank", "rawz"))
    branches.append(f"ⓑKR 최강팔 최고점 {kr_best_all:.4f} — B {B_KR} " + ("아래(전이 우위 자 무관 생존)" if kr_best_all < B_KR else "위 존재(전이 우위 조건부)"))
branches.append("ⓑ4.843 재현 " + ("성공(자 차 확정·요행 철회)" if abs(rep_mean - 0.3826) <= 0.02 else f"실패({rep_mean:.4f})"))

out = {"격자": grid, "격자 해시(rankdata)": hashes,
       "핵심 셀": {"KR×모바일 Δ(무정체−모바일)": round(d_kr_mob, 4), "KR×만화 Δ": round(d_kr_man, 4),
                  "앱×만화 Δ(무정체−만화)": round(d_app_man, 4), "앱 무정체=모바일 해시": bool(same_hash_app)},
       "릿지": RIDGE, "843 재현 팔": {"값": round(rep_mean, 4), "뽑기별": [round(x, 4) for x in rep]},
       "갈래": branches, "초": round(time.time() - t0, 1)}
print(json.dumps({k: v for k, v in out.items() if k not in ("격자 해시(rankdata)", "릿지")}, ensure_ascii=False, indent=1), flush=True)
json.dump(out, open(ROOT / "runners/out854_namegrid.json", "w"), ensure_ascii=False, indent=1)
