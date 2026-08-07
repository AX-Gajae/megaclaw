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
                         gridspec_kw={"width_ratios": [1.1, 1], "wspace": 0.36})
# 왼쪽 — 코호트별 중앙값
ax = axes[0]
C = [("2025\nH1", 12, 39209), ("2025\nH2", 18, 28991),
     ("2026\nH1", 79, 18070), ("2026 H2\n$+$", 54, 4485)]
x = np.arange(len(C))
ax.bar(x, [c[2] for c in C], color="#a33b3b", width=0.55)
for xx, c in zip(x, C):
    ax.text(xx, c[2] + 1400, f"{c[2]:,}", ha="center", fontsize=8)
    ax.text(xx, 1600, f"{c[1]}건", ha="center", fontsize=7, color="white")
ax.set_xticks(x); ax.set_xticklabels([c[0] for c in C], fontsize=8)
ax.set_ylabel("sales point 중앙값"); ax.set_ylim(0, 46000)
ax.set_title("유보 안에서만 8.7배 --- 순수한 쌓임", fontsize=9.4, pad=6)

# 오른쪽 — 도서가 네 번 짚힌 자리
ax = axes[1]
R = [("노트 252\n여지 1위", 0.177), ("노트 253\n학습 덜면 좋아짐", 0.042),
     ("노트 254\n아홉 중 도서만", 0.042), ("노트 267\n달력이 모형을 이김", 0.214)]
y = np.arange(len(R))[::-1]
ax.barh(y, [r[1] for r in R], color="#c08a3e", height=0.55)
for yy, r in zip(y, R):
    ax.text(r[1] + 0.006, yy, f"{r[1]:+.3f}", va="center", fontsize=7.6)
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in R], fontsize=7)
ax.set_xlim(0, 0.27); ax.set_xlabel("그때 잰 크기")
ax.set_title("네 번 다 같은 뿌리였다", fontsize=9.4, pad=6)
fig.suptitle("도서 라벨은 ``얼마나 팔렸나''가 아니라 ``언제 나왔나'' 다",
             fontsize=10, y=1.0)
fig.tight_layout(); fig.savefig(D / "book.pdf"); plt.close(fig)
print("ok")
