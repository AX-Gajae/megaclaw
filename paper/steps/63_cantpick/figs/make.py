import json, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import paper.figs  # noqa: F401,E402
D = Path(__file__).resolve().parent

# ── 그림 1 · 도메인별 기울기를 주면 ────────────────────────────────────
BARS = [("target breadth\n세 도메인",  +0.0102, True),
        ("target breadth\n전 도메인",  +0.0062, True),
        ("media push\n전 도메인",      +0.0040, True),
        ("venue prominence\n전 도메인", +0.0009, True),
        ("target breadth\n이름 공유",   +0.0005, False),
        ("goods scale\n전 도메인",     -0.0037, True),
        ("entry friction\n전 도메인",  -0.0309, True)]
fig, ax = plt.subplots(figsize=(7.0, 3.0))
x = np.arange(len(BARS))
v = [b[1] for b in BARS]
cs = ["#2f6f4f" if t > 0 else "#a33b3b" for t in v]
cs[4] = "#8a8f98"
ax.bar(x, v, color=cs, width=0.6)
ax.axhline(0, color="#333", lw=0.9)
for i, (lab, val, _) in enumerate(BARS):
    ax.text(i, val + (0.0012 if val > 0 else -0.0018), f"{val:+.4f}",
            ha="center", va="bottom" if val > 0 else "top", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels([b[0] for b in BARS], fontsize=7.4)
ax.set_ylabel("판 $\\rho$ 짝 차")
ax.set_ylim(-0.036, 0.016)
ax.set_title("도메인별 기울기를 주면 --- 다섯 중 넷은 손해다(노트 126)",
             fontsize=10, pad=7)
ax.annotate("이름을 공유하면\n벌점만 반이 되는데\n아무 일도 안 난다",
            xy=(4, 0.0005), xytext=(3.1, -0.0175), fontsize=7.2, color="#444",
            ha="center", arrowprops=dict(arrowstyle="->", color="#777", lw=0.8))
fig.tight_layout(); fig.savefig(D / "slopes.pdf"); plt.close(fig)

# ── 그림 2 · 안쪽 순위와 유보 승자 ─────────────────────────────────────
rows = json.loads(Path("data/state/note241_inner.json").read_text())
WIN = {("target_breadth", "웹툰"), ("target_breadth", "세계애니"),
       ("target_breadth", "만화")}
TOP3 = {("goods_scale", "웹툰"), ("entry_friction", "애니"),
        ("venue_prominence", "애니")}
fig, ax = plt.subplots(figsize=(7.0, 3.4))
g = [r["안쪽이득"] for r in rows]
y = np.arange(len(g))[::-1]
cs, ls = [], []
for r in rows:
    k = (r["축"], r["도메인"])
    cs.append("#a33b3b" if k in WIN else ("#2f5fa3" if k in TOP3 else "#c9ccd1"))
    ls.append(f"{r['축'].replace('_',' ')}  {r['도메인']}  ({r['부호']}/3)")
ax.barh(y, g, color=cs, height=0.72)
ax.axvline(0, color="#333", lw=0.8)
ax.set_yticks(y); ax.set_yticklabels(ls, fontsize=6.0)
ax.set_xlabel("안쪽(학습 구간) 이득 · 앞으로 세 조각 평균")
ax.set_title("안쪽 1위(파랑)는 유보에서 $-$0.0070 · 유보 승자(빨강)는 안쪽 6 · 7위와 순위권 밖",
             fontsize=9, pad=7)
fig.tight_layout(); fig.savefig(D / "innerrank.pdf"); plt.close(fig)
print("ok")
