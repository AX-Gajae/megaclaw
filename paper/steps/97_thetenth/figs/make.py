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

RED, GRN, GRY, INK = "#a33b3b", "#2f6f4f", "#9aa0a8", "#3b3b3b"
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.05),
                         gridspec_kw={"width_ratios": [1, 1.15], "wspace": 0.38})

# --- 왼쪽: 판이 얼마나 움직였나 -----------------------------------------
ax = axes[0]
ax.axhspan(-0.010, 0.010, color="#e9edf1", zorder=1)
ax.axhline(0.010, color="#b9c0c8", lw=0.9, ls="--", zorder=2)
ax.text(2.42, 0.0113, "노트 245 미결정 폭 ±0.010", fontsize=7.0,
        color=INK, ha="right")
P = [("저장된 이벤트\n07-30 두 실행", 0.0107, None, GRY),
     ("짝지어 잰 값\nF18", 0.0011, 0.00262, GRN),
     ("짝지어 잰 값\nF21", 0.0002, 0.00029, GRN)]
x = np.arange(len(P))
for xx, (lab, v, se, c) in zip(x, P):
    ax.bar(xx, v, color=c, width=0.44, zorder=3)
    if se:
        ax.errorbar(xx, v, yerr=2 * se, fmt="none", ecolor=INK,
                    elinewidth=1.1, capsize=3, zorder=4)
    ax.text(xx, v + 0.0013, f"{v:+.4f}", ha="center", fontsize=8.0, color=c)
ax.axhline(0, color=INK, lw=0.9, zorder=2)
ax.set_xticks(x)
ax.set_xticklabels([p[0] for p in P], fontsize=7.4)
ax.set_ylim(-0.006, 0.0155)
ax.tick_params(axis="y", labelsize=7.2)
ax.set_ylabel("판 rho 의 변화 (문턱 40 → 15)", fontsize=7.8)
ax.set_title("저장된 차는 10배 부풀어 있었다", fontsize=9.4, pad=6)

# --- 오른쪽: 문턱이 실제로 무엇을 가르나 ---------------------------------
ax = axes[1]
DM = [("세계애니", 2648), ("웹툰", 2106), ("만화", 1783), ("모바일", 1559),
      ("애니", 1467), ("펀딩", 320), ("게임", 259), ("도서", 80),
      ("아이돌", 54), ("팝업", 16)]
y = np.arange(len(DM))[::-1]
for yy, (nm, n) in zip(y, DM):
    c = RED if nm == "팝업" else GRY
    ax.barh(yy, n, color=c, height=0.58, zorder=3,
            alpha=1 if c == RED else .62)
    ax.text(n * 1.13, yy, f"{n:,}", va="center", fontsize=7.0, color=c)
ax.axvline(40, color=INK, lw=1.3, ls="-", zorder=5)
ax.axvline(15, color=INK, lw=1.3, ls=":", zorder=5)
ax.text(43, -0.80, "문턱 40", fontsize=7.2, color=INK)
ax.text(14.2, -0.80, "15", fontsize=7.2, color=INK, ha="right")
ax.set_xscale("log")
ax.set_xlim(8, 9000)
ax.set_ylim(-1.95, 9.7)
ax.set_yticks(y)
ax.set_yticklabels([d[0] for d in DM], fontsize=7.4)
ax.set_xticks([10, 100, 1000])
ax.set_xticklabels(["10", "100", "1,000"], fontsize=7.2)
ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
ax.set_xlabel("배포 규약 학습행 (2025년 이전 · 로그)", fontsize=7.8, labelpad=2)
ax.set_title("두 문턱 사이에 있는 것은 팝업뿐이다", fontsize=9.4, pad=6)
ax.text(9.5, -1.62, "문턱을 내린다 = 출발점 하나를 학습에 넣는다",
        fontsize=7.0, color=RED)
fig.suptitle("문턱이 가르는 것은 도메인 하나 --- 그리고 판은 그 하나를 못 본다",
             fontsize=10.2, y=1.005)
fig.subplots_adjust(left=.108, right=.988, top=.805, bottom=.195)
fig.savefig(D / "thresh.pdf")
plt.close(fig)
print("ok")
