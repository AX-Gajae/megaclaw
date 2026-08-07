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
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.35),
                         gridspec_kw={"width_ratios": [1.15, 1], "wspace": 0.44})

# 축, 빌림, 짝SE, t
R = [("trend_level", 0.0681, 0.0289, -2.35), ("trend_momentum", 0.0509, 0.0293, -1.74),
     ("cal_month_sin", 0.0056, 0.0040, -1.38), ("cal_dow_sin", 0.0021, 0.0028, -0.77),
     ("cal_holiday_gap", -0.0011, 0.0037, 0.29), ("cal_dow_cos", -0.0011, 0.0050, 0.21),
     ("cal_weekend", -0.0012, 0.0077, 0.15), ("cal_month_cos", -0.0082, 0.0035, 2.37),
     ("trend_volatility", -0.0222, 0.0157, 1.41)]

ax = axes[0]
y = np.arange(len(R))[::-1]
for yy, (nm, b, se, t) in zip(y, R):
    c = BLU if nm.startswith("trend_") else GRY
    ax.errorbar(b, yy, xerr=2 * se, fmt="o", color=c, ms=4.6, capsize=3,
                lw=1.4, zorder=3)
ax.axvline(0, color=INK, lw=.9, zorder=2)
ax.set_yticks(y)
ax.set_yticklabels([r[0] for r in R], fontsize=6.9)
for lb, c in zip(ax.get_yticklabels(), [BLU if r[0].startswith("trend_") else GRY for r in R]):
    lb.set_color(c)
ax.set_xlim(-0.065, 0.135)
ax.set_xlabel("도서가 그 축에서 빌린 양 ($\\pm$2$\\times$짝SE)", fontsize=7.6)
ax.tick_params(axis="x", labelsize=6.8)
ax.set_title("낱개로는 아무것도 문턱을 못 넘는다", fontsize=8.5, pad=8)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.grid(axis="x", lw=.4, color="#e3e3e3", zorder=0)
ax.set_ylim(-0.9, 8.9)
ax.text(-0.063, -0.82, "파랑 = 검색 · 회색 = 달력", fontsize=6.7, color=INK)

# --- 오른쪽: 계열로 묶으면 --------------------------------------------
ax = axes[1]
G = [("검색 셋", 0.1132, 0.0326, -3.48, BLU),
     ("달력 여섯", -0.0051, 0.0093, 0.55, GRY),
     ("아홉 다", 0.1143, 0.0302, -3.79, GRN)]
x = np.arange(len(G))
for xx, (nm, b, se, t, c) in zip(x, G):
    ax.bar(xx, b, 0.5, color=c, zorder=3)
    ax.errorbar(xx, b, yerr=2 * se, fmt="none", ecolor=INK, capsize=3.6,
                lw=1.1, zorder=4)
    ax.text(xx, b + 2 * se + 0.007, f"{b:+.4f}", ha="center", fontsize=7.6, color=c)
    ax.text(xx, -0.026, f"$t{{=}}${t:+.2f}", ha="center", fontsize=7.0,
            color=(c if abs(t) > 2.77 else GRY))
ax.axhline(0, color=INK, lw=.9, zorder=2)
ax.set_xticks(x); ax.set_xticklabels([g[0] for g in G], fontsize=8.0)
ax.set_ylim(-0.042, 0.215)
ax.set_ylabel("빌린 양 (rho)", fontsize=8)
ax.tick_params(axis="y", labelsize=7.0)
ax.set_title("검색 셋이 전부다", fontsize=8.6, pad=8)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(axis="y", lw=.4, color="#e3e3e3", zorder=0)
ax.text(0.5, 0.185, "낱개 합 $+$0.0930 < 셋 묶음 $+$0.1132", fontsize=6.7,
        color=BLU, ha="center")

fig.suptitle("빌리는 것은 검색이지 달력이 아니다", fontsize=10.4, y=1.03)
fig.savefig(D / "which.pdf", bbox_inches="tight")
fig.savefig(D / "which.png", dpi=150, bbox_inches="tight")
print("ok")
