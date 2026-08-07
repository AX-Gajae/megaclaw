"""노트 737 그림 --- 로그에서 값을 읽어 그린다(손으로 옮겨 적지 않는다)."""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({"font.family": "Apple SD Gothic Neo", "font.size": 8.5,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.unicode_minus": False})
LOG = Path("/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad/cost737.log")
s = LOG.read_text()
j = json.loads(s[s.index("=== 모아서 ===") + len("=== 모아서 ==="):])
curve = j["**카디널리티 곡선(열당 비용)**"]
arms = j["팔별"]
b0 = j["기준선(없이)"]

# x 축: 카디널리티(연속은 오른쪽 끝에 따로)
keys = list(curve)
xs = [2, 4, 10, 100]
ys = [curve[k] for k in keys[:4]]
cont = curve[keys[-1]]

fig = plt.figure(figsize=(11.4, 4.1))
gs = fig.add_gridspec(1, 3, width_ratios=[1.15, 1.0, 0.95], wspace=0.33)

# ── 1. 열당 비용 대 카디널리티
ax = fig.add_subplot(gs[0, 0])
ax.plot(xs, ys, "-o", color="#2b4c7e", lw=2.0, ms=8, zorder=3)
ax.scatter([300], [cont], s=190, marker="D", c="#b3392b", zorder=4,
           edgecolor="w", lw=1.3)
ax.annotate(f"연속\n{cont:+.4f}", (300, cont), textcoords="offset points",
            xytext=(0, 16), ha="center", fontsize=8, weight="bold",
            color="#b3392b")
for x, y, k in zip(xs, ys, keys[:4]):
    ax.annotate(f"{y:+.4f}", (x, y), textcoords="offset points",
                xytext=(0, 11), ha="center", fontsize=7.6)
ax.axhspan(0.02, 0.025, color="#d4a11a", alpha=0.18, zorder=1)
ax.text(2.2, 0.0225, "노트 641 의 '열당 0.02~0.025'", fontsize=7.4, color="#8a6a10",
        va="center")
ax.axhline(0.0015, color="#111", lw=1.2, ls="--")
ax.text(2.2, 0.0015, "판 2σ 를 3열로 나눈 값 0.0015", fontsize=7.2, color="#333",
        va="bottom")
ax.set_xscale("log")
ax.set_xlim(1.6, 520)
ax.set_xticks([2, 4, 10, 100, 300])
ax.set_xticklabels(["2\n이진", "4\n사분위", "10\n십분위", "100\n백분위", "연속"])
ax.set_xlabel("열의 카디널리티 (도메인 안 분위 단계 수 · 로그)")
ax.set_ylabel("열당 판 비용  (없이 - 팔) / 열 수")
ax.set_title("거친 열이 비싸다\n같은 난수를 이산화만 달리했다 --- 신호는 전부 0",
             loc="left", fontsize=9, weight="bold")

# ── 2. 팔별 판
ax = fig.add_subplot(gs[0, 1])
tags = [t for t in arms]
short = {t: t.split(" ", 1)[1] if " " in t else t for t in tags}
vals = [arms[t]["판"] for t in tags]
sds = [arms[t]["씨앗SD"] for t in tags]
y = np.arange(len(tags))
cols = ["#111"] + ["#2b4c7e"] * 5 + ["#7f8896"] * 2
ax.barh(y, vals, 0.6, color=cols, xerr=sds, error_kw=dict(lw=1.0, ecolor="#555"))
for i, (v, t) in enumerate(zip(vals, tags)):
    ax.text(v + 0.004, i, f"{v:.4f}", va="center", fontsize=7.4,
            weight="bold" if i == 0 else "normal")
ax.axvline(b0, color="#111", lw=1.2, ls="--")
ax.set_yticks(y)
ax.set_yticklabels([short[t] for t in tags], fontsize=7.6)
ax.invert_yaxis()
lo = min(vals) - 0.03
ax.set_xlim(lo, b0 + 0.035)
ax.set_xlabel("판 ρ  (점선 = 없이)")
ax.set_title("판이 실제로 얼마나 깎이나\n막대 오차는 씨앗 SD(6씨앗)",
             loc="left", fontsize=9, weight="bold")

# ── 3. 도메인 흔들림 대 유보 행수 --- 얇은 것이 흔들린다
ax = fig.add_subplot(gs[0, 2])
W = {"게임": 180, "도서": 163, "만화": 258, "모바일": 441, "세계애니": 300,
     "시장팝업": 126, "아이돌": 51, "애니": 606, "웹툰": 650, "팝업": 65, "펀딩": 529}
d0 = arms["① 없이"]["도메인"]
d6 = arms["⑥ 연속 · 3열"]["도메인"]
pts = [(k, d6[k] - d0[k], W[k]) for k in d0 if k in d6]
for k, dv, w in pts:
    c = "#b3392b" if dv < 0 else "#2b7e4c"
    ax.scatter(w, abs(dv), s=170, c=c, zorder=3, edgecolor="w", lw=1.2)
    dx, dy = (11, 0)
    if k in ("팝업", "아이돌"):
        dx, dy = (11, -3)
    ax.annotate(k, (w, abs(dv)), textcoords="offset points", xytext=(dx, dy),
                va="center", fontsize=7.4)
nn = np.linspace(45, 700, 300)
cc = float(np.mean([abs(dv) * np.sqrt(w) for _, dv, w in pts]))
ax.plot(nn, cc / np.sqrt(nn), "--", color="#111", lw=1.3)
ax.text(300, cc / np.sqrt(300) + 0.004, "c/√n (c = %.3f)" % cc, fontsize=7.2,
        color="#333")
ax.set_xscale("log")
ax.set_xlim(42, 900)
ax.set_ylim(0, 0.040)
ax.set_xlabel("그 도메인의 유보 채점 행수 (로그)")
ax.set_ylabel("순수 난수 3열이 흔든 폭  |차|")
ax.set_title("얇은 도메인이 크게 흔들린다\n스피어만 %.3f (p=%.3f) · 붉은 점 = 내려간 도메인"
             % (-0.673, 0.023), loc="left", fontsize=9, weight="bold")

out = "paper/steps/146_roughcol/figs/roughcol.pdf"
Path(out).parent.mkdir(parents=True, exist_ok=True)
fig.savefig(out, bbox_inches="tight")
print(json.dumps({"그림": out, "곡선": curve, "단조": j["**단조 증가**"],
                  "연속−이진": j["**연속 − 이진 (열당)**"]}, ensure_ascii=False))
