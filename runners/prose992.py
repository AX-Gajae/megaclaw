# -*- coding: utf-8 -*-
"""🔴 노트 992 의 **산문 주장 = 산출물 키** 등록부.

🔴🔴🔴 **989 와 다른 점** --- `CLAIMS` 를 **손으로 안 적는다.**
  `runners/out992_slots.json`(문서를 찍을 때 남긴 «슬롯 대장»)에서 «기계로» 만든다.
  각 슬롯은 이미 「어느 산출물의 어느 키 경로가 문서의 어느 «문자 자리»에 앉았나」이므로
  **그것이 곧 「산문 주장 = 산출물 키」다.**

🔴 **형식 문자열도 손으로 안 고른다** --- `ledger.render` 가 낸 «자릿수»에서 뽑는다.
🔴 **못 만든 슬롯은 「없다」가 아니라 「못 만들었다」로 센다**(`조항 59`) --- `SKIPPED`.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

SLOTS = ROOT / "runners/out992_slots.json"

CLAIMS = []
SKIPPED = []


def _line_of(text, pos):
    a = text.rfind("\n", 0, pos) + 1
    b = text.find("\n", pos)
    return text[a:(b if b >= 0 else len(text))]


def _fmt_for(v, shown):
    """🔴 `ledger.render` 가 낸 «자릿수»에서 형식을 «뽑는다». 손으로 안 고른다."""
    if isinstance(v, bool):
        return None                                # 불리언은 「기대」 갈래로 간다
    if isinstance(v, int):
        return "{:,}"
    if isinstance(v, float):
        d = len(shown.split(".")[1]) if "." in shown else 0
        return "{:.%df}" % d
    return None


def _build():
    if not SLOTS.is_file():
        SKIPPED.append({"🔴": "슬롯 대장이 없다 --- `note992_gen.py --stage docs` 를 먼저 돌려라"})
        return
    man = json.loads(SLOTS.read_text(encoding="utf-8"))
    for rel, info in (man.get("파일별") or {}).items():
        p = ROOT / rel
        if not p.is_file():
            SKIPPED.append({"문서": rel, "🔴": "문서가 없다"})
            continue
        text = p.read_text(encoding="utf-8")
        for sl in info["슬롯"]:
            path = sl["키 경로"]
            art = "runners/" + path[0]
            keys = path[1:]
            try:
                v = json.loads((ROOT / art).read_text(encoding="utf-8"))
                for k in keys:
                    v = v[k]
            except Exception:                                      # noqa: BLE001
                SKIPPED.append({"문서": rel, "슬롯": sl["슬롯"], "🔴": "키를 못 읽는다"})
                continue
            sentence = _line_of(text, sl["시작"]).strip()
            if not sentence:
                SKIPPED.append({"문서": rel, "슬롯": sl["슬롯"], "🔴": "줄이 비었다"})
                continue
            if isinstance(v, bool):
                CLAIMS.append({"문서": rel, "산출물": art, "키": keys,
                               "기대": v, "문장": sentence})
                continue
            f = _fmt_for(v, sl["값"])
            if f is None:
                SKIPPED.append({"문서": rel, "슬롯": sl["슬롯"],
                                "🔴": "형식을 못 뽑는다(값이 수·불리언이 아니다)",
                                "값 꼴": type(v).__name__})
                continue
            CLAIMS.append({"문서": rel, "산출물": art, "키": keys,
                           "형식": f, "문장": sentence})


_build()

#: 🔴 **분모를 숨기지 않는다**(`조항 59`).
META = {
    "🔴 등록한 주장 수": len(CLAIMS),
    "🔴 못 만든 슬롯 수": len(SKIPPED),
    "🔴 못 만든 까닭": SKIPPED,
    "🔴 출처": "runners/out992_slots.json --- 🔴 **손으로 안 적었다**",
}

if __name__ == "__main__":
    print(json.dumps(META, ensure_ascii=False, indent=1))
