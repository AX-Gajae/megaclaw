#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 노트 918·919 그림 — 🔴 손 전사 금지: 값은 전부 산출물에서 **읽는다**.
#   fig1 (918) (a) 신호 대 순열 바닥 BCa  (b) 팔 넷의 개선  (c) τ 민감도
#   fig2 (919) (a) 부착 전/후  (b) 실패를 셋으로 갈라 셈  (c) 교차확인 — 회복분 대 옛 행
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


IV = json.loads((ROOT / "runners/out918_interval.json").read_text())
WR = json.loads((ROOT / "runners/out918_wire.json").read_text())
GC = json.loads((ROOT / "runners/out919_geocode.json").read_text())

KARM = "팔별"
KMAIN = "τ=1.2 🔴 주"
KPERM = "🔴 ② 순열 귀무(진짜 비교보다 먼저 돌렸다)"
KREAL = "🔴 ④ 진짜 비교"
KRULER = "🔴 자 — MAE(기후값) − MAE(팔)"
KBOOT = "🔴 군집 부트스트랩(규약 47)"
KCOND = "나 조건부(주)"

M = at(at(IV, KARM, "918"), KMAIN, "팔별")
PERM = at(M, KPERM, KMAIN)
REAL = at(M, KREAL, KMAIN)


def band(sec, arm):
    b = at(at(at(sec, KRULER, "절"), arm, KRULER), KBOOT, arm)
    return (at(at(sec, KRULER, "절")[arm], "개선(일)", arm),
            at(b, "lo", arm), at(b, "hi", arm), at(b, "구간 종류", arm),
            at(b, "🔴 폴백 사유", arm), at(b, "판정", arm))


sig = band(REAL, KCOND)          # 진짜 신호
nul = band(PERM, KCOND)          # 🔴 순열 귀무 — 진짜보다 **먼저** 돌렸다

# ── fig1 ────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(1, 3, figsize=(13.6, 4.2))

# (a) 신호 대 바닥 — 두 구간이 겹치나
items = [("🔴 순열 귀무\n(사건 날짜를 격자 안에서 섞음)", nul, "#c0392b"),
         ("진짜 비교\n(조건부 대 기후값)", sig, "#1f7a1f")]
for i, (lab, (pt, lo, hi, kind, fb, vd), col) in enumerate(items):
    ax[0].errorbar([pt], [i], xerr=[[pt - lo], [hi - pt]], fmt="o", color=col,
                   capsize=6, lw=2.4, markersize=9)
    ax[0].annotate(f"{pt:+.4f}\n[{lo:+.4f}, {hi:+.4f}]", (pt, i),
                   textcoords="offset points", xytext=(0, 16), ha="center",
                   fontsize=8.4, color=col, weight="bold")
ax[0].axvline(0, color="#333333", lw=1.0)
# 🔴 두 구간 사이의 빈틈 — 겹치지 않는다는 사실 자체를 그린다
gap_lo, gap_hi = sig[2], nul[1]          # 신호 hi, 바닥 lo
ax[0].axvspan(gap_lo, gap_hi, color="#f6d5d5", zorder=0)
ax[0].annotate(f"겹치지 않는다\n빈틈 {gap_hi-gap_lo:.4f}일",
               ((gap_lo + gap_hi) / 2, 0.5), ha="center", fontsize=8.0, color="#8e2f2f")
ax[0].set_yticks([0, 1])
ax[0].set_yticklabels([it[0] for it in items], fontsize=8.0)
ax[0].set_ylim(-0.6, 1.6)
ax[0].set_xlabel(f"개선(일) = MAE(기후값) − MAE(조건부)   [{sig[3]} · 폴백 {sig[4]}]")
ax[0].set_title("(a) 🔴 바닥이 신호보다 **위**에 있다\n섞은 쪽이 더 잘 맞는다", fontsize=10)
ax[0].grid(axis="x", alpha=.25)

# (b) 팔 넷
arms = [KCOND, "다 조건부(보조)", "라 무정보"]
labs, pts, los, his, cols = [], [], [], [], []
for a in arms:
    pt, lo, hi, kind, fb, vd = band(REAL, a)
    labs.append(a.split(" ", 1)[1] + f"\n({vd})")
    pts.append(pt)
    los.append(pt - lo)
    his.append(hi - pt)
    cols.append("#1f7a1f" if vd == "승" else "#c0392b")
y = range(len(arms))
ax[1].errorbar(pts, list(y), xerr=[los, his], fmt="s", ecolor="#8e8e8e",
               capsize=5, lw=0, elinewidth=1.8, markersize=0)
for i, (p, c) in enumerate(zip(pts, cols)):
    ax[1].plot([p], [i], "s", color=c, markersize=9)
    ax[1].annotate(f"{p:+.3f}", (p, i), textcoords="offset points", xytext=(0, 10),
                   ha="center", fontsize=8.6, weight="bold", color=c)
