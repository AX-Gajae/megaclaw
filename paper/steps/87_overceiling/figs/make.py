import json, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import paper.figs  # noqa: F401,E402
D = Path(__file__).resolve().parent
R = json.loads(Path("data/state/note265_ceiling.json").read_text())
R = sorted(R, key=lambda r: r["여지"])

fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.5),
                         gridspec_kw={"width_ratios": [1.2, 1], "wspace": 0.34})
ax = axes[0]
y = np.arange(len(R))[::-1]
for yy, r in zip(y, R):
    small = r["n"] < 100 or r["섞음"] > 0.40
    c = "#c9ccd1" if small else ("#2f6f4f" if r["여지"] < 0 else "#a33b3b")
    ax.plot([r["지금"], r["CV"]], [yy, yy], color=c, lw=1.6, zorder=2)
    ax.scatter([r["지금"]], [yy], s=44, color=c, zorder=4)
    ax.scatter([r["CV"]], [yy], s=30, color=c, marker="|", zorder=4)
    ax.text(0.70, yy, f"{r['여지']:+.3f}", fontsize=7, va="center", color=c)
ax.axvline(0, color="#888", lw=0.6)
ax.set_yticks(y)
ax.set_yticklabels([f"{r['도메인']} ({r['n']})" for r in R], fontsize=7.4)
ax.set_xlim(0.13, 0.78); ax.set_xlabel("$\\rho$  (점 = 지금, 막대 = 유보 안 CV)")
ax.set_title("여섯이 제 천장 위에 있다", fontsize=9.4, pad=6)
from matplotlib.lines import Line2D
ax.legend(handles=[
    Line2D([], [], marker="o", ls="", color="#2f6f4f", label="여지 음수"),
    Line2D([], [], marker="o", ls="", color="#a33b3b", label="여지 양수"),
    Line2D([], [], marker="o", ls="", color="#c9ccd1", label="표본 작음 · 못 읽음"),
], fontsize=6.6, frameon=False, loc="lower right")

ax = axes[1]
S = [("17축\n노트 252", 0.4569, 0.4697), ("21축\n노트 260", 0.4688, 0.4808),
     ("23축\n지금", 0.4842, 0.4762)]
x = np.arange(len(S)); w = 0.34
ax.bar(x - w / 2, [s[1] - 0.44 for s in S], bottom=0.44, width=w,
       color="#2f5fa3", label="판(배포)")
ax.bar(x + w / 2, [s[2] - 0.44 for s in S], bottom=0.44, width=w,
       color="#c08a3e", label="유보 안 CV(천장)")
for xx, s in zip(x, S):
    ax.text(xx - w / 2, s[1] + 0.0012, f"{s[1]:.4f}", ha="center", fontsize=7)
    ax.text(xx + w / 2, s[2] + 0.0012, f"{s[2]:.4f}", ha="center", fontsize=7)
ax.set_xticks(x); ax.set_xticklabels([s[0] for s in S], fontsize=7.6)
ax.set_ylim(0.44, 0.497); ax.set_ylabel("$\\rho$")
ax.legend(fontsize=7, frameon=False, loc="upper left")
ax.set_title("따라잡고 넘어섰다", fontsize=9.4, pad=6)
fig.suptitle("판이 유보 안 CV 를 넘었다 --- 여지 $-$0.008", fontsize=10, y=1.0)
fig.tight_layout(); fig.savefig(D / "ceiling.pdf"); plt.close(fig)
print("ok")
