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
# alpha, 판, 판차, 아이돌, 도서
R = [(1.00, 0.4799, 0.0000, 0.1012, 0.3895), (0.90, 0.4791, -0.0008, 0.1555, 0.3650),
     (0.75, 0.4770, -0.0029, 0.1820, 0.3484), (0.50, 0.4665, -0.0134, 0.2513, 0.3040),
     (0.25, 0.4608, -0.0192, 0.2410, 0.2736), (0.00, 0.4652, -0.0147, 0.3432, 0.2234)]

fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.35),
                         gridspec_kw={"width_ratios": [1.05, 1], "wspace": 0.40})

# --- 왼쪽: 절충 곡선 (판 차 대 아이돌 이득) ----------------------------
ax = axes[0]
gx = [-r[2] for r in R]           # 판이 잃은 양
gy = [r[3] - R[0][3] for r in R]  # 아이돌이 얻은 양
ax.plot(gx, gy, "-o", color=BLU, ms=5.4, lw=1.6, zorder=3)
for (a, b, db, i, bk), x, y in zip(R, gx, gy):
    dx, dy = (7, -3)
    if a in (0.25,): dx, dy = (4, 8)
    if a == 0.0: dx, dy = (-30, 2)
    ax.annotate(f"$\\alpha{{=}}${a:g}", (x, y), textcoords="offset points",
                xytext=(dx, dy), fontsize=6.8, color=INK)
ax.axvline(0.010, color=INK, lw=1.1, ls="--", zorder=4)
ax.text(0.0105, 0.028, "판 미결정 띠 0.010", fontsize=6.7, color=INK)
ax.axvspan(-0.001, 0.010, color="#eef4ef", zorder=0)
ax.set_xlim(-0.001, 0.0225); ax.set_ylim(-0.01, 0.28)
ax.set_xlabel("판이 잃은 양", fontsize=7.9)
ax.set_ylabel("아이돌이 얻은 양", fontsize=7.9)
ax.tick_params(labelsize=6.9)
ax.set_title("볼록하다 --- 처음 조금이 제일 싸다", fontsize=8.6, pad=8)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(lw=.4, color="#e3e3e3", zorder=0)
ax.text(0.0005, 0.255, "초록 = 배포 가능 구간", fontsize=6.6, color=GRN)

# --- 오른쪽: 효율 -------------------------------------------------------
ax = axes[1]
E = [(0.90, 0.0543/0.0008), (0.75, 0.0808/0.0029), (0.50, 0.1501/0.0134),
     (0.25, 0.1398/0.0192), (0.00, 0.2420/0.0147)]
x = np.arange(len(E))
for xx, (a, e) in zip(x, E):
    c = GRN if a >= 0.75 else GRY
    ax.bar(xx, e, 0.55, color=c, zorder=3)
    ax.text(xx, e + 1.5, f"{e:.0f}", ha="center", fontsize=7.8, color=c)
ax.set_xticks(x); ax.set_xticklabels([f"$\\alpha{{=}}${a:g}" for a, _ in E],
                                     fontsize=7.6)
ax.set_ylim(0, 82)
ax.set_ylabel("아이돌 이득 $\\div$ 판 손실", fontsize=8)
ax.tick_params(axis="y", labelsize=7.0)
ax.set_title("첫 걸음이 쉰 배 싸다", fontsize=8.6, pad=8)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(axis="y", lw=.4, color="#e3e3e3", zorder=0)
ax.text(2.0, 74, "$\\alpha{=}0.9$ · $0.75$ 는 배포 규칙 둘 다 통과",
        fontsize=6.8, color=GRN, ha="center")

fig.suptitle("처음 조금은 거의 공짜다", fontsize=10.4, y=1.03)
fig.savefig(D / "convex.pdf", bbox_inches="tight")
fig.savefig(D / "convex.png", dpi=150, bbox_inches="tight")
print("ok")
