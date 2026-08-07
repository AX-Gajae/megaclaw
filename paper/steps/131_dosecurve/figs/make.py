"""그림 둘 — 용량 곡선과 상쇄."""
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

DOM = ["만화", "세계애니", "게임", "애니", "모바일"]
GEN = [0.316, 0.403, 0.573, 0.683, 0.770]
SIG = [0.0184, 0.0041, -0.0028, -0.0047, -0.0104]     # 신호 몫 = 진짜 − 위약
REAL = [0.0079, 0.0033, -0.0104, -0.0042, -0.0116]
PLA = [-0.0105, -0.0008, -0.0076, 0.0005, -0.0012]
W = [258, 300, 180, 606, 441]
TOT = 3369

# ── (a) 용량 곡선 ──────────────────────────────────────────────
fig, axs = plt.subplots(1, 2, figsize=(7.6, 3.3))
a = axs[0]
a.axhline(0, color="#333", lw=0.8)
a.plot(GEN, SIG, "o-", color="#1a3f6b", lw=2, ms=8, label="신호 몫 (진짜 - 위약)")
a.plot(GEN, PLA, "s--", color="#8b1a1a", lw=1.2, ms=6, alpha=0.8, label="위약만")
for x, y, d in zip(GEN, SIG, DOM):
    a.annotate(d, (x, y), textcoords="offset points", xytext=(0, 11 if y > 0 else -16),
               ha="center", fontsize=8.5)
a.set_xlabel("`gen` 축과의 겹침 |스피어만|".replace("`", ""), fontsize=9)
a.set_ylabel("도메인 신호 몫 (Δρ)", fontsize=9)
a.set_xlim(0.26, 0.83)
a.set_title("겹침 ↔ 신호 몫 스피어만 -1.000\n위약만 보면 +0.500 (p=0.391)",
            fontsize=10, fontweight="bold")
a.legend(fontsize=8, frameon=False, loc="upper right")
a.spines[["top", "right"]].set_visible(False)
a.axvspan(0.26, 0.49, color="#dff0e0", alpha=0.55, zorder=0)
a.axvspan(0.49, 0.83, color="#f7dede", alpha=0.55, zorder=0)
a.text(0.36, min(SIG) * 0.85, "번다", fontsize=9, color="#1a5c2a", fontweight="bold")
a.text(0.70, max(SIG) * 0.72, "낸다", fontsize=9, color="#8b1a1a", fontweight="bold")

# ── (b) 상쇄 ──────────────────────────────────────────────────
a = axs[1]
mo = [s * w / TOT for s, w in zip(SIG, W)]
y = np.arange(len(DOM))[::-1]
col = ["#1a5c2a" if v > 0 else "#8b1a1a" for v in mo]
a.barh(y, mo, 0.58, color=col)
a.axvline(0, color="#333", lw=0.8)
for yy, v, d, w in zip(y, mo, DOM, W):
    a.text(v + (0.00006 if v > 0 else -0.00006), yy, f"{v:+.5f}",
           va="center", ha="left" if v > 0 else "right", fontsize=8.5)
a.set_yticks(y)
a.set_yticklabels([f"{d} ({w}행)" for d, w in zip(DOM, W)], fontsize=8.5)
a.set_xlabel("판 신호 몫에 낸 몫 (도메인 × 유보 가중)", fontsize=9)
tot = sum(mo)
a.set_title(f"양수 둘 {sum(v for v in mo if v>0):+.5f} · 음수 셋 "
            f"{sum(v for v in mo if v<0):+.5f}\n합 {tot:+.5f} — 판 신호 몫 -0.0004",
            fontsize=10, fontweight="bold")
a.spines[["top", "right"]].set_visible(False)
a.set_xlim(-0.0016, 0.0022)
fig.tight_layout(); fig.savefig(OUT / "dose.pdf")
print("그림 저장")
