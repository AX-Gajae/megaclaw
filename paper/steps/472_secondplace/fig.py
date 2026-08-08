# -*- coding: utf-8 -*-
# 논문 472 figure — 손 수치 금지: out884_newcol.json 에서 계산한다.
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).parent
o = json.load(open(HERE / "../../../runners/out884_newcol.json"))["결과"]
KEYS = [("mob_ndevice", "mobile n_device\n(rule's 1st pick)"),
        ("film_nation", "film nationality\n(rule's 2nd - not adjudicable)")]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 3.1), gridspec_kw={"width_ratios": [1.25, 1]})

for i, (k, lab) in enumerate(KEYS):
    r = o[k]
    x = i * 1.6
    pv = r["위약 6"]
    ax1.scatter([x - 0.18] * len(pv), pv, s=26, color="#9aa7b4", zorder=3,
                label="placebo x6" if i == 0 else None)
    ax1.hlines(r["위약 평균"], x - 0.34, x - 0.02, color="#5b6b7a", lw=1.6,
               label="placebo mean" if i == 0 else None)
    ax1.hlines(r["없이(그 도메인)"], x - 0.34, x + 0.34, color="#bbb", lw=1.0, ls=":",
               label="baseline (no column)" if i == 0 else None)
    ax1.scatter([x + 0.20], [r["진짜(그 도메인)"]], s=90, marker="D",
                color="#2e7d32" if r["신호 몫"] > 0 else "#b0522e", zorder=4,
                label="real" if i == 0 else None)
    ax1.annotate(f"share {r['신호 몫']:+.4f}\n= {r['신호 몫']/r['그 도메인 2σ']:.1f}x 2σ",
                 (x + 0.24, r["진짜(그 도메인)"]), fontsize=7.5, va="center")
ax1.set_xticks([0, 1.6]); ax1.set_xticklabels([l for _k, l in KEYS], fontsize=7.5)
ax1.set_ylabel("domain spearman")
ax1.set_title("the rule picked the dead one", fontsize=9)
ax1.legend(fontsize=6.5, loc="lower left")

ax2.axis("off"); ax2.set_title("what the board did", fontsize=9)
rows = [("board without column", f"{o['film_nation']['판 없이']:.4f}"),
        ("board + mobile n_device", f"{o['mob_ndevice']['판 진짜']:.4f}  (+0.0000)"),
        ("board + film nationality", f"{o['film_nation']['판 진짜']:.4f}  ({o['film_nation']['판 변화']:+.4f})"),
        ("board adoption threshold", "0.0045"),
        ("verdict on the 2nd pick", "NOT adjudicable")]
for i, (k, v) in enumerate(rows):
    y = 0.84 - i * 0.17
    ax2.text(0.02, y, k, fontsize=8, va="center")
    ax2.text(0.98, y, v, fontsize=8.5, va="center", ha="right", weight="bold",
             color="#b0522e" if i == len(rows) - 1 else "#2e7d32" if i == 2 else "#333")
    ax2.plot([0.02, 0.98], [y - 0.07, y - 0.07], lw=0.4, color="#ddd")
plt.tight_layout(); plt.savefig(HERE / "figs/secondplace.png", dpi=150)
print("figure computed from artifacts")
