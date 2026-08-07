import json, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import paper.figs  # noqa: F401,E402
D = Path(__file__).resolve().parent
C = json.loads(Path("data/state/note253_curve.json").read_text())

fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.3),
                         gridspec_kw={"width_ratios": [1, 1], "wspace": 0.30})
ax = axes[0]
n = [r["학습"] for r in C]; v = [r["도서"] for r in C]; sd = [r["SD"] for r in C]
ax.errorbar(n, v, yerr=sd, fmt="o-", ms=6, color="#2f5fa3", ecolor="#9bb0cc",
            capsize=3, lw=1.4, zorder=3)
ax.axhline(0.4980, color="#2f6f4f", lw=1.0, ls=(0, (4, 3)))
ax.text(78, 0.487, "유보 안 CV 0.498 (노트 252)", fontsize=6.8, color="#2f6f4f",
        ha="right")
ax.axhline(0.3482, color="#999", lw=0.9, ls=(0, (2, 3)))
ax.text(22, 0.353, "풀링 되돌림 0.348", fontsize=6.8, color="#777")
ax.set_xlabel("도서 학습 행 수"); ax.set_ylabel("도서 유보 $\\rho$")
ax.set_ylim(0.30, 0.52)
ax.set_title("학습을 덜어 내면 --- 좋아진다", fontsize=9.4, pad=6)

ax = axes[1]
E = [("종이책\n(판에 있다)", 4.30, "#2f5fa3"), ("전자책\n(빠져 있다)", 3.31, "#a33b3b")]
x = np.arange(len(E))
ax.bar(x, [e[1] for e in E], color=[e[2] for e in E], width=0.5)
for xx, e in zip(x, E):
    ax.text(xx, e[1] + 0.06, f"{e[1]:.2f}", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels([e[0] for e in E], fontsize=8)
ax.set_ylabel("$\\log_{10}$ sales point 평균"); ax.set_ylim(0, 5.2)
ax.text(0.5, 4.75, "전자책 여부 $\\sim$ 라벨\n$\\rho = -0.81$ (학습)",
        ha="center", fontsize=7.6, color="#a33b3b")
ax.set_title("전자책을 넣을 수 없는 이유", fontsize=9.4, pad=6)
fig.suptitle("도서의 여지는 수집으로 못 메운다", fontsize=10, y=1.0)
fig.tight_layout(); fig.savefig(D / "book.pdf"); plt.close(fig)
print("ok")
