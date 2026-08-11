#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 노트 925 그림 — 🔴 손 전사 금지: 값은 전부 산출물에서 **읽는다**.
#   fig1 (a) 네 절제 × 두 세계  (b) 관문 비(도달 가능 폭 ÷ 문턱)  (c) 바닥을 바꾸면
#   fig2 (a) 가장자리 절  (b) 구간 덮음 눈금  (c) 배선 — 분모 둘
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


D = json.loads((ROOT / "runners/out925_gapsplit.json").read_text())


def sec_by(prefix):
    hits = [k for k in D if k.startswith(prefix)]
    if len(hits) != 1:
        raise SystemExit(f"🔴 '{prefix}' 로 시작하는 절이 {len(hits)}개 — {list(D)}")
    return D[hits[0]], hits[0]


EIGHT, k8 = sec_by("④ 여덟 수")
GATES, kg = sec_by("⑥ 관문 신고")
EDGE, ke = sec_by("⑤-가")
FLOOR, kf = sec_by("⑤-나")
COV, kc = sec_by("⑤-다")
WIRE, kw = sec_by("⑦ 배선 검사")

ABL = [k for k in EIGHT if not k.startswith("🔴")]

# ── fig1 ────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(1, 3, figsize=(14.2, 4.3))

# (a) 네 절제 × 두 세계
ys = []
for i, a in enumerate(ABL):
    s = EIGHT[a]
    for j, (arm, col, off) in enumerate([("진짜", "#1f7a1f", -0.17), ("N2", "#c0392b", 0.17)]):
        v = at(s, arm, a)
        pt, lo, hi = at(v, "개선(일)", arm), at(v, "BCa", arm)[0], at(v, "BCa", arm)[1]
        ax[0].errorbar([pt], [i + off], xerr=[[pt - lo], [hi - pt]], fmt="o",
                       color=col, capsize=4, lw=1.9, markersize=7)
        ax[0].annotate(f"{pt:.4f}", (pt, i + off), textcoords="offset points",
                       xytext=(0, 8 if j == 0 else -13), ha="center", fontsize=7.0, color=col)
    g = at(s, "🔴 관문", a)
    ok = at(g, "🔴 안 겹치나(진짜 lo > 귀무 hi)", "관문")
    ax[0].annotate("안 겹침" if ok else "🔴 겹친다", (0.005, i),
                   xycoords=("axes fraction", "data"), fontsize=7.6,
                   color="#1f7a1f" if ok else "#c0392b",
                   weight="normal" if ok else "bold", va="center")
ax[0].set_yticks(range(len(ABL)))
ax[0].set_yticklabels(ABL, fontsize=8.4)
ax[0].invert_yaxis()
ax[0].set_xlabel("개선(일) = MAE(기후값) − MAE(조건부)")
ax[0].set_title("(a) 절제를 둘 다 걸면 겹친다\n🔴 주 판정 판은 맨 아래 [둘 다]", fontsize=10)
ax[0].grid(axis="x", alpha=.25)

# (b) 관문 비 — 🔴 1 미만이면 검정력 0
G1 = at(GATES, "G1 주 판정", kg)
rows = [("G1 주 판정\n(빈틈)", at(G1, "🔴 비(|기대 빈틈| ÷ MDE)", "G1"),
         at(G1, "🔴 검정력 0 인가(비 < 1 이면 자동)", "G1"))]
for name in ("G2", "G3", "G4"):
    if name in GATES:
        g = GATES[name]
        r = at(g, "🔴 비(도달 가능 폭 ÷ 문턱)", name)
        rows.append((f"{name}\n{str(at(g,'축',name))[:16]}", r,
                     at(g, "🔴 검정력 0 인가(비 < 1 이면 자동)", name)))
xs = range(len(rows))
vals = [max(r[1], 1e-3) for r in rows]
cols = ["#c0392b" if r[2] else "#1f7a1f" for r in rows]
bars = ax[1].bar(list(xs), vals, color=cols, width=.55)
for b, r in zip(bars, rows):
    ax[1].annotate(f"{r[1]:.3g}", (b.get_x() + b.get_width() / 2, max(r[1], 1e-3)),
                   textcoords="offset points", xytext=(0, 3), ha="center",
                   fontsize=8.6, weight="bold")
