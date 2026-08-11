# -*- coding: utf-8 -*-
"""496 그림 — 🔴 값을 손으로 안 적는다. 전부 산출물에서 읽는다.

읽는 것:
  runners/out928_paired.json    (판정 · 순열 · 크기 관문 · 408 분해)
  runners/out928_draws.json     (200뽑기 원자료 — 히스토그램의 유일한 출처)
  runners/out928_addendum.json  (검출력 예측 실패 · W4 자백)
"""
import json
import math
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


OUT = load("out928_paired.json")
DRAWS = load("out928_draws.json")
ADD = load("out928_addendum.json")

PERM = OUT["④ 순열 200뽑기 — 🔴 진짜의 순위로 p 를 낸다"]
NN = OUT["④-나 🔴 귀무 대 귀무 — 참 귀무 안의 변동이 효과와 같은 크기인가"]
G408 = OUT["④-다 🔴 408개 격자의 정체 (조항 60 — 925 가 어긴 자리)"]
SIZE = OUT["⑤ 🔴 크기 관문 — 유의성과 둘이다"]
VERD = OUT["🔴🔴 판정 (사전등록 §4 를 기계로 적용)"]
POW = ADD["🔴 ② 사전등록의 검출력 계산이 틀렸다 — 내가 먼저 적는다"]

vals = list(DRAWS["draws"].values())
real = PERM["진짜"]
mean = PERM["귀무 평균"]
sd = PERM["귀무 SD(ddof=1)"]
kk = PERM["🔴 귀무 ≥ 진짜 인 뽑기 수 k"]
pp = PERM["🔴 순열 p = (1+k)/(1+B)"]
B = PERM["🔴 뽑기 수 B(성공한 것만 · 분모)"]

# 🔴 산출물이 말한 k 를 원자료로 다시 센다. 어긋나면 그림을 안 그린다.
k_recount = sum(1 for v in vals if v >= real)
assert len(vals) == B, (len(vals), B)
assert k_recount == kk, (k_recount, kk)
assert abs(st.mean(vals) - mean) < 1e-12
assert abs(st.stdev(vals) - sd) < 1e-12

INK = "#1b1b1b"
RED = "#c0392b"
BLUE = "#2c5f8a"
GREY = "#9aa0a6"
GOLD = "#b8860b"


def fig1():
    fig, ax = plt.subplots(1, 3, figsize=(13.2, 3.9))

    # (a) 귀무 200뽑기 + 진짜 — 그리고 정규근사가 어디서 깨지나
    a = ax[0]
    a.hist(vals, bins=24, color=BLUE, alpha=0.72, edgecolor="white", linewidth=0.4)
    xs = [mean - 4 * sd + i * (8 * sd) / 240 for i in range(241)]
    dens = [len(vals) * (max(vals) - min(vals)) / 24
            * math.exp(-0.5 * ((x - mean) / sd) ** 2) / (sd * math.sqrt(2 * math.pi))
            for x in xs]
    a.plot(xs, dens, color=GREY, lw=1.4, ls="--", label="정규 근사")
    a.axvline(real, color=RED, lw=2.2)
    a.annotate("진짜 %.6f\n귀무 %d 개가 전부 아래\nk=%d · p=%.6f"
               % (real, B, kk, pp),
               xy=(real, 0), xytext=(0.985, 0.62), textcoords="axes fraction",
               ha="right", fontsize=8.4, color=RED)
    a.axvline(max(vals), color=GOLD, lw=1.2, ls=":")
    a.text(max(vals), a.get_ylim()[1] * 0.14, " 귀무 최대\n %.6f" % max(vals),
           fontsize=7.6, color=GOLD, va="bottom")
    a.set_title("(a) 순열 %d뽑기 — 꼬리가 정규보다 짧다\n초과첨도 %.2f · 표준화 최대 %.2f SD"
                % (B, POW["🔴 왜 틀렸나 — 세어서 답한다"]["초과 첨도"],
                   POW["🔴 왜 틀렸나 — 세어서 답한다"]["표준화한 귀무 최대"]),
                fontsize=9.2)
    a.set_xlabel("개선(일)")
    a.set_ylabel("뽑기 수")
    a.legend(fontsize=7.4, loc="upper left", frameon=False)

    # (b) 🔴 두 자 — 유의성은 이겼고 크기는 졌다
    b = ax[1]
    thr = SIZE["🔴 문턱(사전등록 §5 · 측정 전에 박았다)"]
    eff = SIZE["실측 효과(일 · 진짜 − 귀무평균)"]
    b.barh([1], [thr], color=GREY, alpha=0.35, height=0.42)
    b.barh([1], [eff], color=RED, height=0.42)
    b.set_yticks([1])
    b.set_yticklabels(["개선(일)"])
    b.set_xlim(0, thr * 1.18)
    b.text(eff, 1.30, "실측 %.4f 일 = %.1f 분" % (eff, SIZE["실측 효과(분)"]),
           fontsize=8.4, color=RED)
    b.text(thr, 0.68, "채택 크기 %.1f 일\n(측정 전에 박았다)" % thr,
           fontsize=8.4, color=INK, ha="right")
    b.set_title("(b) 유의성과 크기는 둘이다\np=%.6f 로 이기고 %.1f 배 모자라서 졌다"
                % (pp, SIZE["🔴 문턱 ÷ 효과(몇 배 모자라나)"]), fontsize=9.2)
    b.set_xlabel("일")

    # (c) 귀무 대 귀무 — 짝지은 BCa 의 거짓 양성률
    c = ax[2]
    fp = NN["🔴 거짓 양성률"]
    pairs = NN["🔴 앞 20 쌍의 짝지은 BCa"]
    labels = ["승", "패", "판정 불능"]
    counts = [sum(1 for q in pairs if q["판정"] == lab) for lab in labels]
    c.bar(labels, counts, color=[RED, RED, GREY], alpha=0.85)
    for i, v in enumerate(counts):
        c.text(i, v + 0.15, str(v), ha="center", fontsize=9)
    c.set_title("(c) 참 귀무끼리 짝지어도 %d/%d = %.0f%% 가 「유의」\n"
                "→ 판정의 근거는 짝지은 구간이 아니라 순열 p 다"
                % (NN["🔴 그중 「유의」로 갈린 쌍(= 참 귀무에서의 거짓 양성)"],
                   len(pairs), fp * 100), fontsize=9.2)
    c.set_ylabel("쌍 수(분모 %d)" % len(pairs))

    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "fig1.pdf"))
    plt.close(fig)


