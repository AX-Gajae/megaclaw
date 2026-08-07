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
AMB = "#b07a3a"
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.35),
                         gridspec_kw={"width_ratios": [1.18, 1], "wspace": 0.40})

# 이름, 표시자rho, 바닥p, 판정(수선전), 판정(수선후)
R = [("게임·위키·유보", 0.397, 0.0008, "볼 것", None),
     ("애니·위키·학습", 0.301, 0.0000, "볼 것", None),
     ("애니·위키·유보", 0.243, 0.0000, "볼 것", "바닥만"),
     ("웹툰·위키·학습", 0.221, 0.0000, "볼 것", None),
     ("세계애니·위키·학습", 0.147, 0.0008, "바닥만", None),
     ("만화·위키·학습", 0.126, 0.0000, "바닥만", None),
     ("모바일·검색·학습", 0.173, 0.0000, "바닥만", "바닥만"),
     ("웹툰·검색·학습", -0.141, 0.0000, "바닥만", "바닥만")]

ax = axes[0]
y = np.arange(len(R))[::-1]
for yy, (nm, rho, p, b, a) in zip(y, R):
    c = RED if b == "볼 것" else AMB
    ax.barh(yy, abs(rho), height=.58, color=c, zorder=3)
    ax.text(abs(rho) + 0.008, yy, f"{rho:+.3f}", va="center", fontsize=6.6,
            color=c)
    tag = "사라짐" if a is None else "남음"
    ax.text(0.585, yy, tag, va="center", ha="right", fontsize=6.5,
            color=(GRN if a is None else GRY),
            weight=("bold" if a is None else "normal"))
ax.axvline(0.20, color=INK, lw=.9, ls="--", zorder=4)
ax.text(0.208, 7.55, "후보 문턱 0.20", fontsize=6.6, color=INK)
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in R], fontsize=6.9)
ax.set_xlim(0, 0.60)
ax.set_xlabel("$|$표시자 $\\sim$ 라벨$|$ (수선 전)", fontsize=7.7)
ax.tick_params(axis="x", labelsize=6.8)
ax.set_title("빨강 = 기계가 '볼 것'으로 짚은 넷", fontsize=8.5, pad=8)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.grid(axis="x", lw=.4, color="#e3e3e3", zorder=0)
ax.set_ylim(-0.9, 8.1)
ax.text(0.0, -0.82, "오른쪽 칸 = 수선 뒤에도 남았나", fontsize=6.5, color=GRY)

# --- 오른쪽: 검사 둘의 층위 --------------------------------------------
ax = axes[1]
K = [("볼 것", 4, 0, RED),
     ("표시자만 큼", 0, 0, BLU),
     ("바닥만 갈림", 4, 3, AMB),
     ("괜찮다 · 못 잼", 21, 26, GRY)]
x = np.arange(2); w = 0.55
bot = np.zeros(2)
for nm, a, b, c in K:
    ax.bar(x, [a, b], w, bottom=bot, color=c, zorder=3, label=nm)
    for xx, v in zip(x, [a, b]):
        if v >= 2:
            ax.text(xx, bot[list(x).index(xx)] + v / 2, str(v), ha="center",
                    va="center", fontsize=7.0,
                    color=("white" if c != GRY else INK))
    bot = bot + np.array([a, b], float)
ax.set_xticks(x); ax.set_xticklabels(["수선 전", "수선 뒤"], fontsize=8.2)
ax.set_ylabel("도메인 $\\times$ 계열 $\\times$ 구간 자리", fontsize=7.8)
ax.tick_params(axis="y", labelsize=7.0)
ax.set_ylim(0, 34)
ax.set_title("수선하면 '볼 것' 이 0 이 된다", fontsize=8.5, pad=8)
ax.legend(fontsize=6.5, frameon=False, loc="upper center", ncol=2,
          bbox_to_anchor=(0.5, 1.0))
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(axis="y", lw=.4, color="#e3e3e3", zorder=0)

fig.suptitle("손으로 찾은 것을 기계가 다시 찾는다", fontsize=10.4, y=1.03)
fig.savefig(D / "audit.pdf", bbox_inches="tight")
fig.savefig(D / "audit.png", dpi=150, bbox_inches="tight")
print("ok")
