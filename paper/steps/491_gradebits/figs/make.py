#!/usr/bin/env python3
# 노트 906 그림 — 🔴 손 전사 금지: 값은 전부 산출물 `runners/out906_grade.json` 에서 **읽는다**.
#   fig1 (a) 복잡도 사다리 — 특징 집합 × 깊이 의 재대입 대 LODO 오류(T1 81)
#        (b) 비트 — H(등급) 과 조건별 상호정보. 「다섯 통계 전부」의 1.3842 는 암기 인공물이다
#   fig2 (a) W 코드 집합(5가지) → 등급 대응표. 섞인 칸이 0 이다
#        (b) 잔여 22짝의 도메인 분해
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

E = json.loads((ROOT / "runners/out906_grade.json").read_text())
D = E["1 분모 (조항 60 — 매 수마다 병기한다)"]
GA = E["3-가 팔 ㄱ · 등급은 무엇의 함수인가 (예측 아님 · §0 에서 이미 돌렸다)"]
GB = E["3-나 팔 ㄱ · 복잡도를 통제한 재현 (재대입 · LODO · 암기 상한)"]
GC = E["3-다 팔 ㄴ · 「등급 미사용」 형제 키가 등급을 복제하는가"]

N1 = D["T1 수(분모)"]

# ── fig1 ────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(1, 2, figsize=(11.8, 4.3))

SETS = ["F5 다섯 통계(전부)", "F4 도메인 뺀 넷", "F3 소수 쪽 뺀 넷(음성 대조)"]
COL = {"F5 다섯 통계(전부)": "#1f77b4", "F4 도메인 뺀 넷": "#2ca02c",
       "F3 소수 쪽 뺀 넷(음성 대조)": "#d62728"}
depths = sorted(GB[SETS[0]]["깊이별"], key=lambda s: int(s.split()[-1]))
xs = [int(s.split()[-1]) for s in depths]
for s in SETS:
    per = GB[s]["깊이별"]
    ax[0].plot(xs, [per[d]["재대입 오류"] for d in depths], "o--",
               color=COL[s], alpha=.55, label=f"{s} · 재대입")
    ax[0].plot(xs, [per[d]["🔴 LODO 오류"] for d in depths], "s-",
               color=COL[s], label=f"{s} · LODO")
ax[0].set_xticks(xs)
ax[0].set_xlabel("결정트리 깊이 (규칙의 표현력)")
ax[0].set_ylabel(f"틀린 짝 수 (분모 T1 {N1})")
ax[0].set_title(f"(a) 재대입은 0 까지 내려가고 LODO 는 {GB['F5 다섯 통계(전부)']['🔴 최소 LODO 오류']} 에서 멈춘다")
ax[0].legend(fontsize=7, ncol=1, loc="upper right")
ax[0].grid(alpha=.25)

ent = GA[f"엔트로피 · T1 {N1}"]
labs = ["소수 쪽 ≥ 10", "+ 형 = d", "도메인만", "LODO 일반화", "다섯 통계 전부(암기)"]
vals = [ent["H(등급 | 소수 쪽 ≥ 10)"]["🔴 상호정보(비트)"],
        ent["H(등급 | 소수 쪽 ≥ 10, 형=d)"]["🔴 상호정보(비트)"],
        ent["H(등급 | 도메인)"]["🔴 상호정보(비트)"],
        GB["🔴 일반화 기준 상호정보(비트)"],
        ent["H(등급 | 다섯 통계 전부)"]["🔴 상호정보(비트)"]]
Hg = ent["H(등급)"]
cols = ["#7f7f7f", "#7f7f7f", "#7f7f7f", "#1f77b4", "#d62728"]
b = ax[1].barh(labs, vals, color=cols)
ax[1].axvline(Hg, color="k", ls="--", lw=1.2)
ax[1].text(Hg, -0.75, f" H(등급)={Hg}", fontsize=8, va="bottom")
for r, v in zip(b, vals):
    ax[1].text(v + .02, r.get_y() + r.get_height() / 2, f"{v}", va="center", fontsize=8)
ax[1].set_xlabel(f"상호정보 (비트) · 분모 T1 {N1}")
ax[1].set_title("(b) 붉은 막대는 자료가 아니라 튜플이 유일해서 생긴 값이다")
ax[1].set_xlim(0, Hg * 1.25)
ax[1].grid(axis="x", alpha=.25)

fig.tight_layout()
fig.savefig(HERE / "fig1.pdf")

# ── fig2 ────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(1, 2, figsize=(11.8, 4.1))

wmap = GC["🔴 W 코드 집합 → 등급 대응표(T1 81)"]
keys = sorted(wmap, key=lambda k: -sum(wmap[k].values()))
GR = ["A", "B", "C"]
M = np.array([[wmap[k].get(g, 0) for g in GR] for k in keys], dtype=float)
im = ax[0].imshow(M, cmap="Blues", aspect="auto")
ax[0].set_xticks(range(len(GR)), GR)
ax[0].set_yticks(range(len(keys)),
                 [k.replace("'", "").replace("(", "").replace(")", "").rstrip(",")
                  for k in keys], fontsize=8)
for i in range(len(keys)):
    for j in range(len(GR)):
        if M[i, j]:
            ax[0].text(j, i, int(M[i, j]), ha="center", va="center",
                       color="white" if M[i, j] > M.max() * .6 else "black", fontsize=10)
ax[0].set_xlabel("식별 등급")
ax[0].set_ylabel("W 코드 집합 (「등급 미사용」이라 적힌 키)", fontsize=9)
mixed = GC["🔴 대응이 일대일인가"]["등급이 두 가지 이상 섞인 W 코드 집합 수"]
ax[0].set_title(f"(a) {len(keys)}가지 값이 등급을 결정한다 — 섞인 칸 {mixed}")

dom = GB["🔴 잔여 짝의 도메인 분해"]
dk = sorted(dom, key=lambda k: -dom[k])
ax[1].bar(dk, [dom[k] for k in dk], color="#d62728")
for i, k in enumerate(dk):
    ax[1].text(i, dom[k] + .15, str(dom[k]), ha="center", fontsize=9)
ax[1].set_ylabel(f"잔여를 지는 짝 수 (합 {GB['🔴 잔여를 지는 짝 수']} / T1 {N1})")
s3 = GB["🔴 잔여 짝의 식3 분해"]
ax[1].set_title("(b) 잔여의 대부분이 한 도메인에 몰린다 · 식3 분해 "
                + " · ".join(f"{k} {v}" for k, v in s3.items()))
ax[1].tick_params(axis="x", labelrotation=30)
ax[1].grid(axis="y", alpha=.25)

fig.tight_layout()
fig.savefig(HERE / "fig2.pdf")
print("fig1.pdf · fig2.pdf 썼다 (값은 전부 out906_grade.json 에서 읽었다)")
