#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 노트 915 그림 — 🔴 손 전사 금지: 값은 전부 산출물에서 **읽는다**.
#   fig1 (a) 층별 설명한 몫 8k(씨앗3) 대 30k  (b) 층별 그래디언트 노름 — 깊을수록 커진다
#        (c) 909 의 추정과 내가 센 수
#   fig2 (a) 소수 라벨 곡선과 **두 바닥**  (b) 부착 깔때기 — 185 에서 93 으로, 그리고 37 칸
import json
import pathlib
import statistics as st

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


CNT = json.loads((ROOT / "runners/out915_count.json").read_text())
LNK = json.loads((ROOT / "runners/out915_link.json").read_text())
SSL = json.loads((ROOT / "runners/out915_ssl.json").read_text())
S30 = json.loads((ROOT / "runners/out915_ssl30k.json").read_text())
PRB = json.loads((ROOT / "runners/out915_probe.json").read_text())

KEXP = "설명한 몫 1-MSE/바닥"
KGRD = "층별 그래디언트 노름 중앙값(뒤 절반)"

# ── 층별 설명한 몫 ───────────────────────────────────────────────────────
def by_layer(doc):
    out = {}
    for br in at(doc, "갈래", "ssl"):
        out.setdefault(at(br, "층", "갈래"), []).append(at(br, KEXP, "갈래"))
    return out


E8 = by_layer(SSL)
E30 = by_layer(S30)
LAYERS = sorted(E8)
m8 = [st.mean(E8[L]) for L in LAYERS]
sd8 = [st.stdev(E8[L]) if len(E8[L]) > 1 else 0.0 for L in LAYERS]  # 표본 SD
m30 = [st.mean(E30[L]) for L in LAYERS]
n30 = [len(E30[L]) for L in LAYERS]

fig, ax = plt.subplots(1, 3, figsize=(13.8, 4.0))

x = range(len(LAYERS))
ax[0].errorbar(x, m8, yerr=sd8, marker="o", color="#c0392b", capsize=4, lw=1.8,
               label=f"8,000스텝 (씨앗 {len(E8[LAYERS[0]])} · 막대는 표본 SD)")
ax[0].plot(x, m30, marker="s", color="#1f4e79", lw=1.8, ls="--",
           label=f"30,000스텝 (씨앗 {n30[0]} — 🔴 폭을 못 가른다)")
for i, (a, b) in enumerate(zip(m8, m30)):
    ax[0].annotate(f"{a:.5f}", (i, a), textcoords="offset points", xytext=(0, -14),
                   ha="center", fontsize=7.4, color="#c0392b")
    ax[0].annotate(f"{b:.5f}", (i, b), textcoords="offset points", xytext=(0, 6),
                   ha="center", fontsize=7.4, color="#1f4e79")
ax[0].set_xticks(list(x))
ax[0].set_xticklabels([f"{L}층" for L in LAYERS])
ax[0].set_ylabel("설명한 몫 1 − MSE/자명바닥")
ax[0].set_title(f"(a) 8,000스텝의 층 폭 {max(m8)-min(m8):.4f} 이\n"
                f"30,000스텝에서 {max(m30)-min(m30):.4f} 로 줄어든다", fontsize=9.6)
ax[0].legend(fontsize=7.4, loc="lower center")
ax[0].grid(alpha=.25)

# (b) 그래디언트 노름 — 깊을수록 커진다
br8 = [b for b in at(S30, "갈래", "30k") if at(b, "층", "갈래") == 8][0]
g = at(br8, KGRD, "L8/30k")
blocks = [k for k in g if k.startswith("block")]
blocks.sort(key=lambda s: int(s[5:]))
gvals = [g[k] for k in blocks]
floor = gvals[0] / 100.0
ax[1].plot(range(len(gvals)), gvals, marker="o", color="#1f7a1f", lw=2.0)
for i, v in enumerate(gvals):
    ax[1].annotate(f"{v:.4f}", (i, v), textcoords="offset points", xytext=(0, 6),
                   ha="center", fontsize=7.2)
ax[1].axhline(floor, color="#c0392b", ls="--", lw=1.2,
              label=f"「안 배운다」 문턱 = 첫 블록의 1/100 = {floor:.5f}")
ax[1].set_xticks(range(len(gvals)))
ax[1].set_xticklabels([b.replace("block", "블록 ") for b in blocks], fontsize=7.4)
ax[1].set_ylabel("그래디언트 노름 중앙값(뒤 절반)")
ax[1].set_yscale("log")
ax[1].set_title("(b) 8층 · 30,000스텝 — 노름이 깊을수록 **커진다**\n"
                "소실 그래디언트가 아니다. 죽은 층 0", fontsize=9.6)