def fig2():
    fig, ax = plt.subplots(1, 3, figsize=(13.2, 3.9))
    g = G408["갈라 센 것"]

    # (a) 408 의 정체 — 조항 60 이 걸렸던 자리
    a = ax[0]
    parts = [
        ("관측률<0.95\n자격 미달", g["  ├ ① 관측률 < 0.95 라 자격 미달(급증을 아예 못 잰다)"]),
        ("자격되나\n급증 0개", g["  ├ ② 자격은 되는데 급증 사건 0개"]),
        ("급증이\n정확히 1개", g["  └ ③ 급증 사건이 정확히 1개(간격은 2개 사건이 있어야 생긴다)"]),
    ]
    a.bar([p[0] for p in parts], [p[1] for p in parts], color=[GREY, BLUE, RED], alpha=0.85)
    for i, p in enumerate(parts):
        a.text(i, p[1] + 4, str(p[1]), ha="center", fontsize=9)
    a.set_title("(a) 408 개 격자의 정체\n홀드아웃 %s - 간격 있는 %s = %d (%.2f%%)"
                % (f"{g['홀드아웃 격자(분모)']:,}",
                   f"{g['🔴 간격이 하나라도 있는 격자(사건 ≥2)']:,}",
                   g["🔴 간격이 0 인 격자"], g["간격 0 인 격자의 비율"] * 100),
                fontsize=9.2)
    a.set_ylabel("격자 수")

    # (b) 행 회계 — 그런데 반올림하면 같은 수
    b = ax[1]
    rows = SIZE["🔴 행 단위로도 세어 본다"]
    base = SIZE["🔴 근거를 실측으로 확인"]
    names = ["시험 팔이\n더 가깝다", "기준 팔이\n더 가깝다", "정확히\n같다"]
    vv = [rows["시험 팔이 더 가까운 행"], rows["기준 팔이 더 가까운 행"], rows["정확히 같은 행"]]
    b.bar(names, vv, color=[RED, BLUE, GREY], alpha=0.85)
    for i, v in enumerate(vv):
        b.text(i, v + 400, f"{v:,}", ha="center", fontsize=8.6)
    b.set_title("(b) 행으로는 순 %s 행이 좋아졌다(분모 %s)\n그런데 MAE %.4f → %.4f, 반올림하면 둘 다 %d 일"
                % (f"{rows['🔴 순(좋아진 − 나빠진) 행']:,}", f"{rows['행(분모)']:,}",
                   base["기준 팔 MAE(일)"], base["시험 팔 MAE(일)"],
                   base["하루 단위로 반올림한 기준 팔 MAE"]), fontsize=9.2)
    b.set_ylabel("행 수")

    # (c) 사전등록의 검출력 예측이 틀렸다 — 자기 적발
    c = ax[2]
    w = POW["🔴 왜 틀렸나 — 세어서 답한다"]
    got = [("사전등록이\n예측한 P(k=0)", w["정규 가정의 P(k=0)"]),
           ("실측", 1.0)]
    c.bar([x[0] for x in got], [x[1] for x in got], color=[GREY, RED], alpha=0.85)
    c.set_ylim(0, 1.14)
    for i, x in enumerate(got):
        c.text(i, x[1] + 0.03, "%.4f" % x[1], ha="center", fontsize=9)
    c.set_title("(c) 자기 적발 — 검출력 계산이 정규 근사 위에 서 있었다\n"
                "정규 기대 k=%.2f · 실측 k=%d → 다음부터 경험분포로"
                % (w["정규 가정의 기대 k"], kk), fontsize=9.2)
    c.set_ylabel("확률")

    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "fig2.pdf"))
    plt.close(fig)


if __name__ == "__main__":
    fig1()
    fig2()
    print("k 재계수 =", k_recount, "· p =", pp, "· 효과(분) =", PERM["🔴 효과(분)"])
    print("크기 판정 =", VERD["§4-나 크기"]["🔴 판정"])
    print("wrote fig1.pdf fig2.pdf")
