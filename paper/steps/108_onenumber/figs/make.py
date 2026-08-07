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

GRN, RED, AMB, GRY, INK = "#2f6f4f", "#a33b3b", "#b8863b", "#9aa0a8", "#3b3b3b"
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.25),
                         gridspec_kw={"width_ratios": [1.15, 1], "wspace": 0.42})

# --- 왼쪽: 도메인 x 검사 격자 -------------------------------------------
ax = axes[0]
DM = [("세계애니", 2648), ("웹툰", 2106), ("만화", 1783), ("모바일", 1559),
      ("애니", 1467), ("펀딩", 320), ("게임", 259), ("시장팝업", 101),
      ("도서", 80), ("아이돌", 54), ("팝업", 16)]
TESTS = [("①③\n학습 상관\n(≥30)", 30), ("②\n조각 다섯\n(≥300)", 300),
         ("청력\nF18\n(≥22)", 22)]
y = np.arange(len(DM))[::-1]
for j, (tn, need) in enumerate(TESTS):
    for yy, (nm, n) in zip(y, DM):
        ok = n >= need
        ax.add_patch(plt.Rectangle((j - .42, yy - .40), .84, .80,
                                   facecolor=(GRN if ok else RED),
                                   alpha=.75 if ok else .8, lw=0))
        ax.text(j, yy, "O" if ok else "X", ha="center", va="center",
                fontsize=8.0, color="white", weight="bold")
ax.set_xticks(range(len(TESTS)))
ax.set_xticklabels([t[0] for t in TESTS], fontsize=7.0)
ax.set_yticks(y)
ax.set_yticklabels([f"{nm}  {n:,}" for nm, n in DM], fontsize=7.2)
ax.set_xlim(-.6, len(TESTS) - .4); ax.set_ylim(-1.35, len(DM) - .25)
ax.set_title("무엇을 할 수 있는 도메인인가", fontsize=9.4, pad=6)
ax.tick_params(length=0)
for s in ax.spines.values():
    s.set_visible(False)
ax.text(-.55, -1.15, "숫자는 배포 학습행", fontsize=6.8, color=INK)

# --- 오른쪽: 팝업의 세 벽과 세 층 ---------------------------------------
ax = axes[1]
W = [("채택 검사 ①", 30), ("청력 문턱 F18", 22)]
T = [("지금 판\n75행", 16, RED), ("wide\n189행", 73, GRN),
     ("시장팝업\n205행", 101, GRN)]
x = np.arange(len(T))
for xx, (nm, n, c) in zip(x, T):
    ax.bar(xx, n, color=c, width=.52, zorder=3)
    ax.text(xx, n + 3.5, f"{n}행", ha="center", fontsize=8.0, color=c)
for nm, v in W:
    ax.axhline(v, color=INK, lw=1.1, ls="--", zorder=4)
    ax.text(-0.50, v + 1.8, nm, fontsize=6.9, color=INK, ha="left")
ax.set_xticks(x); ax.set_xticklabels([t[0] for t in T], fontsize=7.4)
ax.set_xlim(-0.62, 2.6); ax.set_ylim(0, 122)
ax.tick_params(axis="y", labelsize=7.2)
ax.set_ylabel("팝업의 배포 학습행", fontsize=7.8)
ax.set_title("벽을 넘기는 손잡이는 이미 있다", fontsize=9.4, pad=6)
fig.suptitle("세 벽이 전부 같은 수 하나에서 나온다 --- 팝업 학습 16행",
             fontsize=10.4, y=1.005)
fig.subplots_adjust(left=.148, right=.985, top=.795, bottom=.175)
fig.savefig(D / "one.pdf"); plt.close(fig)
print("ok")
