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

GRN, RED, BLU, GRY, INK = "#2f6f4f", "#a33b3b", "#3c5f8a", "#9aa0a8", "#3b3b3b"
N = [16, 54, 80, 259, 2106]
S = [("F9", [.6341, .6411, .6709, .3839, .5964], GRN, "-"),
     ("F6", [.5272, .5349, .6442, .3595, .5597], GRN, "--"),
     ("F8", [.0000, .6623, .4325, .3815, .5260], RED, "-"),
     ("F18", [.0000, .5677, .3472, .3561, .5490], RED, "--"),
     ("F23", [.0454, .4213, .3607, .3280, .5610], GRY, "-"),
     ("F21", [.0880, .2459, .3107, .3140, .5957], BLU, "--"),
     ("F10", [.0000, .0000, .0000, .4034, .7354], BLU, "-")]

fig, ax = plt.subplots(figsize=(6.9, 3.7))
ax.axvspan(10, 40, color="#f3e6e6", zorder=1)
ax.axvline(40, color=RED, lw=1.1, ls=":", zorder=2)
ax.text(38, .775, "40행 = 2$\\times$잎 하한", fontsize=7.0, color=RED,
        ha="right")
ax.axvspan(80, 259, color="#e6ebf3", zorder=1)
ax.text(88, .690, "F10 의 문턱은\n이 사이", fontsize=7.0, color=BLU)
# 오른쪽 끝값 넷이 0.55 언저리에 뭉쳐 있어 절대 위치로 흩고 인출선을 단다
LY = {"F10": .740, "F9": .650, "F21": .592, "F23": .534, "F6": .476,
      "F18": .418, "F8": .360}
for nm, g, c, ls in S:
    ax.plot(N, g, ls, color=c, lw=1.7, marker="o", ms=5.2, zorder=4,
            alpha=.95)
    ax.plot([2106, 2850], [g[-1], LY[nm]], "-", color=c, lw=0.7, alpha=.5,
            zorder=3)
    ax.text(3050, LY[nm], nm, fontsize=7.6, color=c, va="center")
ax.set_xscale("log")
ax.set_xlim(11, 5200)
ax.set_ylim(-0.05, 0.83)
ax.set_xticks([16, 54, 80, 259, 2106])
ax.set_xticklabels(["16\n팝업", "54\n아이돌", "80\n도서", "259\n게임",
                    "2,106\n웹툰"], fontsize=7.4)
ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
ax.tick_params(axis="y", labelsize=7.4)
ax.axhline(0, color=INK, lw=0.9, zorder=3)
ax.set_xlabel("도메인의 배포 학습행 (로그)", fontsize=8.0, labelpad=3)
ax.set_ylabel("라벨을 그대로 준 전용 열의 이득", fontsize=8.0)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
ax.set_title("정식화마다 들리기 시작하는 크기가 다르다", fontsize=10.2, pad=9)
fig.subplots_adjust(left=.105, right=.945, top=.865, bottom=.185)
fig.savefig(D / "curve.pdf"); plt.close(fig)
print("ok")
