# -*- coding: utf-8 -*-
# 노트 853 — 무정체 자의 일반화 (사전등록 '853' · 같은 적합 한 벌 · 앱/CN 4팔 + KR 릿지 재판정)
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge

sys.path.insert(0, "/Users/ax/world_model")
from lab import guards as G, pairs as PR, sideaudit  # noqa: E402
from lab.forms import REGISTRY  # noqa: E402

t0 = time.time()
T = 2025.0
SEEDS = list(range(12))
ROOT = Path("/Users/ax/world_model")

data12 = sideaudit.champion_data()
cls = REGISTRY["F18_bagboost"]["cls"]


def build_pair(pair, datefield):
    src = PR.SRC_DOM[pair]
    names = list(data12.names[src])
    recs = PR.build(pair)
    A, M, y, t = PR.to_arrays(recs, names)
    A = np.asarray(A, float); M = np.asarray(M, float)
    y = np.asarray(y, float); t = np.asarray(t, float)
    years = np.array([int(str((r.get(datefield) or r.get("start_date") or r.get("release_date") or "0000"))[:4] or 0)
                      for r in recs.values()])
    fin = np.isfinite(y)
    ev = np.flatnonzero(fin & (years >= 2025))
    pool = np.flatnonzero(fin & (years < 2025) & (years > 0))
    fp = hashlib.sha256(np.round(y[ev], 6).tobytes()).hexdigest()[:12]
    # 배선: 관측 축 덮음 + spec 후보 축 관측 수
    cov = {names[j]: round(float(M[:, j].mean()), 3) for j in range(len(names)) if M[:, j].mean() > 0}
    return src, names, A, M, y, t, ev, pool, fp, cov


pairs_cfg = [("비게임 앱", "release_date"), ("CN 만화", "start_date")]
built = {p: build_pair(p, df) for p, df in pairs_cfg}
for p, b in built.items():
    src, names, A, M, y, t, ev, pool, fp, cov = b
    spec_axes = [a for a in cov if a.startswith("tag_") or a.startswith("meta_")]
    print(f"{p}: 평가 {len(ev)} · 풀 {len(pool)} · 지문 {fp} · 관측 축 {cov} · spec류 관측 {spec_axes}", flush=True)
    data12.names[f"무정체_{p}"] = list(names)     # B팔 names 등록(서빙 지뢰 회피)

# 같은 적합 한 벌
fits = []
for s in SEEDS:
    fits.append(G._fit_on(lambda s=s: cls(seed=s), data12, T, seed=s))
    print(f"  씨앗 {s} ({time.time()-t0:.0f}s)", flush=True)

RES = {}
for p, b in built.items():
    src, names, A, M, y, t, ev, pool, fp, cov = b
    pa = np.nanmean([np.asarray(f.predict(src, A[ev], M[ev], t[ev]), float) for f in fits], axis=0)
    pb = np.nanmean([np.asarray(f.predict(f"무정체_{p}", A[ev], M[ev], t[ev]), float) for f in fits], axis=0)
    oka = np.isfinite(pa) & np.isfinite(y[ev])
    okb = np.isfinite(pb) & np.isfinite(y[ev])
    ra = float(spearmanr(pa[oka], y[ev][oka])[0])
    rb = float(spearmanr(pb[okb], y[ev][okb])[0])
    RES[p] = {"평가": len(ev), "지문": fp, "A(정체)": round(ra, 4), "B(무정체)": round(rb, 4),
              "격차 B−A": round(rb - ra, 4), "유한": [int(oka.sum()), int(okb.sum())]}
    print(f"{p}: A {ra:.4f} · B {rb:.4f} · 격차 {rb-ra:+.4f}", flush=True)

# ── KR 릿지 재판정(뽑기 12 · α=1 고정 · 지문 대조) ───────────────
srcK = PR.SRC_DOM["KR 만화"]
namesK = list(data12.names[srcK])
recsK = PR.build("KR 만화")
AK, MK, yK, tK = PR.to_arrays(recsK, namesK)
AK = np.asarray(AK, float); MK = np.asarray(MK, float)
yK = np.asarray(yK, float); tK = np.asarray(tK, float)
yearsK = np.array([int(str((r.get("start_date") or "0000"))[:4] or 0) for r in recsK.values()])
finK = np.isfinite(yK)
evK = np.flatnonzero(finK & (yearsK >= 2025))
poolK = np.flatnonzero(finK & (yearsK < 2025) & (yearsK > 0))
fpK = hashlib.sha256(np.round(yK[evK], 6).tobytes()).hexdigest()[:12]
assert fpK == "adb00d2827b0", f"KR 지문 불일치 {fpK}"
XrK = np.nan_to_num(np.hstack([AK, MK, tK[:, None]]), nan=0.5)
from scipy.stats import rankdata as _rk  # noqa: E402
curve = {}
for n in (10, 20, 50, 100, 200, 400, 800):
    vals = []
    for dd in range(12):
        r2 = np.random.default_rng(8530 + 100 * n + dd)
        pick = r2.choice(poolK, size=min(n, len(poolK)), replace=False)
        m = Ridge(alpha=1.0).fit(XrK[pick], _rk(yK[pick]) / len(pick))
        pr_ = m.predict(XrK[evK])
        ok = np.isfinite(pr_) & np.isfinite(yK[evK])
        vals.append(float(spearmanr(pr_[ok], yK[evK][ok])[0]))
    a_ = np.array(vals)
    curve[n] = {"평균": round(float(a_.mean()), 4), "SE": round(float(a_.std(ddof=1) / np.sqrt(12)), 4)}
    print(f"  KR 릿지 n={n}: {curve[n]['평균']} ± SE {curve[n]['SE']}", flush=True)
B_KR = 0.3919
sep10 = curve[10]["평균"] + curve[10]["SE"] < B_KR
max_n = max(curve, key=lambda n: curve[n]["평균"])
never = all(curve[n]["평균"] + 2 * curve[n]["SE"] < B_KR or curve[n]["평균"] < B_KR for n in curve)

branches = []
gA = RES["비게임 앱"]["격차 B−A"]
gC = RES["CN 만화"]["격차 B−A"]
if gA >= 0.05 and gC >= 0.05:
    branches.append("1.보편 — 이름 해로움은 짝 무관 · 전이 정본=무정체 승격 · 앱 창 재판정")
elif abs(gA) < 0.02 and abs(gC) < 0.02:
    branches.append("2.KR 특이 — 852 처방 KR 한정 후퇴")
else:
    branches.append("3.혼합 — 도메인별 표 그대로")
branches.append("4.KR 재판정 — " + ("n10 이 B 아래 분리(전이 우위 확정)" if sep10 else "n≤20 미분리 명문"))

out = {"4팔": RES, "KR 릿지(뽑기12·α=1·지문 " + fpK + ")": curve,
       "B_KR 대비": {"n10 분리": bool(sep10), "최고점 n": int(max_n),
                    "최고점": curve[max_n]["평균"], "전 격자 B 아래": bool(never)},
       "갈래": branches, "초": round(time.time() - t0, 1)}
print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)
json.dump(out, open(ROOT / "runners/out853_general.json", "w"), ensure_ascii=False, indent=1)
