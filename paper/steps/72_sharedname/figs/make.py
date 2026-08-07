import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import paper.figs  # noqa: F401,E402
D = Path(__file__).resolve().parent
SH = [("웹툰", +0.0110, +0.0024, -0.0003), ("애니", -0.0197, -0.0322, +0.0002),
      ("게임", +0.0124, +0.0122, -0.0008)]
PR = [("웹툰", +0.0110, -0.0007, +0.0067), ("애니", -0.0197, -0.0054, -0.0252),
      ("게임", +0.0124, -0.0084, +0.0072)]

fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.4), sharey=True,
                         gridspec_kw={"wspace": 0.12})
for ax, ROWS, ttl, rat in ((axes[0], SH, "이름 공유 (계수를 나눠 쓴다)", 1.01),
                           (axes[1], PR, "이름 분리 (전용 계수)", 0.18)):
    x = np.arange(len(ROWS)); w = 0.21
    S = [("혼자", 1, "#6f86b3"), ("남만", 2, "#c08a3e"), ("합", None, "#8a8f98"),
         ("전체", 3, "#2f6f4f")]
    for i, (lab, idx, c) in enumerate(S):
        v = [(r[1] + r[2]) if idx is None else r[idx] for r in ROWS]
        ax.bar(x + (i - 1.5) * w, v, width=w, color=c, label=lab)
    ax.axhline(0, color="#333", lw=0.9)
    for j, r in enumerate(ROWS):
        s = r[1] + r[2]
        if abs(r[3] - s) > 0.008:
            ax.annotate("", xy=(x[j] + 1.5 * w, r[3]), xytext=(x[j] + 0.5 * w, s),
                        arrowprops=dict(arrowstyle="->", color="#a33b3b", lw=1.2))
    ax.set_xticks(x); ax.set_xticklabels([r[0] for r in ROWS], fontsize=8.4)
    ax.set_title(f"{ttl}\n교차항/부분합 $=$ {rat:.2f}", fontsize=9, pad=6)
axes[0].set_ylabel("도메인 $\\rho$ 변화")
axes[0].legend(fontsize=7.2, frameon=False, ncol=4, loc="lower center")
axes[0].set_ylim(-0.058, 0.030)
fig.suptitle("같은 자료 · 같은 열 --- 이름만 다르다", fontsize=10, y=0.99)
fig.tight_layout(); fig.savefig(D / "names.pdf"); plt.close(fig)

fig, ax = plt.subplots(figsize=(7.0, 2.6))
B = [("축 추가\n이름 분리\n(다섯 도메인)", 0.27, "#2f6f4f"),
     ("축 추가\n이름 분리\n(셋)", 0.18, "#2f6f4f"),
     ("축 추가\n이름 공유\n(셋)", 1.01, "#a33b3b"),
     ("부호화 변경\n공유 축\n(노트 249)", 0.98, "#a33b3b")]
x = np.arange(len(B))
ax.bar(x, [b[1] for b in B], color=[b[2] for b in B], width=0.55)
ax.axhline(1.0, color="#333", lw=0.8, ls=(0, (4, 3)))
for xx, b in zip(x, B):
    ax.text(xx, b[1] + 0.03, f"{b[1]:.2f}", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels([b[0] for b in B], fontsize=7.4)
ax.set_ylabel("교차항 / 부분합"); ax.set_ylim(0, 1.22)
ax.set_title("가르는 것은 무엇을 바꾸느냐가 아니라 계수를 나눠 쓰느냐다",
             fontsize=10, pad=7)
fig.tight_layout(); fig.savefig(D / "ratio.pdf"); plt.close(fig)
print("ok")
