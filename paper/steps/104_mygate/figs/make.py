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
J = json.loads((ROOT / "data/state/note282_leaf.json").read_text())

fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.2),
                         gridspec_kw={"width_ratios": [1, 1.25], "wspace": 0.40})

# --- 왼쪽: 판은 세 값이 다 미결정 폭 안 ----------------------------------
ax = axes[0]
L = [(20, 0.4857), (10, 0.4840), (5, 0.4849)]
x = np.arange(3)
ax.axhspan(0.4857 - 0.010, 0.4857 + 0.010, color="#e9edf1", zorder=1)
ax.plot(x, [l[1] for l in L], "-o", color=INK, lw=1.7, ms=7, zorder=4)
for xx, (lf, v) in zip(x, L):
    ax.text(xx + (0.12 if xx == 0 else 0), v + 0.0022, f"{v:.4f}",
            ha="left" if xx == 0 else "center", fontsize=7.6, color=INK)
ax.set_xticks(x)
ax.set_xticklabels(["20\n(기본값)", "10", "5"], fontsize=7.8)
ax.set_ylim(0.4735, 0.4975)
ax.tick_params(axis="y", labelsize=7.2)
ax.set_xlabel("min_samples_leaf", fontsize=7.8, labelpad=2)
ax.set_ylabel("판 rho", fontsize=7.8)
ax.set_title("판은 셋 다 미결정 폭 안이다", fontsize=9.4, pad=6)
ax.text(0.06, 0.4952, "회색 띠 = 노트 245 미결정 폭 ±0.010", fontsize=6.9,
        color=INK)

# --- 오른쪽: 도메인별 t, 두 문턱 -----------------------------------------
ax = axes[1]
D10 = J["10"]["도메인별"]; D5 = J["5"]["도메인별"]
doms = sorted(D10, key=lambda d: D10[d]["차"])
y = np.arange(len(doms))[::-1]
for yy, dm in zip(y, doms):
    for dd, off, mk_, lab in ((D10, +0.17, "o", "20→10"),
                              (D5, -0.17, "D", "20→5")):
        v = dd.get(dm)
        if not v:
            continue
        t = v["t"]
        t = float(t) if t is not None else 0.0
        c = RED if t <= -2.0 else (GRN if t >= 2.0 else GRY)
        ax.plot(t, yy + off, mk_, color=c, ms=5.4, zorder=4,
                mfc=c if mk_ == "o" else "white", mew=1.3)
ax.axvline(0, color=INK, lw=0.9, zorder=2)
for v, c, ls in ((-2, RED, "-"), (2, GRN, "-"),
                 (-2.77, RED, ":"), (2.77, GRN, ":")):
    ax.axvline(v, color=c, lw=1.0, ls=ls, zorder=3, alpha=.8)
ax.set_yticks(y); ax.set_yticklabels(doms, fontsize=7.2)
ax.set_xlim(-3.6, 3.6)
ax.set_ylim(-1.6, len(doms) - 0.4)
ax.tick_params(axis="x", labelsize=7.2)
ax.set_xlabel("짝지은 t", fontsize=7.8, labelpad=2)
ax.set_title("● 20→10   ◇ 20→5", fontsize=9.4, pad=6)
ax.text(-3.5, -0.85, "실선 |t|=2 (노트 275 규칙 ②)", fontsize=6.9, color=INK)
ax.text(-3.5, -1.35, "점선 |t|=2.77 (아홉 도메인 본페로니)", fontsize=6.9,
        color=INK)
fig.suptitle("내가 만든 문은 우연만으로 세 번에 한 번 닫힌다",
             fontsize=10.4, y=1.005)
fig.subplots_adjust(left=.105, right=.985, top=.805, bottom=.185)
fig.savefig(D / "gate.pdf"); plt.close(fig)
print("ok")
