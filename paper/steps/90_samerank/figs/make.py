import json, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import paper.figs  # noqa: F401,E402
D = Path(__file__).resolve().parent
R = json.loads(Path("data/state/note268_rank.json").read_text())
R = sorted(R, key=lambda r: -r["판"])

fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.3),
                         gridspec_kw={"width_ratios": [1.15, 1], "wspace": 0.34})
ax = axes[0]
x = np.arange(len(R)); w = 0.36
ax.bar(x - w / 2, [r["판"] for r in R], width=w, color="#2f5fa3", label="판 $\\rho$")
ax.bar(x + w / 2, [r["코호트"] for r in R], width=w, color="#c08a3e",
       label="코호트 안 $\\rho$")
for xx, r in zip(x, R):
    ax.text(xx, max(r["판"], r["코호트"]) + 0.008, f"{r['코호트']-r['판']:+.4f}",
            ha="center", fontsize=6.8, color="#a33b3b")
ax.set_xticks(x)
ax.set_xticklabels([r["정식화"].split("_")[0] for r in R], fontsize=8)
ax.set_ylabel("$\\rho$"); ax.set_ylim(0, 0.58)
ax.legend(fontsize=7.2, frameon=False, loc="upper right")
ax.set_title("코호트 통제는 모두를 조금씩 내린다", fontsize=9.4, pad=6)

ax = axes[1]
byc = sorted(R, key=lambda r: -r["코호트"])
cr = {r["정식화"]: i + 1 for i, r in enumerate(byc)}
for i, r in enumerate(R):
    ax.plot([0, 1], [len(R) - i, len(R) - cr[r["정식화"]]], "-o",
            color="#2f6f4f", lw=1.4, ms=6)
    ax.text(-0.06, len(R) - i, r["정식화"].split("_")[0], ha="right",
            va="center", fontsize=7.6)
    ax.text(1.06, len(R) - cr[r["정식화"]], r["정식화"].split("_")[0],
            ha="left", va="center", fontsize=7.6)
ax.set_xlim(-0.5, 1.5); ax.set_ylim(0.4, len(R) + 0.6)
ax.set_xticks([0, 1]); ax.set_xticklabels(["판 순위", "코호트 순위"], fontsize=8.4)
ax.set_yticks([]); ax.spines[:].set_visible(False)
ax.set_title("선이 하나도 안 엇갈린다\nspearman $=+1.000$", fontsize=9.4, pad=6)
fig.suptitle("코호트를 판정 기준으로 써도 줄이 그대로다", fontsize=10, y=1.0)
fig.tight_layout(); fig.savefig(D / "rank.pdf"); plt.close(fig)
print("ok")

# 그림 2 — 챔피언
fig, ax = plt.subplots(figsize=(7.0, 2.7))
P = [("F18 배깅나무", 0.4845, "#2f6f4f"), ("F23 섞음(지금 챔피언)", 0.4839, "#8a8f98"),
     ("F21 능형", 0.4542, "#a33b3b")]
x = np.arange(len(P))
ax.bar(x, [p[1] - 0.44 for p in P], bottom=0.44, color=[p[2] for p in P], width=0.5)
for xx, p in zip(x, P):
    ax.text(xx, p[1] + 0.0012, f"{p[1]:.4f}", ha="center", fontsize=9)
ax.annotate("", xy=(1, 0.4805), xytext=(0, 0.4805),
            arrowprops=dict(arrowstyle="<->", color="#2f6f4f", lw=1.3))
ax.text(0.5, 0.4818, "$-$0.0010 · $t{=}-$0.17\n1 SE 안 → 동점", ha="center",
        fontsize=7.4, color="#2f6f4f")
ax.annotate("", xy=(2, 0.4645), xytext=(0, 0.4645),
            arrowprops=dict(arrowstyle="<->", color="#a33b3b", lw=1.3))
ax.text(1.0, 0.4585, "$-$0.0300 · $t{=}-$2.82  유의", ha="center", fontsize=7.4,
        color="#a33b3b")
ax.set_xticks(x); ax.set_xticklabels([p[0] for p in P], fontsize=8)
ax.set_ylim(0.44, 0.492); ax.set_ylabel("판 $\\rho$")
ax.set_title("F23 은 F21 과 F18 의 섞음이다 --- 그 F21 쪽이 죽었다",
             fontsize=10, pad=7)
fig.tight_layout(); fig.savefig(D / "champ.pdf"); plt.close(fig)
print("ok2")
