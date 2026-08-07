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
                         gridspec_kw={"width_ratios": [1.05, 1], "wspace": 0.42})

# --- 왼쪽: 두 축의 무리 분포 -------------------------------------------
ax = axes[0]
F = [("publication", 84), ("food", 40), ("perfumes", 39), ("apparels", 32),
     ("home", 29), ("webtoon-res", 27), ("assorted", 25), ("design", 24),
     ("board-games", 22), ("jewellery", 18), ("stationery", 17),
     ("character", 15)]
A = [("TVA", 1915), ("극장판", 103), ("OVA", 29), ("기타", 26)]
tf, ta = sum(v for _, v in F), sum(v for _, v in A)
x0 = 0
for nm, v in F:
    ax.barh(1, 100*v/tf, left=x0, height=.42, color=BLU, zorder=3,
            edgecolor="white", linewidth=.7)
    x0 += 100*v/tf
x0 = 0
for i, (nm, v) in enumerate(A):
    ax.barh(0, 100*v/ta, left=x0, height=.42,
            color=(RED if i == 0 else "#d99"), zorder=3,
            edgecolor="white", linewidth=.7)
    x0 += 100*v/ta
ax.text(50, 1.31, "fund\\_cat --- 12무리 · 최빈 23\\%", ha="center",
        fontsize=7.4, color=BLU)
ax.text(50, -0.38, "anime\\_medium --- 4무리 · 최빈 \\textbf{92\\%}", ha="center",
        fontsize=7.4, color=RED)
ax.text(46, 0.0, "TVA 하나가 92%", ha="center", va="center", fontsize=7.6,
        color="white")
ax.set_yticks([]); ax.set_xlim(0, 100); ax.set_ylim(-0.75, 1.7)
ax.set_xlabel("무리별 비율 (%)", fontsize=7.9)
ax.set_title("같은 검사를 통과했는데 모양이 다르다", fontsize=8.6, pad=8)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)

# --- 오른쪽: 최빈 밖 대 유보 이득 --------------------------------------
ax = axes[1]
P = [("fund\\_cat", 77, +0.1213, +2.23, BLU),
     ("mkt\\_cat", 80, +0.0048, +0.12, GRY),
     ("anime\\_medium", 6, -0.0111, -2.00, RED)]
for nm, mo, g, t, c in P:
    ax.scatter(mo, g, s=70, color=c, zorder=3, edgecolor="white", linewidth=.9)
    ax.annotate(f"{nm}\n$t{{=}}${t:+.2f}", (mo, g), textcoords="offset points",
                xytext=(6, -14 if nm == "mkt\\_cat" else 5), fontsize=6.8,
                color=c)
ax.axhline(0, color=INK, lw=.9, zorder=2)
ax.axvline(20, color=INK, lw=1.1, ls="--", zorder=4)
ax.text(21, -0.048, "검사 ④ 문턱 20\\%", fontsize=6.8, color=INK)
ax.axvspan(0, 20, color="#f7eded", zorder=0)
ax.set_xlim(0, 95); ax.set_ylim(-0.06, 0.17)
ax.set_xlabel("최빈 무리 밖 행의 비율 (\\%)", fontsize=7.8)
ax.set_ylabel("그 도메인의 유보 rho 변화", fontsize=7.8)
ax.tick_params(labelsize=6.9)
ax.set_title("비상수성은 필요조건 --- 충분조건은 아니다", fontsize=8.4, pad=8)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(lw=.4, color="#e3e3e3", zorder=0)
ax.text(2, 0.148, "판의 '새롭다' 38자리\n최빈 밖 중앙 79\\%", fontsize=6.6,
        color=GRY)

fig.suptitle("셋을 통과하고도 못 벌었다", fontsize=10.4, y=1.03)
fig.savefig(D / "const.pdf", bbox_inches="tight")
fig.savefig(D / "const.png", dpi=150, bbox_inches="tight")
print("ok")
