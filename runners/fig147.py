import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
plt.rcParams.update({"font.family":"Apple SD Gothic Neo","font.size":8.5,
                     "axes.spines.top":False,"axes.spines.right":False,
                     "axes.unicode_minus":False})
fig=plt.figure(figsize=(11.5,4.2))
gs=fig.add_gridspec(1,3,width_ratios=[1.0,1.05,1.05],wspace=0.34)

# ── 1. 판 네 팔
ax=fig.add_subplot(gs[0,0])
rows=[("없이",0.4685,0.0028,"#111"),
      ("진짜\n(장 시간축)",0.4251,0.0035,"#b3392b"),
      ("위약 7440",0.4372,0.0032,"#a8b4c8"),
      ("위약 7441",0.4404,0.0017,"#a8b4c8"),
      ("위약 7442",0.4373,0.0000,"#a8b4c8")]
y=np.arange(len(rows))
ax.barh(y,[r[1] for r in rows],0.6,color=[r[3] for r in rows],
        xerr=[r[2] for r in rows],error_kw=dict(lw=1.0,ecolor="#555"))
for i,r in enumerate(rows):
    ax.text(r[1]+0.0015,i,f"{r[1]:.4f}",va="center",fontsize=7.6,
            weight="bold" if i<2 else "normal")
ax.axvline(0.4685,color="#111",lw=1.2,ls="--")
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in rows],fontsize=8)
ax.invert_yaxis(); ax.set_xlim(0.418,0.474)
ax.set_xlabel("판 ρ (점선 = 없이 · 막대 오차 = 씨앗 SD)")
ax.set_title("진짜가 위약보다 나쁘다\n신호 몫 -0.0132 = 문턱의 2.9배 음수",
             loc="left",fontsize=9,weight="bold")

# ── 2. 원인 ① 날짜 대리변수 --- 반증
ax=fig.add_subplot(gs[0,1])
D={"시장팝업":(0.983,5,126),"펀딩":(0.918,6,529),"아이돌":(0.845,6,51),
   "팝업":(0.534,84,65),"게임":(0.423,305,180),"모바일":(0.309,778,441),
   "만화":(-0.251,1003,258),"도서":(0.13,107,163),"세계애니":(0.118,481,300),
   "애니":(0.099,1055,606),"웹툰":(0.071,1594,650)}
for k,(r,u,w) in D.items():
    c="#b3392b" if u<=6 else "#2b4c7e"
    ax.scatter(u,abs(r),s=60+w/6,c=c,zorder=3,edgecolor="w",lw=1.1)
    dx=(10,0) if k not in ("애니","도서") else (10,-6)
    ax.annotate(k,(u,abs(r)),textcoords="offset points",xytext=dx,va="center",
                fontsize=7.4)
ax.axhline(0.5,color="#111",lw=1.1,ls="--")
ax.text(1400,0.52,"|상관| 0.5",fontsize=7.2,ha="right")
ax.set_xscale("log"); ax.set_xlim(3,3000); ax.set_ylim(0,1.05)
ax.set_xlabel("그 도메인에서 축의 고유값 수 (로그)")
ax.set_ylabel("|축 ↔ 날짜| 스피어만")
ax.text(4.5,0.18,"붉은 점 = 고유값 6 이하\n(날짜가 연 단위라 상관이 뜻 없다)",
        fontsize=7.2,color="#b3392b")
ax.set_title("날짜 대리변수가 아니다\n판 기여 1위 웹툰이 0.071 · 중앙값 0.309",
             loc="left",fontsize=9,weight="bold")

# ── 3. 후보 넷을 지우고 남은 하나
ax=fig.add_subplot(gs[0,2])
rows=[("완전관측 1열\n(노트 742·747)",0.0061,0.0006,"#7f8896"),
      ("덮음 0.53\n(노트 747)",0.0068,0.0034,"#7f8896"),
      ("날짜 동률\n(노트 749)",0.0107,0.0032,"#7f8896"),
      ("극단 동률\n(노트 749)",0.0042,0.0050,"#7f8896"),
      ("덮음 0.27\n(노트 747)",0.0157,0.0019,"#d4a11a"),
      ("**마스크가 유보를\n가른다**(노트 752)".replace("**",""),0.0308,0.0002,"#b3392b")]
y=np.arange(len(rows))
ax.barh(y,[r[1] for r in rows],0.62,color=[r[3] for r in rows],
        xerr=[3*r[2] for r in rows],error_kw=dict(lw=1.0,ecolor="#333"))
for i,r in enumerate(rows):
    ax.text(r[1]+0.0009,i,f"{r[1]:.4f}",va="center",fontsize=7.6,
            weight="bold" if i==len(rows)-1 else "normal")
ax.axvline(0.0302,color="#b3392b",lw=1.6,ls="--")
ax.text(0.0302,-0.85,"노트 745 가 설명해야 했던 값\n0.0302",color="#b3392b",
        fontsize=7.4,ha="center")
ax.axvline(0.0045,color="#555",lw=1.0,ls=":")
ax.text(0.0045,5.75,"판 2σ",fontsize=7.0,color="#555",ha="center")
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in rows],fontsize=7.6)
ax.invert_yaxis(); ax.set_xlim(0,0.036)
ax.set_xlabel("쓰레기 1열의 판 비용 (오차 3σ)")
ax.set_title("후보 넷을 지우고 남은 하나\n13.8σ --- 유보 213행(6.1%)이 마스크 0 인 것만으로",
             loc="left",fontsize=9,weight="bold")
fig.savefig("paper/steps/147_nopath/figs/nopath.pdf",bbox_inches="tight")
print("그림 저장")
