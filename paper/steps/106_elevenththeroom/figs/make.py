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

GRN, RED, GRY, INK = "#2f6f4f", "#a33b3b", "#9aa0a8", "#3b3b3b"
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.15),
                         gridspec_kw={"width_ratios": [1.1, 1], "wspace": 0.36})

# --- 왼쪽: 활성 축 수와 rho ---------------------------------------------
ax = axes[0]
DM = [("게임", 19, .6240), ("웹툰", 18, .4487), ("애니", 18, .4993),
      ("팝업", 17, .3649), ("모바일", 17, .5458), ("아이돌", 14, .1085),
      ("세계애니", 14, .5292), ("도서", 13, .3735), ("펀딩", 13, .2350),
      ("시장팝업", 4, .1970)]
POS = {"게임": (0, .030), "웹툰": (0, -.042), "애니": (0.7, -.010),
       "팝업": (0, -.042), "모바일": (0, .030), "아이돌": (0, .030),
       "세계애니": (0, .030), "도서": (0, .030), "펀딩": (0, -.042),
       "_": (0, 0),
       "시장팝업": (1.3, .012)}
for nm, a, r in DM:
    c = RED if nm == "시장팝업" else GRY
    ax.plot(a, r, "o", color=c, ms=8 if c == RED else 6.5, zorder=4)
    dx, dy = POS[nm]
    ax.text(a + dx, r + dy, nm, fontsize=7.0, color=c,
            ha="left" if dx else "center")
ax.axvspan(0, 8, color="#f3e6e6", zorder=1)
ax.set_xlim(1.5, 21.5); ax.set_ylim(0.03, 0.70)
ax.tick_params(labelsize=7.2)
ax.set_xlabel("활성 축 수 (마스크 > 1%)", fontsize=7.8, labelpad=2)
ax.set_ylabel("도메인 rho (유보)", fontsize=7.8)
ax.set_title("약한 게 아니라 굶었다", fontsize=9.4, pad=6)
ax.text(2.2, 0.63, "축 넷으로 0.197", fontsize=7.0, color=RED)

# --- 오른쪽: 둘로 갈라 본 판정 ------------------------------------------
ax = axes[1]
S = [("팝업", -.0282, .0226), ("펀딩", -.0229, .0227), ("아이돌", -.0204, .0641),
     ("세계애니", -.0058, .0039), ("도서", -.0038, .0193), ("애니", -.0028, .0050),
     ("웹툰", -.0022, .0054), ("게임", -.0017, .0100), ("모바일", +.0032, .0041)]
y = np.arange(len(S))[::-1]
for yy, (nm, d, se) in zip(y, S):
    c = GRN if d > 0 else GRY
    ax.plot(d, yy, "o", color=c, ms=5.2, zorder=4)
    ax.plot([d - 2 * se, d + 2 * se], [yy, yy], "-", color=c, lw=1.3, zorder=3)
ax.axvline(0, color=INK, lw=0.9, zorder=2)
ax.set_yticks(y); ax.set_yticklabels([s[0] for s in S], fontsize=7.2)
ax.set_xlim(-0.16, 0.15); ax.set_ylim(-1.15, 8.55)
ax.tick_params(axis="x", labelsize=7.2)
ax.set_xlabel("기존 아홉의 변화 (수염 = ±2 짝SE)", fontsize=7.8, labelpad=2)
ax.set_title("아홉 중 여덟이 음수 --- 진짜는 0개", fontsize=9.4, pad=6)
ax.text(-0.155, -0.85, "t 문턱 2.77 (도메인 아홉 · 노트 282) --- 넘는 것 없음",
        fontsize=6.9, color=INK)
fig.suptitle("방을 하나 더 열었다 --- 그리고 판 수를 못 견주게 됐다",
             fontsize=10.4, y=1.005)
fig.subplots_adjust(left=.108, right=.985, top=.805, bottom=.185)
fig.savefig(D / "room.pdf"); plt.close(fig)
print("ok")
