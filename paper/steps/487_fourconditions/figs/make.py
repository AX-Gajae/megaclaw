#!/usr/bin/env python3
# 노트 902 그림 — 🔴 손 전사 금지: 값은 전부 산출물에서 **읽는다**.
#   fig1 (a) 옛→새 등급 이동  (b) 바뀐 이유 분해  (c) 무엇이 막았나
#   fig2 (a) 식1×식3 교차 — 교집합이 왜 0 이었나  (b) 이미 열려 있던 열(지평)
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

ID = json.loads((ROOT / "runners/out902_identify.json").read_text())
SNAP = json.loads((ROOT / "runners/out902h_snap.json").read_text())

KH = "🔴 헤드라인 — T1 만의 수 (T2 는 절대 안 더한다 · prereg_901:61)"
H = ID[KH]
MOVE = ID["등급 이동표(옛→새)"]
WHY = ID["바뀐 이유별"]
BLOCK = ID["🔴 무엇이 막았나"]
T1 = "T1"                       # 🔴 헤드라인은 T1 칸만 쓴다(사전등록 규칙)

# ── fig1 ────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(1, 3, figsize=(13.6, 4.0))

# (a) 옛 대 새 등급 (T1)
grades = ["A", "B", "C"]
old = [H[f"옛 등급 {g}"][T1] for g in grades]
new = [H[f"새 등급 {g}"][T1] for g in grades]
x = range(3)
w = .36
ax[0].bar([i - w / 2 for i in x], old, width=w, color="#adb5bd", label="901 (5조건)")
ax[0].bar([i + w / 2 for i in x], new, width=w,
          color=["#1f7a1f", "#e8a33d", "#c0392b"], label="902 (4조건)")
for i, (o, n) in enumerate(zip(old, new)):
    ax[0].annotate(str(o), (i - w / 2, o), textcoords="offset points", xytext=(0, 3),
                   ha="center", fontsize=9, color="#666666")
    ax[0].annotate(str(n), (i + w / 2, n), textcoords="offset points", xytext=(0, 3),
                   ha="center", fontsize=10, weight="bold")
ax[0].set_xticks(list(x))
ax[0].set_xticklabels([f"{g}등급" for g in grades], fontsize=10)
ax[0].set_ylabel(f"개입-결과 짝 (분모 T1 {H['짝 전량'][T1]})")
ax[0].set_title(f"(a) 「A=0」은 재현되지 않는다 — A: {old[0]} → {new[0]}", fontsize=10)
ax[0].legend(fontsize=8)
ax[0].grid(axis="y", alpha=.25)

# (b) 바뀐 이유
labs, vals = [], []
for k, v in WHY.items():
    labs.append(k.replace("🔴 ", "").replace(" — ", "\n"))
    vals.append(v[T1])
yy = list(range(len(labs)))[::-1]
cols = ["#adb5bd" if "변화 없음" in l else "#c0392b" for l in labs]
ax[1].barh(yy, vals, color=cols, height=.6)
for y, v in zip(yy, vals):
    ax[1].annotate(str(v), (v, y), textcoords="offset points", xytext=(4, 0),
                   va="center", fontsize=9.5, weight="bold")
ax[1].set_yticks(yy)
ax[1].set_yticklabels([l[:38] for l in labs], fontsize=7.4)
ax[1].set_xlabel(f"짝 수 (분모 T1 {H['짝 전량'][T1]})")
ax[1].set_title("(b) 무엇 때문에 바뀌었나 —\n🔴 식5 폐지만으로도 움직인 짝이 있다", fontsize=10)
ax[1].set_xlim(0, max(vals) * 1.2)
ax[1].grid(axis="x", alpha=.25)

# (c) 무엇이 막았나
BK = [("🔴 W4 처치 시점 없음 = 식3「모른다」짝 수", "W4 처치 시점 없음\n(식3=모른다)"),
      ("B 등급이 못 채운 칸 — 식3=모른다(W4)", "B 가 못 채운 칸\n= W4"),
      ("C 등급 — 식1·식3 둘 다 못 채움", "C — 둘 다 못 채움"),
      ("C 등급 — 식3=아니오(W7 역인과 확정)", "C — 역인과 확정(W7)"),
      ("B 등급이 못 채운 칸 — 식1=아니오", "B 가 못 채운 칸\n= 식1")]
labs2 = [lb for k, lb in BK if k in BLOCK]
vals2 = [BLOCK[k][T1] for k, lb in BK if k in BLOCK]
yy2 = list(range(len(labs2)))[::-1]
ax[2].barh(yy2, vals2, color=["#c0392b" if v == max(vals2) else "#8e8e8e" for v in vals2],
           height=.6)
for y, v in zip(yy2, vals2):
    ax[2].annotate(str(v), (v, y), textcoords="offset points", xytext=(4, 0),
                   va="center", fontsize=9.5)
ax[2].set_yticks(yy2)
ax[2].set_yticklabels(labs2, fontsize=7.4)
ax[2].set_xlabel(f"짝 수 (분모 T1 {H['짝 전량'][T1]})")
ax[2].set_title("(c) 막는 것은 W4 하나다 —\nW8·W2 는 등급에 안 들어간다", fontsize=10)
ax[2].set_xlim(0, max(vals2) * 1.2)
ax[2].grid(axis="x", alpha=.25)

