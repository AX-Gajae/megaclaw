import json, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import paper.figs  # noqa: F401,E402
D = Path(__file__).resolve().parent
R = json.loads(Path("data/state/note249_inter.json").read_text())

fig, ax = plt.subplots(figsize=(7.0, 3.6))
x = np.arange(len(R)); w = 0.20
SER = [("혼자", "혼자", "#6f86b3"), ("남만", "남만", "#c08a3e"),
       ("합", "합 (혼자 $+$ 남만)", "#8a8f98"), ("전체", "전체 (실제)", "#2f6f4f")]
for i, (k, lab, c) in enumerate(SER):
    ax.bar(x + (i - 1.5) * w, [r[k] for r in R], width=w, color=c, label=lab)
ax.axhline(0, color="#333", lw=0.9)
for j, r in enumerate(R):
    if abs(r["상호작용"]) > 0.015:
        ax.annotate("", xy=(x[j] + 1.5 * w, r["전체"]), xytext=(x[j] + 0.5 * w, r["합"]),
                    arrowprops=dict(arrowstyle="->", color="#a33b3b", lw=1.2))
        ax.text(x[j] + w, (r["전체"] + r["합"]) / 2 - 0.006,
                f"{r['상호작용']:+.3f}", fontsize=6.8, color="#a33b3b", ha="center")
ax.set_xticks(x); ax.set_xticklabels([f"{r['도메인']}\n({r['n']})" for r in R],
                                     fontsize=8)
ax.set_ylabel("도메인 $\\rho$ 변화")
ax.legend(fontsize=7.4, frameon=False, ncol=4, loc="lower center")
ax.set_ylim(-0.098, 0.055)
ax.set_title("혼자 바꾸기 $+$ 남만 바꾸기 $\\neq$ 둘 다 바꾸기", fontsize=10, pad=8)
fig.tight_layout(); fig.savefig(D / "parts.pdf"); plt.close(fig)

fig, ax = plt.subplots(figsize=(7.0, 3.2))
add = np.array([abs(r["합"]) for r in R]); it = np.array([abs(r["상호작용"]) for r in R])
ax.scatter(add, it, s=60, color="#2f5fa3", zorder=3)
for r in R:
    ax.annotate(r["도메인"], (abs(r["합"]), abs(r["상호작용"])),
                textcoords="offset points", xytext=(7, 4), fontsize=7.4)
lim = [0, 0.062]
ax.plot(lim, lim, ls=(0, (4, 3)), color="#666", lw=1.0)
ax.text(0.047, 0.050, "상호작용 $=$ 부분합", fontsize=7.2, color="#666",
        rotation=38, ha="center")
ax.set_xlim(*lim); ax.set_ylim(*lim)
ax.set_xlabel("$|$부분의 합$|$"); ax.set_ylabel("$|$상호작용$|$")
ax.set_title(f"다섯 도메인 합계로 보면 상호작용이 부분합의 "
             f"{it.sum()/add.sum():.2f} 배 --- 절반이 교차항이다",
             fontsize=9.6, pad=8)
fig.tight_layout(); fig.savefig(D / "ratio.pdf"); plt.close(fig)
print("ok")
