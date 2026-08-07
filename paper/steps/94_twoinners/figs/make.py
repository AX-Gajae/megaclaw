import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import paper.figs  # noqa: F401,E402
D = Path(__file__).resolve().parent
DEP = [2, 3, 4, 5, 6]
S73 = [0.5250, 0.5268, 0.5264, 0.5228, 0.5201]
S24 = [0.4808, 0.4848, 0.4868, 0.4885, 0.4830]
OUT = [0.4629, 0.4754, 0.4845, 0.4857, 0.4863]

fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.3),
                         gridspec_kw={"width_ratios": [1.15, 1], "wspace": 0.34})
ax = axes[0]
def norm(v):
    v = np.array([x for x in v if x is not None], float)
    return (v - v.min()) / (v.max() - v.min())
ax.plot(DEP, norm(S73), "o-", color="#c08a3e", lw=1.6, ms=6, label="안쪽 7:3")
ax.plot(DEP, norm(S24), "s-", color="#6f86b3", lw=1.6, ms=6, label="안쪽 2024 조각")
ax.plot(DEP, norm(OUT), "^--", color="#2f6f4f", lw=1.6, ms=6, label="유보 (봉우리 없음)")
ax.scatter([3], [norm(S73)[1]], s=150, facecolors="none", edgecolors="#c08a3e",
           lw=1.6, zorder=5)
ax.scatter([5], [norm(S24)[3]], s=150, facecolors="none", edgecolors="#6f86b3",
           lw=1.6, zorder=5)
ax.set_xticks(DEP); ax.set_xlabel("나무 깊이")
ax.set_ylabel("각 곡선 안에서 정규화")
ax.legend(fontsize=7.2, frameon=False, loc="lower left")
ax.set_title("안쪽 둘이 서로 다른 봉우리를 짚는다", fontsize=9.4, pad=6)

ax = axes[1]
B = [("안쪽 7:3", 0.269, 0.700), ("안쪽 2024 조각", 0.481, 0.400)]
x = np.arange(len(B)); w = 0.34
ax.bar(x - w / 2, [b[1] for b in B], width=w, color="#8a9ab3", label="봉우리")
ax.bar(x + w / 2, [b[2] for b in B], width=w, color="#c9ccd1", label="단조")
ax.axhline(0.5, color="#a33b3b", lw=1.1, ls=(0, (4, 3)))
ax.text(1.42, 0.52, "봉우리 문턱 0.5", fontsize=6.8, color="#a33b3b", ha="right")
ax.axhline(0.8, color="#a33b3b", lw=1.1, ls=(0, (2, 3)))
ax.text(1.42, 0.82, "단조 문턱 0.8", fontsize=6.8, color="#a33b3b", ha="right")
for xx, b in zip(x, B):
    ax.text(xx - w / 2, b[1] + 0.02, f"{b[1]:.3f}", ha="center", fontsize=8)
    ax.text(xx + w / 2, b[2] + 0.02, f"{b[2]:.3f}", ha="center", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels([b[0] for b in B], fontsize=8)
ax.set_ylim(0, 1.0)
ax.legend(fontsize=7.2, frameon=False, loc="upper left")
ax.set_title("둘 다 문턱을 못 넘는다", fontsize=9.4, pad=6)
fig.suptitle("F18 깊이 --- 손잡이가 하나 더 죽었다", fontsize=10, y=1.0)
fig.tight_layout(); fig.savefig(D / "depth.pdf"); plt.close(fig)
print("ok")
