import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
plt.rcParams.update({"font.family":"Apple SD Gothic Neo","font.size":8.5,
                     "axes.spines.top":False,"axes.spines.right":False,
                     "axes.unicode_minus":False})
fig=plt.figure(figsize=(11.4,4.2))
gs=fig.add_gridspec(1,3,width_ratios=[1.15,1.0,0.95],wspace=0.34)

# ── 1. 후보 다섯의 설명력
ax=fig.add_subplot(gs[0,0])
rows=[("① 방향 뒤집힘\n갈림 5/11 · 갈림↔기여 +0.637",0.0,"#7f8896"),
      ("② 결측 무늬\n앞채움 뒤에도 남았다",0.0,"#7f8896"),
      ("③ 거칠기\n고유 1594→4 폭 0.005",0.0,"#7f8896"),
      ("④ 공변량 이동\n겹침 0.074→0.996",0.59,"#2b7e4c"),
      ("⑤ 감쇠\n스피어만 +0.009 (p=0.98)",0.0,"#7f8896"),
      ("〔재기 전 사망〕라벨 수준\n유보 안 순위 채점이라 무관",0.0,"#c0a0c8")]
y=np.arange(len(rows))
ax.barh(y,[r[1] for r in rows],0.58,color=[r[2] for r in rows])
for i,r in enumerate(rows):
    ax.text(max(r[1],0)+0.012,i,("설명 59%" if r[1]>0 else "설명 0"),
            va="center",fontsize=7.8,weight="bold" if r[1]>0 else "normal",
            color="#2b7e4c" if r[1]>0 else "#555")
ax.axvline(0,color="#111",lw=1.2)
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in rows],fontsize=7.4)
ax.invert_yaxis(); ax.set_xlim(0,0.86)
ax.set_xlabel("해로움 중 설명한 몫")
ax.set_title("후보 다섯 중 하나만 부분 성공\n남은 41% 는 기제 미상으로 닫는다",
             loc="left",fontsize=9,weight="bold")

# ── 2. 감쇠는 무관하다
ax=fig.add_subplot(gs[0,1])
D={"팝업":(0.168,-0.0034,1),"아이돌":(0.079,0.0008,2),"웹툰":(0.060,-0.0397,3),
   "애니":(0.057,0.0032,4),"세계애니":(0.040,-0.0061,5),"만화":(0.025,0.0060,6),
   "모바일":(0.011,0.0110,7),"게임":(0.008,-0.0060,8),"펀딩":(-0.065,-0.0049,9),
   "시장팝업":(-0.087,0.0446,10),"도서":(-0.090,-0.0546,11)}
for k,(a,s,r) in D.items():
    c="#b3392b" if s<-0.02 else "#2b4c7e"
    ax.scatter(a,s,s=150,c=c,zorder=3,edgecolor="w",lw=1.2)
    dy=11 if k not in ("애니","게임","펀딩") else -14
    ax.annotate(f"{k}({r})",(a,s),textcoords="offset points",xytext=(0,dy),
                ha="center",fontsize=7.0)
ax.axhline(0,color="#111",lw=1.1); ax.axvline(0,color="#111",lw=1.1)
ax.axhline(-0.0045,color="#555",lw=1.0,ls=":")
ax.set_xlim(-0.115,0.20); ax.set_ylim(-0.068,0.058)
ax.set_xlabel("감쇠량  |학습 상관| - |유보 상관|  (괄호는 감쇠 순위)")
ax.set_ylabel("도메인 신호 몫")
ax.text(-0.105,0.045,"스피어만 +0.009 (p=0.98)\n가장 해로운 둘이 양극단에 있다",
        fontsize=7.4,color="#b3392b")
ax.set_title("감쇠도 아니다\n웹툰 3위 · 도서 11위",loc="left",fontsize=9,weight="bold")

# ── 3. 아는 것과 모르는 것
ax=fig.add_subplot(gs[0,2]); ax.axis("off")
ax.text(0.0,0.97,"아는 것",fontsize=10,weight="bold",color="#2b7e4c",va="top")
know=["전국 시간축은 판을 해친다\n  신호 몫 -0.0079 (문턱의 1.8배)",
      "그 59% 가 창별 분포 불일치다\n  겹침 0.074 → 0.996 로 -0.0192→-0.0079",
      "남은 것은 웹툰(-0.0397)·도서(-0.0546)\n  두 도메인에 몰려 있다",
      "채점에서만 빼면 +0.0032 (문턱 안)",
      "그 둘은 분포가 맞아도 해롭다\n  겹침 0.991 · 0.962"]
yy=0.90
for t in know:
    ax.text(0.03,yy,"· "+t,fontsize=7.6,va="top")
    yy-=0.088*(1+t.count("\n")*0.55)
ax.text(0.0,0.36,"모르는 것",fontsize=10,weight="bold",color="#b3392b",va="top")
ax.text(0.03,0.29,"· 그 둘에서 무엇이 해로운가\n  — 후보 다섯이 다 아니다",
        fontsize=7.6,va="top")
ax.text(0.0,0.15,"그래서 '왜' 를 닫고\n'무엇을 대신 쓰나' 로 간다",fontsize=8.6,
        weight="bold",va="top")
ax.text(0.03,0.03,"사전등록 규칙 (다) 가 그렇게 적혀 있었다",fontsize=7.2,
        color="#555",va="top")
fig.savefig("paper/steps/150_fivedoors/figs/fivedoors.pdf",bbox_inches="tight")
print("그림 저장")
