#!/usr/bin/env python3
# 노트 901 그림 — 🔴 손 전사 금지: 값은 전부 산출물에서 **읽는다**.
#   fig1 (a) 식별 등급 분포  (b) W(막는 것) 빈도  (c) 분모 넷이 다르다
#   fig2 (a) 시장팝업 is_free_entry — 채워도 대조군이 안 는다  (b) 지평 접합 깔때기
import json
import pathlib
from collections import Counter

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

ID = json.loads((ROOT / "runners/out901_identify.json").read_text())
INV = json.loads((ROOT / "runners/out901_inventory.json").read_text())
LINK = json.loads((ROOT / "runners/out901h_link.json").read_text())

T = ID["판정 표"]
pairs = [(dom, col, p) for dom, v in T.items() for col, p in v.get("짝", {}).items()]
assert len(pairs) == 105, len(pairs)

# ── fig1 ────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(1, 3, figsize=(13.6, 4.0))

# (a) 식별 등급
gr = Counter(p["등급(식별)"] for _, _, p in pairs)
order = [k for k in ("A", "B", "C") if k in gr] + [k for k in gr if k not in "ABC"]
vals = [gr[k] for k in order]
col = {"A": "#1f7a1f", "B": "#e8a33d", "C": "#c0392b"}
bars = ax[0].bar(range(len(order)), vals,
                 color=[col.get(k, "#7f8c8d") for k in order], width=.6)
for b, v in zip(bars, vals):
    ax[0].annotate(str(v), (b.get_x() + b.get_width() / 2, v), textcoords="offset points",
                   xytext=(0, 3), ha="center", fontsize=11, weight="bold")
ax[0].set_xticks(range(len(order)))
ax[0].set_xticklabels([f"{k}등급" for k in order], fontsize=10)
ax[0].set_ylabel(f"개입-결과 짝 (분모 {len(pairs)})")
nA = gr.get("A", 0)
ax[0].set_title(f"(a) 식별 가능(A)은 {nA}개다", fontsize=10)
ax[0].set_ylim(0, max(vals) * 1.2)
ax[0].grid(axis="y", alpha=.25)

# (b) W 빈도 — 무엇이 막나
wc = Counter()
for _, _, p in pairs:
    ws = p.get("W") or []
    for x in ([ws] if isinstance(ws, str) else ws):
        wc[str(x).split()[0]] += 1
items = wc.most_common()
lab = [k for k, _ in items]
val = [v for _, v in items]
y = range(len(lab))[::-1]
ax[1].barh(list(y), val, color=["#c0392b" if v == len(pairs) else "#8e8e8e" for v in val],
           height=.62)
for yy, v in zip(y, val):
    ax[1].annotate(f"{v}", (v, yy), textcoords="offset points", xytext=(4, 0),
                   va="center", fontsize=9)
ax[1].set_yticks(list(y))
ax[1].set_yticklabels(lab, fontsize=8.5)
ax[1].set_xlabel(f"막힌 짝 수 (분모 {len(pairs)})")
ax[1].set_title("(b) 막는 것은 결측이 아니다", fontsize=10)
ax[1].set_xlim(0, len(pairs) * 1.14)
ax[1].grid(axis="x", alpha=.25)

# (c) 분모 넷 — 팝업 하나에서 다 다르다
inv = INV["재고"]
doms = ["팝업", "시장팝업"]
D1 = [T[d]["D1"] for d in doms]
D3 = [T[d].get("D3 되짚은 레코드 수") or 0 for d in doms]
x = range(len(doms))
w = .36
ax[2].bar([i - w / 2 for i in x], D1, width=w, color="#5b7fa6", label="D1 원천 레코드")
ax[2].bar([i + w / 2 for i in x], D3, width=w, color="#c0392b", label="D3 판 채점 유보")
for i, (a_, b_) in enumerate(zip(D1, D3)):
    ax[2].annotate(str(a_), (i - w / 2, a_), textcoords="offset points", xytext=(0, 3),
                   ha="center", fontsize=9)
    ax[2].annotate(str(b_), (i + w / 2, b_), textcoords="offset points", xytext=(0, 3),
                   ha="center", fontsize=9)
ax[2].set_xticks(list(x))
ax[2].set_xticklabels(doms, fontsize=10)
ax[2].set_ylabel("행 수")
ax[2].set_title("(c) 같은 도메인, 다른 분모 —\n이어 붙이면 조항 60 위반", fontsize=10)
ax[2].legend(fontsize=8, loc="upper left")
ax[2].grid(axis="y", alpha=.25)

fig.tight_layout()
fig.savefig(HERE / "fig1.pdf")
plt.close(fig)

# ── fig2 ────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(1, 2, figsize=(10.4, 4.0))

# (a) 시장팝업 is_free_entry — 채워도 대조군이 안 는다
p = T["시장팝업"]["짝"]["intervention.is_free_entry"]
d1n, d1o = p["D1"], p["비결측(D1)"]
d3n, d3o = p["D3(유보 채점행)"], p["비결측(D3)"]
minor = p["소수 쪽(D3 · 최빈 대 나머지)"]
names = [f"D1 전체\n{d1n}", f"D1 관측\n{d1o}", f"D3 유보\n{d3n}", f"D3 관측\n{d3o}",
         f"🔴 D3 대조군\n{minor}"]
