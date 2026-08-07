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
AMB = "#b07a3a"
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.35),
                         gridspec_kw={"width_ratios": [1.15, 1], "wspace": 0.40})

# 도메인, 새롭다, 이미 있다, 안 오른다, 못 잰다, 학습행
R = [("웹툰", 11, 1, 4, 2, 2106), ("애니", 9, 3, 2, 4, 1467),
     ("게임", 7, 3, 6, 6, 259), ("만화", 3, 2, 4, 9, 1783),
     ("모바일", 3, 4, 5, 6, 1559), ("세계애니", 1, 4, 4, 9, 2648),
     ("아이돌", 2, 0, 4, 12, 54), ("도서", 0, 0, 9, 9, 80),
     ("펀딩", 0, 0, 9, 9, 320), ("시장팝업", 0, 0, 0, 18, 101),
     ("팝업", 0, 0, 0, 1, 16)]

ax = axes[0]
y = np.arange(len(R))[::-1]
for yy, (nm, a, b, c, d, tr) in zip(y, R):
    x0 = 0
    for v, col in ((a, GRN), (b, AMB), (c, RED), (d, "#dfe2e5")):
        if v:
            ax.barh(yy, v, left=x0, height=.62, color=col, zorder=3)
            if v >= 2:
                ax.text(x0 + v / 2, yy, str(v), ha="center", va="center",
                        fontsize=6.6, color=("white" if col != "#dfe2e5" else GRY))
        x0 += v
    ax.text(x0 + 0.5, yy, f"학습 {tr:,}", va="center", fontsize=6.2, color=GRY)
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in R], fontsize=7.4)
ax.set_xlim(0, 30); ax.set_xlabel("전용 축 자리 (도메인 × 축)", fontsize=7.8)
ax.tick_params(axis="x", labelsize=6.8)
ax.set_title("다섯 도메인은 새로운 축이 하나도 없다", fontsize=8.6, pad=8)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.grid(axis="x", lw=.4, color="#eef0f2", zorder=0)
ax.set_ylim(-0.75, 11.1)
hs = [plt.Rectangle((0, 0), 1, 1, color=c) for c in (GRN, AMB, RED, "#dfe2e5")]
ax.legend(hs, ["새롭다", "이미 있다", "안 오른다", "못 잰다"], fontsize=6.6,
          frameon=False, ncol=1, loc="upper right", bbox_to_anchor=(1.005, 1.02),
          handlelength=1.1, handleheight=.85, labelspacing=.45)

# --- 오른쪽: 같은 축이 도메인마다 다른 일을 한다 -------------------------
ax = axes[1]
AX = ["wiki_level", "wiki_volatility", "cal_month_sin", "cal_weekend",
      "trend_volatility", "cal_dow_sin"]
DM = ["웹툰", "애니", "게임", "만화", "모바일", "세계애니"]
V = {("wiki_level","게임"):1,("wiki_level","만화"):1,("wiki_level","모바일"):2,
     ("wiki_level","세계애니"):0,("wiki_level","애니"):0,("wiki_level","웹툰"):0,
     ("wiki_volatility","게임"):0,("wiki_volatility","만화"):1,("wiki_volatility","모바일"):2,
     ("wiki_volatility","세계애니"):1,("wiki_volatility","애니"):2,("wiki_volatility","웹툰"):0,
     ("cal_month_sin","게임"):2,("cal_month_sin","만화"):2,("cal_month_sin","모바일"):1,
     ("cal_month_sin","세계애니"):1,("cal_month_sin","애니"):0,("cal_month_sin","웹툰"):2,
     ("cal_weekend","게임"):2,("cal_weekend","만화"):0,("cal_weekend","모바일"):2,
     ("cal_weekend","세계애니"):2,("cal_weekend","애니"):1,("cal_weekend","웹툰"):0,
     ("trend_volatility","게임"):0,("trend_volatility","만화"):3,("trend_volatility","모바일"):0,
     ("trend_volatility","세계애니"):3,("trend_volatility","애니"):1,("trend_volatility","웹툰"):0,
     ("cal_dow_sin","게임"):2,("cal_dow_sin","만화"):0,("cal_dow_sin","모바일"):1,
     ("cal_dow_sin","세계애니"):2,("cal_dow_sin","애니"):0,("cal_dow_sin","웹툰"):0}
COL = {0: GRN, 1: AMB, 2: RED, 3: "#dfe2e5"}
for i, a in enumerate(AX):
    for j, dm in enumerate(DM):
        v = V.get((a, dm), 3)
        ax.add_patch(plt.Rectangle((j, len(AX) - 1 - i), .92, .92,
                                   color=COL[v], zorder=3))
ax.set_xlim(-0.1, len(DM) + .1); ax.set_ylim(-0.1, len(AX) + .1)
ax.set_xticks(np.arange(len(DM)) + .46)
ax.set_xticklabels(DM, fontsize=6.8, rotation=32, ha="right")
ax.set_yticks(np.arange(len(AX)) + .46)
ax.set_yticklabels(AX[::-1], fontsize=6.6)
ax.set_title("같은 축이 도메인마다 다른 일을 한다", fontsize=8.6, pad=8)
for s in ("top", "right", "bottom", "left"):
    ax.spines[s].set_visible(False)
ax.tick_params(length=0)

fig.suptitle("축은 큰 도메인만 섬긴다", fontsize=10.4, y=1.03)
fig.savefig(D / "serve.pdf", bbox_inches="tight")
fig.savefig(D / "serve.png", dpi=150, bbox_inches="tight")
print("ok")
