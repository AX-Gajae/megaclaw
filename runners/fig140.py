import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
plt.rcParams.update({"font.family":"Apple SD Gothic Neo","font.size":8.5,
                     "axes.spines.top":False,"axes.spines.right":False,
                     "axes.unicode_minus":False})
D={"비게임 앱":{"n":[1600,800,400],"sd":[0.01198,0.01454,0.02034],"sl":-0.382,"c":0.432,
              "psd":0.158,"rho":0.4968,"col":"#2b4c7e"},
   "KR 만화":{"n":[1716,858,429],"sd":[0.00270,0.00462,0.00648],"sl":-0.632,"c":0.127,
             "psd":0.0967,"rho":0.6831,"col":"#b3392b"},
   "CN 만화":{"n":[352,176,88],"sd":[0.01174,0.01631,0.02588],"sl":-0.570,"c":0.227,
             "psd":0.109,"rho":0.3874,"col":"#d4a11a"}}
fig=plt.figure(figsize=(11.4,4.0))
gs=fig.add_gridspec(1,3,width_ratios=[1.1,1.0,1.05],wspace=0.32)

ax=fig.add_subplot(gs[0,0])
for k,v in D.items():
    ax.plot(v["n"],v["sd"],"o-",color=v["col"],lw=1.6,ms=6,
            label=f"{k}  기울기 {v['sl']:.3f}")
ax.set_xscale("log"); ax.set_yscale("log")
xs=np.array([80,1800])
ax.plot(xs,0.0155*(xs/1600)**-0.5,"--",color="#111",lw=1.0)
ax.text(150,0.040,"기울기 -0.5\n(예측)",fontsize=7.4)
from matplotlib.ticker import FixedLocator, FixedFormatter, NullFormatter
ax.xaxis.set_major_locator(FixedLocator([100,200,400,800,1600]))
ax.xaxis.set_major_formatter(FixedFormatter(["100","200","400","800","1600"]))
ax.xaxis.set_minor_formatter(NullFormatter())
ax.yaxis.set_major_locator(FixedLocator([0.003,0.006,0.012,0.025]))
ax.yaxis.set_major_formatter(FixedFormatter(["0.003","0.006","0.012","0.025"]))
ax.yaxis.set_minor_formatter(NullFormatter())
ax.set_xlabel("채점 행수 n (로그)"); ax.set_ylabel("참값 0 SD (로그)")
ax.legend(frameon=False,fontsize=7.4,loc="lower left")
ax.set_title("짝 안에서 n 만 바꾸니 기울기가 -0.5 근처다\n부분표본 100% · 50% · 25%",
             loc="left",fontsize=9,weight="bold")

ax=fig.add_subplot(gs[0,1])
w=0.26
for i,(k,v) in enumerate(D.items()):
    vals=[s*np.sqrt(n) for s,n in zip(v["sd"],v["n"])]
    x=np.arange(3)+(i-1)*w
    ax.bar(x,vals,w,color=v["col"],label=k)
    for xx,vv in zip(x,vals):
        ax.text(xx,vv+0.012,f"{vv:.2f}",ha="center",fontsize=6.8)
ax.set_xticks(np.arange(3)); ax.set_xticklabels(["100%","50%","25%"])
ax.set_ylabel("√n × SD  ( = c )"); ax.set_ylim(0,0.58)
ax.legend(frameon=False,fontsize=7.4,loc="upper left")
ax.set_title("짝 안에서 거의 상수 — 그래서 c 다\n짝 사이는 3.40배 남는다",
             loc="left",fontsize=9,weight="bold")

ax=fig.add_subplot(gs[0,2])
steps=["c 그대로","나누기\n예보퍼짐","나누기 예보퍼짐\n곱하기 (1-p²)"]
vals={k:[v["c"], v["c"]/v["psd"], v["c"]/(v["psd"]*(1-v["rho"]**2))] for k,v in D.items()}
mx=[max(x[i] for x in vals.values()) for i in range(3)]
x=np.arange(3)
for k,v in D.items():
    ax.plot(x,[vals[k][i]/mx[i] for i in range(3)],"o-",color=v["col"],lw=1.8,ms=7,label=k)
for i,s in enumerate([3.40,2.08,1.48]):
    ax.text(i,1.07,f"{s:.2f}배",ha="center",fontsize=8.4,weight="bold")
ax.set_xticks(x); ax.set_xticklabels(steps,fontsize=7.6)
ax.set_ylabel("최대값 대비 (흩어짐이 줄어야 좋다)"); ax.set_ylim(0,1.18)
ax.legend(frameon=False,fontsize=7.4,loc="lower left")
ax.set_title("정규화하면 3.40 → 1.48배\nCN 2.45 · KR 2.46 이 만나고 앱만 3.63",
             loc="left",fontsize=9,weight="bold")
fig.savefig("paper/steps/140_noiselaw/figs/noiselaw.pdf",bbox_inches="tight")
print("그림 저장")
