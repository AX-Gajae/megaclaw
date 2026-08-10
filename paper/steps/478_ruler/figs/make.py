# -*- coding: utf-8 -*-
"""그림 1 — 자를 바꾸면 같은 결론이 어디까지 움직이나(노트 891)."""
import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager, rcParams
for c in ("AppleSDGothicNeo","Apple SD Gothic Neo","NanumGothic"):
    try: font_manager.findfont(c, fallback_to_default=False); rcParams["font.family"]=c; break
    except Exception: pass
rcParams["axes.unicode_minus"]=False
d=json.load(open("/Users/ax/world_model/runners/out891_thresh.json"))
R=d["자 다섯"]; J=d["판정"]["🔴 36% 대 146% 결착"]

fig,ax=plt.subplots(1,2,figsize=(7.6,3.4))
# 왼쪽 — 자 다섯의 눈금
names=["R2 씨앗짝\n(890 예리)","R5 합성\n★정본","R1 씨앗수준\n(단일)","옛 상수","R3 행수준\n(비짝)"]
vals =[R["R2 씨앗 짝 평균 2σ(n=12 · 890 의 예리한 자)"], R["🔴 R5 합성 2σ = 채택 문턱"],
       R["R1 씨앗 수준 2σ(단일 측정)"], R["옛 상수"], R["R3 행 수준 비짝 2σ(12씨앗 앙상블)"]]
cols=["#999","#2a6f6f","#999","#a33","#999"]
b=ax[0].bar(range(5), vals, color=cols)
ax[0].set_yscale("log"); ax[0].set_xticks(range(5))
ax[0].set_xticklabels(names, fontsize=7.2)
ax[0].set_title("자 다섯의 눈금 (로그)", fontsize=9)
for i,v in enumerate(vals):
    ax[0].text(i, v*1.15, "%.5f"%v, ha="center", fontsize=6.8)
ax[0].tick_params(axis="y", labelsize=7)

# 오른쪽 — 자④ 상한이 요구치의 몇 %인가
labs=["옛 0.0045","R5 0.00353\n★정본","890 예리 0.0011"]
pct=[J["상한/요구(옛) %"], J["상한/요구(R5) %"], J["상한/요구(예리) %"]]
c2=["#a33","#2a6f6f","#c88"]
ax[1].bar(range(3), pct, color=c2)
ax[1].axhline(100, color="k", lw=.8, ls="--")
ax[1].text(2.45, 103, "100% = 넘는다", fontsize=7, ha="right")
ax[1].set_xticks(range(3)); ax[1].set_xticklabels(labs, fontsize=7.2)
ax[1].set_ylabel("자④ 상한 / 요구 아이돌 Δ  (%)", fontsize=8)
ax[1].set_title("같은 결론이 자에 따라 어디까지 움직이나", fontsize=9)
for i,v in enumerate(pct):
    ax[1].text(i, v+3, "%.1f%%"%v, ha="center", fontsize=7.5)
ax[1].tick_params(axis="y", labelsize=7)
for a in ax:
    for s in ("top","right"): a.spines[s].set_visible(False)
fig.suptitle("53노트 묵은 문턱을 널 팔 쌍으로 처음 쟀다 — 옛 자는 헐거웠고, 어제의 예리한 자는 자격이 없었다",
             fontsize=10, y=1.02)
fig.tight_layout()
out=sys.argv[1] if len(sys.argv)>1 else "fig1.pdf"
fig.savefig(out, bbox_inches="tight"); print("저장", out)
