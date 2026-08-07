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
                         gridspec_kw={"width_ratios": [1.12, 1], "wspace": 0.42})

# --- 왼쪽: 세 비교 ------------------------------------------------------
ax = axes[0]
C = [("진짜 대 위약\n(내용의 값)", -0.0763, 0.1302, -0.59, RED),
     ("위약 대 제거\n(모양의 값)", +0.2843, 0.1129, +2.52, GRN),
     ("진짜 대 제거\n(둘의 합)", +0.2080, 0.0902, +2.30, GRY)]
y = np.arange(len(C))[::-1]
for yy, (nm, e, se, t, c) in zip(y, C):
    ax.errorbar(e, yy, xerr=1.96 * se, fmt="o", color=c, ms=5.6, capsize=3.6,
                lw=1.7, zorder=3)
    ax.text(e + 1.96 * se + 0.02, yy, f"$t{{=}}${t:+.2f}", va="center",
            fontsize=7.6, color=c)
ax.axvline(0, color=INK, lw=.9, zorder=2)
ax.set_yticks(y); ax.set_yticklabels([c[0] for c in C], fontsize=7.4)
ax.set_xlim(-0.36, 0.68)
ax.set_xlabel("기준팔이 더 나은 배수 (log · 사전 등록한 척도)", fontsize=7.6)
ax.tick_params(axis="x", labelsize=6.9)
ax.set_title("내용을 부수어도 이득이 안 준다", fontsize=8.6, pad=8)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.grid(axis="x", lw=.4, color="#e3e3e3", zorder=0)
ax.set_ylim(-1.15, 2.85)
ax.text(-0.35, -0.88, "사전 등록 문턱 $|t|{>}2.24$ · $n{=}47$ 짝",
        fontsize=6.9, color=INK)

# --- 오른쪽: 세 팔의 APE ------------------------------------------------
ax = axes[1]
A = [("진짜\n신호 그대로", 0.4000, 3.1420, GRY),
     ("위약\n섞은 신호", 0.4444, 3.1498, GRN),
     ("제거\n신호 없음", 0.5200, 4.1445, RED)]
x = np.arange(len(A))
for xx, (nm, med, mean, c) in zip(x, A):
    ax.bar(xx, med, color=c, width=.55, zorder=3)
    ax.text(xx, med + 0.012, f"{med:.3f}", ha="center", fontsize=8.0, color=c)
    ax.text(xx, -0.052, f"평균 {mean:.2f}", ha="center", fontsize=6.5, color=GRY)
ax.set_xticks(x); ax.set_xticklabels([a[0] for a in A], fontsize=7.2)
ax.set_ylim(-0.085, 0.60)
ax.set_ylabel("APE 중앙값", fontsize=8)
ax.tick_params(axis="y", labelsize=7.0)
ax.set_title("진짜와 위약이 같고 제거만 나쁘다", fontsize=8.6, pad=8)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(axis="y", lw=.4, color="#e3e3e3", zorder=0)
ax.annotate("", xy=(1.0, 0.545), xytext=(0.0, 0.545),
            arrowprops=dict(arrowstyle="<->", lw=.9, color=GRN))
ax.text(0.5, 0.556, "차이 없음", ha="center", fontsize=6.8, color=GRN)

fig.suptitle("섞어도 똑같이 듣는다", fontsize=10.4, y=1.03)
fig.savefig(D / "placebo.pdf", bbox_inches="tight")
fig.savefig(D / "placebo.png", dpi=150, bbox_inches="tight")
print("ok")
