import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
plt.rcParams.update({"font.family":"Apple SD Gothic Neo","font.size":8.5,
                     "axes.spines.top":False,"axes.spines.right":False,
                     "axes.unicode_minus":False})
fig=plt.figure(figsize=(11.6,4.2))
gs=fig.add_gridspec(1,3,width_ratios=[1.0,1.0,1.1],wspace=0.33)

# ── 1. U 자 --- 단조 상관이 0 인데 창이 갈린다
ax=fig.add_subplot(gs[0,0])
yr=[2020,2021,2022,2023,2024,2025,2026]
md=[0.00853,0.00841,0.00809,0.00793,0.00814,0.00846,0.00900]
ax.plot(yr,md,"-o",color="#2b4c7e",lw=2.2,ms=8,zorder=3)
ax.axvspan(2019.6,2024.99,color="#2b4c7e",alpha=0.10)
ax.axvspan(2024.99,2026.5,color="#b3392b",alpha=0.12)
ax.text(2022.2,0.00895,"학습 (2020~24)",fontsize=7.8,color="#2b4c7e",ha="center")
ax.text(2025.6,0.00895,"유보",fontsize=7.8,color="#b3392b",ha="center")
for x,y in zip(yr,md):
    ax.annotate(f"{y:.5f}",(x,y),textcoords="offset points",xytext=(0,-14),
                ha="center",fontsize=6.8)
ax.annotate("골",(2023,0.00793),textcoords="offset points",xytext=(0,13),
            ha="center",fontsize=8,weight="bold",color="#2b4c7e")
ax.annotate("어깨",(2026,0.00900),textcoords="offset points",xytext=(-6,10),
            ha="center",fontsize=8,weight="bold",color="#b3392b")
ax.set_xlim(2019.6,2026.6); ax.set_ylim(0.0077,0.0092)
ax.set_xlabel("연도")
ax.set_ylabel("원천 계열 중앙값 (예보 Δ 의 동네 간 SD)")
ax.set_title("날짜 상관은 -0.001 인데 U 자다\n학습이 골에 · 유보가 어깨에 앉았다",
             loc="left",fontsize=9,weight="bold")

# ── 2. 겹침과 신호 몫
ax=fig.add_subplot(gs[0,1])
rows=[("전 구간 백분위\n(노트 754)",0.074,-0.0192,"#b3392b"),
      ("직전 365일 편차\n(배포 가능)",0.452,None,"#d4a11a"),
      ("창 안 백분위\n(전이적 · 기제 시험)",0.996,-0.0079,"#2b4c7e")]
y=np.arange(len(rows))
ax.barh(y,[r[1] for r in rows],0.5,color=[r[3] for r in rows])
for i,r in enumerate(rows):
    ax.text(r[1]+0.02,i,f"겹침 {r[1]:.3f}",va="center",fontsize=7.8,weight="bold")
    if r[2] is not None:
        ax.text(0.02,i-0.27,f"신호 몫 {r[2]:+.4f}",fontsize=7.4,color="#333")
    else:
        ax.text(0.02,i-0.27,"판에서 안 쟀다",fontsize=7.4,color="#8a6a10")
ax.axvline(0.9,color="#111",lw=1.2,ls="--")
ax.text(0.9,2.62,"게이트 0.9",fontsize=7.2,ha="center")
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in rows],fontsize=8)
ax.invert_yaxis(); ax.set_xlim(0,1.15)
ax.set_xlabel("학습·유보 백분위 사분위 겹침 비율")
ax.set_title("분포를 맞추면 해로움이 59% 줄어든다\n그러나 배포 가능한 정상화는 절반만 회복",
             loc="left",fontsize=9,weight="bold")

# ── 3. 남은 해로움이 두 도메인에 몰려 있다
ax=fig.add_subplot(gs[0,2])
D={"웹툰":(-0.0442,-0.0397,650),"도서":(-0.0816,-0.0546,163),
   "시장팝업":(-0.0987,0.0446,126),"애니":(-0.0077,0.0032,606),
   "모바일":(-0.0055,0.0110,441),"만화":(-0.0069,0.0060,258),
   "게임":(-0.0075,-0.0060,180),"세계애니":(-0.0038,-0.0061,300),
   "펀딩":(0.0047,-0.0049,529),"팝업":(0.0259,-0.0034,65),
   "아이돌":(0.0028,0.0008,51)}
ks=sorted(D,key=lambda k:D[k][1])
y=np.arange(len(ks)); w=0.36
ax.barh(y-w/2,[D[k][0] for k in ks],w,color="#c8a0a0",label="전 구간 백분위(고유10)")
ax.barh(y+w/2,[D[k][1] for k in ks],w,
        color=["#b3392b" if D[k][1]<-0.02 else "#2b4c7e" for k in ks],
        label="창 안 백분위(분포 맞춤)")
for i,k in enumerate(ks):
    ax.text(D[k][1]+(0.003 if D[k][1]>0 else -0.003),i+w/2,f"{D[k][1]:+.4f}",
            va="center",ha="left" if D[k][1]>0 else "right",fontsize=7.0,
            weight="bold" if D[k][1]<-0.02 else "normal")
ax.axvline(0,color="#111",lw=1.2)
ax.axvline(-0.0045,color="#555",lw=1.0,ls=":")
ax.set_yticks(y); ax.set_yticklabels(
    [f"{k} ({D[k][2]})" for k in ks],fontsize=7.6)
ax.invert_yaxis(); ax.set_xlim(-0.115,0.075)
ax.set_xlabel("도메인 신호 몫 (괄호는 유보 행수)")
ax.legend(fontsize=7.0,loc="lower right",frameon=False)
ax.set_title("아홉은 0 으로 오고 둘만 남는다\n웹툰(겹침 0.991) · 도서(0.962)",
             loc="left",fontsize=9,weight="bold")
fig.savefig("paper/steps/149_ushape/figs/ushape.pdf",bbox_inches="tight")
print("그림 저장")
