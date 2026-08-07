import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
plt.rcParams.update({"font.family":"Apple SD Gothic Neo","font.size":8.5,
                     "axes.spines.top":False,"axes.spines.right":False,
                     "axes.unicode_minus":False})
fig=plt.figure(figsize=(11.5,4.2))
gs=fig.add_gridspec(1,3,width_ratios=[1.0,1.05,1.0],wspace=0.33)

# ── 1. 만화 --- 진짜 대 위약 여섯
ax=fig.add_subplot(gs[0,0])
plac=[0.3338,0.3257,0.3487,0.3283,0.3413,0.3226]
base=0.3373; real=0.3565
m=float(np.mean(plac)); sd=float(np.std(plac,ddof=1))
ax.axhspan(m-2*sd,m+2*sd,color="#a8b4c8",alpha=0.30,zorder=1,
           label="위약 평균 ±2×뽑기SD")
ax.axhline(m,color="#555",lw=1.3,zorder=2)
for i,p in enumerate(plac):
    ax.scatter(i+1,p,s=120,c="#7f8896",zorder=3,edgecolor="w",lw=1.1)
ax.axhline(base,color="#111",lw=1.4,ls=":",zorder=2)
ax.scatter([7.6],[real],s=280,marker="D",c="#2b7e4c",zorder=5,edgecolor="w",lw=1.5)
ax.annotate(f"진짜\n{real:.4f}",(7.6,real),textcoords="offset points",
            xytext=(0,20),ha="center",fontsize=9,weight="bold",color="#2b7e4c")
ax.text(0.4,base+0.0012,f"없이 {base:.4f}",fontsize=7.6)
ax.text(0.4,m-0.0028,f"위약 평균 {m:.4f}",fontsize=7.6,color="#555")
ax.annotate("",xy=(6.9,real),xytext=(6.9,m),
            arrowprops=dict(arrowstyle="<->",lw=1.8,color="#2b7e4c"))
ax.text(6.6,(real+m)/2,f"신호 몫\n+{real-m:.4f}",ha="right",va="center",
        fontsize=8.6,weight="bold",color="#2b7e4c")
ax.set_xlim(0.2,8.6); ax.set_ylim(0.316,0.362)
ax.set_xticks(list(range(1,7))+[7.6])
ax.set_xticklabels([f"위약{i}" for i in range(1,7)]+["진짜"],fontsize=7.2)
ax.set_ylabel("만화 도메인 점수 (유보 스피어만)")
ax.legend(fontsize=7.0,loc="lower left",frameon=False)
ax.set_title("만화 3열이 위약 여섯을 다 이겼다\n뽑기 6 · 씨앗 3 · 라벨을 한 번도 안 봤다",
             loc="left",fontsize=9,weight="bold")

# ── 2. 못박은 자 둘
ax=fig.add_subplot(gs[0,1])
rows=[("신호 몫",0.0231,"#2b7e4c"),
      ("2 × 뽑기 SD\n(못박은 자)",0.0200,"#b3392b"),
      ("그 도메인 2σ\n(c/√n · 노트 717)",0.0163,"#d4a11a")]
y=np.arange(len(rows))
ax.barh(y,[r[1] for r in rows],0.5,color=[r[2] for r in rows])
for i,r in enumerate(rows):
    ax.text(r[1]+0.0008,i,f"{r[1]:.4f}",va="center",fontsize=9,weight="bold",
            color=r[2])
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in rows],fontsize=8)
ax.invert_yaxis(); ax.set_xlim(0,0.028)
ax.set_xlabel("만화 도메인 눈금")
ax.text(0.0035,2.62,"신호가 자 둘을 다 넘는다 --- 통과",fontsize=8.4,weight="bold",
        color="#2b7e4c")
ax.text(0.0035,-0.72,"노트 779 에서는 자 둘이 충돌해 판정을 못 했다.\n"
        "이번엔 사전등록에서 자를 하나로 못박았다.",fontsize=7.2,color="#555")
ax.set_title("자를 하나로 못박으니 갈렸다\n0.0231 > 0.0200 그리고 > 0.0163",
             loc="left",fontsize=9,weight="bold")

# ── 3. 세 도메인 --- 두께가 설명한다
ax=fig.add_subplot(gs[0,2])
D={"만화":(5644,0.0231,0.0163,3,"#2b7e4c"),
   "게임":(259,0.0023,0.0195,3,"#7f8896"),
   "도서":(80,-0.0331,0.0205,5,"#b3392b")}
for k,(n,sig,thr,nc,c) in D.items():
    ax.scatter(n,sig,s=120+nc*40,c=c,zorder=3,edgecolor="w",lw=1.3)
    ax.annotate(f"{k}\n{nc}열 · 신호 {sig:+.4f}",(n,sig),
                textcoords="offset points",xytext=(14,0),va="center",fontsize=7.6)
    ax.plot([n,n],[0,thr],color=c,lw=1.0,ls=":",alpha=0.7)
    ax.scatter([n],[thr],marker="_",s=200,color=c,zorder=4)
ax.axhline(0,color="#111",lw=1.2)
ax.set_xscale("log"); ax.set_xlim(45,20000); ax.set_ylim(-0.042,0.034)
ax.set_xlabel("그 도메인 학습 행수 (로그 · 노트 723)")
ax.set_ylabel("그 도메인 신호 몫")
ax.text(60,0.024,"점 크기 = 넣은 열 수\n짧은 막대 = 그 도메인 2σ",fontsize=7.2,
        color="#333")
ax.text(60,-0.036,"도서는 위약 폭이 신호의 5.3배 --- 판정 불가",fontsize=7.4,
        color="#b3392b")
ax.set_title("두께가 갈랐다\n학습 5,644 대 259 대 80",loc="left",fontsize=9,
             weight="bold")
fig.savefig("paper/steps/155_firstpass/figs/firstpass.pdf",bbox_inches="tight")
print("그림 저장")
