#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""🔴 노트 988 의 **산문 주장 = 산출물 키** 등록부 · 🔴🔴🔴 **그 자를 «뒤집는다»**.

🔴 **즉시 정정(티처 #126)**: 987 의 덮은 비율은 986 의 **4.3 배**로 올랐는데
**등록 안 된 «절대수»는 42 → 74 로 늘었다** --- **판정문 길이가 분모를 키운다.**
🔴 **988 은 「주장 문장당 등록」을 목표로 등록 문장을 늘린다.**

    python3 runners/prose988.py --ref <40자 sha>
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
import cycle988 as CY                                            # noqa: E402

OUT = "runners/out988_prose.json"

D = "docs/판정_988.md"
AU = "runners/out988_audit.json"
HS = "runners/out988_house.json"
CE = "runners/out988_certify.json"

SA = "§A 🔴🔴🔴 987 의 최상위 통과를 등록 정의대로 다시 채점한다"
SB = "§B 🔴🔴🔴 여덟째 칸 — 등록 판정식 대조"
SC = "§C 🔴🔴 「자리 0」 감사"
SD = "§D 🔴🔴 늘린 한글 바늘을 987 문서에 문다"
SE = "§E 🔴🔴🔴 단조 불변(동어반복) 자"
SF = "§F 🔴 `⑤′` 수리 레인 파싱 — 구판 / 신판"
SG = "§G 🔴 `⑤′` §3 명부 — 데몬 셋(아는 red)"
SH = "§H 🔴 즉시 정정"
HC = "§0-가 🔴🔴 집을 닫았나"
CN = "§나 🔴🔴 검정력 시연 — 같은 여덟 칸 자를 987·986·985 에 문다(조항 64)"
CL = "§라 🔴🔴 자기 입력 교란"

CLAIMS: list = [
    # ── 가 · 987 의 최상위 통과는 거짓이다 ─────────────────────
    {"문서": D, "산출물": AU, "키": [SA, "🔴🔴🔴 등록 정의대로의 최상위 통과"], "기대": False,
     "문장": "987 의 «최상위 통과»는 등록한 판정식대로 재면 «거짓»이다"},
    {"문서": D, "산출물": AU, "키": [SA, "🔴🔴🔴 최상위 통과가 «뒤집히나»"], "기대": True,
     "문장": "«최상위 통과»가 뒤집힌다 --- 987 이 실은 값과 등록 정의대로의 값이 다르다"},
    {"문서": D, "산출물": AU, "키": [SA, "🔴 예측별",
                               "P6 고정 명부로 다시 계산하면 986 의 `⑤′` §3 초록이 뒤집힌다",
                               "🔴🔴 갈리나"], "기대": True,
     "문장": "«P6» 하나에서 채점기 값과 등록 정의대로의 값이 갈린다"},
    # ── 나 · 여덟째 칸 ────────────────────────────────────────
    {"문서": D, "산출물": AU, "키": [SB, "🔴🔴 988 자신에 문다(㉠ 엄격)",
                               "🔴🔴🔴 ㉠ 두 집합이 같은가"], "기대": True,
     "문장": "988 의 «사전등록 키 경로 집합»과 «선언표 키 경로 집합»이 같다"},
    # ── 다 · 「자리 0」 ────────────────────────────────────────
    {"문서": D, "산출물": AU, "키": [SC, "🔴 조건별", "987 §K 바늘 대조", "🔴🔴🔴 미측정인가"],
     "기대": True,
     "문장": "987 의 «§K 바늘 대조»는 「깨끗함」이 아니라 «미측정»이다"},
    # ── 라 · 동어반복 ────────────────────────────────────────
    {"문서": D, "산출물": AU, "키": [SE, "🔴 변이체별", "V1", "🔴🔴🔴 발화(= 동어반복이다)"],
     "기대": True,
     "문장": "«V1» 은 `h` 를 `h` 에 대해 검정한다 --- 단조 불변 자가 발화한다"},
    {"문서": D, "산출물": AU, "키": [SE, "🔴 변이체별", "V0", "🔴🔴🔴 발화(= 동어반복이다)"],
     "기대": False,
     "문장": "«V0» 에서는 단조 불변 자가 발화하지 않는다"},
    {"문서": D, "산출물": AU,
     "키": [SE, "🔴🔴🔴 심은 자에서 «갈리나»(단조는 발화 · 비단조는 «안» 발화)"], "기대": True,
     "문장": "«심은 자»에서 단조 짝은 발화하고 비단조 짝은 발화하지 않는다"},
    # ── 마 · 수리 레인 파싱 ───────────────────────────────────
    {"문서": D, "산출물": AU, "키": [SF, "🔴🔴🔴 구판이 987 에서 절을 찾았나"], "기대": False,
     "문장": "«구판» 정규식은 987 사전등록에서 수리 레인 절을 못 찾는다"},
    {"문서": D, "산출물": AU, "키": [SF, "🔴🔴🔴 신판이 987 에서 절을 찾았나"], "기대": True,
     "문장": "«신판» 정규식(절 이름)은 987 사전등록에서 그 절을 찾는다"},
    # ── 바 · 아는 red ────────────────────────────────────────
    {"문서": D, "산출물": AU, "키": [SG, "🔴🔴🔴 987 과 같은 목록인가"], "기대": True,
     "문장": "«데몬 셋» 중 §3 을 떨어뜨리는 파일 목록이 987 이 잰 것과 같다"},
    # ── 사 · 즉시 정정 ───────────────────────────────────────
    {"문서": D, "산출물": AU,
     "키": [SH, "① 🔴🔴 `u=3` 의 마지막 구간 기울기(987 표가 «안 실은» 더 강한 수)", "u=3",
           "🔴🔴 단조 비감소인가"], "기대": True,
     "문장": "«u=3» 은 마지막 구간에서 발화 수가 단조 비감소다(z 근거는 §H 에 있다)"},
    {"문서": D, "산출물": AU,
     "키": [SH, "② 🔴 「열린 PR 0」은 «측정 시각»의 값이다", "🔴🔴🔴 측정이 PR 생성보다 «먼저»였나"],
     "기대": True,
     "문장": "987 의 «열린 PR 0» 은 측정 시각의 값이고 PR 생성보다 먼저 쟀다"},
    # ── 아 · 여덟째 칸 검정력 · 집 ────────────────────────────
    {"문서": D, "산출물": CE, "키": [CN, "🔴🔴🔴 여덟째 칸이 987 에서 «떨어지나»"], "기대": True,
     "문장": "같은 «여덟째 칸» 자를 987 에 물리면 «떨어진다»"},
    {"문서": D, "산출물": CE, "키": [CL, "🔴🔴🔴 가짜 판에서 «떨어지나»"], "기대": True,
     "문장": "자기 입력을 한 글자 «교란»하면 자가 떨어진다"},
    {"문서": D, "산출물": HS,
     "키": [HC, "🔴🔴🔴 머지 뒤 규칙 A-2 가 참인가(= 같거나, 갈린 것이 등록한 것뿐)"],
     "기대": True, "문장": "규칙 «A-2» 가 참이다"},
]


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
        ("🔴 무엇", "🔴🔴🔴 **판정문의 «주장 문장» 중 «등록 안 된» 것이 몇인가**"),
        ("🔴 「주장 문장」의 정의(측정 전에 박았다)", "굵은 조각(`**…**`)을 담고 숫자가 있는 줄"),
        ("🔴🔴 분모: 판정문의 주장 문장 수", len(sents)),
        ("🔴 등록된 주장 수", len(reg)),
        ("🔴🔴 등록에 «덮인» 주장 문장 수", len(covered)),
        ("🔴🔴🔴 등록 안 된 주장 문장 수", len(uncovered)),
        ("🔴🔴🔴 덮은 비율", round(float(len(covered)) / len(sents), 4) if sents else None),
        ("🔴 등록 안 된 주장 문장(앞 20)", uncovered[:20] or "없음"),
        ("🔴🔴 즉시 정정(티처 #126) — 비율이 올라도 «절대수»가 늘 수 있다",
         "🔴 **986 은 등록 안 된 42 · 비율 0.0667 이고 987 은 74 · 0.2885 다** --- "
         "**비율은 4.3 배 개선인데 절대수는 76% 증가**다. "
         "🔴 **판정문 길이가 분모를 키운다** --- 「주장 문장당 등록」을 목표로 삼는다"),
        ("⚠ 이 자의 한계(조항 61)",
         "🔴 **「주장 문장」의 정의는 여전히 사람이 골랐다.** 굵은 표시가 없는 주장은 "
         "원리상 안 보인다"),
        ("통과", bool(sents)),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "🔴 **분모를 «냈는가»** 하나다"),
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
    out["무엇"] = "988 산문 — 🔴 등록 대조 + 🔴🔴🔴 «뒤집은» 자"
    out["§A 🔴 등록 주장 대 산출물 키"] = collections.OrderedDict(
        list(res.items()) + [
            ("🔴 주장 수(등록한 것만 본다 · 조항 61)", len(CLAIMS)),
            ("🔴 987 의 등록 주장 수", 10),
            ("🔴 이 대조가 «못 보는» 것",
             "🔴 **등록 안 한 문장은 원리상 안 보인다** --- 그래서 §B 를 더했다"),
        ])
    out["§B 🔴🔴 뒤집은 자 — 분모를 «문서»가 정한다"] = inverted(CLAIMS)
    out["통과"] = bool(out["§A 🔴 등록 주장 대 산출물 키"].get("통과")
                     and out["§B 🔴🔴 뒤집은 자 — 분모를 «문서»가 정한다"]["통과"])
    CY.write(OUT, out, a.ref, cs0, t0)
    print(json.dumps({"통과": out["통과"], "등록 주장": len(CLAIMS),
                      "등록 안 된 주장 문장":
                      out["§B 🔴🔴 뒤집은 자 — 분모를 «문서»가 정한다"]
                      .get("🔴🔴🔴 등록 안 된 주장 문장 수")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
