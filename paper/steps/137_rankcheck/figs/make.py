import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import paper.figs  # noqa: F401,E402
sys.path.insert(0, "/Users/ax/world_model")
from lab import ordering
matplotlib.rcParams["axes.unicode_minus"] = False
D = Path(__file__).resolve().parent

GRN, RED, GRY, INK, BLU = "#2f6f4f", "#a33b3b", "#9aa0a8", "#3b3b3b", "#33628f"
F18 = {k: (d, abs(d)/abs(t)) for k, (d, t) in
       {"웹툰": (-0.0773, -2.27), "애니": (-0.0587, -2.03),
        "만화": (-0.0491, -1.93), "모바일": (-0.0341, -1.65),
        "시장팝업": (-0.0222, -1.15), "게임": (-0.0217, -0.88),
        "세계애니": (-0.0125, -0.61), "아이돌": (-0.0106, -0.39)}.items()}
order = sorted(F18, key=lambda k: F18[k][0])   # 빌림이 큰 순(차가 작은 순)

fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.35),
                         gridspec_kw={"width_ratios": [1.05, 1], "wspace": 0.36})

# --- 왼쪽: 짝짝이 확률 행렬 -------------------------------------------
ax = axes[0]
n = len(order)
M = np.full((n, n), np.nan)
for i in range(n):
    for j in range(n):
        if i == j: continue
        M[i, j] = ordering.pair_prob(F18[order[j]][0], F18[order[j]][1],
                                     F18[order[i]][0], F18[order[i]][1])
im = ax.imshow(M, cmap="RdYlGn", vmin=0.4, vmax=1.0, zorder=3)
for i in range(n):
    for j in range(n):
        if i == j:
            ax.text(j, i, "—", ha="center", va="center", fontsize=7, color=GRY)
        else:
            v = M[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=5.6,
                    color=("white" if v > 0.93 or v < 0.5 else INK))
ax.set_xticks(range(n)); ax.set_xticklabels(order, fontsize=6.2, rotation=40,
                                            ha="right")
ax.set_yticks(range(n)); ax.set_yticklabels(order, fontsize=6.4)
ax.set_title("$P$(세로가 가로보다 더 빌려 준다)", fontsize=8.4, pad=8)
ax.tick_params(length=0)
for s in ("top", "right", "bottom", "left"):
    ax.spines[s].set_visible(False)
cb = plt.colorbar(im, ax=ax, fraction=.045, pad=.03)
cb.ax.tick_params(labelsize=6.2)
cb.ax.axhline(0.90, color=INK, lw=1.2)
cb.set_label("0.90 위여야 섰다고 본다", fontsize=6.2)

# --- 오른쪽: 두 노트의 판정 -------------------------------------------
ax = axes[1]
S = [("노트 310\n(F18)", 5, 28, 0, 7), ("노트 314\n(F6)", 1, 28, 0, 7)]
x = np.arange(len(S)); w = 0.36
for xx, (nm, st, tot, ast_, atot) in zip(x, S):
    ax.bar(xx - w/2, 100*st/tot, w, color=RED, zorder=3,
           label="모든 쌍" if xx == 0 else None)
    ax.bar(xx + w/2, 100*ast_/atot, w, color="#7a2f2f", zorder=3,
           label="이웃 쌍" if xx == 0 else None)
    ax.text(xx - w/2, 100*st/tot + 2, f"{st}/{tot}", ha="center", fontsize=7.4,
            color=RED)
    ax.text(xx + w/2, 100*ast_/atot + 2, f"{ast_}/{atot}", ha="center",
            fontsize=7.4, color="#7a2f2f")
ax.axhline(80, color=INK, lw=1.1, ls="--", zorder=4)
ax.text(1.42, 82, "'순서 선다' 문턱 80%", fontsize=6.8, color=INK, ha="right")
ax.set_xticks(x); ax.set_xticklabels([s[0] for s in S], fontsize=7.8)
ax.set_ylim(0, 100); ax.set_xlim(-0.6, 1.6)
ax.set_ylabel("선 쌍의 비율 (%)", fontsize=8)
ax.tick_params(axis="y", labelsize=7.0)
ax.set_title("둘 다 '순서 못 읽는다'", fontsize=8.6, pad=8)
ax.legend(fontsize=6.9, frameon=False, loc="upper right")
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(axis="y", lw=.4, color="#e3e3e3", zorder=0)
ax.text(-0.55, 92, "노트 310 은 이 표를 그때 낼 수 있었다\n(차와 짝SE 가 다 있었다)",
        fontsize=6.6, color=INK)

fig.suptitle("이 순서를 주장해도 되나", fontsize=10.4, y=1.03)
fig.savefig(D / "rank.pdf", bbox_inches="tight")
fig.savefig(D / "rank.png", dpi=150, bbox_inches="tight")
print("ok")
