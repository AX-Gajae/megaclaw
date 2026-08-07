import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import paper.figs  # noqa: F401,E402
D = Path(__file__).resolve().parent
ROWS = [("아이돌", 1.0, 0.154, 0.285), ("웹툰", 27.3, 0.380, 0.404),
        ("펀딩", 3.1, 0.236, 0.242), ("세계애니", 11.5, 0.520, 0.524),
        ("팝업", 2.3, 0.391, 0.386), ("애니", 23.2, 0.487, 0.476),
        ("모바일", 16.9, 0.537, 0.526), ("도서", 6.2, 0.321, 0.296),
        ("게임", 8.6, 0.640, 0.556)]
fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.6),
                         gridspec_kw={"width_ratios": [1.35, 1], "wspace": 0.34})
ax = axes[0]
y = np.arange(len(ROWS))[::-1]
for yy, (dm, w, a, b) in zip(y, ROWS):
    c = "#2f6f4f" if b > a else "#a33b3b"
    ax.plot([a, b], [yy, yy], color=c, lw=1.6, zorder=2)
    ax.scatter([a], [yy], s=22, color="#999", zorder=3)
    ax.scatter([b], [yy], s=38, color=c, zorder=4)
    ax.text(max(a, b) + 0.012, yy, f"{b-a:+.3f}", va="center", fontsize=7,
            color=c)
ax.set_yticks(y); ax.set_yticklabels([f"{r[0]} ({r[1]:.0f}\\%)" for r in ROWS],
                                     fontsize=7.4)
ax.set_xlim(0.10, 0.76); ax.set_xlabel("도메인 $\\rho$  (회색 전 $\\to$ 색 후)")
ax.set_title("도메인은 크게 움직인다", fontsize=9.4, pad=6)
ax = axes[1]
net = sum(r[1] / 100 * (r[3] - r[2]) for r in ROWS)
mov = sum(r[1] / 100 * abs(r[3] - r[2]) for r in ROWS)
ax.bar([0, 1], [mov, abs(net)], color=["#8a6d9f", "#8a8f98"], width=0.5)
ax.set_xticks([0, 1]); ax.set_xticklabels(["움직인 총량\n$\\sum w|\\Delta|$",
                                           "판이 본 것\n$|\\sum w\\Delta|$"],
                                          fontsize=8)
for xx, v in ((0, mov), (1, abs(net))):
    ax.text(xx, v + 0.0007, f"{v:.4f}", ha="center", fontsize=9)
ax.set_ylim(0, 0.027); ax.set_ylabel("판 $\\rho$ 단위")
ax.set_title("판은 거의 못 본다", fontsize=9.4, pad=6)
fig.suptitle("부호화 규약 하나를 바꿨을 뿐인데 --- 자료는 한 글자도 안 바뀌었다",
             fontsize=10, y=1.0)
fig.tight_layout(); fig.savefig(D / "zerosum.pdf"); plt.close(fig)
print("ok")
