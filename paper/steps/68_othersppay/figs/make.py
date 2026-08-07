import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import paper.figs  # noqa: F401,E402
D = Path(__file__).resolve().parent
ROWS = [("웹툰", 27.3, -0.0766, -0.0209), ("애니", 23.2, -0.0441, -0.0103),
        ("아이돌", 1.0, -0.2672, -0.0026), ("게임", 8.6, -0.0141, -0.0012),
        ("모바일", 16.9, -0.0074, -0.0012), ("펀딩", 3.1, -0.0005, -0.0000),
        ("세계애니", 11.5, +0.0011, +0.0001), ("도서", 6.2, +0.0158, +0.0010),
        ("팝업", 2.3, +0.0817, +0.0018)]
fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.5),
                         gridspec_kw={"width_ratios": [1, 1], "wspace": 0.32})
ax = axes[0]
R = sorted(ROWS, key=lambda r: r[2])
y = np.arange(len(R))[::-1]
cs = ["#a33b3b" if r[0] != "모바일" else "#2f5fa3" for r in R]
ax.barh(y, [r[2] for r in R], color=cs, height=0.66)
ax.axvline(0, color="#333", lw=0.8)
ax.set_yticks(y); ax.set_yticklabels([f"{r[0]} ({r[1]:.0f}\\%)" for r in R], fontsize=7.2)
ax.set_xlabel("도메인 $\\rho$ 변화")
ax.set_title("도메인마다 얼마나", fontsize=9, pad=6)
ax = axes[1]
mob = sum(r[3] for r in ROWS if r[0] == "모바일")
oth = sum(r[3] for r in ROWS if r[0] != "모바일")
ax.bar([0, 1], [mob, oth], color=["#2f5fa3", "#a33b3b"], width=0.55)
ax.axhline(0, color="#333", lw=0.8)
ax.set_xticks([0, 1]); ax.set_xticklabels(["모바일\n(자료를 고친 곳)",
                                           "나머지 여덟\n(자료가 그대로인 곳)"],
                                          fontsize=7.6)
for xx, v in ((0, mob), (1, oth)):
    ax.text(xx, v - 0.0016, f"{v:+.4f}", ha="center", va="top", fontsize=8.4)
ax.text(1, -0.0295, "96\\%", ha="center", fontsize=9, color="#a33b3b")
ax.set_ylabel("판 $\\rho$ 기여")
ax.set_ylim(-0.037, 0.004)
ax.set_title("판에 낸 몫", fontsize=9, pad=6)
fig.suptitle("모바일 가격 눈금을 고치면 --- 값은 모바일에서만 바뀌는데 "
             "판은 웹툰에서 무너진다", fontsize=10, y=1.0)
fig.tight_layout(); fig.savefig(D / "whopays.pdf"); plt.close(fig)
print("ok")
