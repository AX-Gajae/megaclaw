# -*- coding: utf-8 -*-
# 노트 855 — 서빙 경로 실물 감사 (사전등록 '855' · 배치·폴백·혼합)
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, "/Users/ax/world_model")
from lab import guards as G, pairs as PR, sideaudit  # noqa: E402
from lab.forms import REGISTRY  # noqa: E402

t0 = time.time()
T = 2025.0
SEEDS = list(range(12))
ROOT = Path("/Users/ax/world_model")

data12 = sideaudit.champion_data()
cls = REGISTRY["F18_bagboost"]["cls"]
DOMS = sorted(data12.dom)

# KR 짝 준비
src = PR.SRC_DOM["KR 만화"]
names = list(data12.names[src])
recs = PR.build("KR 만화")
A, M, y, t = PR.to_arrays(recs, names)
A = np.asarray(A, float); M = np.asarray(M, float)
y = np.asarray(y, float); t = np.asarray(t, float)
years = np.array([int(str((r.get("start_date") or "0000"))[:4] or 0) for r in recs.values()])
ev = np.flatnonzero(np.isfinite(y) & (years >= 2025))
assert len(ev) == 322
data12.names["NL_KR"] = list(names)     # 등록 경로

fits = []
for s in SEEDS:
    fits.append(G._fit_on(lambda s=s: cls(seed=s), data12, T, seed=s))
    print(f"  씨앗 {s} ({time.time()-t0:.0f}s)", flush=True)

# ── ⓐ 판 배치 감사: post 전체 대 post∩라벨 ───────────────────────
aud = {}
pool_a, pool_b, weights = [], [], []
for dmn in DOMS:
    yr_d = np.asarray(data12.yr[dmn], float)
    y_d = np.asarray(data12.dom[dmn][2], float)
    post = np.isfinite(yr_d) & (yr_d >= T)
    lab = post & np.isfinite(y_d)
    if lab.sum() < 20:
        continue
    Aa, Ma, ya, ta = data12.slice(dmn, post)
    lab_in_post = np.isfinite(ya)
    Ab, Mb, yb, tb = data12.slice(dmn, lab)
    ra, rb = [], []
    for f in fits:
        pa = np.asarray(f.predict(dmn, Aa, Ma, ta), float)[lab_in_post]
        pb = np.asarray(f.predict(dmn, Ab, Mb, tb), float)
        oka = np.isfinite(pa) & np.isfinite(ya[lab_in_post])
        okb = np.isfinite(pb) & np.isfinite(yb)
        ra.append(float(spearmanr(pa[oka], ya[lab_in_post][oka])[0]))
        rb.append(float(spearmanr(pb[okb], yb[okb])[0]))
    aud[dmn] = {"라벨/전체": f"{int(lab.sum())}/{int(post.sum())}",
                "ρ(전체 배치)": round(float(np.mean(ra)), 4),
                "ρ(라벨 배치)": round(float(np.mean(rb)), 4),
                "Δ": round(float(np.mean(rb) - np.mean(ra)), 4)}
    pool_a.append((float(np.mean(ra)), int(lab.sum())))
    pool_b.append((float(np.mean(rb)), int(lab.sum())))
pan_a = sum(r * w for r, w in pool_a) / sum(w for _, w in pool_a)
pan_b = sum(r * w for r, w in pool_b) / sum(w for _, w in pool_b)
d_pan = pan_b - pan_a
print(f"ⓐ 판: 전체 배치 {pan_a:.4f} · 라벨 배치 {pan_b:.4f} · Δ판 {d_pan:+.5f}", flush=True)

# ── ⓑ 폴백 등가성: 등록 대 미등록(ALL5 폴백) — 자루 원점수 해시 ──
f0 = fits[0]
D_reg = f0._design("NL_KR", A[ev], M[ev], t[ev])
D_fb = f0._design("폴백_미등록_KR", A[ev], M[ev], t[ev])   # names 미등록 → _feat ALL5 폴백
raw_reg = np.vstack([m.predict(D_reg) for m in f0.ms])
raw_fb = np.vstack([m.predict(D_fb) for m in f0.ms])
h_reg = hashlib.sha256(np.round(raw_reg, 10).tobytes()).hexdigest()[:12]
h_fb = hashlib.sha256(np.round(raw_fb, 10).tobytes()).hexdigest()[:12]
same_fb = h_reg == h_fb
# 폴백 예측의 ρ 도 병기(오정렬 숫자의 크기)
pe_fb = np.nanmean([np.asarray(f.predict("폴백_미등록_KR", A[ev], M[ev], t[ev]), float) for f in fits], axis=0)
ok = np.isfinite(pe_fb) & np.isfinite(y[ev])
rho_fb = float(spearmanr(pe_fb[ok], y[ev][ok])[0])
print(f"ⓑ 폴백: 등가 {same_fb} · 등록 해시 {h_reg} 대 폴백 {h_fb} · 폴백 ρ {rho_fb:.4f}(등록 0.3919)", flush=True)

