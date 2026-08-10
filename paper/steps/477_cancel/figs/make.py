# -*- coding: utf-8 -*-
"""그림 1 — 판 Δ≈0 은 '아무 일 없음'이 아니라 **상쇄**다(노트 890)."""
import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager, rcParams
for c in ("AppleSDGothicNeo","Apple SD Gothic Neo","NanumGothic"):
    try: font_manager.findfont(c, fallback_to_default=False); rcParams["font.family"]=c; break
    except Exception: pass
rcParams["axes.unicode_minus"]=False

W={"웹툰":650,"애니":606,"펀딩":529,"모바일":441,"영화":406,"세계애니":300,
   "만화":258,"게임":180,"도서":163,"시장팝업":126,"팝업":65,"아이돌":51}
T=3775
d=json.load(open("/Users/ax/world_model/runners/out890_ruler.json"))
dom=d["도메인별 씨앗 짝"]
rows=sorted(((k,v["짝Δ 평균"],v["|Δ|/SE"],v["짝Δ 평균"]*W[k]/T) for k,v in dom.items()),
            key=lambda x:-x[3])
names=[r[0] for r in rows]; contrib=[r[3] for r in rows]; tstat=[r[2] for r in rows]

fig,ax=plt.subplots(1,2,figsize=(7.6,3.6))
# 왼쪽 — 판 기여(상쇄가 보이게)
y=range(len(names))
cols=["#2a6f6f" if c>0 else "#a33" for c in contrib]
ax[0].barh(list(y),contrib,color=cols)
ax[0].axvline(0,color="k",lw=.6)
ax[0].set_yticks(list(y)); ax[0].set_yticklabels(names,fontsize=8); ax[0].invert_yaxis()
ax[0].tick_params(axis="x",labelsize=7)
ax[0].set_title("판에 실린 몫 (도메인Δ × 가중)",fontsize=9)
pos=sum(c for c in contrib if c>0); neg=sum(c for c in contrib if c<0)
ax[0].text(0.98,0.03,"양수합 %+.5f\n음수합 %+.5f\n──────────\n순합 %+.5f"%(pos,neg,pos+neg),
           transform=ax[0].transAxes,ha="right",va="bottom",fontsize=7.5,family="monospace",
           bbox=dict(boxstyle="round,pad=0.35",fc="white",ec="#bbb",lw=.6))

# 오른쪽 — |Δ|/SE (안정성)
ax[1].barh(list(y),tstat,color=cols)
ax[1].axvline(2,color="#555",lw=.8,ls="--")
ax[1].text(2,-0.7," |Δ|/SE = 2",fontsize=7,color="#555",va="top")
ax[1].set_yticks(list(y)); ax[1].set_yticklabels([]); ax[1].invert_yaxis()
ax[1].tick_params(axis="x",labelsize=7)
ax[1].set_title("씨앗 안정성  |Δ|/SE  (짝 12씨앗)",fontsize=9)
ax[1].text(0.98,0.03,"12도메인 중 **10개**가 2 이상\n양의 방향 5 · 음의 방향 5",
           transform=ax[1].transAxes,ha="right",va="bottom",fontsize=7.5,
           bbox=dict(boxstyle="round,pad=0.35",fc="white",ec="#bbb",lw=.6))
for a in ax:
    for s in ("top","right"): a.spines[s].set_visible(False)
fig.suptitle("특기 칸 하나를 더 줬을 때 — 판은 0 을 냈고, 그 0 은 합이 아니라 상쇄였다",fontsize=10.5,y=1.0)
fig.tight_layout()
out=sys.argv[1] if len(sys.argv)>1 else "fig1.pdf"
fig.savefig(out,bbox_inches="tight"); print("저장",out)
