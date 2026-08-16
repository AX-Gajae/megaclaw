#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""985 R4 — 🔴🔴 **`seal_sections` 가 남의 dict(치환표)를 오염시키는 것을 끊는다**.

🔴 **왜 (티처 #123 1순위 ⓓ).** 984 의 `cycle984.seal_sections` 는 **최상위 dict 값 전부**를
「절」로 보고 `통과`·`🔴 이 절의 `통과`` 두 키를 **주입**했다. 그런데 `out984_table.json` 의
`🔴🔴 치환표` 도 최상위 dict 값이라 **표 자신이 오염됐다**:

| | 값 |
|---|---|
| 표가 스스로 적은 칸 수 | **166** |
| 디스크 파일의 실제 표 키 수 | 🔴 **168** |
| 문서가 인용한 표 sha | `eea591a4…` (= **165 키 판**의 해시) |
| 🔴 디스크 파일을 통째로 해시하는 검증자가 얻는 값 | `736db334…` |

🔴 **곧 도장이 «원리상» 재현 불가능했다** --- 아무도 그 sha 를 다시 만들 수 없다.

**985 판이 고치는 것 셋:**
1. 🔴 **봉인 대상을 「절 명부」로 좁힌다** --- `seal_skip` 으로 **봉인 «제외» 키를 명시**하고
   그 목록을 산출물에 싣는다. 조용히 빼지 않는다(조항 59·60).
2. 🔴 **주입한 자리를 전부 기록한다** --- 어느 절에 무엇을 넣었는지가 산출물에 남는다.
3. 🔴 **표 sha 는 「디스크에 실제로 쓰인 표」에서 계산한다** --- `note985_gen` 이 봉인 «뒤»에
   다시 읽어 해시하므로 **검증자가 같은 값을 얻는다**(`certify985.py` 가 그것을 잰다).
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

#: 🔴🔴🔴 **사이클 전체 러너 합집합.** 985 의 모든 산출물이 이 하나를 쓴다(984 R2 를 물려받는다).
#:  ㉠ 985 가 «돌리는» 러너 · ㉡ 985 가 «값을 읽는» 983·984 러너(조항 66-① 잰 소스) ·
#:  ㉢ 그 둘이 import 하는 실험실 러너.
RAN_ALL = (
    # ㉠ 985 가 돌린다
    "runners/cycle985.py",
    "runners/house985.py",
    "runners/audit985.py",
    "runners/power985.py",
    "runners/score985.py",
    "runners/note985_gen.py",
    "runners/certify985.py",
    "runners/prose985.py",
    "runners/fiveprime902.py",
    # ㉡ 985 가 값을 읽는다 --- 🔴 조항 66-① 「잰 소스의 sha 를 산출물에 박는다」
    "runners/cycle984.py",
    "runners/house984.py",
    "runners/leak984.py",
    "runners/regrid984.py",
    "runners/score984.py",
    "runners/note984_gen.py",
    "runners/stat983.py",
    "runners/tgrid983.py",
    "runners/house983.py",
    # ㉢ 그 둘이 import 한다
    "runners/ledger.py",
    "runners/alpha977.py",
    "runners/ruler979.py",
    "runners/mix980.py",
    "runners/predict971.py",
    "runners/plumb979.py",
)

#: 🔴🔴 **반증조건 12 의 분모** --- 985 가 «새로 쓴» 러너 전량.
#:  984 의 반증조건 12 는 `score984.py` **한 파일**만 훑어 984 가 새로 심은
#:  리터럴 `("통과", True)` **아홉**(`house984:135` · `leak984:282,318,443` ·
#:  `regrid984:175,222,256,321,371`)을 **원리상 못 봤다**(티처 #123 3순위 ⑤).
RAN_985 = (
    "runners/cycle985.py",
    "runners/house985.py",
    "runners/audit985.py",
    "runners/power985.py",
    "runners/score985.py",
    "runners/note985_gen.py",
    "runners/certify985.py",
    "runners/prose985.py",
)

#: 자료 지문 --- 규칙 C 「자료 파일을 분모에 넣어라」(티처 #110 중-14)
DATA = dict(LG.DATA) if isinstance(getattr(LG, "DATA", None), dict) else {}

#: 985 가 값을 읽는 산출물
FEEDS_IN = (
    "runners/out983_grid.json",
    "runners/out983_reps.json",
    "runners/out983_stat.json",
    "runners/out984_leak.json",
    "runners/out984_grid.json",
    "runners/out984_table.json",
    "runners/fiveprime_984_cert.json",
)

#: 🔴🔴🔴 **985 R4** --- **봉인에서 «제외»하는 최상위 키.**
#:  이 키의 값은 「절」이 아니라 **자료**다. 여기 넣지 않으면 `seal_sections` 가
#:  그 dict 에 `통과` 두 키를 주입해 **자기 칸 수와 자기 sha 를 거짓으로 만든다**(984 실측).
#:  🔴 **조용히 빼지 않는다** --- 제외 목록을 산출물에 싣는다(조항 59·60).
SEAL_SKIP_DEFAULT = ("🔴🔴 치환표",)


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
    """🔴🔴 **조항 66-② 신고** --- 측정 창 «안»에 바뀐 러너를 이름으로 낸다."""
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
    }


