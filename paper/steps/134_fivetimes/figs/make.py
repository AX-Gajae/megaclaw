"""그림 둘 — 다섯 사례, 그리고 감사가 다섯에서 아홉으로."""
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

fig, axs = plt.subplots(2, 1, figsize=(7.6, 6.4),
                        gridspec_kw={"height_ratios": [1.25, 1]})

# ── (a) 다섯 사례 ─────────────────────────────────────────────
a = axs[0]
a.axis("off")
ROWS = [
    ("671", "T 전파 검사", "위치 인자만 봤다", "키워드 전용 T(Data.rows)를 통째로 놓쳤다",
     "오탐 목록을 비웠는데 rows 가 안 나왔다"),
    ("672", "죽은 숫자 검사", "정정 문맥을 몰랐다", "내가 방금 쓴 설명 문장을 잡았다",
     "첫 실행 결과를 눈으로 봤다"),
    ("674", "장소 필드 열거", "키워드 목록에 scale 이 없었다", "showcase_scale 을 놓쳤다",
     "전수 열거로 필드를 다시 봤다"),
    ("676", "리포트 규약 확인", "HTML 이스케이프를 안 되돌렸다", "규약 둘이 '빠졌다' 고 나왔다",
     "빠진 둘이 다 아포스트로피 문장이었다"),
    ("677", "죽은 숫자 검사", "숫자 경계가 없었다", "0.037 이 +0.0374 안에서 맞았다",
     "남은 넷을 열어 봤다"),
]
hdr = ["노트", "무슨 검사", "구멍", "증상", "무엇이 드러냈나"]
xs = [0.02, 0.11, 0.28, 0.50, 0.75]
for x, h in zip(xs, hdr):
    a.text(x, 0.94, h, fontsize=9, fontweight="bold")
a.plot([0.0, 1.0], [0.90, 0.90], color="#333", lw=1.1)
for i, r in enumerate(ROWS):
    y = 0.80 - i * 0.16
    for x, v in zip(xs, r):
        a.text(x, y, v, fontsize=8.2, va="top", wrap=True,
               color="#8b1a1a" if x == xs[2] else "#222")
    if i < len(ROWS) - 1:
        a.plot([0.0, 1.0], [y - 0.055, y - 0.055], color="#ddd", lw=0.7)
a.set_xlim(0, 1); a.set_ylim(0.0, 1.0)
a.set_title("다섯 번 다 통과 결과가 아니라 회귀 시험이나 눈이 드러냈다",
            fontsize=11, fontweight="bold")

# ── (b) 감사가 다섯에서 아홉으로 ──────────────────────────────
a = axs[1]
OLD = ["덮음", "출처", "절단", "신선도", "대조"]
NEW = ["법칙전용\n(656)", "주장한고침\n(670)", "T 전파\n(668·671)", "죽은숫자\n(672·677)"]
CAUGHT = [0, 1, 1, 3]
x1 = np.arange(len(OLD)); x2 = np.arange(len(NEW)) + len(OLD) + 0.6
a.bar(x1, [0] * len(OLD), 0.6, color="#c9ccd1")
a.bar(x1, [0.35] * len(OLD), 0.6, color="#c9ccd1")
a.bar(x2, [c + 0.35 for c in CAUGHT], 0.6, color="#1a3f6b")
for x, c in zip(x2, CAUGHT):
    a.text(x, c + 0.45, f"{c}건 잡음" if c else "0건", ha="center", fontsize=8.5,
           fontweight="bold")
a.set_xticks(list(x1) + list(x2))
a.set_xticklabels(OLD + NEW, fontsize=8.5)
a.set_yticks([])
a.set_ylabel("실제로 잡은 결함", fontsize=9)
a.set_title("자료를 재는 다섯(회색) + 저장소와 기록 자신을 재는 넷(남색)\n"
            "새 넷이 이 세션에서 실제 결함 다섯을 잡았다",
            fontsize=10.5, fontweight="bold")
a.spines[["top", "right", "left"]].set_visible(False)
fig.tight_layout(); fig.savefig(OUT / "fivetimes.pdf")
print("그림 저장")
