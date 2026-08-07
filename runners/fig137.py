import json
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
plt.rcParams.update({"font.family":"Apple SD Gothic Neo","font.size":8.5,
                     "axes.spines.top":False,"axes.spines.right":False})
fig=plt.figure(figsize=(11.2,4.0))
gs=fig.add_gridspec(1,3,width_ratios=[1.1,1.05,1.0],wspace=0.34)

# --- 1. 표본 안 대 유보
ax=fig.add_subplot(gs[0,0])
rows=[("제작사\n154 고정효과",0.3865,0.1559,"#b3392b"),
      ("만화 인기\n2 모수",0.4412,0.5266,"#2b4c7e"),
      ("만화 안전특징\n7 열",np.nan,0.1127,"#7f8896")]
x=np.arange(len(rows))
ax.bar(x-0.19,[r[1] for r in rows],0.36,color="#c9ccd4",label="표본 안")
ax.bar(x+0.19,[r[2] for r in rows],0.36,color=[r[3] for r in rows],label="유보")
for i,r in enumerate(rows):
    if np.isfinite(r[1]): ax.text(i-0.19,r[1]+0.012,f"{r[1]:.3f}",ha="center",fontsize=7.4)
    ax.text(i+0.19,r[2]+0.012,f"{r[2]:.3f}",ha="center",fontsize=7.4,weight="bold")
ax.annotate("60% 무너진다\n(자유도 27.3%)",xy=(0.19,0.156),xytext=(0.55,0.30),
            fontsize=7.4,color="#b3392b",
            arrowprops=dict(arrowstyle="->",color="#b3392b",lw=0.9))
ax.set_xticks(x); ax.set_xticklabels([r[0] for r in rows],fontsize=7.6)
ax.set_ylabel("애니 인기 설명 R²"); ax.set_ylim(0,0.62)
ax.legend(frameon=False,fontsize=7.6,loc="upper left")
ax.set_title("노트 692 를 정정한다\n표본 안 비교는 154모수에 유리했다",loc="left",fontsize=9,weight="bold")

# --- 2. 제작사를 얹어도 안 오른다
ax=fig.add_subplot(gs[0,1])
arms=[("물음A\n만화 특징만",0.3657,"#2b4c7e"),
      ("물음B\n+제작사 2열",0.3637,"#2b4c7e"),
      ("위약\n제작사 값만 섞음",0.3632,"#c9ccd4"),
      ("대조\n난수 연속 2열",0.2863,"#b3392b")]
y=np.arange(len(arms))
ax.barh(y,[a[1] for a in arms],0.6,color=[a[2] for a in arms])
for i,a in enumerate(arms): ax.text(a[1]+0.006,i,f"{a[1]:.4f}",va="center",fontsize=7.6)
ax.set_yticks(y); ax.set_yticklabels([a[0] for a in arms],fontsize=7.6); ax.invert_yaxis()
ax.axvline(0.3657,color="#111",lw=0.9,ls=":")
ax.set_xlim(0.24,0.42); ax.set_xlabel("조건부 전이 유보 스피어만 (127행)")
ax.set_title("B 와 위약이 붙어 있다 (차 0.0005)\n부트2σ = 0.1583",loc="left",fontsize=9,weight="bold")

# --- 3. 차원 비용은 거칠기에 달렸다
ax=fig.add_subplot(gs[0,2])
ax.bar([0,1],[0.001,0.040],0.5,color=["#2b4c7e","#b3392b"])
ax.text(0,0.0025,"0.001",ha="center",fontsize=8.4,weight="bold")
ax.text(1,0.0415,"0.040",ha="center",fontsize=8.4,weight="bold")
ax.set_xticks([0,1]); ax.set_xticklabels(["이산·저카디널리티\n(제작사 2열)",
                                           "연속·고카디널리티\n(난수 2열)"],fontsize=7.6)
ax.set_ylabel("열 하나당 ρ 손실"); ax.set_ylim(0,0.049)
ax.axhline(0.0225,color="#555",lw=1.0,ls="--")
ax.text(1.42,0.0235,"노트 641 이 쟀던\n'열당 0.02~0.025'",fontsize=7.2,color="#555",ha="right")
ax.annotate("",xy=(0.25,0.001),xytext=(0.75,0.040),
            arrowprops=dict(arrowstyle="<->",color="#111",lw=0.9))
ax.text(0.5,0.021,"40배",ha="center",fontsize=9,weight="bold")
ax.set_title("'열을 적게' 가 아니라\n'거친 열을 적게' 다",loc="left",fontsize=9,weight="bold")
fig.savefig("paper/steps/137_sealed/figs/sealed.pdf",bbox_inches="tight")
print("그림 저장")