def feeds_in():
    """🔴 985 가 «읽는» 산출물의 sha."""
    return {p: _sha_file(p) for p in FEEDS_IN}


def seal_sections(obj, skip=SEAL_SKIP_DEFAULT):
    """🔴 **모든 «절»에 `통과` 키가 있게 한다**(`⑤′` 절 3 · `docs/루프.md`).

    🔴🔴 **985 R4 --- `skip` 에 든 최상위 키는 «절이 아니라 자료»라 안 건드린다.**
    984 는 이 구분이 없어 `🔴🔴 치환표` 에 두 키를 주입했고 **표가 자기 칸 수와 자기
    sha 를 거짓으로 만들었다.**

    🔴 **리터럴 `True` 를 심지 않는다.** 절이 이미 `통과` 를 가지면 안 건드리고,
    없으면 그 절이 «잰 값»에서 만든다. 그 둘 밖의 절이 `통과` 없이 오면
    **`False` 를 넣고 왜 못 재는지 적는다**(조항 59: 「모른다」는 「통과」가 아니다).

    돌려주는 값: **무엇을 봉인했고 무엇을 건너뛰었나**(산출물에 싣는다).
    """
    sealed, skipped, already = [], [], []
    for k, v in list(obj.items()):
        if not isinstance(v, dict):
            continue
        if k in skip:
            skipped.append(k)
            continue
        if "sha256" in k or "시각" in k:
            skipped.append(k)
            continue
        if "통과" in v:
            already.append(k)
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
                "참이다.**")
        else:
            v["통과"] = False
            v["🔴 이 절의 `통과`"] = (
                "🔴 **이 절은 `통과` 를 안 만들었다 --- 「모른다」다**(조항 59). "
                "`False` 로 센다. 「검사할 게 없다」가 아니다")
        sealed.append(k)
    return {
        "🔴🔴🔴 985 R4 봉인 감사": (
            "🔴 984 는 봉인 대상을 「최상위 dict 값 전부」로 잡아 **치환표 자신에 "
            "`통과` 두 키를 주입했다** --- 표가 스스로 「166」이라 적은 파일에 168 개가 "
            "들어 있었고, 문서가 인용한 표 sha 는 **165 키 판**의 것이라 "
            "**디스크 파일을 해시하는 검증자가 다른 값을 얻었다.** 🔴 도장이 원리상 "
            "재현 불가능했다"),
        "🔴 봉인한 절": sealed or "없음",
        "🔴 이미 `통과` 가 있어 안 건드린 절": already or "없음",
        "🔴🔴 봉인에서 «명시적으로» 뺀 키(= 절이 아니라 자료다)": skipped or "없음",
        "🔴 제외 목록(인자로 받은 것)": list(skip),
    }


def write(path, obj, ref, cs0, t0, seal_skip=SEAL_SKIP_DEFAULT):
    """🔴 도장 + 조항 66-② 신고를 **같이** 붙여 쓴다(도장 없이 쓰는 길을 없앤다)."""
    cs1 = code_stamp()
    obj["🔴🔴 조항 66-② (985 R5)"] = clause66_2(cs0, cs1)
    obj["🔴 985 가 읽은 산출물 sha256"] = feeds_in()
    LG.write_stamped(str(ROOT / path), obj, ref, cs0, t0, RAN_ALL, DATA)
    #: 🔴 `write_stamped` 가 도장을 얹은 «뒤»에 절을 봉한다 --- 도장 자신도 절이다
    import collections as _c
    raw = json.loads((ROOT / path).read_text(encoding="utf-8"),
                     object_pairs_hook=_c.OrderedDict)
    audit = seal_sections(raw, seal_skip)
    raw["🔴🔴🔴 985 R4 봉인 감사(무엇을 봉했고 무엇을 뺐나)"] = audit
    (ROOT / path).write_text(
        json.dumps(raw, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return raw


if __name__ == "__main__":
    cs = code_stamp()
    print(json.dumps({
        "RAN_ALL": len(RAN_ALL),
        "RAN_985": len(RAN_985),
        "code_stamp 분모": len(cs),
        "못 덮은 항목": [r for r in RAN_ALL if r not in cs],
        "봉인 제외 기본값": list(SEAL_SKIP_DEFAULT),
    }, ensure_ascii=False))
