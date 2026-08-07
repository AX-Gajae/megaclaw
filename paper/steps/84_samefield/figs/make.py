import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import paper.figs  # noqa: F401,E402
D = Path(__file__).resolve().parent

fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.3),
                         gridspec_kw={"width_ratios": [1, 1.1], "wspace": 0.34})
# 왼쪽 — 시기별 비율
ax = axes[0]
x = np.arange(2); w = 0.5
ax.bar(x, [70.1, 22.4], color=["#8a9ab3", "#a33b3b"], width=w)
for xx, v in zip(x, [70.1, 22.4]):
    ax.text(xx, v + 1.8, f"{v:.1f}\\%", ha="center", fontsize=9.5)
ax.set_xticks(x); ax.set_xticklabels(["학습\n(2025 이전)", "유보\n(2025 이후)"],
                                     fontsize=8.4)
ax.set_ylabel("\\texttt{daily\\_pass} 인 작품 비율"); ax.set_ylim(0, 84)
ax.set_title("같은 축이 두 시기에 다른 것을 뜻한다", fontsize=9.4, pad=6)

# 오른쪽 — 도메인마다 무엇으로 채우나
ax = axes[1]
R = [("웹툰", "daily\\_pass", True), ("애니", "가격", False),
     ("모바일", "가격", False), ("도서", "정가", False),
     ("펀딩", "최저 후원", False), ("아이돌", "앨범 정가", False),
     ("만화", "성인 여부", False), ("세계애니", "성인 여부", False),
     ("게임", "(막힘)", False)]
y = np.arange(len(R))[::-1]
for yy, (dm, src, bad) in zip(y, R):
    ax.text(0.02, yy, dm, fontsize=7.6, va="center")
    ax.text(0.42, yy, src, fontsize=7.6, va="center",
            color="#a33b3b" if bad else "#333",
            fontweight="bold" if bad else "normal")
    if bad:
        ax.text(0.93, yy, "사후", fontsize=7.2, va="center", color="#a33b3b")
ax.set_xlim(0, 1.1); ax.set_ylim(-0.8, len(R) - 0.2)
ax.axis("off")
ax.set_title("\\texttt{entry\\_friction} 을 무엇으로 채우나", fontsize=9.4, pad=6)
fig.suptitle("한 축 이름, 아홉 가지 원본 --- 하나만 사후였다", fontsize=10, y=1.0)
fig.tight_layout(); fig.savefig(D / "fields.pdf"); plt.close(fig)

# 그림 2 — 판 되돌림
fig, ax = plt.subplots(figsize=(7.0, 2.5))
S = [("노트 242\n17축", 0.4569), ("노트 255\n웹툰 태그", 0.4623),
     ("노트 257\n$+$애니", 0.4687), ("노트 260\n$+$메타", 0.4916),
     ("노트 262\n$-$새는 축", 0.4772)]
x = np.arange(len(S))
cs = ["#8a8f98", "#5f8f6f", "#3f7a55", "#1f5138", "#a33b3b"]
ax.plot(x, [s[1] for s in S], "o-", color="#333", lw=1.5, ms=0, zorder=1)
ax.scatter(x, [s[1] for s in S], s=70, color=cs, zorder=3)
for xx, s in zip(x, S):
    ax.text(xx, s[1] + 0.0035, f"{s[1]:.4f}", ha="center", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels([s[0] for s in S], fontsize=7.4)
ax.set_ylim(0.450, 0.500); ax.set_ylabel("판 $\\rho$")
ax.set_title("노트 213과 같은 되돌림 --- 점수가 아니라 자료가 옳아진다",
             fontsize=10, pad=7)
fig.tight_layout(); fig.savefig(D / "board.pdf"); plt.close(fig)
print("ok")
