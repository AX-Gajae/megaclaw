# -*- coding: utf-8 -*-
"""노트 968 figure — **통제라 부른 열의 절반은 채움값이었다**.

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
R = json.loads((ROOT / "runners/out968_audit.json").read_text(encoding="utf-8"))
B = R["🔴🔴 §B wiki_level 감사(P1·P2)"]["도메인별"]
C = R["🔴🔴 §C level 을 빼면 변하나(P3)"]["도메인별"]

fig, (ax, ax2) = plt.subplots(1, 2, figsize=(FULL, 2.5),
                              gridspec_kw={"width_ratios": [1.15, 1]})

# ── 왼쪽: 도메인별 wiki_level 의 「마스크가 선 행」 ─────────────────────
doms = sorted(B, key=lambda d: -B[d].get("🔴🔴 마스크가 선 행(M > 0)", 0))
seen = [B[d].get("🔴🔴 마스크가 선 행(M > 0)", 0) for d in doms]
tot = [B[d].get("n(판 전량)", 0) for d in doms]
y = np.arange(len(doms))
ax.barh(y, tot, color="0.86", height=0.62, label="판의 행")
ax.barh(y, seen, color=INK, height=0.62, label="wiki_level 을 실제로 잰 행")
for i, (s, t) in enumerate(zip(seen, tot)):
    if s == 0:
        ax.text(t * 0.02 + 30, i, "0 행 — 값 0.5 는 **채움값**", va="center",
                fontsize=6.4, color=CLAIM)
ax.set_yticks(y)
ax.set_yticklabels(doms, fontsize=7)
ax.invert_yaxis()
ax.set_xlabel("행 수", fontsize=7.5)
ax.set_title("판 12 도메인 중 **7** 에서 `wiki_level` 은\n한 행도 안 쟀다",
             fontsize=8.2, loc="left")
ax.legend(fontsize=6.4, loc="lower right", frameon=False)
ax.tick_params(labelsize=6.6)

# ── 오른쪽: level 을 빼면 값이 얼마나 움직이나 ─────────────────────────
dd = sorted(C, key=lambda d: abs(C[d]["🔴 Δ"]))
delta = np.array([abs(C[d]["🔴 Δ"]) for d in dd])
card = np.array([C[d]["wiki_level 가짓수"] for d in dd])
col = [CLAIM if c <= 1 else GATE for c in card]
yy = np.arange(len(dd))
ax2.barh(yy, np.maximum(delta, 1e-18), color=col, height=0.62)
ax2.set_xscale("log")
ax2.set_xlim(1e-18, 1e-1)
ax2.set_yticks(yy)
ax2.set_yticklabels(["%s (가짓수 %d)" % (d, c) for d, c in zip(dd, card)], fontsize=6.4)
ax2.set_xlabel(r"$|\Delta\rho|$   ($\rho$ 에서 wiki_level 을 뺐을 때)", fontsize=7.5)
ax2.set_title("가짓수 1 이면 $10^{-17}$, 아니면 $10^{-3}$\n**14 자릿수로 갈라진다**",
              fontsize=8.2, loc="left")
ax2.axvline(1e-9, color="0.5", lw=0.8, ls=":")
ax2.tick_params(labelsize=6.4)

fig.tight_layout()
fig.savefig(HERE / "deadcontrol.pdf", bbox_inches="tight")
print("wrote", HERE / "deadcontrol.pdf")
