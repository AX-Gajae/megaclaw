import json, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import paper.figs  # noqa: F401,E402
D = Path(__file__).resolve().parent
R = json.loads(Path("data/state/note258_acc.json").read_text())
x = np.arange(len(R))
fig, ax = plt.subplots(figsize=(7.0, 3.6))
SER = [("웹툰", "#a33b3b", "o"), ("애니", "#2f6f4f", "s"),
       ("모바일", "#2f5fa3", "^"), ("판", "#333", "D")]
for dm, c, mk in SER:
    v = [r[dm] for r in R]
    ax.plot(x, v, marker=mk, ms=6, lw=1.6 if dm == "판" else 1.3, color=c,
            label=dm, zorder=4 if dm == "판" else 3,
            ls="-" if dm != "판" else (0, (4, 2)))
for i, r in enumerate(R):
    ax.axvline(i, color="#eee", lw=0.8, zorder=0)
ax.annotate("제 축 $+$0.021", xy=(1, R[1]["웹툰"]), xytext=(0.55, 0.437),
            fontsize=7.4, color="#a33b3b",
            arrowprops=dict(arrowstyle="->", color="#a33b3b", lw=0.9))
ax.annotate("남의 축 $-$0.028", xy=(3, R[3]["웹툰"]), xytext=(2.15, 0.352),
            fontsize=7.4, color="#a33b3b",
            arrowprops=dict(arrowstyle="->", color="#a33b3b", lw=0.9))
ax.set_xticks(x)
ax.set_xticklabels([r["단계"].replace(" (", "\n(") for r in R], fontsize=7.6)
ax.set_ylabel("$\\rho$")
ax.set_ylim(0.34, 0.60)
ax.legend(fontsize=7.6, frameon=False, ncol=4, loc="upper left")
ax.set_title("도메인 전용 축을 쌓을수록 --- 판은 오르고 웹툰은 내린다",
             fontsize=10, pad=8)
fig.tight_layout(); fig.savefig(D / "crowd.pdf"); plt.close(fig)
print("ok")
