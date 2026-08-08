# -*- coding: utf-8 -*-
# 논문 474 figure — 손 수치 금지: out886_band.json 과 annex8 에서 계산한다.
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).parent
R = Path("/Users/ax/world_model")
o = json.load(open(R / "runners/out886_band.json"))
a8 = json.load(open(R / "cycle_log/forward/kobis/annex8_2026-08-09.json"))

b_rho = o["갑① 짝 Δρ 귀무 밴드(m=30)"]
pw = o["갑① 출력(power) — 정직 계산"]
b_err = o["2차 후보 — 짝 순위오차 감소(평균)"]

# 귀무분포를 그림용으로 다시 뽑는다(같은 정의 · 표본만 작게)
rows = json.load(open(R / "cycle_log/forward/kobis/annex7_2026-08-09.json"))["예측 팔(자루 평균 순위)"]
rn = np.array([r["국적 팔 순위"] for r in rows], float)
rc = np.array([r["대조 순위"] for r in rows], float)
m = len(rn)
az = (-rn - (-rn).mean()) / (-rn).std()
bz = (-rc - (-rc).mean()) / (-rc).std()
w = az - bz
rs = np.random.default_rng(886)
d_rho, d_err = np.empty(60000), np.empty(60000)
for i in range(60000):
    y = rs.permutation(np.arange(1.0, m + 1))
    yz = (y - y.mean()) / y.std()
    d_rho[i] = (w @ yz) / m
    ry = (-y).argsort().argsort() + 1
    d_err[i] = (np.abs(rc - ry) - np.abs(rn - ry)).mean()

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.4, 3.0))

for ax, d, band, ceil, name, unit in (
        (ax1, d_rho, b_rho["2σ"], pw["🔴 국적 팔이 라벨을 **완벽히** 맞혔을 때의 Δρ"],
         "primary: delta rho", ""),
        (ax2, d_err, b_err["2σ"], b_err["🔴 국적 팔 완벽 예측 시 Δ|err|"],
         "secondary: delta |err|", " ranks")):
    ax.hist(d, bins=70, color="#c8d2dc", edgecolor="none")
    ax.axvline(band, color="#b03a2e", lw=1.6, label=f"2sigma band {band:.3f}")
    ax.axvline(-band, color="#b03a2e", lw=1.0, ls=":")
    ax.axvline(ceil, color="#2e7d32", lw=2.0, ls="--",
               label=f"ceiling (perfect) {ceil:.3f}{unit}")
    reach = "UNREACHABLE" if ceil < band else "reachable"
    ax.set_title(f"{name}  --  {reach}", fontsize=9)
    ax.legend(fontsize=6.6, loc="upper left")
    ax.set_yticks([])
    ax.set_xlabel("null distribution (label permutations)", fontsize=7.5)

fig.suptitle(f"same 30 sealed films, same permutations; arms correlate "
             f"{pw['두 팔 순위 상관']:.3f}", fontsize=8.5, y=0.995)
fig.tight_layout()
(HERE / "figs").mkdir(exist_ok=True)
fig.savefig(HERE / "figs/bandceiling.png", dpi=200)
print(json.dumps({"1차 밴드": b_rho["2σ"], "1차 천장": pw["🔴 국적 팔이 라벨을 **완벽히** 맞혔을 때의 Δρ"],
                  "1차 도달": pw["🔴 완벽 예측이 밴드를 넘나"],
                  "2차 밴드": b_err["2σ"], "2차 천장": b_err["🔴 국적 팔 완벽 예측 시 Δ|err|"],
                  "2차 도달": b_err["🔴 완벽 예측이 밴드를 넘나"],
                  "2차 σ배수": b_err["완벽 예측의 σ 배수"]}, ensure_ascii=False))
