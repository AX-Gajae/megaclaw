#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""🔴 노트 986 의 **산문 주장 = 산출물 키** 등록부 · 🔴🔴🔴 **그 자를 «뒤집는다»**.

🔴 **왜 뒤집나 (티처 #124 즉시정정 ⑤).** 985 의 「산문 8/8」은 **등록 문장을 판정문
생성기에 넣어** 닫았다 --- 곧 **분모를 자기가 정했다.** 그러면 「전부 초록」은
**「등록한 것만 봤다」**의 다른 말이다.

**986 이 더하는 자(§B)**: 🔴 **판정문의 «주장 문장» 전량을 분모로 두고,
그중 «등록되지 않은» 것이 몇인지를 센다.** 분모를 문서가 정하지 자가 정하지 않는다.

조항 61: 이 자도 한계가 있다 --- 「주장 문장」의 정의(굵은 조각 + 숫자)는 여전히
사람이 고른 것이다. **그 정의를 여기 박고 산출물에 싣는다.**

    python3 runners/prose986.py --ref <40자 sha>
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runners"))

from runners.prose_check import check                            # noqa: E402
import cycle986 as CY                                            # noqa: E402

OUT = "runners/out986_prose.json"

D = "docs/판정_986.md"
PR = "docs/pr_986.md"
AU = "runners/out986_audit.json"
PW = "runners/out986_power.json"
HS = "runners/out986_house.json"
CE = "runners/out986_certify.json"

SA = "§A 🔴🔴🔴 985 의 세 오기"
SB = "§B 🔴🔴 PR #243 본문 대 985 문서"
SC = "§C 🔴🔴🔴 R3 손 전사 자의 분모"
P1 = "§1 🔴🔴🔴 부트스트랩 감싼 δ 쓸기"
P2 = "§2 🔴🔴🔴 천장 — 「δ 를 아무리 키워도 발화율은 얼마인가」"
P3 = "§3 🔴🔴🔴 983 에도 같은 자 — 「U 자 되오름」의 검정력"
HC = "§0-가 🔴🔴 집을 닫았나"
CN = "§나 🔴🔴 검정력 시연 — 같은 여섯 칸 자를 985 에 문다(조항 64)"
CL = "§라 🔴🔴🔴 자기 입력 교란(986 신설)"

CLAIMS: list = [
    # ── 가 · 여섯째 칸 ─────────────────────────────────────────
    {"문서": D, "산출물": CE, "키": [CN, "🔴🔴🔴 수렴했나(여섯 칸이 전부 같다)"],
     "기대": False,
     "문장": "같은 여섯 칸 자를 985 에 물리면 «떨어진다»"},
    {"문서": D, "산출물": CE, "키": [CN, "🔴🔴🔴 여섯째 칸이 985 에서 «떨어지나»"],
     "기대": True,
     "문장": "985 에서 떨어지는 것은 «여섯째 칸»이다 --- 다섯 칸은 전부 초록이었다"},
    {"문서": D, "산출물": CE, "키": [CL, "🔴🔴🔴 가짜 판에서 «떨어지나»"], "기대": True,
     "문장": "자기 입력을 한 글자 교란하면 자가 떨어진다"},
    # ── 나 · 985 의 세 오기 ────────────────────────────────────
    {"문서": D, "산출물": AU, "키": [SA, "① 반증조건", "🔴🔴🔴 어긋나나"], "기대": True,
     "문장": "985 의 다섯 문서가 실은 「반증조건 13 / 14」는 정본 채점과 어긋난다"},
    {"문서": D, "산출물": AU, "키": [SA, "② 「끊은 자리」", "🔴🔴🔴 어긋나나"], "기대": True,
     "문장": "「끊은 자리」의 하드코딩 합은 실제 합과 어긋난다"},
    {"문서": D, "산출물": AU, "키": [SA, "③ `⑤′` 절 1 소비자", "🔴🔴🔴 어긋나나"],
     "기대": True,
     "문장": "PR #243 이 실은 소비자 수는 정본과 어긋난다"},
    # ── 다 · 검정력 ────────────────────────────────────────────
    {"문서": D, "산출물": PW,
     "키": [P1, "🔴 λ 별", "u=0", "🔴🔴 식별됐나(구간 폭이 δ 격자 한 칸 이하인가)"],
     "기대": False,
     "문장": "`u=0` 의 최소 검출 δ 는 «식별되지 않는다»"},
    {"문서": D, "산출물": PW,
     "키": [P2, "🔴 λ 별", "u=0", "🔴🔴 천장이 1.0 에 «훨씬» 못 미치나(< 0.75)"],
     "기대": True,
     "문장": "이 규칙의 발화율에는 «천장»이 있다 --- δ 를 키워도 안 오른다"},
    # ── 라 · R3 ────────────────────────────────────────────────
    {"문서": D, "산출물": AU,
     "키": [SC, "🔴🔴 검정력 시연(조항 64) — 같은 신판 자를 985 의 러너 전량에 문다",
           "🔴🔴🔴 `audit985.py` 의 `= 3` 을 잡았나"], "기대": True,
     "문장": "신판 손 전사 자가 `audit985.py` 의 하드코딩을 «실제로» 잡는다"},
    # ── 마 · 집 ────────────────────────────────────────────────
    {"문서": D, "산출물": HS,
     "키": [HC, "🔴🔴🔴 머지 뒤 규칙 A-2 가 참인가(= 같거나, 갈린 것이 등록한 것뿐)"],
     "기대": True, "문장": "규칙 A-2 가 참이다"},
]

#: 🔴 **「주장 문장」의 정의(측정 전에 박는다)** --- 굵은 조각을 담고 숫자가 있는 문장.
CLAIM_SENT = re.compile(r"[^\n]*\*\*[^\n*]+\*\*[^\n]*")
HAS_NUM = re.compile(r"\d")


def inverted(claims):
    """🔴🔴🔴 **자를 뒤집는다** --- 분모를 «문서»가 정한다."""
    t = (ROOT / D).read_text(encoding="utf-8") if (ROOT / D).is_file() else None
    if t is None:
        return collections.OrderedDict([
            ("🔴", "🔴 판정문이 아직 없다 --- 「등록 안 된 문장 0」이 아니라 「모른다」다"),
            ("통과", bool(t)),
        ])
    body = t.split("\n")
    sents = [ln.strip() for ln in body
             if CLAIM_SENT.fullmatch(ln.strip() or "\0") and HAS_NUM.search(ln)]
    reg = [c["문장"] for c in claims]
    #: 등록됐나 --- 등록 문장의 «특징 조각»(굵은 부분)이 그 줄에 있나
    def _covered(ln):
        for r in reg:
            core = re.findall(r"«([^»]+)»|`([^`]+)`", r)
            keys = [a or b for a, b in core] or [r[:12]]
            if any(k and k in ln for k in keys):
                return True
        return False
    covered = [s for s in sents if _covered(s)]
    uncovered = [s for s in sents if not _covered(s)]
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴🔴 **판정문의 «주장 문장» 중 «등록 안 된» 것이 몇인가** --- "
                 "분모를 문서가 정한다(티처 #124 즉시정정 ⑤)"),
        ("🔴 「주장 문장」의 정의(측정 전에 박았다)",
         "굵은 조각(`**…**`)을 담고 숫자가 있는 줄"),
        ("🔴🔴 분모: 판정문의 주장 문장 수", len(sents)),
        ("🔴 등록된 주장 수", len(reg)),
        ("🔴🔴 등록에 «덮인» 주장 문장 수", len(covered)),
        ("🔴🔴🔴 등록 안 된 주장 문장 수", len(uncovered)),
        ("🔴🔴🔴 덮은 비율", round(float(len(covered)) / len(sents), 4) if sents else None),
        ("🔴 등록 안 된 주장 문장(앞 20)", uncovered[:20] or "없음"),
        ("🔴🔴 그래서 「산문 8/8」이 뜻하는 것",
         "🔴 **「등록한 것이 전부 맞았다」이지 「문서에 거짓이 없다」가 아니다.** "
         "985 는 이 분모를 «안 냈다» --- 등록 문장을 판정문 생성기에 넣어 닫았다"),
        ("⚠ 이 자의 한계(조항 61)",
         "🔴 **「주장 문장」의 정의는 여전히 사람이 골랐다.** 굵은 표시가 없는 주장은 "
         "원리상 안 보인다. 🔴 그래도 «분모를 자가 정하지 않는다»는 점에서 구판보다 낫다"),
        ("통과", bool(sents)),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **분모를 «냈는가»** 하나다 --- 덮은 비율이 낮은 것은 «불통과»가 아니라 "
         "«이 자가 잰 값»이다(조항 59)"),
    ])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    a = ap.parse_args()
    t0 = CY.now()
    CY.begin(a.ref)
    cs0 = CY.code_stamp()
    res = check(CLAIMS, stdout=False)
    out = collections.OrderedDict()
    out["무엇"] = "986 산문 — 🔴 등록 대조 + 🔴🔴🔴 «뒤집은» 자"
    out["§A 🔴 등록 주장 대 산출물 키(985 판 자)"] = collections.OrderedDict(
        list(res.items()) + [
            ("🔴 주장 수(등록한 것만 본다 · 조항 61)", len(CLAIMS)),
            ("🔴 이 대조가 «못 보는» 것",
             "🔴 **등록 안 한 문장은 원리상 안 보인다** --- 그래서 §B 를 더했다"),
        ])
    out["§B 🔴🔴🔴 뒤집은 자 — 분모를 «문서»가 정한다(986 신설)"] = inverted(CLAIMS)
    out["통과"] = bool(out["§A 🔴 등록 주장 대 산출물 키(985 판 자)"].get("통과")
                     and out["§B 🔴🔴🔴 뒤집은 자 — 분모를 «문서»가 정한다(986 신설)"]["통과"])
    CY.write(OUT, out, a.ref, cs0, t0)
    print(json.dumps({"통과": out["통과"], "등록 주장": len(CLAIMS),
                      "등록 안 된 주장 문장":
                      out["§B 🔴🔴🔴 뒤집은 자 — 분모를 «문서»가 정한다(986 신설)"]
                      .get("🔴🔴🔴 등록 안 된 주장 문장 수")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
