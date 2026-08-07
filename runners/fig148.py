import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
plt.rcParams.update({"font.family":"Apple SD Gothic Neo","font.size":8.5,
                     "axes.spines.top":False,"axes.spines.right":False,
                     "axes.unicode_minus":False})
fig=plt.figure(figsize=(11.6,4.2))
gs=fig.add_gridspec(1,3,width_ratios=[1.0,1.05,1.05],wspace=0.34)

# ── 1. 마스크 구멍 있음 / 없음
ax=fig.add_subplot(gs[0,0])
G=[("유보에 구멍\n(노트 745)",0.4685,0.4251,0.4383),
   ("구멍 메움\n(노트 754)",0.4685,0.4401,0.4593)]
x=np.arange(len(G)); w=0.26
for i,(nm,b,r,p) in enumerate(G):
    ax.bar(i-w,b,w,color="#111")
    ax.bar(i,r,w,color="#b3392b")
    ax.bar(i+w,p,w,color="#a8b4c8")
    for off,v,c in ((-w,b,"#111"),(0,r,"#b3392b"),(w,p,"#555")):
        ax.text(i+off,v+0.0012,f"{v:.4f}",ha="center",fontsize=7.2,color=c)
    sig=r-p
    ax.annotate("",xy=(i,r),xytext=(i+w,p),
                arrowprops=dict(arrowstyle="<->",lw=1.5,color="#2b4c7e"))
    ax.text(i+w*0.5,(r+p)/2-0.0035,f"신호 몫\n{sig:+.4f}",ha="center",fontsize=7.8,
            weight="bold",color="#2b4c7e")
ax.set_xticks(x); ax.set_xticklabels([g[0] for g in G],fontsize=8)
ax.set_ylim(0.418,0.476)
ax.set_ylabel("판 ρ")
ax.legend(handles=[plt.Rectangle((0,0),1,1,fc=c) for c in ("#111","#b3392b","#a8b4c8")],
          labels=["없이","진짜","위약(3뽑기 평균)"],fontsize=7.2,loc="lower center",
          frameon=False,ncol=3)
ax.set_title("위약 비용은 줄고 신호 몫은 커졌다\n0.0302 → 0.0092 · -0.0132 → -0.0192",
             loc="left",fontsize=9,weight="bold")

# ── 2. 도메인별 판 기여 대 유보 행수
ax=fig.add_subplot(gs[0,1])
D={"웹툰":(-0.00853,650,0.71),"시장팝업":(-0.00423,126,1.00),"도서":(-0.00395,163,0.81),
   "애니":(-0.00127,606,0.64),"모바일":(-0.00114,441,0.55),"게임":(-0.00059,180,0.83),
   "세계애니":(-0.00041,300,0.36),"만화":(-0.00041,258,0.27),"아이돌":(0.00008,51,0.76),
   "팝업":(0.00023,65,1.00),"펀딩":(0.00107,529,0.66)}
for k,(c,n,cv) in D.items():
    col="#b3392b" if c<-0.002 else ("#7f8896" if c<0 else "#2b7e4c")
    ax.scatter(n,c,s=90+cv*130,c=col,zorder=3,edgecolor="w",lw=1.1)
    dx=(11,0) if k not in ("세계애니","만화") else (11,-5)
    ax.annotate(k,(n,c),textcoords="offset points",xytext=dx,va="center",fontsize=7.4)
ax.axhline(0,color="#111",lw=1.1)
ax.set_xlim(20,900); ax.set_xscale("log")
ax.set_xlabel("그 도메인의 유보 채점 행수 (로그) · 점 크기 = 덮음률")
ax.set_ylabel("판 기여 (신호 몫 × 가중)")
ax.text(24,-0.0078,"1위가 가장 두꺼운 도메인이다\n→ 얇은 도메인의 잡음이 아니다",
        fontsize=7.4,color="#b3392b")
ax.set_title("해로움이 두꺼운 도메인에서 온다\n웹툰 유보 650행 · 덮음 0.71",
             loc="left",fontsize=9,weight="bold")

# ── 3. 방향 진단 --- 뒤집히지 않고 감쇠한다
ax=fig.add_subplot(gs[0,2])
S={"웹툰":(0.082,0.022,-0.00853),"시장팝업":(-0.034,-0.121,-0.00423),
   "도서":(-0.020,-0.110,-0.00395),"애니":(0.077,0.020,-0.00127),
   "모바일":(-0.017,0.006,-0.00114),"게임":(0.021,0.013,-0.00059),
   "만화":(0.051,-0.026,-0.00041),"세계애니":(0.053,-0.013,-0.00041),
   "아이돌":(0.125,0.046,0.00008),"팝업":(-0.310,0.142,0.00023),
   "펀딩":(0.004,-0.069,0.00107)}
for k,(a,b,c) in S.items():
    col="#b3392b" if c<-0.002 else ("#7f8896" if c<0 else "#2b7e4c")
    ax.scatter(a,b,s=150,c=col,zorder=3,edgecolor="w",lw=1.2)
    dx=(0,11) if k not in ("애니","도서","세계애니") else (0,-14)
    ax.annotate(k,(a,b),textcoords="offset points",xytext=dx,ha="center",fontsize=7.2)
ax.axhline(0,color="#111",lw=1.1); ax.axvline(0,color="#111",lw=1.1)
lim=[-0.34,0.17]
ax.plot(lim,lim,"--",color="#999",lw=1.0)
ax.set_xlim(*lim); ax.set_ylim(-0.17,0.17)
ax.set_xlabel("학습 구간 축↔라벨 스피어만")
ax.set_ylabel("유보 축↔라벨 스피어만")
ax.text(-0.32,0.13,"2·4 사분면 = 부호 갈림 (5/11)",fontsize=7.2,color="#333")
ax.text(0.015,-0.15,"붉은 점(가장 해로운 셋)이\n1·3 사분면에 있다 --- 안 갈린다",
        fontsize=7.4,color="#b3392b")
ax.set_title("뒤집히지 않고 감쇠한다\n웹툰 0.082→0.022 · 애니 0.077→0.020",
             loc="left",fontsize=9,weight="bold")
fig.savefig("paper/steps/148_dilution/figs/dilution.pdf",bbox_inches="tight")
print("그림 저장")
