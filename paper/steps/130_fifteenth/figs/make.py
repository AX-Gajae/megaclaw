"""그림 하나 — 덮음 31건을 셋으로 가른다."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager as fm
from pathlib import Path

for cand in ("AppleGothic", "Apple SD Gothic Neo"):
    if any(cand in f.name for f in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams["axes.unicode_minus"] = False
OUT = Path(__file__).resolve().parent

fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.3),
                        gridspec_kw={"width_ratios": [1.15, 1]})

# (a) 깔때기 — 281 → 31 → 13
a = axs[0]
lab = ["아이돌 레코드", "장소가 붙음", "유효 (시간게이트 통과 ·\n위양성 아님)"]
val = [281, 31, 13]
col = ["#4a5c6a", "#c9a13c", "#1a5c2a"]
a.barh([2, 1, 0], val, color=col, height=0.58)
for y, v, p in zip([2, 1, 0], val, [1.0, 31 / 281, 13 / 281]):
    a.text(v + 5, y, f"{v}  ({p:.3f})", va="center", fontsize=9.5, fontweight="bold")
a.axvline(281 * 0.7, ls="--", lw=1.2, color="#8b1a1a")
a.text(281 * 0.7 - 6, 1.6, "게이트 0.7", fontsize=8.5, color="#8b1a1a",
       rotation=90, va="center", ha="right")
a.set_yticks([2, 1, 0]); a.set_yticklabels(lab, fontsize=9)
a.set_xlim(0, 330)
a.set_xlabel("레코드 수", fontsize=9)
a.set_title("유효 덮음은 게이트의 15분의 1", fontsize=10.5, fontweight="bold")
a.spines[["top", "right"]].set_visible(False)

# (b) 31건의 내역
a = axs[1]
parts = ["유효\n13", "시간게이트 위반\n12", "위양성\n6"]
vals = [13, 12, 6]
cols = ["#1a5c2a", "#8b1a1a", "#b07d2a"]
wedges, _ = a.pie(vals, colors=cols, startangle=90,
                  wedgeprops=dict(width=0.52, edgecolor="white", lw=1.6))
a.text(0, 0, "31건", ha="center", va="center", fontsize=13, fontweight="bold")
for wg, p, v in zip(wedges, parts, vals):
    ang = np.deg2rad((wg.theta1 + wg.theta2) / 2)
    a.text(1.30 * np.cos(ang), 1.30 * np.sin(ang), p, ha="center", va="center",
           fontsize=9, fontweight="bold")
a.set_title("붙은 31건을 눈으로 다 봤다", fontsize=10.5, fontweight="bold")
fig.tight_layout(); fig.savefig(OUT / "funnel.pdf")
print("그림 저장")
