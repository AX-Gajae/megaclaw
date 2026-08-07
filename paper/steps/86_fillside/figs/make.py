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
                         gridspec_kw={"width_ratios": [1.1, 1], "wspace": 0.36})
# 왼쪽 — 마스크를 씌우기 전후
ax = axes[0]
E = [("2010\\textasciitilde18", 68.0), ("2018\\textasciitilde22", 91.4),
     ("2022\\textasciitilde25", 93.4), ("2025\\textasciitilde", 98.9)]
x = np.arange(len(E))
ax.plot(x, [e[1] for e in E], "o-", color="#c08a3e", lw=1.6, ms=7)
for xx, e in zip(x, E):
    ax.text(xx, e[1] + 1.6, f"{e[1]:.0f}\\%", ha="center", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels([e[0] for e in E], fontsize=7.4)
ax.set_ylabel("\\texttt{n\\_shot} $=$ 0 인 비율"); ax.set_ylim(60, 106)
ax.set_title("가드가 처음 문 것 --- 그런데 이 0 들은\n이미 마스크 0 이었다",
             fontsize=9, pad=6)

# 오른쪽 — 되짚어 잡히나
ax = axes[1]
R = [("웹툰 entry\\_friction\n$\\leftarrow$ daily\\_pass", -0.44, 32),
     ("웹툰 goods\\_scale\n$\\leftarrow$ n\\_episode", -0.49, 45)]
y = np.arange(len(R))[::-1]
ax.barh(y, [abs(r[1]) for r in R], color="#a33b3b", height=0.5)
for yy, r in zip(y, R):
    ax.text(abs(r[1]) + 0.015, yy, f"연도 {r[1]:+.2f} · 비 {r[2]}\\%",
            va="center", fontsize=7.4, color="#a33b3b")
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in R], fontsize=7)
ax.set_xlim(0, 0.82); ax.set_xlabel("$|$연도 상관$|$")
ax.set_title("막기 전 판에 돌리면\n손으로 찾은 둘을 그대로 문다", fontsize=9, pad=6)
fig.suptitle("가드 열여덟 · 쌓임 --- 축 이름이 아니라 채우는 필드를 본다",
             fontsize=10, y=1.0)
fig.tight_layout(); fig.savefig(D / "guard.pdf"); plt.close(fig)
print("ok")
