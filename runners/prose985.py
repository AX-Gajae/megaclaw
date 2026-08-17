#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""🔴 노트 985 의 **산문 주장 = 산출물 키** 등록부.

판정문·카드·인계 카드는 `runners/note985_gen.py` 가 **치환표에서** 지었으므로 수는
원리상 어긋날 수 없다. **그래서 여기서 등록하는 것은 「했다/안 했다」와 「어느 쪽으로
갈렸나」다** --- 특히 **이 사이클의 헤드라인 판정**(「누출에 특이적이지 않다 ·
이 설계로는 못 잰다」)이 산출물의 불리언과 같은 쪽인지.

조항 61: **대조는 등록한 주장만 본다.** 등록 안 한 문장은 원리상 안 보이므로
「전부 초록」은 「거짓이 없다」가 **아니다**.

    python3 runners/prose985.py --ref <40자 sha>
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runners"))

from runners.prose_check import check                            # noqa: E402
import cycle985 as CY                                            # noqa: E402

OUT = "runners/out985_prose.json"

D = "docs/판정_985.md"
C = "docs/card_985.md"
H = "docs/handoff_985.md"
AU = "runners/out985_audit.json"
PW = "runners/out985_power.json"
HS = "runners/out985_house.json"
CE = "runners/out985_certify.json"

SA = "§A 🔴🔴🔴 984 `⑤′` 절 8 재판정"
SB = "§B 🔴 「끊은 자리」를 갈라 센다 · 공통 17"
SC = "§C 🔴🔴 `⑤′` 절 1 소비자 분모의 기전"
P2 = "§2 🔴🔴 팔 사이 상관(위약 배터리를 «쓰기 전에»)"
P3 = "§3 🔴🔴🔴 `u=3` 네 칸은 한 검정이다"
P4 = "§4 🔴🔴 자 ③(붓스트랩)을 판정 규칙 안으로"
P5 = "§5 🔴🔴🔴 심은 누출 검정력 곡선(새 측정)"
HC = "§0-가 🔴🔴 집을 닫았나"
CG = "§가 🔴🔴🔴 985 자신"
CN = "§나 🔴🔴 검정력 시연 — 같은 자를 984 에 물린다(조항 64)"

CLAIMS: list = [
    # ── 가 · 984 채점 재발행 ────────────────────────────────────
    {"문서": D, "산출물": AU,
     "키": [SA, "🔴🔴🔴 지금 다시 재면", "절 8 통과"], "기대": False,
     "문장": "984 의 `⑤′` 절 8 은 «지금 다시 재면» 불통과다"},
    {"문서": D, "산출물": AU,
     "키": [SA, "🔴🔴🔴 지금 다시 재면", "🔴 ㉢ 미신고 저장소 밖 수리"], "기대": True,
     "문장": "984 의 사전등록 §8 「저장소 밖 레인: 0」이 거짓이다"},
    # ── 나 · u=3 네 칸이 한 검정 ────────────────────────────────
    {"문서": D, "산출물": PW,
     "키": [P3, "🔴 λ 별", "u=3", "🔴🔴🔴 네 칸이 한 검정인가"], "기대": True,
     "문장": "`u=3` 의 네 칸은 «한 검정»이 네 번 인쇄된 것이다"},
    {"문서": D, "산출물": PW,
     "키": [P3, "🔴 λ 별", "u=0", "🔴🔴🔴 네 칸이 한 검정인가"], "기대": False,
     "문장": "`u=0` 에서는 두 순위 벡터가 갈린다"},
    # ── 다 · 판정 강등 ─────────────────────────────────────────
    {"문서": D, "산출물": PW,
     "키": ["§1 🔴 이름 정정 — `오라클 여유` → `대조 여유`",
           "🔴🔴 그 양이 오라클 팔(`㉮`)에 의존하나"], "기대": False,
     "문장": "`대조 여유` 는 오라클 팔에 원리상 의존하지 않는다"},
    {"문서": D, "산출물": PW,
     "키": [P4, "🔴 λ 별", "u=0", "🔴🔴🔴 셋을 다 넘어 「선다」로 적을 수 있나"],
     "기대": False,
     "문장": "관문 셋을 다 넘지 못한다 — 「안 쟀다」로 적는다"},
    # ── 라 · 문서 고리 수렴과 그 자의 검정력 ─────────────────────
    {"문서": D, "산출물": CE,
     "키": [CN, "🔴🔴🔴 수렴했나(다섯 칸이 전부 같다)"], "기대": False,
     "문장": "같은 자를 984 에 물리면 떨어진다"},
    # ── 마 · 집 ────────────────────────────────────────────────
    {"문서": D, "산출물": HS,
     "키": [HC, "🔴🔴🔴 머지 뒤 규칙 A-2 가 참인가(= 같거나, 갈린 것이 이 사이클 항목 하나뿐)"],
     "기대": True,
     "문장": "규칙 A-2 가 참이다"},
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    a = ap.parse_args()
    t0 = CY.now()
    CY.begin(a.ref)
    cs0 = CY.code_stamp()
    res = check(CLAIMS, stdout=False)
    res["🔴 주장 수(등록한 것만 본다 · 조항 61)"] = len(CLAIMS)
    res["🔴 이 대조가 «못 보는» 것"] = (
        "🔴 **등록 안 한 문장은 원리상 안 보인다.** 「전부 초록」은 「거짓이 없다」가 "
        "아니라 「등록한 %d 개가 산출물과 같은 쪽이다」다(조항 61)" % len(CLAIMS))
    CY.write(OUT, res, a.ref, cs0, t0)
    print(json.dumps({"통과": res.get("통과"), "주장": len(CLAIMS)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
