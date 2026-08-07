import json, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import paper.figs  # noqa: F401,E402
D = Path(__file__).resolve().parent
R = json.loads(Path("data/state/note248_se.json").read_text())

fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.5),
                         gridspec_kw={"width_ratios": [1.1, 1], "wspace": 0.36})
# 왼쪽 — 차와 짝 SE
ax = axes[0]
R2 = sorted(R, key=lambda r: r["차"])
y = np.arange(len(R2))[::-1]
for yy, r in zip(y, R2):
    real = abs(r["t"]) >= 2
    c = "#2f6f4f" if (real and r["차"] > 0) else ("#a33b3b" if real else "#c9ccd1")
    ax.errorbar(r["차"], yy, xerr=r["짝SE"], fmt="o", ms=5, color=c,
                ecolor=c, elinewidth=1.3, capsize=2.5, zorder=3)
    ax.text(0.30, yy, f"$t{{=}}{r['t']:+.2f}$", fontsize=6.6, va="center",
            color="#333" if real else "#999")
ax.axvline(0, color="#333", lw=0.8)
ax.set_yticks(y)
ax.set_yticklabels([f"{r['도메인']} ({r['n']})" for r in R2], fontsize=7.4)
ax.set_xlim(-0.20, 0.42)
ax.set_xlabel("정규화 차 $\\pm$ 짝 SE")
ax.set_title("아이돌의 $+$0.131 은 잡음이다", fontsize=9.4, pad=6)

# 오른쪽 — n 과 SE
ax = axes[1]
n = np.array([r["n"] for r in R]); se = np.array([r["SE"] for r in R])
ax.scatter(n, se, s=44, color="#2f5fa3", zorder=3)
for r in R:
    ax.annotate(r["도메인"], (r["n"], r["SE"]), textcoords="offset points",
                xytext=(6, 4), fontsize=6.6, color="#333")
xx = np.linspace(20, 760, 200)
ax.plot(xx, 1.0 / np.sqrt(xx), ls=(0, (4, 3)), color="#888", lw=1.0,
        label="$1/\\sqrt{n}$")
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlabel("유보 레코드 수"); ax.set_ylabel("도메인 $\\rho$ 의 SE")
ax.legend(fontsize=7.2, frameon=False, loc="upper right")
ax.set_title("SE 가 여섯 배 벌어져 있다", fontsize=9.4, pad=6)
fig.suptitle("도메인 수는 SE 없이 읽으면 안 된다", fontsize=10, y=1.0)
fig.tight_layout(); fig.savefig(D / "se.pdf"); plt.close(fig)

# 그림 2 — 잡음을 걷으면 상쇄가 더 뚜렷하다
fig, ax = plt.subplots(figsize=(7.0, 2.5))
tot = sum(r["n"] for r in R)
mov = sum(r["n"] / tot * abs(r["차"]) for r in R)
net = sum(r["n"] / tot * r["차"] for r in R)
rmov = sum(r["n"] / tot * abs(r["차"]) for r in R if abs(r["t"]) >= 2)
rnet = sum(r["n"] / tot * r["차"] for r in R if abs(r["t"]) >= 2)
BARS = [("총량\n(전부)", mov, "#8a6d9f"), ("순\n(전부)", abs(net), "#8a8f98"),
        ("진짜 총량\n($|t|\\geq2$)", rmov, "#5c4a7a"),
        ("진짜 순\n($|t|\\geq2$)", abs(rnet), "#6b6f78")]
x = np.arange(len(BARS))
ax.bar(x, [b[1] for b in BARS], color=[b[2] for b in BARS], width=0.55)
for xx_, b in zip(x, BARS):
    ax.text(xx_, b[1] + 0.0006, f"{b[1]:.4f}", ha="center", fontsize=8.4)
ax.set_xticks(x); ax.set_xticklabels([b[0] for b in BARS], fontsize=7.8)
ax.set_ylabel("판 $\\rho$ 단위"); ax.set_ylim(0, 0.026)
ax.set_title(f"잡음을 걷으면 상쇄가 {mov/abs(net):.0f}배에서 "
             f"{rmov/abs(rnet):.0f}배로 뚜렷해진다", fontsize=10, pad=7)
fig.tight_layout(); fig.savefig(D / "cancel.pdf"); plt.close(fig)
print("ok")
