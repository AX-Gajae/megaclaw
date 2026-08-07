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

GRN, RED, GRY, INK, BLU = "#2f6f4f", "#a33b3b", "#9aa0a8", "#3b3b3b", "#33628f"
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.25),
                         gridspec_kw={"width_ratios": [1, 1.08], "wspace": 0.40})

# --- 왼쪽: 정규화한 검출 문턱 (문턱 / 지표 수준) --------------------------
ax = axes[0]
T = [("판", 2.1, "2,675", GRN),
     ("게임", 2.4, "180", GRN),
     ("웹툰", 10.2, "711", GRN),
     ("신호", 15.0, "27", RED),
     ("피처", 26.4, "29", RED),
     ("시장층", 41.2, "30", RED),
     ("내부", 64.9, "9", RED)]
x = np.arange(len(T)) + np.array([0, 0, 0, .55, .55, .55, .55])
for xx, (nm, pc, note, c) in zip(x, T):
    ax.bar(xx, pc, color=c, width=.62, zorder=3)
    ax.text(xx, pc + 1.8, f"{pc:.0f}%", ha="center", fontsize=8.0, color=c)
    ax.text(xx, -5.6, f"n {note}", ha="center", fontsize=6.3, color=GRY)
ax.set_xticks(x)
ax.set_xticklabels([t[0] for t in T], fontsize=7.4)
ax.text(1.0, -12.6, "lab (ρ)", ha="center", fontsize=7.6, color=GRN)
ax.text(4.55, -12.6, "하네스 (MAPE)", ha="center", fontsize=7.6, color=RED)
ax.plot([-.4, 2.4], [-9.4, -9.4], lw=.9, color=GRN)
ax.plot([3.1, 6.05], [-9.4, -9.4], lw=.9, color=RED)
ax.set_ylim(-16, 74)
ax.set_yticks([0, 10, 20, 30, 40, 50, 60, 70])
ax.tick_params(axis="y", labelsize=7.2)
ax.set_ylabel("검출 문턱 ÷ 지표 수준", fontsize=8)
ax.set_title("하네스가 더 거칠다 --- 표본이 100배 작아서", fontsize=8.6, pad=8)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(axis="y", lw=.4, color="#e3e3e3", zorder=0)

# --- 오른쪽: 배수 척도의 효과 + 두 문턱 ----------------------------------
ax = axes[1]
S = [("시장층", 0.3204, 0.1953, 30),
     ("피처", 0.1874, 0.1186, 29),
     ("신호", 0.2107, 0.1395, 27),
     ("합침", 0.2411, 0.0895, 86)]
y = np.arange(len(S))[::-1]
for yy, (nm, e, se, n) in zip(y, S):
    c = BLU if nm != "합침" else GRN
    ax.errorbar(e, yy, xerr=1.96 * se, fmt="o", color=c, ms=5.0,
                capsize=3.2, lw=1.5, zorder=3)
    ax.text(e + 1.96 * se + 0.035, yy, f"t={e/se:+.2f}", va="center",
            fontsize=7.4, color=c)
    ax.text(-0.30, yy, f"n {n}", va="center", ha="left", fontsize=6.8, color=GRY)
ax.axvline(0, color=INK, lw=.8, zorder=2)
ax.set_yticks(y)
ax.set_yticklabels([s[0] for s in S], fontsize=8)
ax.set_xlim(-0.34, 0.92)
ax.set_xlabel("주입이 APE 를 줄인 배수 (log 척도)", fontsize=8)
ax.tick_params(axis="x", labelsize=7.2)
ax.set_title("셋이 거의 같은 값을 낸다 --- 합쳐야 문턱을 넘는다",
             fontsize=8.6, pad=8)
ax.text(0.29, -0.55, "각각은 자기 문턱 아래 · 합쳐야 $|t|{>}2$",
        fontsize=7.0, color=INK, ha="center")
ax.text(0.29, -0.95, "다중비교 $m{=}4$ 는 2.50 통과 · $m{=}8$ 은 2.73 미달",
        fontsize=6.8, color=RED, ha="center")
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.grid(axis="x", lw=.4, color="#e3e3e3", zorder=0)
ax.set_ylim(-1.35, 3.5)

fig.suptitle("가 보려던 자리가 더 거친 자리였다", fontsize=10.4, y=1.02)
fig.savefig(D / "floor.pdf", bbox_inches="tight")
fig.savefig(D / "floor.png", dpi=150, bbox_inches="tight")
print("ok")
