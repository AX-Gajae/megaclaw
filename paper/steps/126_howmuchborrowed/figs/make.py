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

R = json.load(open("/Users/ax/.claude/jobs/a5c89f96/tmp/n302.json"))
# 학습행(노트 296 표)
TRAIN = {"웹툰": 2106, "세계애니": 2648, "애니": 1467, "만화": 1783, "모바일": 1559,
         "게임": 259, "펀딩": 320, "시장팝업": 101, "도서": 80, "아이돌": 54, "팝업": 16}

GRN, RED, GRY, INK, BLU = "#2f6f4f", "#a33b3b", "#9aa0a8", "#3b3b3b", "#33628f"
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.35),
                         gridspec_kw={"width_ratios": [1.1, 1], "wspace": 0.42})

rows = sorted(R.items(), key=lambda kv: kv[1]["차"])
ax = axes[0]
y = np.arange(len(rows))[::-1]
for yy, (d, v) in zip(y, rows):
    t = v["t"]
    c = RED if t < -2 else (GRN if t > 2 else GRY)
    ax.errorbar(v["차"], yy, xerr=2 * v["짝SE"], fmt="o", color=c, ms=4.8,
                capsize=3.2, lw=1.5, zorder=3)
    ax.text(0.088, yy, f"{v['끈축']}축", va="center", ha="right", fontsize=6.4,
            color=(c if abs(t) > 2 else GRY))
ax.axvline(0, color=INK, lw=.9, zorder=2)
ax.set_yticks(y); ax.set_yticklabels([d for d, _ in rows], fontsize=7.4)
lo = min(v["차"] - 2 * v["짝SE"] for _, v in rows)
ax.set_xlim(min(lo * 1.12, -0.06), 0.095)
ax.set_xlabel("자기 '안 오른다' 축을 껐을 때 rho 변화 ($\\pm$2$\\times$짝SE)",
              fontsize=7.5)
ax.tick_params(axis="x", labelsize=6.8)
ax.set_title("빌리는 도메인은 둘뿐이다", fontsize=8.6, pad=8)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.grid(axis="x", lw=.4, color="#e3e3e3", zorder=0)

# --- 오른쪽: 학습행 대 빌린 양 ------------------------------------------
ax = axes[1]
for d, v in R.items():
    n = TRAIN.get(d)
    if not n: continue
    b = -v["차"]
    c = RED if v["t"] < -2 else GRY
    ax.scatter(n, b, s=34, color=c, zorder=3)
    ax.annotate(d, (n, b), textcoords="offset points", xytext=(5, 3),
                fontsize=6.6, color=INK)
ax.axhline(0, color=INK, lw=.8, zorder=2)
ax.set_xscale("log")
ax.set_xlabel("학습행 (로그)", fontsize=7.8)
ax.set_ylabel("빌린 양 (rho)", fontsize=8)
ax.tick_params(labelsize=6.9)
ax.set_title("작은 도메인이 빌린다", fontsize=8.6, pad=8)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(lw=.4, color="#e3e3e3", zorder=0)

fig.suptitle("누가 누구에게서 빌리나", fontsize=10.4, y=1.03)
fig.savefig(D / "borrow.pdf", bbox_inches="tight")
fig.savefig(D / "borrow.png", dpi=150, bbox_inches="tight")
print("ok")
