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

RED, GRN, BLU, GRY, INK = "#a33b3b", "#2f6f4f", "#3c5f8a", "#9aa0a8", "#3b3b3b"
T = [("F9_ranklik", .4449, .6341, "순수 풀링", GRN),
     ("F6_directpool", .4472, .5272, "순수 풀링", GRN),
     ("F21_recentpick", .4544, .0880, "도메인별 배합", BLU),
     ("F23_rankmix", .4842, .0454, "반반 섞음", GRY),
     ("F10_pershrink", .4082, .0000, "도메인별 배합", BLU),
     ("F8_boost", .4766, .0000, "잎 하한", RED),
     ("F18_bagboost", .4842, .0000, "잎 하한", RED)]

fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.1),
                         gridspec_kw={"width_ratios": [1.1, 1], "wspace": 0.36})

# --- 왼쪽: 판 대 전용열 이득 --------------------------------------------
ax = axes[0]
POS = {"F9_ranklik": (0, .040), "F6_directpool": (0, .040),
       "F21_recentpick": (0, .045), "F23_rankmix": (-.0055, .048),
       "F10_pershrink": (0, .045), "F8_boost": (0, -.060),
       "F18_bagboost": (.0058, -.008)}
for nm, b, g, mech, c in T:
    ax.plot(b, g, "o", color=c, ms=8, zorder=4)
    dx, dy = POS[nm]
    ax.text(b + dx, g + dy, nm.split("_")[0], fontsize=7.2, color=c,
            ha="center")
ax.annotate("", xy=(.4085, -.012), xytext=(.4200, -.045),
            arrowprops=dict(arrowstyle="->", color=INK, lw=1.0))
ax.text(.4210, -.050, "반례 --- 판도 꼴찌고 못 쓴다", fontsize=6.9,
        color=INK, va="center")
ax.set_xlim(.400, .497)
ax.set_ylim(-.10, .72)
ax.tick_params(labelsize=7.2)
ax.set_xlabel("판 rho (유보)", fontsize=7.8, labelpad=2)
ax.set_ylabel("팝업 전용 열(라벨 누출)의 이득", fontsize=7.8)
ax.set_title("판 상위 셋이 전부 눈이 멀어 있다", fontsize=9.4, pad=6)
ax.text(.4025, .655, "spearman $-$0.34 (n$=$7, p$=$0.46)\n"
        "--- 경향이지 법칙이 아니다", fontsize=6.9, color=INK)

# --- 오른쪽: 기전별 --------------------------------------------------
ax = axes[1]
order = sorted(T, key=lambda x: -x[2])
y = np.arange(len(order))[::-1]
for yy, (nm, b, g, mech, c) in zip(y, order):
    ax.barh(yy, g, color=c, height=0.56, zorder=3)
    ax.text(g + 0.012, yy, f"{g:+.4f}", va="center", fontsize=7.0, color=c)
ax.set_yticks(y)
ax.set_yticklabels([f"{o[0].split('_')[0]}  ·  {o[3]}" for o in order],
                   fontsize=7.0)
ax.set_xlim(0, 0.80)
ax.tick_params(axis="x", labelsize=7.2)
ax.axvline(0, color=INK, lw=0.9, zorder=2)
ax.set_xlabel("전용 열의 이득", fontsize=7.8, labelpad=2)
ax.set_title("눈이 머는 방식이 셋이다", fontsize=9.4, pad=6)
fig.suptitle("판에서 이기는 쪽이 작은 도메인의 말을 못 듣는다",
             fontsize=10.4, y=1.005)
fig.subplots_adjust(left=.105, right=.985, top=.805, bottom=.185)
fig.savefig(D / "picked.pdf"); plt.close(fig)
print("ok")