ax[1].axhline(1.0, color="#333333", ls="--", lw=1.5)
ax[1].annotate("비 = 1 — 이 아래면 🔴 검정력 0", (len(rows) - 0.45, 1.0),
               textcoords="offset points", xytext=(0, 4), ha="right", fontsize=7.6)
ax[1].set_yscale("log")
ax[1].set_xticks(list(xs))
ax[1].set_xticklabels([r[0] for r in rows], fontsize=7.2)
ax[1].set_ylabel("도달 가능 폭 ÷ 문턱 (로그)")
ax[1].set_title("(b) 🔴 관문마다 비를 자동 신고했다 —\n주 판정 관문 자신이 검정력 0 이다", fontsize=10)
ax[1].grid(axis="y", alpha=.25)

# (c) 바닥을 바꾸면 — 자 대 자′
FR = at(FLOOR, "결과", kf)
labs, gaps, gaps2, oks, oks2 = [], [], [], [], []
for a in ABL:
    s = EIGHT[a]
    labs.append(a)
    g = at(s, "🔴 관문", a)
    gaps.append(at(g, "실측 빈틈(일)", "관문"))
    oks.append(at(g, "🔴 안 겹치나(진짜 lo > 귀무 hi)", "관문"))
    f = FR.get(a)
    gk = [k for k in f if k.startswith("🔴 관문 G6-분리")]
    fg = f[gk[0]]
    gaps2.append(at(fg, "실측 빈틈(일)", "G6-분리"))
    oks2.append(at(fg, "🔴 안 겹치나(진짜 lo > 귀무 hi)", "G6-분리"))
w = .36
xs = range(len(labs))
ax[2].bar([i - w / 2 for i in xs], gaps, width=w, color="#8e8e8e", label="자(기후값 바닥)")
ax[2].bar([i + w / 2 for i in xs], gaps2, width=w, color="#1f4e79",
          label="🔴 자′(격자를 아는 바닥)")
for i, (a, b, o1, o2) in enumerate(zip(gaps, gaps2, oks, oks2)):
    ax[2].annotate(f"{a:+.3f}", (i - w / 2, a), textcoords="offset points",
                   xytext=(0, 3 if a >= 0 else -11), ha="center", fontsize=7.0)
    ax[2].annotate(f"{b:+.3f}", (i + w / 2, b), textcoords="offset points",
                   xytext=(0, 3), ha="center", fontsize=7.4, weight="bold", color="#1f4e79")
ax[2].axhline(0, color="#333333", lw=1.1)
ax[2].set_xticks(list(xs))
ax[2].set_xticklabels(labs, fontsize=7.4)
ax[2].set_ylabel("빈틈(일) = 진짜 lo − 귀무 hi")
ax[2].set_title("(c) 🔴 바닥에서 격자를 빼자\n네 판이 모두 갈렸다 (병기 · 주 판정 아님)", fontsize=10)
ax[2].legend(fontsize=7.6)
ax[2].grid(axis="y", alpha=.25)

fig.tight_layout()
fig.savefig(HERE / "fig1.pdf")
plt.close(fig)

# ── fig2 ────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(1, 3, figsize=(14.0, 4.2))

# (a) 가장자리 절
n_edge = at(EDGE, "행 수", ke)
n_hold = at(EDGE, "홀드아웃 간격(분모)", ke)
share = at(at(EDGE, "🔴 빈틈에서의 몫", ke), "🔴 결측행의 몫 비율", "몫")
labs2 = [f"행 수\n{n_edge:,} / {n_hold:,}", "평균 간격\n(그 행)", "평균 간격\n(나머지)"]
v2 = [100 * n_edge / n_hold, at(EDGE, "그 행의 평균 간격(일) — 진짜", ke),
      at(EDGE, "나머지 행의 평균 간격(일) — 진짜", ke)]
c2 = ["#c0392b", "#c0392b", "#8e8e8e"]
bars = ax[0].bar(range(3), v2, color=c2, width=.55)
for b, v, u in zip(bars, v2, ["%", "일", "일"]):
    ax[0].annotate(f"{v:.3f}{u}", (b.get_x() + b.get_width() / 2, v),
                   textcoords="offset points", xytext=(0, 3), ha="center",
                   fontsize=9, weight="bold")
