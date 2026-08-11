# -*- coding: utf-8 -*-
"""497 그림 — 🔴 값을 손으로 안 적는다. 전부 산출물에서 읽는다.

읽는 것:
  runners/out933_calpanel.json  (뽑기 200개 전량 · 판정 · 배선)
  runners/out933_oracle.json    (오라클 천장 · 규율 4 의 Y)
"""
import json
import os
import statistics as st

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager, rcParams

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))  # /Users/ax/world_model

for cand in ("AppleGothic", "Apple SD Gothic Neo", "NanumGothic"):
    if any(f.name == cand for f in font_manager.fontManager.ttflist):
        rcParams["font.family"] = cand
        break
rcParams["axes.unicode_minus"] = False


def load(name):
    with open(os.path.join(ROOT, "runners", name), encoding="utf-8") as fh:
        return json.load(fh)


OUT = load("out933_calpanel.json")
ORC = load("out933_oracle.json")

PERM = OUT["⑥ 🔴 판정용 순열 — 판 둘"]
VERD = OUT["🔴🔴 판정 (사전등록 §4 를 기계로 적용)"]
SIZE = VERD["§4-크기 — 🔴 측정 전에 정해졌다(규율 4)"]
REC = OUT["⑤ 뽑기 원자료 — 🔴 뽑기마다 전량 싣는다"]["기록"]

P1, P2 = "① [달력제거]", "② [달력제거·경계강제]"
real = PERM[P1]["진짜"]

# 🔴 산출물이 말한 k 를 원자료로 다시 센다. 어긋나면 그림을 안 그린다.
draws = {p: [r[p]["개선(일)"] for r in REC] for p in (P1, P2)}
for p in (P1, P2):
    v = draws[p]
    assert len(v) == PERM[p]["🔴 뽑기 수 B(성공한 것만 · 분모)"], p
    assert sum(1 for x in v if x >= real) == PERM[p]["🔴 귀무 ≥ 진짜 인 뽑기 수 k"], p
    assert abs(st.mean(v) - PERM[p]["귀무 평균"]) < 1e-12, p

INK = "#1b1b1b"
RED = "#c0392b"
BLUE = "#2c5f8a"
GREY = "#9aa0a6"
GOLD = "#b8860b"
GREEN = "#2e7d5b"


def fig1():
    fig, ax = plt.subplots(1, 3, figsize=(13.2, 3.9))

    # (a)(b) 두 판의 귀무 분포와 진짜
    for i, (p, title) in enumerate([(P1, "(a) 판 ① 달력제거"),
                                    (P2, "(b) 판 ② 달력제거 + 경계 강제")]):
        a = ax[i]
        v = draws[p]
        a.hist(v, bins=22, color=BLUE, alpha=0.72, edgecolor="white", linewidth=0.4)
        a.axvline(real, color=RED, lw=2.2)
        a.axvline(max(v), color=GOLD, lw=1.2, ls=":")
        ns = PERM[p]["🔴 경계 상태별 표"]["상태 수"]
        a.set_title("%s\n경계 상태 %d개 · k=%d/200 · p=%.6f"
                    % (title, ns, PERM[p]["🔴 귀무 ≥ 진짜 인 뽑기 수 k"],
                       PERM[p]["🔴 순열 p = (1+k)/(1+B)"]), fontsize=9.2)
        a.set_xlabel("개선(일)")
        a.set_ylabel("뽑기 수")
        a.set_xlim(min(v) - 0.004, real + 0.012)
        a.annotate("진짜 %.5f\n효과 %.1f 분" % (real, PERM[p]["🔴 효과(분)"]),
                   xy=(0.97, 0.70), xycoords="axes fraction", ha="right",
                   fontsize=8.4, color=RED)
        a.text(max(v), a.get_ylim()[1] * 0.06, " 귀무 최대", fontsize=7.4, color=GOLD)

    # (c) 경계 상태별 — 판 ① 은 4개, 판 ② 는 1개
    c = ax[2]
    tab = PERM[P1]["🔴 경계 상태별 표"]["상태별"]
    labels = ["%.1f/%.1f\nn=%d" % (t["경계"][0], t["경계"][1], t["개수"]) for t in tab]
    means = [t["평균"] for t in tab]
    sds = [t["상태 내 SD(ddof=1)"] for t in tab]
    c.bar(range(len(tab)), means, yerr=sds, color=BLUE, alpha=0.8, capsize=4)
    c.set_xticks(range(len(tab)))
    c.set_xticklabels(labels, fontsize=7.6)
    forced = PERM[P2]["🔴 경계 상태별 표"]["상태별"][0]
    c.axhline(forced["평균"], color=GREEN, lw=1.6, ls="--")
    c.text(len(tab) - 0.5, forced["평균"], " 판 ② 강제 %.1f/%.1f\n 평균 %.5f"
           % (forced["경계"][0], forced["경계"][1], forced["평균"]),
           fontsize=7.6, color=GREEN, ha="right", va="bottom")
    c.set_title("(c) 귀무의 prevmed 경계 상태\n진짜는 (4.5, 7.0) — 200뽑기가 한 번도 안 가는 자리",
                fontsize=9.2)
    c.set_ylabel("개선(일)")

    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "fig1.pdf"))
    plt.close(fig)


