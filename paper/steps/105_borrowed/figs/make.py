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

GRN, RED, BLU, GRY, INK = "#2f6f4f", "#a33b3b", "#3c5f8a", "#9aa0a8", "#3b3b3b"
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.15),
                         gridspec_kw={"width_ratios": [1, 1.1], "wspace": 0.36})

ax = axes[0]
IN = [2.02, 2.29, 2.66, 2.99, 3.22]
MK = [2.55, 2.88, 3.12, 3.44, 3.70]
for q, c, nm, xo in ((IN, BLU, "내부 팝업 75행", 0), (MK, RED, "시장 207행", 1)):
    ax.plot([xo, xo], [q[0], q[4]], "-", color=c, lw=1.4, zorder=3)
    ax.add_patch(plt.Rectangle((xo - .17, q[1]), .34, q[3] - q[1],
                               facecolor=c, alpha=.28, edgecolor=c, lw=1.2,
                               zorder=4))
    ax.plot([xo - .17, xo + .17], [q[2]] * 2, "-", color=c, lw=2.2, zorder=5)
    ax.text(xo, q[4] + .09, nm, ha="center", fontsize=7.4, color=c)
for a, b in zip(IN, MK):
    ax.plot([.17, .83], [a, b], ":", color=GRY, lw=0.8, zorder=2)
ax.annotate("", xy=(0.5, 3.12), xytext=(0.5, 2.66),
            arrowprops=dict(arrowstyle="<->", color=INK, lw=1.1))
ax.text(0.56, 2.87, "0.46 log10\n= 3.2배", fontsize=7.2, color=INK)
ax.set_xlim(-.58, 1.62); ax.set_ylim(1.85, 4.05)
ax.set_xticks([0, 1]); ax.set_xticklabels(["내부", "시장"], fontsize=8.2)
ax.tick_params(axis="y", labelsize=7.2)
ax.set_ylabel("log10 일평균 방문", fontsize=7.8)
ax.set_title("같은 자인데 통째로 위에 있다", fontsize=9.4, pad=6)
ax.text(-.54, 1.94, "상자 = 25~75% · 선 = 10~90%", fontsize=6.8, color=INK)

ax = axes[1]
S = [("기간 일수", .535, -.061), ("IP 이력", .292, .217),
     ("멀티스토어", .287, .227), ("연도", -.238, -.147),
     ("IP 협업", .115, .114)]
y = np.arange(len(S))[::-1]
w = 0.34
for yy, (nm, a, b) in zip(y, S):
    ax.barh(yy + w / 2, abs(a), height=w, color=GRY, alpha=.75, zorder=3)
    c = RED if nm == "기간 일수" else GRN
    ax.barh(yy - w / 2, abs(b), height=w, color=c, zorder=3)
    ax.text(abs(a) + .012, yy + w / 2, f"{a:+.3f}", va="center",
            fontsize=6.9, color=INK)
    ax.text(abs(b) + .012, yy - w / 2, f"{b:+.3f}", va="center",
            fontsize=6.9, color=c)
ax.set_yticks(y); ax.set_yticklabels([s[0] for s in S], fontsize=7.4)
ax.set_xlim(0, 0.70); ax.set_ylim(-0.75, len(S) - 0.15)
ax.tick_params(axis="x", labelsize=7.2)
ax.set_xlabel("라벨과의 |순위상관|", fontsize=7.8, labelpad=2)
ax.set_title("회색 = 총방문 · 색 = 일평균", fontsize=9.4, pad=6)
ax.text(.31, 0.55, "기간 일수는 교락이었다", fontsize=7.0, color=RED)
ax.text(.31, 0.15, "나머지는 살아남는다", fontsize=7.0, color=GRN)
fig.suptitle("빌려올 수는 있는데 같은 방에 못 넣는다", fontsize=10.4, y=1.005)
fig.subplots_adjust(left=.108, right=.985, top=.805, bottom=.185)
fig.savefig(D / "borrow.pdf"); plt.close(fig)
print("ok")
