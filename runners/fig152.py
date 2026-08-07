import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
plt.rcParams.update({"font.family":"Apple SD Gothic Neo","font.size":8.5,
                     "axes.spines.top":False,"axes.spines.right":False,
                     "axes.unicode_minus":False})
fig=plt.figure(figsize=(11.5,4.2))
gs=fig.add_gridspec(1,3,width_ratios=[1.0,1.05,1.05],wspace=0.34)

# ── 1. 자료가 줄어드는 사다리
ax=fig.add_subplot(gs[0,0])
labs=["레코드","시군구 있음","+ 방문객 라벨","+ 장 창(30일)","+ 동네 고정\n(같은 구 2건+)"]
n=[380,179,66,62,62]
y=np.arange(len(n))
ax.barh(y,n,0.6,color=["#111","#6d8ab8","#2b4c7e","#2b4c7e","#b3392b"])
for i,v in enumerate(n):
    ax.text(v+7,i,str(v),va="center",fontsize=8.4,weight="bold" if i>=2 else "normal")
ax.axvline(2028,color="#b3392b",lw=1.8,ls="--")
ax.text(2028,-0.85,"필요 2,028",color="#b3392b",fontsize=8,ha="center",weight="bold")
ax.set_xscale("log"); ax.set_xlim(30,3600)
ax.set_yticks(y); ax.set_yticklabels(labs,fontsize=7.8); ax.invert_yaxis()
ax.set_xlabel("행 수 (로그)")
ax.set_title("380 에서 62 로 줄었다\n노트 688 이 예상한 243 은 라벨 없는 것까지였다",
             loc="left",fontsize=9,weight="bold")

# ── 2. SD 로 읽으면 못 쓴다 · IQR 로 읽으면 쓴다
ax=fig.add_subplot(gs[0,1])
rows=[("SD 로 읽기\nSE(a) = 1,131",49.1672,89160999,"#7f8896"),
      ("IQR 로 읽기\nIQR(a) = 7.99",0.2345,2028,"#2b4c7e")]
y=np.arange(len(rows))
ax.barh(y,[r[1] for r in rows],0.5,color=[r[3] for r in rows])
for i,r in enumerate(rows):
    ax.text(r[1]*1.4,i,f"MDE {r[1]:.4f}\n필요 {r[2]:,}행",va="center",fontsize=8,
            weight="bold" if i else "normal",color=r[3])
ax.axvline(0.041,color="#b3392b",lw=1.6,ls="--")
ax.text(0.041,1.62,"실무 문턱 0.041\n(방문객 10%)",color="#b3392b",fontsize=7.4,
        ha="center")
ax.set_xscale("log"); ax.set_xlim(0.02,900)
from matplotlib.ticker import FixedFormatter, FixedLocator
tk=[0.04,0.1,1,10,100]
ax.xaxis.set_major_locator(FixedLocator(tk))
ax.xaxis.set_major_formatter(FixedFormatter(["0.04","0.1","1","10","100"]))
ax.xaxis.set_minor_locator(FixedLocator([]))
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in rows],fontsize=8)
ax.invert_yaxis()
ax.set_xlabel("MDE(a × SD(g))  --- 로그 눈금")
ax.set_title("같은 부트 분포를 두 자로 읽었다\n폭발한 뽑기가 SD 를 지배한다",
             loc="left",fontsize=9,weight="bold")

# ── 3. 클러스터 크기가 폭발의 원인
ax=fig.add_subplot(gs[0,2])
CL={"성동구":24,"영등포구":11,"강남구":10,"중구":3,"마포구":3,"송파구":3,
    "종로구":2,"용산구":2,"분당구":2,"일산서구":2}
ks=list(CL); v=[CL[k] for k in ks]
y=np.arange(len(ks))
ax.barh(y,v,0.62,color=["#2b4c7e" if x>=10 else "#b3392b" for x in v])
for i,x in enumerate(v):
    ax.text(x+0.3,i,str(x),va="center",fontsize=8,weight="bold")
ax.axvline(4,color="#111",lw=1.2,ls=":")
ax.set_yticks(y); ax.set_yticklabels(ks,fontsize=7.8); ax.invert_yaxis()
ax.set_xlim(0,28)
ax.set_xlabel("그 시군구의 행 수 (전체 62)")
ax.text(6.5,7.4,"붉은 일곱은 2~3행 --- 재표집에서\n그 동네만 뽑히면 동네 안 g 변동이\n0 에 가까워 a 가 폭발한다",
        fontsize=7.4,color="#b3392b")
ax.set_title("세 동네가 72% 를 낸다\n성동구 24 · 영등포구 11 · 강남구 10",
             loc="left",fontsize=9,weight="bold")
fig.savefig("paper/steps/152_twothousand/figs/twothousand.pdf",bbox_inches="tight")
print("그림 저장")
