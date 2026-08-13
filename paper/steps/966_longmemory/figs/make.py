# -*- coding: utf-8 -*-
"""노트 966 figure — **90일 밖의 기억**.

🔴 자료를 저장소 산출물에서 **직접 읽는다**(하드코딩 금지 — `paper/figs.py` 규약).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, "/Users/ax/world_model")
import numpy as np
from paper.figs import plt, COL, FULL, INK, GATE, CLAIM   # noqa: E402

ROOT = Path("/Users/ax/world_model")
HERE = Path(__file__).resolve().parent
R = json.loads((ROOT / "runners/out966_longmem.json").read_text(encoding="utf-8"))
P = R["§4 명제"]["도메인별"]

live = [(d, v) for d, v in P.items() if v.get("🔴 잰다")]
live.sort(key=lambda kv: kv[1]["🔴 들뜸 ↔ 결과(수준을 뺀 뒤)"])
names = [d for d, _ in live]
par = np.array([v["🔴 들뜸 ↔ 결과(수준을 뺀 뒤)"] for _, v in live])
flr = np.array([v["순열 바닥 |ρ| 95%"] for _, v in live])
lvl = np.array([v["곁: 수준 ↔ 결과"] for _, v in live])
ns = [v["n"] for _, v in live]
over = np.array([v["🔴 바닥을 넘었나"] for _, v in live])

fig, ax = plt.subplots(figsize=(FULL, 2.45))
y = np.arange(len(names))

# 순열 바닥 --- ±95% 띠. 이 띠 밖이 「바닥을 넘었다」다.
for i, f in enumerate(flr):
    ax.plot([-f, f], [i, i], lw=5.5, color="#d9d9d9",
            solid_capstyle="butt", zorder=1)

ax.axvline(0, color=INK, lw=0.6, zorder=2)
# 곁 자 --- 판이 이미 보는 90일 「수준」
ax.scatter(lvl, y, s=17, marker="D", facecolor="none",
           edgecolor=GATE, lw=0.9, zorder=3, label="수준 ↔ 결과 (판이 이미 보는 90일)")
# 주장 --- 「들뜸」, 수준을 뺀 뒤
ax.scatter(par[~over], y[~over], s=34, marker="o", facecolor="white",
           edgecolor=CLAIM, lw=1.1, zorder=4)
ax.scatter(par[over], y[over], s=34, marker="o", color=CLAIM, zorder=5,
           label="들뜸 ↔ 결과, 수준을 뺀 뒤 (속 채운 것 = 순열 바닥 밖)")

ax.set_yticks(y)
ax.set_yticklabels(["%s  (n=%d)" % (d, n) for d, n in zip(names, ns)])
ax.set_xlabel("도메인 안 순위 상관 ρ")
ax.set_xlim(-0.42, 0.55)
ax.legend(loc="lower right", frameon=False, fontsize=6.4)
ax.set_title("회색 띠 = 라벨 순열 1,000회의 |ρ| 95% 바닥", fontsize=7.0,
             color="#555555", loc="left", pad=4)
fig.savefig(HERE / "domains.pdf")
print("wrote", HERE / "domains.pdf")

# ── 둘째 그림: 두 자의 분모가 다르다 ────────────────────────────────────
B = R.get("§3 판")
if B:
    fig2, ax2 = plt.subplots(figsize=(COL, 1.9))
    d = B["🔴 Δρ"]
    t = B["🔴 문턱(열 1개 증가)"]
    ax2.bar([0], [d], width=0.5, color=(CLAIM if d >= t else "#9e9e9e"))
    ax2.axhline(t, color=INK, lw=0.8, ls="--")
    ax2.text(0.34, t, " 문턱 %.5f\n (열 1개 증가)" % t, va="center",
             fontsize=6.3, color=INK)
    ax2.axhline(0, color=INK, lw=0.6)
    ax2.set_xticks([])
    ax2.set_ylabel("판 ρ 의 변화")
    ax2.set_title("부착 유보 %d / 3,775 (%.2f%%)"
                  % (R["§2 배선"]["검사"]["W2 유보 부착"]["🔴 분자: 부착 유보 행"],
                     R["§2 배선"]["검사"]["W2 유보 부착"]["부착률(%)"]),
                  fontsize=7.0, color="#555555", loc="left", pad=4)
    ax2.set_ylim(min(-0.001, d * 1.4), max(t * 1.35, d * 1.4))
    fig2.savefig(HERE / "board.pdf")
    print("wrote", HERE / "board.pdf")
