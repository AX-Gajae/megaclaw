import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
plt.rcParams.update({"font.family":"Apple SD Gothic Neo","font.size":8.5,
                     "axes.spines.top":False,"axes.spines.right":False,
                     "axes.unicode_minus":False})
# 도메인: (전부, LODO, 학습행, 계열)
D={"애니":(0.3680,0.1411,2779,"일본 만화·애니"),
   "세계애니":(0.0821,0.0581,2647,"일본 만화·애니"),
   "만화":(0.0322,0.0164,5644,"일본 만화·애니"),
   "모바일":(0.1473,-0.0011,1558,"앱·게임"),
   "웹툰":(0.0015,-0.0141,2936,"한국 IP"),
   "시장팝업":(-0.0393,-0.0281,123,"한국 IP"),
   "게임":(-0.0824,-0.0711,259,"앱·게임"),
   "펀딩":(-0.1292,-0.0859,2358,"그밖"),
   "도서":(-0.1270,-0.1461,80,"그밖"),
   "팝업":(-0.1832,-0.2000,17,"한국 IP"),
   "아이돌":(-0.3704,-0.3725,56,"한국 IP")}
FAM={"일본 만화·애니":"#2b4c7e","한국 IP":"#b3392b","앱·게임":"#d4a11a","그밖":"#7f8896"}
fig=plt.figure(figsize=(11.4,4.2))
gs=fig.add_gridspec(1,3,width_ratios=[1.15,1.0,1.0],wspace=0.33)

# ── 1. LODO 막대
ax=fig.add_subplot(gs[0,0])
ks=sorted(D,key=lambda k:-D[k][1])
y=np.arange(len(ks))
ax.barh(y,[D[k][1] for k in ks],0.6,color=[FAM[D[k][3]] for k in ks])
for i,k in enumerate(ks):
    v=D[k][1]
    ax.text(v+(0.012 if v>0 else -0.012), i, f"{v:+.4f}", va="center",
            ha="left" if v>0 else "right", fontsize=7.2)
ax.axvline(0,color="#111",lw=1.4)
ax.set_yticks(y); ax.set_yticklabels(ks); ax.invert_yaxis()
ax.set_xlim(-0.47,0.24)
ax.set_xlabel("LODO --- 자기 행이 하나도 안 든 트렁크의 예보 품질")
ax.set_title("순수 전이는 셋만 양수 · 여덟은 거꾸로 간다\n색 = 계열 (남색 일본 만화·애니)",
             loc="left",fontsize=9,weight="bold")

# ── 2. 전부 대 LODO
ax=fig.add_subplot(gs[0,1])
for k,(f,lo,n,fam) in D.items():
    ax.scatter(f,lo,s=150,c=FAM[fam],zorder=3,edgecolor="w",lw=1.2)
    dy=-0.030 if k in ("세계애니","게임") else 0.022
    ax.annotate(k,(f,lo),textcoords="offset points",xytext=(0,10 if dy>0 else -16),
                ha="center",fontsize=7.4)
lim=[-0.45,0.42]
ax.plot(lim,lim,"--",color="#999",lw=1.0)
ax.axhline(0,color="#111",lw=1.0); ax.axvline(0,color="#111",lw=1.0)
ax.fill_between([0,0.42],[-0.45,-0.45],[0,0],color="#b3392b",alpha=0.08)
ax.text(0.20,-0.10,"전부는 양수인데\nLODO 는 음수\n= 자기 행이 다 한 것",
        fontsize=7.2,ha="center",color="#b3392b")
ax.set_xlim(*lim); ax.set_ylim(*lim)
ax.set_xlabel("전부 넣은 트렁크"); ax.set_ylabel("LODO")
ax.set_title("모바일·웹툰은 전부만 양수다\n대각선 위면 자기 행 몫이 0",
             loc="left",fontsize=9,weight="bold")

# ── 3. 경쟁 설명 --- 계열 대 행수
ax=fig.add_subplot(gs[0,2])
for k,(f,lo,n,fam) in D.items():
    ax.scatter(n,lo,s=150,c=FAM[fam],zorder=3,edgecolor="w",lw=1.2)
    ax.annotate(k,(n,lo),textcoords="offset points",xytext=(0,10),
                ha="center",fontsize=7.2)
ax.axhline(0,color="#111",lw=1.2)
ax.set_xscale("log")
from matplotlib.ticker import FixedLocator, FixedFormatter, NullFormatter
ax.xaxis.set_major_locator(FixedLocator([20,50,100,300,1000,3000,6000]))
ax.xaxis.set_major_formatter(FixedFormatter(["20","50","100","300","1000","3000","6000"]))
ax.xaxis.set_minor_formatter(NullFormatter())
ax.set_xlabel("자기 학습 행수 (로그)"); ax.set_ylabel("LODO")
hs=[plt.Line2D([],[],marker="o",ls="",color=c,label=f) for f,c in FAM.items()]
ax.legend(handles=hs,frameon=False,fontsize=7.0,loc="lower right")
ax.set_title("경쟁 설명 둘 --- 계열인가 행수인가\nLODO↔행수 스피어만 +0.818 (p=0.002)",
             loc="left",fontsize=9,weight="bold")
fig.savefig("paper/steps/142_backwards/figs/backwards.pdf",bbox_inches="tight")
print("그림 저장")
