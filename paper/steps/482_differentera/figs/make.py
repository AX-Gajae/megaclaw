# -*- coding: utf-8 -*-
"""그림 1 — 노트 896. **값은 전부 산출물에서 읽는다(손 전사 금지 · 티처 #57 M1).**

왼쪽   0단계 깔때기 --- 895 의 자가 판의 유보에 닿는 데까지 몇 행이 남나
가운데 팔 A --- 도메인별 ρ_A 와 **순열 널** 띠. 존재는 부호가 갈리고 양만 한쪽이다
오른쪽 팔 B --- 신호 몫 대 문턱 0.00353 · 잡음 바닥 0.01055
"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                 # noqa: E402
from matplotlib import font_manager, rcParams                   # noqa: E402

for c in ("AppleSDGothicNeo", "Apple SD Gothic Neo", "NanumGothic"):
    try:
        font_manager.findfont(c, fallback_to_default=False)
        rcParams["font.family"] = c
        break
    except Exception:
        pass
rcParams["axes.unicode_minus"] = False

R = "/Users/ax/world_model/runners/"
S0 = json.load(open(R + "out896_step0.json"))
AA = json.load(open(R + "out896_armA.json"))
BB = json.load(open(R + "out896_armB.json"))

GA, NA = "ㄱ 존재 이진", "ㄴ 양(설명문 글자수)"
fig, ax = plt.subplots(1, 3, figsize=(12.0, 3.6))

# ── 왼쪽: 0단계 깔때기 ──────────────────────────────────────────────────────
I = S0["ⓑ 895 자 ↔ 유보 교집합"]
steps = [("895 정답지\n실물", I["895 실물"]),
         ("manga_records\n(7,982) 안", I["manga_records(7982) 안"]),
         ("판의 만화 행\n(5,905) 안", I["판 만화 행(manga_axes) 안"]),
         ("유보(258)\n교집합", I["🔴 유보 교집합 n"])]
xs = range(len(steps))
vals = [v for _, v in steps]
cols = ["#4c78a8", "#4c78a8", "#e08214", "#a33"]
ax[0].bar(list(xs), vals, 0.62, color=cols)
for i, v in enumerate(vals):
    ax[0].text(i, v + 5, str(v), ha="center", fontsize=9,
               fontweight="bold" if i == 3 else "normal",
               color="#a33" if i == 3 else "#333")
ax[0].set_xticks(list(xs))
ax[0].set_xticklabels([s for s, _ in steps], fontsize=7)
ax[0].set_ylabel("작품 수", fontsize=8)
ax[0].set_ylim(0, 235)
ax[0].set_title("0단계 · 자는 판에 닿지 않는다", fontsize=9)
ax[0].tick_params(labelsize=7)

# ── 가운데: 팔 A ────────────────────────────────────────────────────────────
def dom_rows(nm):
    r = AA["결과"][nm]
    per = r["도메인별"]
    ks = sorted(per, key=lambda k: per[k]["ρ_A 무통제"] or 0.0)
    return r, ks, per


rA, ksA, perA = dom_rows(GA)
rB, ksB, perB = dom_rows(NA)
labs, vv, cc = [], [], []
for k in ksA:
    labs.append(k); vv.append(perA[k]["ρ_A 무통제"]); cc.append("#4c78a8")
labs.append(""); vv.append(0.0); cc.append("none")
for k in ksB:
    labs.append(k + " ‡"); vv.append(perB[k]["ρ_A 무통제"]); cc.append("#2a6f6f")
y = range(len(labs))
ax[1].barh(list(y), vv, 0.6, color=cc)
ax[1].axvline(0, color="#666", lw=0.8)
s2a = rA["순열 널 2σ"]
ax[1].axvspan(-s2a, s2a, color="#bbb", alpha=0.30, zorder=0)
ax[1].errorbar(rA["ρ_A (행수 가중 · 무통제)"], -1.0,
               xerr=[[rA["ρ_A (행수 가중 · 무통제)"] - rA["BCa 95%"][0]],
                     [rA["BCa 95%"][1] - rA["ρ_A (행수 가중 · 무통제)"]]],
               fmt="o", ms=5, color="#4c78a8", capsize=3, lw=1.2)
ax[1].errorbar(rB["ρ_A (행수 가중 · 무통제)"], len(labs),
               xerr=[[rB["ρ_A (행수 가중 · 무통제)"] - rB["BCa 95%"][0]],
                     [rB["BCa 95%"][1] - rB["ρ_A (행수 가중 · 무통제)"]]],
               fmt="o", ms=5, color="#2a6f6f", capsize=3, lw=1.2)
ax[1].set_yticks([-1.0] + list(y) + [len(labs)])
ax[1].set_yticklabels(["존재 · 모아서"] + labs + ["양 · 모아서"], fontsize=7)
ax[1].set_xlabel("rho_A = Spearman(용량, -오차)   양수면 잘 맞힌다", fontsize=7.5)
ax[1].set_title(f"팔 A · 회색 띠 = 순열 널 2σ({s2a:.3f})", fontsize=9)
ax[1].tick_params(labelsize=7)

# ── 오른쪽: 팔 B ────────────────────────────────────────────────────────────
V = BB["판별"]
names = [GA, NA]
sig = [V[n]["**신호 몫(진짜 − 널평균)**"] for n in names]
net = [V[n]["**순효과(진짜 − 기준선)**"] for n in names]
lo = [V[n]["씨앗 짝 BCa 95%"][0] for n in names]
hi = [V[n]["씨앗 짝 BCa 95%"][1] for n in names]
x = range(len(names))
w = 0.34
ax[2].bar([i - w / 2 for i in x], sig, w, color="#4c78a8", label="신호 몫")
ax[2].bar([i + w / 2 for i in x], net, w, color="#9ecae1", label="순효과")
for i in x:
    ax[2].errorbar(i - w / 2, sig[i],
                   yerr=[[sig[i] - lo[i]], [hi[i] - sig[i]]],
                   fmt="none", ecolor="#233", capsize=3, lw=1.1)
TH = BB["설계"]["판정선"]
FL = BB["설계"]["잡음 바닥(노트 892)"]
ax[2].axhline(TH, color="#a33", ls="--", lw=1.1)
ax[2].axhline(-TH, color="#a33", ls="--", lw=0.7)
ax[2].axhline(FL, color="#888", ls=":", lw=1.0)
ax[2].text(1.48, TH, f" 문턱 {TH}", fontsize=6.5, color="#a33", va="bottom")
ax[2].text(1.48, FL, f" 잡음 바닥 {FL}", fontsize=6.5, color="#666", va="bottom")
ax[2].axhline(0, color="#666", lw=0.8)
ax[2].set_xticks(list(x))
ax[2].set_xticklabels(["존재 이진\n(7도메인)", "양 · 글자수\n(2도메인)"], fontsize=7.5)
ax[2].set_ylabel("판 Δρ", fontsize=8)
ax[2].set_title("팔 B · 개입(막대 = 씨앗 6 짝 · BCa)", fontsize=9)
ax[2].legend(fontsize=6.5, loc="lower right")
ax[2].tick_params(labelsize=7)

fig.suptitle("노트 896 — 자와 판이 다른 시대를 산다", fontsize=10.5, y=1.02)
fig.tight_layout()
fig.savefig("/Users/ax/world_model/paper/steps/482_differentera/figs/fig1.pdf",
            bbox_inches="tight")
print("ok")
