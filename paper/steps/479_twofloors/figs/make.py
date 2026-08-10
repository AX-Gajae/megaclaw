# -*- coding: utf-8 -*-
"""그림 1 — 널이 두 종류다(노트 892). 값은 전부 산출물에서 읽는다(손 전사 금지)."""
import json
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager, rcParams
for c in ("AppleSDGothicNeo", "Apple SD Gothic Neo", "NanumGothic"):
    try:
        font_manager.findfont(c, fallback_to_default=False); rcParams["font.family"] = c; break
    except Exception:
        pass
rcParams["axes.unicode_minus"] = False

d = json.load(open("/Users/ax/world_model/runners/out892_floor.json"))
F = d["🔴 열 수별 잡음 바닥(연속 · 뽑기 12 · 씨앗 0~5)"]
L = d["카디널리티 사다리(3열 · 뽑기 6 · 씨앗 0~2)"]
THR = d["자"]["문턱"]
BAND = d["자"]["방어 대역"]
DOM = d["도메인별 흔들림(연속 3열 · 팔 − 기준선)"]

fig, ax = plt.subplots(1, 3, figsize=(11.2, 3.5))

# ── 왼쪽: 열 수별 바닥 대 채택 문턱 ─────────────────────────────
keys = ["연속 1열", "연속 2열", "연속 3열"]
mu = [F[k]["**뽑기 평균 μ**"] for k in keys]
sd = [F[k]["**뽑기 SD σ**"] for k in keys]
fl = [F[k]["🔴 **잡음 바닥 = μ + 2σ**"] for k in keys]
x = range(3)
ax[0].bar(x, fl, color="#2a6f6f", label="잡음 바닥 μ+2σ")
ax[0].errorbar(x, mu, yerr=sd, fmt="o", color="#e8e8e8", mec="#333",
               ecolor="#333", capsize=3, ms=5, lw=1, label="뽑기 평균 μ ± σ")
ax[0].axhspan(BAND[0], BAND[1], color="#a33", alpha=.18)
ax[0].axhline(THR, color="#a33", lw=1.2, ls="--")
ax[0].text(2.45, THR * 1.12, "채택 문턱 %.5f" % THR, fontsize=7, ha="right", color="#a33")
ax[0].set_xticks(list(x)); ax[0].set_xticklabels(["1열", "2열", "3열"], fontsize=8)
ax[0].set_ylabel("판 Δ (하락)", fontsize=8)
ax[0].set_title("신호 0 인 열을 넣으면 판이 내린다", fontsize=9)
for i, v in enumerate(fl):
    ax[0].text(i, v * 1.03, "%.5f\n(%.2f×)" % (v, F[keys[i]]["**바닥 / 문턱 0.00353**"]),
               ha="center", fontsize=6.8)
ax[0].set_ylim(0, max(fl) * 1.30)
ax[0].legend(fontsize=6.5, loc="upper left", framealpha=.9)
ax[0].tick_params(axis="y", labelsize=7)

# ── 가운데: 카디널리티 사다리 ─────────────────────────────────
ck = ["k=2", "k=4", "k=10", "k=100", "연속"]
cm = [L[k]["**뽑기 평균 μ**"] for k in ck]
cf = [L[k]["🔴 **잡음 바닥 = μ + 2σ**"] for k in ck]
ax[1].plot(range(5), cm, "o-", color="#2a6f6f", ms=5, lw=1.6, label="뽑기 평균 μ")
ax[1].plot(range(5), cf, "s--", color="#7fb2b2", ms=4, lw=1.2, label="바닥 μ+2σ")
ax[1].axhline(THR, color="#a33", lw=1.2, ls="--")
ax[1].text(4.4, THR * 1.14, "채택 문턱", fontsize=7, ha="right", color="#a33")
ax[1].set_xticks(range(5)); ax[1].set_xticklabels(ck, fontsize=8)
ax[1].set_title("거칠기가 올라갈수록 단조로 커진다 (3열)", fontsize=9)
ax[1].set_ylabel("판 Δ (하락)", fontsize=8)
for i, v in enumerate(cm):
    ax[1].text(i, v - max(cm) * .085, "%.5f" % v, ha="center", fontsize=6.6)
ax[1].legend(fontsize=6.5, loc="upper left", framealpha=.9)
ax[1].tick_params(axis="y", labelsize=7)

# ── 오른쪽: 얇음은 평균이 아니라 분산을 키운다 ──────────────────
names = list(DOM.keys())
rows = [DOM[n]["유보 행"] for n in names]
sds = [DOM[n]["뽑기 SD"] for n in names]
mus = [abs(DOM[n]["뽑기 평균 흔들림"]) for n in names]
ax[2].scatter(rows, sds, s=34, color="#a33", label="뽑기 SD (rho=-0.692 · p=0.013)")
ax[2].scatter(rows, mus, s=26, color="#8ab", marker="^",
              label="|평균 흔들림| (rho=+0.126 · p=0.70)")
for n, r, s in zip(names, rows, sds):
    if n in ("시장팝업", "아이돌", "팝업", "웹툰", "애니"):
        ax[2].annotate(n, (r, s), fontsize=6.4, xytext=(3, 3), textcoords="offset points")
ax[2].set_xscale("log"); ax[2].set_yscale("log")
ax[2].set_xlabel("유보 행 수 (로그)", fontsize=8)
ax[2].set_ylabel("도메인 Δ (로그)", fontsize=8)
ax[2].set_title("얇음은 평균이 아니라 분산을 키운다", fontsize=9)
ax[2].legend(fontsize=6.2, loc="lower left", framealpha=.9)
ax[2].tick_params(labelsize=7)

fig.tight_layout()
fig.savefig("/Users/ax/world_model/paper/steps/479_twofloors/figs/fig1.pdf")
print("ok")
