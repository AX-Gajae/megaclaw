# -*- coding: utf-8 -*-
"""501 그림 — 🔴 값을 손으로 안 적는다. 전부 `runners/out958_within.json` 에서 읽는다."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager, rcParams

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))

for cand in ("Nanum Gothic", "Nanum Myeongjo", "AppleGothic", "Apple SD Gothic Neo"):
    if any(f.name == cand for f in font_manager.fontManager.ttflist):
        rcParams["font.family"] = cand
        break
rcParams["axes.unicode_minus"] = False
rcParams["figure.dpi"] = 200
rcParams["font.size"] = 7.2
rcParams["savefig.bbox"] = "tight"
rcParams["axes.spines.top"] = False
rcParams["axes.spines.right"] = False
INK, GATE, CLAIM = "#1a1a1a", "#2166ac", "#b2182b"

d = json.load(open(os.path.join(ROOT, "runners/out958_within.json")))
K = "§6 자 A · 고정 모형 within/between"
B = d[K]["팔 B · ① → ①+③ (도메인)"]
A = d[K]["팔 A · ① → ①+② (좌표원천)"]
AD = d[K]["팔 A · ① → ①+② (도메인)"]
SZ = d["§7 곁들이 · 표본 크기 실험 (판정 아님 · 957 의 수)"]["팔 B · 도메인"]
wB = B["🔴 자 A · 고정 모형 · 묶음 안"]
kB, kA, kAD = (B["🔴 자 B · 켄달 짝 단위"], A["🔴 자 B · 켄달 짝 단위"],
               AD["🔴 자 B · 켄달 짝 단위"])
T = "🔴 문턱 T = max(0.00353, 2·SE)"

fig, ax = plt.subplots(1, 3, figsize=(11.4, 2.9))

# ── (가) 자를 바꾸면 수가 이만큼 움직인다 ──────────────────────────────────
a = ax[0]
vals = [SZ["묶음 안 평균 Δρ(= 957 의 헤드라인 수)"],
        wB["🔴 Δρ_within (쌍 가중 안쪽 평균)"], B["🔴 합산 Δρ"]]
labs = ["957 의 자\n(도메인마다 재적합)", "958 의 자\n(모형 고정·채점만 좁힘)", "합산"]
cols = [INK, CLAIM, GATE]
a.bar(range(3), vals, color=cols, width=0.56)
se = B["🔴 SE_boot(Δρ_within)"]
a.errorbar(1, vals[1], yerr=se, fmt="none", ecolor=CLAIM, capsize=4, lw=1.2)
a.axhline(0, color=INK, lw=0.7)
a.axhline(B[T], color=CLAIM, ls=":", lw=1.0)
a.text(2.46, B[T], f"T={B[T]:.4f}", color=CLAIM, va="bottom", ha="right", fontsize=6.4)
for i, v in enumerate(vals):
    a.text(i, v + 0.004, f"{v:+.6f}", ha="center", fontsize=6.6, color=cols[i])
a.set_xticks(range(3))
a.set_xticklabels(labs, fontsize=6.3)
a.set_ylabel("Δρ (층 ③ · 팔 B · 464쌍)")
a.set_title("(가) 자를 바꾸니 헤드라인 수가 53.7배 움직인다", fontsize=7.6)
a.set_ylim(-0.012, 0.155)

# ── (나) 켄달 짝 단위 — 안 + 사이 = 전체 (항등) ────────────────────────────
b = ax[1]
w, bt = kB["분자: 안 차(C−D)"], kB["분자: 사이 차(C−D)"]
nw, nb = kB["분모: 안 짝"], kB["분모: 사이 짝"]
b.barh([1], [w], color=CLAIM, height=0.5)
b.barh([0], [bt], color=GATE, height=0.5)
b.set_yticks([0, 1])
b.set_yticklabels([f"도메인 사이\n{nb:,}짝", f"도메인 안\n{nw:,}짝"], fontsize=6.6)
b.text(w + 90, 1, f"{w:+,.0f}  ({kB['안 짝당']:+.4f}/짝)", va="center",
       fontsize=6.6, color=CLAIM)
b.text(bt + 90, 0, f"{bt:+,.0f}  ({kB['사이 짝당']:+.4f}/짝)", va="center",
       fontsize=6.6, color=GATE)
b.set_xlim(0, 4900)
b.set_xlabel("일치쌍 차 C−D (짝 단위로 더해진다)")
b.set_title(f"(나) 안쪽 몫 {kB['🔴 안쪽 몫 = 안쪽 차 ÷ 전체 차']:.2%} — "
            f"짝당은 안쪽이 {kB['짝당 안쪽 ÷ 짝당 바깥쪽']:.2f}배", fontsize=7.6)

# ── (다) 칸막이를 바꾸면 안/사이가 뒤집힌다 (팔 A · 같은 Δρ) ───────────────
c = ax[2]
sh = [kA["🔴 안쪽 몫 = 안쪽 차 ÷ 전체 차"], kAD["🔴 안쪽 몫 = 안쪽 차 ÷ 전체 차"]]
c.bar([0, 1], sh, color=[GATE, CLAIM], width=0.5)
c.axhline(0, color=INK, lw=0.7)
c.axhline(1, color=INK, lw=0.5, ls=":")
for i, v in enumerate(sh):
    c.text(i, v + (0.04 if v > 0 else -0.09), f"{v:+.2%}", ha="center", fontsize=7.0,
           color=[GATE, CLAIM][i])
c.set_xticks([0, 1])
c.set_xticklabels(["칸막이 = 좌표원천", "칸막이 = 도메인"], fontsize=6.6)
c.set_ylabel("안쪽 몫 (안쪽 차 ÷ 전체 차)")
c.set_ylim(-0.45, 1.15)
c.set_title(f"(다) 같은 팔 A · 같은 Δρ {A['🔴 합산 Δρ']:+.6f}\n"
            "— 칸막이만 바꿔도 「전부 사이」가 「거의 다 안」이 된다", fontsize=7.6)

fig.tight_layout()
fig.savefig(os.path.join(HERE, "ret.pdf"))
print("ok", [f"{v:+.6f}" for v in vals], f"{kB['🔴 안쪽 몫 = 안쪽 차 ÷ 전체 차']:.6f}", sh)
