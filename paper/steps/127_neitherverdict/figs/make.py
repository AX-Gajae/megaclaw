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
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.3),
                         gridspec_kw={"width_ratios": [1, 1.12], "wspace": 0.44})

# --- 왼쪽: 자리당 비용 --------------------------------------------------
ax = axes[0]
C = [("① 안 오른다\n47자리", -0.0121, 0.0047, 47, RED),
     ("③ 이미 있다\n17자리", -0.0068, 0.0035, 17, AMB)]
x = np.arange(len(C))
for xx, (nm, d, se, k, c) in zip(x, C):
    ax.bar(xx, -1e4 * d / k, 0.46, color=c, zorder=3)
    ax.text(xx, -1e4 * d / k + 0.13, f"{-1e4*d/k:.2f}", ha="center",
            fontsize=8.6, color=c)
    ax.text(xx, -0.30, f"판 {d:+.4f}\n$t{{=}}${d/se:+.2f} · 문턱 {2*se:.4f}",
            ha="center", fontsize=6.5, color=INK)
ax.set_xticks(x); ax.set_xticklabels([c[0] for c in C], fontsize=7.6)
ax.set_ylim(-0.95, 5.0)
ax.set_ylabel("자리 하나를 끄는 값 ($\\times 10^{-4}$ rho)", fontsize=7.8)
ax.tick_params(axis="y", labelsize=7.0)
ax.set_title("③ 자리가 ① 자리보다 비싸다", fontsize=8.6, pad=8)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(axis="y", lw=.4, color="#e3e3e3", zorder=0)
ax.text(0.5, 4.62, "③ 이 ① 보다 자리당 1.57배 비싸다", ha="center",
        fontsize=7.4, color=AMB)

# --- 오른쪽: 도메인별 --------------------------------------------------
ax = axes[1]
R = [("도서", -0.0407, 0.0192, 0), ("게임", -0.0126, 0.0172, 3),
     ("애니", -0.0119, 0.0061, 3), ("아이돌", -0.0085, 0.0553, 0),
     ("세계애니", -0.0080, 0.0069, 4), ("웹툰", -0.0075, 0.0063, 1),
     ("시장팝업", -0.0060, 0.0298, 0), ("팝업", +0.0072, 0.0336, 0),
     ("모바일", +0.0089, 0.0058, 4), ("펀딩", +0.0263, 0.0195, 0)]
y = np.arange(len(R))[::-1]
for yy, (nm, d, se, k) in zip(y, R):
    t = d / se
    c = RED if t < -1.9 else GRY
    ax.errorbar(d, yy, xerr=2 * se, fmt="o", color=c, ms=4.6, capsize=3,
                lw=1.4, zorder=3)
    ax.text(0.075, yy, f"{k}축", va="center", ha="right", fontsize=6.4,
            color=(RED if (k == 0 and t < -1.9) else GRY),
            weight=("bold" if (k == 0 and t < -1.9) else "normal"))
ax.axvline(0, color=INK, lw=.9, zorder=2)
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in R], fontsize=7.2)
ax.set_xlim(-0.095, 0.082)
ax.set_xlabel("'이미 있다' 를 껐을 때 rho 변화 ($\\pm$2$\\times$짝SE)", fontsize=7.6)
ax.tick_params(axis="x", labelsize=6.8)
ax.set_title("도서는 축을 하나도 안 껐는데 제일 크게 움직인다",
             fontsize=8.4, pad=8)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.grid(axis="x", lw=.4, color="#e3e3e3", zorder=0)
ax.set_ylim(-1.0, 9.75)
ax.text(-0.093, -0.85, "남의 도메인 축을 끄면 공유 적합이 바뀐다", fontsize=6.7,
        color=RED)

fig.suptitle("판정 셋 중 어느 것도 뺄 근거가 아니다", fontsize=10.4, y=1.03)
fig.savefig(D / "neither.pdf", bbox_inches="tight")
fig.savefig(D / "neither.png", dpi=150, bbox_inches="tight")
print("ok")
