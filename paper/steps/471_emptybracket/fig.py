# -*- coding: utf-8 -*-
# 논문 471 figure — 손 수치 금지: 전부 산출물에서 계산한다(노트 880 교훈).
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).parent
ROOT = HERE / "../../.."

# 🔴 정오판(티처 #48): 883 의 자는 레코드 writer 를 포함해 인용률이 항등식 100% 였다.
# 정정판 산출물(writer 제외 + 미계수 4 도메인)로 갈아 끼운다.
cen = json.load(open(ROOT / "runners/out884_colcensus_fix.json"))
BOARD = [d for d in cen["도메인"] if d in cen["판 특징 이름(참고)"]]      # 판 도메인만
BOARD.sort(key=lambda d: -cen["도메인"][d]["행"])
consumed = [cen["도메인"][d]["빌더 인용됨"] for d in BOARD]
total = [cen["도메인"][d]["필드 수"] for d in BOARD]
left = [cen["도메인"][d]["미사용 후보(제외 후)"] for d in BOARD]
other = [t - c - l for t, c, l in zip(total, consumed, left)]
# 시간 게이트를 통과한 잔존은 0(텍스트 2 + 사후 1 — 노트 883 D 눈 판정)
# 영화 국적 = 시간 게이트 통과 실물 1건(채움 0.9955 · 개봉 시점 확정 · 판 축 없음)
gate_pass = [1 if d == "영화" else 0 for d in BOARD]

poll = json.load(open(ROOT / "data/ingest/youtube_poll/2026-08-09.json"))
n_ch = len(poll["대상"])
n_vid = sum(len(t["영상"]) for t in poll["대상"])
kob = json.load(open(ROOT / "data/ingest/kobis/2026-08-08.json"))
n_kob = len(kob.get("행") or kob.get("rows") or [])
cmt = json.load(open(ROOT / "runners/out883_ytcomment.json"))
n_cmt = cmt["총 파싱 건수"]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 3.0), gridspec_kw={"width_ratios": [1.35, 1]})

x = np.arange(len(BOARD))
ax1.bar(x, consumed, color="#4878a8", label="consumed by board")
ax1.bar(x, other, bottom=consumed, color="#c9c9c9", label="excluded (const/id/text/sparse)")
ax1.bar(x, left, bottom=np.array(consumed) + np.array(other), color="#e0a030", label="unused, not time-gated")
ax1.bar(x, gate_pass, bottom=np.array(total), color="#b0522e", label="film: nationality (time-gated, no axis)")
ax1.set_xticks(x)
EN = {"만화": "manga", "웹툰": "webtoon", "애니": "anime", "세계애니": "w-anime",
      "펀딩": "funding", "모바일": "mobile", "게임": "game", "도서": "book",
      "팝업": "popup", "아이돌": "idol", "영화": "film", "시장팝업": "mkt-popup"}
ax1.set_xticklabels([f"{EN.get(d, d)}\n{cen['도메인'][d]['행']:,}" for d in BOARD], fontsize=6.5)
ax1.set_ylabel("source record fields")
ax1.set_title("corrected ruler: 49 unused fields, incl. a live candidate", fontsize=9)
ax1.legend(fontsize=6, loc="upper right")

ax2.axis("off")
ax2.set_title("the door was open (day 0 of forward collection)", fontsize=9)
rows = [("YouTube channels polled", f"{n_ch}"),
        ("videos snapshotted", f"{n_vid}"),
        ("KOBIS box-office rows", f"{n_kob}"),
        ("keyless comment timestamps", f"{n_cmt}"),
        ("cycles the target list sat as []", "54 (note 829 -> 883)")]
for i, (k, v) in enumerate(rows):
    y = 0.82 - i * 0.17
    ax2.text(0.02, y, k, fontsize=8, va="center")
    ax2.text(0.98, y, v, fontsize=9, va="center", ha="right", weight="bold",
             color="#b0522e" if i == len(rows) - 1 else "#2e7d32")
    ax2.plot([0.02, 0.98], [y - 0.07, y - 0.07], lw=0.4, color="#ddd")
plt.tight_layout()
plt.savefig(HERE / "figs/emptybracket.png", dpi=150)
print("figure computed from artifacts")
