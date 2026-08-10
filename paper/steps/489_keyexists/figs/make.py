#!/usr/bin/env python3
# 노트 904 그림 — 🔴 손 전사 금지: 값은 전부 산출물 `runners/out904_xtab.json` 에서 **읽는다**.
#   fig1 (a) A∧T1 21 의 형 × 분모 교차표 — 대각선이 비어 있다
#        (b) (형≠d) ∧ (분모=D3) 을 네 모집단에서 — 0 은 A 등급에만 있다
#   fig2 (a) 팝업 유보 65 의 되짚기 갈래 (b) 12 A짝의 비결측(D1) 대 D3 덮음
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

E = json.loads((ROOT / "runners/out904_xtab.json").read_text())
X = E["4-가 형 × 분모 교차표"]
AX = E["4-나 팝업 축 파일"]

TYPES = ["b", "c", "l", "d"]
DENS = ["D1", "D3"]
POPS = ["A∧T1", "A 전량(T2 포함)", "T1 전량", "전량"]

# ── fig1 ────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(1, 2, figsize=(11.6, 4.2))

# (a) A∧T1 교차표 — 옆에 105 전량을 흐리게 겹친다
def grid(pop):
    g = np.zeros((len(TYPES), len(DENS)))
    for k, v in X[f"{pop} — 형 × 분모"].items():
        t, d = k.split("×")
        g[TYPES.index(t), DENS.index(d)] = v
    return g

gA, gAll = grid("A∧T1"), grid("전량")
im = ax[0].imshow(gA, cmap="Blues", vmin=0, vmax=gA.max())
for i in range(len(TYPES)):
    for j in range(len(DENS)):
        ax[0].text(j, i, f"{int(gA[i, j])}\n({int(gAll[i, j])})",
                   ha="center", va="center", fontsize=11,
                   color="white" if gA[i, j] > gA.max() * 0.6 else "black")
ax[0].set_xticks(range(len(DENS)), DENS)
ax[0].set_yticks(range(len(TYPES)), [f"형 {t}" for t in TYPES])
ax[0].set_title(f"(a) A∧T1 {X['A∧T1 — 수(분모)']}짝의 형 × 분모\n"
                f"괄호는 105짝 전량 — (형≠d)∧D3 칸이 비었다", fontsize=10)
ax[0].set_xlabel("분모 딱지 (D1 원천 레코드 · D3 판 채점 유보)")
fig.colorbar(im, ax=ax[0], fraction=0.046)

# (b) 핵심 수를 네 모집단에서
vals = [X[f"🔴 {p} — (형≠d) ∧ (분모=D3)"] for p in POPS]
den = [X[f"{p} — 수(분모)"] for p in POPS]
c = ["#c0392b" if v == 0 else "#2c7fb8" for v in vals]
b = ax[1].bar(range(len(POPS)), vals, color=c)
for i, (v, d) in enumerate(zip(vals, den)):
    ax[1].text(i, v + 1.2, f"{v} / {d}", ha="center", fontsize=11)
ax[1].set_xticks(range(len(POPS)), [f"{p}\n(n={d})" for p, d in zip(POPS, den)],
                 fontsize=9)
ax[1].set_ylabel("(형 ≠ d) ∧ (분모 = D3) 인 짝 수")
ax[1].set_ylim(0, max(vals) * 1.25 + 2)
ax[1].set_title("(b) 0 은 A 등급에만 있다 — 자료 전체의 성질이 아니다", fontsize=10)

fig.tight_layout()
fig.savefig(HERE / "fig1.pdf")

# ── fig2 ────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(1, 2, figsize=(12.2, 4.2))

R = AX["D3 되짚기"]
lab = ["data/records\n(원천 레코드)", "data/market_records\n(시장팝업)", "못 붙은 키"]
val = [R["data/records 에 붙은 수"], R["data/market_records 에 붙은 수"],
       R["🔴 못 붙은 수"]]
ax[0].bar(lab, val, color=["#2c7fb8", "#7fcdbb", "#c0392b"])
for i, v in enumerate(val):
    ax[0].text(i, v + 0.9, str(v), ha="center", fontsize=12)
ax[0].set_ylabel("유보 키 수")
ax[0].set_ylim(0, R["유보 키 수(분모)"] * 1.15)
ax[0].set_title(f"(a) 팝업 판 채점 유보 {R['유보 키 수(분모)']} 키의 되짚기\n"
                f"「원리상 불가능」이라던 자리 — 못 붙은 키 {R['🔴 못 붙은 수']}",
                fontsize=10)

C = AX["🔴 12 A∧T1 팝업 짝의 D3 덮음"]
names = list(C)
short = [n.split(".")[-1] for n in names]
nz = [C[n]["비결측(D1)"] for n in names]
cv = [C[n]["🔴 D3 덮음(비결측 ∧ 유보)"] for n in names]
o = np.argsort(nz)[::-1]
y = np.arange(len(names))
ax[1].barh(y, [nz[i] for i in o], color="#dbe9f6", label="비결측 (분모 D1 = %d)"
           % C[names[0]]["D1 원천 레코드(분모)"])
ax[1].barh(y, [cv[i] for i in o], color="#2c7fb8", label="D3 덮음 (비결측 ∧ 유보)")
ax[1].set_yticks(y, [short[i] for i in o], fontsize=8)
ax[1].invert_yaxis()
ax[1].set_xlabel("레코드 수")
ax[1].legend(fontsize=8, loc="lower right")
ax[1].set_title("(b) 12 A∧T1 팝업 짝 — 「못 셌다」가 수가 됐다\n"
                "덮음이 비결측과 같은 짝 %d 개"
                % AX["🔴 D3 덮음 요약"]["🔴 덮음이 비결측과 같은 짝 수"], fontsize=10)

fig.tight_layout()
fig.savefig(HERE / "fig2.pdf")
print("fig1.pdf · fig2.pdf 완료")
