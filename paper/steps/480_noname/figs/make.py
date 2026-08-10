# -*- coding: utf-8 -*-
"""그림 1 — 롱테일은 자료가 없는 게 아니라 부를 이름이 없다(노트 893).
값은 전부 산출물에서 읽는다(손 전사 금지)."""
import json
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager, rcParams
for c in ("AppleSDGothicNeo", "Apple SD Gothic Neo", "NanumGothic"):
    try:
        font_manager.findfont(c, fallback_to_default=False); rcParams["font.family"] = c; break
    except Exception:
        pass
rcParams["axes.unicode_minus"] = False

R = "/Users/ax/world_model/runners/"
P = json.load(open(R + "out893_pilot.json"))
D = json.load(open(R + "out893_diag.json"))

Q = D["③ 질의어 종류별 수확(실물)"]
XB = D["③-b 층 × 질의어"]
NEG = D["🔴 ⑤ 언어를 맞춘 음성 비교(사전등록 비는 교란돼 있었다)"]
G1 = P["G1 원천별"]
LAY = P["게이트"]["G2 작품당 수확 중앙값 > 5"]["층별"]

fig, ax = plt.subplots(1, 3, figsize=(11.4, 3.5))

# ── 왼쪽: 질의어의 언어가 수확을 가른다 ────────────────────────
names = ["native\n(한글)", "synonyms\n(한글)", "english", "records\n(로마자)"]
keys = ["AniList native(한글)", "AniList synonyms(한글)",
        "AniList english", "manga_records.title(romaji)"]
med = [Q[k]["중앙값"] for k in keys]
zero = [Q[k]["0건"] for k in keys]
n = [Q[k]["n"] for k in keys]
cols = ["#2a6f6f", "#4f9494", "#c8a25a", "#a33"]
b = ax[0].bar(range(4), med, color=cols)
for i, (m, z, nn) in enumerate(zip(med, zero, n)):
    ax[0].text(i, m + 3, "%g" % m, ha="center", fontsize=8, fontweight="bold")
    ax[0].text(i, -9, "n=%d\n0건 %d" % (nn, z), ha="center", fontsize=6.4, color="#555")
ax[0].set_xticks(range(4)); ax[0].set_xticklabels(names, fontsize=7.2)
ax[0].set_ylabel("작품당 수확 중앙값", fontsize=8)
ax[0].set_title("질의어의 언어가 수확을 가른다", fontsize=9)
ax[0].set_ylim(-16, max(med) * 1.18)
ax[0].tick_params(axis="y", labelsize=7)

# ── 가운데: 층 × 언어 — 언어를 고정하면 단조가 돌아온다 ─────────
tiers = ["상", "중", "하"]
ko = [XB[f"{t}·한글"]["중앙값"] for t in tiers]
non = [XB[f"{t}·비한글"]["중앙값"] for t in tiers]
raw = [LAY[t]["중앙값"] for t in tiers]
x = range(3)
ax[1].plot(x, ko, "o-", color="#2a6f6f", ms=6, lw=1.8, label="한글 질의")
ax[1].plot(x, non, "s-", color="#a33", ms=5, lw=1.4, label="비한글 질의")
ax[1].plot(x, raw, "^--", color="#888", ms=5, lw=1.2, label="섞은 값(사전등록)")
for i, v in enumerate(ko):
    ax[1].text(i, v + 3, "%g" % v, ha="center", fontsize=7.5, color="#2a6f6f")
for i, v in enumerate(raw):
    ax[1].text(i, v + 3, "%g" % v, ha="center", fontsize=7, color="#888")
ax[1].set_xticks(list(x)); ax[1].set_xticklabels(["상위", "중간", "하위"], fontsize=8)
ax[1].set_ylabel("작품당 수확 중앙값", fontsize=8)
ax[1].set_title("언어를 고정하면 단조가 돌아온다", fontsize=9)
ax[1].legend(fontsize=6.6, framealpha=.9)
ax[1].tick_params(axis="y", labelsize=7)

# ── 오른쪽: 음성 통제 ─────────────────────────────────────────
labs = ["실물\n한글 질의", "음성 통제\n(없는 작품)", "실물\n비한글 질의"]
vals = [NEG["실물 한글 질의"]["중앙값"], NEG["음성(전부 한글)"]["중앙값"],
        NEG["실물 비한글 질의"]["중앙값"]]
c3 = ["#2a6f6f", "#a33", "#c8b0b0"]
ax[2].bar(range(3), vals, color=c3)
for i, v in enumerate(vals):
    ax[2].text(i, v + 2, "%g" % v, ha="center", fontsize=8.5, fontweight="bold")
ax[2].set_xticks(range(3)); ax[2].set_xticklabels(labs, fontsize=7)
ax[2].set_ylabel("작품당 수확 중앙값", fontsize=8)
r = NEG["언어 맞춘 비(음성 ÷ 실물한글)"]
ax[2].set_title("없는 작품이 실물의 %.0f%% 를 긁었다\n(사전등록 무효 문턱 25%%)"
                % (r * 100), fontsize=9)
ax[2].tick_params(axis="y", labelsize=7)
ax[2].text(0.5, max(vals) * .62,
           "언어 맞춘 비 %.2f\n사전등록 비 %.2f(언어 교란)"
           % (r, NEG["사전등록 비(음성 ÷ 실물전체)"]),
           fontsize=6.8, ha="center", color="#a33",
           bbox=dict(boxstyle="round,pad=.35", fc="#fff0f0", ec="#a33", lw=.6))

fig.tight_layout()
fig.savefig("/Users/ax/world_model/paper/steps/480_noname/figs/fig1.pdf")
print("ok")