ax[1].axvline(0, color="#333333", lw=1.0)
ax[1].set_yticks(list(y))
ax[1].set_yticklabels(labs, fontsize=8.0)
ax[1].set_xlabel(f"개선(일) · 홀드아웃 간격 {at(REAL,'홀드아웃 간격 수(분모)',KREAL):,} · "
                 f"군집(격자) {at(REAL,'홀드아웃 격자(군집) 수',KREAL):,}")
ax[1].set_title("(b) 이긴 팔은 하나뿐이고\n그 하나도 (a) 의 바닥을 못 넘는다", fontsize=10)
ax[1].grid(axis="x", alpha=.25)

# (c) τ 민감도
taus = []
for k in at(IV, KARM, "918"):
    sec = at(IV, KARM, "918")[k]
    key = KREAL if KREAL in sec else "진짜 비교(민감도 · 덮음 생략)"
    if key not in sec:
        continue
    pt, lo, hi, kind, fb, vd = band(sec[key], KCOND)
    taus.append((k, pt, lo, hi))
taus.sort(key=lambda t: float(t[0].split("=")[1].split()[0]))
xs = range(len(taus))
ax[2].errorbar([t[1] for t in taus], list(xs),
               xerr=[[t[1] - t[2] for t in taus], [t[3] - t[1] for t in taus]],
               fmt="o", color="#1f4e79", capsize=5, lw=0, elinewidth=1.8, markersize=8)
for i, t in enumerate(taus):
    ax[2].annotate(f"{t[1]:+.3f}", (t[1], i), textcoords="offset points", xytext=(0, 10),
                   ha="center", fontsize=8.4)
# 🔴 주 팔의 순열 바닥을 같은 축에 긋는다 — 민감도 전부가 그 아래인지 보이게
ax[2].axvline(nul[0], color="#c0392b", ls="--", lw=1.6,
              label=f"🔴 τ=1.2 의 순열 바닥 {nul[0]:+.3f}")
ax[2].axvline(0, color="#333333", lw=1.0)
ax[2].set_yticks(list(xs))
ax[2].set_yticklabels([t[0].replace(" 🔴 주", " (주)") for t in taus], fontsize=8.4)
ax[2].set_xlabel("개선(일)")
ax[2].set_title("(c) 문턱 τ 를 바꿔도 바닥 아래다\n(바닥은 τ=1.2 에서만 쟀다)", fontsize=10)
ax[2].legend(fontsize=7.4, loc="lower right")
ax[2].grid(axis="x", alpha=.25)

fig.tight_layout()
fig.savefig(HERE / "fig1.pdf")
plt.close(fig)

# ── fig2 (919) ──────────────────────────────────────────────────────────
fig, ax = plt.subplots(1, 3, figsize=(13.6, 4.2))

KSELF = "② 🔴 자기시험 — 회복 전 값이 915 와 같은가"
KAFT = "④ 🔴 회복 전 / 후"
KX = "④-나 🔴 회복이 진짜인가 — 교차확인과 보수적 수"
KSPL = "③ 회복 — 🔴 실패를 셋으로 갈라 센다 (조항 59)"

SELF = at(GC, KSELF, "919")
AFT = at(at(GC, KAFT, "919"), "회복 후 전체 계수", KAFT)
before = at(at(SELF, "내 코드", KSELF), "🔴 격자 + 날짜 둘 다", "내 코드")
gbefore = at(SELF, "🔴 서로 다른 격자 — 내 값", KSELF)
after = at(AFT, "🔴 격자 + 날짜 둘 다", "회복 후")
gafter = at(AFT, "🔴 서로 다른 격자(군집)", "회복 후")
UNION = at(at(SELF, "내 코드", KSELF), "분모", "내 코드")

# (a) 부착 전/후 + 문턱 + 🔴 원리상 상한
groups = [("붙는 행", before, after, 200, "#1f7a1f"),
          ("서로 다른 격자\n(군집)", gbefore, gafter, 60, "#5b7fa6")]
w = 0.34
for i, (lab, b, a_, thr, col) in enumerate(groups):
    ax[0].bar([i - w / 2], [b], width=w, color="#adb5bd", label="회복 전" if i == 0 else None)
    ax[0].bar([i + w / 2], [a_], width=w, color=col, label="회복 후" if i == 0 else None)
    ax[0].annotate(str(b), (i - w / 2, b), textcoords="offset points", xytext=(0, 3),
                   ha="center", fontsize=9)
    ax[0].annotate(f"{a_}\n({a_-b:+d})", (i + w / 2, a_), textcoords="offset points",
                   xytext=(0, 3), ha="center", fontsize=9.4, weight="bold")
    ax[0].hlines(thr, i - .45, i + .45, color="#c0392b", ls="--", lw=1.6)
    ax[0].annotate(f"문턱 {thr}", (i + .45, thr), textcoords="offset points",
                   xytext=(-4, 4), ha="right", fontsize=7.6, color="#c0392b")
