"""그림 둘 — 고침이 죽인 것(갈래 개수)과 **죽이지 못한 것**(창 불변)."""
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

DOM = ["애니", "만화", "세계애니", "게임", "모바일"]
UN = [0.8559, 0.7488, 0.7299, 0.4856, 0.0804]     # 합집합
AV = [0.1637, 0.1915, 0.1150, 0.2213, 0.0524]     # 갈래별 평균

# ── (a) 고침이 죽인 것 ─────────────────────────────────────────
fig, ax = plt.subplots(figsize=(6.6, 3.2))
x = np.arange(len(DOM))
w = 0.38
ax.bar(x - w / 2, UN, w, label="합집합 (돌린 버전)", color="#8b1a1a")
ax.bar(x + w / 2, AV, w, label="갈래별 평균 (고친 버전)", color="#4a5c6a")
ax.axhline(0.25, ls="--", lw=1, color="#333")
ax.text(4.45, 0.27, "사전등록 문턱 0.25", fontsize=8, ha="right", color="#333")
for xi, (u, a) in enumerate(zip(UN, AV)):
    ax.text(xi - w / 2, u + 0.015, f"{u:.2f}", ha="center", fontsize=8.5)
    ax.text(xi + w / 2, a + 0.015, f"{a:.2f}", ha="center", fontsize=8.5)
ax.set_xticks(x); ax.set_xticklabels(DOM, fontsize=9.5)
ax.set_ylabel("축 ↔ **갈래 개수** |스피어만|".replace("**", ""), fontsize=9)
ax.set_ylim(0, 0.98)
ax.set_title("혼잡도 축이 재던 것 — 갈래 개수", fontsize=11, fontweight="bold")
ax.legend(fontsize=8.5, frameon=False, loc="upper right")
ax.spines[["top", "right"]].set_visible(False)
ax.annotate("모바일은 애초에 깨끗하다\n(작품당 갈래가 거의 하나)", xy=(4, 0.09),
            xytext=(2.55, 0.42), fontsize=8, color="#555",
            arrowprops=dict(arrowstyle="->", color="#555", lw=1))
fig.tight_layout(); fig.savefig(OUT / "killed.pdf")

# ── (b) 고침이 못 죽인 것 ──────────────────────────────────────
fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.0))
W = [30, 90, 365]
a = axs[0]
a.plot(W, [0.1408, 0.1462, 0.1544], "o-", color="#8b1a1a", label="합집합")
a.plot(W, [0.0980, 0.1051, 0.1173], "s-", color="#4a5c6a", label="갈래별 평균")
a.set_xscale("log"); a.set_xticks(W); a.set_xticklabels([str(v) for v in W])
a.set_xlabel("창 길이 (일)", fontsize=9)
a.set_ylabel("축 ↔ 라벨 |스피어만| (학습, 가중)", fontsize=8.5)
a.set_ylim(0, 0.19)
a.set_title("창을 12배 바꿔도 거의 안 움직인다\n최대/최소 1.097 → 1.197 (문턱 1.3)",
            fontsize=9.5, fontweight="bold")
a.legend(fontsize=8.5, frameon=False)

a = axs[1]
AC_U = [0.9073, 0.8725, 0.8841, 0.8769, 0.8865]
AC_A = [0.8433, 0.7887, 0.8287, 0.9051, 0.8623]
x = np.arange(len(DOM))
a.bar(x - 0.19, AC_U, 0.38, color="#8b1a1a", label="합집합")
a.bar(x + 0.19, AC_A, 0.38, color="#4a5c6a", label="갈래별 평균")
a.set_xticks(x); a.set_xticklabels(DOM, fontsize=8.5, rotation=20)
a.set_ylim(0, 1.05)
a.set_ylabel("창 30일 ↔ 365일 자기상관", fontsize=8.5)
a.set_title("고쳐도 12배 다른 창이\n거의 같은 값을 낸다", fontsize=9.5, fontweight="bold")
a.legend(fontsize=8.5, frameon=False, loc="lower right")
for ax_ in axs:
    ax_.spines[["top", "right"]].set_visible(False)
fig.suptitle("내 예측이 틀린 자리 — 창 불변은 버그가 아니었다",
             fontsize=11, fontweight="bold")
fig.tight_layout(); fig.savefig(OUT / "survived.pdf")
print("그림 둘 저장")
