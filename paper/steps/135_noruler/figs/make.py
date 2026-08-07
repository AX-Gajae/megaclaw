"""그림 둘 — 세 팔의 신호 몫, 그리고 자 여섯 중 하나만 돌아간다."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager as fm
from pathlib import Path

for cand in ("AppleGothic", "Apple SD Gothic Neo"):
    if any(cand in f.name for f in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams["axes.unicode_minus"] = False
OUT = Path(__file__).resolve().parent

fig, axs = plt.subplots(1, 2, figsize=(7.8, 3.5),
                        gridspec_kw={"width_ratios": [1.05, 1]})

# ── (a) 세 팔 ─────────────────────────────────────────────────
a = axs[0]
a.axhline(0, color="#333", lw=0.9)
a.axhline(0.0045, ls="--", lw=1.3, color="#8b1a1a")
a.text(2.42, 0.0050, "문턱 0.0045", fontsize=8.5, color="#8b1a1a", ha="right")
bars = [("진짜\n(순효과)", 0.0076, "#1a3f6b"), ("위약", -0.0042, "#8b1a1a"),
        ("신호 몫\n(진짜-위약)", 0.0118, "#1a5c2a")]
for i, (nm, v, c) in enumerate(bars):
    a.bar(i, v, 0.55, color=c)
    a.text(i, v + (0.0006 if v > 0 else -0.0011), f"{v:+.4f}", ha="center",
           fontsize=10, fontweight="bold")
a.set_xticks(range(3)); a.set_xticklabels([b[0] for b in bars], fontsize=9)
a.set_ylim(-0.0065, 0.0148)
a.set_ylabel("판 Δρ (씨앗 12 · 짝 차이)", fontsize=9)
a.set_title("텍스트 열 하나 — 신호 몫이 문턱의 2.6배\n진짜 12/12 · 위약 0/12",
            fontsize=10.5, fontweight="bold")
a.spines[["top", "right"]].set_visible(False)

# ── (b) 자 여섯 중 하나 ───────────────────────────────────────
a = axs[1]
R = [("판", 3369, True), ("날짜 통제 판", 3369, False), ("무리 안 판", 3369, False),
     ("KR 만화", 1716, False), ("비게임 앱", 1600, False), ("CN 만화", 352, False)]
y = np.arange(len(R))[::-1]
a.barh(y, [n for _, n, _ in R], 0.6,
       color=["#1a5c2a" if ok else "#c9ccd1" for _, _, ok in R])
for yy, (nm, n, ok) in zip(y, R):
    a.text(n + 60, yy, ("돌아간다" if ok else "채점기 없음"), va="center",
           fontsize=9, fontweight="bold" if ok else "normal",
           color="#1a5c2a" if ok else "#8b1a1a")
a.set_yticks(y); a.set_yticklabels([f"{nm}" for nm, _, _ in R], fontsize=9)
a.set_xlim(0, 4900)
a.set_xlabel("유보 행수 (sideaudit.SENS 에 적힌 값)", fontsize=9)
a.set_title("규약은 다섯 자를 요구하는데\n저장소에서 돌아가는 자는 하나다",
            fontsize=10.5, fontweight="bold")
a.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(OUT / "noruler.pdf")
print("그림 저장")
