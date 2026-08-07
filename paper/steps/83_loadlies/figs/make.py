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
                         gridspec_kw={"width_ratios": [1.1, 1], "wspace": 0.34})
# 왼쪽 — 떼어 보기
ax = axes[0]
R = [("셋 다", 0.4916, 0.4768, 5.33), ("요일만", 0.4881, 0.4603, 5.20),
     ("요일$+$등급", 0.4872, 0.4606, 5.05), ("작가수만", 0.4714, 0.4060, 2.99),
     ("등급만", 0.4701, 0.4010, 1.24), ("등급$+$작가수", 0.4691, 0.3994, 0.74),
     ("바탕(21축)", 0.4687, 0.3943, None)]
y = np.arange(len(R))[::-1]
cs = ["#1f5138" if r[3] and r[3] >= 5 else
      ("#5f8f6f" if r[3] and r[3] >= 2 else "#c9ccd1") for r in R]
ax.barh(y, [r[1] - 0.465 for r in R], left=0.465, color=cs, height=0.62)
for yy, r in zip(y, R):
    lab = f"{r[1]:.4f}" + (f"  ($t{{=}}{r[3]:.1f}$)" if r[3] else "")
    ax.text(r[1] + 0.0008, yy, lab, va="center", fontsize=7)
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in R], fontsize=7.6)
ax.set_xlim(0.465, 0.4985); ax.set_xlabel("판 $\\rho$ (괄호는 웹툰 $t$)")
ax.set_title("요일이 거의 다 낸다", fontsize=9.4, pad=6)

# 오른쪽 — 실린 무게 대 실제 기여
ax = axes[1]
G = [("요일", 1, 24, 0.0194), ("등급", 62, 2, 0.0014), ("작가수", 37, 74, 0.0027)]
x = np.arange(len(G)); w = 0.26
ax.bar(x - w, [g[1] for g in G], width=w, color="#8a9ab3", label="성분0 무게 \\%")
ax.bar(x, [g[2] for g in G], width=w, color="#6f86b3", label="성분3 무게 \\%")
ax2 = ax.twinx()
ax2.bar(x + w, [g[3] for g in G], width=w, color="#1f5138", label="떼어 보기 이득")
ax.set_xticks(x); ax.set_xticklabels([g[0] for g in G], fontsize=8.4)
ax.set_ylabel("SVD 성분에 실린 무게 (\\%)"); ax.set_ylim(0, 100)
ax2.set_ylabel("혼자 넣었을 때 판 이득", color="#1f5138")
ax2.set_ylim(0, 0.026)
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, fontsize=6.6, frameon=False, loc="upper center")
ax.set_title("무게가 낮은 것이 제일 많이 낸다", fontsize=9.4, pad=6)
fig.suptitle("SVD 에 실린 무게로 기여를 읽으면 틀린다", fontsize=10, y=1.0)
fig.tight_layout(); fig.savefig(D / "load.pdf"); plt.close(fig)
print("ok")
