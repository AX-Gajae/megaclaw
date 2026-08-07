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
                         gridspec_kw={"width_ratios": [1.05, 1], "wspace": 0.42})

# --- 왼쪽: 세 번의 시도가 닿은 행의 비율 ---------------------------------
ax = axes[0]
T = [("IP 그래프\n(노트 291)", 2 / 104 * 100, "유보 2행"),
     ("만화 별칭\n(노트 293)", 0.8, "23 / 2,817"),
     ("회사 이력\n(노트 294)", 49.0, "234 / 482")]
x = np.arange(len(T))
for xx, (nm, pc, note) in zip(x, T):
    c = GRN if pc > 10 else RED
    ax.bar(xx, max(pc, 0.6), color=c, width=.5, zorder=3)
    ax.text(xx, max(pc, 0.6) + 1.6, f"{pc:.1f}%", ha="center", fontsize=8.4,
            color=c)
    ax.text(xx, -4.6, note, ha="center", fontsize=6.9, color=INK)
ax.set_xticks(x); ax.set_xticklabels([t[0] for t in T], fontsize=7.4)
ax.set_ylim(-7, 60)
ax.tick_params(axis="y", labelsize=7.2)
ax.set_ylabel("축이 닿는 행의 비율", fontsize=7.8)
ax.set_title("표본은 세 번째에 처음 충분했다", fontsize=9.4, pad=6)

# --- 오른쪽: 그런데 이득이 문턱 아래다 -----------------------------------
ax = axes[1]
G = [("게임", 0.0040, 0.015), ("모바일", -0.0019, 0.008)]
x = np.arange(len(G)); w = 0.34
for xx, (nm, g, fl) in zip(x, G):
    c = GRN if g > 0 else GRY
    ax.bar(xx - w / 2, abs(g), width=w, color=c, zorder=3)
    ax.bar(xx + w / 2, fl, width=w, color=RED, alpha=.45, zorder=3)
    ax.text(xx - w / 2, abs(g) + .0006, f"{g:+.4f}", ha="center", fontsize=7.4,
            color=c)
    ax.text(xx + w / 2, fl + .0006, f"{fl:.3f}", ha="center", fontsize=7.4,
            color=RED)
ax.set_xticks(x); ax.set_xticklabels([g[0] for g in G], fontsize=8.0)
ax.set_ylim(0, 0.021)
ax.tick_params(axis="y", labelsize=7.2)
ax.set_ylabel("rho", fontsize=7.8)
ax.set_title("색 = 얻은 값 · 붉은 = 검출 문턱", fontsize=9.2, pad=6)
ax.text(-0.42, 0.0193, "학습 상관은 올랐다 (+0.2002 $\\to$ +0.2149)",
        fontsize=6.9, color=INK)
ax.text(-0.42, 0.0180, "유보 이득은 문턱의 4분의 1", fontsize=6.9, color=RED)
fig.suptitle("건널 다리가 생겨도 건너오는 것이 작다", fontsize=10.4, y=1.005)
fig.subplots_adjust(left=.118, right=.985, top=.795, bottom=.185)
fig.savefig(D / "three.pdf"); plt.close(fig)
print("ok")
