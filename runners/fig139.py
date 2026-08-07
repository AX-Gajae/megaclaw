import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
plt.rcParams.update({"font.family":"Apple SD Gothic Neo","font.size":8.5,
                     "axes.spines.top":False,"axes.spines.right":False})
fig=plt.figure(figsize=(11.4,4.0))
gs=fig.add_gridspec(1,3,width_ratios=[1.2,1.0,1.0],wspace=0.33)

pairs=["비게임 앱","KR 만화","CN 만화"]
rows=[1600,1716,352]
sd=[0.0154,0.0040,0.0120]        # 참값 0 차 SD
thr=[0.024,0.025,0.022]          # 기록된 문턱
sig=[0.0839,0.0092,0.0053]       # 실제 신호 몫
fp=[0.278,0.000,0.083]           # 씨앗 단위 오탐률

# ── 1. 참값 0 분포와 문턱
ax=fig.add_subplot(gs[0,0])
y=np.arange(len(pairs))
for i,(s,t,r) in enumerate(zip(sd,thr,rows)):
    ax.barh(i,2*s,0.42,left=-s,color="#c9ccd4")          # ±1σ 띠
    ax.plot([-2*s,2*s],[i,i],color="#8a94a0",lw=1.0)     # ±2σ
    ax.plot([t,t],[i-0.30,i+0.30],color="#b3392b",lw=2.0)
    ax.plot([-t,-t],[i-0.30,i+0.30],color="#b3392b",lw=2.0)
    ax.text(t+0.0012,i,f"문턱 {t:.3f}\n= {t/s:.1f}σ",fontsize=7.4,
            va="center",color="#b3392b",weight="bold")
    ax.text(-0.036,i+0.28,f"{r:,}행",fontsize=7.0,color="#555")
ax.axvline(0,color="#111",lw=0.9)
ax.set_yticks(y); ax.set_yticklabels(pairs); ax.invert_yaxis()
ax.set_xlim(-0.038,0.040); ax.set_xlabel("참값 0 인 차 (위약 대 위약)")
ax.set_title("같은 '2σ' 라고 적힌 문턱이 1.6σ~6.2σ다\n회색 = ±1σ · 가는 선 = ±2σ · 붉은 선 = 기록된 문턱",
             loc="left",fontsize=9,weight="bold")

# ── 2. σ 단위로 본 신호
ax=fig.add_subplot(gs[0,1])
z=[s/d for s,d in zip(sig,sd)]
col=["#2b4c7e" if v>2 else "#b3392b" for v in z]
ax.barh(y,z,0.55,color=col)
for i,(v,s,d) in enumerate(zip(z,sig,sd)):
    ax.text(v+0.11,i,f"{v:.1f}σ",va="center",fontsize=8.4,weight="bold")
    ax.text(0.1,i-0.30,f"{s:+.4f} / SD {d:.4f}",fontsize=7.0,color="#fff" if v>1.5 else "#555")
ax.axvline(2,color="#111",lw=1.4,ls="--")
ax.text(2.08,-0.55,"2σ",fontsize=8,weight="bold")
ax.set_yticks(y); ax.set_yticklabels(pairs); ax.invert_yaxis()
ax.set_xlim(0,6.2); ax.set_xlabel("신호 몫 ÷ 참값 0 차 SD")
ax.set_title("이 자로 읽으면 판정이 하나 뒤집힌다\nKR 은 옛 문턱에서 미달인데 2.3σ다",
             loc="left",fontsize=9,weight="bold")

# ── 3. '집 밖 ≥k' 의 우연 확률
ax=fig.add_subplot(gs[0,2])
k=[1,2,3]
assumed=[0.1426,0.0073,0.000125]
measured=[0.3379,0.0231,0.0000]
x=np.arange(3)
ax.bar(x-0.2,assumed,0.38,color="#c9ccd4",label="문턱이 5% 라 가정")
ax.bar(x+0.2,measured,0.38,color="#b3392b",label="실측 오탐률로")
for i,(a,m) in enumerate(zip(assumed,measured)):
    ax.text(i-0.2,a+0.008,f"{a:.1%}",ha="center",fontsize=7.2,color="#555")
    ax.text(i+0.2,m+0.008,f"{m:.1%}",ha="center",fontsize=7.6,weight="bold")
ax.axhline(0.05,color="#111",lw=1.0,ls=":")
ax.text(2.35,0.058,"5%",fontsize=7.4,ha="right")
ax.set_xticks(x); ax.set_xticklabels([f"집 밖 ≥{i}" for i in k])
ax.set_ylabel("우연히 넘을 확률"); ax.set_ylim(0,0.40)
ax.legend(frameon=False,fontsize=7.4,loc="upper right")
ax.set_title("'하나만 통과' 는 세 번에 한 번 우연이다\n그래서 규칙이 ≥2 여야 한다",
             loc="left",fontsize=9,weight="bold")
fig.savefig("paper/steps/139_sigma/figs/sigma.pdf",bbox_inches="tight")
print("그림 저장")
