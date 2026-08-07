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

GRN, RED, BLU, INK = "#2f6f4f", "#a33b3b", "#3c5f8a", "#3b3b3b"
sub = json.loads((ROOT / "data/state/note281_sub.json").read_text())
N = [r["학습행"] for r in sub]
F6 = [r["F6_directpool"] for r in sub]
F18 = [r["F18_bagboost"] for r in sub]
F10 = [r["F10_pershrink"] for r in sub]
step = json.loads((ROOT / "data/state/note281_step.json").read_text())

fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.15),
                         gridspec_kw={"width_ratios": [1.15, 1], "wspace": 0.34})

# --- 왼쪽: 웹툰 하나만 얇게 만든 곡선 -----------------------------------
ax = axes[0]
ax.plot(N, F6, "-o", color=GRN, lw=1.7, ms=5.2, zorder=4, label="F6 순수 풀링")
ax.plot(N, F18, "-o", color=RED, lw=1.7, ms=5.2, zorder=4, label="F18 나무")
ax.plot(N, F10, "-o", color=BLU, lw=1.7, ms=5.2, zorder=4, label="F10 배합")
# 노트 280 의 도메인 가로지른 F18 점 --- 겹치면 교락이 없다는 뜻
CD = [(16, .0000), (54, .5677), (80, .3472), (259, .3561), (2106, .5490)]
ax.plot([c[0] for c in CD], [c[1] for c in CD], "s", mfc="none",
        mec=RED, mew=1.2, ms=7, zorder=5)
ax.set_xscale("log")
ax.set_xlim(12, 3600)
ax.set_ylim(-0.06, 0.82)
ax.set_xticks([16, 40, 100, 400, 2106])
ax.set_xticklabels(["16", "40", "100", "400", "2,106"], fontsize=7.2)
ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
ax.tick_params(axis="y", labelsize=7.2)
ax.axhline(0, color=INK, lw=0.9, zorder=2)
ax.set_xlabel("웹툰의 학습행만 줄인다 (로그)", fontsize=7.8, labelpad=2)
ax.set_ylabel("전용 열(라벨 누출)의 이득", fontsize=7.8)
ax.set_title("한 도메인만 얇게 해도 문턱은 그대로다", fontsize=9.4, pad=6)
ax.legend(fontsize=6.9, loc="center right", frameon=False,
          bbox_to_anchor=(1.0, 0.36))
ax.text(17, .755, "□ 노트 280 의 도메인 가로지른 F18 점", fontsize=6.8,
        color=RED)
ax.text(17, .705, "   양 끝은 겹치고 가운데는 흩어진다 ---", fontsize=6.8,
        color=RED)
ax.text(17, .655, "   문턱은 행 수가 · 크기는 도메인이", fontsize=6.8,
        color=RED)

# --- 오른쪽: 계단이 어디 있나 -------------------------------------------
ax = axes[1]
k = [r["학습행"] for r in step]
g = [r["이득"] for r in step]
ax.axvspan(12, 20.5, color="#f3e6e6", zorder=1)
ax.axvline(20, color=RED, lw=1.4, zorder=3)
ax.axvline(40, color="#b9c0c8", lw=1.4, ls="--", zorder=3)
ax.plot(k, g, "-o", color=RED, lw=1.8, ms=6, zorder=5)
LBL = {16: (-1.2, .030), 18: (0, -.036), 20: (1.2, .030),
       22: (0, .034), 25: (0, -.040), 30: (0, .032), 40: (0, .032)}
for kk, gg in zip(k, g):
    dx, dy = LBL.get(kk, (0, .030))
    ax.text(kk + dx, gg + dy, f"{gg:+.4f}", fontsize=6.8, color=RED,
            ha="center")
ax.axhline(0, color=INK, lw=0.9, zorder=2)
ax.set_xlim(13, 44)
ax.set_ylim(-0.065, 0.52)
ax.set_xticks([16, 20, 22, 25, 30, 40])
ax.tick_params(labelsize=7.2)
ax.set_xlabel("웹툰 학습행", fontsize=7.8, labelpad=2)
ax.set_ylabel("F18 의 이득", fontsize=7.8)
ax.set_title("계단은 20 바로 위다 --- 40 이 아니다", fontsize=9.4, pad=6)
ax.text(20.6, .478, "min_samples_leaf = 20", fontsize=7.0, color=RED)
ax.text(39.4, .300, "노트 276 이 쓴 40", fontsize=7.0, color="#8d949c",
        ha="right")
fig.suptitle("문턱은 잎 하한 그 자체였다 --- 두 배가 아니라",
             fontsize=10.4, y=1.005)
fig.subplots_adjust(left=.105, right=.985, top=.805, bottom=.185)
fig.savefig(D / "knob.pdf"); plt.close(fig)
print("ok")
