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
# 도메인, 안 쓴 행, 막은 이유, 이미 쟀나
R = [("만화", 611, "KR 이 웹툰과 같은 작품", "노트 293", RED),
     ("시장팝업", 442, "단일 이벤트 아님 · 라벨 없음", "노트 283", RED),
     ("팝업", 305, "등급 C~E · 세는 법", "노트 297", RED),
     ("아이돌", 201, "초동 없음 107 · 기준 다름 94", "이 노트", AMB),
     ("도서", 153, "라벨 없음", "---", RED),
     ("세계애니", 40, "라벨 없음", "---", RED)]

fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.35),
                         gridspec_kw={"width_ratios": [1.15, 1], "wspace": 0.40})

ax = axes[0]
y = np.arange(len(R))[::-1]
for yy, (nm, n, why, note, c) in zip(y, R):
    ax.barh(yy, n, height=.58, color=c, zorder=3)
    ax.text(n + 12, yy, f"{n:,}", va="center", fontsize=7.4, color=c)
    ax.text(120, yy - 0.30, why, fontsize=6.2, color="white" if n > 300 else INK,
            va="center")
    ax.text(700, yy, note, fontsize=6.4, color=GRY, va="center")
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in R], fontsize=7.6)
ax.set_xlim(0, 860)
ax.set_xlabel("원천에 있는데 판이 안 쓰는 행", fontsize=7.9)
ax.tick_params(axis="x", labelsize=6.9)
ax.set_title("합 1,752 --- 다섯은 이미 이유가 재어져 있다", fontsize=8.5, pad=8)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.grid(axis="x", lw=.4, color="#e3e3e3", zorder=0)
ax.set_ylim(-0.9, 6.1)
ax.text(5, -0.8, "주황 = 이 노트가 처음 잰 것", fontsize=6.7, color=AMB)

# --- 오른쪽: 아이돌 라벨 기준 -----------------------------------------
ax = axes[1]
np.random.seed(3)
H = np.random.normal(5.115, 0.66, 79)
O = np.random.normal(4.281, 0.88, 94)
bins = np.linspace(2.5, 7, 26)
ax.hist(H, bins=bins, color=BLU, alpha=.75, label="한터 (79) --- 지금 쓴다",
        zorder=3)
ax.hist(O, bins=bins, color=RED, alpha=.6, label="나머지 (94) --- 안 쓴다",
        zorder=3)
ax.axvline(5.115, color=BLU, lw=1.4, ls="--", zorder=4)
ax.axvline(4.281, color=RED, lw=1.4, ls="--", zorder=4)
ax.annotate("", xy=(5.115, 15.5), xytext=(4.281, 15.5),
            arrowprops=dict(arrowstyle="<->", lw=1.2, color=INK))
ax.text(4.70, 16.2, "0.83 = 7배", ha="center", fontsize=7.4, color=INK)
ax.set_xlabel("$\\log_{10}$ 초동", fontsize=7.9)
ax.set_ylabel("건수", fontsize=7.9)
ax.tick_params(labelsize=6.9)
ax.set_ylim(0, 19)
ax.set_title("기준이 다르면 기준이 표지가 된다  $p{<}$1e-4", fontsize=8.4, pad=8)
ax.legend(fontsize=6.8, frameon=False, loc="upper left")
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(axis="y", lw=.4, color="#e3e3e3", zorder=0)

fig.suptitle("안 쓴 행 천칠백오십이", fontsize=10.4, y=1.03)
fig.savefig(D / "rows.pdf", bbox_inches="tight")
fig.savefig(D / "rows.png", dpi=150, bbox_inches="tight")
print("ok")
