import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import paper.figs  # noqa: F401,E402
D = Path(__file__).resolve().parent

fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.3),
                         gridspec_kw={"width_ratios": [1.15, 1], "wspace": 0.34})
# 왼쪽 — 겹침 대 판 이득
ax = axes[0]
P = [("웹툰 성분1", 0.356, +0.0052, "#2f6f4f"),
     ("웹툰 성분3", 0.389, +0.0052, "#2f6f4f"),
     ("세계애니 성분3", 0.621, -0.0037, "#a33b3b")]
for lab, ov, g, c in P:
    ax.scatter([ov], [g], s=70, color=c, zorder=3)
    ax.annotate(lab, (ov, g), textcoords="offset points", xytext=(0, 11),
                ha="center", fontsize=7.4, color=c)
ax.axhline(0, color="#333", lw=0.9)
ax.axvline(0.95, color="#a33b3b", lw=1.0, ls=(0, (4, 3)))
ax.text(0.93, -0.0028, "가드 겹말 문턱 0.95", fontsize=6.8, color="#a33b3b",
        rotation=90, va="bottom", ha="right")
ax.set_xlim(0.25, 1.0); ax.set_ylim(-0.006, 0.009)
ax.set_xlabel("기존 축과의 최대 겹침 $|\\rho|$")
ax.set_ylabel("판 $\\rho$ 짝 차")
ax.set_title("셋 다 가드는 통과한다", fontsize=9.4, pad=6)

# 오른쪽 — 어디서 깨졌나
ax = axes[1]
B = [("F21\n능형", +0.0002, "#6f86b3"), ("F18\n나무", -0.0041, "#c08a3e"),
     ("F23\n판", -0.0037, "#a33b3b")]
x = np.arange(len(B))
ax.bar(x, [b[1] for b in B], color=[b[2] for b in B], width=0.5)
ax.axhline(0, color="#333", lw=0.9)
for xx, b in zip(x, B):
    ax.text(xx, b[1] - 0.00025, f"{b[1]:+.4f}", ha="center",
            va="top" if b[1] < 0 else "bottom", fontsize=8.4)
ax.set_xticks(x); ax.set_xticklabels([b[0] for b in B], fontsize=8)
ax.set_ylabel("짝 차"); ax.set_ylim(-0.0052, 0.0016)
ax.set_title("나무에서 깨진다 ($t{=}-2.80$)", fontsize=9.4, pad=6)
fig.suptitle("세계애니 장르 축 --- 학습 검사를 다 통과하고 판에서 떨어졌다",
             fontsize=10, y=1.0)
fig.tight_layout(); fig.savefig(D / "overlap.pdf"); plt.close(fig)
print("ok")
