import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
plt.rcParams.update({"font.family":"Apple SD Gothic Neo","font.size":8.5,
                     "axes.spines.top":False,"axes.spines.right":False,
                     "axes.unicode_minus":False})
PER={"시장팝업":(0.1857,126),"팝업":(0.0233,65),"펀딩":(0.0119,529),
     "모바일":(0.0110,441),"세계애니":(0.0077,300),"만화":(0.0072,258),
     "아이돌":(0.0005,51),"도서":(0.0004,163),"게임":(-0.0014,180),
     "애니":(-0.0031,606),"웹툰":(-0.0038,650)}
THR0, N0 = 0.0045, 3369
fig=plt.figure(figsize=(11.4,4.2))
gs=fig.add_gridspec(1,3,width_ratios=[1.25,0.95,1.0],wspace=0.34)

# ── 1. 도메인별 신호 몫 대 그 도메인의 문턱(717 법칙)
ax=fig.add_subplot(gs[0,0])
ks=sorted(PER,key=lambda k:-PER[k][0]/(THR0*np.sqrt(N0/PER[k][1])))
y=np.arange(len(ks))
for i,k in enumerate(ks):
    s,n=PER[k]; t=THR0*np.sqrt(N0/n)
    r=s/t
    ax.barh(i,r,0.55,color="#2b4c7e" if r>1 else ("#c9ccd4" if r>0 else "#b3392b"))
    ax.text(r+0.12 if r>0 else 0.12, i, f"{s:+.4f} / {t:.4f}  n={n}",
            va="center",fontsize=6.9,color="#333")
ax.axvline(1,color="#111",lw=1.6)
ax.text(1.08,-0.72,"자기 문턱 = 1",fontsize=7.4,weight="bold")
ax.set_yticks(y); ax.set_yticklabels(ks); ax.invert_yaxis()
ax.set_xlim(-0.6,9.6); ax.set_xlabel("신호 몫 ÷ 그 도메인의 문턱 (노트 717 법칙)")
ax.set_title("문턱을 도메인마다 계산하면 하나만 넘는다\n시장팝업 7.98배 · 나머지는 다 1 아래",
             loc="left",fontsize=9,weight="bold")

# ── 2. 판 분해
ax=fig.add_subplot(gs[0,1])
bars=[("판 전체",0.0106,"#2b4c7e"),("시장팝업 뺀 판",0.0038,"#b3392b")]
x=np.arange(2)
ax.bar(x,[b[1] for b in bars],0.5,color=[b[2] for b in bars])
for i,b in enumerate(bars):
    ax.text(i,b[1]+0.0004,f"{b[1]:.4f}",ha="center",fontsize=8.4,weight="bold")
ax.axhline(0.0045,color="#111",lw=1.4,ls="--")
ax.text(1.52,0.0047,"판 문턱\n0.0045",fontsize=7.4,ha="right")
ax.axhline(0.0119,color="#0E7C86",lw=1.4,ls=":")
ax.text(1.52,0.0121,"도메인별 축\n0.0119 (노트 695)",fontsize=7.4,ha="right",color="#0E7C86")
ax.set_xticks(x); ax.set_xticklabels([b[0] for b in bars],fontsize=8)
ax.set_ylabel("판 신호 몫"); ax.set_ylim(0,0.0142)
ax.set_title("유보 126행 도메인 하나가\n전체의 66% 를 만든다",loc="left",fontsize=9,weight="bold")

# ── 3. 노트 698 대 721
ax=fig.add_subplot(gs[0,2])
rows=[("축 붙은 도메인",10,11,"개"),("웹툰 신호 몫",-0.0190,-0.0038,""),
      ("판 신호 몫",0.0040,0.0106,""),("시장팝업 뺀 판",-0.0018,0.0038,"")]
y=np.arange(len(rows))
w=0.36
ax.barh(y+w/2,[abs(r[1]) for r in rows],w,color="#c9ccd4",label="노트 698 (공유 어휘·가중)")
ax.barh(y-w/2,[abs(r[2]) for r in rows],w,color="#2b4c7e",label="노트 721 (+ 도메인 임베딩)")
for i,r in enumerate(rows):
    sc=11 if i==0 else 0.02
    ax.text(abs(r[1])/sc*0.0 + abs(r[1]) , i+w/2, f" {r[1]}{r[3]}",va="center",fontsize=7.0,color="#555")
    ax.text(abs(r[2]), i-w/2, f" {r[2]}{r[3]}",va="center",fontsize=7.4,weight="bold")
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in rows],fontsize=8); ax.invert_yaxis()
from matplotlib.ticker import FixedLocator, FixedFormatter, NullFormatter
ax.set_xscale("symlog",linthresh=0.002)
ax.xaxis.set_major_locator(FixedLocator([0,0.002,0.01,0.1,1,11]))
ax.xaxis.set_major_formatter(FixedFormatter(["0","0.002","0.01","0.1","1","11"]))
ax.xaxis.set_minor_formatter(NullFormatter())
ax.set_xlabel("절대값 (로그 · 부호는 글자로)")
ax.legend(frameon=False,fontsize=7.2,loc="lower right")
ax.set_title("두 단계 비교 — 넷 다 나아졌다\n그런데 판은 여전히 못 움직인다",
             loc="left",fontsize=9,weight="bold")
fig.savefig("paper/steps/141_yesterday/figs/yesterday.pdf",bbox_inches="tight")
print("그림 저장")
