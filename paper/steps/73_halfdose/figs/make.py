import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import paper.figs  # noqa: F401,E402
D = Path(__file__).resolve().parent

# 그림 1 — 값을 갈아 본다
fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.2), sharey=True,
                         gridspec_kw={"wspace": 0.10})
SUB = [("진짜 복사본", +0.0110), ("잡음 값", +0.0023), ("상수 값", +0.0000)]
ALL = [("진짜 복사본", -0.0003), ("잡음 값", -0.0031), ("상수 값", -0.0001)]
for ax, ROWS, ttl in ((axes[0], SUB, "웹툰에게만 준다\n(깃발이 웹툰을 가리킨다)"),
                      (axes[1], ALL, "전 도메인에게 준다\n(깃발이 상수다)")):
    x = np.arange(len(ROWS))
    cs = ["#2f6f4f", "#8a9ab3", "#c9ccd1"]
    ax.bar(x, [r[1] for r in ROWS], color=cs, width=0.52)
    ax.axhline(0, color="#333", lw=0.9)
    for xx, r in zip(x, ROWS):
        ax.text(xx, r[1] + (0.0006 if r[1] >= 0 else -0.0009), f"{r[1]:+.4f}",
                ha="center", va="bottom" if r[1] >= 0 else "top", fontsize=8.2)
    ax.set_xticks(x); ax.set_xticklabels([r[0] for r in ROWS], fontsize=7.8)
    ax.set_title(ttl, fontsize=9, pad=6)
axes[0].set_ylabel("웹툰 $\\rho$ 변화")
axes[0].set_ylim(-0.006, 0.015)
fig.suptitle("마스크는 그대로 두고 값만 갈았다 --- 깃발은 아무 일도 안 한다",
             fontsize=10, y=0.99)
fig.tight_layout(); fig.savefig(D / "flag.pdf"); plt.close(fig)

# 그림 2 — 부분 적용은 사실 전용 열이다
fig, ax = plt.subplots(figsize=(7.0, 2.9))
B = [("이름 공유 열을\n웹툰에게만", +0.0110, "#c08a3e"),
     ("웹툰 \\emph{전용} 이름 열을\n웹툰에게 (노트 241)", +0.0103, "#c08a3e"),
     ("이름 공유 열을\n전 도메인에게", -0.0003, "#8a8f98"),
     ("같은 열 · 이름 공유\n판 전체 (노트 241)", +0.0005, "#8a8f98")]
x = np.arange(len(B))
ax.bar(x, [b[1] for b in B], color=[b[2] for b in B], width=0.5)
ax.axhline(0, color="#333", lw=0.9)
for xx, b in zip(x, B):
    ax.text(xx, b[1] + 0.0005, f"{b[1]:+.4f}", ha="center", fontsize=8.6)
ax.set_xticks(x); ax.set_xticklabels([b[0] for b in B], fontsize=7.0)
ax.set_ylabel("$\\rho$ 변화"); ax.set_ylim(-0.003, 0.0155)
ax.set_title("``일부에게 준 공유 열''과 ``전용 열''은 같은 것이다",
             fontsize=10, pad=7)
fig.tight_layout(); fig.savefig(D / "same.pdf"); plt.close(fig)
print("ok")
