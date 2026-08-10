#!/usr/bin/env python3
# 노트 900 그림 — 🔴 손 전사 금지: 값은 전부 산출물에서 **읽는다**.
#   fig1  (a) 팔별 판 평균 ± SE   (b) 세 팔의 판 짝 Δ · BCa · 채택 문턱   (c) 게임 대 나머지 열하나
#   fig2  (a) 유보 126행 고유 설계행 다섯 변형   (b) 필요치 대 실측(게임 Δρ)
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parents[4]
HERE = pathlib.Path(__file__).resolve().parent

for cand in ("AppleGothic", "Apple SD Gothic Neo", "NanumGothic", "Malgun Gothic"):
    if any(f.name == cand for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams["axes.unicode_minus"] = False

L = json.loads((ROOT / "runners/out900_levers.json").read_text())
H = json.loads((ROOT / "runners/out900h_design2.json").read_text())

PAIR = L["③ 짝 Δ(팔 X − 팔 A · 같은 씨앗)"]
BOARD = L["판 수준(팔별)"]
VERD = L["④ 판정"]
ARMS = ["B_union", "C_domax", "D_nanpad"]
THR = VERD["B_union"]["문턱(정본)"]
THR_DAY = VERD["B_union"]["문턱(일 군집 병기)"]

# ── fig1 ────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(1, 3, figsize=(13.6, 4.0))

# (a) 팔별 판 평균 ± SE
names = ["A_common", "B_union", "C_domax", "D_nanpad"]
mu = [BOARD[n]["평균"] for n in names]
se = [BOARD[n]["SE"] for n in names]
cols = ["#333333", "#c0392b", "#c0392b", "#8e44ad"]
ax[0].errorbar(range(4), mu, yerr=se, fmt="o", ms=7, capsize=5,
               ecolor="#888888", mfc="none", mec="none", lw=1.2, zorder=1)
for i, (m, c) in enumerate(zip(mu, cols)):
    ax[0].plot(i, m, "o", ms=8, color=c, zorder=3)
ax[0].axhline(mu[0], color="#333333", ls="--", lw=1.0, alpha=.6)
ax[0].set_xticks(range(4))
ax[0].set_xticklabels(["A\n(챔피언)\n36축·88열", "B\nunion\n40축·96열",
                       "C\nDOMAX\n36축·96열", "D\nNaN패딩\n40축·96열"], fontsize=8)
ax[0].set_ylabel("판 ρ (12씨앗 평균 ± SE)")
ax[0].set_title("(a) 축 넷을 닿게 한 세 방식 — 전부 팔 A 아래", fontsize=10)
ax[0].annotate(f"{mu[0]:.5f}", (0, mu[0]), textcoords="offset points",
               xytext=(6, 8), fontsize=8, color="#333333")
ax[0].grid(axis="y", alpha=.25)

# (b) 판 짝 Δ · BCa · 채택 문턱
d = [PAIR[a]["평균 Δ"] for a in ARMS]
lo = [PAIR[a]["평균 Δ"] - PAIR[a]["BCa 95%"][0] for a in ARMS]
hi = [PAIR[a]["BCa 95%"][1] - PAIR[a]["평균 Δ"] for a in ARMS]
ax[1].axhline(0, color="#666666", lw=1.0)
ax[1].axhline(THR, color="#1f7a1f", lw=1.4, ls="-")
ax[1].axhline(THR_DAY, color="#1f7a1f", lw=1.0, ls=":")
ax[1].errorbar(range(3), d, yerr=[lo, hi], fmt="s", ms=8, capsize=6,
               color="#c0392b", ecolor="#c0392b", lw=1.6)
ax[1].set_xticks(range(3))
ax[1].set_xticklabels(["B union", "C DOMAX", "D NaN"], fontsize=9)
ax[1].set_ylabel("판 짝 Δ (팔 X − 팔 A · 같은 씨앗)")
ax[1].set_title("(b) 셋 다 상한 < 0 — 「모른다」가 아니라 패", fontsize=10)
ax[1].annotate(f"채택 문턱 {THR}", (2.35, THR), fontsize=8, color="#1f7a1f",
               ha="right", va="bottom")
ax[1].annotate(f"일 군집 {THR_DAY}", (2.35, THR_DAY), fontsize=7.5, color="#1f7a1f",
               ha="right", va="top", alpha=.8)
for i, a in enumerate(ARMS):
    ax[1].annotate(f"{PAIR[a]['양수 씨앗 수']}/12 양수", (i, PAIR[a]["BCa 95%"][0]),
                   textcoords="offset points", xytext=(0, -14),
                   fontsize=7.5, ha="center", color="#c0392b")
ax[1].grid(axis="y", alpha=.25)

# (c) 게임 대 나머지 열하나 (판 기여)
g53 = PAIR["B_union"]["🔴 5.3 게임 대 나머지 열하나"]
gc, rc = g53["게임 판 기여"], g53["나머지 11 판 기여 합"]
ax[2].barh([1, 0], [gc, rc], color=["#c0392b", "#95a5a6"], height=.5)
ax[2].axvline(0, color="#666666", lw=1.0)
ax[2].set_yticks([1, 0])
ax[2].set_yticklabels(["게임\n(축 넷의 주인)", "나머지 열하나\n합"], fontsize=9)
ax[2].set_xlabel("판 기여 (w/3775 × Δρ) · 팔 B")
share = 100 * gc / (gc + rc)
ax[2].set_title(f"(c) 손실의 {share:.0f}%가 게임 자신에게서 나온다", fontsize=10)
ax[2].annotate(f"{gc:+.6f}", (gc, 1), textcoords="offset points",
               xytext=(-6, 0), fontsize=8.5, ha="right", va="center", color="white")
ax[2].annotate(f"{rc:+.6f}  (음수 도메인 {g53['나머지 11 중 Δρ 음수 도메인 수']}/11)",
               (rc, 0), textcoords="offset points", xytext=(-6, 0),
               fontsize=8, ha="right", va="center")
ax[2].grid(axis="x", alpha=.25)

fig.tight_layout()
fig.savefig(HERE / "fig1.pdf")
plt.close(fig)

# ── fig2 ────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(1, 2, figsize=(10.4, 4.0))

# (a) 유보 126행 고유 설계행 — 다섯 변형
# 🔴 변형 0·1 은 1차 시험(H1)에만, 채움 변형 2·2b 는 **재시험(H2)에만** 있다.
#    H1 의 변형 2(=27)는 채움 패치가 `json.load` 를 걸었는데 `tri_domain.py:69` 는
#    `json.loads(read_text())` 라 **한 번도 안 걸린** 무효값이다(지평 팔 자가 적발) — 안 그린다.
#    교차 확인: 음성대조 3 이 두 파일에서 같은 값이어야 한다.
H1 = json.loads((ROOT / "runners/out900h_design.json").read_text())
key = "고유 설계행 uniq(_design)"
NEG = "3 채우기만(BLOCK 유지) — 음성대조"
assert H1[NEG][key] == H[NEG][key], (H1[NEG][key], H[NEG][key])
assert H["2 BLOCK 해제 + 88행 채움(가정 · 씨앗0)"]["🔴 유보 entry_friction 마스크 합"] == 126.0
pick = [(H1, "0 현행(BLOCK 그대로)"),
        (H1, "1 BLOCK 만 항등(채우지 않음)"),
        (H, "2 BLOCK 해제 + 88행 채움(가정 · 씨앗0)"),
        (H, "2b BLOCK 해제 + 88행 채움(가정 · 씨앗7)"),
        (H1, NEG)]
vals = [src[k][key] for src, k in pick]
lab = [src[k]["이름"] for src, k in pick]
col = ["#7f8c8d", "#1f7a1f", "#c0392b", "#c0392b", "#7f8c8d"]
bars = ax[0].bar(range(len(vals)), vals, color=col[:len(vals)], width=.62)
for b, v in zip(bars, vals):
    ax[0].annotate(str(v), (b.get_x() + b.get_width() / 2, v),
                   textcoords="offset points", xytext=(0, 3),
                   ha="center", fontsize=10, weight="bold")
ax[0].set_xticks(range(len(vals)))
ax[0].set_xticklabels([s.replace(" ", "\n", 1) for s in lab], fontsize=7.6)
ax[0].set_ylabel("유보 126행의 고유 설계행")
ax[0].set_title("(a) 27 은 수집이 아니라 한 줄에서 나온다 —\n채우면 오히려 내려간다", fontsize=10)
ax[0].set_ylim(0, max(vals) * 1.22)
ax[0].grid(axis="y", alpha=.25)

# (b) 필요치 대 실측
v = VERD["B_union"]
need, need_d = v["🔴 넘으려면 게임 Δρ 가 얼마여야 하나(문턱 0.00353)"], \
    v["🔴 넘으려면 게임 Δρ 가 얼마여야 하나(문턱 0.00370)"]
obs = {a: VERD[a]["실측 게임 Δρ"] for a in ARMS}
ax[1].axhline(0, color="#666666", lw=1.0)
ax[1].axhline(need, color="#1f7a1f", lw=1.6)
ax[1].axhline(need_d, color="#1f7a1f", lw=1.0, ls=":")
xs = range(len(ARMS))
ax[1].bar(xs, [obs[a] for a in ARMS], color="#c0392b", width=.5)
gb = PAIR["B_union"]["도메인별 짝 Δ"]["게임"]["BCa 95%"]
ax[1].errorbar([0], [obs["B_union"]], yerr=[[obs["B_union"] - gb[0]], [gb[1] - obs["B_union"]]],
               fmt="none", ecolor="#333333", capsize=5, lw=1.3)
ax[1].set_xticks(list(xs))
ax[1].set_xticklabels(["B union", "C DOMAX", "D NaN"], fontsize=9)
ax[1].set_ylabel("게임 Δρ")
ax[1].set_title("(b) 크기가 모자란 게 아니라 부호부터 반대다", fontsize=10)
ax[1].annotate(f"판 문턱을 넘으려면 게임 Δρ ≥ {need:+.5f}", (2.4, need),
               fontsize=8.5, color="#1f7a1f", ha="right", va="bottom")
ax[1].annotate(f"(일 군집이면 {need_d:+.5f})", (2.4, need_d), fontsize=7.5,
               color="#1f7a1f", ha="right", va="top", alpha=.85)
for i, a in enumerate(ARMS):
    ax[1].annotate(f"{obs[a]:+.5f}\n({VERD[a]['🔴 실측 / 필요']:+.3f}배)",
                   (i, obs[a]), textcoords="offset points", xytext=(0, -26),
                   ha="center", fontsize=7.8, color="#c0392b")
ax[1].set_ylim(min(obs.values()) * 1.9, need * 1.28)
ax[1].grid(axis="y", alpha=.25)

fig.tight_layout()
fig.savefig(HERE / "fig2.pdf")
plt.close(fig)
print("fig1.pdf · fig2.pdf 그림")
print("  팔 A 판", mu[0], "· 팔 B 짝 Δ", d[0], "· 게임 판 기여", gc, "· 게임 몫", round(share, 1), "%")
print("  설계행", dict(zip(lab, vals)))
print("  필요치", need, "· 실측", obs)
