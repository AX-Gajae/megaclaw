"""노트 898 그림 — 🔴 **값은 전부 산출물 json 에서 읽는다. 손 전사 금지**(루프 ⑥).

    python3 paper/steps/484_oneruler/figs/make.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402
from matplotlib import font_manager      # noqa: E402

ROOT = Path("/Users/ax/world_model")
R = ROOT / "runners"
HERE = Path(__file__).resolve().parent

for f in ("AppleSDGothicNeo.ttc", "AppleGothic.ttf"):
    p = Path("/System/Library/Fonts") / f
    if p.exists() and p.suffix == ".ttf":
        font_manager.fontManager.addfont(str(p))
plt.rcParams["font.family"] = ["AppleGothic", "Apple SD Gothic Neo", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

V = json.loads((R / "out898_verdict.json").read_text())
W = json.loads((R / "out898_wire.json").read_text())
BD = json.loads((R / "out898_board.json").read_text())

BLUE, RED, GRAY, GREEN = "#1f4e79", "#c0392b", "#8a8a8a", "#1e8449"


def fig1():
    fig, ax = plt.subplots(1, 3, figsize=(15.2, 4.6))

    # (a) 동률 --- 채점행 대 예측 고유값
    tie = W["ㄴ 동률"]
    ks = sorted(tie, key=lambda d: -tie[d]["동률 비율"])
    rat = [tie[d]["동률 비율"] for d in ks]
    cols = [RED if r > 0.3 else BLUE for r in rat]
    ax[0].barh(range(len(ks)), rat, color=cols)
    ax[0].set_yticks(range(len(ks)))
    ax[0].set_yticklabels(
        [f"{d} {tie[d]['채점행(post∩라벨유한∩예측유한)']}행→{tie[d]['예측 고유값']}" for d in ks],
        fontsize=8)
    ax[0].invert_yaxis()
    ax[0].set_xlabel("동률 비율 = 1 − 예측 고유값/채점행")
    ax[0].set_title("(a) 동률은 예외가 아니다 — 두 도메인은 자료의 성질이다", fontsize=10)

    # (b) 씨앗별 짝 Δ + BCa + 문턱
    dd = np.array(BD["짝 Δ"]["짝 Δ(B−A) 씨앗별"], float)
    ci = BD["① 씨앗 짝 BCa(주)"]
    thr = V["자(문턱)"]["팔 B(동률 평균 · 891 이 이미 쓰던 것)"]["R5(전정밀)"]
    ax[1].plot(range(len(dd)), dd, "o", color=BLUE, ms=6, label="씨앗별 짝 Δ")
    ax[1].axhline(ci["점추정"], color=RED, lw=1.6,
                  label=f"평균 {ci['점추정']:+.5f}")
    ax[1].axhspan(ci["lo"], ci["hi"], color=RED, alpha=.12,
                  label=f"BCa 95% [{ci['lo']:+.5f}, {ci['hi']:+.5f}]")
    ax[1].axhline(0, color="k", lw=.8)
    ax[1].axhline(thr, color=GREEN, ls="--", lw=1.2,
                  label=f"채택 문턱 {thr:.5f}")
    ax[1].set_xlabel("씨앗")
    ax[1].set_ylabel("Δ = 동률평균 − 서수 (판 ρ)")
    ax[1].set_title("(b) 12씨앗 전량 · 완전 짝(같은 적합·같은 예측)", fontsize=10)
    ax[1].legend(fontsize=7, loc="best")

    # (c) 판 기여 Δ (1e-4 단위 · 선형) --- 도메인 Δ 와 양수 씨앗 수를 글자로 병기
    per = BD["도메인별"]
    ds = sorted(per, key=lambda d: per[d]["판 기여 Δ"])
    y = np.arange(len(ds))
    v = [per[d]["판 기여 Δ"] * 1e4 for d in ds]
    ax[2].barh(y, v, color=[RED if x < 0 else BLUE for x in v])
    ax[2].set_yticks(y)
    ax[2].set_yticklabels(ds, fontsize=8)
    ax[2].axvline(0, color="k", lw=.8)
    tot = BD["짝 Δ"]["평균"] * 1e4
    for i, d in enumerate(ds):
        p = per[d]
        ax[2].text(max(v[i], 0.0) + .15, i,
                   f"도메인 Δ {p['Δ 평균']:+.5f} ({p['Δ 양수 씨앗']}/12)",
                   va="center", ha="left", fontsize=6.6)
    ax[2].set_xlim(-1.6, 8.4)
    ax[2].set_xlabel("판 기여 Δ  ($\\times 10^{-4}$)")
    ax[2].set_title(f"(c) 어느 도메인이 움직이나 — 합 {tot:+.3f}e-4 중 "
                    f"시장팝업이 98.4%", fontsize=10)

    fig.tight_layout()
    fig.savefig(HERE / "fig1.pdf")
    plt.close(fig)


def fig2():
    fig, ax = plt.subplots(1, 2, figsize=(10.6, 4.4))

    # (a) 행 순서 의존성
    o = BD["R-1 행 순서 의존성"]["도메인별"]
    r1 = BD["R-1 행 순서 의존성"]
    ks = sorted(o, key=lambda d: -o[d]["A 폭"])
    x = np.arange(len(ks))
    ax[0].bar(x, [o[d]["A 폭"] for d in ks], .62, color=RED,
              label="서수(state/rank_test.py)")
    ax[0].set_yscale("log")
    ax[0].set_ylim(3e-4, 1.0)
    ax[0].yaxis.set_major_formatter(plt.FuncFormatter(
        lambda v, _: ("%g" % v).replace("−", "-")))
    ax[0].set_xticks(x)
    ax[0].set_xticklabels(ks, rotation=60, fontsize=8, ha="right")
    ax[0].set_ylabel("행을 20번 섞었을 때 나온 $\\rho$ 의 폭")
    ax[0].set_title("(a) P1 — 통계량이 행 순서에 의존하면 안 된다", fontsize=10)
    ax[0].text(.98, .93,
               f"서수: {len(r1['A 가 순서 의존인 도메인'])}/12 도메인이 갈린다 "
               f"(최대 {r1['A 최대 폭']:.5f})\n"
               f"동률 평균: {len(r1['B 가 순서 의존인 도메인'])}/12 · "
               f"폭 = {r1['B 최대 폭']:.1f} (정확히 0 — 그려지지 않는다)",
               transform=ax[0].transAxes, ha="right", va="top", fontsize=7.6,
               bbox=dict(fc="white", ec=GRAY, lw=.6, alpha=.92))

    # (b) 문턱 두 팔
    t = V["자(문턱)"]
    names = ["팔 B\n(동률 평균)", "팔 A\n(서수로 통일했다면)"]
    vals = [t["팔 B(동률 평균 · 891 이 이미 쓰던 것)"]["R5(전정밀)"],
            t["팔 A(서수로 통일했다면)"]["R5(전정밀)"]]
    ax[1].bar(names, vals, color=[BLUE, RED], width=.5)
    ax[1].axhspan(0.00312, 0.00393, color=GRAY, alpha=.2,
                  label="티처 #54 방어 대역 0.00312~0.00393")
    ax[1].axhline(t["891 이 인쇄한 값"], color="k", ls=":", lw=1.2,
                  label=f"891 이 인쇄한 값 {t['891 이 인쇄한 값']}")
    for i, v in enumerate(vals):
        ax[1].text(i, v + 6e-5, f"{v:.5f}", ha="center", fontsize=9)
    ax[1].set_ylim(0, max(vals) * 1.35)
    ax[1].set_ylabel("채택 문턱 R5 = 2·√(씨앗² + 행짝²)")
    ax[1].set_title("(b) 자는 이미 동률 평균이었다 — 팔 B 는 자를 안 움직인다",
                    fontsize=10)
    ax[1].legend(fontsize=7, loc="lower right")

    fig.tight_layout()
    fig.savefig(HERE / "fig2.pdf")
    plt.close(fig)


if __name__ == "__main__":
    fig1()
    fig2()
    print("fig1.pdf fig2.pdf")
