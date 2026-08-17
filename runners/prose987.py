#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""🔴 노트 987 의 **산문 주장 = 산출물 키** 등록부 · 🔴🔴🔴 **그 자를 «뒤집는다»**.

🔴 **왜 뒤집나 (티처 #124 즉시정정 ⑤).** 985 의 「산문 8/8」은 **등록 문장을 판정문
생성기에 넣어** 닫았다 --- 곧 **분모를 자기가 정했다.** 그러면 「전부 초록」은
**「등록한 것만 봤다」**의 다른 말이다.

**986 이 더하는 자(§B)**: 🔴 **판정문의 «주장 문장» 전량을 분모로 두고,
그중 «등록되지 않은» 것이 몇인지를 센다.** 분모를 문서가 정하지 자가 정하지 않는다.

조항 61: 이 자도 한계가 있다 --- 「주장 문장」의 정의(굵은 조각 + 숫자)는 여전히
사람이 고른 것이다. **그 정의를 여기 박고 산출물에 싣는다.**

    python3 runners/prose987.py --ref <40자 sha>
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
import cycle987 as CY                                            # noqa: E402

OUT = "runners/out987_prose.json"

D = "docs/판정_987.md"
PR = "docs/pr_987.md"
AU = "runners/out987_audit.json"
PW = "runners/out987_power.json"
HS = "runners/out987_house.json"
CE = "runners/out987_certify.json"



SA = "§A 🔴🔴🔴 「전」을 고정 ref 로 다시 잰다"
SB = "§B 🔴🔴🔴 985 가 한 이름으로 두 범위를 쟀다"
SC = "§C 🔴🔴 `⑤′` 절 3 을 고정 명부로 다시 낸다"
P1 = "§1 🔴🔴🔴 천장은 항등식이다 — `P(¬㉰ 선다)`"
P2 = "§2 🔴🔴🔴 팔을 다시 짓는다 — V0 · V1 · V1′ · V2"
P4 = "§4 🔴🔴 983 모양 자 — 구간으로 · 확정 / 미확정"
HC = "§0-가 🔴🔴 집을 닫았나"
CN = "§나 🔴🔴 검정력 시연 — 같은 일곱 칸 자를 986 에 문다(조항 64)"
CL = "§라 🔴🔴 자기 입력 교란"

CLAIMS: list = [
    # ── 가 · 천장은 항등식이다 ─────────────────────────────────
    {"문서": D, "산출물": PW, "키": [P2, "🔴🔴🔴 항등식 검사(V0 의 발화 수가 상한을 넘나)",
                               "u=0", "🔴🔴🔴 모든 δ 에서 `발화 수 ≤ 상한` 인가"],
     "기대": True,
     "문장": "V0 의 발화 수는 «모든» δ 에서 항등식 상한을 «안» 넘는다"},
    {"문서": D, "산출물": PW, "키": [P2, "🔴🔴🔴 항등식 검사(V0 의 발화 수가 상한을 넘나)",
                               "u=3", "🔴🔴 상한에 «닿았나»(여유 ≤ 1)"],
     "기대": False,
     "문장": "`u=3` 은 격자 최대 δ 에서도 상한에 «안 닿았다» --- 아직 오르는 중이다"},
    {"문서": D, "산출물": PW, "키": [P2, "🔴🔴🔴 변이체별", "V1", "u=0",
                               "🔴 δ>0 에서 발화율이 «상수»인가(= 자가 δ 를 안 탄다)"],
     "기대": True,
     "문장": "사전등록 원안 V1 은 δ 를 «전혀» 안 탄다 --- 척도 불변이라 대수적으로 소거된다"},
    # ── 나 · 「전」을 고정 ref 로 ───────────────────────────────
    {"문서": D, "산출물": AU, "키": [SA, "🔴🔴🔴 986 이 실은 값이 틀렸나"], "기대": True,
     "문장": "986 이 「986 이 넣기 전 실측」이라 실은 값은 «틀렸다»"},
    # ── 다 · 한 이름 두 값 ────────────────────────────────────
    {"문서": D, "산출물": AU, "키": [SB, "🔴🔴🔴 그 반박이 참인가", "🔴🔴🔴 986 의 반박이 «거짓»인가"],
     "기대": True,
     "문장": "「티처의 `446/349` 는 985 산출물에 없다」는 986 의 반박은 «거짓»이다"},
    {"문서": D, "산출물": AU, "키": [SB, "🔴🔴🔴 진짜 병 — 같은 이름 · 다른 범위", "🔴🔴🔴 범위가 다른가"],
     "기대": True,
     "문장": "985 는 «같은 이름»으로 서로 다른 두 «범위»를 쟀다"},
    # ── 라 · ⑤′ 절 3 ─────────────────────────────────────────
    {"문서": D, "산출물": AU, "키": [SC, "🔴🔴🔴 985 → 986 에서 대상이 줄었나"], "기대": True,
     "문장": "986 의 `⑤′` 절 3 초록은 «대상이 줄어» 생긴 것이다(조용한 좁힘)"},
    # ── 마 · 일곱째 칸 ────────────────────────────────────────
    {"문서": D, "산출물": CE, "키": [CN, "🔴🔴🔴 일곱째 칸이 986 에서 «떨어지나»"], "기대": True,
     "문장": "같은 «일곱째 칸» 자를 986 에 물리면 «떨어진다»"},
    {"문서": D, "산출물": CE, "키": [CL, "🔴🔴🔴 가짜 판에서 «떨어지나»"], "기대": True,
     "문장": "자기 입력을 한 글자 교란하면 자가 떨어진다"},
    # ── 바 · 집 ──────────────────────────────────────────────
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
    out["무엇"] = "987 산문 — 🔴 등록 대조 + 🔴🔴🔴 «뒤집은» 자"
    out["§A 🔴 등록 주장 대 산출물 키"] = collections.OrderedDict(
        list(res.items()) + [
            ("🔴 주장 수(등록한 것만 본다 · 조항 61)", len(CLAIMS)),
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
