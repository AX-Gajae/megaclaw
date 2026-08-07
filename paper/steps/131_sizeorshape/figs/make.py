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
AMB = "#b07a3a"
# 도메인, 학습행, 빌린 양, t, '새롭다' 개수
R = [("웹툰", 2106, 0.0773, -2.27, 6), ("애니", 1467, 0.0587, -2.03, 6),
     ("만화", 1783, 0.0491, -1.93, 3), ("모바일", 1559, 0.0341, -1.65, 3),
     ("시장팝업", 101, 0.0222, -1.15, 0), ("게임", 259, 0.0217, -0.88, 3),
     ("세계애니", 2648, 0.0125, -0.61, 0), ("아이돌", 54, 0.0106, -0.39, 2)]
COL = {6: GRN, 3: BLU, 2: AMB, 0: RED}

fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.35),
                         gridspec_kw={"width_ratios": [1, 1.1], "wspace": 0.40})

# --- 왼쪽: 크기 대 빌린 양 ---------------------------------------------
ax = axes[0]
for nm, n, b, t, f in R:
    ax.scatter(n, b, s=54, color=COL[f], zorder=3,
               edgecolor="white", linewidth=.8)
    dx, dy = (7, 4)
    if nm == "세계애니": dx, dy = (-8, -14)
    if nm == "만화": dx, dy = (7, -3)
    ax.annotate(nm, (n, b), textcoords="offset points", xytext=(dx, dy),
                fontsize=6.8, color=INK)
ax.set_xscale("log")
ax.set_xlabel("뺀 도메인의 학습행 (로그)", fontsize=7.8)
ax.set_ylabel("도서가 그 도메인에서 빌린 양 (rho)", fontsize=7.8)
ax.tick_params(labelsize=6.9)
ax.set_ylim(0, 0.093)
ax.set_title("크기로는 안 맞는다 --- $\\rho{=}{+}0.405$ ($p{=}0.32$)",
             fontsize=8.4, pad=8)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(lw=.4, color="#e3e3e3", zorder=0)
hs = [plt.Line2D([], [], marker="o", ls="", color=COL[k], ms=6) for k in (6, 3, 2, 0)]
ax.legend(hs, ["새롭다 6", "3", "2", "0"], fontsize=6.5, frameon=False,
          loc="upper left", ncol=2, title="그 축이 그 도메인에서",
          title_fontsize=6.3)

# --- 오른쪽: '새롭다' 대 빌린 양 ---------------------------------------
ax = axes[1]
groups = [(6, ["웹툰", "애니"]), (3, ["만화", "모바일", "게임"]),
          (2, ["아이돌"]), (0, ["시장팝업", "세계애니"])]
x = np.arange(len(groups))
by = {r[0]: r for r in R}
for xx, (k, doms) in zip(x, groups):
    vals = [by[d][2] for d in doms]
    ax.bar(xx, np.mean(vals), 0.52, color=COL[k], zorder=3)
    for v, d in zip(vals, doms):
        ax.scatter(xx, v, s=22, color="white", edgecolor=INK, linewidth=.8,
                   zorder=4)
        ax.text(xx + 0.30, v, d, fontsize=6.2, va="center", color=INK)
    ax.text(xx, max(max(vals), np.mean(vals)) + 0.006, f"{np.mean(vals):.4f}",
            ha="center", fontsize=7.4, color=COL[k])
ax.set_xticks(x); ax.set_xticklabels([f"새롭다 {k}" for k, _ in groups], fontsize=7.6)
ax.set_ylim(0, 0.098); ax.set_xlim(-0.55, 3.9)
ax.set_ylabel("빌린 양 (rho)", fontsize=7.8)
ax.tick_params(axis="y", labelsize=6.9)
ax.set_title("닮음으로는 맞는다 --- $\\rho{=}{+}0.803$ ($p{=}0.016$)",
             fontsize=8.4, pad=8)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(axis="y", lw=.4, color="#e3e3e3", zorder=0)
ax.annotate("세계애니는 학습 2,648행으로 제일 큰데\n빌려 주는 것은 웹툰의 6분의 1",
            xy=(3.12, 0.0125), xytext=(1.35, 0.065), fontsize=6.5, color=RED,
            arrowprops=dict(arrowstyle="->", lw=.8, color=RED,
                            connectionstyle="arc3,rad=-0.25"))

fig.suptitle("큰 데서 빌리는 게 아니라 닮은 데서 빌린다", fontsize=10.4, y=1.03)
fig.savefig(D / "whom.pdf", bbox_inches="tight")
fig.savefig(D / "whom.png", dpi=150, bbox_inches="tight")
print("ok")
