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
S = [("혼자", 54, 100.00, 0.5977), ("+팝업", 70, 77.14, 0.5977),
     ("+도서", 150, 36.00, 0.6391), ("+시장팝업", 251, 21.51, 0.5407),
     ("+게임", 510, 10.59, 0.4813), ("+펀딩", 830, 6.51, 0.4995),
     ("+애니", 2297, 2.35, 0.2860), ("+모바일", 3856, 1.40, 0.3368),
     ("+만화", 5639, 0.96, 0.2398), ("+웹툰", 7745, 0.70, 0.2436),
     ("+세계애니", 10393, 0.52, 0.1012)]

fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.35),
                         gridspec_kw={"width_ratios": [1.12, 1], "wspace": 0.40})

ax = axes[0]
x = np.array([s[2] for s in S]); y = np.array([s[3] for s in S])
ax.plot(x, y, "-o", color=BLU, ms=5.2, lw=1.5, zorder=3)
for (nm, n, sh, r) in S:
    dx, dy = (5, 6)
    if nm in ("+펀딩", "+모바일"): dy = -13
    if nm == "+만화": dx, dy = (4, -13)
    if nm == "+웹툰": dx, dy = (5, 5)
    if nm == "혼자": dx = -22
    ax.annotate(nm, (sh, r), textcoords="offset points", xytext=(dx, dy),
                fontsize=6.3, color=INK)
ax.axvspan(2.35, 6.51, color="#f6eaea", zorder=0)
ax.text(3.9, 0.075, "절벽", fontsize=7.0, color=RED, ha="center")
ax.set_xscale("log")
ax.invert_xaxis()
ax.set_xlabel("풀에서 아이돌 학습 행의 몫 (%, 로그 · 왼쪽이 큼)", fontsize=7.6)
ax.set_ylabel("아이돌 유보 rho", fontsize=7.8)
ax.tick_params(labelsize=6.9)
ax.set_ylim(0, 0.72)
ax.set_title("몫이 줄수록 단조롭게 무너진다  $\\rho_s{=}{-}0.943$", fontsize=8.4,
             pad=8)
for s_ in ("top", "right"):
    ax.spines[s_].set_visible(False)
ax.grid(lw=.4, color="#e3e3e3", zorder=0)

# --- 오른쪽: 다른 도메인들도 같은 자리에 놓는다 ------------------------
ax = axes[1]
# 도메인, 학습몫(%), 풀링-혼자
R = [("웹툰", 20.3, +0.0297), ("세계애니", 25.5, +0.0146), ("모바일", 15.0, -0.0130),
     ("애니", 14.1, -0.0073), ("펀딩", 3.1, -0.0230), ("게임", 2.5, +0.0145),
     ("시장팝업", 0.97, +0.2493), ("도서", 0.77, +0.2806), ("아이돌", 0.52, -0.4964)]
for nm, sh, d in R:
    c = GRN if d > 0.1 else (RED if d < -0.1 else GRY)
    ax.scatter(sh, d, s=56, color=c, zorder=3, edgecolor="white", linewidth=.8)
    dx, dy = (6, 4)
    if nm in ("애니", "게임"): dy = -12
    if nm == "세계애니": dx, dy = (5, -13)
    if nm == "시장팝업": dx, dy = (4, -13)
    ax.annotate(nm, (sh, d), textcoords="offset points", xytext=(dx, dy),
                fontsize=6.5, color=INK)
ax.axhline(0, color=INK, lw=.9, zorder=2)
ax.axvspan(0.3, 1.2, color="#f2f4f6", zorder=0)
ax.set_xscale("log"); ax.invert_xaxis()
ax.set_xlabel("학습 풀에서의 몫 (%, 로그)", fontsize=7.7)
ax.set_ylabel("풀링 $-$ 혼자 (F18)", fontsize=7.8)
ax.tick_params(labelsize=6.9)
ax.set_ylim(-0.60, 0.40)
ax.set_title("몫이 1% 아래면 크게 갈린다 --- 방향은 따로다", fontsize=8.3, pad=8)
for s_ in ("top", "right"):
    ax.spines[s_].set_visible(False)
ax.grid(lw=.4, color="#e3e3e3", zorder=0)
ax.text(0.36, -0.56, "회색 띠 = 1% 아래", fontsize=6.5, color=GRY)

fig.suptitle("몫이 없으면 삼켜진다", fontsize=10.4, y=1.03)
fig.savefig(D / "share.pdf", bbox_inches="tight")
fig.savefig(D / "share.png", dpi=150, bbox_inches="tight")
print("ok")
