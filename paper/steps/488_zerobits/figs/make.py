#!/usr/bin/env python3
# 노트 903 그림 — 🔴 손 전사 금지: 값은 전부 산출물 `runners/out903_effect.json` 에서 **읽는다**.
#   fig1 (a) 두 팔의 δ 와 BCa 구간 · 위약 ② 탐지 문턱
#        (b) 팝업 위약 ② 분포와 진짜 δ 의 자리
#        (c) 위약이 진짜 분할을 재현한 비율 — 「A」가 0비트인 자리
#   fig2 (a) MDE 대 실측 |δ|   (b) 영화 창 절단 — 주장이 아니라 측정
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

E = json.loads((ROOT / "runners/out903_effect.json").read_text())
K_PU = "팔 ㄴ 팝업 entry_friction (판정을 진다)"
K_MV = "팔 ㄱ 영화 개봉일 (재되 판정 안 한다)"
K_CI = "🔴 구간(규약 47 · lab.pairboot.cluster_boot)"
K_D = "효과 크기 Cliff's δ (저군 대 고군 · 양수=고군이 크다)"
K_P2 = "위약 ② 무작위 중앙값 분할(처치 열 안 셔플)"
K_P1 = "위약 ① 값 셔플(결과를 섞는다)"
K_REP = "🔴 위약 ② 가 진짜 분할(절단값·저군·고군·소수 쪽)을 재현한 횟수"
K_MDE = "🔴 이 설계가 잴 수 있는 최소 효과(MDE · 사후 서술 · 판정 미사용)"
PU, MV = E[K_PU], E[K_MV]
P4 = E["🔴 P4 창 절단 — 주장이 아니라 측정"]

# ── fig1 ────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(1, 3, figsize=(13.6, 4.0))

# (a) δ 와 BCa 구간
arms = [("팝업 entry\\_friction\n→ 방문자 (D1 · 짝 %d)" % PU["짝 행"], PU, "#c0392b"),
        ("영화 개봉일\n→ y (D3 · 짝 %d)" % MV["짝 행"], MV, "#7f8c8d")]
for i, (lab, A, c) in enumerate(arms):
    d, lo, hi = A[K_D], A[K_CI]["lo"], A[K_CI]["hi"]
    thr = A["위약 ② |δ| 95분위"]
    ax[0].axhspan(-thr, thr, xmin=(i) / 2 + .03, xmax=(i + 1) / 2 - .03,
                  color="#dfe6e9", zorder=0)
    ax[0].errorbar([i], [d], yerr=[[d - lo], [hi - d]], fmt="o", color=c,
                   capsize=6, lw=2, ms=8)
    ax[0].annotate(f"δ={d:+.4f}\n[{lo:+.3f},{hi:+.3f}]", (i, d),
                   textcoords="offset points", xytext=(14, -4), fontsize=8.5)
ax[0].axhline(0, color="#2d3436", lw=1)
ax[0].set_xticks([0, 1])
ax[0].set_xticklabels([a[0] for a in arms], fontsize=8.5)
ax[0].set_xlim(-.6, 1.9)
ax[0].set_ylabel("Cliff's δ (저군 대 고군)")
ax[0].set_title("(a) 두 팔 다 구간이 0 을 문다\n회색 띠 = 위약 ② 의 |δ| 95분위", fontsize=10)
ax[0].grid(axis="y", alpha=.25)

# (b) 팝업 위약 ② 분포(요약값으로 정규 근사 곡선 + 분위 눈금) · 진짜 δ 자리
p2 = PU["위약"][K_P2]
sd, mu = p2["SD"], p2["평균"]
xs = np.linspace(-4 * sd, 4 * sd, 400)
ax[1].plot(xs, np.exp(-((xs - mu) ** 2) / (2 * sd ** 2)), color="#636e72", lw=1.4)
ax[1].fill_between(xs, 0, np.exp(-((xs - mu) ** 2) / (2 * sd ** 2)),
                   color="#dfe6e9")
for q, lab in ((p2["5분위"], "5%"), (p2["95분위"], "95%")):
    ax[1].axvline(q, color="#0984e3", ls=":", lw=1.2)
    ax[1].annotate(lab, (q, 1.02), fontsize=8, ha="center", color="#0984e3")
ax[1].axvline(PU[K_D], color="#c0392b", lw=2.2)
ax[1].annotate("진짜 δ\n%+.4f" % PU[K_D], (PU[K_D], .55), fontsize=9,
               color="#c0392b", ha="center")
ax[1].set_xlabel("위약 ② δ  (씨앗 %d × 반복 %d = %d)"
                 % (PU["위약"]["🔴 씨앗 수 K"], PU["위약"]["씨앗당 반복"],
                    PU["위약"]["총 반복"]))
ax[1].set_yticks([])
ax[1].set_title("(b) 진짜 효과는 위약 한복판에 있다\n위약이 진짜를 넘은 비율 = %.3f"
                % p2["🔴 진짜 |δ| 를 넘은 위약 비율(경험적 p)"], fontsize=10)

