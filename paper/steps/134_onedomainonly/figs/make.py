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

# 도메인, 유보, 빌림(F6), 짝SE(F6), t(F6)
R = [("도서", 163, 0.1143, 0.0302, -3.79), ("펀딩", 80, 0.0474, 0.0311, -1.53),
     ("애니", 606, 0.0017, 0.0062, -0.26), ("웹툰", 711, -0.0019, 0.0040, 0.47),
     ("게임", 180, -0.0027, 0.0057, 0.47), ("세계애니", 300, -0.0051, 0.0150, 0.34),
     ("모바일", 441, -0.0069, 0.0036, 1.91), ("아이돌", 25, -0.0242, 0.0338, 0.72)]

ax = axes[0]
y = np.arange(len(R))[::-1]
for yy, (nm, n, b, se, t) in zip(y, R):
    c = RED if abs(t) > 2.77 else GRY
    ax.errorbar(b, yy, xerr=2 * se, fmt="o", color=c, ms=5.0, capsize=3.2,
                lw=1.6, zorder=3)
    ax.text(0.203, yy, f"$t{{=}}${t:+.2f}", va="center", ha="right",
            fontsize=6.9, color=c, weight=("bold" if abs(t) > 2.77 else "normal"))
ax.axvline(0, color=INK, lw=.9, zorder=2)
ax.set_yticks(y); ax.set_yticklabels([f"{r[0]} ({r[1]})" for r in R], fontsize=7.3)
ax.set_xlim(-0.10, 0.245)
ax.set_xlabel("빌린 양 (rho, $\\pm$2$\\times$짝SE) --- F6 로 잼", fontsize=7.6)
ax.tick_params(axis="x", labelsize=6.9)
ax.set_title("문턱을 넘는 것은 도서 하나다", fontsize=8.6, pad=8)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.grid(axis="x", lw=.4, color="#e3e3e3", zorder=0)
ax.set_ylim(-0.95, 7.9)
ax.text(-0.098, -0.85, "괄호는 유보 행 수 · 문턱 $|t|{>}2.77$", fontsize=6.6,
        color=GRY)

# --- 오른쪽: 정식화 넷에서 도서와 펀딩 ---------------------------------
ax = axes[1]
F = [("F6", -3.79, -1.53), ("F9", -3.45, None), ("F21", -3.30, None),
     ("F18", -2.64, -2.00)]
x = np.arange(len(F)); w = 0.36
for xx, (nm, dt, pt) in zip(x, F):
    ax.bar(xx - w/2, -dt, w, color=(RED if -dt > 2.77 else GRY), zorder=3)
    ax.text(xx - w/2, -dt + 0.08, f"{-dt:.2f}", ha="center", fontsize=6.8,
            color=(RED if -dt > 2.77 else GRY))
    if pt is not None:
        ax.bar(xx + w/2, -pt, w, color=BLU, alpha=.55, zorder=3)
        ax.text(xx + w/2, -pt + 0.08, f"{-pt:.2f}", ha="center", fontsize=6.8,
                color=BLU)
    else:
        ax.text(xx + w/2, 0.12, "안 쟀다", ha="center", fontsize=6.2,
                color=GRY, rotation=90, va="bottom")
ax.axhline(2.77, color=INK, lw=1.1, ls="--", zorder=4)
ax.text(-0.55, 2.87, "문턱 2.77", fontsize=6.8, color=INK, ha="left")
ax.set_xticks(x); ax.set_xticklabels([f[0] for f in F], fontsize=8.0)
ax.set_ylim(0, 4.5); ax.set_xlim(-0.6, 3.6)
ax.set_ylabel("$|t|$", fontsize=8)
ax.tick_params(axis="y", labelsize=7.0)
ax.set_title("도서는 셋에서 넘고 펀딩은 어디서도 못 넘는다", fontsize=8.2, pad=8)
hs = [plt.Rectangle((0,0),1,1,color=RED), plt.Rectangle((0,0),1,1,color=BLU, alpha=.55)]
ax.legend(hs, ["도서", "펀딩"], fontsize=6.9, frameon=False, loc="upper right",
          ncol=2)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(axis="y", lw=.4, color="#e3e3e3", zorder=0)

fig.suptitle("확실한 것은 도메인 하나다", fontsize=10.4, y=1.03)
fig.savefig(D / "one.pdf", bbox_inches="tight")
fig.savefig(D / "one.png", dpi=150, bbox_inches="tight")
print("ok")
