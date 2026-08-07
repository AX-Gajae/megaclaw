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
R = [("F18", "나무", 0.3895, 0.1263, 0.0478, -2.64, 32),
     ("F8", "나무", 0.3675, 0.1123, 0.0415, -2.71, 31),
     ("F6", "선형", 0.3108, 0.1143, 0.0325, -3.52, 37),
     ("F9", "선형", 0.3055, 0.1045, 0.0303, -3.45, 34),
     ("F21", "선형", 0.3118, 0.1111, 0.0336, -3.30, 36),
     ("F23", "섞음", 0.3754, 0.1350, 0.0430, -3.14, 36)]
COL = {"나무": RED, "선형": BLU, "섞음": AMB}

fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.3),
                         gridspec_kw={"width_ratios": [1.1, 1], "wspace": 0.42})

ax = axes[0]
x = np.arange(len(R))
for xx, (nm, fam, base, b, se, t, sh) in zip(x, R):
    ax.bar(xx, b, 0.55, color=COL[fam], zorder=3)
    ax.errorbar(xx, b, yerr=2 * se, fmt="none", ecolor=INK, capsize=3.4,
                lw=1.1, zorder=4)
    ax.text(xx, b + 2 * se + 0.006, f"{b:.3f}", ha="center", fontsize=7.0,
            color=COL[fam])
    ax.text(xx, -0.016, f"{sh}%", ha="center", fontsize=7.0, color=GRY)
ax.set_xticks(x); ax.set_xticklabels([r[0] for r in R], fontsize=7.8)
ax.set_ylim(-0.028, 0.245)
ax.set_ylabel("도서가 빌린 양 (rho, $\\pm$2$\\times$짝SE)", fontsize=7.8)
ax.tick_params(axis="y", labelsize=7.0)
ax.set_title("여섯이 다 같은 만큼 빌린다", fontsize=8.6, pad=8)
hs = [plt.Rectangle((0, 0), 1, 1, color=COL[k]) for k in ("나무", "선형", "섞음")]
ax.legend(hs, ["나무", "선형", "섞음"], fontsize=6.8, frameon=False,
          loc="upper right", ncol=3)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(axis="y", lw=.4, color="#e3e3e3", zorder=0)
ax.text(0.0, -0.0255, "아래 숫자는 제 점수에서 빌린 몫", fontsize=6.5, color=GRY)

# --- 오른쪽: |t| 와 문턱 -----------------------------------------------
ax = axes[1]
y = np.arange(len(R))[::-1]
for yy, (nm, fam, base, b, se, t, sh) in zip(y, R):
    c = COL[fam]
    ax.barh(yy, -t, height=.56, color=c, zorder=3,
            alpha=(1.0 if -t > 2.77 else .45))
    ax.text(-t + 0.06, yy, f"{-t:.2f}", va="center", fontsize=7.2, color=c)
ax.axvline(2.77, color=INK, lw=1.1, ls="--", zorder=4)
ax.text(2.83, 5.35, "도메인 문턱 2.77", fontsize=6.8, color=INK)
ax.set_yticks(y)
ax.set_yticklabels([f"{r[0]} ({r[1]})" for r in R], fontsize=7.2)
ax.set_xlim(0, 4.3)
ax.set_xlabel("$|t|$", fontsize=8)
ax.tick_params(axis="x", labelsize=7.0)
ax.set_title("문턱을 넘는 것은 선형 셋뿐이다", fontsize=8.6, pad=8)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.grid(axis="x", lw=.4, color="#e3e3e3", zorder=0)
ax.set_ylim(-0.85, 5.9)
ax.text(0.05, -0.75, "선형의 짝SE 가 작아서다 (0.030~0.034 대 나무 0.042~0.048)",
        fontsize=6.6, color=BLU)

fig.suptitle("선형이 더 잘 빌린다", fontsize=10.4, y=1.03)
fig.savefig(D / "pooled.pdf", bbox_inches="tight")
fig.savefig(D / "pooled.png", dpi=150, bbox_inches="tight")
print("ok")
