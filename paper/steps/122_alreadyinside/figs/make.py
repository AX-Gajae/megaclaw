import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import paper.figs  # noqa: F401,E402
matplotlib.rcParams["axes.unicode_minus"] = False
D = Path(__file__).resolve().parent

GRN, RED, GRY, INK, BLU = "#2f6f4f", "#a33b3b", "#9aa0a8", "#3b3b3b", "#33628f"
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.3),
                         gridspec_kw={"width_ratios": [1.05, 1], "wspace": 0.44})

# --- 왼쪽: 카테고리별 일평균 -------------------------------------------
ax = axes[0]
C = [("game_webtoon", 4264, 10), ("character", 2659, 14), ("beauty", 2408, 12),
     ("electronics", 1643, 5), ("other", 1543, 16), ("entertainment", 1154, 9),
     ("fnb", 1094, 13), ("fashion", 966, 19)]
y = np.arange(len(C))[::-1]
for yy, (nm, v, n) in zip(y, C):
    ax.barh(yy, v, height=.6, color=(BLU if v > 2000 else GRY), zorder=3)
    ax.text(v + 90, yy, f"{v:,}", va="center", fontsize=7.0, color=INK)
    ax.text(-120, yy, f"n{n}", va="center", ha="right", fontsize=6.4, color=GRY)
ax.set_yticks(y); ax.set_yticklabels([c[0] for c in C], fontsize=7.2)
ax.set_xlim(-700, 5400); ax.set_xlabel("일평균 방문 중앙값 (학습 101행)", fontsize=7.8)
ax.tick_params(axis="x", labelsize=6.8)
ax.set_title("카테고리는 네 배 반으로 가른다", fontsize=8.6, pad=8)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.grid(axis="x", lw=.4, color="#e3e3e3", zorder=0)
ax.text(5300, -0.95, "크루스칼 $H{=}18.4$ · $p{=}0.010$", fontsize=7.0,
        color=BLU, ha="right")
ax.set_ylim(-1.3, 7.7)

# --- 오른쪽: 채택 검사 셋 ----------------------------------------------
ax = axes[1]
T = [("① 혼자서 가르나", 0.0103, True),
     ("② target_breadth 와 겹치나", 0.0044, True),
     ("② venue_prominence 와 겹치나", 0.0134, True),
     ("③ 다섯을 통제하고도 남나", 0.1176, False)]
y2 = np.arange(len(T))[::-1]
for yy, (nm, p, sig) in zip(y2, T):
    c = BLU if yy == 3 else (RED if yy in (1, 2) else GRN)
    if yy == 0:
        c = RED
    ax.barh(yy, -np.log10(p), height=.55,
            color=(BLU if yy == 3 else (GRY if yy in (1, 2) else RED)), zorder=3)
    ax.text(-np.log10(p) + 0.05, yy, f"$p{{=}}${p:.4f}", va="center",
            fontsize=7.2, color=INK)
ax.axvline(-np.log10(0.05), color=INK, lw=1.0, ls="--", zorder=4)
ax.text(-np.log10(0.05) + 0.04, 3.55, "$p{=}0.05$", fontsize=6.8, color=INK)
ax.set_yticks(y2); ax.set_yticklabels([t[0] for t in T], fontsize=7.0)
ax.set_xlabel("$-\\log_{10} p$", fontsize=7.8)
ax.set_xlim(0, 3.4)
ax.tick_params(axis="x", labelsize=6.8)
ax.set_title("겹치고, 통제하면 안 남는다", fontsize=8.6, pad=8)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.grid(axis="x", lw=.4, color="#e3e3e3", zorder=0)
ax.set_ylim(-1.05, 3.95)
ax.text(0.0, -0.85, "그래서 노트 285의 mkt_cat $+$0.0048($t{=}0.12$)이 설명된다",
        fontsize=6.8, color=INK)

fig.suptitle("제일 잘 가르는 것이 이미 판 안에 있었다", fontsize=10.4, y=1.03)
fig.savefig(D / "inside.pdf", bbox_inches="tight")
fig.savefig(D / "inside.png", dpi=150, bbox_inches="tight")
print("ok")
