import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
plt.rcParams.update({"font.family":"Apple SD Gothic Neo","font.size":8.5,
                     "axes.spines.top":False,"axes.spines.right":False,
                     "axes.unicode_minus":False})
fig=plt.figure(figsize=(11.6,4.2))
gs=fig.add_gridspec(1,3,width_ratios=[1.1,1.0,1.0],wspace=0.33)

# ── 1. 도메인별 원천 열 → 조인 통과
ax=fig.add_subplot(gs[0,0])
D={"웹툰":(17,17,11,5,650),"애니":(22,21,14,7,606),"펀딩":(19,19,12,5,529),
   "모바일":(18,17,11,3,441),"세계애니":(22,22,13,4,300),"만화":(18,18,9,4,258),
   "게임":(20,19,10,3,180),"도서":(19,18,10,5,163)}
ks=list(D); y=np.arange(len(ks))
ax.barh(y,[D[k][0] for k in ks],0.66,color="#dfe4ea",label="원천 열 (채움≥10%)")
ax.barh(y,[D[k][2] for k in ks],0.66,color="#6d8ab8",label="느슨한 게이트 통과")
ax.barh(y,[D[k][3] for k in ks],0.66,color="#b3392b",label="**조인 게이트 통과**".replace("**",""))
for i,k in enumerate(ks):
    ax.text(D[k][3]+0.4,i,str(D[k][3]),va="center",fontsize=8.6,weight="bold",
            color="#b3392b")
    ax.text(D[k][0]+0.4,i,f"{D[k][0]}",va="center",fontsize=7.4,color="#666")
ax.axvline(3,color="#111",lw=1.3,ls="--")
ax.text(3,-0.85,"문턱 3",fontsize=7.6,ha="center")
ax.set_yticks(y); ax.set_yticklabels([f"{k} ({D[k][4]})" for k in ks],fontsize=7.8)
ax.invert_yaxis(); ax.set_xlim(0,25)
ax.set_xlabel("열 수 (괄호는 유보 채점 행수)")
ax.legend(fontsize=6.9,loc="lower right",frameon=False)
ax.set_title("8/8 도메인이 문턱을 넘었다\n게이트를 두 번 조여도 3~7 개가 남는다",
             loc="left",fontsize=9,weight="bold")

# ── 2. 게이트가 떨어뜨린 것
ax=fig.add_subplot(gs[0,1])
rows=[("원천 열 (여덟 도메인 합)",155,"#dfe4ea"),
      ("- 이미 쓰는 것",4,"#c8c8c8"),
      ("- 결과성 (라벨 포함)",41,"#b3392b"),
      ("- 텍스트 (T5 가 확정)",25,"#d4a11a"),
      ("- 날짜 (cal_* 에 있다)",13,"#7f8896"),
      ("- 이름만 다른 것",11,"#7f8896"),
      ("= 후보 열",36,"#2b4c7e")]
y=np.arange(len(rows))
ax.barh(y,[r[1] for r in rows],0.6,color=[r[2] for r in rows])
for i,r in enumerate(rows):
    ax.text(r[1]+2,i,str(r[1]),va="center",fontsize=8.2,
            weight="bold" if i in (0,len(rows)-1) else "normal")
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in rows],fontsize=7.6)
ax.invert_yaxis(); ax.set_xlim(0,180)
ax.set_xlabel("열 수 (도메인별 합 · 중복 포함)")
ax.text(52,5.6,"🔴 눈으로 읽어 넷을 더 잡았다\nis_ending · n_episode · n_chapter · n_volume\n(최종 편수는 결과다)".replace("🔴 ",""),
        fontsize=7.0,color="#b3392b")
ax.set_title("정규식만으로는 라벨이 샜다\ny_ 접두 넷이 첫 게이트를 통과했다",
             loc="left",fontsize=9,weight="bold")

# ── 3. 🔴 이미 된 일 --- 그리고 안 훑은 세 도메인
ax=fig.add_subplot(gs[0,2]); ax.axis("off")
ax.text(0.0,0.98,"노트 321·324·348 이 이미 했다",fontsize=9.6,weight="bold",
        color="#b3392b",va="top")
steps=[("후보 43","축 파일 + 원천 레코드에서 검사 ①③④ 통과"),
       ("- 출처가 32 막음 (74%)","사후 라벨 · 스냅샷 · 식별자 · 끝나야 붙는 것\n"
        "🔴 사후 의심 --- 쌓인다: n_episode · n_tag".replace("🔴 ","")),
       ("= 11 → 10 만듦","검사 ② (시간 조각 다섯 부호) 5/5"),
       ("묶음으로 판 -0.0027","서랍에 넣었다 (노트 324)"),
       ("갈라서 넷만 +0.0068","12/12 · 펀딩 +0.0521 · 모바일 +0.0135 (노트 348)\n"
        "= loop.RAW_KEEP")]
yy=0.90
for h,b2 in steps:
    ax.text(0.02,yy,h,fontsize=8.2,weight="bold",va="top")
    ax.text(0.05,yy-0.055,b2,fontsize=6.9,va="top",color="#555")
    yy-=0.055+0.052*(1+b2.count("\n")*1.1)
ax.text(0.0,0.40,"🔴 내가 '가장 값 있는 발견' 으로 꼽은\n     n_tag 가 이미 막힌 열이었다".replace("🔴 ",""),
        fontsize=8.4,weight="bold",color="#b3392b",va="top")
ax.text(0.0,0.27,"그래도 남는 것 --- SPEC 이 안 훑은 세 도메인",fontsize=9,
        weight="bold",color="#2b4c7e",va="top")
ax.text(0.03,0.19,"만화 3열 (format · is_adult · n_author)\n"
        "게임 3열 (is_free · n_dlc · n_platform)\n"
        "도서 5열 (book_format · pages · 폭 · 높이 · 무게)\n"
        "= 11열 · 유보 채점 601 = 17.8%",fontsize=7.4,va="top")
ax.text(0.0,0.02,"규율: 세기 전에 그 일을 이미 한 코드를 찾는다",fontsize=7.6,
        weight="bold",color="#111",va="top")
fig.savefig("paper/steps/154_sametwentynine/figs/same29.pdf",bbox_inches="tight")
print("그림 저장")
