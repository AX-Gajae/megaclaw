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
                         gridspec_kw={"width_ratios": [1, 1.2], "wspace": 0.34})
# 왼쪽 — 세 행 집합
ax = axes[0]
R = [("게임", 223, 180, 96), ("모바일", 441, 441, 5), ("웹툰", 711, 711, 0)]
x = np.arange(len(R)); w = 0.26
ax.bar(x - w, [r[1] for r in R], width=w, color="#8a9ab3", label="유보 행")
ax.bar(x, [r[2] for r in R], width=w, color="#2f6f4f", label="라벨 있는 행")
ax.bar(x + w, [r[3] for r in R], width=w, color="#c08a3e",
       label="media\\_push 관측")
for xx, r in zip(x, R):
    for dx, v in ((-w, r[1]), (0, r[2]), (w, r[3])):
        ax.text(xx + dx, v + 14, str(v), ha="center", fontsize=6.8)
ax.set_xticks(x); ax.set_xticklabels([r[0] for r in R], fontsize=8.4)
ax.set_ylabel("행 수"); ax.set_ylim(0, 830)
ax.legend(fontsize=6.8, frameon=False, loc="upper left")
ax.set_title("셋이 다르다", fontsize=9.4, pad=6)

# 오른쪽 — 세 번 틀린 자리
ax = axes[1]
E = [("노트 264\n가드 쌓임", "축 마스크를 안 보고\n원본 필드를 전 행에서",
      "판 $+$0.0000 이 잡았다"),
     ("노트 266\n후보 검사", "토큰 없는 행까지 넣고 SVD →\n``기록됐나'' 성분",
      "$+$0.285 가 통과했다"),
     ("노트 270\nrank.clock", "유보 행 수와 라벨 있는\n행 수를 같게 봄",
      "게임이 조용히 빠졌다")]
y = np.arange(len(E))[::-1]
for yy, (a, b, c) in zip(y, E):
    ax.text(0.02, yy + 0.22, a, fontsize=7.6, va="center", fontweight="bold")
    ax.text(0.34, yy + 0.22, b, fontsize=6.8, va="center", color="#444")
    ax.text(0.34, yy - 0.22, c, fontsize=6.8, va="center", color="#a33b3b")
ax.set_xlim(0, 1.05); ax.set_ylim(-0.7, len(E) - 0.1)
ax.axis("off")
ax.set_title("같은 자리에서 세 번", fontsize=9.4, pad=6)
fig.suptitle("``어느 행이 진짜 있는 행인가'' --- 이름이 없어서 세 번 틀렸다",
             fontsize=10, y=1.0)
fig.tight_layout(); fig.savefig(D / "rows.pdf"); plt.close(fig)
print("ok")
