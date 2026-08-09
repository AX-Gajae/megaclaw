# -*- coding: utf-8 -*-
"""노트 886 후속 검산 — 티처 #51 F1·F2 를 내 손으로.

F1: "양성 갈래가 발화할 라벨이 우주에 없다"가 거짓인가.
F2: Δ|err| 가 **현실 효과 크기**에서 정말 Δρ 보다 나은가(완벽예측 점 말고).

라벨·자료·판 하네스 무접촉 — 동결된 두 순위 벡터만 쓴다.
"""
import json
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

R = Path("/Users/ax/world_model")
rows = json.loads((R / "cycle_log/forward/kobis/annex7_2026-08-09.json").read_text())[
    "예측 팔(자루 평균 순위)"]
rn = np.array([r["국적 팔 순위"] for r in rows], float)
rc = np.array([r["대조 순위"] for r in rows], float)
m = len(rn)
BAND_RHO, BAND_ERR, TAU = 0.1668, 1.1612, 1.4667


def d_rho(y):
    return float(spearmanr(-rn, y)[0] - spearmanr(-rc, y)[0])


def d_err(y):
    ry = (-np.asarray(y, float)).argsort().argsort() + 1.0
    return float((np.abs(rc - ry) - np.abs(rn - ry)).mean())


# ── F1: 적대적 y 가 정말 밴드를 넘나 ─────────────────────────────
az = (-rn - (-rn).mean()) / (-rn).std()
bz = (-rc - (-rc).mean()) / (-rc).std()
w = az - bz
ys = np.arange(1.0, m + 1)
ysz = (ys - ys.mean()) / ys.std()
order = np.argsort(w)                       # w 작은 자리에 작은 y
y_adv = np.empty(m)
y_adv[order] = ys                           # 재배열 부등식 = 정확해
f1 = {"적대적 y 의 Δρ": round(d_rho(y_adv), 4),
      "밴드": BAND_RHO,
      "🔴 밴드를 넘나": bool(d_rho(y_adv) > BAND_RHO),
      "그 y 와 국적 팔 spearman": round(float(spearmanr(-rn, y_adv)[0]), 4),
      "그 y 와 대조 팔 spearman": round(float(spearmanr(-rc, y_adv)[0]), 4),
      "그 y 의 Δ|err|": round(d_err(y_adv), 4),
      "판정": ("**티처 #51 F1 이 옳다** — '우주에 없다'는 거짓이다. 다만 그 y 는 "
             "**대조 팔이 음의 상관**인 세계다(국적 팔이 단지 더 나은 세계가 아니다). "
             "참인 명제: '국적 팔이 라벨을 잘 맞히는 방향으로는 못 넘는다'")}

# ── F2: 현실 효과 크기에서의 검정력 ─────────────────────────────
# 라벨 = 국적 팔 순위 + 잡음. 잡음 크기를 바꿔 ρ_n 을 훑는다.
rs = np.random.default_rng(8862)
base = -rn                                   # 큰 값 = 좋은 성적
rows_out = []
for sd in (0.0, 0.15, 0.30, 0.45, 0.60, 0.90, 1.30, 2.00):
    n_hit_rho = n_hit_err = n_harm = 0
    rho_ns, drs, des = [], [], []
    for _ in range(3000):
        y = (base - base.mean()) / base.std() + rs.normal(0, sd, m)
        rho_ns.append(float(spearmanr(-rn, y)[0]))
        dr, de = d_rho(y), d_err(y)
        drs.append(dr); des.append(de)
        n_hit_rho += dr > BAND_RHO
        n_hit_err += de > BAND_ERR
        n_harm += de < -BAND_ERR
    rows_out.append({
        "잡음 SD": sd, "ρ_국적팔(평균)": round(float(np.mean(rho_ns)), 3),
        "Δρ 평균": round(float(np.mean(drs)), 4),
        "Δ|err| 평균": round(float(np.mean(des)), 4),
        "P(Δρ > 밴드)": round(n_hit_rho / 3000, 4),
        "🔴 P(Δ|err| > 밴드) = 검정력": round(n_hit_err / 3000, 4),
        "P(해롭다 오발화)": round(n_harm / 3000, 4)})

# 귀무(라벨 무관)에서의 크기
n_sz_r = n_sz_e = n_sz_h = 0
for _ in range(3000):
    y = rs.permutation(np.arange(1.0, m + 1))
    n_sz_r += d_rho(y) > BAND_RHO
    de = d_err(y)
    n_sz_e += de > BAND_ERR
    n_sz_h += de < -BAND_ERR

# MDE: Δ|err| 가 80% 로 밴드를 넘는 크기
out = {
 "F1 — '우주에 없다'가 거짓인가": f1,
 "F2 — 현실 효과 크기 검정력": {
   "설계": "라벨 = 국적 팔 순위 + 정규잡음 · 3,000회 · 씨앗 8862. 두 통계에 **같은 라벨**을 먹인다",
   "표": rows_out,
   "귀무 크기": {"Δρ": round(n_sz_r / 3000, 4), "Δ|err|": round(n_sz_e / 3000, 4),
              "해롭다": round(n_sz_h / 3000, 4)},
   "τ 가 뜻하는 효과 크기": TAU,
 },
}
with open(R / "runners/out886b_power.json", "x") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
