import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
plt.rcParams.update({"font.family":"Apple SD Gothic Neo","font.size":8.5,
                     "axes.spines.top":False,"axes.spines.right":False,
                     "axes.unicode_minus":False})
fig=plt.figure(figsize=(11.6,4.2))
gs=fig.add_gridspec(1,3,width_ratios=[1.05,1.0,1.05],wspace=0.34)

# ── 1. 뽑기 3 → 6 에서 Δ 가 줄었다
ax=fig.add_subplot(gs[0,0])
p3=[0.6527,0.6769,0.6583]; p6=p3+[0.6698,0.6810,0.6690]
real=0.6856
for i,v in enumerate(p3):
    ax.scatter(1,v,s=110,c="#7f8896",zorder=3,edgecolor="w",lw=1.0)
for i,v in enumerate(p6):
    ax.scatter(2,v,s=110,c="#7f8896" if i<3 else "#b3392b",zorder=3,
               edgecolor="w",lw=1.0)
m3=float(np.mean(p3)); m6=float(np.mean(p6))
ax.plot([0.78,1.22],[m3,m3],lw=2.4,color="#2b4c7e")
ax.plot([1.78,2.22],[m6,m6],lw=2.4,color="#2b4c7e")
ax.text(1.26,m3,f"평균\n{m3:.4f}",fontsize=7.6,va="center",color="#2b4c7e")
ax.text(2.26,m6,f"평균\n{m6:.4f}",fontsize=7.6,va="center",color="#2b4c7e")
ax.axhline(real,color="#2b7e4c",lw=1.8,ls="--")
ax.text(0.62,real+0.0009,f"진짜 {real:.4f}",fontsize=7.8,color="#2b7e4c",
        weight="bold")
for x,mm,d in ((1,m3,real-m3),(2,m6,real-m6)):
    ax.annotate("",xy=(x,real),xytext=(x,mm),
                arrowprops=dict(arrowstyle="<->",lw=1.6,color="#b3392b"))
    ax.text(x-0.07,(real+mm)/2,f"Δ {d:+.4f}",ha="right",va="center",
            fontsize=8.6,weight="bold",color="#b3392b")
ax.set_xlim(0.55,2.6); ax.set_ylim(0.648,0.690)
ax.set_xticks([1,2]); ax.set_xticklabels(["위약 뽑기 3","위약 뽑기 6"],fontsize=8.4)
ax.set_ylabel("KR 만화 rho (짝 채점)")
ax.text(0.62,0.6505,"붉은 점 = 새로 더한 셋\n앞 셋이 우연히 낮았다",fontsize=7.2,
        color="#b3392b")
ax.set_title("뽑기를 늘리니 Δ 가 줄었다\n0.0230 → 0.0177 (23% 감쇠)",
             loc="left",fontsize=9,weight="bold")

# ── 2. 벽이 둘이다
ax=fig.add_subplot(gs[0,1])
rows=[("집안 신호 몫\n(만화 도메인)",0.0231,0.0163,"#2b7e4c"),
      ("집 밖 Δ\n(KR 만화)",0.0177,0.025,"#b3392b"),
      ("집 밖 Δ\n(CN 만화)",0.0078,0.022,"#7f8896")]
y=np.arange(len(rows)); w=0.34
ax.barh(y-w/2,[r[1] for r in rows],w,color=[r[3] for r in rows],label="효과 크기")
ax.barh(y+w/2,[r[2] for r in rows],w,color="#dfe4ea",label="그 시험대 문턱")
for i,r in enumerate(rows):
    ax.text(r[1]+0.0007,i-w/2,f"{r[1]:.4f}",va="center",fontsize=7.8,
            weight="bold",color=r[3])
    ax.text(r[2]+0.0007,i+w/2,f"{r[2]:.4f}",va="center",fontsize=7.6,color="#555")
    ok = "통과" if r[1]>r[2] else f"{r[1]/r[2]*100:.0f}%"
    ax.text(0.0295,i,ok,fontsize=8.4,weight="bold",
            color="#2b7e4c" if r[1]>r[2] else "#b3392b")
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in rows],fontsize=7.8)
ax.invert_yaxis(); ax.set_xlim(0,0.034)
ax.set_xlabel("그 시험대 눈금")
ax.legend(fontsize=7.0,loc="lower right",frameon=False)
ax.set_title("벽이 둘이다\n전이 23% 감쇠 그리고 문턱 5.6배",loc="left",
             fontsize=9,weight="bold")

# ── 3. 뽑기를 늘리면 어느 쪽으로든 간다
ax=fig.add_subplot(gs[0,2])
pairs=[("집안\n(노트 780)",0.0204,0.0231,"#2b7e4c"),
       ("집 밖 KR\n(노트 785)",0.0230,0.0177,"#b3392b")]
x=np.arange(len(pairs)); w=0.3
for i,(nm,a,b,c) in enumerate(pairs):
    ax.plot([i-w,i+w],[a,b],"-o",color=c,lw=2.4,ms=10,zorder=3)
    ax.text(i-w,a,f"{a:.4f}",ha="right",va="center",fontsize=8,color="#555")
    ax.text(i+w+0.05,b,f"{b:.4f}",ha="left",va="center",fontsize=8.6,
            weight="bold",color=c)
    d = b-a
    ax.text(i,(a+b)/2+(0.0012 if d>0 else -0.0016),
            f"{'↑ 통과' if d>0 else '↓ 미달'}\n{d:+.4f}",ha="center",
            fontsize=8.2,weight="bold",color=c)
ax.set_xlim(-0.6,1.75); ax.set_ylim(0.014,0.026)
ax.set_xticks(x); ax.set_xticklabels([p[0] for p in pairs],fontsize=8.2)
ax.set_ylabel("효과 크기 (뽑기 3 → 6)")
ax.text(-0.5,0.0242,"같은 절차가 한 번은 통과를 만들고\n한 번은 미달을 만들었다",
        fontsize=7.6,color="#333")
ax.text(-0.5,0.0150,"→ 뽑기 3 을 판정에 쓰지 않는다\n     (규약 20 의 6 이 최소)",
        fontsize=7.8,weight="bold",color="#111")
ax.set_title("뽑기를 늘리면 어느 쪽으로든 간다\n좋게도 나쁘게도",loc="left",
             fontsize=9,weight="bold")
fig.savefig("paper/steps/156_drawer/figs/drawer.pdf",bbox_inches="tight")
print("그림 저장")