vals = [d1n, d1o, d3n, d3o, minor]
cols = ["#adb5bd", "#7f8c8d", "#adb5bd", "#7f8c8d", "#c0392b"]
bars = ax[0].bar(range(5), vals, color=cols, width=.62)
for b, v in zip(bars, vals):
    ax[0].annotate(str(v), (b.get_x() + b.get_width() / 2, v), textcoords="offset points",
                   xytext=(0, 3), ha="center", fontsize=9.5, weight="bold")
ax[0].set_xticks(range(5))
ax[0].set_xticklabels(names, fontsize=7.6)
ax[0].set_ylabel("행 수")
ax[0].set_title("(a) 노트 900 이 「채우면 열린다」던 그 열 —\n채워도 대조군은 안 는다", fontsize=10)
ax[0].set_yscale("log")
ax[0].grid(axis="y", alpha=.25)

# (b) 지평 접합 깔때기 — 유보 채점행 층.
# 🔴 **정정(티처 #64 M1)**: 위 주석의 초판은 *"「합집합 185 · 붙음 93」은 문서에만 있고
#     산출물에는 없다"* 라고 적었다. **틀렸다 — 산출물에 있다.**
#     `runners/out901h_link.json` 의 **`⑥ 🔴 결정적 수 — 판 유보 기준`** 절에
#     `팝업 두 도메인 유보 합(중복 제거)=185` · `🔴 격자에 붙음=93` 이 그대로 있고,
#     이 사이클 자신의 도구로 `rc=0` 으로 뽑힌다.
# 🔴 **일어난 일**: 아래 `K` 가 **다른 절**(`④⑤⑥ …`)만 보고 assert 로 죽었다.
#     즉 **조회 경로가 틀린 것을 「그 수는 측정 안 됐다」로 읽었다** — 조항 59 의 정확한 반대 방향이고,
#     그것을 「인용 규약이 발화한 성공 사례」로 네 곳에 기록했다. **승리가 아니라 오독이었다.**
#     ⚠ 그림은 유보 채점행 층을 그대로 그린다(그 자체는 옳다). 아래에 185/93 도 함께 읽어 둔다.
K = "④⑤⑥ 매칭 · 날짜 · 결정적 수"
assert K in LINK, list(LINK)
STEP = ["분모", "좌표 있음", "🔴 격자에 붙음", "격자 붙음 · ±7일 검증 통과",
        "받아 둔 두 달과 날짜 겹침", "🔴 결정적 수(좌표 · 격자 · 두 달 겹침)"]
doms = ["팝업", "시장팝업"]
rows = {}
for dm in doms:
    h = LINK[K][dm]["유보 채점행"]
    missing = [s for s in STEP if s not in h]
    assert not missing, (dm, missing, list(h))
    rows[dm] = [h[s] for s in STEP]
yy = list(range(len(STEP)))[::-1]
w = .38
for i, dm in enumerate(doms):
    off = (-w / 2) if i == 0 else (w / 2)
    c = "#5b7fa6" if i == 0 else "#8e5aa6"
    ax[1].barh([y + off for y in yy], rows[dm], height=w, color=c,
               label=f"{dm} (유보 {rows[dm][0]})")
    for y, v in zip(yy, rows[dm]):
        ax[1].annotate(f"{v}", (v, y + off), textcoords="offset points", xytext=(4, 0),
                       va="center", fontsize=7.8,
                       color="#c0392b" if v <= 1 else "#333333",
                       weight="bold" if v <= 1 else "normal")
ax[1].set_yticks(yy)
ax[1].set_yticklabels([s.replace("🔴 ", "").replace(" · ", "\n· ") for s in STEP], fontsize=7.2)
ax[1].set_xlabel("팝업 수 (분모 = 각 도메인 유보 채점행)")
K6 = "⑥ 🔴 결정적 수 — 판 유보 기준"
assert K6 in LINK, list(LINK)
U = LINK[K6]["팝업 두 도메인 유보 합(중복 제거)"]
G = LINK[K6]["🔴 격자에 붙음"]
ax[1].set_title(f"(b) 붙는다 — 두 도메인 합집합 {U} 중 {G} 이 격자에 붙는다.\n"
                "막는 것은 공간이 아니라 받아 둔 두 달", fontsize=9.5)
ax[1].set_xlim(0, max(max(v) for v in rows.values()) * 1.22)
ax[1].legend(fontsize=7.5, loc="lower right")
ax[1].grid(axis="x", alpha=.25)

fig.tight_layout()
fig.savefig(HERE / "fig2.pdf")
plt.close(fig)

print("fig1.pdf · fig2.pdf")
print("  등급", dict(gr), "· 짝", len(pairs))
print("  W", dict(wc))
print("  is_free_entry D1", d1n, d1o, "· D3", d3n, d3o, "· 대조군", minor)
print("  합집합/붙음 =", U, G)
print("  깔때기", {d: dict(zip(STEP, v)) for d, v in rows.items()})
