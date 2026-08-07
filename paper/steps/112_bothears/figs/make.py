import sys, json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import paper.figs  # noqa: F401,E402
matplotlib.rcParams["axes.unicode_minus"] = False
D = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[4]

GRN, RED, GRY, INK = "#2f6f4f", "#a33b3b", "#9aa0a8", "#3b3b3b"
W = json.loads((ROOT / "data/state/note290_who.json").read_text())
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.2),
                         gridspec_kw={"width_ratios": [1, 1.1], "wspace": 0.40})

ax = axes[0]
POS = {"F9_ranklik": (1.20, .012), "F6_directpool": (1.20, -.014),
       "F21_recentpick": (1.20, 0), "F23_rankmix": (1.20, 0),
       "F8_boost": (1.22, -.020), "F18_bagboost": (1.22, .018),
       "F10_pershrink": (0.82, 0)}
for w in W:
    th = max(w["청력문턱"], 1.0)
    c = GRN if w["청력문턱"] == 0 else (RED if w["청력문턱"] >= 400 else GRY)
    ax.plot(th, w["잃는값"], "o", color=c, ms=7.5, zorder=4)
    fx, dy = POS[w["정식화"]]
    ax.text(th * fx, w["잃는값"] + dy, w["정식화"].split("_")[0], fontsize=7.2,
            color=c, ha="left" if fx > 1 else "right", va="center")
ax.axhline(0, color=INK, lw=0.9, zorder=2)
ax.set_xscale("log"); ax.set_xlim(0.6, 1600); ax.set_ylim(-0.50, 0.28)
ax.set_xticks([1, 22, 400])
ax.set_xticklabels(["0\n(문턱 없음)", "22", "400"], fontsize=7.2)
ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
ax.tick_params(axis="y", labelsize=7.2)
ax.set_xlabel("청력 문턱 (학습행 · 노트 280)", fontsize=7.8, labelpad=2)
ax.set_ylabel("표지를 지웠을 때 잃는 값", fontsize=7.8)
ax.set_title("귀가 밝을수록 누출을 줍는다", fontsize=9.4, pad=6)
ax.text(0.72, 0.235, "spearman $-$0.896 (n$=$7 · p$=$0.006)", fontsize=7.0,
        color=INK)

ax = axes[1]
S = sorted(W, key=lambda w: -w["표지지움"])
y = np.arange(len(S))[::-1]
wd = 0.36
for yy, s in zip(y, S):
    c = GRN if s["청력문턱"] == 0 else (RED if s["청력문턱"] >= 400 else GRY)
    ax.barh(yy + wd / 2, s["표지있음"], height=wd, color=c, alpha=.40, zorder=3)
    ax.barh(yy - wd / 2, s["표지지움"], height=wd, color=c, zorder=3)
ax.axvline(0, color=INK, lw=0.9, zorder=2)
ax.set_yticks(y)
ax.set_yticklabels([s["정식화"].split("_")[0] for s in S], fontsize=7.4)
ax.set_xlim(-0.11, 0.47)
ax.tick_params(axis="x", labelsize=7.2)
ax.set_xlabel("팝업 rho   연한 = 표지 있음 · 진한 = 지움", fontsize=7.4,
              labelpad=2)
ax.set_title("지우고 나면 순위가 뒤집힌다", fontsize=9.4, pad=6)
fig.suptitle("청력은 양날이다 --- 신호도 줍고 누출도 줍는다", fontsize=10.4,
             y=1.005)
fig.subplots_adjust(left=.108, right=.985, top=.795, bottom=.19)
fig.savefig(D / "ears.pdf"); plt.close(fig)
print("ok")
