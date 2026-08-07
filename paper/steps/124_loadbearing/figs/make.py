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
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.35),
                         gridspec_kw={"width_ratios": [1.12, 1], "wspace": 0.42})

# 도메인, 원래, 막음, 짝SE, 끈 축 수
R = [("도서", 0.3988, 0.2682, 0.0454, 9),
     ("펀딩", 0.2444, 0.1223, 0.0524, 9),
     ("애니", 0.5012, 0.4853, 0.0061, 2),
     ("시장팝업", 0.4075, 0.4049, 0.0334, 0),
     ("팝업", 0.3750, 0.3250, 0.0538, 0),
     ("세계애니", 0.5336, 0.5387, 0.0093, 4),
     ("게임", 0.6214, 0.6258, 0.0144, 6),
     ("웹툰", 0.4619, 0.4671, 0.0067, 4),
     ("모바일", 0.5435, 0.5547, 0.0073, 5),
     ("아이돌", 0.0751, 0.0961, 0.0650, 4)]

ax = axes[0]
y = np.arange(len(R))[::-1]
for yy, (nm, a, b, se, k) in zip(y, R):
    d = b - a
    t = d / se if se else 0
    c = RED if t < -2 else (GRN if t > 2 else GRY)
    ax.errorbar(d, yy, xerr=2 * se, fmt="o", color=c, ms=4.8, capsize=3.2,
                lw=1.5, zorder=3)
    ax.text(0.090, yy, f"{k}축 끔", va="center", ha="right", fontsize=6.4,
            color=(c if abs(t) > 2 else GRY))
ax.axvline(0, color=INK, lw=.9, zorder=2)
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in R], fontsize=7.4)
ax.set_xlim(-0.185, 0.095)
ax.set_xlabel("도메인 rho 의 변화 ($\\pm$2$\\times$짝SE)", fontsize=7.8)
ax.tick_params(axis="x", labelsize=6.8)
ax.set_title("'정보 없음' 축을 끄면 두 도메인이 무너진다", fontsize=8.5, pad=8)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.grid(axis="x", lw=.4, color="#e3e3e3", zorder=0)
ax.set_ylim(-1.1, 9.8)
ax.text(-0.182, -0.92, "판 0.4851 $\\to$ 0.4730 · $t{=}{-}2.58$ · 문턱 0.0094 --- 갈린다",
        fontsize=6.8, color=RED)

# --- 오른쪽: 값이냐 표시자냐 -------------------------------------------
ax = axes[1]
S = [("도서", 0.3988, 0.2682, 0.2444), ("펀딩", 0.2444, 0.1223, 0.1127),
     ("판", 0.4851, 0.4730, 0.4736)]
x = np.arange(len(S)); w = 0.26
for i, (lab, col) in enumerate((("원래", GRY), ("값+표시자 끔", RED),
                                ("값만 중립", "#c9776f"))):
    ax.bar(x + (i - 1) * w, [s[1 + i] for s in S], w, color=col, label=lab,
           zorder=3)
for xx, s in zip(x, S):
    for i in range(3):
        ax.text(xx + (i - 1) * w, s[1 + i] + 0.012, f"{s[1+i]:.3f}",
                ha="center", fontsize=6.0, color=INK)
ax.set_xticks(x); ax.set_xticklabels([s[0] for s in S], fontsize=8.0)
ax.set_ylim(0, 0.60); ax.set_ylabel("rho", fontsize=8)
ax.tick_params(axis="y", labelsize=7.0)
ax.set_title("값이 일한다 --- 표시자를 남겨도 무너진다", fontsize=8.5, pad=8)
ax.legend(fontsize=6.6, frameon=False, loc="upper left", ncol=1)
for s_ in ("top", "right"):
    ax.spines[s_].set_visible(False)
ax.grid(axis="y", lw=.4, color="#e3e3e3", zorder=0)

fig.suptitle("빈 칸인 줄 알았더니 기둥이었다", fontsize=10.4, y=1.03)
fig.savefig(D / "load.pdf", bbox_inches="tight")
fig.savefig(D / "load.png", dpi=150, bbox_inches="tight")
print("ok")
