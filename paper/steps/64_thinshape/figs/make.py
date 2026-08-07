import json, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import paper.figs  # noqa: F401,E402
D = Path(__file__).resolve().parent
R = json.loads(Path("data/state/note242_thin.json").read_text())

# ── 그림 1 · 무엇을 빼면 무엇이 무너지나 ────────────────────────────────
KEYS = [("나 peak 뺌(17축)", "peak ratio 뺌"),
        ("다 vol 뺌(17축)", "volatility 뺌"),
        ("마 peak+vol(15축)", "둘 다 뺌"),
        ("라 level 뺌(17축)", "level 뺌")]
FS = [("F21_recentpick", "F21 능형", "#6f86b3"),
      ("F18_bagboost", "F18 나무", "#c08a3e"),
      ("F23_rankmix", "F23 섞음", "#2f6f4f")]
fig, ax = plt.subplots(figsize=(7.0, 3.2))
w = 0.26
x = np.arange(len(KEYS))
for i, (f, lab, c) in enumerate(FS):
    v = [R[k]["짝"][f]["차"] for k, _ in KEYS]
    ax.bar(x + (i - 1) * w, v, width=w, color=c, label=lab)
ax.axhline(0, color="#333", lw=0.9)
ax.set_xticks(x); ax.set_xticklabels([b for _, b in KEYS], fontsize=8.4)
ax.set_ylabel("판 $\\rho$ 짝 차")
ax.legend(fontsize=7.4, frameon=False, ncol=3, loc="lower left")
ax.set_ylim(-0.0125, 0.0048)
ax.set_title("셋 다 $\\rho \\geq 0.95$ 로 겹치는데 --- 빼도 되는 것은 하나뿐이다",
             fontsize=10, pad=7)
ax.annotate("나무가 무너진다\n($t{=}-3.33$)", xy=(3.0, -0.0099), xytext=(2.35, -0.0110),
            fontsize=7.2, color="#7a4b1e", ha="center",
            arrowprops=dict(arrowstyle="->", color="#a98", lw=0.8))
fig.tight_layout(); fig.savefig(D / "drops.pdf"); plt.close(fig)

# ── 그림 2 · 겹말 쌍이 줄었다 ─────────────────────────────────────────
cur = json.loads(Path("data/state/note240_dups.json").read_text())
kept = [h for h in cur
        if "peak_ratio" not in h["a"] and "peak_ratio" not in h["b"]]
fig, ax = plt.subplots(figsize=(7.0, 2.5))
allr = sorted(abs(h["rho"]) for h in cur)
keptr = sorted(abs(h["rho"]) for h in kept)
ax.plot(np.arange(1, len(allr) + 1), allr, "o-", color="#a33b3b", ms=4,
        lw=1.2, label=f"19축 · {len(allr)}쌍")
ax.plot(np.arange(1, len(keptr) + 1), keptr, "s-", color="#2f6f4f", ms=4,
        lw=1.2, label=f"17축 · {len(keptr)}쌍")
ax.axhline(0.95, color="#333", lw=0.8, ls=(0, (3, 3)))
ax.set_xlabel("겹말 쌍(작은 순)"); ax.set_ylabel("$|\\rho|$")
ax.set_ylim(0.948, 1.004)
ax.legend(fontsize=7.6, frameon=False, loc="lower right")
ax.set_title("peak ratio 둘을 빼면 겹말 열다섯 쌍이 셋으로 준다", fontsize=10, pad=7)
fig.tight_layout(); fig.savefig(D / "pairs.pdf"); plt.close(fig)
print("ok")
