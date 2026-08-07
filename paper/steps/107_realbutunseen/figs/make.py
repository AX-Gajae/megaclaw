import sys, json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import paper.figs  # noqa: F401,E402
matplotlib.rcParams["axes.unicode_minus"] = False
D = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[4]

GRN, RED, GRY, INK = "#2f6f4f", "#a33b3b", "#9aa0a8", "#3b3b3b"
S = json.loads((ROOT / "data/state/note285_split.json").read_text())
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.2),
                         gridspec_kw={"width_ratios": [.85, 1.25], "wspace": 0.34})

# --- 왼쪽: 엿보기 ------------------------------------------------------
ax = axes[0]
B = [("전부\n205행", 29.7, GRY), ("학습\n101행", 14.5, GRN), ("유보\n104행", 14.4, GRY)]
x = np.arange(3)
for xx, (nm, h, c) in zip(x, B):
    ax.bar(xx, h, color=c, width=.5, zorder=3,
           alpha=1 if nm.startswith("학습") else .65)
    ax.text(xx, h + .7, f"{h:.1f}", ha="center", fontsize=8.0, color=c)
ax.set_xticks(x); ax.set_xticklabels([b[0] for b in B], fontsize=7.6)
ax.set_ylim(0, 35)
ax.tick_params(axis="y", labelsize=7.2)
ax.set_ylabel("크루스칼 H (범주가 라벨을 가르나)", fontsize=7.8)
ax.set_title("반은 유보에서 왔다", fontsize=9.4, pad=6)
ax.annotate("", xy=(0, 27.5), xytext=(1, 27.5),
            arrowprops=dict(arrowstyle="->", color=RED, lw=1.2))
ax.text(0.5, 28.6, "노트 283 이 쓴 수", fontsize=7.0, color=RED, ha="center")
ax.text(0.05, 4.2, "채택 근거는\n학습 구간이다\n(노트 239)", fontsize=7.0,
        color=GRN)

# --- 오른쪽: 순서가 재현된다 -------------------------------------------
ax = axes[1]
keys = [k for k in S["학습"] if k in S["유보"]]
keys = sorted(keys, key=lambda k: -S["학습"][k])
y = np.arange(len(keys))[::-1]
for yy, k in zip(y, keys):
    a, b = S["학습"][k], S["유보"][k]
    ax.plot([a, b], [yy, yy], "-", color=GRY, lw=1.1, zorder=3)
    ax.plot(a, yy, "o", color=GRN, ms=6, zorder=4)
    ax.plot(b, yy, "D", color=RED, ms=5.6, zorder=4, mfc="white", mew=1.3)
ax.set_yticks(y); ax.set_yticklabels(keys, fontsize=7.4)
ax.set_xlim(2.72, 3.78)
ax.tick_params(axis="x", labelsize=7.2)
ax.set_xlabel("log10 일평균 방문 (집단 중앙)", fontsize=7.8, labelpad=2)
ax.set_title("● 학습   ◇ 유보 --- 순위상관 +0.94", fontsize=9.4, pad=6)
ax.text(2.75, -0.55, "유보가 통째로 왼쪽 --- 최근 팝업이 작다", fontsize=6.9,
        color=INK)
ax.set_ylim(-1.0, len(keys) - 0.4)
fig.suptitle("신호는 재현되는데 모형의 이득은 못 잰다", fontsize=10.4, y=1.005)
fig.subplots_adjust(left=.115, right=.985, top=.805, bottom=.185)
fig.savefig(D / "unseen.pdf"); plt.close(fig)
print("ok")
