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
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.15),
                         gridspec_kw={"width_ratios": [1, 1.2], "wspace": 0.40})

# --- 왼쪽: 크기가 같은 수 셋 --------------------------------------------
ax = axes[0]
L = [("저장소에서 뺀 값\n17축 → 23축", -0.0670, None, GRY),
     ("짝지어 다시 잰 값\n17축 → 23축", +0.0071, 0.0417, GRN),
     ("웹툰 두 열 막기\n(노트 262·263)", -0.0690, 0.0531, RED)]
y = np.arange(len(L))[::-1]
for yy, (lab, v, se, c) in zip(y, L):
    ax.barh(yy, v, color=c, height=0.44, zorder=3)
    if se:
        ax.errorbar(v, yy, xerr=2 * se, fmt="none", ecolor=INK,
                    elinewidth=1.1, capsize=3, zorder=4)
    ax.text(v + (0.007 if v > 0 else -0.007), yy + 0.30, f"{v:+.4f}",
            fontsize=8.2, color=c, ha="left" if v > 0 else "right")
ax.axvline(0, color=INK, lw=0.9, zorder=2)
ax.set_yticks(y)
ax.set_yticklabels([l[0] for l in L], fontsize=7.4)
ax.set_xlim(-0.20, 0.14)
ax.set_ylim(-1.05, 2.55)
ax.set_xticks([-0.15, -0.10, -0.05, 0, 0.05, 0.10])
ax.tick_params(axis="x", labelsize=7.2)
ax.set_xlabel("팝업 rho 의 변화", fontsize=7.8, labelpad=2)
ax.set_title("-0.067 은 재현된다 --- 다른 원인으로", fontsize=9.4, pad=6)
ax.text(-0.198, -0.72, "막대 = 값 · 수염 = ±2 짝SE", fontsize=7.0, color=INK)
ax.text(-0.198, -1.00, "수염이 0 을 지나면 못 가른다", fontsize=7.0,
        color=INK, style="italic")

# --- 오른쪽: 보이는 크기 대 쓸 수 있는 크기 ------------------------------
ax = axes[1]
DM = [("웹툰", .273, .0228), ("애니", .236, .0124), ("모바일", .172, .0038),
      ("세계애니", .117, .0038), ("게임", .070, .0074), ("도서", .064, .0163),
      ("펀딩", .031, .0272), ("팝업", .023, .0417), ("아이돌", .010, .0336)]
y = np.arange(len(DM))[::-1]
for yy, (nm, sh, se) in zip(y, DM):
    dd, nn = 2 * se, 0.010 / sh
    c = RED if nm == "팝업" else (GRN if nn < dd else GRY)
    ax.plot([dd, nn], [yy, yy], "-", color=c, lw=1.7, zorder=3,
            alpha=.55 if c == GRY else 1)
    ax.plot(dd, yy, "o", color=c, ms=5.2, zorder=4)
    ax.plot(nn, yy, "D", color=c, ms=5.2, zorder=4, mfc="white", mew=1.4)
ax.set_xscale("log")
ax.set_yticks(y)
ax.set_yticklabels([d[0] for d in DM], fontsize=7.4)
ax.set_xlim(0.005, 1.6)
ax.set_ylim(-2.05, 8.55)
ax.set_xticks([0.01, 0.03, 0.1, 0.3, 1.0])
ax.set_xticklabels(["0.01", "0.03", "0.1", "0.3", "1.0"], fontsize=7.2)
ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
ax.set_xlabel("도메인 안에서 필요한 delta-rho (로그)", fontsize=7.8, labelpad=2)
ax.set_title("● 재면 보이는 크기      ◇ 판이 쓸 수 있는 크기",
             fontsize=9.0, pad=6)
ax.text(0.0056, -1.25, "웹툰만 ◇ 가 ● 왼쪽 --- 판이 도메인보다 먼저 본다",
        fontsize=7.0, color=GRN)
ax.text(0.0056, -1.80, "팝업의 0.083~0.435 --- 재면 보여도 판은 못 쓴다",
        fontsize=7.0, color=RED)
fig.suptitle("잰 자리에서만 보이고, 판에서는 안 보인다", fontsize=10.4, y=1.005)
fig.subplots_adjust(left=.105, right=.988, top=.815, bottom=.185)
fig.savefig(D / "popup.pdf")
plt.close(fig)
print("ok")
