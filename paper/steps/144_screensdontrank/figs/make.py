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

# --- 왼쪽: 가중을 걸어도 mkt_cat 은 안 산다 ---------------------------
ax = axes[0]
AL = [1.0, 0.75, 0.0]
MK = [+0.0259, -0.0058, -0.0233]
FU = [+0.1173, +0.1311, +0.0799]
x = np.arange(len(AL))
ax.plot(x, FU, "-o", color=BLU, ms=6, lw=1.8, zorder=3, label="fund_cat (펀딩)")
ax.plot(x, MK, "-s", color=RED, ms=6, lw=1.8, zorder=3, label="mkt_cat (시장팝업)")
for xx, v in zip(x, FU):
    ax.text(xx, v + 0.009, f"{v:+.4f}", ha="center", fontsize=6.8, color=BLU)
for xx, v in zip(x, MK):
    ax.text(xx, v - 0.014, f"{v:+.4f}", ha="center", fontsize=6.8, color=RED)
ax.axhline(0, color=INK, lw=.9, zorder=2)
ax.set_xticks(x)
ax.set_xticklabels([f"$\\alpha{{=}}${a:g}\n시장팝업 몫 {s}"
                    for a, s in zip(AL, ["0.97%", "2.5%", "9.09%"])],
                   fontsize=7.0)
ax.set_ylim(-0.075, 0.185)
ax.set_ylabel("전용 축의 유보 이득", fontsize=8)
ax.tick_params(axis="y", labelsize=7.0)
ax.set_title("몫을 올려도 mkt_cat 은 안 산다 --- 예측 반증",
             fontsize=8.4, pad=8)
ax.legend(fontsize=7.0, frameon=False, loc="upper right")
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(axis="y", lw=.4, color="#e3e3e3", zorder=0)
ax.text(-0.35, -0.057, "예측: alpha=0 에서 +0.05 ~ +0.20 (반증)",
        fontsize=6.7, color=RED)

# --- 오른쪽: 어떤 성질도 세 축을 정렬 못 한다 -------------------------
ax = axes[1]
P = [("학습 eps$^2$", [0.148, 0.127, 0.005], False),
     ("유보 eps$^2$", [0.037, 0.089, 0.112], False),
     ("최빈 밖", [0.77, 0.80, 0.06], False),
     ("도메인 몫", [0.031, 0.010, 0.141], False),
     ("기준 rho", [0.254, 0.410, 0.476], True)]
GAIN = [+0.1173, +0.0259, -0.0091]
y = np.arange(len(P))[::-1]
for yy, (nm, vals, ok) in zip(y, P):
    order = np.argsort(-np.array(vals))
    gain_order = np.argsort(-np.array(GAIN))
    match = list(order) == list(gain_order)
    rev = list(order) == list(gain_order)[::-1]
    c = GRN if (match or rev) else GRY
    lbl = "정렬함" if match else ("거꾸로 정렬함" if rev else "정렬 못 함")
    ax.barh(yy, 1, height=.6, color=c, alpha=.85, zorder=3)
    ax.text(0.04, yy, nm, va="center", fontsize=7.4, color="white")
    ax.text(1.06, yy, lbl, va="center", fontsize=7.2, color=c,
            weight=("bold" if (match or rev) else "normal"))
ax.set_xlim(0, 2.5); ax.set_yticks([]); ax.set_xticks([])
ax.set_ylim(-0.9, 5.0)
ax.set_title("이득 순서: fund $>$ mkt $>$ anime", fontsize=8.6, pad=8)
for s in ("top", "right", "bottom", "left"):
    ax.spines[s].set_visible(False)
ax.text(0.0, -0.75, "$n{=}3$ --- '기준 rho' 는 우연일 수 있다(노트 315·316)",
        fontsize=6.7, color=GRY)

fig.suptitle("검사는 거르지 줄 세우지 못한다", fontsize=10.4, y=1.03)
fig.savefig(D / "rank.pdf", bbox_inches="tight")
fig.savefig(D / "rank.png", dpi=150, bbox_inches="tight")
print("ok")
