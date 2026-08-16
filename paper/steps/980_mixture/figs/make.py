# -*- coding: utf-8 -*-
"""노트 980 figure — **모형이 보는 행은 자료가 아니라 상수가 정한다**.

🔴 자료를 저장소 산출물에서 **직접 읽는다**(하드코딩 금지 · `paper/figs.py` 규약 · 규칙 D).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, "/Users/ax/world_model")
import numpy as np                                            # noqa: E402
from paper.figs import plt, FULL, INK, GATE, CLAIM, MUTE      # noqa: E402

ROOT = Path("/Users/ax/world_model")
HERE = Path(__file__).resolve().parent
B = json.loads((ROOT / "runners/out980_budget.json").read_text(encoding="utf-8"))
M = json.loads((ROOT / "runners/out980_mixarm.json").read_text(encoding="utf-8"))
F = json.loads((ROOT / "runners/out980_funnel.json").read_text(encoding="utf-8"))

grid = B["🔴 격자"]
cells = B["🔴🔴 칸"]
KEY = "λ u=3"
nh = np.array([cells["N_B=%d" % n][KEY]["🔴 겹당 hplt 학습 행 ㉯"] for n in grid], float)
rc = np.array([cells["N_B=%d" % n][KEY]["🔴 ㉯ 대조 ρ(정본 자)"] for n in grid], float)
rs = np.array([cells["N_B=%d" % n][KEY]["🔴 ㉮ 층화 ρ(정본 자)"] for n in grid], float)
se = np.array([cells["N_B=%d" % n][KEY]["🔴🔴 Δ = ㉮ − ㉯"]["🔴🔴 짝 SE(5 벌 정합)"]
               for n in grid], float)
dl = np.array([cells["N_B=%d" % n][KEY]["🔴🔴 Δ = ㉮ − ㉯"]["Δ"] for n in grid], float)
bound = np.array([len(cells["N_B=%d" % n]["🔴🔴 공급에 묶인 도메인"]) for n in grid])
n_reg = F["🔴🔴 깔때기"]["④ 🔴🔴 모형이 보는 hplt 학습 행"]

fig, (ax, ax2) = plt.subplots(1, 2, figsize=(FULL, 2.6),
                              gridspec_kw={"width_ratios": [1.1, 1]})

ax.plot(nh, rc, "o-", color=GATE, lw=1.4, ms=4, label="㉯ 대조 — 순열 앞머리")
ax.plot(nh, rs, "s--", color=CLAIM, lw=1.4, ms=4, label="㉮ 처리 — 도메인 층화")
ax.axvline(n_reg, color=INK, lw=0.9, ls=":")
ax.annotate("현행 예산 %d 행\n(자료가 아니라 `N_B` 상수)" % n_reg,
            xy=(n_reg, ax.get_ylim()[0]), xytext=(n_reg * 1.25, rc.min()),
            fontsize=6.4, color=INK)
ax.set_xscale("log")
ax.set_xlabel("겹당 hplt 학습 행 수 (log)", fontsize=7.5)
ax.set_ylabel(r"유보 $\rho$ (정본 자)", fontsize=7.5)
ax.set_title("예산을 16 배로 늘리면 대조가 층화를 따라잡는다\n"
             "— 1,710 은 곡선의 **평평한 곳이 아니다**", fontsize=8.2, loc="left")
ax.legend(fontsize=6.4, frameon=False, loc="lower right")
ax.tick_params(labelsize=6.6)

y = np.arange(len(grid))
col = [CLAIM if d - 2 * s > 0 else (GATE if d > 0 else MUTE)
       for d, s in zip(dl, se)]
ax2.barh(y, dl, xerr=2 * se, color=col, height=0.6,
         error_kw={"lw": 0.9, "ecolor": "0.35"})
ax2.axvline(0, color=INK, lw=0.9)
ax2.set_yticks(y)
ax2.set_yticklabels(["%s 행 · 묶인 도메인 %d" % ("{:,}".format(int(v)), b)
                     for v, b in zip(nh, bound)], fontsize=6.3)
ax2.invert_yaxis()
ax2.set_xlabel(r"$\Delta = $ 층화 $-$ 대조   (막대는 $\pm 2$ 짝SE)", fontsize=7.5)
ax2.set_title("혼합을 맞춘 이득은 **작은 예산에서만** 산다\n"
              "— 공급이 묶이기 시작하면 사라진다", fontsize=8.2, loc="left")
ax2.tick_params(labelsize=6.4)

fig.tight_layout()
fig.savefig(HERE / "budget.pdf", bbox_inches="tight")
print("wrote", HERE / "budget.pdf")
