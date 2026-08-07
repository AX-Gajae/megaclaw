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

RED, GRN, GRY, INK = "#a33b3b", "#2f6f4f", "#9aa0a8", "#3b3b3b"
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.05),
                         gridspec_kw={"width_ratios": [1, 1.05], "wspace": 0.38})

# --- 왼쪽: 넷 칸 ---------------------------------------------------------
ax = axes[0]
G = [("F21 능형", -0.0070, +0.0880, GRN), ("F18 나무", 0.0000, 0.0000, RED)]
x = np.arange(2); w = 0.34
for i, (nm, real, leak, c) in enumerate(G):
    ax.bar(x[i] - w / 2, real, width=w, color=c, alpha=.42, zorder=3)
    ax.bar(x[i] + w / 2, leak, width=w, color=c, zorder=3)
    ax.text(x[i] - w / 2, real + (0.004 if real >= 0 else -0.010),
            f"{real:+.4f}", ha="center", fontsize=7.4, color=c,
            va="bottom" if real >= 0 else "top")
    ax.text(x[i] + w / 2, leak + 0.004, f"{leak:+.4f}", ha="center",
            fontsize=7.4, color=c)
ax.axhline(0, color=INK, lw=0.9, zorder=2)
ax.set_xticks(x); ax.set_xticklabels([g[0] for g in G], fontsize=8.0)
ax.set_ylim(-0.022, 0.108)
ax.tick_params(axis="y", labelsize=7.2)
ax.set_ylabel("팝업 rho 의 변화", fontsize=7.8)
ax.set_title("같은 열, 다른 정식화", fontsize=9.4, pad=6)
ax.text(0.63, 0.093, "연한 막대 = 진짜 축 넷", fontsize=6.9, color=INK)
ax.text(0.63, 0.084, "진한 막대 = 라벨을 그대로 준 열", fontsize=6.9, color=INK)
ax.text(1.0, 0.017, "나무는 둘 다\n정확히 0", fontsize=7.2, color=RED,
        ha="center")

# --- 오른쪽: 잎 하한 곡선 위에 능형을 얹는다 -----------------------------
ax = axes[1]
L = [(20, 0.0000), (10, 0.0394), (5, 0.4373), (2, 0.4786)]
lf = np.array([l[0] for l in L], float); gv = np.array([l[1] for l in L])
ax.plot(lf, gv, "o-", color=RED, lw=1.7, ms=6.5, zorder=4, label="F18 나무")
ax.axhline(0.0880, color=GRN, lw=1.7, ls="--", zorder=3)
ax.text(19, 0.235, "F21 능형 +0.0880\n잎 하한이 없다",
        fontsize=7.2, color=GRN, ha="left", va="top")
DY = {20: -0.045, 10: -0.048, 5: 0.032, 2: 0.032}
for x0, y0 in L:
    ax.text(x0 * (0.93 if x0 in (20, 10) else 1.06), y0 + DY[x0],
            f"{y0:+.4f}", fontsize=7.0, color=RED,
            ha="right" if x0 in (20, 10) else "left")
ax.set_xscale("log"); ax.invert_xaxis()
ax.set_xticks([20, 10, 5, 2])
ax.set_xticklabels(["20\n(기본값)", "10", "5", "2"], fontsize=7.2)
ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
ax.tick_params(axis="y", labelsize=7.2)
ax.set_ylim(-0.10, 0.60)
ax.set_xlabel("min_samples_leaf", fontsize=7.8, labelpad=2)
ax.set_ylabel("라벨을 그대로 준 열의 이득", fontsize=7.8)
ax.set_title("벽은 나무에만 있다", fontsize=9.4, pad=6)
fig.suptitle("챔피언은 작은 도메인의 전용 정보에 눈이 멀어 있다",
             fontsize=10.4, y=1.005)
fig.subplots_adjust(left=.108, right=.985, top=.80, bottom=.20)
fig.savefig(D / "blind.pdf"); plt.close(fig)
print("ok")
