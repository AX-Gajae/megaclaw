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

RED, GRN, BLU, GRY, INK = "#a33b3b", "#2f6f4f", "#3c5f8a", "#9aa0a8", "#3b3b3b"
# (이름, 웹툰 2106행, 팝업 14행, 색)
T = [("F9", .5964, .6341, GRN), ("F6", .5597, .5272, GRN),
     ("F21", .5957, .0880, BLU), ("F23", .5610, .0454, GRY),
     ("F10", .7354, .0000, BLU), ("F8", .5260, .0000, RED),
     ("F18", .5490, .0000, RED)]

fig, ax = plt.subplots(figsize=(6.6, 3.5))
x0, x1 = 0.0, 1.0
# 점은 진짜 값에 찍고 **글자만** 흩는다
# 왼쪽은 값 넷이 0.012 안에 뭉쳐 있어 절대 위치로 고르게 흩는다(값 순서 유지)
LABY = {"F8": .437, "F18": .487, "F6": .537, "F23": .587,
        "F21": .637, "F9": .687, "F10": .737}
RDY = {"F9": 0.0, "F6": 0.0, "F21": .010, "F23": -.014,
       "F10": .014, "F18": -.014, "F8": -.042}
for nm, w, p, c in T:
    ax.plot([x0, x1], [w, p], "-o", color=c, lw=1.6, ms=6.5, zorder=4,
            alpha=.92)
    ax.plot([x0 - 0.038, x0 - 0.008], [LABY[nm], w], "-", color=c,
            lw=0.7, alpha=.5, zorder=3)
    ax.text(x0 - 0.045, LABY[nm], f"{nm}  {w:+.3f}", fontsize=7.4,
            color=c, ha="right", va="center")
    ax.text(x1 + 0.045, p + RDY[nm], f"{p:+.4f}  {nm}", fontsize=7.4,
            color=c, ha="left", va="center")
ax.set_xlim(-0.42, 1.42)
ax.set_ylim(-0.09, 0.82)
ax.set_xticks([x0, x1])
ax.set_xticklabels(["웹툰\n학습 2,106행", "팝업\n관측 학습 14행"], fontsize=8.4)
ax.tick_params(axis="y", labelsize=7.4)
ax.set_ylabel("라벨을 그대로 준 전용 열의 이득", fontsize=8.0)
ax.axhline(0, color=INK, lw=0.9, zorder=2)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.set_title("큰 도메인에서는 일곱이 다 똑같다 --- 갈리는 것은 작은 쪽에서다",
             fontsize=10.0, pad=10)
ax.text(0.5, 0.775, "웹툰 폭 0.526$\\sim$0.735", fontsize=7.6, color=INK,
        ha="center")
ax.text(0.5, 0.725, "팝업 폭 0.000$\\sim$0.634", fontsize=7.6, color=RED,
        ha="center")
fig.subplots_adjust(left=.155, right=.845, top=.845, bottom=.155)
fig.savefig(D / "hearing.pdf"); plt.close(fig)
print("ok")
