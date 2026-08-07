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
                         gridspec_kw={"width_ratios": [1, 1.1], "wspace": 0.42})

# 도메인, F18 차, F6 차, F6 짝SE, 새롭다
R = [("웹툰", -0.0773, -0.0098, 0.0101, 6), ("애니", -0.0587, +0.0142, 0.0119, 6),
     ("만화", -0.0491, +0.0029, 0.0080, 3), ("모바일", -0.0341, +0.0178, 0.0260, 3),
     ("시장팝업", -0.0222, -0.0010, 0.0011, 0), ("게임", -0.0217, +0.0009, 0.0044, 3),
     ("세계애니", -0.0125, +0.0020, 0.0105, 0), ("아이돌", -0.0106, +0.0015, 0.0018, 2)]

ax = axes[0]
for nm, a, b, se, f in R:
    ax.scatter(a, b, s=52, color=BLU, zorder=3, edgecolor="white", linewidth=.8)
    dx, dy = (6, 4)
    if nm in ("만화", "시장팝업"): dy = -11
    ax.annotate(nm, (a, b), textcoords="offset points", xytext=(dx, dy),
                fontsize=6.7, color=INK)
ax.axhline(0, color=INK, lw=.8, zorder=2)
ax.axvline(0, color=INK, lw=.8, zorder=2)
lo, hi = -0.088, 0.030
ax.plot([lo, hi], [lo, hi], ls=":", lw=.9, color=GRY, zorder=1)
ax.set_xlim(-0.088, 0.012); ax.set_ylim(-0.017, 0.026)
ax.set_xlabel("F18 로 잰 차 (노트 310)", fontsize=7.8)
ax.set_ylabel("F6 로 잰 차 (이 노트)", fontsize=7.8)
ax.tick_params(labelsize=6.8)
ax.set_title("두 자가 서로 무관하다 --- $\\rho{=}{-}0.048$ ($p{=}0.91$)",
             fontsize=8.3, pad=8)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(lw=.4, color="#e3e3e3", zorder=0)
ax.text(-0.086, 0.0235, "점선 = 두 자가 같았다면", fontsize=6.4, color=GRY)

# --- 오른쪽: 검색 빌림은 누구를 빼도 그대로 ---------------------------
ax = axes[1]
B = [("아무도 안 뺌", 0.1132), ("웹툰 뺌", 0.1054), ("애니 뺌", 0.1155),
     ("만화 뺌", 0.1172), ("모바일 뺌", 0.1284), ("세계애니 뺌", 0.1192),
     ("게임 뺌", 0.1151)]
y = np.arange(len(B))[::-1]
for yy, (nm, v) in zip(y, B):
    c = GRN if yy == len(B) - 1 else BLU
    ax.barh(yy, v, height=.56, color=c, zorder=3)
    ax.text(v + 0.003, yy, f"{v:.4f}", va="center", fontsize=7.0, color=c)
ax.axvline(0.1132, color=INK, lw=1.0, ls="--", zorder=4)
ax.set_yticks(y); ax.set_yticklabels([b[0] for b in B], fontsize=7.2)
ax.set_xlim(0, 0.163)
ax.set_xlabel("도서의 검색 축을 껐을 때 잃는 양", fontsize=7.7)
ax.tick_params(axis="x", labelsize=6.8)
ax.set_title("누구를 빼도 검색 빌림은 그대로다", fontsize=8.5, pad=8)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.grid(axis="x", lw=.4, color="#e3e3e3", zorder=0)
ax.set_ylim(-0.95, 7.0)
ax.text(0.002, -0.85, "0.105 $\\sim$ 0.128 --- 폭이 짝SE(0.033) 안이다",
        fontsize=6.7, color=BLU)

fig.suptitle("빌려 준 사람이 없다", fontsize=10.4, y=1.03)
fig.savefig(D / "nolender.pdf", bbox_inches="tight")
fig.savefig(D / "nolender.png", dpi=150, bbox_inches="tight")
print("ok")
