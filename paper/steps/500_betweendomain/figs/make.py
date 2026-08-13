# -*- coding: utf-8 -*-
"""500 그림 — 🔴 값을 손으로 안 적는다. 전부 `runners/out957_layers.json` 에서 읽는다."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager, rcParams

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))

for cand in ("Nanum Gothic", "Nanum Myeongjo", "AppleGothic", "Apple SD Gothic Neo"):
    if any(f.name == cand for f in font_manager.fontManager.ttflist):
        rcParams["font.family"] = cand
        break
rcParams["axes.unicode_minus"] = False
rcParams["figure.dpi"] = 200
rcParams["font.size"] = 7.2
rcParams["savefig.bbox"] = "tight"
rcParams["axes.spines.top"] = False
rcParams["axes.spines.right"] = False
INK, GATE, CLAIM = "#1a1a1a", "#2166ac", "#b2182b"

d = json.load(open(os.path.join(ROOT, "runners/out957_layers.json")))
M = d["§6 측정 · 주 표적 y_들림"]
B3 = M["B-③ 무관 배경"]
A2 = M["A-② 물리 장"]
dom = {k: v for k, v in d["곁 · 도메인별 Δρ(③) (판정 아님)"].items() if isinstance(v, dict) and "Δρ" in v}
dd = d["🔴 사후 · 도메인 지시자를 넣고 다시"]
inner = d["🔴 사후 · 합산 이득이 도메인 사이의 것인가"]["🔴 도메인 안 평균 Δρ"]

fig, ax = plt.subplots(1, 3, figsize=(6.75, 2.25),
                       gridspec_kw={"width_ratios": [2.0, 1.0, 1.0]})

# ── 왼쪽: 도메인별 Δρ ± 2SE 와 합산 ────────────────────────────────────────
ks = sorted(dom, key=lambda k: -dom[k]["쌍"])
y = np.arange(len(ks))
v = np.array([dom[k]["Δρ"] for k in ks])
e = np.array([2 * dom[k]["SE"] for k in ks])
ax[0].errorbar(v, y, xerr=e, fmt="o", ms=3.2, lw=1.0, color=GATE, capsize=2)
ax[0].axvline(0, color=INK, lw=0.7)
ax[0].errorbar([B3["🔴 Δρ"]], [len(ks) + 0.6],
               xerr=[2 * B3["SE_boot(Δρ)"]], fmt="s", ms=4.2, lw=1.4,
               color=CLAIM, capsize=2)
ax[0].axhline(len(ks) - 0.3, color=INK, lw=0.5, ls=":")
ax[0].set_yticks(list(y) + [len(ks) + 0.6])
ax[0].set_yticklabels([f"{k} ({dom[k]['쌍']})" for k in ks]
                      + [f"합산 ({B3['분모: 쌍']})"])
ax[0].set_xlabel("Δρ(층 ③ 을 더했을 때) · 가로선은 ±2·SE")
ax[0].set_title("도메인 안에서는 아무 데도 안 든다", fontsize=7.6)
ax[0].text(inner, -1.0, f"도메인 안 평균 {inner:+.5f}", color=INK, fontsize=6.4,
           ha="center", va="center")

# ── 가운데: 도메인 지시자를 넣으면 ③ 이 죽는다 ───────────────────────────
lbl = ["① → +③", "①+도메인 → +③"]
val = [B3["🔴 Δρ"], dd["①+도메인 → +③"]["Δρ"]]
err = [2 * B3["SE_boot(Δρ)"], 2 * dd["①+도메인 → +③"]["SE"]]
ax[1].bar([0, 1], val, yerr=err, color=[CLAIM, GATE], width=0.55, capsize=3)
ax[1].axhline(0, color=INK, lw=0.7)
ax[1].set_xticks([0, 1])
ax[1].set_xticklabels(lbl, fontsize=6.6)
ax[1].set_ylabel("Δρ")
ax[1].set_title("도메인을 알면 ③ 은 해롭다", fontsize=7.6)

# ── 오른쪽: 문턱 셋 ──────────────────────────────────────────────────────
T = "🔴 문턱 T = max(0.00353, 2·SE)"
names = ["판 문턱\n0.00353", "팔 B\n(464쌍)", "팔 A\n(39쌍)"]
vals = [0.00353, B3[T], A2[T]]
ax[2].bar(range(3), vals, color=[INK, GATE, CLAIM], width=0.55)
ax[2].set_yscale("log")
ax[2].set_yticks([0.001, 0.01, 0.1])
ax[2].set_yticklabels(["0.001", "0.01", "0.1"])
ax[2].set_xticks(range(3))
ax[2].set_xticklabels(names, fontsize=6.4)
ax[2].set_ylabel("가를 수 있는 최소 효과")
ax[2].set_title("빌려온 문턱은 80배 작다", fontsize=7.6)
for i, x in enumerate(vals):
    ax[2].text(i, x * 1.15, f"{x:.4f}", ha="center", fontsize=6.2)

fig.tight_layout()
fig.savefig(os.path.join(HERE, "lay.pdf"))
print("lay.pdf")
