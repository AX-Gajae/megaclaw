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
# 도메인(이름 순), 새 축 수, raw 차, raw t, fundraw 차, fundraw t
R = [("게임", 0, -0.0010, -0.10, +0.0056, +0.55),
     ("도서", 0, -0.0017, -0.11, -0.0005, -0.03),
     ("모바일", 3, +0.0087, +0.46, +0.0086, +0.46),
     ("세계애니", 3, +0.0075, +0.63, +0.0058, +0.49),
     ("시장팝업", 0, -0.1231, -1.79, -0.0014, -0.04),
     ("아이돌", 0, -0.0583, -1.15, -0.0408, -0.71),
     ("애니", 2, -0.0348, -2.18, -0.0329, -2.16),
     ("웹툰", 1, -0.0069, -1.76, -0.0061, -1.50),
     ("팝업", 0, +0.0102, +0.50, +0.0124, +0.61),
     ("펀딩", 1, +0.0998, +1.67, +0.1320, +2.05)]

fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.4),
                         gridspec_kw={"width_ratios": [1.2, 1], "wspace": 0.40})

ax = axes[0]
y = np.arange(len(R))[::-1]
w = 0.34
for yy, (nm, k, d1, t1, d2, t2) in zip(y, R):
    c1 = GRN if t1 > 1.6 else (RED if t1 < -1.6 else GRY)
    c2 = GRN if t2 > 1.6 else (RED if t2 < -1.6 else GRY)
    ax.barh(yy + w/2, d1, height=w, color=c1, alpha=.55, zorder=3)
    ax.barh(yy - w/2, d2, height=w, color=c2, zorder=3)
    ax.text(0.152, yy, f"새 축 {k}" if k else "—", va="center", ha="right",
            fontsize=6.5, color=(INK if k else GRY),
            weight=("bold" if k else "normal"))
ax.axvline(0, color=INK, lw=.9, zorder=2)
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in R], fontsize=7.4)
ax.set_xlim(-0.145, 0.162)
ax.set_xlabel("도메인 rho 변화 (연한 = 열 축 · 진한 = 열하나)", fontsize=7.5)
ax.tick_params(axis="x", labelsize=6.8)
ax.set_title("축을 받은 다섯 중 하나만 번다", fontsize=8.6, pad=8)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.grid(axis="x", lw=.4, color="#e3e3e3", zorder=0)
ax.set_ylim(-1.0, 10.0)
ax.text(-0.142, -0.9, "판 $-$0.0096 / $-$0.0027 · 문턱 넘는 도메인 0개",
        fontsize=6.7, color=RED)

# --- 오른쪽: 깔때기 ---------------------------------------------------
ax = axes[1]
F = [("선별기 후보", 43, GRY), ("출처가 통과", 11, BLU),
     ("검사 ② 통과", 10, BLU), ("지었다", 10, BLU), ("번 것", 1, GRN)]
y2 = np.arange(len(F))[::-1]
for yy, (nm, v, c) in zip(y2, F):
    ax.barh(yy, v, height=.58, color=c, zorder=3)
    ax.text(v + 0.8, yy, str(v), va="center", fontsize=8.0, color=c)
ax.set_yticks(y2); ax.set_yticklabels([f[0] for f in F], fontsize=7.6)
ax.set_xlim(0, 50)
ax.set_xlabel("축 후보 수", fontsize=7.9)
ax.tick_params(axis="x", labelsize=6.9)
ax.set_title("출처가 74% 를 막고 검사가 못 세운다", fontsize=8.5, pad=8)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.grid(axis="x", lw=.4, color="#e3e3e3", zorder=0)
ax.set_ylim(-0.95, 5.0)
ax.annotate("", xy=(11, 3.55), xytext=(43, 3.55),
            arrowprops=dict(arrowstyle="->", lw=1.1, color=RED))
ax.text(27, 3.72, "출처가 32개 막음", fontsize=6.8, color=RED, ha="center")
ax.text(0.5, -0.85, "그 하나도 $t{=}2.05$ --- 문턱 2.81 미달", fontsize=6.7,
        color=INK)

fig.suptitle("마흔셋에서 열을 골랐더니 하나가 벌었다", fontsize=10.4, y=1.03)
fig.savefig(D / "ten.pdf", bbox_inches="tight")
fig.savefig(D / "ten.png", dpi=150, bbox_inches="tight")
print("ok")
