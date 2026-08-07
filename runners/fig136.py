import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
plt.rcParams.update({"font.family":"Apple SD Gothic Neo","font.size":8.5,
                     "axes.spines.top":False,"axes.spines.right":False})
s=Path("/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad/cal691.out").read_text()
j=json.loads(s[s.find('{\n "판"'):])
dm=j["도메인별"]
fig=plt.figure(figsize=(11.2,4.1))
gs=fig.add_gridspec(1,3,width_ratios=[1.28,1.0,1.05],wspace=0.33)

# --- 왼쪽: 진짜 대 위약 (자 넷)
ax=fig.add_subplot(gs[0,0])
ds=sorted(dm, key=lambda d: -dm[d]["진짜"]["자릿수오차비율"])
x=np.arange(len(ds))
r=[dm[d]["진짜"]["자릿수오차비율"] for d in ds]
p=[dm[d]["위약"]["자릿수오차비율"] for d in ds]
ax.barh(x+0.19,r,0.36,color="#2b4c7e",label="진짜")
ax.barh(x-0.19,p,0.36,color="#c9ccd4",label="위약(값만 섞음)")
ax.set_yticks(x); ax.set_yticklabels(ds); ax.invert_yaxis()
ax.axvline(0.30,color="#b3392b",lw=1.1,ls="--")
ax.text(0.305,len(ds)-0.4,"T6 이 미리 못박은\n판정선 30%",color="#b3392b",fontsize=7.4,va="bottom")
ax.set_xlabel("자릿수 오차 비율  |예측-실제| > 1 자리")
ax.set_title("자릿수 오차 — 위약과 구분되지 않는다\n판 가중 진짜 0.4195 · 위약 0.4192",
             loc="left",fontsize=9,weight="bold")
ax.legend(frameon=False,fontsize=7.6,loc="lower right")

# --- 가운데: 이름과 실제
ax=fig.add_subplot(gs[0,1])
cov=[(d,dm[d]["진짜"]["구간덮음"]) for d in dm if dm[d]["진짜"].get("구간덮음") is not None]
cov.sort(key=lambda t:-t[1])
ax.barh(np.arange(len(cov)),[c for _,c in cov],0.6,
        color=["#2b4c7e" if c>=0.78 else "#d4a11a" if c>=0.6 else "#b3392b" for _,c in cov])
ax.set_yticks(np.arange(len(cov))); ax.set_yticklabels([d for d,_ in cov]); ax.invert_yaxis()
ax.axvline(0.80,color="#111",lw=1.3)
ax.text(0.805,len(cov)-0.35,"우리가 붙인 이름\n= 80%",fontsize=7.4,va="bottom")
ax.axvline(0.5016,color="#b3392b",lw=1.1,ls="--")
ax.text(0.505,-0.45,"실측 50.2%",color="#b3392b",fontsize=7.4)
ax.set_xlim(0,1); ax.set_xlabel("실제로 덮은 몫")
ax.set_title("'80% 구간' 이 실제로 덮는 것\n만화는 0.0000 이다",loc="left",fontsize=9,weight="bold")

# --- 오른쪽: 오늘 값 절단
ax=fig.add_subplot(gs[0,2])
arms=[("인기까지 넣음\n(배급 안 함)",0.9722,"#c9ccd4"),
      ("오늘 값 포함",0.9524,"#c9ccd4"),
      ("오늘 값 셋 뺌\n← 배급하는 팔",0.9408,"#2b4c7e"),
      ("화수·권수만",0.7966,"#c9ccd4"),
      ("시작연도만",0.5000,"#b3392b")]
y=np.arange(len(arms))
ax.barh(y,[a[1] for a in arms],0.62,color=[a[2] for a in arms])
for i,a in enumerate(arms):
    ax.text(a[1]+0.006,i,f"{a[1]:.4f}",va="center",fontsize=7.6)
ax.set_yticks(y); ax.set_yticklabels([a[0] for a in arms],fontsize=7.6); ax.invert_yaxis()
ax.axvline(0.5,color="#b3392b",lw=1.0,ls=":")
ax.set_xlim(0.45,1.03); ax.set_xlabel("선별 유보 AUC (양성 131 · 기저율 3.07%)")
ax.set_title("오늘 값을 버린 값 = 1.2%p\n시작연도만 = 0.5000 → 시간 누출 0",
             loc="left",fontsize=9,weight="bold")
fig.savefig("paper/steps/136_whatsells/figs/whatsells.pdf",bbox_inches="tight")
print("그림 저장")
