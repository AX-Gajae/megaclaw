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

GRN, RED, GRY, INK, BLU = "#2f6f4f", "#a33b3b", "#9aa0a8", "#3b3b3b", "#33628f"
R = [("문턱 40 대 15\n(노트 296)", 17, 45, 1, 9, -0.0062),
     ("fund\\_cat · F18\n(노트 309)", 15, 45, 1, 9, +0.0038),
     ("fund\\_cat · F6", 4, 45, 0, 9, -0.0003),
     ("mkt 축\n(노트 285)", 0, 45, 0, 9, +0.0007),
     ("팝업 전용 축", 0, 45, 0, 9, 0.0000),
     ("LOO · F18\n(노트 310)", 5, 28, 0, 7, None),
     ("LOO · F6\n(노트 314)", 1, 28, 0, 7, None)]

fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.35),
                         gridspec_kw={"width_ratios": [1.15, 1], "wspace": 0.40})

ax = axes[0]
y = np.arange(len(R))[::-1]
for yy, (nm, st, tot, ast_, atot, net) in zip(y, R):
    f = 100 * st / tot
    ax.barh(yy, f, height=.55, color=RED, zorder=3)
    ax.text(f + 1.5, yy, f"{st}/{tot}", va="center", fontsize=6.9, color=RED)
    ax.text(93, yy, f"이웃 {ast_}/{atot}", va="center", ha="right", fontsize=6.5,
            color=GRY)
ax.axvline(80, color=INK, lw=1.2, ls="--", zorder=4)
ax.text(81, 6.5, "'순서 선다' 문턱 80%", fontsize=6.8, color=INK)
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in R], fontsize=6.8)
ax.set_xlim(0, 96)
ax.set_xlabel("짝짝이 순서가 선 비율 (%)", fontsize=7.8)
ax.tick_params(axis="x", labelsize=6.9)
ax.set_title("일곱 중 하나도 문턱 근처에 못 간다", fontsize=8.6, pad=8)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.grid(axis="x", lw=.4, color="#e3e3e3", zorder=0)
ax.set_ylim(-0.75, 7.3)

# --- 오른쪽: 무엇을 대신 읽나 -----------------------------------------
ax = axes[1]
LV = [("도메인 하나의 값\n(짝SE 붙임)", 3, GRN),
      ("계열로 묶은 값\n(검색 셋 등)", 3, GRN),
      ("무리로 묶은 값\n(나무 대 선형)", 2, "#7aa87f"),
      ("도메인 순서", 0, RED)]
x = np.arange(len(LV))
for xx, (nm, v, c) in zip(x, LV):
    ax.bar(xx, v, 0.55, color=c, zorder=3)
    ax.text(xx, v + 0.08, ["못 읽는다", "", "일부", "읽는다"][min(v, 3)] if False else
            ("읽는다" if v >= 3 else ("일부" if v == 2 else "못 읽는다")),
            ha="center", fontsize=7.4, color=c)
ax.set_xticks(x); ax.set_xticklabels([l[0] for l in LV], fontsize=6.9)
ax.set_yticks([]); ax.set_ylim(0, 3.9)
ax.set_title("이 판에서 읽을 수 있는 것", fontsize=8.6, pad=8)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.text(-0.55, 3.55, "노트 312·313 이 문턱을 넘은 자리 = 앞의 둘",
        fontsize=6.7, color=INK)

fig.suptitle("이 판은 도메인 순서를 읽은 적이 없다", fontsize=10.4, y=1.03)
fig.savefig(D / "never.pdf", bbox_inches="tight")
fig.savefig(D / "never.png", dpi=150, bbox_inches="tight")
print("ok")