fig.tight_layout()
fig.savefig(HERE / "fig1.pdf")
plt.close(fig)

# ── fig2 ────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(1, 2, figsize=(10.4, 4.0))

# (a) 식1 × 식3 — 교집합이 왜 0 이었나
d3 = BLOCK["식3 값 분포(105짝)"]
d1 = BLOCK["식1 값 분포(105짝)"]
names = ["식3 = 예\n(역인과 아님)", "식3 = 모른다\n(W4)", "식3 = 아니오\n(W7)",
         "식1 = 예", "식1 = 아니오"]
vals3 = [d3["예"], d3["모른다"], d3["아니오"], d1["예"], d1["아니오"]]
cols3 = ["#1f7a1f", "#c0392b", "#8e5aa6", "#1f7a1f", "#c0392b"]
bars = ax[0].bar(range(5), vals3, color=cols3, width=.62)
for b, v in zip(bars, vals3):
    ax[0].annotate(str(v), (b.get_x() + b.get_width() / 2, v), textcoords="offset points",
                   xytext=(0, 3), ha="center", fontsize=10, weight="bold")
ax[0].axvline(2.5, color="#666666", lw=1.0, ls="--")
ax[0].set_xticks(range(5))
ax[0].set_xticklabels(names, fontsize=7.4)
ax[0].set_ylabel("짝 수 (분모 105 · T1+T2)")
ax[0].set_title("(a) 901 에서 식1=예 34 와 식3=예 25 의\n교집합이 0 이었다 — 구조적으로",
                fontsize=9.5)
ax[0].grid(axis="y", alpha=.25)

# (b) 지평 — 이미 열려 있던 열. 🔴 키 경로를 **명시**로 잡는다(추측 탐색 금지).
KV = "🔴 ⑥ 판정 — W4 를 여나"
KN = "나 · 🔴 그런데 901 이 T1 로 세지 **않은** 열 하나가 열려 있다"
assert KV in SNAP, list(SNAP)
assert KN in SNAP[KV], list(SNAP[KV])
V = SNAP[KV][KN]
KM = "②③ 영화 일별 박스오피스"
assert KM in SNAP, list(SNAP)
M = SNAP[KM]

# 🔴 키 경로를 **명시**로 잡는다. 없으면 키 목록을 들고 죽는다(조항 59).
def at(sec, key, where):
    if key not in sec:
        raise SystemExit(f"🔴 '{key}' 가 없다 — {where} 의 키: {list(sec)}")
    return sec[key]

OBJ = at(M, "② 개체", "영화 일별")
CHG = at(M, "③ 값 변화", "영화 일별")
XS = at(at(SNAP, "⑤ 판 유보(D3) 교집합", "snap"), "영화", "⑤ 교집합")
WIN = at(XS, "🔴 라벨 창 안의 처치 시점", "영화 교집합")

rows = at(OBJ, "총 관측(행)", "② 개체")
rep = at(CHG, "분모(2회 이상 관측된 제목)", "③ 값 변화")
tot = at(WIN, "분모(D3 · 2회+ 관측)", "라벨 창")
inwin = [v for k, v in WIN.items() if "스크린수 변화가 1회 이상" in str(k)]
if not inwin:
    raise SystemExit(f"🔴 '창 안 스크린수 변화' 키가 없다 — {list(WIN)}")
inwin = inwin[0]

labs4 = [f"일별 표 총행\n{rows:,}", f"2회 이상 관측된 제목\n{rep:,}",
         f"영화 D3 유보\n(2회+ 관측) {tot}", f"🔴 라벨 창 안에서\n스크린수 변함 {inwin}"]
vals4 = [rows, rep, tot, inwin]
bars = ax[1].bar(range(4), vals4,
                 color=["#adb5bd", "#7f8c8d", "#5b7fa6", "#1f7a1f"], width=.6)
for b, v in zip(bars, vals4):
    ax[1].annotate(f"{v:,}", (b.get_x() + b.get_width() / 2, v), textcoords="offset points",
                   xytext=(0, 3), ha="center", fontsize=9.5, weight="bold")
ax[1].set_xticks(range(4))
ax[1].set_xticklabels(labs4, fontsize=7.4)
ax[1].set_ylabel("행 / 개체 수 (로그)")
ax[1].set_yscale("log")
ax[1].set_title("(b) 이미 열려 있던 열 — 일별 스크린수·상영횟수\n"
                "🔴 902 는 이것이 개입인지 판정 안 했다", fontsize=9.3)
ax[1].grid(axis="y", alpha=.25)

fig.tight_layout()
fig.savefig(HERE / "fig2.pdf")
plt.close(fig)

print("fig1.pdf · fig2.pdf")
print("  T1 옛", old, "→ 새", new)
print("  이유", dict(zip(labs, vals)))
print("  막음", dict(zip(labs2, vals2)))
print("  지평", rows, rep, tot, inwin)
print("  판정문:", str(V.get("얼마나"))[:90])
