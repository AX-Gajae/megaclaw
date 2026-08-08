# -*- coding: utf-8 -*-
# 논문 473 figure — 손 수치 금지: out885_nation.json 에서 계산한다.
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).parent
o = json.load(open(HERE / "../../../runners/out885_nation.json"))
A = o["팔"]
base = A["① 없이(씨앗3)"]["값"]; base_s = A["① 없이(씨앗3)"]["씨앗별"]
real = A["② 진짜(씨앗3)"]["값"]; real_s = A["② 진짜(씨앗3)"]["씨앗별"]
val = A["③ 값셔플 6"]; row = A["④ 행셔플 3"]
two_sigma = o["자"]["그 도메인 2σ(837 정본 3,775 분모)"]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.4, 3.2), gridspec_kw={"width_ratios": [1.15, 1]})

ax1.scatter([0] * len(row), row, s=30, color="#c9a227", zorder=3, label="row-shuffle placebo x3")
ax1.scatter([1] * len(val), val, s=30, color="#9aa7b4", zorder=3, label="value-shuffle placebo x6")
ax1.scatter([2] * len(base_s), base_s, s=34, marker="s", color="#5b6b7a", zorder=3,
            label="no column (3 seeds)")
ax1.scatter([3] * len(real_s), real_s, s=90, marker="D", color="#2e7d32", zorder=4,
            label="with nationality (3 seeds)")
for x, arr in ((0, row), (1, val), (2, base_s), (3, real_s)):
    ax1.hlines(np.mean(arr), x - 0.22, x + 0.22, color="#333", lw=1.3)
ax1.set_xticks([0, 1, 2, 3])
ax1.set_xticklabels(["row-shuf", "value-shuf", "baseline", "real"], fontsize=8)
ax1.set_ylabel("film-domain spearman")
ax1.set_title(f"share {o['신호 몫(값셔플 분모)']:+.4f} = {o['신호 몫(값셔플 분모)']/two_sigma:.1f}x 2sigma",
              fontsize=9)
ax1.legend(fontsize=6.3, loc="lower right")

labels, vals, cols = [], [], []
for k, txt in (("⑤ 학습만 _cat(씨앗3)", "train-only\ncoding"), ("⑥ 원핫", "one-hot\n(no order)"),
               ("⑧ 파싱 정정 전(씨앗0)", "before junk\ncleanup")):
    if A.get(k):
        labels.append(txt); vals.append(A[k]["값"]); cols.append("#4878a8")
vp = A["⑦ vp"]
labels += ["distributor\naxis OFF", "  + nationality"]
vals += [vp["vp 끈 기준선"], vp["vp 끈 뒤+국적"]]
cols += ["#b0522e", "#b0522e"]
y = np.arange(len(labels))
ax2.barh(y, vals, color=cols)
ax2.axvline(real, color="#2e7d32", lw=1.4, ls="--")
ax2.text(real + 0.006, len(labels) - 0.4, f"real {real:.4f}", fontsize=7, color="#2e7d32")
ax2.axvline(base, color="#888", lw=1.0, ls=":")
ax2.set_yticks(y); ax2.set_yticklabels(labels, fontsize=7)
ax2.set_xlabel("film-domain spearman")
ax2.set_title(f"decomposition (distributor off: +{vp['vp 없을 때 이득']:.4f})", fontsize=9)
for i, v in enumerate(vals):
    ax2.text(v + 0.004, i, f"{v:.4f}", fontsize=7, va="center")
ax2.set_xlim(0, max(vals + [real]) * 1.22)
plt.tight_layout(); plt.savefig(HERE / "figs/hidden.png", dpi=150)
print("figure computed from artifacts")
