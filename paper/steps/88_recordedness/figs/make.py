import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import paper.figs  # noqa: F401,E402
D = Path(__file__).resolve().parent

fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.4),
                         gridspec_kw={"width_ratios": [1, 1.05], "wspace": 0.36})
# 왼쪽 — 고치기 전후
ax = axes[0]
C = [("성분 0", 0.123, 0.026), ("성분 1", 0.035, -0.046),
     ("성분 2", -0.105, 0.025), ("성분 3", 0.285, -0.006)]
x = np.arange(len(C)); w = 0.36
ax.bar(x - w / 2, [c[1] for c in C], width=w, color="#c08a3e", label="전체 행에서")
ax.bar(x + w / 2, [c[2] for c in C], width=w, color="#2f6f4f", label="기록된 행에서만")
ax.axhline(0, color="#333", lw=0.9)
ax.axhline(0.12, color="#a33b3b", lw=0.9, ls=(0, (3, 3)))
ax.text(3.42, 0.132, "채택 문턱", fontsize=6.8, color="#a33b3b", ha="right")
ax.text(3, 0.30, "$+$0.285\n조각 5/5\n통과했다", fontsize=7, ha="center",
        color="#c08a3e")
ax.set_xticks(x); ax.set_xticklabels([c[0] for c in C], fontsize=8)
ax.set_ylabel("연도 통제 상관"); ax.set_ylim(-0.13, 0.40)
ax.legend(fontsize=7, frameon=False, loc="upper left")
ax.set_title("애니 방영 분기", fontsize=9.4, pad=6)

# 오른쪽 — 기록률이 시기마다 다르다
ax = axes[1]
B = [("학습\n(2025 이전)", 81.7), ("유보\n(2025 이후)", 93.6)]
x = np.arange(2)
ax.bar(x, [b[1] for b in B], color=["#8a9ab3", "#a33b3b"], width=0.5)
for xx, b in zip(x, B):
    ax.text(xx, b[1] + 1.2, f"{b[1]:.1f}\\%", ha="center", fontsize=9.5)
ax.set_xticks(x); ax.set_xticklabels([b[0] for b in B], fontsize=8.4)
ax.set_ylabel("\\texttt{air\\_quarter} 가 기록된 비율"); ax.set_ylim(70, 102)
ax.text(0.5, 74, "``기록됨'' 과 라벨: 학습 $+$0.342", ha="center", fontsize=7.6,
        color="#a33b3b")
ax.set_title("그래서 결측이 신호가 된다", fontsize=9.4, pad=6)
fig.suptitle("토큰이 없는 행은 SVD 에서 ``기록됐나'' 라는 방향을 만든다",
             fontsize=10, y=1.0)
fig.tight_layout(); fig.savefig(D / "rec.pdf"); plt.close(fig)
print("ok")
