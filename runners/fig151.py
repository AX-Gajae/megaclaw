import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
plt.rcParams.update({"font.family":"Apple SD Gothic Neo","font.size":8.5,
                     "axes.spines.top":False,"axes.spines.right":False,
                     "axes.unicode_minus":False})
fig=plt.figure(figsize=(11.5,4.2))
gs=fig.add_gridspec(1,3,width_ratios=[1.0,1.05,1.05],wspace=0.34)

# ── 1. 분산 층별 제거 --- 96% 를 빼고 남은 것
ax=fig.add_subplot(gs[0,0])
labs=["원천\n로그 수준","동네 평균\n뺀 뒤","+ 요일·월\n뺀 뒤 (소박)","+ 전국·공휴일\n뺀 뒤 (장)"]
sd=[0.4291,0.1248,0.0871,0.0602]
var=[s**2 for s in sd]; frac=[v/var[0] for v in var]
x=np.arange(len(sd))
ax.bar(x,frac,0.6,color=["#111","#6d8ab8","#2b4c7e","#b3392b"])
for i,(f,s) in enumerate(zip(frac,sd)):
    ax.text(i,f+0.022,f"{f*100:.2f}%\nSD {s:.4f}",ha="center",fontsize=7.6,
            weight="bold" if i==3 else "normal")
ax.set_xticks(x); ax.set_xticklabels(labs,fontsize=7.6)
ax.set_ylim(0,1.14)
ax.set_ylabel("남은 분산 / 전체 분산")
ax.annotate("",xy=(2,0.041),xytext=(0,1.0),
            arrowprops=dict(arrowstyle="->",lw=1.6,color="#2b4c7e"))
ax.text(0.62,0.62,"소박 규칙이\n95.88% 를 먹는다",fontsize=8.2,color="#2b4c7e",
        weight="bold")
ax.text(2.55,0.20,"장이 사는 자리\n= 전체의 1.97%",fontsize=7.8,color="#b3392b",
        weight="bold",ha="center")
ax.set_title("96퍼센트를 빼고 남은 것에서 쟀다\n장은 전체 변동의 1.97% 위에 있다",
             loc="left",fontsize=9,weight="bold")

# ── 2. R² 환산
ax=fig.add_subplot(gs[0,1])
rows=[("노트 736 이 보고한 것\n잔차 위 유보 R²",0.1200,"#2b4c7e"),
      ("전체 변동으로 환산\n0.12 × 0.0197",0.00236,"#b3392b")]
y=np.arange(len(rows))
ax.barh(y,[r[1] for r in rows],0.5,color=[r[2] for r in rows])
for i,r in enumerate(rows):
    ax.text(r[1]+0.003,i,f"{r[1]*100:.3f}%" if i else f"{r[1]:.4f}",
            va="center",fontsize=9,weight="bold",color=r[2])
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in rows],fontsize=8)
ax.invert_yaxis(); ax.set_xlim(0,0.145)
ax.set_xlabel("설명한 분산 몫")
ax.annotate("",xy=(0.012,1),xytext=(0.115,0),
            arrowprops=dict(arrowstyle="->",lw=2.0,color="#111"))
ax.text(0.055,0.55,"51 배",fontsize=11,weight="bold",ha="center")
ax.text(0.004,1.42,"잔차 위 R² 는 그 잔차의 분산 비중을\n곱해야 전체 설명력이 된다",
        fontsize=7.8,color="#333")
ax.set_title("0.1200 은 실은 0.0024 였다\n같은 수를 두 자로 읽으면 51배 차이",
             loc="left",fontsize=9,weight="bold")

# ── 3. 결정 지표 --- 아무것도 더하지 않는다
ax=fig.add_subplot(gs[0,2])
rows=[("어디에 열까\n동네 순위 스피어만",0.9915,0.9911,0.0000),
      ("언제 열까\n날짜 순위 스피어만",0.7242,0.7231,0.0005),
      ("top-10 적중\n(10 중 몇)",8.9713/10,8.9425/10,0.0311/10)]
y=np.arange(len(rows)); w=0.34
ax.barh(y-w/2,[r[1] for r in rows],w,color="#2b4c7e",label="소박(운영자가 아는 것)")
ax.barh(y+w/2,[r[2] for r in rows],w,color="#b3392b",label="소박 + 장")
for i,r in enumerate(rows):
    d=r[2]-r[1]
    mark="2σ 밖" if abs(d)>r[3] else "2σ 안"
    ax.text(r[2]+0.012,i+w/2,f"Δ {d:+.4f}\n({mark})",va="center",fontsize=7.2,
            color="#b3392b")
    ax.text(r[1]+0.012,i-w/2,f"{r[1]:.4f}",va="center",fontsize=7.4)
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in rows],fontsize=8)
ax.invert_yaxis(); ax.set_xlim(0,1.24)
ax.set_xlabel("실제 30일 뒤 방문과의 일치")
ax.legend(fontsize=7.2,loc="lower right",frameon=False)
ax.set_title("장을 더해도 결정이 안 바뀐다\n'해친다' 가 아니라 '아무것도 더하지 않는다'",
             loc="left",fontsize=9,weight="bold")
fig.savefig("paper/steps/151_ninetysix/figs/ninetysix.pdf",bbox_inches="tight")
print("그림 저장")