# ── ⓒ 혼합 배치 불변성 ──────────────────────────────────────────
def subset_order(pred_full, idx_subset):
    sub = pred_full[idx_subset]
    return [int(i) for i in np.argsort(-sub, kind="stable")]


Amn, Mmn, ymn, tmn = data12.slice(src, np.isfinite(np.asarray(data12.yr[src], float)) &
                                  (np.asarray(data12.yr[src], float) >= T))
res_mix = {}
for ident in ("NL_KR", "아이돌"):
    if ident == "아이돌":
        names_i = list(data12.names["아이돌"])
        Ai, Mi, yi, ti = PR.to_arrays(recs, names_i)
        Ai = np.asarray(Ai, float); Mi = np.asarray(Mi, float); ti = np.asarray(ti, float)
        Ae, Me, te = Ai[ev], Mi[ev], ti[ev]
        # 혼합 상대는 판 아이돌 유보
        yr_i = np.asarray(data12.yr["아이돌"], float)
        Ax, Mx, yx, tx = data12.slice("아이돌", np.isfinite(yr_i) & (yr_i >= T))
    else:
        Ae, Me, te = A[ev], M[ev], t[ev]
        Ax, Mx, yx, tx = Amn, Mmn, ymn, tmn
    solo = np.nanmean([np.asarray(f.predict(ident, Ae, Me, te), float) for f in fits], axis=0)
    Amix = np.vstack([Ae, Ax])
    Mmix = np.vstack([Me, Mx])
    tmix = np.concatenate([te, tx])
    mixed = np.nanmean([np.asarray(f.predict(ident, Amix, Mmix, tmix), float) for f in fits], axis=0)
    idx = list(range(len(ev)))
    ord_solo = subset_order(solo, idx)
    ord_mix = subset_order(mixed, idx)
    n_moved = sum(1 for a, b in zip(ord_solo, ord_mix) if a != b)
    rho_solo = float(spearmanr(solo[np.isfinite(solo) & np.isfinite(y[ev])],
                               y[ev][np.isfinite(solo) & np.isfinite(y[ev])])[0])
    okm = np.isfinite(mixed[:len(ev)]) & np.isfinite(y[ev])
    rho_mix = float(spearmanr(mixed[:len(ev)][okm], y[ev][okm])[0])
    res_mix[ident] = {"보존": bool(ord_solo == ord_mix), "자리 다른 행": n_moved,
                      "ρ 단독": round(rho_solo, 4), "ρ 혼합": round(rho_mix, 4)}
    print(f"ⓒ 혼합 {ident}: 보존 {ord_solo == ord_mix} · 이동 {n_moved} · ρ {rho_solo:.4f}→{rho_mix:.4f}", flush=True)

# ── 갈래 ─────────────────────────────────────────────────────────
SEED_SD = 0.0010
branches = []
if not same_fb:
    branches.append(f"2.폴백 지뢰 실물 — 원점수 불일치(폴백 ρ {rho_fb:.4f} 대 등록 0.3919) → NL 등록 가드 필요")
if abs(d_pan) < SEED_SD:
    branches.append(f"1.판 배치 무해(Δ판 {d_pan:+.5f} < 씨앗SD) — '판 배치 = post 전체' 명문화")
elif abs(d_pan) >= 2 * SEED_SD:
    branches.append(f"4.판 배치 감사 초과(Δ판 {d_pan:+.5f}) — 배치 규약 재사전등록")
else:
    branches.append(f"중간(Δ판 {d_pan:+.5f} ∈ [1σ,2σ)) — 도메인별 표 병기")
if res_mix["NL_KR"]["보존"]:
    branches.append("3a.무정체 혼합 보존(행 함수 코드 예측 검증)")
else:
    branches.append("3b.무정체도 혼합 변동 — 짝 단독 배치 규약 필요")
branches.append("3c.아이돌 정체 혼합 " + ("변동(spec 배치 효과 실물)" if not res_mix["아이돌"]["보존"] else "보존(예상 밖)"))

out = {"ⓐ 판 배치": {"도메인별": aud, "판(전체)": round(pan_a, 4), "판(라벨)": round(pan_b, 4),
                    "Δ판": round(d_pan, 5)},
       "ⓑ 폴백": {"등가": bool(same_fb), "해시": [h_reg, h_fb], "폴백 ρ": round(rho_fb, 4)},
       "ⓒ 혼합": res_mix, "갈래": branches, "초": round(time.time() - t0, 1)}
print(json.dumps({k: v for k, v in out.items() if k != "ⓐ 판 배치"} | {"Δ판": out["ⓐ 판 배치"]["Δ판"]},
                 ensure_ascii=False, indent=1), flush=True)
json.dump(out, open(ROOT / "runners/out855_servaudit.json", "w"), ensure_ascii=False, indent=1)
