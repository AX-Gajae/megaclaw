import json, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import paper.figs  # noqa: F401,E402
D = Path(__file__).resolve().parent

R = [("도서", 0.369, 0.561, 10.46), ("웹툰", 0.453, 0.350, 4.78),
     ("모바일", 0.535, 0.198, 12.69), ("게임", 0.622, 0.182, 34.51),
     ("애니", 0.505, 0.144, 1.62), ("세계애니", 0.534, 0.099, 1.17),
     ("펀딩", 0.267, -0.012, 0.92), ("팝업", 0.361, -0.113, 0.52)]

fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.4),
                         gridspec_kw={"width_ratios": [1.1, 1], "wspace": 0.36})
ax = axes[0]
R2 = sorted(R, key=lambda r: -(r[2] / r[1]))
y = np.arange(len(R2))[::-1]
w = 0.36
ax.barh(y + w / 2, [r[1] for r in R2], height=w, color="#2f6f4f", label="모형")
ax.barh(y - w / 2, [r[2] for r in R2], height=w, color="#c08a3e",
        label="$-$시작일만")
for yy, r in zip(y, R2):
    q = r[2] / r[1]
    ax.text(0.66, yy, f"{q:5.2f}", fontsize=7.4, va="center",
            color="#a33b3b" if q > 1 else "#555",
            fontweight="bold" if q > 1 else "normal")
ax.axvline(0, color="#888", lw=0.7)
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in R2], fontsize=7.6)
ax.set_xlim(-0.18, 0.76); ax.set_xlabel("$\\rho$   (오른쪽 숫자 = 시계 몫)")
ax.legend(fontsize=7.2, frameon=False, loc="lower right")
ax.set_title("도서만 시계가 모형을 이긴다", fontsize=9.4, pad=6)

ax = axes[1]
for dm, mod, cal, dec in R:
    q = cal / mod
    c = "#a33b3b" if q > 1 else "#2f5fa3"
    ax.scatter([dec], [q], s=54, color=c, zorder=3)
    ax.annotate(dm, (dec, q), textcoords="offset points", xytext=(7, 4),
                fontsize=7, color=c)
ax.axhline(1.0, color="#a33b3b", lw=1.0, ls=(0, (4, 3)))
ax.set_xscale("log")
ax.set_xlabel("라벨 쇠퇴비 (첫 조각 $\\div$ 끝 조각)")
ax.set_ylabel("시계 몫 (달력 $\\div$ 모형)")
ax.set_ylim(-0.5, 1.8)
ax.text(20, 1.06, "여기 위면 능력이 아니라 시계", fontsize=7, color="#a33b3b",
        ha="right")
ax.set_title("쇠퇴가 크다고 시계인 건 아니다", fontsize=9.4, pad=6)
fig.suptitle("도메인 점수의 얼마가 ``언제 나왔나'' 인가", fontsize=10, y=1.0)
fig.tight_layout(); fig.savefig(D / "clock.pdf"); plt.close(fig)
print("ok")
