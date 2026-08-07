import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
plt.rcParams.update({"font.family":"Apple SD Gothic Neo","font.size":8.5,
                     "axes.spines.top":False,"axes.spines.right":False,
                     "axes.unicode_minus":False})
# (자카드, 부호일치/9, 채점 유보행)
AG={"애니":(0.833,8,606),"시장팝업":(0.75,8,126),"웹툰":(0.667,8,650),
    "모바일":(0.6,7,441),"만화":(0.5,6,258),"세계애니":(0.5,5,300),
    "펀딩":(0.25,3,529),"게임":(0.143,3,180)}
# 고른 소스 수(자기 제외)
A={"세계애니":7,"애니":6,"모바일":5,"펀딩":5,"게임":4,"만화":3,"시장팝업":3,
   "웹툰":2,"도서":0,"아이돌":0,"팝업":0}
B={"만화":6,"팝업":6,"도서":5,"세계애니":5,"애니":5,"펀딩":5,"게임":4,
   "시장팝업":4,"모바일":3,"웹툰":3,"아이돌":1}
fig=plt.figure(figsize=(11.0,4.0))
gs=fig.add_gridspec(1,2,width_ratios=[1.0,1.15],wspace=0.28)

# ── 1. 일치도 대 채점 행수
ax=fig.add_subplot(gs[0,0])
for k,(j,s,n) in AG.items():
    c="#2b4c7e" if j>=0.5 else "#b3392b"
    ax.scatter(n,j,s=170,c=c,zorder=3,edgecolor="w",lw=1.2)
    ax.annotate(f"{k} {s}/9",(n,j),textcoords="offset points",xytext=(0,11),
                ha="center",fontsize=7.4)
ax.axhline(0.5,color="#111",lw=1.0,ls="--")
ax.text(660,0.52,"자카드 0.5",fontsize=7.2,color="#333",ha="right")
ax.set_xlim(60,760); ax.set_ylim(0,1.0)
ax.set_xlabel("그 목표의 유보 채점 행수")
ax.set_ylabel("두 행렬이 고른 소스의 자카드")
ax.set_title("얇은 칸이 잡음이다 --- 전부가 잡음은 아니다\n부호 일치 전체 48/72 = 0.667 · 칸 값 스피어만 0.429",
             loc="left",fontsize=9,weight="bold")

# ── 2. 고른 소스 수: 앞→뒤 대 전부→유보
ax=fig.add_subplot(gs[0,1])
ks=sorted(B,key=lambda k:-(B[k]-A.get(k,0)))
y=np.arange(len(ks))
ax.barh(y-0.2,[A.get(k,0) for k in ks],0.36,color="#b3392b",
        label="앞(<2024) → 뒤(2024)  · 누출 없음 · 노트 728 이 쓴 것")
ax.barh(y+0.2,[B[k] for k in ks],0.36,color="#a8b4c8",
        label="학습 전부 → 유보  · 누출본 · 노트 727 이 쓴 것")
for i,k in enumerate(ks):
    for off,v in ((-0.2,A.get(k,0)),(0.2,B[k])):
        ax.text(v+0.12,i+off,str(v),va="center",fontsize=7.4,
                weight="bold" if off<0 else "normal")
for i,k in enumerate(ks):
    if A.get(k,0)==0:
        ax.text(-0.35,i-0.2,"자기만",va="center",ha="right",fontsize=7.2,
                color="#b3392b",weight="bold")
ax.set_yticks(y); ax.set_yticklabels(ks); ax.invert_yaxis()
ax.set_xlim(-1.5,8.2)
ax.set_xlabel("그 목표가 고른 소스 도메인 수 (자기 제외)")
ax.legend(fontsize=7.2,loc="lower right",frameon=False)
ax.set_title("풀 붕괴는 실체가 아니라 창의 산물이었다\n도서·아이돌·팝업이 0 개를 고른 것은 2024 한 해로 채점했기 때문",
             loc="left",fontsize=9,weight="bold")
fig.savefig("paper/steps/144_shrinkpool/figs/agree.pdf",bbox_inches="tight")
print("그림 저장")
