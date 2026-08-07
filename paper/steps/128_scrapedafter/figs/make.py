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
                         gridspec_kw={"width_ratios": [1.15, 1], "wspace": 0.44})

# --- 왼쪽: 결정적 대조 --------------------------------------------------
ax = axes[0]
# 도메인, 구간, 문서없음 중앙, 문서有·창0 중앙, p, n0, n1
C = [("게임", "유보", 7.643, 9.087, 0.0008, 108, 23),
     ("애니", "학습", 2.049, 2.508, 0.0000, 1008, 175),
     ("애니", "유보", 1.663, 2.081, 0.0000, 383, 108),
     ("웹툰", "학습", 4.786, 5.378, 0.0000, 1930, 135),
     ("만화", "학습", 3.960, 4.089, 0.0000, 1486, 269),
     ("세계애니", "학습", 4.649, 4.749, 0.0008, 1354, 292),
     ("모바일", "학습", 2.710, 2.752, 0.3221, 1405, 59),
     ("게임", "학습", 8.179, 8.659, 0.2748, 125, 46)]
y = np.arange(len(C))[::-1]
for yy, (dm, seg, a, b, p, n0, n1) in zip(y, C):
    rel = (b - a) / abs(a) * 100
    c = RED if p < 0.01 else GRY
    ax.barh(yy, rel, height=.6, color=c, zorder=3)
    ax.text(rel + 0.35, yy, f"$p{{=}}${p:.4f}" if p >= 1e-4 else "$p{<}10^{-4}$",
            va="center", fontsize=6.4, color=c)
ax.axvline(0, color=INK, lw=.9, zorder=2)
ax.set_yticks(y)
ax.set_yticklabels([f"{d} {s}" for d, s, *_ in C], fontsize=7.0)
ax.set_xlim(-1.2, 33)
ax.set_xlabel("문서 있는 쪽 라벨이 높은 정도 (%)", fontsize=7.7)
ax.tick_params(axis="x", labelsize=6.8)
ax.set_title("둘 다 사전 조회수 0 인데 문서 유무로 갈린다", fontsize=8.4, pad=8)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.grid(axis="x", lw=.4, color="#e3e3e3", zorder=0)
ax.set_ylim(-1.1, 8.0)
ax.text(-1.0, -0.9, "출시 전 관심이 같은데 라벨이 갈린다 --- 사전 정보일 수 없다",
        fontsize=6.7, color=RED)

# --- 오른쪽: 표지와 대가 -----------------------------------------------
ax = axes[1]
M = [("게임 유보", 0.397, 0.310), ("애니 학습", 0.301, 0.179),
     ("애니 유보", 0.243, 0.098), ("웹툰 학습", 0.221, 0.030),
     ("세계애니 학습", 0.147, 0.136), ("만화 학습", 0.126, -0.011)]
x = np.arange(len(M)); w = 0.36
ax.bar(x - w/2, [m[1] for m in M], w, color=RED, label="지금 (사후)", zorder=3)
ax.bar(x + w/2, [m[2] for m in M], w, color=GRN, label="수선 (사전)", zorder=3)
for xx, m in zip(x, M):
    ax.text(xx - w/2, m[1] + 0.008, f"{m[1]:.2f}", ha="center", fontsize=6.2, color=RED)
    ax.text(xx + w/2, m[2] + 0.008, f"{m[2]:.2f}", ha="center", fontsize=6.2, color=GRN)
ax.axhline(0, color=INK, lw=.8, zorder=2)
ax.set_xticks(x); ax.set_xticklabels([m[0] for m in M], fontsize=6.4, rotation=32,
                                     ha="right")
ax.set_ylim(-0.05, 0.47)
ax.set_ylabel("표시자 ~ 라벨 (spearman)", fontsize=7.8)
ax.tick_params(axis="y", labelsize=6.9)
ax.set_title("수선하면 표지가 준다", fontsize=8.4, pad=8)
ax.legend(fontsize=6.6, frameon=False, loc="upper right", bbox_to_anchor=(1.0, 0.97))
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(axis="y", lw=.4, color="#e3e3e3", zorder=0)
ax.text(0.02, 1.075, "판 0.4851 $\\to$ 0.4799 ($t{=}{-}1.44$ · 문턱 0.0072)",
        transform=ax.transAxes, fontsize=6.6, color=INK, va="top")

fig.suptitle("문서가 생긴 것은 나중 일이다", fontsize=10.4, y=1.03)
fig.savefig(D / "after.pdf", bbox_inches="tight")
fig.savefig(D / "after.png", dpi=150, bbox_inches="tight")
print("ok")
