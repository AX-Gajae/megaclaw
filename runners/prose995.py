#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""🔴 노트 995 의 **산문 주장 = 산출물 키** 등록부 (`⑤′` 절 8).

🔴🔴🔴 **`CLAIMS` 를 손으로 안 적는다.** `runners/out995_docsha.json` 의 «치환표»에서
«기계로» 만든다 --- 슬롯마다 「어느 산출물의 어느 키 경로가 어느 «줄»에 앉았나」가
이미 적혀 있으므로 **그것이 곧 주장이다**.

🔴 **못 만든 슬롯은 「없다」가 아니라 「못 만들었다」로 센다**(조항 59) --- `SKIPPED`.
  · 값이 목록/사전이면 형식본이 한 줄에 안 들어가므로 뺀다.
  · 값이 문서 «어느 줄에도» 안 보이면 **빼지 않고 «빈 문장»으로 등록해 «떨어뜨린다»** ---
    그게 「표를 고치고 문서를 안 다시 찍은」 자리를 잡는 유일한 길이다.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

DOCSHA = ROOT / "runners/out995_docsha.json"
DOC = "docs/판정_995.md"

CLAIMS = []
SKIPPED = []


def _fmt(v):
    return repr(v) if isinstance(v, float) else str(v)


def _build():
    if not DOCSHA.is_file():
        SKIPPED.append({"🔴": "도장이 없다 --- `note995_gen.py` 를 먼저 돌려라"})
        return
    d = json.loads(DOCSHA.read_text(encoding="utf-8"))
    body = (ROOT / DOC).read_text(encoding="utf-8")
    lines = body.split("\n")
    for slot, rec in (d.get("🔴 치환표") or {}).items():
        v, art = rec["값"], rec["파일"]
        key = list(rec["키 경로"])          # 🔴 목록이다(키에 " / " 가 들어서)
        if isinstance(v, bool):
            SKIPPED.append({"슬롯": slot, "🔴": "불리언은 문서에 「참/거짓」으로 찍혀 형식본이 안 맞는다"})
            continue
        if isinstance(v, (list, dict)) or v is None:
            SKIPPED.append({"슬롯": slot, "🔴": "값이 목록/사전이라 한 줄 형식본이 없다"})
            continue
        s = _fmt(v)
        hit = ""
        for ln in lines:
            if s in ln:
                hit = ln
                break
        if not hit:
            SKIPPED.append({"슬롯": slot, "🔴": "문서 어느 줄에도 안 보인다 --- 떨어뜨린다"})
        CLAIMS.append({"문서": DOC, "산출물": art, "키": key, "형식": "{}", "문장": hit})


_build()

if __name__ == "__main__":
    from runners.prose_check import check
    r = check(CLAIMS)
    sys.stdout.write("등록 %d · 못 만든 것 %d\n" % (len(CLAIMS), len(SKIPPED)))
