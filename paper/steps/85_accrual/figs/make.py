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
# 왼쪽 — 원본 필드 훑기
ax = axes[0]
R = [("웹툰 goods\\_scale\n$\\leftarrow$ n\\_episode", -0.490, 45, True),
     ("세계애니 goods\\_scale\n$\\leftarrow$ n\\_episode$\\times$분", -0.063, 81, False),
     ("만화 goods\\_scale\n$\\leftarrow$ n\\_chapter", -0.002, 39, None),
     ("애니 media\\_push\n$\\leftarrow$ is\\_dubbed", +0.014, 95, False)]
y = np.arange(len(R))[::-1]
cs = ["#a33b3b" if r[3] is True else ("#c9ccd1" if r[3] is None else "#2f6f4f")
      for r in R]
ax.barh(y, [abs(r[1]) for r in R], color=cs, height=0.6)
for yy, r in zip(y, R):
    tag = "막음" if r[3] is True else ("유보 6건 — 증거 없음" if r[3] is None else "둔다")
    ax.text(abs(r[1]) + 0.012, yy, f"{r[1]:+.3f}   {tag}", va="center", fontsize=7,
            color="#a33b3b" if r[3] is True else "#555")
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in R], fontsize=6.8)
ax.set_xlim(0, 0.72)
ax.set_xlabel("$|$연도와의 상관$|$")
ax.set_title("쌓이는 것은 연도에 붙는다", fontsize=9.4, pad=6)

# 오른쪽 — 판
ax = axes[1]
S = [("노트 260\n$+$메타", 0.4916, "#1f5138"),
     ("노트 262\n$-$daily\\_pass", 0.4772, "#a33b3b"),
     ("노트 263\n$-$n\\_episode", 0.4842, "#2f6f4f")]
x = np.arange(len(S))
ax.bar(x, [s[1] - 0.465 for s in S], bottom=0.465, color=[s[2] for s in S], width=0.55)
for xx, s in zip(x, S):
    ax.text(xx, s[1] + 0.0009, f"{s[1]:.4f}", ha="center", fontsize=8.6)
ax.set_xticks(x); ax.set_xticklabels([s[0] for s in S], fontsize=7.4)
ax.set_ylim(0.465, 0.497); ax.set_ylabel("판 $\\rho$")
ax.set_title("새는 축 둘을 빼고 더 높다", fontsize=9.4, pad=6)
fig.suptitle("손 축의 원본 필드를 훑었다", fontsize=10, y=1.0)
fig.tight_layout(); fig.savefig(D / "accrual.pdf"); plt.close(fig)
print("ok")
