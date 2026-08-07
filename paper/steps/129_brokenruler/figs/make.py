"""그림 셋 — 효과 대 문턱, 위약의 부호 반전, 그리고 40행이 판을 정하는 그림."""
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

# ── (a) 효과와 문턱이 같이 오른다 ──────────────────────────────
fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.1))
a = axs[0]
x = np.arange(2)
w = 0.36
eff = [0.0016, 0.0115]
thr = [0.0045, 0.0125]
a.bar(x - w / 2, eff, w, color="#4a5c6a", label="순효과 (③-①)")
a.bar(x + w / 2, thr, w, color="#c9ccd1", label="되뽑기 2σ 문턱")
for xi, (e, t) in enumerate(zip(eff, thr)):
    a.text(xi - w / 2, e + 0.0004, f"{e:+.4f}", ha="center", fontsize=8.5, fontweight="bold")
    a.text(xi + w / 2, t + 0.0004, f"{t:.4f}", ha="center", fontsize=8.5)
a.set_xticks(x)
a.set_xticklabels(["T=2025\n유보 3,369행", "T=2026\n유보 1,287행"], fontsize=9)
a.set_ylim(0, 0.0155)
a.set_ylabel("판 Δρ", fontsize=9)
a.set_title("효과 7.2배 · 문턱 2.8배\n비는 0.36 → 0.92 (좋아졌다)", fontsize=9.5, fontweight="bold")
a.legend(fontsize=8, frameon=False, loc="upper left")

a = axs[1]
real = [0.0016, 0.0115]
pla = [-0.0048, 0.0074]
a.axhline(0, color="#333", lw=0.8)
a.bar(x - w / 2, real, w, color="#4a5c6a", label="진짜 (③)")
a.bar(x + w / 2, pla, w, color="#8b1a1a", label="위약 (④)")
for xi, (r, p) in enumerate(zip(real, pla)):
    a.text(xi - w / 2, r + (0.0005 if r > 0 else -0.0012), f"{r:+.4f}",
           ha="center", fontsize=8.5, fontweight="bold")
    a.text(xi + w / 2, p + (0.0005 if p > 0 else -0.0012), f"{p:+.4f}",
           ha="center", fontsize=8.5, fontweight="bold", color="#8b1a1a")
a.set_xticks(x)
a.set_xticklabels(["T=2025", "T=2026"], fontsize=9)
a.set_ylabel("판 Δρ", fontsize=9)
a.set_ylim(-0.0075, 0.0155)
a.set_title("위약이 부호를 뒤집었다\n신호 몫 +0.0064 -> +0.0041", fontsize=9.5, fontweight="bold")
a.legend(fontsize=8, frameon=False, loc="upper left")
for ax_ in axs:
    ax_.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(OUT / "effectvsnoise.pdf")

# ── (b) 40행이 판을 정한다 ─────────────────────────────────────
W = {"시장팝업": 40, "팝업": 21, "펀딩": 159, "모바일": 206, "아이돌": 20, "만화": 43,
     "도서": 133, "애니": 233, "웹툰": 216, "세계애니": 140, "게임": 76}
REAL = {"시장팝업": .3222, "팝업": .0591, "펀딩": .0071, "모바일": -.0015, "아이돌": -.01,
        "만화": .0024, "도서": .0004, "애니": -.0002, "웹툰": -.0002, "세계애니": -.0001,
        "게임": -.0001}
PLA = {"시장팝업": .1827, "팝업": .0409, "펀딩": .0031, "모바일": .0019, "아이돌": .0043,
       "만화": -.0003, "도서": .0025, "애니": -.0005, "웹툰": .0022, "세계애니": -.0016,
       "게임": -.0001}
TOT = sum(W.values())
doms = sorted(W, key=lambda d: -abs(REAL[d] * W[d]))
fig, ax = plt.subplots(figsize=(7.4, 3.2))
y = np.arange(len(doms))[::-1]
r = [REAL[d] * W[d] / TOT for d in doms]
p = [PLA[d] * W[d] / TOT for d in doms]
ax.barh(y + 0.19, r, 0.38, color="#4a5c6a", label="진짜의 몫")
ax.barh(y - 0.19, p, 0.38, color="#8b1a1a", label="위약의 몫")
ax.axvline(0, color="#333", lw=0.8)
ax.set_yticks(y)
ax.set_yticklabels([f"{d} ({W[d]}행)" for d in doms], fontsize=8.5)
ax.set_xlabel("판 Δρ 에 낸 몫 (도메인 Δρ × 유보 가중)", fontsize=9)
ax.legend(fontsize=8.5, frameon=False, loc="lower right")
ax.spines[["top", "right"]].set_visible(False)
ax.set_title("판 이득의 87%가 시장팝업 유보 40행에서 온다 — 위약도 76%",
             fontsize=10.5, fontweight="bold")
ax.annotate("40행에서 ρ 표본 SD ≈ 0.158\n진짜 0.322 대 위약 0.183 은 그 안이다",
            xy=(0.0100, y[0] + 0.19), xytext=(0.0035, y[0] - 2.4), fontsize=8.5,
            color="#8b1a1a",
            arrowprops=dict(arrowstyle="->", color="#8b1a1a", lw=1.1))
fig.tight_layout(); fig.savefig(OUT / "fortyrows.pdf")
print("그림 둘 저장")
