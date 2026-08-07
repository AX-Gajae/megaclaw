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
                         gridspec_kw={"width_ratios": [1.25, 1], "wspace": 0.32})
# 왼쪽 — 판 사다리
ax = axes[0]
S = [("노트 242\n17축", 0.4569, 0.3805, "#8a8f98"),
     ("노트 255\n웹툰 태그", 0.4623, 0.4018, "#5f8f6f"),
     ("노트 257\n$+$애니 태그", 0.4687, 0.3943, "#3f7a55"),
     ("노트 260\n$+$웹툰 메타", 0.4916, 0.4768, "#1f5138")]
x = np.arange(len(S))
ax.plot(x, [s[1] for s in S], "o-", color="#1f5138", lw=1.8, ms=7, label="판")
ax.plot(x, [s[2] for s in S], "s--", color="#a33b3b", lw=1.4, ms=6, label="웹툰")
for xx, s in zip(x, S):
    ax.text(xx, s[1] + 0.006, f"{s[1]:.4f}", ha="center", fontsize=7.6,
            color="#1f5138")
ax.set_xticks(x); ax.set_xticklabels([s[0] for s in S], fontsize=7.2)
ax.set_ylabel("$\\rho$"); ax.set_ylim(0.36, 0.52)
ax.legend(fontsize=7.6, frameon=False, loc="lower right")
ax.set_title("웹툰이 판을 끌고 온다", fontsize=9.4, pad=6)

# 오른쪽 — 데일리패스를 빼니 세졌다
ax = axes[1]
B = [("데일리패스\n넣음", 0.4831, 0.4461, "#c08a3e"),
     ("데일리패스\n뺌", 0.4916, 0.4768, "#2f6f4f")]
w = 0.36; x = np.arange(2)
ax.bar(x - w / 2, [b[1] for b in B], width=w, color=[b[3] for b in B], label="판")
ax.bar(x + w / 2, [b[2] for b in B], width=w,
       color=[b[3] for b in B], alpha=0.5, label="웹툰")
for xx, b in zip(x, B):
    ax.text(xx - w / 2, b[1] + 0.004, f"{b[1]:.4f}", ha="center", fontsize=7.4)
    ax.text(xx + w / 2, b[2] + 0.004, f"{b[2]:.4f}", ha="center", fontsize=7.4)
ax.set_xticks(x); ax.set_xticklabels([b[0] for b in B], fontsize=8)
ax.set_ylim(0.40, 0.53); ax.set_ylabel("$\\rho$")
ax.legend(fontsize=7.2, frameon=False, ncol=2, loc="lower left")
ax.set_title("새는 열이 신호를 흐리고 있었다", fontsize=9.4, pad=6)
fig.suptitle("연재 요일 --- 몇 요일이 아니라 어느 요일", fontsize=10, y=1.0)
fig.tight_layout(); fig.savefig(D / "board.pdf"); plt.close(fig)
print("ok")
