# -*- coding: utf-8 -*-
"""그림 1 — 막히는 것은 롱테일이 아니라 인기작이다(노트 894).
값은 전부 산출물에서 읽는다(손 전사 금지)."""
import json
from datetime import date
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
K = json.load(open(R + "out894_knock.json"))
F = json.load(open(R + "out894_refit.json"))
C = K["🔴 ⓒ' 도달 깊이는 무엇이 정하는가(사후 탐색)"]
TODAY = date(2026, 8, 10)

fig, ax = plt.subplots(1, 3, figsize=(11.6, 3.5))

# ── 왼쪽: 수리 효과 ────────────────────────────────────────────
# 🔴 티처 #57 M1 정정 — 초판은 이 숫자를 **하드코딩**했다(docstring 이 '손 전사 금지'
# 라고 적어 놓고 `json.dumps(F)` 를 변수에 담기만 하고 안 썼다). 이제 실제로 읽는다.
G = F["🔴 ① 디시 가드 뒤집기"]
labs = ["디시\n판정 불가", "실물 1,200단계\n판정 불가"]
before = [G["🔴 디시 판정 불가"]["수리 전"], G["실물 1,200 단계 회계"]["수리 전"]["판정 불가"]]
after = [G["🔴 디시 판정 불가"]["수리 후"], G["실물 1,200 단계 회계"]["수리 후"]["판정 불가"]]
x = range(2)
w = 0.36
ax[0].bar([i - w/2 for i in x], before, w, color="#a33", label="수리 전")
ax[0].bar([i + w/2 for i in x], after, w, color="#2a6f6f", label="수리 후")
for i, (b, a) in enumerate(zip(before, after)):
    ax[0].text(i - w/2, b + 8, str(b), ha="center", fontsize=8, color="#a33")
    ax[0].text(i + w/2, a + 8, str(a), ha="center", fontsize=8,
               fontweight="bold", color="#2a6f6f")
ax[0].set_xticks(list(x)); ax[0].set_xticklabels(labs, fontsize=7.5)
ax[0].set_ylabel("단계 수", fontsize=8)
ax[0].set_title("가드가 반대 방향이었다\n('확인된 0' 을 '모른다' 로 강등)", fontsize=9)
ax[0].legend(fontsize=6.8, framealpha=.9)
ax[0].tick_params(axis="y", labelsize=7)

# ── 가운데: 끝쪽 분포 ──────────────────────────────────────────
ends = C["끝쪽 분포"]
capped = C["끝쪽 = 120(상한에 붙음)"]
free = C["끝쪽 < 120(검색이 전량을 소진)"]
cols = ["#a33" if e >= 120 else "#2a6f6f" for e in sorted(ends)]
ax[1].bar(range(len(ends)), sorted(ends), color=cols)
ax[1].axhline(120, color="#a33", lw=1.2, ls="--")
ax[1].text(0.1, 124, "서버 상한 120쪽 = 3,000건", fontsize=7, color="#a33")
ax[1].set_xticks(range(len(ends)))
ax[1].set_xticklabels([str(e) for e in sorted(ends)], fontsize=7)
ax[1].set_xlabel("작품별 검색 끝쪽", fontsize=8)
ax[1].set_ylabel("끝쪽", fontsize=8)
ax[1].set_title("%d/%d 이 상한에 붙었다 (붉은색)" % (capped, capped + free), fontsize=9)
ax[1].set_ylim(0, 150)
ax[1].tick_params(axis="y", labelsize=7)

# ── 오른쪽: 언급이 많을수록 못 판다 ────────────────────────────
xs, ys, ann = [], [], []
for r in C["상세"]:
    cap = r.get("검색 상한 추정(건)")
    old = r.get("1쪽 제일 오래된")
    if not cap or not old:
        continue
    y, m, d2 = (int(v) for v in old.split("-"))
    days = (TODAY - date(y, m, d2)).days
    xs.append(cap); ys.append(max(days, 1)); ann.append(r["질의"][:10])
ax[2].scatter(xs, ys, s=46, color="#a33", zorder=3)
for xx, yy, nn in zip(xs, ys, ann):
    ax[2].annotate(nn, (xx, yy), fontsize=6.3, xytext=(4, 4),
                   textcoords="offset points")
ax[2].set_xscale("log"); ax[2].set_yscale("log")
ax[2].set_xlabel("검색이 주는 총량 상한 (건 · 로그)", fontsize=8)
ax[2].set_ylabel("1쪽이 덮는 과거 (일 · 로그)", fontsize=8)
ax[2].set_title("언급이 많을수록 과거를 못 판다", fontsize=9)
ax[2].tick_params(labelsize=7)
ax[2].grid(alpha=.25, lw=.5)

fig.tight_layout()
fig.savefig("/Users/ax/world_model/paper/steps/481_popularblocked/figs/fig1.pdf")
print("ok · 점", len(xs))
