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
J = json.load(open("/Users/ax/.claude/jobs/a5c89f96/tmp/n309b.json"))

GRN, RED, GRY, INK, BLU = "#2f6f4f", "#a33b3b", "#9aa0a8", "#3b3b3b", "#33628f"
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.35),
                         gridspec_kw={"width_ratios": [1.1, 1], "wspace": 0.42})

# --- 왼쪽: 도메인별 변화 -----------------------------------------------
ax = axes[0]
rows = sorted([(k, v) for k, v in J["도메인"].items() if isinstance(v, dict) and "차" in v], key=lambda kv: -kv[1]["차"])
y = np.arange(len(rows))[::-1]
for yy, (d, v) in zip(y, rows):
    t = v["t"] or 0
    c = GRN if t > 2 else (RED if t < -2 else GRY)
    ax.errorbar(v["차"], yy, xerr=2 * v["짝SE"], fmt="o", color=c, ms=4.8,
                capsize=3.2, lw=1.5, zorder=3)
ax.axvline(0, color=INK, lw=.9, zorder=2)
ax.set_yticks(y); ax.set_yticklabels([d for d, _ in rows], fontsize=7.4)
lim = max(abs(v["차"]) + 2 * v["짝SE"] for _, v in rows) * 1.12
ax.set_xlim(-lim, lim)
ax.set_xlabel("fund_cat 을 더했을 때 rho 변화 ($\\pm$2$\\times$짝SE)", fontsize=7.6)
ax.tick_params(axis="x", labelsize=6.8)
ax.set_title("펀딩만 움직여야 한다 --- 전용 축이므로", fontsize=8.5, pad=8)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.grid(axis="x", lw=.4, color="#e3e3e3", zorder=0)
b = J["판"]
ax.text(-lim * 0.96, -0.85,
        f"판 {b['기준']:.4f} $\\to$ {b['새']:.4f} ({b['차']:+.4f} · "
        f"$t{{=}}${b['차']/b['짝SE']:+.2f})", fontsize=6.8, color=INK)
ax.set_ylim(-1.1, len(rows) - 0.25)

# --- 오른쪽: 빌림이 주나 -----------------------------------------------
ax = axes[1]
bw = J["도메인"]["_빌림"]
lab = ["제 축 없음\n(대조)", "제 축 있음\n(이 노트)"]
own = [0.2536 - 0.1089, 0.3709 - bw["새판 빌림"]]
bor = [0.1089, bw["새판 빌림"]]
x = np.arange(2)
for xx, o, b in zip(x, own, bor):
    ax.bar(xx, o, 0.5, color=GRY, zorder=3, label="제 것" if xx == 0 else None)
    ax.bar(xx, b, 0.5, bottom=o, color=BLU, zorder=3,
           label="빌린 것" if xx == 0 else None)
    ax.text(xx, o / 2, f"{o:.3f}", ha="center", va="center", fontsize=7.4,
            color="white")
    ax.text(xx, o + b / 2, f"{b:.3f}", ha="center", va="center", fontsize=7.4,
            color="white")
    ax.text(xx, o + b + 0.008, f"$\\rho$ {o+b:.4f}", ha="center", fontsize=8.0,
            color=INK)
    ax.text(xx, -0.020, f"빌린 몫 {100*b/(o+b):.0f}%", ha="center", fontsize=7.2,
            color=BLU)
ax.set_xticks(x); ax.set_xticklabels(lab, fontsize=7.6)
ax.set_ylim(-0.035, 0.46)
ax.set_ylabel("펀딩 유보 rho", fontsize=8)
ax.tick_params(axis="y", labelsize=7.0)
ax.set_title("빌림이 물러난 게 아니라 제 것이 늘었다", fontsize=8.5, pad=8)
ax.legend(fontsize=7.0, frameon=False, loc="upper left")
for s_ in ("top", "right"):
    ax.spines[s_].set_visible(False)
ax.grid(axis="y", lw=.4, color="#e3e3e3", zorder=0)

fig.suptitle("빌리던 도메인에 제 축을 준다", fontsize=10.4, y=1.03)
fig.savefig(D / "own.pdf", bbox_inches="tight")
fig.savefig(D / "own.png", dpi=150, bbox_inches="tight")
print("ok")
