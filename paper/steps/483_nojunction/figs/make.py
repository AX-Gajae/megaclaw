"""노트 897 그림 — 🔴 **값은 전부 산출물 json 에서 읽는다. 손 전사 금지**(루프 ⑥).

    python3 paper/steps/483_nojunction/figs/make.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402
from matplotlib import font_manager      # noqa: E402

ROOT = Path("/Users/ax/world_model")
R = ROOT / "runners"
HERE = Path(__file__).resolve().parent

for f in ("AppleSDGothicNeo.ttc", "AppleGothic.ttf"):
    p = Path("/System/Library/Fonts") / f
    if p.exists():
        font_manager.fontManager.addfont(str(p)) if p.suffix == ".ttf" else None
plt.rcParams["font.family"] = ["AppleGothic", "Apple SD Gothic Neo", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

G = json.loads((R / "out897_graph.json").read_text())
DE = json.loads((R / "out897_decay.json").read_text())
PL = json.loads((R / "out897_placebo.json").read_text())
CT = json.loads((R / "out897_control.json").read_text())
PA = json.loads((R / "out897_partial.json").read_text())
NC = json.loads((R / "out897_nnchk.json").read_text())

BLUE, RED, GRAY, GREEN = "#1f4e79", "#c0392b", "#8a8a8a", "#1e8449"


# ── 그림 1 ────────────────────────────────────────────────────────────
def fig1():
    fig, ax = plt.subplots(1, 3, figsize=(15.2, 4.5))

    # (a) 배선 --- 조각별 호출자 수
    cnt = G["조각별 호출자 수"]
    orph = set(G["🔴 아무도 안 부르는 조각"])
    ks = sorted(cnt, key=lambda k: cnt[k])
    v = [cnt[k] for k in ks]
    cols = [RED if k in orph else BLUE for k in ks]
    ax[0].barh(range(len(ks)), v, color=cols)
    ax[0].set_xlim(0, max(v) * 1.15)
    ax[0].set_yticks(range(len(ks)))
    ax[0].set_yticklabels([k.replace("state.", "").replace("lab.", "") for k in ks],
                          fontsize=8)
    ax[0].set_xlabel("이 조각을 반입하는 파일 수", fontsize=9)
    ax[0].set_title(f"(a) 0단계 — 조각은 있는데 다리가 없다\n"
                    f"파이썬 {G['파이썬 파일 수']}개 전수 AST 스캔", fontsize=10)
    for i, k in enumerate(ks):
        if k in orph:
            ax[0].text(1.0, i, " 아무도 안 부른다", va="center", fontsize=7.5, color=RED)
    ax[0].text(0.30, 0.06,
               "장 ∩ 텍스트 = %d개\n장 ∩ 공유인코더·파운데이션 = %d개\n"
               "두 축 이름이 같이 나오는 파일 = %d개"
               % (len(G["🔴 장 ∩ 텍스트(같은 파일이 둘 다 반입)"]),
                  len(G["🔴 장 ∩ 공유인코더·파운데이션"]),
                  len([f for f in G["🔴 두 축 이름이 같이 나오는 파일"]
                       if not f.endswith("wire897")])),
               transform=ax[0].transAxes, fontsize=8.5, va="bottom", ha="left",
               bbox=dict(fc="#fdf2f2", ec=RED, lw=0.8))

    # (b) 도메인별 --- 부호를 학습으로 고정한 유보 ρ
    per = DE["진짜"]["도메인"]
    u1 = DE["진짜"]["1열"]["도메인별 기여"]
    u8 = DE["진짜"]["표현"]["도메인별 기여"]
    doms = sorted(u8, key=lambda d: -u8[d]["n"])
    x = range(len(doms))
    a1 = [u1[d]["sign"] * u1[d]["유보ρ"] for d in doms]
    a8 = [u8[d]["sign"] * u8[d]["유보ρ"] for d in doms]
    w = 0.38
    ax[1].bar([i - w / 2 for i in x], a1, w, color=GRAY, label="1열(현행 축)")
    ax[1].bar([i + w / 2 for i in x], a8, w, color=BLUE, label="표현 8열")
    deg = set(CT["ㄹ 퇴화 도메인 제외"]["뺀 도메인(유보 고유날 < 10)"])
    ax[1].set_xticks(list(x))
    ax[1].set_xticklabels([(d + " ▲" if d in deg else d) for d in doms],
                          rotation=45, ha="right", fontsize=8)
    ax[1].axhline(0, color="k", lw=0.7)
    ax[1].set_ylabel("sign(학습ρ) × 유보ρ", fontsize=9)
    ax[1].legend(fontsize=8)
    ax[1].set_title("(b) 1단계 — 표현이 1열보다 남는다\n▲ = 유보 고유날 < 10 (퇴화)",
                    fontsize=10)

    # (c) 팔별 헤드라인 S
    rows = []
    d1, d8 = DE["진짜"]["1열"], DE["진짜"]["표현"]
    rows.append(("1열 (현행 축)", d1["헤드라인 S"], d1["순열 널"]["널 2σ"],
                 d1["군집 BCa"]["lo"], d1["군집 BCa"]["hi"], GRAY))
    rows.append(("표현 8열", d8["헤드라인 S"], d8["순열 널"]["널 2σ"],
                 d8["군집 BCa"]["lo"], d8["군집 BCa"]["hi"], BLUE))
    for a in PL["팔"]:
        rows.append((a["태그"], a["표현"]["헤드라인 S"], None, None, None, "#c9c9c9"))
    c = CT["ㄷ 시간 대용 통제"]
    rows.append(("시간 RBF 8열", c["표현"]["S"], c["순열 널(시간 8열)"]["널 2σ"],
                 c["군집 BCa(시간 8열)"]["lo"], c["군집 BCa(시간 8열)"]["hi"], GREEN))
    for tag, col in (("ㅂ-1 시각만 · 퇴화 제외", GREEN),
                     ("ㅂ-3 장만 · 퇴화 제외", BLUE),
                     ("ㅂ-2 시각+장 · 퇴화 제외", RED)):
        a = PA["팔"][tag]
        rows.append((tag.replace(" · 퇴화 제외", "\n(퇴화 제외)"), a["S"],
                     a["순열 널"]["널 2σ"], a["군집 BCa"]["lo"], a["군집 BCa"]["hi"], col))
    y = range(len(rows))
    for i, (nm, s, n2, lo, hi, col) in enumerate(rows):
        if lo is not None:
            ax[2].plot([lo, hi], [i, i], color=col, lw=2.2, alpha=0.55)
            ax[2].plot([lo, lo], [i - .16, i + .16], color=col, lw=1.4)
            ax[2].plot([hi, hi], [i - .16, i + .16], color=col, lw=1.4)
        if n2 is not None:
            ax[2].plot([-n2, n2], [i + .30, i + .30], color="k", lw=1.0, alpha=0.5)
        ax[2].plot([s], [i], "o", color=col, ms=6, zorder=5)
    ax[2].axvline(0, color="k", lw=0.7)
    ax[2].set_yticks(list(y))
    ax[2].set_yticklabels([r[0] for r in rows], fontsize=7.5)
    ax[2].invert_yaxis()
    ax[2].set_xlabel("헤드라인 S = Σ n·sign(학습ρ)·유보ρ / Σ n", fontsize=9)
    ax[2].set_title("(c) 굵은 선 = 날짜 군집 BCa 95%\n"
                    "얇은 가로선 = 순열 널 ±2σ", fontsize=10)
    fig.tight_layout()
    fig.savefig(HERE / "fig1.pdf")


# ── 그림 2 ────────────────────────────────────────────────────────────
def fig2():
    fig, ax = plt.subplots(1, 3, figsize=(14.6, 4.1))

    # (a) 입력 지우기
    ab = NC["§9.1 배선 검사 여덟 — 이 사이클에서 돈 것"]["⑥ 입력 지우기"]
    ks = [k for k in ab if k != "뜻"]
    v = [ab[k]["‖Δ표현‖/‖표현‖"] for k in ks]
    cols = [RED if x == max(v) else BLUE for x in v]
    ax[0].bar(range(len(ks)), v, color=cols)
    ax[0].set_xticks(range(len(ks)))
    ax[0].set_xticklabels([k.replace(" ", "\n", 1) for k in ks], fontsize=8)
    ax[0].set_ylabel("‖Δ표현‖ / ‖표현‖ (갈래를 0 으로)", fontsize=9)
    ax[0].set_title("(a) 배선검사 6 입력 지우기 — 표현의 대부분이\n입력과 무관한 상수(동네 임베딩)다",
                    fontsize=10)
    for i, x in enumerate(v):
        ax[0].text(i, x + .01, f"{x:.3f}", ha="center", fontsize=8)

    # (b) 한 배치 과적합
    of = NC["§9.1 배선 검사 여덟 — 이 사이클에서 돈 것"]["① 한 배치 과적합"]
    st = [h["step"] for h in of["이력"]]
    ls = [h["loss"] for h in of["이력"]]
    ax[1].plot(st, ls, "-o", color=BLUE, ms=3)
    ax[1].axhline(of["첫 손실"] * 0.05, color=RED, ls="--", lw=1,
                  label="문턱 = 첫 손실 × 0.05")
    ax[1].set_yscale("log")
    ax[1].set_xlabel("걸음", fontsize=9)
    ax[1].set_ylabel("손실(로그)", fontsize=9)
    ax[1].legend(fontsize=8)
    ax[1].set_title("(b) 배선검사 1 한 배치 과적합 — 통과\n"
                    f"{of['첫 손실']:.4f} → {of['끝 손실']:.6f} (비율 {of['비율']:.4f})"
                    f" · 죽은 층 {len(of['🔴 죽은 층(‖Δθ‖ == 0)'])}",
                    fontsize=10)

    # (c) 표현 8열의 날짜 상관
    dr = CT["표현 열의 날짜 상관(스피어만)"]
    ks = list(dr)
    v = [dr[k] for k in ks]
    ax[2].bar(range(len(ks)), v, color=[RED if abs(x) > .45 else GRAY for x in v])
    ax[2].axhline(0, color="k", lw=0.7)
    for s in (0.45, -0.45):
        ax[2].axhline(s, color=RED, ls=":", lw=0.8)
    ax[2].set_xticks(range(len(ks)))
    ax[2].set_xticklabels([k.replace("열 ", "") for k in ks], fontsize=8)
    ax[2].set_xlabel("표현 요약 열 번호 (0~3 평균 · 4~7 산포)", fontsize=9)
    ax[2].set_ylabel("날짜와의 스피어만", fontsize=9)
    ax[2].set_title("(c) 왜 시각이 이기나 — 표현 8열이\n날짜와 세게 단조다",
                    fontsize=10)
    fig.tight_layout()
    fig.savefig(HERE / "fig2.pdf")


if __name__ == "__main__":
    fig1()
    fig2()
    print("→", HERE / "fig1.pdf", HERE / "fig2.pdf")
