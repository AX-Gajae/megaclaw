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
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.25),
                         gridspec_kw={"width_ratios": [1.1, 1], "wspace": 0.42})

# --- 왼쪽: 청력 문턱을 넘겨도 이득이 안 나온다 --------------------------
ax = axes[0]
C = [("문턱 40→15\n(노트 296)", 16, +0.0127, 0.0312, RED),
     ("좁힘→넓힘\n(이 노트)", 73, +0.0116, 0.0849, BLU)]
x = np.array([0, 1])
for xx, (nm, tr, dd, se, c) in zip(x, C):
    ax.errorbar(xx, dd, yerr=2 * se, fmt="o", color=c, ms=6.5, capsize=5,
                lw=1.8, zorder=3)
    ax.text(xx + 0.13, dd, f"{dd:+.4f}", fontsize=8.0, color=c, va="center")
    ax.text(xx, -0.21, f"학습 {tr}행", ha="center", fontsize=7.4,
            color=(RED if tr < 22 else GRN))
    ax.text(xx, -0.243, "청력 22 아래" if tr < 22 else "청력 22 위",
            ha="center", fontsize=6.6, color=(RED if tr < 22 else GRN))
ax.axhline(0, color=INK, lw=.9, zorder=2)
ax.set_xticks(x); ax.set_xticklabels([c[0] for c in C], fontsize=7.4)
ax.set_xlim(-0.5, 1.62)
ax.set_ylim(-0.26, 0.20)
ax.set_ylabel("팝업 rho 의 변화 ($\\pm$2$\\times$짝SE)", fontsize=8)
ax.tick_params(axis="y", labelsize=7.2)
ax.set_title("문턱을 넘겨도 0 을 못 벗어난다", fontsize=8.6, pad=8)
ax.text(0.55, 0.163, "$t{=}0.41$          $t{=}0.14$", fontsize=7.2,
        color=GRY, ha="center")
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(axis="y", lw=.4, color="#e3e3e3", zorder=0)

# --- 오른쪽: 가드 19 ----------------------------------------------------
ax = axes[1]
G = [("trendcalwikitag\n(챔피언)", True, "학습 16 · 유보 59"),
     ("narrow_tcwt\n(같은 코드 경로)", True, "학습 16 · 유보 59"),
     ("wide_trendcal", False, "노트 292"),
     ("wide_trendcalpop", False, "노트 292"),
     ("wide_tcwt\n(이 노트)", False, "학습 73 · rho=-0.387")]
y = np.arange(len(G))[::-1]
for yy, (nm, ok, note) in zip(y, G):
    c = GRN if ok else RED
    ax.barh(yy, 1, height=.55, color=c, alpha=.92, zorder=3)
    ax.text(0.045, yy, "통과" if ok else "실패", va="center", fontsize=8.0,
            color="white", weight="bold")
    ax.text(1.05, yy, note, va="center", fontsize=6.8, color=GRY)
ax.set_yticks(y); ax.set_yticklabels([g[0] for g in G], fontsize=7.0)
ax.set_xlim(0, 2.5); ax.set_xticks([])
ax.set_title("넓힌 판은 셋 다 출처 가드에 걸린다", fontsize=8.6, pad=8)
for s in ("top", "right", "bottom", "left"):
    ax.spines[s].set_visible(False)
ax.set_ylim(-0.9, 4.75)
ax.text(0.0, -0.75, "가드 19(출처) --- 계열을 가로지르는 동시 결측 뭉치가 라벨을 예측하나",
        fontsize=6.5, color=INK)

fig.suptitle("문턱을 넘었는데 조용하다", fontsize=10.4, y=1.03)
fig.savefig(D / "crossed.pdf", bbox_inches="tight")
fig.savefig(D / "crossed.png", dpi=150, bbox_inches="tight")
print("ok")
