"""그림 둘 — 닫힌 문 넷, 그리고 텍스트가 가진 몫."""
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

# ── (a) 문 넷 ─────────────────────────────────────────────────
fig, axs = plt.subplots(1, 2, figsize=(7.6, 3.4),
                        gridspec_kw={"width_ratios": [1, 1.1]})
a = axs[0]
a.axis("off")
DOORS = [
    ("KOPIS 자체 API", "SERVICE KEY IS\nNOT REGISTERED", "#8b1a1a"),
    ("문화포털 api.kcisa.kr", "HTTP 403\nAPI Key is not valid", "#8b1a1a"),
    ("포털 B553457", "NO_OPENAPI_SERVICE", "#8b1a1a"),
    ("KOPIS 공개 웹", "열린다 —\n**집중값만**".replace("**", ""), "#b07d2a"),
    ("대조: B551011 방문자", "HTTP 200\n종로구 98,007명", "#1a5c2a"),
]
for i, (nm, msg, c) in enumerate(DOORS):
    y = 0.86 - i * 0.19
    a.add_patch(plt.Rectangle((0.03, y - 0.075), 0.44, 0.15,
                              facecolor="#f4f4f4", edgecolor=c, lw=1.4))
    a.text(0.25, y, nm, ha="center", va="center", fontsize=9, fontweight="bold")
    a.text(0.53, y, msg, ha="left", va="center", fontsize=8.2, color=c)
a.set_xlim(0, 1.15); a.set_ylim(0.02, 1.0)
a.set_title("문 넷을 두드리고 대조를 세웠다\n키는 멀쩡하다 — data.go.kr 은 서비스별 승인",
            fontsize=10, fontweight="bold")

# ── (b) 텍스트가 가진 몫 ──────────────────────────────────────
a = axs[1]
DOM = ["애니", "모바일", "펀딩", "세계애니", "웹툰", "게임", "만화"]
RHO = [0.4910, 0.2928, 0.2469, 0.1927, 0.0969, 0.0968, 0.0590]
y = np.arange(len(DOM))[::-1]
col = ["#1a3f6b" if v >= 0.30 else ("#4a5c6a" if v >= 0.10 else "#b0b6bd") for v in RHO]
a.barh(y, RHO, 0.6, color=col)
for yy, v in zip(y, RHO):
    a.text(v + 0.008, yy, f"{v:.3f}", va="center", fontsize=8.5, fontweight="bold")
a.axvline(0.2399, color="#1a3f6b", ls="-", lw=1.6)
a.axvline(0.4689, color="#333", ls="--", lw=1.4)
a.text(0.2399, len(DOM) - 0.35, " 판 0.2399", fontsize=8.5, color="#1a3f6b",
       fontweight="bold")
a.text(0.4689, len(DOM) - 1.3, " 챔피언 0.4689", fontsize=8.5, color="#333")
a.set_yticks(y); a.set_yticklabels(DOM, fontsize=9)
a.set_xlim(0, 0.60)
a.set_xlabel("제목 텍스트만으로 얻은 스피어만 (유보 채점)", fontsize=9)
a.set_title("텍스트 단독이 챔피언의 51%\n애니 하나는 챔피언 판 전체를 넘는다",
            fontsize=10, fontweight="bold")
a.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(OUT / "doors.pdf")
print("그림 저장")
