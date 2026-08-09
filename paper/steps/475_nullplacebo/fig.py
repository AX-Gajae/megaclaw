# -*- coding: utf-8 -*-
# 논문 475 figure — 손 수치 금지: out887b_ruler.json 에서 계산한다.
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).parent
R = Path("/Users/ax/world_model")
o = json.load(open(R / "runners/out887b_ruler.json"))
arms = o["팔"]
ruler = o["자(837 미결 ① — 여기서 처음 잰다)"]

pl = [v["도메인 Δ"]["점추정"] for k, v in arms.items() if k.startswith("③")]
ver = arms["② versions"]["도메인 Δ"]
unit = arms["② unit_price"]["도메인 Δ"]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.4, 3.1),
                               gridspec_kw={"width_ratios": [1, 1.15]})

# 왼쪽: 위약 여섯이 정확히 0 · 후보 둘
ax1.axhline(0, color="#999", lw=0.8, zorder=1)
ax1.scatter([0] * len(pl), pl, s=70, color="#b03a2e", zorder=3,
            label=f"placebo x{len(pl)} (all exactly 0)")
ax1.errorbar([1], [ver["점추정"]],
             yerr=[[ver["점추정"] - ver["lo(2.5%)"]], [ver["hi(97.5%)"] - ver["점추정"]]],
             fmt="D", ms=8, color="#2e7d32", capsize=5, zorder=3, label="versions (95% CI)")
ax1.scatter([2], [unit["점추정"]], s=70, marker="s", color="#5b6b7a", zorder=3,
            label="unit_price (exactly 0)")
ax1.set_xticks([0, 1, 2])
ax1.set_xticklabels(["placebo", "versions", "unit_price"], fontsize=8)
ax1.set_ylabel("idol-domain delta rho")
ax1.set_title(f"placebo spread SD = {ruler['위약 도메인 Δ 뽑기 SD']:.5f}", fontsize=9)
ax1.legend(fontsize=6.4, loc="upper left")

# 오른쪽: 도메인별 '요구 델타' --- 판 문턱이 얇은 도메인을 배제한다
req = {"webtoon": 0.0261, "anime": 0.0280, "funding": 0.0321, "mobile": 0.0385,
       "film": 0.0418, "w-anime": 0.0566, "manga": 0.0658, "game": 0.0944,
       "book": 0.1042, "mkt-popup": 0.1348, "popup": 0.2613, "idol": 0.3331}
ks = list(req)[::-1]
vs = [req[k] for k in ks]
cols = ["#b03a2e" if req[k] > 0.09 else "#5b6b7a" for k in ks]
ax2.barh(range(len(ks)), vs, color=cols)
ax2.set_yticks(range(len(ks)))
ax2.set_yticklabels(ks, fontsize=7)
ax2.axvline(0.0577, color="#2e7d32", ls="--", lw=1.4)
ax2.text(0.0600, 0.4, "largest 1-col effect\nmeasured (0.0577)", fontsize=6.4, color="#2e7d32")
ax2.set_xlabel("domain delta needed to clear board threshold 0.0045", fontsize=7.5)
ax2.set_title("the board threshold excludes thin domains", fontsize=9)

fig.tight_layout()
(HERE / "figs").mkdir(exist_ok=True)
fig.savefig(HERE / "figs/nullplacebo.png", dpi=200)
print(json.dumps({"위약 점추정": pl, "위약 SD": ruler["위약 도메인 Δ 뽑기 SD"],
                  "versions": ver, "unit_price 점추정": unit["점추정"],
                  "아이돌 요구": ruler["요구 도메인 Δ(= 옛 문턱/가중)"]}, ensure_ascii=False))
