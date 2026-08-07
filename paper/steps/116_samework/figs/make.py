import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import paper.figs  # noqa: F401,E402
matplotlib.rcParams["axes.unicode_minus"] = False
D = Path(__file__).resolve().parent

GRN, RED, GRY, INK = "#2f6f4f", "#a33b3b", "#9aa0a8", "#3b3b3b"
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.15),
                         gridspec_kw={"width_ratios": [1.05, 1], "wspace": 0.40})

# --- 왼쪽: 175건의 정체 ------------------------------------------------
ax = axes[0]
S = [("이름이 붙는 쌍", 175, GRY),
     ("만화가 먼저\n(진짜 크로스 IP)", 23, GRN),
     ("lab 만화 도메인 안", 0, RED)]
x = np.arange(len(S))
for xx, (nm, n, c) in zip(x, S):
    ax.bar(xx, max(n, 1.5), color=c, width=.5, zorder=3,
           alpha=.75 if n else 1)
    ax.text(xx, max(n, 1.5) + 5, f"{n}", ha="center", fontsize=9.0, color=c)
ax.set_xticks(x); ax.set_xticklabels([s[0] for s in S], fontsize=7.4)
ax.set_ylim(0, 205)
ax.tick_params(axis="y", labelsize=7.2)
ax.set_ylabel("웹툰 2,817행 중", fontsize=7.8)
ax.set_title("별칭 사전이 연 175건의 정체", fontsize=9.4, pad=6)
ax.text(0.55, 150, "152건은 같은 작품이\n두 곳에 있는 것", fontsize=7.0,
        color=INK)

# --- 오른쪽: lab 이 이미 걸러 놓았다 -------------------------------------
ax = axes[1]
C = [("JP", 1789, 1789), ("KR", 556, 0), ("CN", 55, 0)]
y = np.arange(len(C))[::-1]
w = 0.36
for yy, (nm, a, b) in zip(y, C):
    ax.barh(yy + w / 2, a, height=w, color=GRY, alpha=.6, zorder=3)
    ax.barh(yy - w / 2, b, height=w, color=GRN, zorder=3)
    ax.text(a + 40, yy + w / 2, f"{a:,}", va="center", fontsize=7.2, color=INK)
    ax.text(max(b, 0) + 40, yy - w / 2, f"{b:,}", va="center", fontsize=7.2,
            color=GRN if b else RED)
ax.set_yticks(y); ax.set_yticklabels([c[0] for c in C], fontsize=8.0)
ax.set_xlim(0, 2200)
ax.tick_params(axis="x", labelsize=7.2)
ax.set_xlabel("만화 레코드 수", fontsize=7.8, labelpad=2)
ax.set_title("연한 = 레코드 전체 · 진한 = lab 도메인", fontsize=8.8, pad=6)
ax.text(300, 0.05, "웹툰과 붙는 것은 KR 556건인데\nlab 만화는 JP 만 쓴다",
        fontsize=7.0, color=RED)
fig.suptitle("도메인이 만나는 자리는 대개 같은 작품이다", fontsize=10.4,
             y=1.005)
fig.subplots_adjust(left=.118, right=.985, top=.795, bottom=.185)
fig.savefig(D / "same.pdf"); plt.close(fig)
print("ok")
