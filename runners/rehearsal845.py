# 노트 845 — 수확 정합성 리허설 (사전등록 '845' · 첫 라벨 관측 전 청정 창)
# 한계(첫 줄 규율): 844 의 동결 규칙은 불가침(694) — 여기서 만드는 것은 전부 '보조 병기'다.
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import pointbiserialr, rankdata, spearmanr

sys.path.insert(0, "/Users/ax/world_model")
from lab import guards as G, sideaudit  # noqa: E402
from lab.forms import REGISTRY  # noqa: E402

t0 = time.time()
T = 2025.0
SEEDS = list(range(12))
ROOT = Path("/Users/ax/world_model")

data12 = sideaudit.champion_data()
y_f = np.asarray(data12.dom["영화"][2], float)
yr_f = np.asarray(data12.yr["영화"], float)
kho = np.isfinite(yr_f) & (yr_f >= T) & np.isfinite(y_f)

# 배선: kobis_axes 의 행 순서가 champion_data 의 영화 행과 같은지 y 로 대조
KA = json.load(open(ROOT / "data/state/kobis_axes.json"))
ids = list(KA)
y_ka = np.array([KA[i]["y"] for i in ids], float)
assert len(y_ka) == len(y_f) and np.allclose(y_ka, y_f, equal_nan=True), "행 정렬 불일치"
cens = np.array([bool(KA[i].get("검열(개봉+14 미달)")) for i in ids])

names = list(data12.names["영화"])
j_vp = names.index("venue_prominence")
j_ef = names.index("entry_friction")

cls = REGISTRY["F18_bagboost"]["cls"]
Ah, Mh, yh, th = data12.slice("영화", kho)
cens_h = cens[kho]
fits = []
preds = []
for s in SEEDS:
    f = G._fit_on(lambda s=s: cls(seed=s), data12, T, seed=s)
    fits.append(f)
    preds.append(np.asarray(f.predict("영화", Ah, Mh, th), float))
    print(f"  씨앗 {s} ({time.time()-t0:.0f}s)", flush=True)
pe = np.nanmean(preds, axis=0)
ok = np.isfinite(pe) & np.isfinite(yh)
rho_ref = float(spearmanr(pe[ok], yh[ok])[0])
print(f"유보 {int(ok.sum())}행 · ρ {rho_ref:.4f}", flush=True)

# ── B. m-적응 밴드 부록 (m=10..30 · B=2000 · 비복원 뽑기) ─────────
rng = np.random.default_rng(845)
idx_all = np.flatnonzero(ok)
band = {}
for m in range(10, 31):
    bs = [spearmanr(pe[p], yh[p])[0]
          for p in (rng.choice(idx_all, size=m, replace=False) for _ in range(2000))]
    band[m] = round(2 * float(np.nanstd(bs, ddof=1)), 4)
print(f"B. 밴드 2σ: m=10 {band[10]} · m=15 {band[15]} · m=20 {band[20]} · m=30 {band[30]}", flush=True)

# ── C. 검열 리허설 (유보 406 의 검열 플래그) ──────────────────────
rate = float(cens_h[ok].mean())
prank = rankdata(-pe[ok])  # 1 = 예측 최상위
pb_r, pb_p = pointbiserialr(cens_h[ok].astype(float), prank)
keep = ok & ~cens_h
rho_excl = float(spearmanr(pe[keep], yh[keep])[0])
# 보조 채점: 검열 행을 실현 공동 최하위로 넣는다(라벨 최소값 아래 동순위)
y_aux = yh.copy()
y_aux[cens_h] = np.nanmin(yh[ok]) - 1.0
rho_tied = float(spearmanr(pe[ok], y_aux[ok])[0])
print(f"C. 검열률 {rate:.3f} · 순위~검열 점이연 r={pb_r:+.3f}(p={pb_p:.4f}) · "
      f"ρ 제외 {rho_excl:.4f} 대 공동최하위 {rho_tied:.4f}", flush=True)

# ── D. 커버리지 정합 기준 (배급 43.3%·등급 16.7% 무작위 마스크 · 6뽑기) ──
dvals = []
for k in range(6):
    r2 = np.random.default_rng(8451 + k)
    A2, M2 = Ah.copy(), Mh.copy()
    for j, frac in ((j_vp, 0.433), (j_ef, 0.167)):
        hit = r2.random(len(A2)) < frac
        A2[hit, j] = 0.5
        M2[hit, j] = 0.0
    pm = np.nanmean([np.asarray(f.predict("영화", A2, M2, th), float) for f in fits], axis=0)
    okm = np.isfinite(pm) & np.isfinite(yh)
    dvals.append(float(spearmanr(pm[okm], yh[okm])[0]))
