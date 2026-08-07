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
AX = ["fund_cat", "mkt_cat", "anime_medium"]
TS = ["① 정보", "② 시기", "③ 겹침", "④ 비상수"]
# 2 = 통과 · 0 = 탈락 · 1 = 못 돌림
M = [[2, 2, 2, 2],
     [2, 1, 0, 2],
     [2, 2, 2, 0]]
GAIN = [+0.1173, +0.0259, -0.0091]
COL = {2: GRN, 0: RED, 1: GRY}
TXT = {2: "통과", 0: "탈락", 1: "못 돌림"}

fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.3),
                         gridspec_kw={"width_ratios": [1.25, 1], "wspace": 0.30})

ax = axes[0]
for i, a in enumerate(AX):
    for j, t in enumerate(TS):
        v = M[i][j]
        ax.add_patch(plt.Rectangle((j, len(AX)-1-i), .92, .92, color=COL[v],
                                   zorder=3))
        ax.text(j+.46, len(AX)-1-i+.46, TXT[v], ha="center", va="center",
                fontsize=7.6, color=("white" if v != 1 else INK))
ax.set_xlim(-0.05, len(TS)+1.55); ax.set_ylim(-0.55, len(AX)+0.15)
ax.set_xticks(np.arange(len(TS))+.46); ax.set_xticklabels(TS, fontsize=7.6)
ax.set_yticks(np.arange(len(AX))+.46)
ax.set_yticklabels(AX[::-1], fontsize=7.6)
for i, g in enumerate(GAIN):
    c = GRN if g > 0.05 else (RED if g < 0 else GRY)
    ax.text(len(TS)+0.75, len(AX)-1-i+.46, f"{g:+.4f}", ha="center",
            va="center", fontsize=8.4, color=c, weight="bold")
ax.text(len(TS)+0.75, len(AX)+0.02, "유보 이득", ha="center", fontsize=7.4,
        color=INK)
ax.tick_params(length=0)
for s in ("top", "right", "bottom", "left"):
    ax.spines[s].set_visible(False)
ax.set_title("넷을 다 통과한 하나만 번다", fontsize=8.8, pad=10)
ax.text(0.0, -0.42, "노트 322 는 '둘 다 ①②③④ 통과' 라 적었다 --- 틀렸다",
        fontsize=6.8, color=RED)

# --- 오른쪽: 답이 어디 있었나 -----------------------------------------
ax = axes[1]
S = [("노트 299", "시장팝업 category 는\n공유 축 통제 후 안 남는다\n$p{=}0.1176$", GRN),
     ("노트 300", "판 전체 감사표에\nmkt\\_cat = '이미 있다'", GRN),
     ("lab/overlap.py", "부르면 즉시 답한다\n(0.3초)", GRN),
     ("노트 321 · 322", "'둘 다 ①②③④ 통과'", RED)]
y = np.arange(len(S))[::-1]
for yy, (t, b, c) in zip(y, S):
    ax.add_patch(plt.Rectangle((0, yy-0.36), 1.0, .72, color=c, alpha=.16,
                               zorder=2))
    ax.text(0.04, yy+0.19, t, fontsize=7.6, color=c, weight="bold", va="center")
    ax.text(0.04, yy-0.13, b, fontsize=6.5, color=INK, va="center")
ax.set_xlim(0, 1.05); ax.set_ylim(-0.65, 3.65)
ax.set_xticks([]); ax.set_yticks([])
for s in ("top", "right", "bottom", "left"):
    ax.spines[s].set_visible(False)
ax.set_title("답이 있던 자리 셋", fontsize=8.8, pad=10)
ax.text(0.02, -0.55, "쓴 사람도 나이고 도구를 만든 사람도 나다", fontsize=6.8,
        color=RED)

fig.suptitle("답은 내 노트에 있었다", fontsize=10.4, y=1.03)
fig.savefig(D / "matrix.pdf", bbox_inches="tight")
fig.savefig(D / "matrix.png", dpi=150, bbox_inches="tight")
print("ok")
