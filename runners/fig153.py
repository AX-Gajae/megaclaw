import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle
plt.rcParams.update({"font.family":"Apple SD Gothic Neo","font.size":8.5,
                     "axes.spines.top":False,"axes.spines.right":False,
                     "axes.unicode_minus":False})
fig=plt.figure(figsize=(11.4,4.2))
gs=fig.add_gridspec(1,3,width_ratios=[1.0,1.05,1.05],wspace=0.30)

# ── 1. 벤 다이어그램 --- 교집합이 비어 있다
ax=fig.add_subplot(gs[0,0]); ax.axis("off")
ax.add_patch(Circle((0.36,0.52),0.30,fc="#2b4c7e",alpha=0.22,ec="#2b4c7e",lw=1.6))
ax.add_patch(Circle((0.66,0.52),0.22,fc="#b3392b",alpha=0.22,ec="#b3392b",lw=1.6))
ax.text(0.24,0.52,"장소 링크\n21",ha="center",va="center",fontsize=9.5,
        weight="bold",color="#2b4c7e")
ax.text(0.74,0.52,"방문객\n7",ha="center",va="center",fontsize=9.5,
        weight="bold",color="#b3392b")
ax.text(0.51,0.52,"0",ha="center",va="center",fontsize=17,weight="bold",color="#111")
ax.text(0.51,0.42,"교집합",ha="center",va="center",fontsize=7.6,color="#111")
ax.text(0.5,0.90,"core.engagement  579 행",ha="center",fontsize=9.5,weight="bold")
ax.text(0.5,0.13,"장소와 방문객을 다 가진 engagement = 0",ha="center",fontsize=8.6,
        weight="bold",color="#b3392b")
ax.text(0.5,0.04,"방문객 행의 venue_id 는 전부 NULL (48/48)",ha="center",fontsize=7.4,
        color="#555")
ax.set_xlim(0,1); ax.set_ylim(0,1)
ax.set_title("교집합이 비어 있다\nT7 문턱 20건 · 실측 0건",loc="left",fontsize=9,
             weight="bold")

# ── 2. 필요한 것과 있는 것
ax=fig.add_subplot(gs[0,1])
rows=[("T2 가 요구한 것\n시군구 고정 방문객 라벨",2028,"#111"),
      ("지금 있는 것\n(노트 771)",62,"#2b4c7e"),
      ("BQ 가 더 줄 수 있는 것\n(교집합)",0,"#b3392b"),
      ("대안 표 retail_sale_daily\nvenue 수",7,"#d4a11a")]
y=np.arange(len(rows))
ax.barh(y,[max(r[1],0.5) for r in rows],0.55,color=[r[2] for r in rows])
for i,r in enumerate(rows):
    ax.text(max(r[1],0.5)*1.5,i,f"{r[1]:,}",va="center",fontsize=9,weight="bold",
            color=r[2])
ax.set_xscale("log"); ax.set_xlim(0.4,6000)
from matplotlib.ticker import FixedFormatter, FixedLocator
ax.xaxis.set_major_locator(FixedLocator([1,10,100,1000]))
ax.xaxis.set_major_formatter(FixedFormatter(["1","10","100","1,000"]))
ax.xaxis.set_minor_locator(FixedLocator([]))
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in rows],fontsize=7.8)
ax.invert_yaxis()
ax.set_xlabel("행 수 / 장소 수 (로그)")
ax.set_title("62 에서 2,028 로 가는 길이 없다\nBQ 가 더 줄 수 있는 것은 0",
             loc="left",fontsize=9,weight="bold")

# ── 3. 버리는 근거 셋
ax=fig.add_subplot(gs[0,2]); ax.axis("off")
ax.text(0.0,0.97,"버리는 근거 셋",fontsize=10.5,weight="bold",color="#b3392b",va="top")
items=[("① 판에서 작다",
        "팝업 89 + 시장팝업 249\n= 유보 채점의 5.67% (노트 767)"),
       ("② 라벨이 안 자란다",
        "노트 635 전수 판독 --- 조직이 방문객을 안 센다\nBQ 적재도 48행 · 마지막 08-04 대 오늘 08-07\n(지연인지 멈춤인지 못 가른다)"),
       ("③ 장소와 방문객이 안 붙는다",
        "교집합 0 · 방문객 행의 venue_id 전부 NULL")]
yy=0.87
for h,b in items:
    ax.text(0.02,yy,h,fontsize=8.8,weight="bold",va="top",color="#111")
    ax.text(0.05,yy-0.075,b,fontsize=7.4,va="top",color="#444")
    yy-=0.075+0.075*(1+b.count("\n"))
ax.text(0.0,0.30,"→ 팝업 방문객 갈래를 파운데이션\n     목적에서 내린다",fontsize=9.6,
        weight="bold",va="top",color="#b3392b")
ax.text(0.03,0.17,"판에서 도메인을 빼는 것이 아니다 ---\n새 자료를 그 쪽으로 요청하지 않는다",
        fontsize=7.6,va="top",color="#555")
ax.text(0.0,0.06,"남은 길: 판의 두꺼운 도메인\n웹툰 650 · 애니 606 · 펀딩 529 · 모바일 441",
        fontsize=7.8,va="top",color="#2b4c7e",weight="bold")
fig.savefig("paper/steps/153_emptyjoin/figs/emptyjoin.pdf",bbox_inches="tight")
print("그림 저장")
