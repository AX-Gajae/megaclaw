# -*- coding: utf-8 -*-
"""499 그림 — 🔴 값을 손으로 안 적는다. 전부 산출물에서 읽는다.

읽는 것:
  runners/out939_threshold.json  (문턱 · 관문 재계수 · 배선 회계)
  runners/out935_rawpanel.json   (뽑기 200개의 상대차 원자료)
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager, rcParams

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))

for cand in ("AppleGothic", "Apple SD Gothic Neo", "NanumGothic"):
    if any(f.name == cand for f in font_manager.fontManager.ttflist):
        rcParams["font.family"] = cand
        break
rcParams["axes.unicode_minus"] = False
rcParams["font.size"] = 7.4

with open(os.path.join(ROOT, "runners", "out939_threshold.json"), encoding="utf-8") as fh:
    T939 = json.load(fh)
with open(os.path.join(ROOT, "runners", "out935_rawpanel.json"), encoding="utf-8") as fh:
    R935 = json.load(fh)

A = T939["A · 문턱"]
VER = A["🔴🔴 A-4 판정"]
PER = A["팔별"]
A5 = T939["A-5 · 관문 재계수"]
C = T939["C · 배선 회계"]
REC = R935["⑤ 뽑기 원자료 — 🔴 뽑기마다 전량 싣는다"]["기록"]

P1, P2, P3 = "① 원판 전량", "② 원판 − b_prv=−1 칸", "진단 b_prv=−1 칸만"
T = VER["🔴🔴 자료가 정한 문턱 T"]
OLD = VER["옛 문턱"]

# 🔴 산출물이 말한 k 를 원자료로 다시 센다. 어긋나면 그림을 안 그린다.
rel = {p: [abs(r[p]["비교가능성 상대차"]) for r in REC] for p in (P1, P2, P3)}
for p in (P1, P2, P3):
    k_new = sum(1 for v in rel[p] if v >= T)
    said = A5["팔별"][f"935 {p}"]["🔴 새 문턱 T"]["🔴 걸린 뽑기 k"]
    assert k_new == said, (p, k_new, said)

# ── fig1 : 상대차 분포와 두 문턱
fig, ax = plt.subplots(1, 3, figsize=(7.4, 2.35))
for i, (p, ttl) in enumerate([(P1, "판 ① 원판 전량"), (P2, "판 ② b_prv=-1 제외"),
                              (P3, "진단 ③ b_prv=-1 만")]):
    v = rel[p]
    ax[i].hist(v, bins=28, color="#5b7fa6", edgecolor="white", linewidth=0.3)
    ax[i].axvline(T, color="#c0392b", lw=1.4,
                  label="자료가 정한 문턱 %.6f" % T)
    ax[i].axvline(OLD, color="#7f8c8d", lw=1.2, ls="--", label="옛 문턱 0.05")
    k = sum(1 for x in v if x >= T)
    ax[i].set_title("%s\n새 문턱에서 걸린 뽑기 k=%d/%d" % (ttl, k, len(v)), fontsize=7.4)
    ax[i].set_xlabel("|기준 팔 MAE 상대차|")
    ax[i].set_xscale("log")
    if i == 0:
        ax[i].set_ylabel("뽑기 수")
        ax[i].legend(fontsize=5.8, loc="upper left")
fig.tight_layout()
fig.savefig(os.path.join(HERE, "fig1.pdf"))
plt.close(fig)

# ── fig2 : (a) 문턱이 허용하는 왜곡 대 판정을 뒤집는 크기 (b) 세 팔의 T (c) 배선 회계
fig, ax = plt.subplots(1, 3, figsize=(7.4, 2.4))

p1 = PER[P1]
dist = p1["🔴 옛 문턱 0.05 가 허용하던 왜곡(일) = 0.05·L_used·cr"]
G = p1["🔴 G 빈틈 = min(R − y_i)(일)"]
newdist = T * p1["🔴 L_used = max(1.0, BCa 상한)"] * p1["cr 진짜 기준 팔 MAE(일)"]
bars = [("옛 문턱 0.05\n가 허용한 왜곡", dist, "#c0392b"),
        ("채택 크기 X", 1.0, "#7f8c8d"),
        ("판정을 뒤집는\n크기 G", G, "#2c3e50"),
        ("새 문턱 T\n가 허용하는 왜곡", newdist, "#27ae60")]
ax[0].bar(range(4), [b[1] for b in bars], color=[b[2] for b in bars], width=0.62)
for i, b in enumerate(bars):
    ax[0].text(i, b[1] + 0.03, "%.3f" % b[1], ha="center", fontsize=6.4)
ax[0].set_xticks(range(4))
ax[0].set_xticklabels([b[0] for b in bars], fontsize=5.8)
ax[0].set_ylabel("개선 눈금(일)")
ax[0].set_title("(a) 문턱이 허용하던 왜곡은 G 의 %.2f배였다" % (dist / G), fontsize=7.4)

names = ["판 ①", "판 ②", "진단 ③"]
Ts = [PER[p]["🔴🔴 T = G/(L_used·cr)"] for p in (P1, P2, P3)]
ax[1].bar(range(3), Ts, color="#5b7fa6", width=0.55)
ax[1].axhline(OLD, color="#7f8c8d", ls="--", lw=1.1)
ax[1].text(2.45, OLD, " 옛 0.05", va="center", fontsize=6.2, color="#7f8c8d")
for i, t in enumerate(Ts):
    ax[1].text(i, t + 0.002, "%.6f" % t, ha="center", fontsize=6.2)
ax[1].set_xticks(range(3))
ax[1].set_xticklabels(names, fontsize=6.6)
ax[1].set_title("(b) 팔마다 T 가 %.2f배 갈린다" % VER["🔴 세 팔의 T 가 몇 배 갈리나"],
                fontsize=7.4)
ax[1].set_ylabel("문턱(상대차)")

lab, val = [], []
for arm in ("933", "935"):
    a = C[arm]
    lab += ["%s ㄱ" % arm, "%s ㄴ" % arm, "%s ㄷ" % arm]
    val += [a["발화한 수"] / a["심은 수"],
            a["발화한 수"] / (a["심은 수"] + a["못 심은 수(전량)"]),
            a["발화한 수"] / (a["심은 수"] + a["그중 ㉯ 심을 수 있었는데 안 심었다"])]
ax[2].bar(range(6), val, color=["#95a5a6", "#2c3e50", "#95a5a6"] * 2, width=0.6)
for i, v in enumerate(val):
    ax[2].text(i, v + 0.02, "%.3f" % v, ha="center", fontsize=6.0)
ax[2].set_xticks(range(6))
ax[2].set_xticklabels(lab, fontsize=6.0)
ax[2].set_ylim(0, 1.15)
ax[2].set_title("(c) 배선 검정력 - ㄱ 은 동어반복이라\n정본은 ㄴ(짙은 칸)", fontsize=7.4)
fig.tight_layout()
fig.savefig(os.path.join(HERE, "fig2.pdf"))
plt.close(fig)
print("wrote fig1.pdf fig2.pdf")
