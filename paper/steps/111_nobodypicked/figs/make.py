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

GRN, RED, GRY, INK = "#2f6f4f", "#a33b3b", "#9aa0a8", "#3b3b3b"
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.2),
                         gridspec_kw={"width_ratios": [1.15, 1], "wspace": 0.42})

# --- 왼쪽: 표지가 할 수 있는 것과 실제로 한 것 ---------------------------
ax = axes[0]
B = [("표지 하나로\n낼 수 있는 값", 0.4157, RED),
     ("표지를 지웠을 때\n실제로 잃는 값", 0.0033, GRY)]
x = np.arange(2)
for xx, (nm, v, c) in zip(x, B):
    ax.bar(xx, v, color=c, width=.46, zorder=3)
    ax.text(xx, v + .012, f"{v:.4f}", ha="center", fontsize=8.4, color=c)
ax.set_xticks(x); ax.set_xticklabels([b[0] for b in B], fontsize=7.6)
ax.set_ylim(0, 0.50)
ax.tick_params(axis="y", labelsize=7.2)
ax.set_ylabel("유보 |rho| (팝업)", fontsize=7.8)
ax.set_title("놓여 있었는데 아무도 안 주웠다", fontsize=9.4, pad=6)
ax.annotate("", xy=(1, 0.055), xytext=(0, 0.40),
            arrowprops=dict(arrowstyle="->", color=INK, lw=1.2,
                            connectionstyle="arc3,rad=-.25"))
ax.text(0.52, 0.28, "126배", fontsize=8.4, color=INK, ha="center")

# --- 오른쪽: 세 수의 분해 ------------------------------------------------
ax = axes[1]
R = [("그대로\n유보 116", 0.3582, GRY),
     ("표지 지움\n유보 116", 0.3549, GRY),
     ("같은 유보 65\n시장 학습 포함", 0.3952, GRN),
     ("같은 유보 65\n시장 학습 뺌", 0.3980, GRN)]
y = np.arange(len(R))[::-1]
for yy, (nm, v, c) in zip(y, R):
    ax.barh(yy, v, color=c, height=.54, zorder=3, alpha=.85)
    ax.text(v + .008, yy, f"{v:.4f}", va="center", fontsize=7.6, color=c)
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in R], fontsize=7.0)
ax.set_xlim(0, 0.50)
ax.tick_params(axis="x", labelsize=7.2)
ax.set_xlabel("팝업 rho", fontsize=7.8, labelpad=2)
ax.set_title("차이는 전부 채점 대상이다", fontsize=9.4, pad=6)
ax.plot([0.455, 0.455], [2.75, 2.25], "-", color=GRY, lw=1.4)
ax.text(0.462, 2.5, "$-$0.0033", fontsize=6.9, color=GRY, va="center")
ax.plot([0.455, 0.455], [0.75, 0.25], "-", color=GRN, lw=1.4)
ax.text(0.462, 0.5, "$+$0.0028", fontsize=6.9, color=GRN, va="center")
fig.suptitle("누출이 있어도 쓰지 않으면 점수에 안 나온다", fontsize=10.4,
             y=1.005)
fig.subplots_adjust(left=.108, right=.955, top=.795, bottom=.185)
fig.savefig(D / "picked.pdf"); plt.close(fig)
print("ok")
