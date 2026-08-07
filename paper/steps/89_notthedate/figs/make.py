import json, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import paper.figs  # noqa: F401,E402
D = Path(__file__).resolve().parent
R = [r for r in json.loads(Path("data/state/note267_cohort.json").read_text())
     if r["코호트모형"] is not None and r["코호트달력"] is not None]

fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.4),
                         gridspec_kw={"width_ratios": [1, 1.25], "wspace": 0.32})
# 왼쪽 — 판 수준
ax = axes[0]
x = np.arange(2); w = 0.36
ax.bar(x - w / 2, [0.4725, 0.4679], width=w, color="#2f6f4f", label="모형")
ax.bar(x + w / 2, [0.2287, 0.1352], width=w, color="#c08a3e", label="$-$시작일만")
for xx, (a, b) in zip(x, [(0.4725, 0.2287), (0.4679, 0.1352)]):
    ax.text(xx - w / 2, a + 0.008, f"{a:.4f}", ha="center", fontsize=8)
    ax.text(xx + w / 2, b + 0.008, f"{b:.4f}", ha="center", fontsize=8)
ax.annotate("", xy=(1.18, 0.1352), xytext=(0.18, 0.2287),
            arrowprops=dict(arrowstyle="->", color="#a33b3b", lw=1.4))
ax.text(0.68, 0.205, "$-$41\\%", fontsize=8.5, color="#a33b3b")
ax.annotate("", xy=(0.82, 0.4679), xytext=(-0.18, 0.4725),
            arrowprops=dict(arrowstyle="->", color="#2f6f4f", lw=1.4))
ax.text(0.32, 0.487, "$-$1\\%", fontsize=8.5, color="#2f6f4f")
ax.set_xticks(x); ax.set_xticklabels(["그대로", "반년 코호트 안"], fontsize=8.4)
ax.set_ylabel("$\\rho$"); ax.set_ylim(0, 0.56)
ax.legend(fontsize=7.4, frameon=False, loc="upper right")
ax.set_title("코호트를 통제하면 달력만 무너진다", fontsize=9.4, pad=6)

# 오른쪽 — 도메인별
ax = axes[1]
R2 = sorted(R, key=lambda r: -r["달력"])
y = np.arange(len(R2))[::-1]
for yy, r in zip(y, R2):
    ax.plot([r["달력"], r["코호트달력"]], [yy + 0.16] * 2, color="#c08a3e",
            lw=1.4, zorder=2)
    ax.scatter([r["달력"]], [yy + 0.16], s=26, color="#c08a3e", zorder=3)
    ax.scatter([r["코호트달력"]], [yy + 0.16], s=26, color="#c08a3e",
               marker="|", zorder=3)
    ax.plot([r["모형"], r["코호트모형"]], [yy - 0.16] * 2, color="#2f6f4f",
            lw=1.4, zorder=2)
    ax.scatter([r["모형"]], [yy - 0.16], s=26, color="#2f6f4f", zorder=3)
    ax.scatter([r["코호트모형"]], [yy - 0.16], s=26, color="#2f6f4f",
               marker="|", zorder=3)
ax.axvline(0, color="#888", lw=0.6)
ax.set_yticks(y); ax.set_yticklabels([f"{r['도메인']} ({r['n']})" for r in R2],
                                     fontsize=7.4)
ax.set_xlabel("$\\rho$  (점 $\\to$ 막대 = 코호트 통제)")
from matplotlib.lines import Line2D
ax.legend(handles=[Line2D([], [], color="#2f6f4f", label="모형"),
                   Line2D([], [], color="#c08a3e", label="$-$시작일만")],
          fontsize=7, frameon=False, loc="lower right")
ax.set_title("도서만 달력이 모형을 이긴다", fontsize=9.4, pad=6)
fig.suptitle("판 0.484 의 얼마가 ``언제 나왔나'' 인가", fontsize=10, y=1.0)
fig.tight_layout(); fig.savefig(D / "cohort.pdf"); plt.close(fig)
print("ok")
