# -*- coding: utf-8 -*-
"""노트 967 figure — **규격 사다리가 간판 하나를 지운다**.

🔴 자료를 저장소 산출물에서 **직접 읽는다**(하드코딩 금지 — `paper/figs.py` 규약).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, "/Users/ax/world_model")
import numpy as np                                            # noqa: E402
from paper.figs import plt, FULL, INK, GATE, CLAIM            # noqa: E402

ROOT = Path("/Users/ax/world_model")
HERE = Path(__file__).resolve().parent
R = json.loads((ROOT / "runners/out967_narrow.json").read_text(encoding="utf-8"))
L = R["§B·D 규격 사다리(P2·P4·P5·P6)"]
SPECS = ["A", "B", "C", "D"]
LABEL = {"A": "A\n966 그대로", "B": "B\n+동률평균",
         "C": "C\n+최근항 통제", "D": "D\n+두 띠 실자료"}

# 규격 A 에서 잰 도메인 전부를 나른다(사후 선택 없음).
doms = sorted(d for d, v in L["A"]["도메인별"].items() if v.get("🔴 잰다"))
HIGH = {"아이돌": CLAIM, "만화": GATE}

fig, (ax, ax2) = plt.subplots(1, 2, figsize=(FULL, 2.35),
                              gridspec_kw={"width_ratios": [1.35, 1]})

x = np.arange(len(SPECS))
for d in doms:
    ys = [L[s]["도메인별"][d].get("🔴 ρ(부분)") for s in SPECS]
    if any(v is None for v in ys):
        continue
    hi = d in HIGH
    ax.plot(x, ys, "-o", ms=3.2, lw=1.6 if hi else 0.8,
            color=HIGH.get(d, "#c8c8c8"), zorder=4 if hi else 2,
            label=d if hi else None)
    if hi:
        ax.annotate(d, (x[-1], ys[-1]), xytext=(3, 0), textcoords="offset points",
                    fontsize=7, color=HIGH[d], va="center")
ax.axhline(0, color=INK, lw=0.6, zorder=1)
ax.set_xticks(x)
ax.set_xticklabels([LABEL[s] for s in SPECS], fontsize=6.4)
ax.set_ylabel("부분 순위상관 ρ", fontsize=7.5)
ax.tick_params(labelsize=7)
ax.set_title("규격을 조일수록 간판이 지워진다", fontsize=8.2)

# 오른쪽 — 규격 D 에서 Holm 을 통과한 것과 아닌 것
D = L["D"]
live = [(d, v) for d, v in D["도메인별"].items() if v.get("🔴 잰다")]
live.sort(key=lambda kv: kv[1]["🔴 ρ(부분)"])
names = [d for d, _ in live]
rho = np.array([v["🔴 ρ(부분)"] for _, v in live])
passed = np.array([D["🔴 Holm"]["도메인별"][d]["통과"] for d, _ in live])
y = np.arange(len(names))
ax2.axvline(0, color=INK, lw=0.6, zorder=1)
ax2.scatter(rho[~passed], y[~passed], s=30, facecolor="white",
            edgecolor="#9a9a9a", lw=1.0, zorder=3)
ax2.scatter(rho[passed], y[passed], s=34, color=CLAIM, zorder=4)
for i, (d, v) in enumerate(live):
    ax2.annotate("n=%d" % v["n"], (rho[i], i), xytext=(4, -7),
                 textcoords="offset points", fontsize=5.8, color="#7a7a7a")
ax2.set_yticks(y)
ax2.set_yticklabels(names, fontsize=6.6)
ax2.tick_params(labelsize=7)
ax2.set_xlabel("규격 D 의 ρ (속 채운 것 = Holm α=.05 통과)", fontsize=7)
ax2.set_title("좁힌 뒤 남은 셋 — 전부 양수", fontsize=8.2)

fig.tight_layout(pad=0.35)
fig.savefig(HERE / "ladder.pdf")
print("썼다:", HERE / "ladder.pdf")
