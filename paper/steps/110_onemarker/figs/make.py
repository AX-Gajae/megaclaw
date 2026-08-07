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
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.2),
                         gridspec_kw={"width_ratios": [1, 1.12], "wspace": 0.40})

# --- 왼쪽: 표지 하나가 모형을 이긴다 ------------------------------------
ax = axes[0]
B = [("손 축 관측 표시자\n하나로", 0.4157, RED),
     ("넓힌 판의\n실제 팝업 점수", 0.3582, GRY),
     ("좁은 판의\n팝업 점수", 0.3649, GRY)]
x = np.arange(len(B))
for xx, (nm, v, c) in zip(x, B):
    ax.bar(xx, v, color=c, width=.5, zorder=3, alpha=1 if c == RED else .65)
    ax.text(xx, v + .012, f"{v:.4f}", ha="center", fontsize=8.0, color=c)
ax.axhline(0.3582, color=INK, lw=1.0, ls="--", zorder=4)
ax.set_xticks(x); ax.set_xticklabels([b[0] for b in B], fontsize=7.2)
ax.set_ylim(0, 0.58)
ax.tick_params(axis="y", labelsize=7.2)
ax.set_ylabel("유보 |rho| (팝업)", fontsize=7.8)
ax.set_title("표지 하나가 모형을 이긴다", fontsize=9.4, pad=6)
ax.text(-0.44, 0.545, "넓힌 판 팝업 189행 = 내부 82 + 시장 107", fontsize=6.9,
        color=INK)
ax.text(-0.44, 0.510, "손 축 마스크 내부 98.8% · 시장 0.0%", fontsize=6.9,
        color=RED)

# --- 오른쪽: 무엇이 가르나 ----------------------------------------------
ax = axes[1]
CASE = [("넓힌 팝업", ["공유", "공유", "공유", "공유", "공유", "검색"], RED,
         "계열 둘 --- 행의 출처가 다르다"),
        ("게임", ["검색", "검색", "검색"], GRN, "계열 하나 --- 정상"),
        ("게임", ["위키", "위키", "위키"], GRN, "계열 하나 --- 정상")]
y = [2, 1, 0]
FAMC = {"공유": BLU, "검색": "#7a9ec4", "위키": "#c4a77a"}
for yy, (nm, fams, c, note) in zip(y, CASE):
    for k, f in enumerate(fams):
        ax.add_patch(plt.Rectangle((k * .105, yy - .17), .092, .34,
                                   facecolor=FAMC.get(f, GRY), lw=0))
    ax.text(-0.03, yy, nm, fontsize=7.6, color=c, ha="right", va="center")
    ax.text(len(fams) * .105 + .03, yy, note, fontsize=7.0, color=c,
            va="center")
ax.set_xlim(-0.30, 1.55); ax.set_ylim(-0.9, 2.75)
ax.axis("off")
ax.text(-0.28, 2.58, "유보에서 표시자가 함께 움직이는 뭉치", fontsize=7.6,
        color=INK)
ax.text(-0.28, -0.62, "색 = 축 계열(공유 · 검색 · 위키)", fontsize=6.9,
        color=INK)
ax.text(-0.28, -0.85, "가드: 뭉치가 계열 둘 이상을 가로지르고 라벨을 예측하면 막는다",
        fontsize=6.9, color=INK)
ax.set_title("정보 있는 결측과 어떻게 가르나", fontsize=9.4, pad=6)
fig.suptitle("합친 자리가 곧 표지가 된다", fontsize=10.4, y=1.005)
fig.subplots_adjust(left=.108, right=.985, top=.795, bottom=.16)
fig.savefig(D / "marker.pdf"); plt.close(fig)
print("ok")
