# -*- coding: utf-8 -*-
# 논문 212 figure — 손 수치 금지: runners/out878b_ledgeraudit.json 에서 계산해 그린다.
# (v1 정정 — 초판 png 는 시대 셀을 손으로 박아 산출물과 3셀 어긋났다 · 티처 #44 치명 1)
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).parent
o = json.load(open(HERE / "../../../runners/out878b_ledgeraudit.json"))
eras = o["시대 표"]
order = ["<863", "863-875", "876+"]
utc = [eras[e]["utc"] / eras[e]["n"] * 100 for e in order]
head = [eras[e]["head"] / eras[e]["n"] * 100 for e in order]
lab = [f"{e}\n(n={eras[e]['n']})" for e in order]

l1 = o["L1"]["경로 누락률"] * 100
l2 = o["L2"]["HEAD 결손률"] * 100

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.0, 2.9), gridspec_kw={"width_ratios": [1.15, 1]})
x = np.arange(3); w = 0.36
ax1.bar(x - w / 2, utc, w, label="UTC stamp", color="#4878a8")
ax1.bar(x + w / 2, head, w, label="git HEAD", color="#b0522e")
ax1.set_xticks(x); ax1.set_xticklabels(lab, fontsize=8)
ax1.set_ylabel("% of out*.json with field")
ax1.set_title("L2: self-description by era (computed)", fontsize=9)
ax1.legend(fontsize=7); ax1.set_ylim(0, 108)
for i in range(3):
    ax1.text(i - w / 2, utc[i] + 3, f"{utc[i]:.0f}", ha="center", fontsize=7)
    ax1.text(i + w / 2, head[i] + 3, f"{head[i]:.0f}", ha="center", fontsize=7)

ax2.barh(["cited paths\nmissing (L1)", "HEAD absent\n(L2)"], [l1, l2], color=["#4878a8", "#b0522e"])
ax2.axvspan(0, 10, alpha=0.12, color="#4878a8")
ax2.axvspan(40, 75, alpha=0.12, color="#b0522e")
ax2.set_xlabel("% (shaded = preregistered bands)")
ax2.set_title("predictions: one hit, one miss", fontsize=9)
ax2.text(l1 + 2, 0, f"{l1:.2f} (1/{o['L1']['고유 경로']})", va="center", fontsize=8)
ax2.text(l2 / 2, 1, f"{l2:.1f} (64/68)", va="center", ha="center", fontsize=8, color="white")
plt.tight_layout()
plt.savefig(HERE / "figs/ghostrx.png", dpi=150)
print("figure computed from out878b")
