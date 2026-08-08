# -*- coding: utf-8 -*-
# 논문 470 figure — 손 수치 금지: game_recent_utc.json 행과 out880 에서 계산해 그린다.
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).parent
ROOT = HERE / "../../.."
u = json.load(open(ROOT / "data/state/game_recent_utc.json"))
rel = np.sort([v["rel_diff"] for v in u["행"].values() if v.get("rel_diff") is not None])
o = json.load(open(ROOT / "runners/out880_numaudit11.json"))["864 p95 박제"]
lin, nr = o["p95 선형보간(864 원 정의)"], o["p95 최근접순위(wfail1 정의)"]

fig, ax = plt.subplots(figsize=(6.6, 3.0))
y = np.arange(1, len(rel) + 1) / len(rel)
ax.step(rel * 100, y, where="post", color="#4878a8", lw=1.5, label=f"ECDF of rel_diff (n={len(rel)})")
ax.axhline(0.95, color="#888", lw=0.7, ls=":")
ax.axvline(lin * 100, color="#2e7d32", lw=1.4, ls="--",
           label=f"p95 linear interp = {lin*100:.3f}% -> '1.6' (note 864)")
ax.axvline(nr * 100, color="#b0522e", lw=1.4, ls="--",
           label=f"p95 nearest rank = {nr*100:.1f}% -> '1.7' (wfail1)")
ax.set_xlim(0, max(rel) * 100 * 1.05)
ax.set_xlabel("relative diff UTC vs stored KST (%)")
ax.set_ylabel("cumulative fraction")
ax.set_title("same 228 rows, two p95 definitions, two restored numbers", fontsize=9)
ax.legend(fontsize=7, loc="lower right")
plt.tight_layout()
plt.savefig(HERE / "figs/p95gauge.png", dpi=150)
print("figure computed from artifacts")
