import json, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import paper.figs  # noqa: F401,E402
from scipy.stats import spearmanr
D = Path(__file__).resolve().parent
R = json.loads(Path("data/state/note243_calib.json").read_text())
HAND = {"target_breadth", "venue_prominence", "entry_friction",
        "media_push", "goods_scale"}
fig, ax = plt.subplots(figsize=(7.0, 4.2))
ax.axhspan(-0.010, 0.010, color="#e9c46a", alpha=0.16, zorder=0)
ax.axvspan(-0.010, 0.010, color="#e9c46a", alpha=0.16, zorder=0)
ax.axhline(0, color="#888", lw=0.7); ax.axvline(0, color="#888", lw=0.7)
for r in R:
    h = r["축"] in HAND
    ax.scatter(r["안쪽"], r["유보F23"], s=46 if h else 30,
               color="#a33b3b" if h else "#2f5fa3",
               marker="o" if h else "s", zorder=3,
               label=("손 축 다섯" if h else "시계열 · 달력 열둘"))
    if abs(r["유보F23"]) > 0.004 or abs(r["안쪽"]) > 0.004:
        ax.annotate(r["축"].replace("_", " "), (r["안쪽"], r["유보F23"]),
                    textcoords="offset points", xytext=(6, 4), fontsize=6.2,
                    color="#333")
h_, l_ = ax.get_legend_handles_labels()
by = dict(zip(l_, h_))
ax.legend(by.values(), by.keys(), fontsize=7.4, frameon=False, loc="lower right")
a = np.array([r["안쪽"] for r in R]); b = np.array([r["유보F23"] for r in R])
sm = [r for r in R if abs(r["유보F23"]) <= 0.010]
a2 = np.array([r["안쪽"] for r in sm]); b2 = np.array([r["유보F23"] for r in sm])
ax.set_xlabel("안쪽 이득(학습 구간 앞으로 세 조각)")
ax.set_ylabel("유보 이득(F23 판 $\\rho$)")
ax.set_title(f"축 하나씩 빼서 만든 열일곱 점 --- 전체 spearman "
             f"{spearmanr(a,b).correlation:+.2f}, "
             f"노란 칸 안 {len(sm)}점만 보면 {spearmanr(a2,b2).correlation:+.2f}",
             fontsize=9.4, pad=8)
ax.text(-0.0085, 0.0068, "여기서는 눈금이 없다\n(부호 6/12)", fontsize=7.2,
        color="#8a6d1f", ha="left", va="top")
fig.tight_layout(); fig.savefig(D / "scale.pdf"); plt.close(fig)
print("ok")
