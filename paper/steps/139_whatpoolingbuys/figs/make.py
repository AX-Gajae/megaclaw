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
# 이름 순(노트 316 규약 --- 크기 순 정렬 안 한다). (유보, 풀링F18, 혼자F18, t)
R = [("게임", 180, 0.5893, 0.5748, +0.34), ("도서", 163, 0.3895, 0.1089, +4.61),
     ("모바일", 441, 0.5464, 0.5594, -0.95), ("세계애니", 300, 0.5475, 0.5329, +0.75),
     ("시장팝업", 104, 0.4098, 0.1605, +2.67), ("아이돌", 25, 0.1012, 0.5977, -2.01),
     ("애니", 606, 0.4764, 0.4837, -0.57), ("웹툰", 711, 0.4614, 0.4317, +1.62),
     ("펀딩", 80, 0.2536, 0.2766, -0.24)]

fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.4),
                         gridspec_kw={"width_ratios": [1.15, 1], "wspace": 0.42})

ax = axes[0]
y = np.arange(len(R))[::-1]
for yy, (nm, n, p, s, t) in zip(y, R):
    d = p - s
    c = GRN if t > 2.5 else (RED if t < -2.0 else GRY)
    ax.barh(yy, d, height=.56, color=c, zorder=3)
    ax.text(d + (0.012 if d >= 0 else -0.012), yy, f"{d:+.3f}",
            va="center", ha="left" if d >= 0 else "right", fontsize=6.6, color=c)
    ax.text(-0.60, yy, f"n{n}", va="center", ha="left", fontsize=6.3, color=GRY)
    ax.text(0.585, yy, f"$t{{=}}${t:+.2f}", va="center", ha="right", fontsize=6.4,
            color=c)
ax.axvline(0, color=INK, lw=.9, zorder=2)
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in R], fontsize=7.4)
ax.set_xlim(-0.62, 0.60)
ax.set_xlabel("풀링 $-$ 혼자 (F18, 같은 자끼리)", fontsize=7.7)
ax.tick_params(axis="x", labelsize=6.8)
ax.set_title("두 얇은 도메인을 살리고 하나를 죽인다", fontsize=8.5, pad=8)
for s_ in ("top", "right", "left"):
    ax.spines[s_].set_visible(False)
ax.grid(axis="x", lw=.4, color="#e3e3e3", zorder=0)
ax.set_ylim(-1.0, 9.0)
ax.text(-0.61, -0.9, "이름 순 정렬(노트 316 규약) · 문턱 $|t|{>}2.81$",
        fontsize=6.5, color=GRY)

# --- 오른쪽: 셈 방식 넷 -------------------------------------------------
ax = axes[1]
C = [("④ 같은 자 F6", 0.0040, GRY),
     ("② 최선 대 최선", 0.0120, "#8fa8b8"),
     ("③ 같은 자 F18", 0.0289, BLU),
     ("① 챔피언 대 혼자F6", 0.0519, "#7aa87f")]
x = np.arange(len(C))
for xx, (nm, v, c) in zip(x, C):
    ax.bar(xx, v, 0.55, color=c, zorder=3)
    ax.text(xx, v + 0.0016, f"{v:+.4f}", ha="center", fontsize=7.6, color=c)
ax.set_xticks(x); ax.set_xticklabels([c[0] for c in C], fontsize=6.7, rotation=18,
                                     ha="right")
ax.set_ylim(0, 0.062)
ax.set_ylabel("판 rho 이득", fontsize=8)
ax.tick_params(axis="y", labelsize=7.0)
ax.set_title("셈 방식에 따라 열세 배 차이", fontsize=8.5, pad=8)
for s_ in ("top", "right"):
    ax.spines[s_].set_visible(False)
ax.grid(axis="y", lw=.4, color="#e3e3e3", zorder=0)
ax.axhspan(0.0120, 0.0289, color="#eef3f6", zorder=0)
ax.text(1.5, 0.0555, "판 자신의 선택 규칙을 쓰면 ③", fontsize=6.8, color=BLU,
        ha="center")
ax.text(1.5, 0.0205, "정직한 띠", fontsize=6.6, color=INK, ha="center")

fig.suptitle("풀링이 사는 것과 죽이는 것", fontsize=10.4, y=1.03)
fig.savefig(D / "pool.pdf", bbox_inches="tight")
fig.savefig(D / "pool.png", dpi=150, bbox_inches="tight")
print("ok")
