import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import paper.figs  # noqa: F401,E402
D = Path(__file__).resolve().parent

fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.4),
                         gridspec_kw={"width_ratios": [1, 1.15], "wspace": 0.32})
# 왼쪽 — 판 사다리
ax = axes[0]
S = [("노트 242\n17축", 0.4569, "#8a8f98"), ("웹툰 태그\n19축", 0.4623, "#2f6f4f"),
     ("애니 태그\n19축", 0.4649, "#2f6f4f"), ("둘 다\n21축", 0.4687, "#1f5138")]
x = np.arange(len(S))
ax.bar(x, [s[1] - 0.45 for s in S], bottom=0.45, color=[s[2] for s in S], width=0.58)
for xx, s in zip(x, S):
    ax.text(xx, s[1] + 0.0006, f"{s[1]:.4f}", ha="center", fontsize=8.2)
ax.set_xticks(x); ax.set_xticklabels([s[0] for s in S], fontsize=7.6)
ax.set_ylim(0.45, 0.4735); ax.set_ylabel("판 $\\rho$")
ax.set_title("거의 가법이다 (교차 $-$0.0016)", fontsize=9.4, pad=6)

# 오른쪽 — 도메인별
ax = axes[1]
R = [("애니", +0.0423, 0.0141, 3.01), ("아이돌", -0.0377, 0.0552, -0.68),
     ("웹툰", -0.0075, 0.0028, -2.69), ("게임", -0.0063, 0.0046, -1.36),
     ("펀딩", +0.0045, 0.0221, 0.20), ("팝업", -0.0042, 0.0147, -0.28),
     ("도서", -0.0023, 0.0098, -0.23), ("세계애니", -0.0023, 0.0018, -1.27),
     ("모바일", -0.0019, 0.0027, -0.72)]
y = np.arange(len(R))[::-1]
for yy, (dm, v, se, t) in zip(y, R):
    real = abs(t) >= 2
    c = ("#2f6f4f" if v > 0 else "#a33b3b") if real else "#c9ccd1"
    ax.barh(yy, v, color=c, height=0.62)
    ax.errorbar(v, yy, xerr=se, fmt="none", ecolor="#666", elinewidth=0.9,
                capsize=2, zorder=3)
    if real:
        ax.text(v + (0.006 if v > 0 else -0.006), yy, f"$t{{=}}{t:+.2f}$",
                fontsize=6.8, va="center", ha="left" if v > 0 else "right",
                color=c)
ax.axvline(0, color="#333", lw=0.9)
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in R], fontsize=7.4)
ax.set_xlim(-0.105, 0.075)
ax.set_xlabel("애니 태그 축을 더했을 때 $\\rho$ 변화 $\\pm$ 짝 SE")
ax.set_title("애니가 얻고 웹툰이 조금 낸다", fontsize=9.4, pad=6)
fig.suptitle("애니 태그 내용 --- 판 0.4623 $\\to$ 0.4687", fontsize=10, y=1.0)
fig.tight_layout(); fig.savefig(D / "board.pdf"); plt.close(fig)
print("ok")
