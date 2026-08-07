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
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.3),
                         gridspec_kw={"width_ratios": [1.2, 1], "wspace": 0.40})

# 이름, 옛(효과,se,n), 새(효과,se,n)
S = [("시장층", (+0.3204, 0.1953, 30), (-0.0275, 0.2000, 18)),
     ("피처",   (+0.1874, 0.1186, 29), (+0.0746, 0.1061, 18)),
     ("신호",   (+0.2107, 0.1395, 27), (+0.2160, 0.0977, 21)),
     ("합침",   (+0.2411, 0.0895, 86), (+0.0945, 0.0797, 57))]

# --- 왼쪽: 옛 대 새 -----------------------------------------------------
ax = axes[0]
y = np.arange(len(S))[::-1]
for yy, (nm, o, w) in zip(y, S):
    ok = GRN if nm == "신호" else (RED if w[0] < 0.10 * 1 and nm != "합침" else GRY)
    ax.errorbar(o[0], yy + 0.17, xerr=1.96 * o[1], fmt="o", color=GRY, ms=4.6,
                capsize=3, lw=1.3, zorder=3)
    ax.errorbar(w[0], yy - 0.17, xerr=1.96 * w[1], fmt="s",
                color=(GRN if nm == "신호" else RED), ms=4.6, capsize=3, lw=1.6,
                zorder=3)
    ax.text(o[0] + 1.96 * o[1] + 0.02, yy + 0.17, f"옛 n{o[2]}", va="center",
            fontsize=6.3, color=GRY)
    ax.text(w[0] + 1.96 * w[1] + 0.02, yy - 0.17, f"새 n{w[2]}", va="center",
            fontsize=6.3, color=(GRN if nm == "신호" else RED))
ax.axvline(0, color=INK, lw=.9, zorder=2)
ax.set_yticks(y); ax.set_yticklabels([s[0] for s in S], fontsize=8.4)
ax.set_xlim(-0.50, 0.92)
ax.set_xlabel("주입이 APE 를 줄인 배수 (log · 사전 등록한 척도)", fontsize=7.8)
ax.tick_params(axis="x", labelsize=7.0)
ax.set_title("옛 자료(동그라미) 대 새 57건(네모)", fontsize=8.6, pad=8)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.grid(axis="x", lw=.4, color="#e3e3e3", zorder=0)
ax.set_ylim(-0.85, 3.75)
ax.text(-0.47, -0.72, "시장층은 부호가 뒤집히고 피처는 반토막 --- 신호만 그대로다",
        fontsize=6.8, color=INK)

# --- 오른쪽: 사전 등록한 문턱 -------------------------------------------
ax = axes[1]
T = [("시장층", 1.32, 48), ("피처", 1.73, 47), ("신호", 2.41, 48)]
x = np.arange(len(T))
for xx, (nm, t, n) in zip(x, T):
    c = GRN if t > 2.39 else RED
    ax.bar(xx, t, color=c, width=.52, zorder=3)
    ax.text(xx, t + 0.07, f"{t:.2f}", ha="center", fontsize=8.2, color=c)
    ax.text(xx, -0.28, f"n {n}", ha="center", fontsize=6.8, color=GRY)
ax.axhline(2.39, color=INK, lw=1.1, ls="--", zorder=4)
ax.text(2.52, 2.44, "사전 등록\n문턱 2.39", fontsize=6.8, color=INK, va="bottom")
ax.set_xticks(x); ax.set_xticklabels([t[0] for t in T], fontsize=8.0)
ax.set_ylim(-0.42, 3.35); ax.set_xlim(-0.62, 3.35)
ax.set_ylabel("$|t|$  (옛 + 새 전부)", fontsize=8)
ax.tick_params(axis="y", labelsize=7.0)
ax.set_title("셋 중 하나만 넘는다", fontsize=8.6, pad=8)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(axis="y", lw=.4, color="#e3e3e3", zorder=0)
ax.text(1.35, 2.99, "미리 적은 규칙: 하나만 넘으면 '넘었다'고 하지 않는다",
        fontsize=6.5, color=RED, ha="center")

fig.suptitle("셋이 같았던 것이 우연이었다", fontsize=10.4, y=1.03)
fig.savefig(D / "replicate.pdf", bbox_inches="tight")
fig.savefig(D / "replicate.png", dpi=150, bbox_inches="tight")
print("ok")