ax[1].legend(fontsize=7.2)
ax[1].grid(alpha=.25)

# (c) 909 의 추정과 내가 센 수
# 🔴 티처 #71 M8 정정 — `out915_count.json` 이 적은 「909 추정 147,690,000」은 **손 전사**다.
#   909 의 실제 공표값은 147,692,959 다. 계수 산출물은 증거물이라 안 고치고,
#   여기서 **909 산출물을 직접 읽는다**(이 논문의 규율이 원래 그것이다).
C909 = at(CNT, "🔴 909 의 추정과 대조", "count")
_S909 = json.loads((ROOT / "runners/out909_ssl.json").read_text())
est = at(at(at(_S909, "0단계 연료", "909"),
             "다 · 판이 한 번도 안 보는 원천", "0단계 연료"),
          "U5 생활인구 격자", "판이 안 보는 원천")["🔴 어림 총행 = 일수 × 표본 하루"]
got = at(C909, "내가 센 수", "대조")
_typo = at(C909, "909 추정", "대조")
assert est != _typo, "🔴 손 전사가 사라졌다면 이 주석과 함께 지워라"
D = at(CNT, "🔴 분모 딱지 — 다섯이 전부 다른 분모다", "count")
# 🔴 '칸' 은 계수 산출물이 아니라 SSL 산출물의 「사실/장」이 적는다. 곱해서 만들지 않는다.
cells = at(at(at(SSL, "사실", "ssl"), "장", "사실"), "칸 = 격자×날짜×시각", "장")
labs = [f"909 의 추정\n(하루 표본 × {at(D,'② 서로 다른 날짜','분모')})",
        "🔴 내가 센 전량\n(zip 19개 스트리밍)",
        "칸 = 격자×날짜×시각\n(🔴 행과 다른 분모다)"]
vs = [est, got, cells]
bars = ax[2].bar(range(3), vs, color=["#adb5bd", "#1f7a1f", "#5b7fa6"], width=.6)
for b, v in zip(bars, vs):
    ax[2].annotate(f"{v:,}", (b.get_x() + b.get_width() / 2, v), textcoords="offset points",
                   xytext=(0, 3), ha="center", fontsize=8.6, weight="bold")
ax[2].set_xticks(range(3))
ax[2].set_xticklabels(labs, fontsize=7.2)
ax[2].set_ylabel("행 / 칸")
ax[2].set_title(f"(c) 추정이 {got-est:+,} 만큼 틀렸다\n"
                f"({100*(est-got)/got:+.2f}% · 조항 60)", fontsize=9.6)
ax[2].grid(axis="y", alpha=.25)

fig.tight_layout()
fig.savefig(HERE / "fig1.pdf")
plt.close(fig)

# ── fig2 ────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(1, 2, figsize=(11.0, 4.2))

FL = at(PRB, "🔴 바닥과 나란히", "probe")
KS = sorted(FL, key=lambda s: int(s))
orig = [at(FL[k], "원 축 ρ", k) for k in KS]
scr = [at(FL[k], "처음부터(격자 원값) ρ", k) for k in KS]
best, bestname = [], []
for k in KS:
    b = at(FL[k], "SSL 최고", k)
    nm = list(b)[0]
    best.append(at(b[nm], "OOF 평균예측 ρ", nm))
    bestname.append(nm.split()[-1])
perm = [at(FL[k], "🔴 라벨 순열 바닥 ρ", k) for k in KS]
rnd = [at(FL[k], "🔴 난수 표현 바닥 ρ 범위", k) for k in KS]

xs = range(len(KS))
for i, (lo, hi) in enumerate(rnd):
    ax[0].fill_between([i - .34, i + .34], lo, hi, color="#d9d9d9", zorder=0)
ax[0].plot(xs, orig, marker="o", color="#8e8e8e", lw=1.6, label="① 원 축(36열)")
ax[0].plot(xs, scr, marker="^", color="#5b7fa6", lw=1.6, label="② 처음부터(격자 원값)")
ax[0].plot(xs, best, marker="s", color="#1f7a1f", lw=2.2, label="③ SSL 최고")
ax[0].plot(xs, perm, marker="x", color="#c0392b", lw=2.0, ls="--",
           label="🔴 ⑤ 라벨 순열 바닥 — 신호가 있을 수 없는 자")
