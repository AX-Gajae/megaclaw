import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import paper.figs  # noqa: F401,E402
D = Path(__file__).resolve().parent
ROWS = [("2024 한 조각\n(배포를 그대로 흉내)", 0.511, True),
        ("무게를 유보 섞임으로\n고정", 0.467, False),
        ("안쪽이 보는\n여섯 도메인만", 0.352, False),
        ("누적 라벨 도메인\n뺌", 0.327, False),
        ("해 셋 평균", 0.357, False),
        ("해 다섯 평균", 0.203, False),
        ("반해 여섯 평균", 0.214, False)]
fig, ax = plt.subplots(figsize=(7.0, 3.5))
y = np.arange(len(ROWS))[::-1]
ax.barh(y, [r[1] for r in ROWS],
        color=["#2f6f4f" if r[2] else "#b9553f" for r in ROWS], height=0.64)
ax.axvline(0.511, color="#333", lw=0.9, ls=(0, (4, 3)))
for yy, r in zip(y, ROWS):
    ax.text(r[1] + 0.008, yy, f"{r[1]:+.3f}", va="center", fontsize=8)
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in ROWS], fontsize=7.6)
ax.set_xlim(0, 0.60)
ax.set_xlabel("작은 칸($|\\Delta| \\leq 0.010$)에서 유보와의 spearman")
ax.set_title("안쪽을 손보는 길 여섯 --- 전부 흉내보다 못하다", fontsize=10, pad=8)
fig.tight_layout(); fig.savefig(D / "mimic.pdf"); plt.close(fig)
print("ok")