# (c) 🔴 위약이 진짜 분할을 재현한 비율 — A 가 0비트인 자리
k3pu = [k for k in PU["위약"] if k.startswith("위약 ③")][0]
bars = [("팝업\n위약 ② 분할 재현",
         PU["위약"][K_REP]["재현"], PU["위약"][K_REP]["분모"]),
        ("영화\n위약 ② 분할 재현",
         MV["위약"][K_REP]["재현"], MV["위약"][K_REP]["분모"]),
        ("팝업\n위약 ③ 식1=예",
         PU["위약"][k3pu]["식1=예"], PU["위약"][k3pu]["분모"])]
ax[2].bar(range(3), [b / c for _, b, c in bars], color="#c0392b", width=.55)
for i, (lab, b, c) in enumerate(bars):
    ax[2].annotate(f"{b}/{c}", (i, b / c), textcoords="offset points",
                   xytext=(0, 4), ha="center", fontsize=10, weight="bold")
ax[2].set_xticks(range(3))
ax[2].set_xticklabels([b[0] for b in bars], fontsize=8.5)
ax[2].set_ylim(0, 1.18)
ax[2].set_ylabel("재현율")
ax[2].set_title("(c) 처치를 아무렇게나 섞어도 등급이 그대로다\n= 「A」는 처치–결과에 대해 0비트", fontsize=10)
ax[2].grid(axis="y", alpha=.25)

fig.tight_layout()
fig.savefig(HERE / "fig1.pdf")
plt.close(fig)

# ── fig2 ────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(1, 2, figsize=(9.6, 3.9))

# (a) MDE 대 실측
names, mdes, obs = [], [], []
for lab, A in (("팝업\nentry\\_friction", PU), ("영화\n개봉일", MV)):
    names.append(lab)
    mdes.append(A[K_MDE]["MDE(검정력 80% 근사 = 문턱 + 0.84·SD)"])
    obs.append(abs(A[K_D]))
x = np.arange(2)
ax[0].bar(x - .18, mdes, width=.34, color="#b2bec3", label="이 설계가 볼 수 있는 최소(MDE)")
ax[0].bar(x + .18, obs, width=.34, color="#c0392b", label="실측 |δ|")
for i in range(2):
    ax[0].annotate(f"{mdes[i]:.3f}", (i - .18, mdes[i]), textcoords="offset points",
                   xytext=(0, 3), ha="center", fontsize=9)
    ax[0].annotate(f"{obs[i]:.4f}", (i + .18, obs[i]), textcoords="offset points",
                   xytext=(0, 3), ha="center", fontsize=9, weight="bold")
ax[0].set_xticks(x)
ax[0].set_xticklabels(names, fontsize=9)
ax[0].set_ylabel("|Cliff's δ|")
ax[0].legend(fontsize=8)
ax[0].set_title("(a) 자가 못 보는 크기다 — 실측/MDE = %.3f · %.3f"
                % (PU[K_MDE]["실측 |δ| / MDE"], MV[K_MDE]["실측 |δ| / MDE"]), fontsize=10)
ax[0].grid(axis="y", alpha=.25)

# (b) 영화 창 절단
lo_l = P4["저군(이른 개봉) 마지막 관측일차 평균"]
hi_l = P4["고군(늦은 개봉) 마지막 관측일차 평균"]
lo_c = P4["저군 검열(개봉+14 미달) 비율"]
hi_c = P4["고군 검열(개봉+14 미달) 비율"]
a2 = ax[1]
a2.bar([0, 1], [lo_l, hi_l], width=.5, color=["#0984e3", "#d63031"])
a2.set_ylim(min(lo_l, hi_l) - 1.2, max(lo_l, hi_l) + .5)
a2.set_xticks([0, 1])
a2.set_xticklabels([f"저군 이른 개봉 (n={P4['저군 n']})",
                    f"고군 늦은 개봉 (n={P4['고군 n']})"], fontsize=9)
a2.set_ylabel("마지막 관측일차 (창 최대 20)")
for i, (v, c) in enumerate(((lo_l, lo_c), (hi_l, hi_c))):
    a2.annotate(f"{v:.2f}\n검열 {c*100:.1f}%", (i, v), textcoords="offset points",
                xytext=(0, 4), ha="center", fontsize=9)
a2.set_title("(b) 처치가 곧 결과 창의 원점 — 주장이 아니라 측정\n차(고 - 저) = %+.4f · 관측일차↔y 스피어만 %+.3f"
             % (P4["차(고−저)"], P4["마지막 관측일차 대 y 스피어만(짝 406)"]), fontsize=9.5)
a2.grid(axis="y", alpha=.25)

fig.tight_layout()
fig.savefig(HERE / "fig2.pdf")
plt.close(fig)
print("fig1.pdf · fig2.pdf 저장")
