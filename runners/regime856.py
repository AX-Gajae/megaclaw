# -*- coding: utf-8 -*-
# 노트 856 — 봉인 밴드의 배치 레짐 재눈금 (사전등록 '856')
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, "/Users/ax/world_model")
from lab import guards as G, sideaudit  # noqa: E402
from lab.forms import REGISTRY  # noqa: E402

t0 = time.time()
T = 2025.0
SEEDS = list(range(12))
K = 200
M30 = 30
ROOT = Path("/Users/ax/world_model")

data12 = sideaudit.champion_data()
cls = REGISTRY["F18_bagboost"]["cls"]
yr_f = np.asarray(data12.yr["영화"], float)
y_f = np.asarray(data12.dom["영화"][2], float)
kho = np.isfinite(yr_f) & (yr_f >= T) & np.isfinite(y_f)
Ah, Mh, yh, th = data12.slice("영화", kho)
n_ev = len(yh)
print(f"영화 유보 {n_ev}", flush=True)

fits = []
for s in SEEDS:
    fits.append(G._fit_on(lambda s=s: cls(seed=s), data12, T, seed=s))
    print(f"  씨앗 {s} ({time.time()-t0:.0f}s)", flush=True)

pe_full = np.nanmean([np.asarray(f.predict("영화", Ah, Mh, th), float) for f in fits], axis=0)
okf = np.isfinite(pe_full) & np.isfinite(yh)
idx_all = np.flatnonzero(okf)
rho_full406 = float(spearmanr(pe_full[okf], yh[okf])[0])
print(f"전체-배치 406 ρ {rho_full406:.4f}", flush=True)

rng = np.random.default_rng(856)
d_list, full_list, solo_list, moved_list = [], [], [], []
for k in range(K):
    pick = rng.choice(idx_all, size=M30, replace=False)
    r_full = float(spearmanr(pe_full[pick], yh[pick])[0])
    pe_solo = np.nanmean([np.asarray(f.predict("영화", Ah[pick], Mh[pick], th[pick]), float)
                          for f in fits], axis=0)
    ok = np.isfinite(pe_solo) & np.isfinite(yh[pick])
    r_solo = float(spearmanr(pe_solo[ok], yh[pick][ok])[0])
    # 참고: 자리 이동(부분집합 내 상대 순위)
    o_full = list(np.argsort(-pe_full[pick], kind="stable"))
    o_solo = list(np.argsort(-pe_solo, kind="stable"))
    moved_list.append(sum(1 for a, b in zip(o_full, o_solo) if a != b))
    full_list.append(r_full)
    solo_list.append(r_solo)
    d_list.append(r_solo - r_full)
    if (k + 1) % 50 == 0:
        print(f"  {k+1}/{K} ({time.time()-t0:.0f}s)", flush=True)

d_arr = np.array(d_list)
full_arr = np.array(full_list)
solo_arr = np.array(solo_list)
mean_d = float(np.nanmean(d_arr))
sd_full = float(np.nanstd(full_arr, ddof=1))
sd_solo = float(np.nanstd(solo_arr, ddof=1))
ratio = sd_solo / sd_full
moved_mean = float(np.mean(moved_list))

THR = 0.014
branches = []
if abs(mean_d) <= THR and 0.8 <= ratio <= 1.25:
    branches.append(f"1.레짐 정합 — |평균 차| {mean_d:+.4f} ≤ {THR} · SD 비 {ratio:.3f} ∈ [0.8,1.25] → 규약 ⑥ 명문화")
elif mean_d < -THR:
    branches.append(f"3.관대 편향 — 단독 계통 하락({mean_d:+.4f}) → 문턱 0.2046 수확 부록 병기")
else:
    branches.append(f"2.밴드 재눈금 — 평균 차 {mean_d:+.4f} 또는 SD 비 {ratio:.3f} 초과 → 봉인 2호 단독 배치 밴드 annex")

out = {"전체-배치 406 ρ": round(rho_full406, 4),
       "K": K, "m": M30,
       "ρ_full(부분추출)": {"평균": round(float(np.mean(full_arr)), 4), "SD": round(sd_full, 4)},
       "ρ_solo(단독 재예측)": {"평균": round(float(np.mean(solo_arr)), 4), "SD": round(sd_solo, 4)},
       "쌍별 차(solo−full)": {"평균": round(mean_d, 4), "SD": round(float(np.nanstd(d_arr, ddof=1)), 4),
                             "|차|>0.05 비율": round(float(np.mean(np.abs(d_arr) > 0.05)), 3)},
       "SD 비(solo/full)": round(ratio, 3),
       "자리 이동(참고 · 30행 중)": round(moved_mean, 1),
       "갈래": branches, "초": round(time.time() - t0, 1)}
print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)
json.dump(out, open(ROOT / "runners/out856_regime.json", "w"), ensure_ascii=False, indent=1)
