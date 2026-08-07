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
                         gridspec_kw={"width_ratios": [1.12, 1], "wspace": 0.42})

# 이름, 전체 t, 상위5 뺀 t, 이김:짐, 짝 로그비 중앙
R = [("신호 · 내용", -0.59, None, "20:15", 0.0000),
     ("신호 · 모양", +2.52, +1.09, "25:21", 0.0747),
     ("피처 · 내용", +2.21, +0.60, "21:21", 0.0000),
     ("피처 · 모양", -1.21, None, "17:20", 0.0000)]

ax = axes[0]
y = np.arange(len(R))[::-1]
for yy, (nm, t, t5, wl, med) in zip(y, R):
    c = BLU if abs(t) > 2.0 else GRY
    ax.barh(yy + 0.16, abs(t), height=.3, color=c, zorder=3)
    ax.text(abs(t) + 0.05, yy + 0.16, f"{t:+.2f}", va="center", fontsize=6.9,
            color=c)
    if t5 is not None:
        ax.barh(yy - 0.16, abs(t5), height=.3, color=RED, alpha=.7, zorder=3)
        ax.text(abs(t5) + 0.05, yy - 0.16, f"{t5:+.2f}", va="center",
                fontsize=6.9, color=RED)
ax.axvline(2.24, color=INK, lw=1.1, ls="--", zorder=4)
ax.text(2.30, 3.62, "사전 등록 문턱 2.24", fontsize=6.7, color=INK)
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in R], fontsize=7.6)
ax.set_xlim(0, 3.5)
ax.set_xlabel("$|t|$", fontsize=8)
ax.tick_params(axis="x", labelsize=7.0)
ax.set_title("문턱을 넘은 둘이 다섯 건을 빼면 무너진다", fontsize=8.4, pad=8)
hs = [plt.Rectangle((0, 0), 1, 1, color=BLU),
      plt.Rectangle((0, 0), 1, 1, color=RED, alpha=.7)]
ax.legend(hs, ["전체 47짝", "상위 5건 뺀 42짝"], fontsize=6.6,
          frameon=False, loc="lower right", bbox_to_anchor=(1.0, 0.02))
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.grid(axis="x", lw=.4, color="#e3e3e3", zorder=0)
ax.set_ylim(-0.85, 3.95)
ax.text(0.03, -0.78, "짝 승패(이김:짐)  신호 내용 20:15 · 모양 25:21 | "
        "피처 내용 21:21 · 모양 17:20", fontsize=6.3, color=GRY)

# --- 오른쪽: 다섯 건이 무엇인가 ----------------------------------------
ax = axes[1]
T = [("MKT-2025-0011", 0.000, 0.700), ("MKT-2023-0038", 0.000, 0.250),
     ("MKT-2025-0093", 0.000, 0.200), ("MKT-2025-0095", 0.000, 0.200),
     ("MKT-2025-0111", 0.000, 0.175)]
x = np.arange(len(T)); w = 0.36
ax.bar(x - w/2, [t[1] for t in T], w, color=BLU, label="진짜 팔 APE", zorder=3)
ax.bar(x + w/2, [t[2] for t in T], w, color=RED, label="위약 팔 APE", zorder=3)
for xx, t in zip(x, T):
    ax.text(xx - w/2, 0.012, "0.000", ha="center", fontsize=6.2, color=BLU,
            rotation=90, va="bottom")
    ax.text(xx + w/2, t[2] + 0.012, f"{t[2]:.3f}", ha="center", fontsize=6.3,
            color=RED)
ax.set_xticks(x)
ax.set_xticklabels([t[0].replace("MKT-", "") for t in T], fontsize=6.5,
                   rotation=30, ha="right")
ax.set_ylim(0, 0.82)
ax.set_ylabel("APE", fontsize=8)
ax.tick_params(axis="y", labelsize=7.0)
ax.set_title("다섯 건 다 진짜 팔이 정확히 0 이다", fontsize=8.4, pad=8)
ax.legend(fontsize=6.7, frameon=False, loc="upper right")
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(axis="y", lw=.4, color="#e3e3e3", zorder=0)
ax.text(-0.5, 0.865, "완충 0.05 가 $\\log\\frac{0.70+0.05}{0+0.05}{=}2.71$ 을 만든다",
        fontsize=6.6, color=INK)
ax.set_ylim(0, 0.94)

fig.suptitle("다섯 건이 답을 정하고 있었다", fontsize=10.4, y=1.03)
fig.savefig(D / "twice.pdf", bbox_inches="tight")
fig.savefig(D / "twice.png", dpi=150, bbox_inches="tight")
print("ok")
