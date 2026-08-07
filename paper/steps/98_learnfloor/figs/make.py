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

RED, GRN, GRY, INK = "#a33b3b", "#2f6f4f", "#9aa0a8", "#3b3b3b"
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.1),
                         gridspec_kw={"width_ratios": [1.15, 1], "wspace": 0.36})

# --- 왼쪽: 학습행 대 새는 열이 닿는 정도 --------------------------------
ax = axes[0]
F = [("세계애니", 2648, .5354, .9911), ("웹툰", 2106, .4449, .9938),
     ("모바일", 1559, .5429, .9873), ("애니", 1467, .5008, .9818),
     ("펀딩", 320, .2588, .9581), ("게임", 259, .6195, .9755),
     ("도서", 80, .3928, .7400), ("아이돌", 54, .1385, .7063),
     ("팝업", 16, .3819, .3819)]
n = np.array([f[1] for f in F], float)
gain = np.array([f[3] - f[2] for f in F])
ax.axvspan(1, 20, color="#f0e2e2", zorder=1)
ax.axvline(20, color=RED, lw=1.3, zorder=4)
# (가로배수, 세로더하기, 정렬) --- 빽빽한 구간은 손으로 흩는다
POS = {"세계애니": (1.16, -0.052, "left"), "웹툰": (1.16, 0.030, "left"),
       "모바일": (0.86, -0.055, "right"), "애니": (0.86, 0.042, "right"),
       "펀딩": (1.18, 0.030, "left"), "게임": (1.18, -0.050, "left"),
       "도서": (1.18, -0.050, "left"), "아이돌": (1.18, 0.036, "left"),
       "팝업": (0.80, 0.045, "right")}
for (nm, nn, a, b), g in zip(F, gain):
    c = RED if nm == "팝업" else GRN
    ax.plot(nn, g, "o", color=c, ms=7, zorder=5)
    fx, dy, ha = POS[nm]
    ax.text(nn * fx, g + dy, nm, fontsize=7.0, color=c, ha=ha, va="center")
ax.axhline(0, color=INK, lw=0.9, zorder=2)
ax.set_xscale("log")
ax.set_xlim(9, 6000)
ax.set_ylim(-0.10, 0.83)
ax.set_xticks([10, 20, 100, 1000])
ax.set_xticklabels(["10", "20", "100", "1,000"], fontsize=7.2)
ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
ax.tick_params(axis="y", labelsize=7.2)
ax.set_xlabel("도메인의 배포 학습행 (로그)", fontsize=7.8, labelpad=2)
ax.set_ylabel("라벨을 그대로 준 전용 열의 이득", fontsize=7.8)
ax.set_title("54행은 배우고 16행은 정확히 0", fontsize=9.4, pad=6)
ax.text(10.5, 0.60, "잎 하한 20\n(sklearn 기본값)", fontsize=7.0, color=RED)

# --- 오른쪽: 잎 하한만 내리면 살아난다 ----------------------------------
ax = axes[1]
L = [(20, 0.0000), (10, 0.0394), (5, 0.4373), (2, 0.4786)]
x = np.arange(len(L))
for xx, (lf, g) in zip(x, L):
    c = RED if g < 0.01 else GRN
    ax.bar(xx, g, color=c, width=0.5, zorder=3)
    ax.text(xx, g + 0.016, f"{g:+.4f}", ha="center", fontsize=7.8, color=c)
ax.axhline(0, color=INK, lw=0.9, zorder=2)
ax.set_xticks(x)
ax.set_xticklabels([f"{l[0]}" for l in L], fontsize=7.6)
ax.set_ylim(-0.03, 0.60)
ax.tick_params(axis="y", labelsize=7.2)
ax.set_xlabel("min_samples_leaf (팝업 학습 16행 · 관측 14)", fontsize=7.8,
              labelpad=2)
ax.set_ylabel("팝업 전용 열의 이득", fontsize=7.8)
ax.set_title("벽은 자료가 아니라 손잡이였다", fontsize=9.4, pad=6)
ax.text(0.12, 0.30, "14행으로는\n잎 20을 못 채운다", fontsize=7.0, color=RED)
fig.suptitle("문을 열었더니 안에 문이 하나 더 있었다", fontsize=10.4, y=1.005)
fig.subplots_adjust(left=.105, right=.985, top=.805, bottom=.185)
fig.savefig(D / "floor.pdf")
plt.close(fig)
print("ok")
