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

# 이름, 청력, 판40, 판15, 팝업Δ, 팝업짝SE, 무리
R = [("F18_bagboost",   22, 0.4851, 0.4819, +0.0127, 0.0312, "나무"),
     ("F8_boost",       22, 0.4741, 0.4758, -0.0431, 0.0492, "나무"),
     ("F23_rankmix",     0, 0.4848, 0.4778, -0.0027, 0.0229, "섞음"),
     ("F6_directpool",   0, 0.4391, 0.4393, +0.0005, 0.0040, "선형"),
     ("F9_ranklik",      0, 0.4363, 0.4365, +0.0040, 0.0059, "선형"),
     ("F21_recentpick",  0, 0.4457, 0.4459, +0.0049, 0.0057, "선형"),
     ("F10_pershrink", 400, 0.3998, 0.3998,  0.0000, 0.0000, "도메인별"),
     ("F1_procrustes", None, 0.2180, 0.2180, 0.0000, 0.0000, "도메인별")]
COL = {"나무": RED, "섞음": "#b07a3a", "선형": BLU, "도메인별": GRY}

fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.3),
                         gridspec_kw={"width_ratios": [1.15, 1], "wspace": 0.44})

# --- 왼쪽: 팝업 Δρ ± 2×짝SE -------------------------------------------
ax = axes[0]
y = np.arange(len(R))[::-1]
for yy, (nm, th, b40, b15, dd, se, fam) in zip(y, R):
    c = COL[fam]
    if se > 0:
        ax.errorbar(dd, yy, xerr=2 * se, fmt="o", color=c, ms=4.4,
                    capsize=3.0, lw=1.4, zorder=3)
    else:
        ax.plot(dd, yy, "D", color=c, ms=4.4, zorder=3)
        ax.text(dd + 0.006, yy, "정확히 0", va="center", fontsize=6.6, color=c)
ax.axvline(0, color=INK, lw=.9, zorder=2)
ax.set_yticks(y)
ax.set_yticklabels([f"{r[0].split('_')[0]}  청력 {r[1] if r[1] is not None else '?'}"
                    for r in R], fontsize=7.0)
ax.set_xlim(-0.155, 0.115)
ax.set_xlabel("팝업 ρ 의 변화 (문턱 15 - 40) ± 2×짝SE", fontsize=7.8)
ax.tick_params(axis="x", labelsize=7.0)
ax.set_title("여덟 다 0 을 못 벗어난다 --- 그런데 폭이 여덟 배 다르다",
             fontsize=8.4, pad=8)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.grid(axis="x", lw=.4, color="#e3e3e3", zorder=0)
ax.text(-0.148, 6.55, "나무 짝SE 0.023~0.049", fontsize=6.8, color=RED)
ax.text(-0.148, 2.55, "선형 짝SE 0.004~0.006", fontsize=6.8, color=BLU)

# --- 오른쪽: 판이 얼마나 움직이나 ---------------------------------------
ax = axes[1]
y2 = np.arange(len(R))[::-1]
ax.axvspan(-0.010, 0.010, color="#eceff1", zorder=0)
for yy, r in zip(y2, R):
    d = r[3] - r[2]
    c = COL[r[6]] if abs(d) > 1e-9 else GRY
    ax.barh(yy, d, height=.52, color=c, zorder=3)
    ax.text(d + (0.0009 if d >= 0 else -0.0009), yy,
            f"{d:+.4f}", va="center", ha="left" if d >= 0 else "right",
            fontsize=6.6, color=c)
ax.axvline(0, color=INK, lw=.9, zorder=2)
ax.set_yticks(y2)
ax.set_yticklabels([f"{r[0].split('_')[0]}  {r[2]:.4f}" for r in R], fontsize=7.0)
ax.set_xlim(-0.0135, 0.0105)
ax.set_xlabel("판 rho 의 변화 (문턱 15 - 40)", fontsize=7.8)
ax.tick_params(axis="x", labelsize=6.6)
ax.set_title("여덟 다 미결정 띠 안이다", fontsize=8.4, pad=8)
ax.text(0.0, 8.05, "회색 = 판 미결정 띠 $\\pm$0.010", fontsize=6.8,
        color=GRY, ha="center")
ax.text(-0.0128, 2.05, "챔피언은 15 에서 돈다 --- 40 이 $+$0.0032 낫지만\n"
        "짝SE 0.0025 · $t{=}{-}1.24$ · 문턱 0.0051 --- 못 가른다",
        fontsize=6.5, color=INK, va="top")
for s_ in ("top", "right", "left"):
    ax.spines[s_].set_visible(False)
ax.grid(axis="x", lw=.4, color="#e3e3e3", zorder=1)
ax.set_ylim(-0.8, 8.6)

fig.suptitle("열여섯 행은 이득이 아니라 흔들림을 준다", fontsize=10.4, y=1.03)
fig.savefig(D / "sixteen.pdf", bbox_inches="tight")
fig.savefig(D / "sixteen.png", dpi=150, bbox_inches="tight")
print("ok")
