#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""984 R2 — 🔴🔴 **`code_stamp` 분모를 「사이클 전체 러너 합집합」으로 통일한다**.

🔴 **왜 (티처 #122 3순위 ⓓ).** 983 은 산출물마다 `RAN` 을 따로 적어 도장 요약이
**여덟 갈래**였고 조항 66-② 신고가 **0** 이었다. 🔴 **더 나쁜 것**: 커밋 `d1877cee0`
(05:15)가 **측정 창(04:57–05:26) 한가운데서 러너 다섯을 고쳤는데** 그 산출물들의
`code_stamp` 분모가 **그 파일들을 안 덮어** 「시작=끝 true」가 나왔다 ---
**가드가 자기가 잡아야 할 위반에 눈이 멀었다.**

그래서 이 모듈이 **한 곳**에서
① `RAN_ALL`(이 사이클이 돌리거나 읽는 러너 전량) 과
② `DATA`(자료 지문) 를 들고,
③ **조항 66-② 신고**(측정 창 안에 바뀐 러너)를 **모든 산출물이 싣게** 한다.

🔴 **이 모듈은 값을 안 만든다.** 명부와 신고만 만든다 --- 그래야 명부가 결과의 함수가
안 된다(`docs/루프.md` 3. 「통제 집합이 결과의 함수다」).
"""
import datetime as dt
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import ledger as LG                                   # noqa: E402

#: 🔴🔴🔴 **사이클 전체 러너 합집합.** 984 의 모든 산출물이 이 하나를 쓴다.
#:  ㉠ 984 가 «돌리는» 러너 · ㉡ 984 가 «값을 읽는» 983 러너(조항 66-① 잰 소스) ·
#:  ㉢ 그 둘이 import 하는 실험실 러너.
#: 🔴 `lab/*.py` 는 `LG.code_stamp` 가 언제나 덧붙인다(그 함수의 문언).
RAN_ALL = (
    # ㉠ 984 가 돌린다
    "runners/cycle984.py",
    "runners/house984.py",
    "runners/leak984.py",
    "runners/regrid984.py",
    "runners/score984.py",
    "runners/note984_gen.py",
    "runners/prose984.py",
    "runners/fiveprime902.py",
    # ㉡ 984 가 값을 읽는다 --- 🔴 조항 66-① 「잰 소스의 sha 를 산출물에 박는다」
    "runners/stat983.py",
    "runners/tgrid983.py",
    "runners/score983.py",
    "runners/note983_gen.py",
    "runners/house983.py",
    "runners/holdout983.py",
    "runners/prose983.py",
    # ㉢ 그 둘이 import 한다
    "runners/ledger.py",
    "runners/alpha977.py",
    "runners/ruler979.py",
    "runners/mix980.py",
    "runners/predict971.py",
    "runners/plumb979.py",
)

#: 자료 지문 --- 규칙 C 「자료 파일을 분모에 넣어라」(티처 #110 중-14)
DATA = dict(LG.DATA) if isinstance(getattr(LG, "DATA", None), dict) else {}

#: 984 가 값을 읽는 산출물 --- 🔴 **새 학습 0** 임을 이 목록이 증언한다
FEEDS_IN = (
    "runners/out983_grid.json",
    "runners/out983_reps.json",
    "runners/out983_stat.json",
    "runners/out981_target.json",
    "runners/out981_decomp.json",
)


def now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha_file(rel):
    p = ROOT / rel
    if not p.is_file():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()


def code_stamp():
    """🔴 **분모는 언제나 `RAN_ALL`** --- 러너마다 다른 `RAN` 을 쓰지 않는다."""
    return LG.code_stamp(RAN_ALL)


def clause66_2(cs0, cs1):
    """🔴🔴 **조항 66-② 신고** --- 측정 창 «안»에 바뀐 러너를 이름으로 낸다.

    「시작=끝 true」만 적으면 **분모가 그 파일을 안 덮을 때** 아무 말도 못 한다
    (983 이 정확히 그렇게 놓쳤다). 여기서는 **분모 자체**와 **갈린 파일 이름**을
    같이 낸다 --- 조항 59: 「안 걸렸다」와 「못 걸린다」는 둘이다.
    """
    keys = sorted(set(cs0) | set(cs1))
    moved = [k for k in keys if cs0.get(k) != cs1.get(k)]
    missing = [r for r in RAN_ALL if r not in cs1]
    return {
        "🔴🔴 조항 66-② 신고": "측정 창 안에서 러너를 고쳤나",
        "🔴 분모: `code_stamp` 가 덮는 파일 수": len(cs1),
        "🔴 분모: `RAN_ALL` 러너 수": len(RAN_ALL),
        "🔴🔴 분모가 못 덮은 `RAN_ALL` 항목(= 「없다」가 아니다 · 조항 59)":
            missing or "없음",
        "🔴🔴🔴 측정 창 안에 바뀐 파일": moved or "없음",
        "🔴🔴🔴 측정 창 안에 러너를 고쳤나": bool(moved),
        "🔴 시작 요약": hashlib.sha256(
            json.dumps(cs0, sort_keys=True).encode()).hexdigest(),
        "🔴 끝 요약": hashlib.sha256(
            json.dumps(cs1, sort_keys=True).encode()).hexdigest(),
        "⚠ 983 이 어떻게 놓쳤나": (
            "🔴 `d1877cee0`(05:15)가 측정 창(04:57–05:26) 한가운데서 러너 다섯을 고쳤는데 "
            "그 산출물의 `code_stamp` 분모가 **그 파일들을 안 덮어** 「시작=끝 true」가 "
            "나왔다. **가드가 자기가 잡아야 할 위반에 눈이 멀었다**(티처 #122 M9)"),
    }


def feeds_in():
    """🔴 984 가 «읽는» 산출물의 sha --- 새 학습이 0 임을 이 표가 증언한다."""
    return {p: _sha_file(p) for p in FEEDS_IN}


#: 🔴🔴 `⑤′` 절 3 「판정 키 규약」이 **절**로 세는 것 --- 최상위 dict 중
#: 키에 `sha256`·`시각` 이 안 든 것 전부(`fiveprime902.keyaudit:940-943`).
#: 🔴 983 의 산출물 아홉은 그 규약을 **한 절도** 안 지켜 절 38 중 34 가 「모른다」였다.
def seal_sections(obj):
    """🔴 **모든 절에 `통과` 키가 있게 한다**(`⑤′` 절 3 · `docs/루프.md:256-258`).

    🔴 **리터럴 `True` 를 심지 않는다.** 절이 이미 `통과` 를 가지면 안 건드리고,
    없으면 그 절이 «잰 값»에서 만든다 --- 도장은 `🔴 F5 통과`, 조항 66-② 는
    「측정 창 안에 러너를 고쳤나」의 **부정**. 그 둘 밖의 절이 `통과` 없이 오면
    **`False` 를 넣고 왜 못 재는지 적는다**(조항 59: 「모른다」는 「통과」가 아니다).
    """
    for k, v in list(obj.items()):
        if not isinstance(v, dict):
            continue
        if "sha256" in k or "시각" in k:
            continue
        if "통과" in v:
            continue
        if "🔴 F5 통과" in v:
            v["통과"] = bool(v["🔴 F5 통과"])
            v["🔴 이 절의 `통과`"] = "도장의 `🔴 F5 통과` 그 값이다(리터럴이 아니다)"
        elif "🔴🔴🔴 측정 창 안에 러너를 고쳤나" in v:
            _miss = [k2 for k2 in v if k2.startswith("🔴🔴 분모가 못 덮은")]
            v["통과"] = bool(not v["🔴🔴🔴 측정 창 안에 러너를 고쳤나"]
                            and _miss and v[_miss[0]] == "없음")
            v["🔴 이 절의 `통과`"] = (
                "🔴 **측정 창 안에 바뀐 러너가 0 이고 «분모가 `RAN_ALL` 을 전부 덮었을 때»만 "
                "참이다.** 983 은 뒤 조건이 거짓인 채로 앞만 보고 「시작=끝 true」를 실었다")
        else:
            v["통과"] = False
            v["🔴 이 절의 `통과`"] = (
                "🔴 **이 절은 `통과` 를 안 만들었다 --- 「모른다」다**(조항 59). "
                "`False` 로 센다. 「검사할 게 없다」가 아니다")
    return obj


def write(path, obj, ref, cs0, t0):
    """🔴 도장 + 조항 66-② 신고를 **같이** 붙여 쓴다(도장 없이 쓰는 길을 없앤다)."""
    cs1 = code_stamp()
    obj["🔴🔴 조항 66-② (984 R2)"] = clause66_2(cs0, cs1)
    obj["🔴 984 가 읽은 산출물 sha256"] = feeds_in()
    LG.write_stamped(str(ROOT / path), obj, ref, cs0, t0, RAN_ALL, DATA)
    #: 🔴 `write_stamped` 가 도장을 얹은 «뒤»에 절을 봉한다 --- 도장 자신도 절이다
    raw = json.loads((ROOT / path).read_text(encoding="utf-8"),
                     object_pairs_hook=__import__("collections").OrderedDict)
    seal_sections(raw)
    (ROOT / path).write_text(
        json.dumps(raw, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return raw


if __name__ == "__main__":
    cs = code_stamp()
    print(json.dumps({
        "RAN_ALL": len(RAN_ALL),
        "code_stamp 분모": len(cs),
        "못 덮은 항목": [r for r in RAN_ALL if r not in cs],
    }, ensure_ascii=False))
