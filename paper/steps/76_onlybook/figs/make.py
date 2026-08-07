import json, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import paper.figs  # noqa: F401,E402
D = Path(__file__).resolve().parent
R = json.loads(Path("data/state/note254_half.json").read_text())
R = sorted(R, key=lambda r: -r["차"])
fig, ax = plt.subplots(figsize=(7.0, 3.4))
y = np.arange(len(R))[::-1]
for yy, r in zip(y, R):
    c = "#2f6f4f" if r["차"] > 0 else "#a33b3b"
    ax.barh(yy, r["차"], color=c, height=0.62)
    ax.errorbar(r["차"], yy, xerr=r["짝SE"], fmt="none", ecolor="#555",
                elinewidth=1.0, capsize=2.5, zorder=3)
ax.axvline(0, color="#333", lw=0.9)
ax.set_yticks(y)
ax.set_yticklabels([f"{r['도메인']} (학습 {r['학습']:,})" for r in R], fontsize=7.4)
ax.set_xlabel("제 학습을 절반으로 줄였을 때 도메인 $\\rho$ 변화 $\\pm$ 짝 SE")
ax.set_title("아홉 중 도서 하나만 제 학습이 해롭다", fontsize=10, pad=8)
ax.text(0.044, len(R) - 1.15, "도서만 오른쪽", fontsize=7.4, color="#2f6f4f")
fig.tight_layout(); fig.savefig(D / "half.pdf"); plt.close(fig)
print("ok")
