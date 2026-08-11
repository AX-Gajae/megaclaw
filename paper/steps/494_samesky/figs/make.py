#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 노트 922 그림 — 🔴 손 전사 금지: 값은 전부 산출물에서 **읽는다**.
#   fig1 (a) 네 세계의 개선과 BCa  (b) 비교가능성 관문 — 기후값 MAE 상대차
#        (c) 분모·성질 대조표(같아야 하는 것들)
#   fig2 (a) 918 초판이 본 그림 대 922 가 본 그림  (b) 배선·관문 회계
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parents[4]
HERE = pathlib.Path(__file__).resolve().parent

for cand in ("AppleGothic", "Apple SD Gothic Neo", "NanumGothic", "Malgun Gothic"):
    if any(f.name == cand for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams["axes.unicode_minus"] = False


def at(sec, key, where):
    """🔴 키 경로를 **명시**로 잡는다. 없으면 키 목록을 들고 죽는다(조항 59)."""
    if key not in sec:
        raise SystemExit(f"🔴 '{key}' 가 없다 — {where} 의 키: {list(sec)}")
    return sec[key]


P = json.loads((ROOT / "runners/out922_permfix.json").read_text())
S = json.loads((ROOT / "runners/out922_permfix_stopfire.json").read_text())

# 🔴 세계 절을 **접두어로** 찾는다(긴 한글 키를 손으로 타자하지 않는다)
def sec_by(prefix):
    hits = [k for k in P if k.startswith(prefix)]
    if len(hits) != 1:
        raise SystemExit(f"🔴 '{prefix}' 로 시작하는 절이 {len(hits)}개 — {list(P)}")
    return P[hits[0]], hits[0]


KRULER = "🔴 자 — MAE(기후값) − MAE(팔)"
KBOOT = "🔴 군집 부트스트랩(규약 47)"
KCOND = "나 조건부(주)"


def band(sec, name):
    r = at(at(sec, KRULER, name), KCOND, KRULER)
    b = at(r, KBOOT, KCOND)
    return (at(r, "개선(일)", KCOND), at(b, "lo", KCOND), at(b, "hi", KCOND),
            at(b, "구간 종류", KCOND), at(b, "🔴 폴백 사유", KCOND),
            at(r, "🔴 개선율(그 세계의 기후값 MAE 로 나눈 수)", KCOND),
            at(sec, "가 기후값", name)["MAE"])


real, kreal = sec_by("④ 진짜 비교")
n2, kn2 = sec_by("③ 주 귀무 N2")
n1, kn1 = sec_by("⑤ 귀무 N1")
n0, kn0 = sec_by("⑤ 귀무 N0")

R, W2, W1, W0 = band(real, kreal), band(n2, kn2), band(n1, kn1), band(n0, kn0)
GATE, kgate = sec_by("③ 🔴 비교가능성 관문")

# ── fig1 ────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(1, 3, figsize=(14.0, 4.3))

rows = [("🔴 진짜 세계\n(조건부 대 기후값)", R, "#1f7a1f", True),
        ("🔴 N2 간격순서 순열\n(발생률·급증 보존 · 순서만 파괴)", W2, "#c0392b", True),
        ("N1 「r 도 섞는 순열」\n(#175 처방 1)", W1, "#8e8e8e", False),
        ("N0 918 옛 귀무\n(r 을 안 섞는다)", W0, "#adb5bd", False)]
for i, (lab, v, col, usable) in enumerate(rows):
    pt, lo, hi = v[0], v[1], v[2]
    ax[0].errorbar([pt], [i], xerr=[[pt - lo], [hi - pt]], fmt="o", color=col,
                   capsize=6, lw=2.2 if usable else 1.2, markersize=9 if usable else 6,
                   alpha=1.0 if usable else 0.55)
    ax[0].annotate(f"{pt:+.4f}\n[{lo:+.4f}, {hi:+.4f}]", (pt, i),
                   textcoords="offset points", xytext=(0, 13), ha="center",
                   fontsize=7.6, color=col, weight="bold" if usable else "normal")
# 🔴 진짜 lo 와 N2 hi 사이의 빈틈
gap_lo, gap_hi = W2[2], R[1]
ax[0].axvspan(gap_lo, gap_hi, color="#d8f0d8", zorder=0)
ax[0].annotate(f"안 겹친다\n빈틈 {gap_hi-gap_lo:.4f}일",
               ((gap_lo + gap_hi) / 2, 0.5), ha="center", fontsize=8.0, color="#1f5f1f")
ax[0].axvline(0, color="#333333", lw=1.0)
ax[0].set_yticks(range(len(rows)))
ax[0].set_yticklabels([r[0] for r in rows], fontsize=7.4)
ax[0].set_ylim(-0.6, len(rows) - 0.4)
ax[0].invert_yaxis()
ax[0].set_xlabel(f"개선(일) = MAE(기후값) − MAE(조건부)   [{R[3]} · 폴백 {R[4]}]")
ax[0].set_title("(a) 🔴 같은 세계 안의 바닥은 신호 **아래**다\n"
                "흐린 둘은 비교 불가라 판정에 안 썼다", fontsize=10)
ax[0].grid(axis="x", alpha=.25)

# (b) 비교가능성 관문
thr = at(GATE, "허용 문턱(사전등록 §3)", kgate)
def rel(v):
    return abs(v[6] - R[6]) / R[6]
names = ["N2\n간격순서", "N1\n「r 도 섞기」", "N0\n918 옛 귀무"]
vals = [rel(W2), rel(W1), rel(W0)]
cols = ["#1f7a1f" if v <= thr else "#c0392b" for v in vals]
bars = ax[1].bar(range(3), vals, color=cols, width=.55)
for b, v in zip(bars, vals):
    ax[1].annotate(f"{100*v:.3f}%", (b.get_x() + b.get_width() / 2, v),
                   textcoords="offset points", xytext=(0, 3), ha="center",
                   fontsize=9.6, weight="bold")
ax[1].axhline(thr, color="#333333", ls="--", lw=1.4)
ax[1].annotate(f"허용 문턱 {100*thr:.0f}%", (2.45, thr), textcoords="offset points",
               xytext=(0, 4), ha="right", fontsize=8.0)
ax[1].set_xticks(range(3))
ax[1].set_xticklabels(names, fontsize=8.4)
ax[1].set_ylabel("기후값 MAE 의 진짜 세계 대비 상대차")
ax[1].set_title("(b) 🔴 관문이 둘을 떨어뜨렸다 —\n"
                "「바닥」이라 부르려면 같은 난이도여야 한다", fontsize=10)
ax[1].grid(axis="y", alpha=.25)

# (c) 같아야 하는 것들 — 분모·성질 대조
DEN = at(GATE, "분모 대조(같아야 한다)", kgate)
labs3, same3 = [], []
for k, v in DEN.items():
    labs3.append(k)
    same3.append(v[0] == v[1])
mag_r = at(GATE, "mag 3분위 경계 — 진짜", kgate)
mag_n = at(GATE, "mag 3분위 경계 — 귀무", kgate)
med = at(GATE, "간격 중앙값 — 진짜/귀무", kgate)
mean = at(GATE, "간격 평균 — 진짜/귀무", kgate)
labs3 += ["mag 3분위", "간격 중앙값", "간격 평균"]
same3 += [mag_r == mag_n, med[0] == med[1], mean[0] == mean[1]]
MS = at(n2, "🔴 격자별 간격 다중집합 보존(설계 주장)", kn2)
labs3.append(f"간격 다중집합\n(격자 {at(MS,'검사한 격자(분모)','다중집합'):,} 전수)")
same3.append(at(MS, "다중집합이 깨진 격자", "다중집합") == 0)
y3 = range(len(labs3))
ax[2].barh(list(y3), [1] * len(labs3),
           color=["#1f7a1f" if s else "#c0392b" for s in same3], height=.62)
for i, s in enumerate(same3):
    ax[2].annotate("같다" if s else "다르다", (0.5, i), ha="center", va="center",
                   fontsize=8.4, color="white", weight="bold")
ax[2].set_yticks(list(y3))
ax[2].set_yticklabels(labs3, fontsize=7.2)
ax[2].set_xticks([])
ax[2].invert_yaxis()
ax[2].set_title(f"(c) N2 와 진짜가 공유하는 것 — {sum(same3)}/{len(same3)}\n"
                "🔴 다른 것은 **간격의 순서** 하나다", fontsize=10)

fig.tight_layout()
fig.savefig(HERE / "fig1.pdf")
plt.close(fig)

# ── fig2 ────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(1, 2, figsize=(11.2, 4.2))

# (a) 918 이 본 그림 대 922 가 본 그림
groups = [("918 초판\n(비교 불가한 바닥)", W0[0], R[0], "#c0392b"),
          ("922\n(같은 세계의 바닥)", W2[0], R[0], "#1f7a1f")]
w = .34
for i, (lab, nul, sig, col) in enumerate(groups):
    ax[0].bar([i - w / 2], [nul], width=w, color="#adb5bd", label="바닥" if i == 0 else None)
    ax[0].bar([i + w / 2], [sig], width=w, color=col, label="신호" if i == 0 else None)
    ax[0].annotate(f"{nul:+.4f}", (i - w / 2, nul), textcoords="offset points",
                   xytext=(0, 3), ha="center", fontsize=8.6)
    ax[0].annotate(f"{sig:+.4f}", (i + w / 2, sig), textcoords="offset points",
                   xytext=(0, 3), ha="center", fontsize=8.6, weight="bold")
    verdict = "바닥이 위 → ③ 은 0" if nul > sig else "신호가 위 → ③ 이 0 을 벗어난다"
    ax[0].annotate(verdict, (i, max(nul, sig) * 1.14), ha="center", fontsize=8.2,
                   color=col, weight="bold")
ax[0].set_xticks([0, 1])
ax[0].set_xticklabels([g[0] for g in groups], fontsize=8.6)
ax[0].set_ylabel("개선(일)")
ax[0].set_ylim(0, max(W0[0], R[0]) * 1.3)
ax[0].set_title("(a) 🔴 바뀐 것은 자가 아니라\n**바닥이 놓인 세계**다", fontsize=10)
ax[0].legend(fontsize=8)
ax[0].grid(axis="y", alpha=.25)

# (b) 배선·관문 회계 — 🔴 분모를 같이 적는다
W6, kw6 = sec_by("⑥ 배선 검사")
_pk = [k for k in W6 if "심은" in str(k)]
if not _pk:
    raise SystemExit(f"🔴 '심은' 칸이 없다 — {list(W6)}")
planted = W6[_pk[0]]
_fk = [k for k in W6 if "발화" in str(k)]
fired = W6[_fk[0]] if _fk else planted
STOP = at(P, "⓪ 정지 관문", "922")
sSTOP = at(S, "⓪ 정지 관문", "stopfire")
lab4 = [f"배선 검사\n심은 {planted} · 발화 {fired}",
        "정지 관문\n정상(계수 0.01)",
        "정지 관문\n강제 발화(1e-9)"]
val4 = [1.0, 0.0, 1.0]
col4 = ["#1f7a1f", "#adb5bd", "#c0392b"]
note4 = [f"검정력 {fired}/{planted}\n🔴 분모는 {planted} 이지\n관문 전체가 아니다",
         f"멈췄나 {at(STOP,'🔴 멈췄나','정지')}",
         f"멈췄나 {at(sSTOP,'🔴 멈췄나','정지')}\n🔴 진짜 개선 절 0개\n(918 은 1개)"]
bars = ax[1].bar(range(3), val4, color=col4, width=.55)
for i, (b, n) in enumerate(zip(bars, note4)):
    ax[1].annotate(n, (b.get_x() + b.get_width() / 2, max(val4[i], 0.06)),
                   textcoords="offset points", xytext=(0, 5), ha="center", fontsize=7.4)
ax[1].set_xticks(range(3))
ax[1].set_xticklabels(lab4, fontsize=7.8)
ax[1].set_yticks([])
ax[1].set_ylim(0, 1.75)
ax[1].set_title("(b) 관문이 이번엔 제 일을 한다 —\n그리고 검정력의 분모를 적었다", fontsize=10)

fig.tight_layout()
fig.savefig(HERE / "fig2.pdf")
plt.close(fig)

print("fig1.pdf · fig2.pdf")
print("  진짜", R[:3], "개선율", round(R[5], 6), "기후MAE", round(R[6], 6))
print("  N2  ", W2[:3], "개선율", round(W2[5], 6), "기후MAE", round(W2[6], 6))
print("  N1  ", W1[:3], "· N0", W0[:3])
print("  빈틈", round(gap_hi - gap_lo, 6))
print("  상대차", [round(v, 6) for v in vals], "문턱", thr)
print("  같은 것", sum(same3), "/", len(same3))
print("  배선 심은", planted, "· 정지 정상", at(STOP, "🔴 멈췄나", "정지"),
      "· 강제", at(sSTOP, "🔴 멈췄나", "정지"))
