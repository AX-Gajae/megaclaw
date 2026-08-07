"""그림 둘 — 전역 대 단일 전환, 그리고 이웃이 구조 효과라는 증거."""
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

fig, axs = plt.subplots(1, 2, figsize=(7.6, 3.4))

# ── (a) 전역 대 단일 ──────────────────────────────────────────
a = axs[0]
G = {"만화": 0.0184, "세계애니": 0.0041}
S = {"만화": -0.0027, "세계애니": 0.0035}
x = [0, 1]
a.axhline(0, color="#333", lw=0.9)
for d, c, mk in (("만화", "#8b1a1a", "o"), ("세계애니", "#1a5c2a", "s")):
    a.plot(x, [G[d], S[d]], mk + "-", color=c, lw=2, ms=9, label=d)
    a.annotate(f"{G[d]:+.4f}", (0, G[d]), textcoords="offset points",
               xytext=(-6, 8), ha="right", fontsize=9, color=c, fontweight="bold")
    a.annotate(f"{S[d]:+.4f}", (1, S[d]), textcoords="offset points",
               xytext=(8, 6 if S[d] > 0 else -14), fontsize=9, color=c,
               fontweight="bold")
a.set_xticks(x)
a.set_xticklabels(["전역 팔\n(다섯 도메인)", "단일 전환\n(둘만)"], fontsize=9.5)
a.set_xlim(-0.35, 1.45)
a.set_ylabel("도메인 신호 몫 (진짜 - 위약)", fontsize=9)
a.set_title("만화는 뒤집히고 세계애니는 버텼다\n85% 보존 대 부호 반전", fontsize=10,
            fontweight="bold")
a.legend(fontsize=9, frameon=False, loc="upper right")
a.spines[["top", "right"]].set_visible(False)
a.text(0.5, -0.0016, "DOMDROP 걸린 도메인", fontsize=8, color="#8b1a1a", ha="center")

# ── (b) 이웃은 구조 효과다 ────────────────────────────────────
a = axs[1]
NB = [("아이돌", 0.0131, 0.0121), ("도서", 0.0105, 0.0007), ("게임", 0.0064, 0.0063),
      ("모바일", 0.0014, 0.0015), ("시장팝업", 0.0011, 0.0074), ("팝업", -0.0063, -0.0043)]
y = np.arange(len(NB))[::-1]
w = 0.38
a.barh(y + w / 2, [r for _, r, _ in NB], w, color="#4a5c6a", label="진짜")
a.barh(y - w / 2, [p for _, _, p in NB], w, color="#8b1a1a", label="위약")
a.axvline(0, color="#333", lw=0.9)
a.set_yticks(y); a.set_yticklabels([n for n, _, _ in NB], fontsize=9)
a.set_xlabel("도메인 Δρ (축이 없는 도메인)", fontsize=9)
a.set_title("축 없는 도메인은 진짜와 위약이 같다\n→ 이웃 움직임은 구조 효과이고 정보가 아니다",
            fontsize=10, fontweight="bold")
a.legend(fontsize=8.5, frameon=False, loc="lower right")
a.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(OUT / "onesurvives.pdf")
print("그림 저장")
