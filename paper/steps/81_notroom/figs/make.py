import json, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import paper.figs  # noqa: F401,E402
D = Path(__file__).resolve().parent

fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.3),
                         gridspec_kw={"width_ratios": [1.1, 1], "wspace": 0.34})
# 왼쪽 — 잡음은 안 밀어낸다
ax = axes[0]
R = [("모바일 진짜 축 2개", -0.0205, -6.23, "#a33b3b"),
     ("잡음 8개 (모바일)", -0.0046, -1.59, "#8a9ab3"),
     ("잡음 4개 (모바일)", -0.0013, -0.49, "#8a9ab3"),
     ("잡음 2개 (게임)", -0.0027, -1.91, "#8a9ab3"),
     ("잡음 2개 (모바일)", +0.0003, 0.16, "#8a9ab3")]
y = np.arange(len(R))[::-1]
ax.barh(y, [r[1] for r in R], color=[r[3] for r in R], height=0.62)
ax.axvline(0, color="#333", lw=0.9)
for yy, r in zip(y, R):
    ax.text(r[1] - 0.0012, yy, f"$t{{=}}{r[2]:+.2f}$", fontsize=6.8,
            va="center", ha="right", color=r[3])
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in R], fontsize=7.2)
ax.set_xlim(-0.030, 0.004)
ax.set_xlabel("웹툰 $\\rho$ 변화")
ax.set_title("열을 더 넣어도 안 밀린다", fontsize=9.4, pad=6)

# 오른쪽 — 나무에서 깨진다
ax = axes[1]
B = [("F21\n능형", -0.0067, "#6f86b3"), ("F18\n나무", -0.0286, "#c08a3e"),
     ("F23\n판", -0.0205, "#a33b3b")]
x = np.arange(len(B))
ax.bar(x, [b[1] for b in B], color=[b[2] for b in B], width=0.5)
ax.axhline(0, color="#333", lw=0.9)
for xx, b in zip(x, B):
    ax.text(xx, b[1] - 0.0012, f"{b[1]:+.4f}", ha="center", va="top", fontsize=8.4)
ax.set_xticks(x); ax.set_xticklabels([b[0] for b in B], fontsize=8)
ax.set_ylabel("웹툰 $\\rho$ 변화"); ax.set_ylim(-0.036, 0.004)
ax.set_title("나무가 낸다", fontsize=9.4, pad=6)
fig.suptitle("웹툰이 내는 것은 자리가 좁아서가 아니다", fontsize=10, y=1.0)
fig.tight_layout(); fig.savefig(D / "noise.pdf"); plt.close(fig)

# 그림 2 — 규약 견주기
R2 = json.loads(Path("data/state/note259_rule.json").read_text())
K = ["가 태그 없음", "마 제일 센 것만 · 웹툰+애니", "나 통과 전부 · 웹툰+애니",
     "라 제일 센 것만 · 셋", "다 통과 전부 · 셋"]
fig, ax = plt.subplots(figsize=(7.0, 2.8))
x = np.arange(len(K))
v = [R2[k]["판"] for k in K]
cs = ["#8a8f98", "#c08a3e", "#2f6f4f", "#c08a3e", "#8a9ab3"]
ax.bar(x, [t - 0.45 for t in v], bottom=0.45, color=cs, width=0.55)
for xx, k in zip(x, K):
    ax.text(xx, R2[k]["판"] + 0.0007, f"{R2[k]['판']:.4f}\n({R2[k]['축']}축)",
            ha="center", fontsize=7.6)
ax.set_xticks(x)
ax.set_xticklabels([k.split(" ", 1)[1].replace(" · ", "\n") for k in K], fontsize=7.2)
ax.set_ylim(0.45, 0.4755); ax.set_ylabel("판 $\\rho$")
ax.set_title("``통과한 것을 다 쓴다''가 두 짝에서 다 이긴다", fontsize=10, pad=7)
fig.tight_layout(); fig.savefig(D / "rule.pdf"); plt.close(fig)
print("ok")
