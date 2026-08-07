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
                         gridspec_kw={"width_ratios": [1.1, 1], "wspace": 0.42})

# --- 왼쪽: 축이 실제로 가진 값 vs 펼쳐진 값 ------------------------------
ax = axes[0]
AX = [("target_breadth", 2), ("goods_scale", 3), ("entry_friction", 4),
      ("venue_prominence", 6)]
y = np.arange(len(AX))[::-1]
for yy, (nm, n) in zip(y, AX):
    ax.barh(yy, 205, height=.52, color=RED, alpha=.30, zorder=2)
    ax.barh(yy, n, height=.52, color=GRN, zorder=3)
    ax.text(n + 4, yy, f"{n}", va="center", fontsize=7.6, color=GRN)
ax.text(196, len(AX) - 1, "205", fontsize=7.6, color=RED,
        ha="right", va="center")
ax.set_yticks(y); ax.set_yticklabels([a[0] for a in AX], fontsize=7.2)
ax.set_xlim(0, 232)
ax.tick_params(axis="x", labelsize=7.2)
ax.set_xlabel("축이 가진 서로 다른 값", fontsize=7.8, labelpad=2)
ax.set_title("초록 = 진짜 · 붉은 = 펼쳐진 것", fontsize=9.4, pad=6)
ax.text(58, 0.05, "argsort 가 동률을 행 순서로 깼다\n행 순서는 연도와 $+$0.864",
        fontsize=6.9, color=RED)

# --- 오른쪽: 고치니 좋아졌다 --------------------------------------------
ax = axes[1]
B = [("고치기 전\n(노트 284)", 0.1970, 2.02, GRY),
     ("고친 뒤", 0.4051, 4.30, GRN)]
x = np.arange(2)
for xx, (nm, r, z, c) in zip(x, B):
    ax.bar(xx, r, color=c, width=.46, zorder=3)
    ax.text(xx, r + .014, f"{r:.4f}", ha="center", fontsize=8.4, color=c)
    ax.text(xx, r / 2, f"z={z:.2f}", ha="center", fontsize=8.0, color="white",
            weight="bold")
ax.set_xticks(x); ax.set_xticklabels([b[0] for b in B], fontsize=7.6)
ax.set_ylim(0, 0.53)
ax.tick_params(axis="y", labelsize=7.2)
ax.set_ylabel("시장팝업 rho (유보 104행)", fontsize=7.8)
ax.set_title("인공물이 돕는 게 아니라 해치고 있었다", fontsize=9.2, pad=6)
ax.text(-0.44, 0.498, "치환 귀무 대비 · p 0.045 $\\to$ $<$0.001", fontsize=6.9,
        color=INK)
fig.suptitle("잡음을 넣으면 점수가 오르지 않는다 --- 내려간다",
             fontsize=10.4, y=1.005)
fig.subplots_adjust(left=.155, right=.985, top=.795, bottom=.175)
fig.savefig(D / "tie.pdf"); plt.close(fig)
print("ok")