def fig2():
    fig, ax = plt.subplots(1, 3, figsize=(13.2, 3.9))

    # (a) 규율 4 — 채택 크기와 오라클 천장
    a = ax[0]
    X = SIZE["채택 크기 X(일)"]
    Y = SIZE["오라클 천장 Y(일)"]
    eff = SIZE["실측 효과(진짜 − 귀무평균 · 일 · 채택 판정에 안 쓴다)"]
    a.barh([2], [X], color=GREY, alpha=0.35, height=0.5)
    a.barh([1], [Y], color=GOLD, alpha=0.75, height=0.5)
    a.barh([0], [eff], color=RED, height=0.5)
    a.set_yticks([0, 1, 2])
    a.set_yticklabels(["실측 효과", "오라클 천장 Y", "채택 크기 X"], fontsize=8.4)
    a.set_xlim(0, X * 1.1)
    for y, val, txt in [(2, X, "%.1f 일" % X), (1, Y, "%.4f 일" % Y),
                        (0, eff, "%.4f 일 = %.1f 분" % (eff, SIZE["실측 효과(분)"]))]:
        a.text(val + X * 0.015, y, txt, va="center", fontsize=8.2)
    a.set_title("(a) 규율 4 — X/Y = %.3f > 1\n🔴 이 자로는 원리상 못 넘는다(측정 전에 났다)"
                % SIZE["X/Y = Z"], fontsize=9.2)
    a.set_xlabel("일")

    # (b) 진짜 팔이 천장의 몇 %인가
    b = ax[1]
    pct = SIZE["진짜 팔이 천장의 몇 %인가"]
    b.bar(["오라클 천장", "진짜 팔"], [Y, real], color=[GOLD, RED], alpha=0.85)
    b.text(1, real + Y * 0.02, "%.5f\n(%.2f%%)" % (real, pct), ha="center", fontsize=8.6)
    b.text(0, Y + Y * 0.02, "%.6f" % Y, ha="center", fontsize=8.6)
    b.set_ylim(0, Y * 1.18)
    b.set_title("(b) 진짜 팔은 이미 천장의 %.2f%% 다\n자료를 더 줘도 이 조건 열로는 못 올라간다"
                % pct, fontsize=9.2)
    b.set_ylabel("개선(일)")

    # (c) 뽑기마다 찍은 관문 넷 — 전부 200/200
    c = ax[2]
    gates = [
        ("정답 다중집합\n동일", sum(1 for r in REC if r["🔴 정답 다중집합 동일"])),
        ("비교가능성\n통과", sum(1 for r in REC if r["🔴 비교가능성 통과"])),
        ("mag 경계\n진짜와 같다", sum(1 for r in REC if r["🔴 mag 경계가 진짜와 같은가"])),
        ("전체 중앙값\n진짜와 같다", sum(1 for r in REC if r["🔴 전체 중앙값이 진짜와 같은가"])),
    ]
    c.bar([g[0] for g in gates], [g[1] for g in gates], color=GREEN, alpha=0.85)
    for i, g in enumerate(gates):
        c.text(i, g[1] + 4, "%d/200" % g[1], ha="center", fontsize=8.4)
    c.set_ylim(0, 230)
    c.set_xticklabels([g[0] for g in gates], fontsize=7.4)
    sw = [r["간격 순서가 바뀐 격자 비율"] for r in REC]
    c.set_title("(c) 뽑기마다 찍은 관문 — 전부 200/200\n순열은 실제로 순서를 부순다"
                "(격자 %.1f%% 중앙값)" % (st.median(sw) * 100), fontsize=9.2)
    c.set_ylabel("통과한 뽑기 수")

    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "fig2.pdf"))
    plt.close(fig)


if __name__ == "__main__":
    fig1()
    fig2()
    for p in (P1, P2):
        print(p, "k =", sum(1 for x in draws[p] if x >= real),
              "· 효과(분) =", round(PERM[p]["🔴 효과(분)"], 4))
    print("X/Y = Z =", SIZE["X/Y = Z"], "· 천장의", round(SIZE["진짜 팔이 천장의 몇 %인가"], 4), "%")
    print("wrote fig1.pdf fig2.pdf")
