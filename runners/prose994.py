# -*- coding: utf-8 -*-
"""🔴 노트 994 의 **산문 주장 = 산출물 키** 등록부 (`⑤′` 절 8).

🔴🔴🔴 **`CLAIMS` 를 손으로 안 적는다.** `runners/out994_slots.json`(문서를 찍을 때
남긴 «슬롯 대장»)에서 «기계로» 만든다 --- 각 슬롯은 이미
「어느 키 경로가 어느 문서의 어느 «줄»에 앉았나」이므로 **그것이 곧 주장이다.**

🔴 **형식 문자열도 손으로 안 고른다** --- 생성기가 슬롯에 «찍을 때 쓴 형식»을 남긴다.
🔴 **못 만든 슬롯은 「없다」가 아니라 「못 만들었다」로 센다**(조항 59) --- `SKIPPED`.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

SLOTS = ROOT / "runners/out994_slots.json"
ART = "runners/out994_score.json"

CLAIMS = []
SKIPPED = []


def _build():
    if not SLOTS.is_file():
        SKIPPED.append({"🔴": "슬롯 대장이 없다 --- `note994_gen.py` 를 먼저 돌려라"})
        return
    man = json.loads(SLOTS.read_text(encoding="utf-8"))
    seen = set()
    for rel, info in (man.get("파일별") or {}).items():
        for sl in info["슬롯"]:
            key = (rel, tuple(sl["키 경로"]), sl["문자"])
            if key in seen:
                continue
            seen.add(key)
            if sl["갈래"] == "bool":
                CLAIMS.append({"문서": rel, "산출물": ART, "키": list(sl["키 경로"]),
                               "기대": sl["기대"], "문장": sl["문장"]})
            elif sl["형식"]:
                CLAIMS.append({"문서": rel, "산출물": ART, "키": list(sl["키 경로"]),
                               "형식": sl["형식"], "문장": sl["문장"]})
            else:
                SKIPPED.append({"문서": rel, "키 경로": sl["키 경로"],
                                "🔴": "형식을 못 뽑았다(수가 아닌 칸)"})


_build()

if __name__ == "__main__":
    from runners.prose_check import check
    r = check(CLAIMS)
    print("등록 %d · 못 만든 것 %d" % (len(CLAIMS), len(SKIPPED)))
