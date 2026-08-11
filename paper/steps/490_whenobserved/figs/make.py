#!/usr/bin/env python3
# 노트 905 그림 — 🔴 손 전사 금지: 값은 전부 산출물 `runners/out905_cond.json` 에서 **읽는다**.
#   fig1 (a) 66짝의 식1 × 식3 교차표 — 한 칸이 51 이다
#        (b) 짝마다 「예가 아닌 조건」의 조합 — 두 조합뿐이고 둘 다 식3 을 품는다
#   fig2 (a) 팔 ㄴ — 조건별 실효 자유도(도메인 단위) 대 짝 수 105
#        (b) 「모른다」 51 을 두 무리로: 도메인에 시점 필드가 없다 / 있는데 개입 열을 안 덮는다
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parents[4]
HERE = pathlib.Path(__file__).resolve().parent

for cand in ("AppleGothic", "Apple SD Gothic Neo", "NanumGothic", "Malgun Gothic"):
    if any(f.name == cand for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams["axes.unicode_minus"] = False

E = json.loads((ROOT / "runners/out905_cond.json").read_text())
GA = E["3-가 팔 ㄱ · 66짝은 식3 하나에서만 떨어지는가"]
GB = E["3-나 「모른다」는 무엇을 안 적어 뒀는가 (열 이름)"]
GB2 = E["3-나′ 🔴 사후 집계 — 「모른다」 안의 두 무리 (예측 아님)"]
GC = E["3-다 팔 ㄴ · 조건의 판정 단위는 짝인가 도메인인가"]

XT = GA["🔴 식1 × 식3 교차표(아무도 안 센 수)"]["표"]
N66 = GA["🔴 수(분모)"]

# ── fig1 ────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(1, 2, figsize=(11.6, 4.2))

R = ["예", "아니오"]          # 식1
C = ["예", "아니오", "모른다"]  # 식3
g = np.zeros((len(R), len(C)))
for k, v in XT.items():
    a, b = k.split(" × ")
    g[R.index(a.split("=")[1]), C.index(b.split("=")[1])] = v
ax[0].imshow(g, cmap="Oranges", vmin=0, vmax=g.max())
for i in range(len(R)):
    for j in range(len(C)):
        ax[0].text(j, i, f"{int(g[i, j])}", ha="center", va="center",
                   fontsize=15, fontweight="bold",
                   color=("white" if g[i, j] > g.max() * 0.6 else "0.2"))
ax[0].set_xticks(range(len(C)), [f"식3={c}" for c in C])
ax[0].set_yticks(range(len(R)), [f"식1={r}" for r in R])
ax[0].set_title(f"(a) (형≠d)∧D3 인 {int(N66)}짝 — 식1 × 식3\n"
                "◆ 식3 에 「예」인 칸이 아예 없다", fontsize=10)

combo = GA["🔴 짝마다 「예가 아닌 조건」의 조합 분포"]
ks = sorted(combo, key=lambda k: -combo[k])
b = ax[1].barh(range(len(ks)), [combo[k] for k in ks],
               color=["#c0392b" if k == "식3" else "#7f8c8d" for k in ks])
ax[1].set_yticks(range(len(ks)), [f"「예」가 아닌 조건: {k}" for k in ks])
ax[1].invert_yaxis()
for r, k in zip(b, ks):
    ax[1].text(r.get_width() + 0.8, r.get_y() + r.get_height() / 2,
               f"{combo[k]}짝", va="center", fontsize=11, fontweight="bold")
ax[1].set_xlim(0, max(combo.values()) * 1.35)
ax[1].set_xlabel(f"짝 수 (분모 {int(N66)})")
ax[1].set_title("(b) 조합이 둘뿐이고 둘 다 식3 을 품는다\n"
                f"◆ 식3 **하나만** 걸리는 짝 {GA['🔴 식3 **하나만** 걸리는 짝 수']}", fontsize=10)
for s in ("top", "right"):
    ax[1].spines[s].set_visible(False)
fig.tight_layout()
fig.savefig(HERE / "fig1.pdf")
plt.close(fig)

# ── fig2 ────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(1, 2, figsize=(11.6, 4.2))

conds = ["식1", "식2", "식3", "식4", "형", "분모"]
dof = [GC["조건별"][c]["🔴 실효 자유도(도메인별 값 가짓수 합)"] for c in conds]
npair = GC["짝 수(분모)"]
ndom = GC["도메인 수(분모)"]
cols = ["#c0392b" if GC["조건별"][c]["🔴 도메인 안 상수인 도메인 수"] == ndom else "#34495e"
        for c in conds]
b = ax[0].bar(range(len(conds)), dof, color=cols)
ax[0].axhline(npair, ls="--", lw=1.2, color="#7f8c8d")
ax[0].text(len(conds) - 0.4, npair + 2, f"짝으로 세면 {npair}", ha="right",
           fontsize=9, color="#7f8c8d")
ax[0].axhline(ndom, ls=":", lw=1.2, color="#c0392b")
ax[0].text(-0.4, ndom + 2, f"도메인 {ndom}", fontsize=9, color="#c0392b")
for r, v in zip(b, dof):
    ax[0].text(r.get_x() + r.get_width() / 2, v + 1.5, str(v),
               ha="center", fontsize=10, fontweight="bold")
ax[0].set_xticks(range(len(conds)), conds)
ax[0].set_ylim(0, npair * 1.15)
ax[0].set_ylabel("실효 자유도 (도메인별 값 가짓수 합)")
ax[0].set_title("(a) 붉은 것은 12/12 도메인에서 상수 —\n"
                "◆ 105번 잰 게 아니라 12번 잰 것이다", fontsize=10)
for s in ("top", "right"):
    ax[0].spines[s].set_visible(False)

kA = "무리 ㄱ · 도메인에 시점 필드가 하나도 없다(「없다」)"
kB = "무리 ㄴ · 시점 필드는 있는데 개입 열을 안 덮는다(「안 적어 뒀다」)"
key = "식3 하나만 걸리고 모른다 인 짝 수"
vals = [GB2[kA][key], GB2[kB][key]]
labs = [f"도메인에 시점 필드가\n**하나도 없다**\n({', '.join(GB2[kA]['도메인'])})",
        f"시점 필드는 있는데\n**개입 열을 안 덮는다**\n({', '.join(GB2[kB]['도메인'])})"]
b = ax[1].bar([0, 1], vals, color=["#2c3e50", "#e67e22"], width=0.55)
for r, v in zip(b, vals):
    ax[1].text(r.get_x() + r.get_width() / 2, v + 0.6, f"{v}짝",
               ha="center", fontsize=12, fontweight="bold")
ax[1].set_xticks([0, 1], [l.replace("**", "") for l in labs], fontsize=8)
ax[1].set_ylim(0, max(vals) * 1.3)
ax[1].set_ylabel(f"짝 수 (합 {GB2['🔴 합(분모 대조)']})")
ax[1].set_title(f"(b) 「모른다」 {GB2['🔴 합(분모 대조)']}건은 한 덩어리가 아니다 — "
                f"이름 {GB['🔴 그 이름의 가짓수']}가지", fontsize=10)
for s in ("top", "right"):
    ax[1].spines[s].set_visible(False)
fig.tight_layout()
fig.savefig(HERE / "fig2.pdf")
plt.close(fig)
print("fig1.pdf fig2.pdf")
