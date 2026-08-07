"""그림 둘 — 원천이 하나였던 대조, 그리고 흐르지 않는 '흐름'."""
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

# ── (a) 대조의 계보 ────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(7.4, 3.3))
ax.axis("off")


def box(x, y, w, h, txt, fc, ec="#333", fs=8.5, bold=False):
    ax.add_patch(plt.Rectangle((x, y), w, h, facecolor=fc, edgecolor=ec, lw=1.0))
    ax.text(x + w / 2, y + h / 2, txt, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal", linespacing=1.5)


# 무효 대조 (위)
ax.text(0.02, 0.88, "노트 636 이 '교차검증 완벽' 이라 적은 것", fontsize=10,
        fontweight="bold", color="#8b1a1a")
box(0.06, 0.60, 0.30, 0.20, "FlowerKnows_팝업\n_운영결과보고서.pdf\n(1meC7L41tG…)", "#f3dede", fs=8)
box(0.44, 0.60, 0.22, 0.20, "우리 라벨\n**7,614**", "#eee", fs=9)
box(0.72, 0.60, 0.24, 0.20, "BQ 표 합계\n**7,614**", "#eee", fs=9)
ax.annotate("", xy=(0.44, 0.70), xytext=(0.36, 0.70),
            arrowprops=dict(arrowstyle="->", lw=1.3, color="#8b1a1a"))
ax.annotate("", xy=(0.72, 0.70), xytext=(0.36, 0.66),
            arrowprops=dict(arrowstyle="->", lw=1.3, color="#8b1a1a",
                            connectionstyle="arc3,rad=-0.35"))
ax.text(0.50, 0.50, "원천이 **하나**다 — 같은 PDF 를 두 번 읽었다",
        fontsize=9, color="#8b1a1a", fontweight="bold")

# 진짜 대조 (아래)
ax.text(0.02, 0.36, "실제로 대조인 것 (노트 673 이 찾았다)", fontsize=10,
        fontweight="bold", color="#1a5c2a")
box(0.06, 0.08, 0.30, 0.20, "고객사 최종 마감 실적\n(6/27 크랙 공유)", "#dff0e0", fs=8)
box(0.44, 0.08, 0.22, 0.20, "우리 라벨\n**5,960**", "#eee", fs=9)
box(0.72, 0.08, 0.24, 0.20, "BQ 일별 합\n**5,962**", "#eee", fs=9)
box(0.06, -0.20, 0.30, 0.20, "구글 시트 15kmc-…\n(우리 문서목록에 **없다**)", "#dff0e0", fs=8)
ax.annotate("", xy=(0.44, 0.18), xytext=(0.36, 0.18),
            arrowprops=dict(arrowstyle="->", lw=1.3, color="#1a5c2a"))
ax.annotate("", xy=(0.72, 0.14), xytext=(0.36, -0.10),
            arrowprops=dict(arrowstyle="->", lw=1.3, color="#1a5c2a",
                            connectionstyle="arc3,rad=0.3"))
ax.text(0.50, -0.14, "원천이 **둘**이고 차가 2명(0.03%)",
        fontsize=9, color="#1a5c2a", fontweight="bold")
ax.set_xlim(0, 1); ax.set_ylim(-0.24, 1.0)
fig.tight_layout(); fig.savefig(OUT / "lineage.pdf")

# ── (b) 흐르지 않는 흐름 ───────────────────────────────────────
fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.9))
a = axs[0]
a.bar([0], [48], color="#4a5c6a", width=0.5)
a.bar([1], [0], color="#8b1a1a", width=0.5)
a.text(0, 49.5, "48", ha="center", fontsize=11, fontweight="bold")
a.text(1, 1.5, "0", ha="center", fontsize=11, fontweight="bold", color="#8b1a1a")
a.set_xticks([0, 1])
a.set_xticklabels(["2026-08-05\n04:47~05:08 (20분)", "그 뒤\n26시간"], fontsize=9)
a.set_ylabel("적재된 행", fontsize=9)
a.set_ylim(0, 58)
a.set_title("'앞으로만 쌓인다' 는 추론이었다\n한 번의 소급 적재는 흐름이 아니다",
            fontsize=9.5, fontweight="bold")

a = axs[1]
lab = ["slack", "gdrive_sheet", "gdrive_pdf"]
val = [28, 13, 7]
col = ["#8b1a1a", "#4a5c6a", "#7d8fa0"]
w = a.barh([2, 1, 0], val, color=col, height=0.55)
for y, v, n in zip([2, 1, 0], val, ["5 프로젝트 · 방문객 65%", "1 프로젝트", "1 프로젝트"]):
    a.text(v + 0.7, y, f"{v}행 · {n}", va="center", fontsize=8.5)
a.set_yticks([2, 1, 0]); a.set_yticklabels(lab, fontsize=9.5)
a.set_xlim(0, 52)
a.set_xlabel("행 수", fontsize=9)
a.set_title("출처가 이유를 말한다\n계측이 아니라 **사람이 옮기는 채널**".replace("**", ""),
            fontsize=9.5, fontweight="bold")
for ax_ in axs:
    ax_.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(OUT / "notflowing.pdf")
print("그림 둘 저장")
