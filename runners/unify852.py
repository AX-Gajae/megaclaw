# -*- coding: utf-8 -*-
# 노트 852 — 전이 자 통일 (사전등록 '852' · 같은 적합 한 벌 · 예측 경로만 격리)
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
src = PR.SRC_DOM["KR 만화"]                       # '만화'
names = list(data12.names[src])
recs = PR.build("KR 만화")
A, M, y, t = PR.to_arrays(recs, names)
A = np.asarray(A, float); M = np.asarray(M, float)
y = np.asarray(y, float); t = np.asarray(t, float)
years = np.array([int(str((r.get("start_date") or "0000"))[:4] or 0) for r in recs.values()])
fin = np.isfinite(y)
ev = np.flatnonzero(fin & (years >= 2025))
assert len(ev) == 322
fp = hashlib.sha256(np.round(y[ev], 6).tobytes()).hexdigest()[:12]
print(f"평가 322 · 라벨 지문 {fp}", flush=True)

# B팔 이름 등록: 예측 시 names 조회가 되도록 names dict 에만 'KR만화' 추가(도메인 미등록 — OOC)
data12.names["KR만화"] = list(names)

cls = REGISTRY["F18_bagboost"]["cls"]
pa, pb = [], []
for s in SEEDS:
    f = G._fit_on(lambda s=s: cls(seed=s), data12, T, seed=s)
    pa.append(np.asarray(f.predict(src, A[ev], M[ev], t[ev]), float))       # A: 만화-정체
    pb.append(np.asarray(f.predict("KR만화", A[ev], M[ev], t[ev]), float))  # B: 무정체(OOC)
    print(f"  씨앗 {s} ({time.time()-t0:.0f}s)", flush=True)

pa_m = np.nanmean(pa, axis=0)
pb_m = np.nanmean(pb, axis=0)
oka = np.isfinite(pa_m) & np.isfinite(y[ev])
okb = np.isfinite(pb_m) & np.isfinite(y[ev])
rho_a = float(spearmanr(pa_m[oka], y[ev][oka])[0])
rho_b = float(spearmanr(pb_m[okb], y[ev][okb])[0])
# 씨앗별 ρ 병기(평균-후-ρ 와 ρ-후-평균의 Jensen 갭 확인)
ra_seed = [float(spearmanr(np.asarray(p)[oka], y[ev][oka])[0]) for p in pa]
rb_seed = [float(spearmanr(np.asarray(p)[okb], y[ev][okb])[0]) for p in pb]
print(f"A(만화-정체) ρ {rho_a:.4f} (씨앗별 평균 {np.mean(ra_seed):.4f} ± {np.std(ra_seed, ddof=1):.4f})", flush=True)
print(f"B(무정체 OOC) ρ {rho_b:.4f} (씨앗별 평균 {np.mean(rb_seed):.4f} ± {np.std(rb_seed, ddof=1):.4f})", flush=True)
print(f"지문: 유한 A {int(oka.sum())} · B {int(okb.sum())} · 격차 B−A {rho_b-rho_a:+.4f}", flush=True)

# 앵커(13도메인 빈-등록) 예측과 B팔 상관 — 두 OOC 변종이 같은 것인가
ck = [json.loads(l) for l in open(ROOT / "runners/out848_checkpoint.jsonl")]
anchor_pred = np.array(next(r["joint_pred"] for r in ck if r["n"] == 0), float)
rho_anchor = float(spearmanr(anchor_pred[okb], y[ev][okb])[0])
corr_b_anchor = float(spearmanr(pb_m[okb], anchor_pred[okb])[0])
print(f"앵커 재채점 ρ {rho_anchor:.4f} · B팔↔앵커 예측 상관 {corr_b_anchor:.4f}", flush=True)

# 갈래 판정(사전등록 그대로)
branches = []
if abs(rho_a - 0.2969) <= 0.02 and rho_b >= 0.36 and (rho_b - rho_a) >= 0.05:
    branches.append("1.경로 차 확정 — 전이 상수는 예측 경로의 함수(만화-정체가 KR 를 해침)")
if abs(rho_a - 0.2969) > 0.02:
    branches.append("2.833 재현 실패 — 스크래치 오류 조사")
if int(oka.sum()) != int(okb.sum()):
    branches.append("3.지문 불일치")
if not branches:
    branches.append("4.격차 미해명 — 두 자 그대로 기록")

out = {"A(만화-정체)": round(rho_a, 4), "B(무정체 OOC)": round(rho_b, 4),
       "격차 B−A": round(rho_b - rho_a, 4),
       "씨앗별": {"A": [round(x, 4) for x in ra_seed], "B": [round(x, 4) for x in rb_seed]},
       "앵커 재채점": round(rho_anchor, 4), "B↔앵커 상관": round(corr_b_anchor, 4),
       "지문": {"라벨": fp, "유한 A": int(oka.sum()), "유한 B": int(okb.sum())},
       "갈래": branches, "초": round(time.time() - t0, 1)}
print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)
json.dump(out, open(ROOT / "runners/out852_unify.json", "w"), ensure_ascii=False, indent=1)
