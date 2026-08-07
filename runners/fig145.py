import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
plt.rcParams.update({"font.family":"Apple SD Gothic Neo","font.size":8.5,
                     "axes.spines.top":False,"axes.spines.right":False,
                     "axes.unicode_minus":False})
EP=[60,200,600,1500]
REAL=[-0.1051,0.1154,-0.3630,-1.7679]
SD=[0.2735,0.0123,0.6717,2.1503]
PLAC=[-0.1951,-0.0054,-0.0110,-0.0462]
VAL=[-0.044,0.1999,-0.1776,-1.4999]
LOSS=[0.00504,0.0034,0.0029,0.0022]
SEED200=[0.1202,0.0971,0.1241,0.1202]
SEED60=[0.0791,-0.5041,-0.0613,0.0661]
fig=plt.figure(figsize=(11.6,4.2))
gs=fig.add_gridspec(1,3,width_ratios=[1.15,1.0,0.95],wspace=0.33)

# ── 1. 걸음별 유보 R² 와 씨앗 띠
ax=fig.add_subplot(gs[0,0])
x=np.arange(len(EP))
ax.fill_between(x,np.array(REAL)-np.array(SD),np.array(REAL)+np.array(SD),
                color="#2b4c7e",alpha=0.14,label="진짜 ±씨앗SD")
ax.plot(x,REAL,"-o",color="#2b4c7e",lw=2.0,ms=7,label="진짜 · 유보 R²")
ax.plot(x,VAL,"--s",color="#6d8ab8",lw=1.4,ms=5,label="진짜 · 학습구간 검증")
ax.plot(x,PLAC,"-^",color="#b3392b",lw=1.6,ms=6,label="위약 · 유보 R²")
ax.axhline(0,color="#111",lw=1.1)
ax.annotate("정점 200\n유보 +0.1154\n씨앗SD 0.0123",(1,0.1154),
            textcoords="offset points",xytext=(16,26),fontsize=7.8,weight="bold",
            arrowprops=dict(arrowstyle="->",lw=1.0,color="#111"))
ax.annotate("60 = 덜 배웠다\n씨앗SD 0.2735",(0,-0.1051),textcoords="offset points",
            xytext=(6,-34),fontsize=7.4,color="#555")
ax.annotate("600+ = 과적합\n(학습 손실은 계속 내려간다)",(2,-0.363),
            textcoords="offset points",xytext=(-4,-40),fontsize=7.4,color="#555")
ax.set_xticks(x); ax.set_xticklabels([str(e) for e in EP])
ax.set_ylim(-2.6,0.65)
ax.set_xlabel("전량배치 걸음 수")
ax.set_ylabel("R² (지속성 예측 대비)")
ax.legend(fontsize=7.0,loc="lower left",frameon=False)
ax.set_title("걸음 하나가 결론을 정했다\n0 보다 크면 어제를 베끼는 것보다 낫다",
             loc="left",fontsize=9,weight="bold")

# ── 2. 씨앗 넷: 60 대 200
ax=fig.add_subplot(gs[0,1])
for i,(v6,v2) in enumerate(zip(SEED60,SEED200)):
    ax.plot([0,1],[v6,v2],"-",color="#aab3c0",lw=1.0,zorder=1)
    ax.scatter([0],[v6],s=140,c="#b3392b",zorder=3,edgecolor="w",lw=1.2)
    ax.scatter([1],[v2],s=140,c="#2b4c7e",zorder=3,edgecolor="w",lw=1.2)
    ax.annotate(f"씨앗 {i}",(1,v2),textcoords="offset points",xytext=(12,0),
                va="center",fontsize=7.4)
ax.axhline(0,color="#111",lw=1.1)
ax.set_xlim(-0.35,1.7); ax.set_xticks([0,1])
ax.set_xticklabels(["걸음 60\n(노트 703 이 본 자리)","걸음 200"],fontsize=8)
ax.set_ylabel("유보 R²")
ax.text(-0.28,-0.44,"노트 703 은 씨앗 0 하나를 봤다\n(넷 중 가장 좋은 씨앗)",
        fontsize=7.4,color="#b3392b")
ax.set_title("덜 배운 자리에서는 초기값이 답을 정한다\n200 걸음에서 넷이 모인다(폭 0.027)",
             loc="left",fontsize=9,weight="bold")

# ── 3. 노트 703 의 두 결론 정정
ax=fig.add_subplot(gs[0,2])
rows=[("장이 배우나\n(진짜 - 위약)",0.1227,0.0438,"#2b4c7e"),
      ("공휴일 항이 돕나\n(있음 - 없음)",-0.0648,0.0518,"#b3392b")]
y=np.arange(len(rows))
ax.barh(y,[r[1] for r in rows],0.5,color=[r[3] for r in rows])
for i,r in enumerate(rows):
    ax.plot([r[2],r[2]],[i-0.28,i+0.28],color="#111",lw=1.8)
    ax.plot([-r[2],-r[2]],[i-0.28,i+0.28],color="#111",lw=1.8)
    ax.text(r[1]+(0.006 if r[1]>0 else -0.006),i,f"{r[1]:+.4f}",va="center",
            ha="left" if r[1]>0 else "right",fontsize=8.4,weight="bold")
ax.axvline(0,color="#111",lw=1.2)
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in rows],fontsize=8)
ax.invert_yaxis(); ax.set_xlim(-0.12,0.20)
ax.set_xlabel("짝지은 차 (검은 선 = 그 차의 2σ)")
ax.text(0.026,0.66,"노트 703 은 +0.024 로 적었다 --- 부호가 반대다.\n그런데 항을 빼면 안 된다 --- 그 이득이\n**달력을 다시 먹어서** 나온다(노트 690)".replace("**",""),
        fontsize=7.0,color="#b3392b")
ax.set_title("하나는 굳고 하나는 뒤집혔다\n배포 절차로 다시 잰 값(씨앗 4 · 짝지어 읽는다)",
             loc="left",fontsize=9,weight="bold")
fig.savefig("paper/steps/145_onestep/figs/onestep.pdf",bbox_inches="tight")
print("그림 저장")
