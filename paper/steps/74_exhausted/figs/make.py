import json, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import paper.figs  # noqa: F401,E402
D = Path(__file__).resolve().parent
R = json.loads(Path("data/state/note252_ceiling.json").read_text())

# 그림 1 — 지금 · 섞음 · CV · 속천장
fig, ax = plt.subplots(figsize=(7.0, 3.6))
R2 = sorted(R, key=lambda r: -(r["여지"] or 0))
y = np.arange(len(R2))[::-1]
for yy, r in zip(y, R2):
    ax.plot([r["섞음"], r["속천장"]], [yy, yy], color="#dcdfe3", lw=5,
            solid_capstyle="butt", zorder=1)
    ax.scatter([r["섞음"]], [yy], s=26, color="#b9553f", marker="|", zorder=3)
    ax.scatter([r["속천장"]], [yy], s=26, color="#999", marker="|", zorder=3)
    ax.scatter([r["지금"]], [yy], s=44, color="#2f5fa3", zorder=4)
    ax.scatter([r["CV"]], [yy], s=44, color="#2f6f4f", marker="D", zorder=4)
    v = r["여지"]
    ax.text(0.86, yy, f"{v:+.3f}", fontsize=7,
            color="#2f6f4f" if v > 0 else "#a33b3b", va="center")
ax.set_yticks(y); ax.set_yticklabels([f"{r['도메인']} ({r['n']})" for r in R2],
                                     fontsize=7.6)
ax.set_xlim(0.05, 0.98)
ax.set_xlabel("도메인 $\\rho$")
from matplotlib.lines import Line2D
ax.legend(handles=[
    Line2D([], [], marker="|", ls="", color="#b9553f", label="섞음(과적합 바닥)"),
    Line2D([], [], marker="o", ls="", color="#2f5fa3", label="지금(풀링)"),
    Line2D([], [], marker="D", ls="", color="#2f6f4f", label="유보 안 5겹 CV"),
    Line2D([], [], marker="|", ls="", color="#999", label="속천장(과적합)"),
], fontsize=6.8, frameon=False, loc="lower right", ncol=2)
ax.set_title("풀링 모형은 아홉 중 다섯에서 이미 도메인 전용 모형을 이긴다",
             fontsize=10, pad=8)
fig.tight_layout(); fig.savefig(D / "ceiling.pdf"); plt.close(fig)

# 그림 2 — 판 수준
fig, ax = plt.subplots(figsize=(7.0, 2.3))
tot = sum(r["n"] for r in R)
vals = [("섞음\n(과적합 바닥)", sum(r["섞음"] * r["n"] for r in R) / tot, "#b9553f"),
        ("지금\n(풀링 · 배포)", sum(r["지금"] * r["n"] for r in R) / tot, "#2f5fa3"),
        ("유보 안 CV\n(도메인 전용)", sum(r["CV"] * r["n"] for r in R) / tot, "#2f6f4f"),
        ("속천장\n(과적합)", sum(r["속천장"] * r["n"] for r in R) / tot, "#c9ccd1")]
x = np.arange(len(vals))
ax.bar(x, [v[1] for v in vals], color=[v[2] for v in vals], width=0.5)
for xx, v in zip(x, vals):
    ax.text(xx, v[1] + 0.008, f"{v[1]:.4f}", ha="center", fontsize=8.6)
ax.annotate("", xy=(2, 0.4697), xytext=(1, 0.4569),
            arrowprops=dict(arrowstyle="<->", color="#2f6f4f", lw=1.2))
ax.text(1.5, 0.508, "여지 $+$0.0128", ha="center", fontsize=8, color="#2f6f4f")
ax.set_xticks(x); ax.set_xticklabels([v[0] for v in vals], fontsize=7.6)
ax.set_ylabel("판 $\\rho$"); ax.set_ylim(0, 0.63)
ax.set_title("축 열일곱으로 남은 여지는 $+$0.013 이다", fontsize=10, pad=7)
fig.tight_layout(); fig.savefig(D / "board.pdf"); plt.close(fig)
print("ok")
