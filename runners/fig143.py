import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
plt.rcParams.update({"font.family":"Apple SD Gothic Neo","font.size":8.5,
                     "axes.spines.top":False,"axes.spines.right":False,
                     "axes.unicode_minus":False})
# 도메인: (계열안, 계열밖, 밖·맞춤, 문턱, 계열, 형제행, 계열밖행)
D={"팝업":(0.0663,-0.1690,-0.1944,0.0324,"한국 IP",3115,17070),
   "만화":(0.0435,-0.0322,-0.0355,0.0163,"일본 만화·애니",5426,10252),
   "펀딩":(0.0165,-0.0752,-0.0186,0.0114,"그밖",80,16019),
   "도서":(-0.0903,-0.1485,-0.1214,0.0205,"그밖",2358,13741),
   "애니":(0.0570,0.0600,0.0600,0.0106,"일본 만화·애니",8291,7387),
   "세계애니":(0.0030,0.0155,0.0155,0.0151,"일본 만화·애니",8423,7255),
   "웹툰":(-0.0234,-0.0027,0.0094,0.0102,"한국 IP",196,15325),
   "시장팝업":(-0.0748,-0.0544,-0.0170,0.0233,"한국 IP",3009,15214),
   "모바일":(-0.0478,-0.0012,0.0792,0.0124,"앱·게임",259,16101),
   "아이돌":(-0.4529,-0.3380,-0.3236,0.0366,"한국 IP",3076,15201),
   "게임":(-0.1857,0.0123,-0.0074,0.0195,"앱·게임",1558,15161)}
FAM={"일본 만화·애니":"#2b4c7e","한국 IP":"#b3392b","앱·게임":"#d4a11a","그밖":"#7f8896"}
fig=plt.figure(figsize=(11.4,4.2))
gs=fig.add_gridspec(1,3,width_ratios=[1.2,1.0,1.0],wspace=0.33)

# ── 1. 안 − 밖·맞춤, 문턱과 함께
ax=fig.add_subplot(gs[0,0])
ks=sorted(D,key=lambda k:-(D[k][0]-D[k][2]))
y=np.arange(len(ks))
for i,k in enumerate(ks):
    ins,_,mt,thr,fam,_,_=D[k]
    diff=ins-mt
    ax.barh(i,diff,0.58,color=FAM[fam])
    ax.plot([thr,thr],[i-0.32,i+0.32],color="#111",lw=1.6)
    ax.plot([-thr,-thr],[i-0.32,i+0.32],color="#111",lw=1.6)
    ax.text(diff+(0.012 if diff>0 else -0.012),i,f"{diff:+.4f}",va="center",
            ha="left" if diff>0 else "right",fontsize=7.2)
ax.axvline(0,color="#111",lw=1.2)
ax.set_yticks(y); ax.set_yticklabels(ks); ax.invert_yaxis()
ax.set_xlim(-0.24,0.32)
ax.set_xlabel("계열 안 − 계열 밖·행수 맞춤  (검은 선 = 그 도메인 문턱)")
ax.set_title("문턱 밖 양수는 4/11 이고 계열로 안 묶인다\n색 = 계열 · JP 셋은 1/3",
             loc="left",fontsize=9,weight="bold")

# ── 2. 계열 안 대 밖·맞춤
ax=fig.add_subplot(gs[0,1])
for k,(ins,_,mt,thr,fam,_,_) in D.items():
    ax.scatter(mt,ins,s=150,c=FAM[fam],zorder=3,edgecolor="w",lw=1.2)
    ax.annotate(k,(mt,ins),textcoords="offset points",xytext=(0,10),
                ha="center",fontsize=7.2)
lim=[-0.36,0.13]
ax.plot(lim,lim,"--",color="#999",lw=1.0)
ax.axhline(0,color="#111",lw=0.9); ax.axvline(0,color="#111",lw=0.9)
ax.text(-0.30,0.08,"대각선 위 = 계열이 이긴다",fontsize=7.4,color="#333")
ax.set_xlim(*lim); ax.set_ylim(*lim)
ax.set_xlabel("계열 밖 · 행수 맞춤"); ax.set_ylabel("계열 안")
ax.set_title("같은 계열 안에서도 갈린다\n만화 이기고 애니·세계애니 진다",
             loc="left",fontsize=9,weight="bold")

# ── 3. 비대칭 --- 팝업의 두 방향
ax=fig.add_subplot(gs[0,2])
rows=[("팝업 ← 한국 IP",0.0663,"#b3392b"),
      ("팝업 ← 일본 만화·애니 등",-0.1944,"#2b4c7e"),
      ("애니 ← 일본 만화·애니",0.0570,"#2b4c7e"),
      ("애니 ← 그 밖 전부",0.0600,"#7f8896")]
y=np.arange(len(rows))
ax.barh(y,[r[1] for r in rows],0.58,color=[r[2] for r in rows])
for i,r in enumerate(rows):
    ax.text(r[1]+(0.008 if r[1]>0 else -0.008),i,f"{r[1]:+.4f}",va="center",
            ha="left" if r[1]>0 else "right",fontsize=7.6,weight="bold")
ax.axvline(0,color="#111",lw=1.2)
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in rows],fontsize=8)
ax.invert_yaxis(); ax.set_xlim(-0.25,0.13)
ax.set_xlabel("그 도메인 유보 예보 품질")
ax.set_title("도움 관계가 비대칭이다\n팝업은 가리는데 애니는 안 가린다",
             loc="left",fontsize=9,weight="bold")
fig.savefig("paper/steps/143_nofamily/figs/nofamily.pdf",bbox_inches="tight")
print("그림 저장")
