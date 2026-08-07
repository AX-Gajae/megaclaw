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
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.15),
                         gridspec_kw={"width_ratios": [1, 1.1], "wspace": 0.40})

# --- 왼쪽: 두 가지 행 세기 ----------------------------------------------
ax = axes[0]
G = [("좁은 판\n75행", 16, 14), ("넓힌 판\n189행", 73, 17)]
x = np.arange(2); w = 0.36
for xx, (nm, lab, obs) in zip(x, G):
    ax.bar(xx - w / 2, lab, width=w, color=GRY, alpha=.7, zorder=3)
    ax.bar(xx + w / 2, obs, width=w, color=RED, zorder=3)
    ax.text(xx - w / 2, lab + 1.8, f"{lab}", ha="center", fontsize=8.0,
            color=INK)
    ax.text(xx + w / 2, obs + 1.8, f"{obs}", ha="center", fontsize=8.0,
            color=RED)
ax.axhline(22, color=INK, lw=1.3, ls="--", zorder=4)
ax.text(1.52, 24, "청력 문턱 22", fontsize=7.2, color=INK, ha="right")
ax.set_xticks(x); ax.set_xticklabels([g[0] for g in G], fontsize=7.8)
ax.set_ylim(0, 88)
ax.tick_params(axis="y", labelsize=7.2)
ax.set_ylabel("팝업의 학습행", fontsize=7.8)
ax.set_title("회색 = 라벨 있는 행 · 붉은색 = pop_* 관측 행",
             fontsize=8.8, pad=6)
ax.text(-0.44, 78, "노트 286 이 본 것", fontsize=7.0, color=GRY)
ax.text(-0.44, 71, "실제로 쓰이는 것", fontsize=7.0, color=RED)

# --- 오른쪽: 노트 281 곡선 위에 얹는다 ----------------------------------
ax = axes[1]
K = [16, 18, 20, 22, 25, 30, 40]
V = [.0000, .0000, .0000, .0765, .0586, .1419, .3846]
ax.plot(K, V, "-o", color=GRY, lw=1.5, ms=4.6, zorder=3, alpha=.85)
ax.axvline(22, color=INK, lw=1.1, ls="--", zorder=2)
ax.plot([14], [0.0000], "D", color=RED, ms=8, zorder=5)
ax.plot([17], [0.0076], "D", color=RED, ms=8, zorder=5)
ax.text(14, -0.030, "좁은 판\n14행 · +0.0000", fontsize=7.0, color=RED,
        ha="center", va="top")
ax.text(17, 0.175, "넓힌 판\n17행 · +0.0076", fontsize=7.0, color=RED,
        ha="center")
ax.annotate("", xy=(17, 0.020), xytext=(17, 0.150),
            arrowprops=dict(arrowstyle="->", color=RED, lw=0.9))
ax.text(27, 0.33, "노트 281 곡선\n(웹툰 얇게 · 라벨 누출)", fontsize=6.9,
        color=GRY)
ax.set_xlim(12, 42); ax.set_ylim(-0.12, 0.44)
ax.tick_params(labelsize=7.2)
ax.set_xlabel("그 축이 관측된 학습행", fontsize=7.8, labelpad=2)
ax.set_ylabel("전용 축의 이득", fontsize=7.8)
ax.axhline(0, color=INK, lw=0.8, zorder=1)
ax.set_title("넓혀도 문턱 아래에 그대로 있다", fontsize=9.4, pad=6)
fig.suptitle("행을 늘렸는데 그 축의 행은 안 늘었다", fontsize=10.4, y=1.005)
fig.subplots_adjust(left=.108, right=.985, top=.795, bottom=.185)
fig.savefig(D / "rows.pdf"); plt.close(fig)
print("ok")