# 🔴 원리상 상한 — 유보 합집합
ax[0].hlines(UNION, -.5, .5, color="#8e5aa6", ls=":", lw=2.0)
ax[0].annotate(f"🔴 원리상 상한 {UNION}\n(팝업 두 도메인 유보 합집합)", (0, UNION),
               textcoords="offset points", xytext=(0, 6), ha="center",
               fontsize=7.6, color="#8e5aa6")
ax[0].set_xticks([0, 1])
ax[0].set_xticklabels([g[0] for g in groups], fontsize=9)
ax[0].set_ylabel(f"수 (분모 — 유보 합집합 {UNION})")
ax[0].set_title("(a) 🔴 상한이 문턱보다 낮다 —\n지오코딩 전에 계산할 수 있던 사실", fontsize=10)
ax[0].legend(fontsize=8)
ax[0].grid(axis="y", alpha=.25)

# (b) 실패를 셋으로
SPL = at(GC, KSPL, "919")
G = at(SPL, "🔴 지오코딩 결과 갈래", KSPL)
rec = sum(v for k, v in G.items() if not str(k).startswith("🔴"))
fail = sum(v for k, v in G.items() if str(k).startswith("🔴"))
nocol = at(AFT, "🔴 좌표 열이 없다(링크가 안 닿는다)", "회복 후")
labs2 = [f"회복했다\n{rec}", f"지오코딩이\n실패했다 {fail}", f"좌표 열을\n못 찾았다 {nocol}"]
vals2 = [rec, fail, nocol]
bars = ax[1].bar(range(3), vals2, color=["#1f7a1f", "#e8a33d", "#8e8e8e"], width=.6)
for b, v in zip(bars, vals2):
    ax[1].annotate(str(v), (b.get_x() + b.get_width() / 2, v), textcoords="offset points",
                   xytext=(0, 3), ha="center", fontsize=10, weight="bold")
ax[1].set_xticks(range(3))
ax[1].set_xticklabels(labs2, fontsize=8.2)
ax[1].set_ylabel("레코드 수")
ax[1].set_title("(b) 🔴 셋은 서로 다른 것이다(조항 59)\n"
                "「없다」와 「못 찾았다」와 「실패했다」", fontsize=10)
ax[1].grid(axis="y", alpha=.25)

# (c) 교차확인 — 회복분 대 옛 행 (음성 대조)
X = at(GC, KX, "919")
newx = at(X, "🔴 교차확인 — 회복분", KX)
oldx = at(X, "🔴 교차확인 — 회복 전부터 붙던 행(같은 자 · 음성 대조)", KX)
pairs = [(f"회복분\n(분모 {at(newx,'분모','회복분')})", at(newx, "일치율", "회복분"), "#1f7a1f"),
         (f"회복 전부터 붙던 행\n(분모 {at(oldx,'분모','옛 행')})", at(oldx, "일치율", "옛 행"), "#8e8e8e")]
bars = ax[2].bar(range(2), [p[1] for p in pairs], color=[p[2] for p in pairs], width=.5)
for b, p in zip(bars, pairs):
    ax[2].annotate(f"{p[1]:.4f}", (b.get_x() + b.get_width() / 2, p[1]),
                   textcoords="offset points", xytext=(0, 3), ha="center",
                   fontsize=10, weight="bold")
ax[2].set_xticks(range(2))
ax[2].set_xticklabels([p[0] for p in pairs], fontsize=8.2)
ax[2].set_ylim(0, 1.0)
ax[2].set_ylabel("좌표의 구 == 레코드가 적은 구")
ax[2].set_title("(c) 어긋남은 회복이 만든 게 아니다 —\n옛 행도 같은 자리에 있다", fontsize=10)
ax[2].grid(axis="y", alpha=.25)

fig.tight_layout()
fig.savefig(HERE / "fig2.pdf")
plt.close(fig)

print("fig1.pdf · fig2.pdf")
print("  918 신호", sig)
print("  918 바닥", nul)
print("  918 빈틈", round(gap_hi - gap_lo, 5))
print("  918 τ", taus)
print("  919 부착", before, "→", after, "· 격자", gbefore, "→", gafter, "· 상한", UNION)
print("  919 갈래", rec, fail, nocol)
print("  919 교차", at(newx, "일치율", "회복분"), at(oldx, "일치율", "옛 행"))
print("  918 배선 검정력", at(at(WR, "🔴 검정력", "wire"), "🔴 검정력", "검정력"))
