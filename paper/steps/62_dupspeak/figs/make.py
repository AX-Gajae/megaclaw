import json, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import paper.figs  # noqa: F401,E402  (한글 폰트·rcParams)
D = Path(__file__).resolve().parent

# ── 그림 1 · 판 사다리 ────────────────────────────────────────────────
LAD = [("그대로\n(19축)",              0.4546, "base"),
       ("태그 수를\n새 열로",            0.4652, "up"),
       ("있는 열을\n그대로 복사",         0.4648, "up"),
       ("alpha\n20$\\to$10",         0.4545, "base"),
       ("모바일 price\n새 열로",         0.4383, "dn"),
       ("뭉갬 풀기\n(분위 경계)",         0.4213, "dn")]
C = {"base": "#8a8f98", "up": "#2f6f4f", "dn": "#a33b3b"}
fig, ax = plt.subplots(figsize=(7.0, 3.1))
x = np.arange(len(LAD))
v = [t[1] for t in LAD]
ax.bar(x, [t - 0.41 for t in v], bottom=0.41,
       color=[C[t[2]] for t in LAD], width=0.62)
ax.axhline(0.4546, color="#333", lw=0.9, ls=(0, (4, 3)))
ax.text(5.42, 0.4553, "그대로", ha="right", va="bottom", fontsize=7.5, color="#333")
for i, (lab, val, k) in enumerate(LAD):
    ax.text(i, val + 0.0012, f"{val:.4f}", ha="center", va="bottom", fontsize=8.2)
ax.set_xticks(x); ax.set_xticklabels([t[0] for t in LAD], fontsize=8.2)
ax.set_ylim(0.41, 0.474)
ax.set_ylabel("판 $\\rho$ (유보 2,565건)")
ax.set_title("정보가 0 인 복사본이 새 축과 같은 값을 낸다", fontsize=10, pad=7)
fig.tight_layout(); fig.savefig(D / "ladder.pdf"); plt.close(fig)

# ── 그림 2 · 겹말 지도 ───────────────────────────────────────────────
cur = json.loads((Path("data/state/note240_dups.json")).read_text())
RET = [(0.985, "웹툰", "target_breadth", "n_tag"),
       (1.000, "세계애니", "target_breadth", "n_tag"),
       (1.000, "만화", "target_breadth", "n_tag"),
       (0.959, "모바일", "entry_friction", "price"),
       (1.000, "애니", "target_breadth", "age")]
fig, ax = plt.subplots(figsize=(7.0, 3.6))
ys, cs, ls = [], [], []
for h in sorted(cur, key=lambda z: abs(z["rho"])):
    ys.append(abs(h["rho"])); cs.append("#8a8f98")
    ls.append(f"{h['dom']}  {h['a'].replace('_',' ')} ~ {h['b'].replace('_',' ')}")
for r, dm, a, b in sorted(RET):
    ys.append(r); cs.append("#a33b3b")
    ls.append(f"{dm}  {a.replace('_',' ')} ~ {b}  (취소)")
y = np.arange(len(ys))
ax.barh(y, [v - 0.94 for v in ys], left=0.94, color=cs, height=0.66)
ax.set_yticks(y); ax.set_yticklabels(ls, fontsize=6.6)
ax.set_xlim(0.94, 1.004); ax.set_xlabel("학습 구간 관측 행 안 순위 상관 $|\\rho|$")
ax.axvline(0.95, color="#333", lw=0.8, ls=(0, (3, 3)))
ax.set_title("지금 판에 이미 있던 겹말 15쌍(회색)과 이번에 취소한 5쌍(빨강)",
             fontsize=10, pad=7)
fig.tight_layout(); fig.savefig(D / "dupmap.pdf"); plt.close(fig)
print("ok")
