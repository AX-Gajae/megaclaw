import json, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import paper.figs  # noqa: F401,E402
from scipy.stats import spearmanr
D = Path(__file__).resolve().parent

# ── 그림 1 · 조각을 줄일수록 잘 읽는다 ──────────────────────────────────
PTS = [("반해 여섯", 6, 3245, 0.214),
       ("해 다섯",   5, 4400, 0.203),
       ("해 셋",     3, 3245, 0.357),
       ("해 둘",     2, 2149, 0.478),
       ("2024 한 조각", 1, 1121, 0.511)]
PTS = sorted(PTS, key=lambda p: -p[2])
fig, ax = plt.subplots(figsize=(7.0, 3.3))
x = [p[2] for p in PTS]; y = [p[3] for p in PTS]
ax.plot(x, y, "o-", color="#2f5fa3", ms=7, lw=1.4, zorder=3)
for lab, n, xx, yy in PTS:
    ax.annotate(f"{lab}\n(조각 {n})", (xx, yy), textcoords="offset points",
                xytext=(0, 11 if lab != "해 다섯" else -24), ha="center", fontsize=7.2,
                color="#333")
ax.set_xlabel("안쪽 평가에 쓴 레코드 수")
ax.set_ylabel("작은 칸 spearman (유보와)")
ax.set_ylim(0.14, 0.60); ax.set_xlim(800, 4800)
ax.set_title("자료를 더 많이 쓸수록 못 읽는다 --- 옛 시대를 섞기 때문이다",
             fontsize=10, pad=8)
fig.tight_layout(); fig.savefig(D / "slices.pdf"); plt.close(fig)

# ── 그림 2 · 유보 반쪽끼리 ────────────────────────────────────────────
R = json.loads(Path("data/state/note244_half.json").read_text())
sm = [r for r in R if abs(r["전체"]) <= 0.010]
fig, ax = plt.subplots(figsize=(7.0, 3.6))
ax.axhline(0, color="#888", lw=0.7); ax.axvline(0, color="#888", lw=0.7)
big = [r for r in R if abs(r["전체"]) > 0.010]
ax.scatter([r["A"] for r in big], [r["B"] for r in big], s=42,
           color="#c9ccd1", marker="o", zorder=2, label="큰 것 넷")
ax.scatter([r["A"] for r in sm], [r["B"] for r in sm], s=38,
           color="#2f6f4f", marker="s", zorder=3,
           label=f"작은 것 {len(sm)} ($|\\Delta| \\leq 0.010$)")
lim = [-0.085, 0.012]
ax.plot(lim, lim, ls=(0, (4, 3)), color="#666", lw=0.9, zorder=1)
ax.set_xlim(*lim); ax.set_ylim(*lim)
A2 = np.array([r["A"] for r in sm]); B2 = np.array([r["B"] for r in sm])
ax.set_xlabel("유보 반쪽 A 이득"); ax.set_ylabel("유보 반쪽 B 이득")
ax.legend(fontsize=7.4, frameon=False, loc="upper left")
ax.set_title(f"유보는 그 칸을 읽는다 --- 반쪽끼리 spearman "
             f"{spearmanr(A2,B2).correlation:+.2f} (부호 11/13)",
             fontsize=10, pad=8)
fig.tight_layout(); fig.savefig(D / "halves.pdf"); plt.close(fig)
print("ok")
