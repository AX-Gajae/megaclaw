import json, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import paper.figs  # noqa: F401,E402
D = Path(__file__).resolve().parent

fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.4),
                         gridspec_kw={"width_ratios": [1, 1.1], "wspace": 0.36})
# 왼쪽 — 게임 점수
ax = axes[0]
DOM = [("게임", 0.1911, 0.6184), ("세계애니", 0.5312, 0.5312),
       ("모바일", 0.5309, 0.5309), ("애니", 0.5076, 0.5076),
       ("웹툰", 0.4520, 0.4520), ("도서", 0.3729, 0.3729),
       ("팝업", 0.3615, 0.3615), ("펀딩", 0.2628, 0.2628),
       ("아이돌", 0.1446, 0.1446)]
y = np.arange(len(DOM))[::-1]
for yy, (dm, a, b) in zip(y, DOM):
    if abs(b - a) > 1e-6:
        ax.plot([a, b], [yy, yy], color="#a33b3b", lw=2.0, zorder=2)
        ax.scatter([a], [yy], s=34, color="#c9ccd1", zorder=3)
        ax.scatter([b], [yy], s=44, color="#a33b3b", zorder=4)
        ax.text(b + 0.015, yy, f"{b-a:+.3f}", fontsize=7.4, va="center",
                color="#a33b3b")
    else:
        ax.scatter([a], [yy], s=34, color="#8a9ab3", zorder=3)
ax.set_yticks(y); ax.set_yticklabels([d[0] for d in DOM], fontsize=7.6)
ax.set_xlim(0.10, 0.78); ax.set_xlabel("배포 규약 $\\rho$")
ax.set_title("게임 하나가 $+$0.43 틀려 있었다", fontsize=9.4, pad=6)

# 오른쪽 — 낙관 편의
ax = axes[1]
AXN = [5, 17, 23]
F18 = [0.2004, 0.2015, 0.1755]
F21 = [0.0348, 0.0360, 0.0319]
ax.plot(AXN, F18, "o-", color="#c08a3e", lw=1.8, ms=8, label="F18 나무")
ax.plot(AXN, F21, "s-", color="#6f86b3", lw=1.8, ms=8, label="F21 능형")
for x, v in zip(AXN, F18):
    ax.text(x, v + 0.012, f"{v:+.3f}", ha="center", fontsize=7.4)
for x, v in zip(AXN, F21):
    ax.text(x, v - 0.022, f"{v:+.3f}", ha="center", fontsize=7.4)
ax.set_xticks(AXN); ax.set_xlabel("축 수")
ax.set_ylabel("낙관 편의 (전체 $-$ 배포)")
ax.set_ylim(0, 0.26)
ax.legend(fontsize=7.4, frameon=False, loc="center right")
ax.set_title("축이 아니라 정식화의 성질이다", fontsize=9.4, pad=6)
fig.suptitle("스무 노트 만에 실제 실행 경로를 돌려 봤다", fontsize=10, y=1.0)
fig.tight_layout(); fig.savefig(D / "run.pdf"); plt.close(fig)
print("ok")
