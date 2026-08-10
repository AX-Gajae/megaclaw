# -*- coding: utf-8 -*-
"""그림 1 — 도메인이 버는 양 대 판이 보는 양(노트 888 병)."""
import json, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager, rcParams

for cand in ("AppleSDGothicNeo", "Apple SD Gothic Neo", "NanumGothic"):
    try:
        font_manager.findfont(cand, fallback_to_default=False); rcParams["font.family"] = cand; break
    except Exception: pass
rcParams["axes.unicode_minus"] = False

REQ = {"웹툰":0.0261,"애니":0.0280,"펀딩":0.0321,"모바일":0.0385,"영화":0.0418,
       "세계애니":0.0566,"만화":0.0658,"게임":0.0944,"도서":0.1042,
       "시장팝업":0.1348,"팝업":0.2613,"아이돌":0.3331}
W = {k: 0.0045/v for k, v in REQ.items()}
r = json.load(open("/Users/ax/world_model/runners/out888_speck.json"))
d1, d2 = r["팔"]["K=1"]["도메인"], r["팔"]["K=2"]["도메인"]
rows = [(k, d2[k]-d1[k], W[k], (d2[k]-d1[k])*W[k]) for k in REQ if k in d1 and k in d2]
rows.sort(key=lambda x: -x[1])
names = [x[0] for x in rows]; dom = [x[1] for x in rows]; brd = [x[3] for x in rows]

fig, ax = plt.subplots(1, 2, figsize=(7.4, 3.5), sharey=True)
y = range(len(names))
ax[0].barh(list(y), dom, color=["#2a6f6f" if v>0 else "#a33" for v in dom])
ax[0].set_title("도메인 안에서 번 양  (K=2 − K=1)", fontsize=9)
ax[0].axvline(0, color="k", lw=.6)
ax[1].barh(list(y), brd, color=["#2a6f6f" if v>0 else "#a33" for v in brd])
ax[1].set_title("판에 실제로 실린 양  (× 가중)", fontsize=9)
ax[1].axvline(0, color="k", lw=.6)
ax[1].axvline(0.0045, color="#888", lw=.8, ls="--")
ax[1].text(0.0045, len(names)-0.6, " 판 문턱 2σ", fontsize=7, color="#666", va="top")
for a in ax:
    a.set_yticks(list(y)); a.set_yticklabels(names, fontsize=8)
    a.tick_params(axis="x", labelsize=7); a.invert_yaxis()
    for s in ("top","right"): a.spines[s].set_visible(False)
ax[0].annotate("아이돌 +0.0274\n(도메인 1위)", xy=(dom[0], 0), xytext=(dom[0]*0.45, 2.4),
               fontsize=7.5, color="#2a6f6f",
               arrowprops=dict(arrowstyle="->", color="#2a6f6f", lw=.7))
ax[1].annotate("같은 팔인데\n+0.00037", xy=(brd[names.index("아이돌")], names.index("아이돌")),
               xytext=(0.0006, 3.2), fontsize=7.5, color="#a33",
               arrowprops=dict(arrowstyle="->", color="#a33", lw=.7))
fig.suptitle("특기 칸을 하나 더 주면 — 버는 곳과 보이는 곳이 다르다", fontsize=10.5, y=1.0)
fig.tight_layout()
fig.savefig(sys.argv[1] if len(sys.argv)>1 else "fig1.pdf", bbox_inches="tight")
print("저장", sys.argv[1] if len(sys.argv)>1 else "fig1.pdf")