ax[0].fill_between([-.5, -.5], 0, 0, color="#d9d9d9", label="④ 난수 표현 바닥 범위")
for i, (b, p, nm) in enumerate(zip(best, perm, bestname)):
    ax[0].annotate(f"{b:+.3f}\n{nm}", (i, b), textcoords="offset points", xytext=(0, 8),
                   ha="center", fontsize=7.2, color="#1f7a1f")
    ax[0].annotate(f"{p:+.3f}", (i, p), textcoords="offset points", xytext=(0, -16),
                   ha="center", fontsize=7.2, color="#c0392b")
ax[0].axhline(0, color="#333333", lw=.9)
ax[0].set_xlim(-.5, len(KS) - .5)
ax[0].set_xticks(list(xs))
T = at(PRB, "표본", "probe")
ax[0].set_xticklabels([f"k = {k}" for k in KS])
ax[0].set_xlabel(f"라벨 수 k  (분모 — 프로브 행 {at(T,'🔴 분모 — 프로브 행','표본')} · "
                 f"군집 {at(T,'서로 다른 격자(군집 수)','표본')})")
ax[0].set_ylabel("스피어만 ρ")
ax[0].set_title("(a) k=16 에서 **최고 SSL 이 라벨 순열 바닥과 같은 자리**에 선다\n"
                "🔴 모든 k · 모든 층에서 Δρ 의 BCa 95% 가 0 을 문다", fontsize=9.6)
ax[0].legend(fontsize=7.0, loc="lower right")
ax[0].grid(alpha=.25)

# (b) 부착 깔때기
U = at(LNK, "③ 부착 — 유보 합집합(분모 185)", "link")
P375 = at(LNK, "🔴 판 유보 3,775 기준", "link")
den = at(LNK, "② 분모 — 🔴 셋이 다르다(조항 60)", "link")
steps = [("판 유보 전체\n(12도메인)", at(den, "판 유보 전체(12도메인)", "분모"), "#adb5bd"),
         ("팝업+시장팝업\n유보 합집합", at(U, "분모", "합집합"), "#8e8e8e"),
         ("좌표가 있다", at(U, "좌표 있음", "합집합"), "#5b7fa6"),
         ("🔴 격자에 붙는다\n(= 격자+날짜)", at(U, "🔴 격자 + 날짜 둘 다", "합집합"), "#1f7a1f"),
         ("±7일 검증(엄격)", at(U, "🔴 격자 + 날짜 + ±7일 검증 좌표", "합집합"), "#7fa66a"),
         ("🔴 서로 다른 격자\n(다른 분모다)", at(T, "서로 다른 격자(군집 수)", "표본"), "#c0392b")]
labs = [s[0] for s in steps]
vals = [s[1] for s in steps]
cols = [s[2] for s in steps]
bars = ax[1].bar(range(len(vals)), vals, color=cols, width=.62)
for b, v in zip(bars, vals):
    ax[1].annotate(f"{v:,}", (b.get_x() + b.get_width() / 2, v), textcoords="offset points",
                   xytext=(0, 3), ha="center", fontsize=8.8, weight="bold")
ax[1].set_xticks(range(len(vals)))
ax[1].set_xticklabels(labs, fontsize=6.8)
ax[1].set_yscale("log")
ax[1].set_ylabel("행 / 격자 (로그)")
ax[1].set_title(f"(b) 붙는 것은 판 유보의 {at(P375,'격자+날짜 %','3775기준')}% — "
                f"그리고 그 {at(P375,'격자+날짜 둘 다','3775기준')}행은\n"
                f"{at(T,'서로 다른 격자(군집 수)','표본')}칸에 몰린다. 마지막 막대만 분모가 다르다",
                fontsize=9.3)
ax[1].grid(axis="y", alpha=.25)

fig.tight_layout()
fig.savefig(HERE / "fig2.pdf")
plt.close(fig)

print("fig1.pdf · fig2.pdf")
print("  8k  ", dict(zip(LAYERS, [round(v, 5) for v in m8])), "SD", [round(s, 5) for s in sd8])
print("  30k ", dict(zip(LAYERS, [round(v, 5) for v in m30])), "씨앗", n30)
print("  노름", dict(zip(blocks, gvals)))
print("  계수", est, got, got - est, cells)
print("  곡선", dict(zip(KS, zip(orig, scr, best, perm))))
print("  깔때기", dict(zip(labs, [s[1] for s in steps])))
