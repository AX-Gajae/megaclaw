# -*- coding: utf-8 -*-
"""498 그림 — 🔴 값을 손으로 안 적는다. 전부 산출물에서 읽는다.

읽는 것:
  runners/out935_rawpanel.json  (뽑기 200개 전량 · 판정 · 관문 검정력 · 부호)
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

with open(os.path.join(ROOT, "runners", "out935_rawpanel.json"), encoding="utf-8") as fh:
    OUT = json.load(fh)

PERM = OUT["⑥ 🔴 판정용 순열"]
VERD = OUT["🔴🔴 판정 (사전등록 §4 를 기계로 적용)"]
SIZE = VERD["§4-크기 — 🔴 측정 전에 정해졌다(규율 4 개정판 · 판정용은 **개선** 눈금)"]
GATE = OUT["④-가 🔴 관문의 검정력 — 파일럿에서 먼저 본다 (티처 #76 M1)"]
SIGN = OUT["⑥-다 🔴 부호를 정한다 — b_prv=−1 칸을 빼면 누가 손해인가"]
REC = OUT["⑤ 뽑기 원자료 — 🔴 뽑기마다 전량 싣는다"]["기록"]

P1, P2 = "① 원판 전량", "② 원판 − b_prv=−1 칸"

# 🔴 산출물이 말한 k 를 원자료로 다시 센다. 어긋나면 그림을 안 그린다.
draws = {p: [r[p]["개선(일)"] for r in REC] for p in (P1, P2)}
for p in (P1, P2):
    v, real = draws[p], PERM[p]["진짜"]
    assert sum(1 for x in v if x >= real) == PERM[p]["🔴 귀무 ≥ 진짜 인 뽑기 수 k"], p
    assert abs(st.mean(v) - PERM[p]["귀무 평균"]) < 1e-12, p

INK, RED, BLUE, GREY, GOLD, GREEN = "#1b1b1b", "#c0392b", "#2c5f8a", "#9aa0a6", "#b8860b", "#2e7d5b"


def fig1():
    fig, ax = plt.subplots(1, 3, figsize=(13.2, 3.9))

    for i, (p, title) in enumerate([(P1, "(a) 판 ① 원판 전량"),
                                    (P2, "(b) 판 ② 그 칸을 통째로 뺐다")]):
        a, v, real = ax[i], draws[p], PERM[p]["진짜"]
        a.hist(v, bins=22, color=BLUE, alpha=0.72, edgecolor="white", linewidth=0.4)
        a.axvline(real, color=RED, lw=2.2)
        a.axvline(max(v), color=GOLD, lw=1.2, ls=":")
        a.set_xlim(min(v) - 0.02, real + 0.06)
        a.set_title("%s\nk=%d/200 · p=%.6f · 개선차 %.1f 분"
                    % (title, PERM[p]["🔴 귀무 ≥ 진짜 인 뽑기 수 k"],
                       PERM[p]["🔴 순열 p = (1+k)/(1+B)"],
                       (real - st.mean(v)) * 1440), fontsize=9.2)
        a.set_xlabel("개선(일)")
        a.set_ylabel("뽑기 수")
        a.annotate("진짜 %.5f\n귀무 최대 %.5f" % (real, max(v)),
                   xy=(0.97, 0.72), xycoords="axes fraction", ha="right",
                   fontsize=8.2, color=RED)

    # (c) 🔴 관문에 검정력이 생겼다 — 933 과의 대조
    c = ax[2]
    n_distinct = GATE["귀무 기준 팔 MAE"]["🔴 서로 다른 값의 개수"]
    denom = GATE["귀무 기준 팔 MAE"]["뽑기 수(분모)"]
    c.bar(["933 [달력제거]\n(원리상 발화 불가)", "935 원판\n(검정력 있다)"],
          [1, n_distinct], color=[GREY, GREEN], alpha=0.85)
    c.text(0, 1.4, "가짓수 1", ha="center", fontsize=9, color=INK)
    c.text(1, n_distinct + 0.4, "가짓수 %d/%d" % (n_distinct, denom),
           ha="center", fontsize=9, color=GREEN)
    c.set_ylim(0, n_distinct * 1.28)
    c.set_title("(c) 귀무 기준 팔 MAE 의 가짓수\n🔴 관문은 이번에 진짜로 걸릴 수 있었다", fontsize=9.2)
    c.set_ylabel("서로 다른 값의 개수")

    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "fig1.pdf"))
    plt.close(fig)


def fig2():
    fig, ax = plt.subplots(1, 3, figsize=(13.2, 3.9))

    # (a) 규율 4 개정판 — 두 판의 X · Y(LOO) · 진짜
    a = ax[0]
    X = SIZE["채택 크기 X(일 · 개선 눈금)"]
    names, ys, reals, zs = [], [], [], []
    for lab, key in [("판 ①", "판 ①"), ("판 ②", "판 ②")]:
        names.append(lab)
        ys.append(SIZE[key]["Y(LOO)"])
        reals.append(SIZE[key]["진짜 개선"])
        zs.append(SIZE[key]["Z = X/Y"])
    xs = range(len(names))
    a.bar([x - 0.22 for x in xs], ys, width=0.42, color=GOLD, alpha=0.8, label="Y (LOO 천장)")
    a.bar([x + 0.22 for x in xs], reals, width=0.42, color=RED, alpha=0.85, label="진짜 개선")
    a.axhline(X, color=INK, lw=1.6, ls="--")
    a.text(len(names) - 0.5, X, " 채택 크기 X = %.1f 일" % X, fontsize=8.4, va="bottom", ha="right")
    a.set_xticks(list(xs))
    a.set_xticklabels(["%s\nZ=%.3f" % (n, z) for n, z in zip(names, zs)], fontsize=8.4)
    a.set_title("(a) 규율 4 개정판 — 천장은 LOO 로 잰다\n🔴 두 판 다 Z > 1 · 이 자로는 원리상 못 넘는다",
                fontsize=9.2)
    a.set_ylabel("개선(일)")
    a.legend(fontsize=7.6, frameon=False)

    # (b) 🔴 부호를 정했다 — 칸 빼기는 보수적이다
    b = ax[1]
    s = SIGN["㉠ 판①개선 − 판②개선"]
    diffs = [r["판①개선 − 판②개선"] for r in REC]
    b.hist(diffs, bins=22, color=BLUE, alpha=0.72, edgecolor="white", linewidth=0.4)
    b.axvline(s["진짜"], color=RED, lw=2.2)
    b.set_title("(b) 그 칸이 나르는 몫 — 진짜가 귀무보다 크다 %d/%d\n"
                "🔴 그러므로 칸을 빼는 것은 **진짜에게 불리**(보수적)"
                % (s["진짜가 귀무보다 큰 뽑기"], s["분모"]), fontsize=9.2)
    b.set_xlabel("판① − 판② 개선(일)")
    b.set_ylabel("뽑기 수")
    b.annotate("진짜 %.5f\n귀무 평균 %.5f" % (s["진짜"], s["귀무 평균"]),
               xy=(0.97, 0.72), xycoords="axes fraction", ha="right", fontsize=8.2, color=RED)

    # (c) 뽑기마다 찍은 검사
    c = ax[2]
    checks = [
        ("mag 경계가\n진짜와 같다", sum(1 for r in REC if r["🔴 mag 경계가 진짜와 같은가"])),
        ("전체 중앙값이\n진짜와 같다", sum(1 for r in REC if r["🔴 전체 중앙값이 진짜와 같은가"])),
    ]
    c.bar([x[0] for x in checks], [x[1] for x in checks], color=GREEN, alpha=0.85)
    for i, x in enumerate(checks):
        c.text(i, x[1] + 4, "%d/200" % x[1], ha="center", fontsize=8.6)
    c.set_ylim(0, 235)
    sw = [r["간격 순서가 바뀐 격자 비율"] for r in REC]
    c.set_title("(c) 뽑기마다 찍은 검사\n순열이 부순 격자 비율 중앙값 %.1f%%" % (st.median(sw) * 100),
                fontsize=9.2)
    c.set_ylabel("통과한 뽑기 수")

    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "fig2.pdf"))
    plt.close(fig)


if __name__ == "__main__":
    fig1()
    fig2()
    for p in (P1, P2):
        v, real = draws[p], PERM[p]["진짜"]
        print(p, "k =", sum(1 for x in v if x >= real), "· 개선차(분) =", round((real - st.mean(v)) * 1440, 4))
    print("Z:", SIZE["판 ①"]["Z = X/Y"], SIZE["판 ②"]["Z = X/Y"])
    print("관문 가짓수:", GATE["귀무 기준 팔 MAE"]["🔴 서로 다른 값의 개수"])
    print("wrote fig1.pdf fig2.pdf")