ax[0].set_xticks(range(3))
ax[0].set_xticklabels(labs2, fontsize=7.6)
ax[0].set_title(f"(a) 홀드아웃의 {100*n_edge/n_hold:.3f}% 가 빈틈의 {100*share:.1f}% 를 만든다\n"
                "🔴 격자마다 첫 간격 하나 — 관측창의 가장자리", fontsize=9.6)
ax[0].grid(axis="y", alpha=.25)

# (b) 덮음 눈금
SW = [k for k in COV if "훑기" in str(k)]
sweep = COV[SW[0]]
al = [r["α"] for r in sweep]
cov_c = [r["조건부"]["눈금확인 덮음"] for r in sweep]
cov_k = [r["달력"]["눈금확인 덮음"] for r in sweep]
ax[1].plot(al, cov_c, marker="o", color="#1f7a1f", lw=1.8, label="조건부")
ax[1].plot(al, cov_k, marker="s", color="#8e8e8e", lw=1.6, label="기후값")
ax[1].axhline(0.80, color="#333333", ls="--", lw=1.4)
ax[1].annotate("명목 0.80", (al[-1], 0.80), textcoords="offset points",
               xytext=(-4, 4), ha="right", fontsize=7.6)
ax[1].axhspan(0.75, 0.85, color="#eef5ee", zorder=0)
V = at(D, "🔴🔴 판정 (사전등록 §6 을 기계로 적용)", "925")
ax[1].set_xlabel("α (눈금 훑기)")
ax[1].set_ylabel("눈금 확인 덮음")
ax[1].set_title("(b) 🔴 900노트 만에 처음 이 자로 판정했다 —\n눈금은 맞았고 폭 조건을 못 넘었다", fontsize=9.6)
ax[1].legend(fontsize=8)
ax[1].grid(alpha=.25)

# (c) 배선 — 분모 둘
planted = at(WIRE, "🔴 심은 수", kw)
fired = at(WIRE, "🔴 발화한 수", kw)
unp = at(WIRE, "🔴 못 심은 수", kw)
labs3 = [f"심은 것 기준\n{fired}/{planted}", f"🔴 못 심은 것까지\n{fired}/{planted+unp}"]
v3 = [fired / planted, fired / (planted + unp)]
bars = ax[2].bar(range(2), v3, color=["#8e8e8e", "#c0392b"], width=.5)
for b, v in zip(bars, v3):
    ax[2].annotate(f"{v:.3f}", (b.get_x() + b.get_width() / 2, v),
                   textcoords="offset points", xytext=(0, 3), ha="center",
                   fontsize=11, weight="bold")
ax[2].set_xticks(range(2))
ax[2].set_xticklabels(labs3, fontsize=8.4)
ax[2].set_ylim(0, 1.2)
ax[2].set_ylabel("검정력")
ax[2].set_title("(c) 🔴 검정력에 분모를 둘 적었다 —\n못 심은 셋도 분모다", fontsize=9.6)
ax[2].grid(axis="y", alpha=.25)

fig.tight_layout()
fig.savefig(HERE / "fig2.pdf")
plt.close(fig)

print("fig1.pdf · fig2.pdf")
for a in ABL:
    s = EIGHT[a]
    g = at(s, "🔴 관문", a)
    print(f"  {a}: 진짜 {s['진짜']['개선(일)']:.6f} {s['진짜']['BCa']} · "
          f"N2 {s['N2']['개선(일)']:.6f} {s['N2']['BCa']} · "
          f"빈틈 {g['실측 빈틈(일)']:+.6f} · 안겹침 {g['🔴 안 겹치나(진짜 lo > 귀무 hi)']}")
print("  G1 비", at(G1, "🔴 비(|기대 빈틈| ÷ MDE)", "G1"),
      "· 검정력0", at(G1, "🔴 검정력 0 인가(비 < 1 이면 자동)", "G1"))
print("  자′ 빈틈", [round(x, 6) for x in gaps2], "· 안겹침", oks2)
print("  가장자리", n_edge, "/", n_hold, "· 몫", share)
print("  배선", f"{fired}/{planted}", "·", f"{fired}/{planted+unp}")
print("  판정", str(at(V, "🔴 첫째 자(간격 예측이 기후값을 이기나)", "판정"))[:70])
