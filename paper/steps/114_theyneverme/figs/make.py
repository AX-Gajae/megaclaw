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

GRN, RED, BLU, GRY, INK = "#2f6f4f", "#a33b3b", "#3c5f8a", "#9aa0a8", "#3b3b3b"
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.2),
                         gridspec_kw={"width_ratios": [1.05, 1], "wspace": 0.40})

# --- 왼쪽: 도메인끼리 얼마나 만나나 -------------------------------------
ax = axes[0]
P = [("게임↔모바일", 34), ("애니↔세계애니", 53), ("웹툰↔애니", 10),
     ("웹툰↔세계애니", 7), ("만화↔모바일", 2), ("만화↔게임", 1),
     ("아이돌↔펀딩", 0), ("책↔펀딩", 0)]
y = np.arange(len(P))[::-1]
for yy, (nm, n) in zip(y, P):
    c = GRY if n else RED
    ax.barh(yy, max(n, 0.4), color=c, height=.58, zorder=3,
            alpha=.8 if n else 1)
    ax.text(max(n, 0.4) + 1.2, yy, f"{n}", va="center", fontsize=7.4, color=c)
ax.set_yticks(y); ax.set_yticklabels([p[0] for p in P], fontsize=7.2)
ax.set_xlim(0, 62)
ax.tick_params(axis="x", labelsize=7.2)
ax.set_xlabel("이름 완전일치로 이어지는 작품 수", fontsize=7.8, labelpad=2)
ax.set_title("콘텐츠 도메인은 서로 안 만난다", fontsize=9.4, pad=6)
ax.text(14, 0.15, "도메인마다 표기가 다르다\n(한글 · romaji · 현지화명)",
        fontsize=6.9, color=INK)

# --- 오른쪽: 팝업 허브의 조인을 넓히면 -----------------------------------
ax = axes[1]
J = [("완전일치\n(지금)", 23, 48, 60), ("정규화", 23, 48, 60),
     ("접두사\n(넓힘)", 40, 70, 97)]
J = [J[0], J[2]]
x = np.arange(len(J)); w = 0.27
for xx, (nm, dq, ri, rm) in zip(x, J):
    ax.bar(xx - w, dq, width=w, color=BLU, zorder=3)
    ax.bar(xx, ri, width=w, color=GRN, zorder=3)
    ax.bar(xx + w, rm, width=w, color=GRY, zorder=3)
    for dx, v in ((-w, dq), (0, ri), (w, rm)):
        ax.text(xx + dx, v + 2.5, f"{v}", ha="center", fontsize=7.4, color=INK)
ax.set_xticks(x); ax.set_xticklabels([j[0] for j in J], fontsize=7.6)
ax.set_ylim(0, 148)
ax.tick_params(axis="y", labelsize=7.2)
ax.set_ylabel("이어지는 수", fontsize=7.8)
ax.set_title("팝업 허브는 넓힐 수 있다", fontsize=9.4, pad=6)
ax.text(-0.44, 139, "■ 서로 다른 IP   ■ 내부 레코드   ■ 시장 레코드",
        fontsize=6.9, color=INK)
ax.text(-0.44, 127, "학습 상관 +0.1392 → +0.2114", fontsize=6.9, color=GRN)
ax.text(-0.44, 116, "판 +0.0011 · 진짜 0개 --- 유보로는 확인 안 됨",
        fontsize=6.9, color=INK)
fig.suptitle("허브는 팝업이다 --- 콘텐츠 도메인끼리는 이름이 안 만난다",
             fontsize=10.4, y=1.005)
fig.subplots_adjust(left=.135, right=.985, top=.795, bottom=.175)
fig.savefig(D / "meet.pdf"); plt.close(fig)
print("ok")
