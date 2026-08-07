import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
plt.rcParams.update({"font.family":"Apple SD Gothic Neo","font.size":8.5,
                     "axes.spines.top":False,"axes.spines.right":False})
fig=plt.figure(figsize=(11.4,4.0))
gs=fig.add_gridspec(1,3,width_ratios=[1.15,1.0,1.05],wspace=0.34)

pairs=["비게임 앱","CN 만화","KR 만화"]
old=[0.2169,0.0166,0.0148]          # 노트 704 --- load(base())
new=[0.1094,0.0271,0.0092]          # 노트 707/709 --- champion_data()
thr=[0.024,0.022,0.025]
b_old=[0.0848,0.3742,0.6303]
b_rec=[0.4968,0.3874,0.6831]

# ── 1. 신호 몫: 두 판
ax=fig.add_subplot(gs[0,0])
y=np.arange(len(pairs))
ax.barh(y+0.20,old,0.36,color="#c9ccd4",label="노트 704 — 잘못 지은 판")
ax.barh(y-0.20,new,0.36,color=["#2b4c7e","#2b4c7e","#b3392b"],
        label="노트 707·709 — 챔피언 판")
for i,(o,n,t) in enumerate(zip(old,new,thr)):
    ax.plot([t,t],[i-0.42,i+0.42],color="#111",lw=1.6)
    ax.text(n+0.004,i-0.20,f"{n:.4f}",va="center",fontsize=7.6,weight="bold")
    ax.text(o+0.004,i+0.20,f"{o:.4f}",va="center",fontsize=7.4,color="#555")
ax.text(thr[0]+0.006,-0.62,"검은 선 = 문턱",fontsize=7.4)
ax.set_yticks(y); ax.set_yticklabels(pairs); ax.invert_yaxis()
ax.set_xlabel("신호 몫 (진짜 − 위약) · 클수록 좋음")
ax.set_xlim(0,0.245)
ax.legend(frameon=False,fontsize=7.4,loc="lower right")
ax.set_title("배선 하나로 판정이 세 번 뒤집혔다\n앱 무효→유효 · CN 미달→통과 · KR 미달→더 미달",
             loc="left",fontsize=9,weight="bold")

# ── 2. 기준선 재현
ax=fig.add_subplot(gs[0,1])
x=np.arange(len(pairs))
ax.bar(x-0.2,b_old,0.38,color="#c9ccd4",label="잘못 지은 판")
ax.bar(x+0.2,b_rec,0.38,color="#2b4c7e",label="챔피언 판 = 기록")
for i,(a,b) in enumerate(zip(b_old,b_rec)):
    ax.text(i-0.2,a+0.012,f"{a:.4f}",ha="center",fontsize=7.4,color="#555")
    ax.text(i+0.2,b+0.012,f"{b:.4f}",ha="center",fontsize=7.6,weight="bold")
ax.annotate("−0.412",xy=(0.2,0.50),xytext=(0.05,0.66),fontsize=8.4,
            color="#b3392b",weight="bold",
            arrowprops=dict(arrowstyle="->",color="#b3392b",lw=1.0))
ax.set_xticks(x); ax.set_xticklabels(pairs,fontsize=8)
ax.set_ylabel("'없이' 팔 rho"); ax.set_ylim(0,0.78)
ax.legend(frameon=False,fontsize=7.4,loc="upper left")
ax.set_title("챔피언 판에서 차가 정확히 0.0000\n세 짝 다 노트 696 기록을 재현",
             loc="left",fontsize=9,weight="bold")

# ── 3. 죽은 가설 둘
ax=fig.add_subplot(gs[0,2])
sd=[0.158,0.109,0.0967]; ov=[0.98,1.00,1.00]
col=["#2b4c7e","#2b4c7e","#b3392b"]
ax.scatter(sd,ov,s=190,c=col,zorder=3,edgecolor="w",lw=1.4)
for s_,o_,p_ in zip(sd,ov,pairs):
    ax.annotate(p_,(s_,o_),textcoords="offset points",xytext=(0,-19),
                ha="center",fontsize=8)
ax.axvline(0.13,color="#b3392b",lw=1.0,ls="--")
ax.text(0.131,0.9915,"예측 SD 로\n가르려 했다",fontsize=7.2,color="#b3392b",va="bottom")
ax.annotate("차 0.012 인데\n판정이 갈린다",xy=(0.103,1.0),xytext=(0.055,0.9935),
            fontsize=7.4,arrowprops=dict(arrowstyle="->",color="#111",lw=0.9))
ax.set_xlabel("텍스트 예보의 SD"); ax.set_ylabel("어휘가 닿은 제목 몫")
ax.set_xlim(0.08,0.175); ax.set_ylim(0.988,1.004)
ax.set_title("가설 둘이 죽었다\n남색=통과 · 붉은색=미달",loc="left",fontsize=9,weight="bold")
fig.savefig("paper/steps/138_baseline/figs/baseline.pdf",bbox_inches="tight")
print("그림 저장")
