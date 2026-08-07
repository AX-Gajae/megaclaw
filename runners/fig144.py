import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
plt.rcParams.update({"font.family":"Apple SD Gothic Neo","font.size":8.5,
                     "axes.spines.top":False,"axes.spines.right":False,
                     "axes.unicode_minus":False})
THR=0.0045
fig=plt.figure(figsize=(11.6,4.3))
gs=fig.add_gridspec(1,3,width_ratios=[1.05,1.05,1.0],wspace=0.34)

# ── 1. 문 셋: 신호 몫 · 시장팝업 뺀 값
ax=fig.add_subplot(gs[0,0])
rows=[("① 공유 어휘·가중\n(노트 698)",0.0040,-0.0018),
      ("② 공유 트렁크 +\n도메인 임베딩 (721)",0.0106,0.0038),
      ("③ 소스 고르기\n(729)",-0.0027,0.0019)]
y=np.arange(len(rows))
ax.barh(y-0.19,[r[1] for r in rows],0.35,color="#2b4c7e",label="판 신호 몫")
ax.barh(y+0.19,[r[2] for r in rows],0.35,color="#a8b4c8",
        label="시장팝업 도메인을 뺀 값")
for i,r in enumerate(rows):
    for off,v in ((-0.19,r[1]),(0.19,r[2])):
        ax.text(v+(0.0006 if v>0 else -0.0006),i+off,f"{v:+.4f}",va="center",
                ha="left" if v>0 else "right",fontsize=7.4,
                weight="bold" if off<0 else "normal")
ax.axvline(0,color="#111",lw=1.2)
ax.axvline(THR,color="#b3392b",lw=1.5,ls="--")
ax.text(THR,-0.72,f"문턱 {THR}\n(2σ · 노트 715·717)",color="#b3392b",fontsize=7.2,
        ha="center")
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in rows],fontsize=8)
ax.invert_yaxis(); ax.set_xlim(-0.005,0.0135)
ax.set_xlabel("판 신호 몫 = 진짜 - 위약")
ax.legend(fontsize=7.2,loc="lower right",frameon=False)
ax.set_title("T5 의 문 셋이 다 닫혔다\n하나도 문턱을 못 넘고 ③은 위약보다 나쁘다",
             loc="left",fontsize=9,weight="bold")

# ── 2. 풀 축소 비용 --- 잡음 곡선 위에 앉힌다
ax=fig.add_subplot(gs[0,1])
TR={"만화":5644,"웹툰":2936,"애니":2779,"세계애니":2647,"펀딩":2358,"모바일":1558,
    "게임":259,"시장팝업":123,"도서":80,"아이돌":56,"팝업":17}
TOT=18457
n=np.geomspace(40,TOT,400)
ax.plot(n,np.sqrt(TOT/n),color="#2b4c7e",lw=2.0)
ax.fill_between(n,1,np.sqrt(TOT/n),color="#2b4c7e",alpha=0.09)
for k,c in (("도서","#b3392b"),("아이돌","#b3392b")):
    v=np.sqrt(TOT/TR[k])
    ax.scatter(TR[k],v,s=170,c=c,zorder=4,edgecolor="w",lw=1.3)
    ax.annotate(f"{k}  {TR[k]}행\n**잡음 ×{v:.1f}**".replace("**",""),
                (TR[k],v),textcoords="offset points",xytext=(13,-2),
                va="center",fontsize=7.8,weight="bold",color=c)
ax.scatter(TR["팝업"],np.sqrt(TOT/TR["팝업"]),s=120,c="#7f8896",zorder=4,
           edgecolor="w",lw=1.2,marker="X")
ax.annotate("팝업 17행 --- 건너뜀\n(자기 20행 미달)",(TR["팝업"],np.sqrt(TOT/TR["팝업"])),
            textcoords="offset points",xytext=(13,4),va="center",fontsize=7.4,
            color="#555")
ax.axhline(1,color="#111",lw=1.1)
ax.scatter([TOT],[1],s=150,c="#111",zorder=4,marker="s")
ax.annotate("전부 합친 풀 18,457행 --- 잡음 ×1\n(이것이 노트 721 이 쓴 풀이다)",
            (TOT,1),textcoords="offset points",xytext=(-8,16),ha="right",
            fontsize=7.6)
ax.set_xscale("log"); ax.set_xlim(13,34000); ax.set_ylim(0,36)
ax.set_xlabel("그 목표의 트렁크가 쓴 학습 행수 (로그)")
ax.set_ylabel("잡음 배수  √(18457 / 풀 행수)")
ax.set_title("셋은 자기만 골랐고 풀이 무너졌다\n노트 717 의 법칙 SD 는 1/√n --- 15~18배 잡음",
             loc="left",fontsize=9,weight="bold")

# ── 3. 시장팝업의 부호 뒤집기
ax=fig.add_subplot(gs[0,2])
rows=[("노트 698\n공유 어휘",0.1534),("노트 721\n공유 트렁크",0.1857),
      ("노트 729\n소스 고르기",-0.1191)]
y=np.arange(len(rows))
ax.bar(y,[r[1] for r in rows],0.52,
       color=["#2b4c7e","#2b4c7e","#b3392b"])
for i,r in enumerate(rows):
    ax.text(i,r[1]+(0.012 if r[1]>0 else -0.012),f"{r[1]:+.4f}",ha="center",
            va="bottom" if r[1]>0 else "top",fontsize=8,weight="bold")
ax.axhline(0,color="#111",lw=1.2)
ax.axhline(-0.0393,color="#7f8896",lw=1.3,ls=":")
ax.text(2.42,-0.0393,"그 도메인 축 품질 -0.0393\n(노트 723 · 처음부터 음수)",
        fontsize=7.2,color="#555",va="center",ha="right")
ax.set_xticks(y); ax.set_xticklabels([r[0] for r in rows],fontsize=8)
ax.set_ylim(-0.16,0.23)
ax.set_ylabel("시장팝업 도메인 신호 몫")
ax.set_title("같은 도메인이 부호를 뒤집었다\n'이득' 이 아니라 판이 뒤집어 쓰던 신호였다",
             loc="left",fontsize=9,weight="bold")
fig.savefig("paper/steps/144_shrinkpool/figs/shrinkpool.pdf",bbox_inches="tight")
print("그림 저장")
