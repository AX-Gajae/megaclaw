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
R = {"세계애니": (25.5, +0.0146, -0.0081), "웹툰": (20.3, +0.0297, -0.0045),
     "모바일": (15.0, -0.0130, -0.0099), "애니": (14.1, -0.0073, -0.0284),
     "펀딩": (3.1, -0.0230, +0.0645), "게임": (2.5, +0.0145, +0.0171),
     "시장팝업": (0.97, +0.2493, +0.0088), "도서": (0.77, +0.2806, -0.1661),
     "아이돌": (0.52, -0.4964, +0.2420)}

fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.35),
                         gridspec_kw={"width_ratios": [1, 1.05], "wspace": 0.40})

ax = axes[0]
for nm, (sh, a, b) in R.items():
    c = RED if sh < 1 else (BLU if sh < 10 else GRY)
    ax.scatter(a, b, s=58, color=c, zorder=3, edgecolor="white", linewidth=.8)
    dx, dy = (6, 5)
    if nm in ("모바일", "웹툰"): dy = -12
    if nm == "도서": dx, dy = (-4, -14)
    ax.annotate(nm, (a, b), textcoords="offset points", xytext=(dx, dy),
                fontsize=6.6, color=INK)
lo, hi = -0.56, 0.34
ax.plot([lo, hi], [-np.array([lo, hi])[0], -np.array([lo, hi])[1]], ls=":",
        lw=.9, color=GRY, zorder=1)
ax.axhline(0, color=INK, lw=.8, zorder=2); ax.axvline(0, color=INK, lw=.8, zorder=2)
ax.set_xlim(lo, hi); ax.set_ylim(-0.22, 0.30)
ax.set_xlabel("풀링 이득 (풀링 $-$ 혼자, 노트 317)", fontsize=7.7)
ax.set_ylabel("가중 이득 (가중 $-$ 기준)", fontsize=7.7)
ax.tick_params(labelsize=6.9)
ax.set_title("가중이 풀링을 되돌린다 --- 피어슨 $-$0.888", fontsize=8.4, pad=8)
for s_ in ("top", "right"):
    ax.spines[s_].set_visible(False)
ax.grid(lw=.4, color="#e3e3e3", zorder=0)
ax.text(-0.545, 0.265, "점선 = 완전히 되돌린다면", fontsize=6.4, color=GRY)
hs = [plt.Line2D([], [], marker="o", ls="", color=c, ms=6)
      for c in (RED, BLU, GRY)]
ax.legend(hs, ["몫 <1%", "1~10%", ">10%"], fontsize=6.5, frameon=False,
          loc="lower right")

# --- 오른쪽: 재배분 -----------------------------------------------------
ax = axes[1]
S = [("아이돌", 25, 0.1012, 0.3432, GRN), ("도서", 163, 0.3895, 0.2234, RED)]
x = np.arange(len(S)); w = 0.34
for xx, (nm, n, a, b, c) in zip(x, S):
    ax.bar(xx - w/2, a, w, color=GRY, zorder=3, label="기준" if xx == 0 else None)
    ax.bar(xx + w/2, b, w, color=c, zorder=3, label="가중" if xx == 0 else None)
    ax.text(xx - w/2, a + 0.012, f"{a:.3f}", ha="center", fontsize=7.0, color=GRY)
    ax.text(xx + w/2, b + 0.012, f"{b:.3f}", ha="center", fontsize=7.0, color=c)
    ax.text(xx, -0.045, f"유보 {n}행\n{(b-a)*n:+.1f} 순위단위", ha="center",
            fontsize=6.6, color=c)
ax.set_xticks(x); ax.set_xticklabels([s[0] for s in S], fontsize=8.4)
ax.set_ylim(-0.09, 0.48); ax.set_xlim(-0.6, 1.75)
ax.set_ylabel("유보 rho", fontsize=8)
ax.tick_params(axis="y", labelsize=7.0)
ax.set_title("아이돌이 얻는 것보다 도서가 잃는 게 크다", fontsize=8.4, pad=8)
ax.legend(fontsize=6.9, frameon=False, loc="upper right")
for s_ in ("top", "right"):
    ax.spines[s_].set_visible(False)
ax.grid(axis="y", lw=.4, color="#e3e3e3", zorder=0)
ax.text(1.28, 0.30, "판\n0.4799 $\\to$ 0.4652\n$t{=}{-}2.70$", fontsize=7.0,
        color=RED, ha="center")

fig.suptitle("손잡이를 찾았는데 배분일 뿐이다", fontsize=10.4, y=1.03)
fig.savefig(D / "realloc.pdf", bbox_inches="tight")
fig.savefig(D / "realloc.png", dpi=150, bbox_inches="tight")
print("ok")