d_mean, d_sd = float(np.mean(dvals)), float(np.std(dvals, ddof=1))
print(f"D. 정합 기준 ρ {d_mean:.4f} ± {d_sd:.4f} (Δ {d_mean-rho_ref:+.4f})", flush=True)

# ── 갈래 판정 (사전등록 그대로) ───────────────────────────────────
branches = []
if rate < 0.15 and pb_p >= 0.05:
    branches.append("2.수확 계획 유지(검열률 낮고 상관 비유의)")
else:
    branches.append("3.보조 채점 승격('검열=공동최하위' 를 수확 보고의 정본 병기로)")
if d_mean <= rho_ref - 0.02:
    branches.append("4.기준 분리('붕괴' 갈래를 '결측 조정 후 재판정'으로)")

# ── E. 부록 동결 (보조 병기 · 동결 규칙 불가침) ──────────────────
annex = {
    "작성일": "2026-08-08", "성격": "보조 병기 — 844 동결 규칙(문턱 0.2046)은 불가침(694)",
    "m-적응 밴드 2σ(부트 B=2000)": band,
    "검열 리허설": {"유보 검열률": round(rate, 4),
                    "예측순위~검열 점이연": {"r": round(float(pb_r), 4), "p": round(float(pb_p), 5)},
                    "ρ(검열 제외)": round(rho_excl, 4), "ρ(검열=공동최하위)": round(rho_tied, 4),
                    "보조 채점 규칙": "수확에서 '검열 제외 ρ'(동결 정본)와 '검열=공동최하위 ρ' 를 병기"},
    "커버리지 정합 기준": {"ρ": round(d_mean, 4), "±SD(6뽑기)": round(d_sd, 4),
                          "기제 차이 병기": "봉인 결측은 무작위가 아니라 소형(사전 밖 배급) 편향 — 이 기준은 하한이 아니라 근사"},
    "합산 검정력 규칙(봉인 2호와 첫 라벨 전 동결)": {
        "결합": "ρ̄ = Σ mᵢρᵢ / Σ mᵢ (mᵢ = 유효 편수)",
        "밴드": "σ̄ = √(Σ mᵢ²σᵢ²) / Σ mᵢ · σᵢ 는 위 m-표(m<10 은 판정 불가)",
        "상표": "'전향 재현' 은 누적 유효 ≥60편부터 · 그 전 통과는 '총붕괴 아님' 까지만(귀무 ρ=0 도 m=30 문턱을 ~13.6% 로 넘는다)",
    },
    "갈래 판정": branches,
}
ap = ROOT / "cycle_log/forward/kobis/annex_2026-08-08.json"
with open(ap, "x") as fh:
    json.dump(annex, fh, ensure_ascii=False, indent=1)

# 사이드카 2호 — 지문 사슬 자백
e2 = ROOT / "cycle_log/forward/kobis/seal_2026-08-08.erratum2.json"
with open(e2, "x") as fh:
    json.dump({
        "대상": "seal_2026-08-08.json 모형 지문",
        "자백": "봉인의 코드 sha b641c61669014ce5 는 커밋된 runners/seal844.py(d478aee6…)와 다르다 — 봉인 후 필드명 수리 편집이 지문 사슬을 끊었다(티처 #11 적발 ①). 봉인 시점 정본을 편집 역산으로 재구성해 sha 일치를 확인하고 runners/seal844_sealed.py 로 커밋했다 — 사슬 복원.",
        "작성일": "2026-08-08",
    }, fh, ensure_ascii=False, indent=1)

out = {"B 밴드(발췌)": {m: band[m] for m in (10, 15, 20, 30)},
       "C": annex["검열 리허설"], "D": annex["커버리지 정합 기준"],
       "갈래": branches, "ρ_ref 재현": round(rho_ref, 4),
       "초": round(time.time() - t0, 1)}
print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)
json.dump(out, open(ROOT / "runners/out845_rehearsal.json", "w"), ensure_ascii=False, indent=1)
