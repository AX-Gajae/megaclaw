"""그림 둘 — 채굴 깔때기와 **양방향** 태그 오류."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from pathlib import Path

for cand in ("AppleGothic", "Apple SD Gothic Neo"):
    if any(cand in f.name for f in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams["axes.unicode_minus"] = False
OUT = Path(__file__).resolve().parent

# ── (a) 깔때기 ────────────────────────────────────────────────
STEP = [("2024년 무라벨 레코드", 92),
        ("드라이브 문서 있음", 92),
        ("**결과보고서 파일** 있음", 24),
        ("텍스트 200자 초과", 9),
        ("숫자가 읽힘", 1),
        ("실측 방문객 (대용물 아님)", 0)]
fig, ax = plt.subplots(figsize=(7.2, 3.4))
lab = [s[0].replace("**", "") for s in STEP]
val = [s[1] for s in STEP]
col = ["#4a5c6a"] * 2 + ["#c25a3c"] + ["#4a5c6a"] * 2 + ["#8b1a1a"]
b = ax.barh(range(len(val))[::-1], val, color=col, height=0.62)
for i, (v, y) in enumerate(zip(val, range(len(val))[::-1])):
    ax.text(v + 1.2, y, f"{v}", va="center", fontsize=10, fontweight="bold")
ax.set_yticks(range(len(val))[::-1])
ax.set_yticklabels(lab, fontsize=9)
ax.set_xlim(0, 104)
ax.set_xlabel("레코드 수", fontsize=9)
ax.set_title("전수 채굴 깔때기 — 92건에서 실측 라벨 0건", fontsize=11, fontweight="bold")
ax.spines[["top", "right"]].set_visible(False)
ax.annotate("여기서 68건이 떨어진다\n(문서가 아예 없다)", xy=(24, 3), xytext=(46, 3.45),
            fontsize=8.5, color="#c25a3c",
            arrowprops=dict(arrowstyle="->", color="#c25a3c", lw=1.1))
fig.tight_layout()
fig.savefig(OUT / "funnel.pdf")

# ── (b) 양방향 오류 ────────────────────────────────────────────
fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.9))
a = axs[0]
a.bar([0, 1], [77, 56], color=["#4a5c6a", "#8b1a1a"], width=0.55)
a.set_xticks([0, 1])
a.set_xticklabels(["'결과보고서'\n태그 붙은 파일", "실은\n요건정의서"], fontsize=9)
a.set_title("노트 635 — 있다고 하는데 없다\n(73% 위양성)", fontsize=10, fontweight="bold")
for x, v in zip([0, 1], [77, 56]):
    a.text(x, v + 1.5, str(v), ha="center", fontsize=10, fontweight="bold")
a.set_ylim(0, 92)

a = axs[1]
a.bar([0, 1], [43, 43], color=["#4a5c6a", "#8b1a1a"], width=0.55)
a.set_xticks([0, 1])
a.set_xticklabels(["제목이 '결과보고서'\n인 실제 파일", "그 `kind` 태그가\n'운영일지'"], fontsize=9)
a.set_title("노트 667 — 없다고 하는데 있다\n(100% 위음성)", fontsize=10, fontweight="bold")
for x, v in zip([0, 1], [43, 43]):
    a.text(x, v + 0.8, str(v), ha="center", fontsize=10, fontweight="bold")
a.set_ylim(0, 52)
for a in axs:
    a.spines[["top", "right"]].set_visible(False)
    a.set_ylabel("파일 수", fontsize=9)
fig.suptitle("같은 메타데이터가 양쪽으로 거짓말한다", fontsize=11, fontweight="bold")
fig.tight_layout()
fig.savefig(OUT / "bothways.pdf")
print("그림 둘 저장")
