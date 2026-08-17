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


#: 🔴🔴🔴 **985 R5 (티처 #123 3순위 ③)** --- **조항 66-② 의 창을 「사이클 단위」로 넓힌다.**
#:
#: 🔴 **왜.** 984 판의 창은 한 러너의 `t0` ~ `write()` 사이라 **0~1 초**였다. 그러면
#: **단계와 단계 «사이»의 수정은 원리상 못 잡는다** --- 984 자신의 러너도 `06:35 ~ 07:07`
#: 에 걸쳐 고쳐졌는데 모든 산출물이 「시작=끝 true」를 냈다. **가드가 자기가 잡아야 할
#: 위반에 눈이 멀었다**는 984 의 자기 진단이 984 자신에게도 그대로 걸린다.
#:
#: 🔴 **985 판**: 사이클 «첫 단계»가 `begin()` 으로 이 파일에 시작 도장을 박고,
#: **모든 산출물이 그 파일과 견준다.** 창 = **첫 단계 시작 ~ 마지막 단계 끝**.
WINDOW = "runners/out985_window.json"

#: 🔴🔴 **산출물 → 그것을 «낸» 러너.** 「값을 낸 뒤에 그 값을 내는 러너를 고치고
#: «안 다시 돌렸나»」를 이 표로 잰다(반증조건 5). 🔴 `RAN_ALL` 전량으로 재면
#: 984 러너를 한 줄만 고쳐도 985 의 모든 산출물이 낡은 것이 되어 **자가 못 쓰게 된다** ---
#: 그래서 **생산자 한 명 + 공용 배관 둘**(`SHARED`)만 본다.
SHARED = ("runners/cycle985.py", "runners/ledger.py")
PRODUCER = {
    "runners/out985_house.json": "runners/house985.py",
    "runners/out985_audit.json": "runners/audit985.py",
    "runners/out985_power.json": "runners/power985.py",
    "runners/out985_score.json": "runners/score985.py",
    "runners/out985_table.json": "runners/note985_gen.py",
    "runners/out985_certify.json": "runners/certify985.py",
    "runners/out985_prose.json": "runners/prose985.py",
}


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


def begin(ref, force=False):
    """🔴🔴 **사이클 창을 «연다»** --- 첫 단계가 한 번 부른다. 두 번째부터는 안 덮어쓴다."""
    p = ROOT / WINDOW
    if p.is_file() and not force:
        d0 = json.loads(p.read_text(encoding="utf-8"))
        #: 🔴 **키 이름만 옮긴다(값은 그대로다).** 창을 «다시 열면» 사이클 시작이 뒤로 밀려
        #:  자가 약해진다 --- 그래서 시작 시각과 시작 도장을 **한 바이트도 안 바꾸고**
        #:  키만 `sha256` 이 든 이름으로 옮긴다(`⑤′` 절 3 이 도장을 절로 안 세게).
        OLD, NEW = "🔴 시작 code_stamp", "🔴 시작 code_stamp(파일별 sha256)"
        if OLD in d0 and NEW not in d0:
            d0[NEW] = d0.pop(OLD)
            d0["⚠ 985 R5 --- 키 이름을 사이클 도중에 옮겼다(값은 그대로다)"] = (
                "🔴 `%s` → `%s`. **시작 시각도 시작 도장의 값도 안 바꿨다** --- "
                "`⑤′` 절 3 이 `sha256`·`시각` 이 든 키를 «도장»으로 세기 때문이다. "
                "🔴 조항 66-③: 자를 바꾸면 전후를 같이 적는다" % (OLD, NEW))
            p.write_text(json.dumps(d0, ensure_ascii=False, indent=1) + "\n",
                         encoding="utf-8")
        return d0
    d = {
        "무엇": "🔴🔴🔴 985 R5 --- **사이클 단위 측정 창**의 시작 도장",
        "🔴 왜": ("984 판 창은 한 러너의 `t0`~`write()` 사이라 **0~1 초**였다. "
                "단계와 단계 «사이»의 수정은 원리상 못 잡는다 --- 984 자신의 러너도 "
                "`06:35~07:07` 에 걸쳐 고쳐졌는데 모든 산출물이 「시작=끝 true」를 냈다"),
        "🔴 사이클 시작(UTC)": now(),
        "🔴 기준 ref": ref,
        #: 🔴 키에 `sha256` 을 넣는 것은 «도장»임을 밝히는 것이다 --- `⑤′` 절 3 은
        #:  `sha256`·`시각` 이 든 키를 **절이 아니라 도장**으로 센다(그 자의 문언).
        "🔴 시작 code_stamp(파일별 sha256)": code_stamp(),
    }
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return d


def cycle_start():
    """🔴 사이클 시작 도장을 읽는다. 없으면 **「모른다」**를 낸다(0 이 아니다 · 조항 59)."""
    p = ROOT / WINDOW
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def stale_outputs():
    """🔴🔴 **「값을 낸 뒤에 그 값을 내는 러너를 고치고 «안 다시 돌렸나»」**를 잰다.

    산출물의 도장에 박힌 **그 생산자의 디스크 sha256** 과 **지금 디스크의 sha256** 을
    견준다. 다르면 **그 산출물은 지금 코드가 낸 값이 아니다.**
    🔴 「없다」와 「못 읽었다」를 가른다(조항 59).
    """
    rows, stale, unread = {}, [], []
    for out, prod in sorted(PRODUCER.items()):
        q = ROOT / out
        if not q.is_file():
            rows[out] = {"🔴": "🔴 산출물이 아직 없다(= 「낡지 않았다」가 아니다)"}
            continue
        try:
            d = json.loads(q.read_text(encoding="utf-8"))
        except Exception as e:                                     # noqa: BLE001
            rows[out] = {"🔴": "🔴 못 읽었다: %s" % e}
            unread.append(out)
            continue
        st = d.get(LG.STAMP_KEY) or {}
        per_r = st.get("러너별") or {}
        watch = [prod] + [x for x in SHARED if x != prod]
        cells, miss, moved = {}, [], []
        for w in watch:
            was = (per_r.get(w) or {}).get("디스크 sha256")
            cur = _sha_file(w)
            if was is None:
                miss.append(w)
                continue
            cells[w] = {"낼 때 sha256": was, "지금 sha256": cur, "같은가": bool(was == cur)}
            if was != cur:
                moved.append(w)
        rows[out] = {"생산자": prod, "🔴 같이 보는 공용 배관": list(SHARED),
                     "🔴 파일별": cells,
                     "🔴 도장에 없어 못 본 것(= 「안 바뀌었다」가 아니다)": miss or "없음",
                     "🔴🔴 낼 때와 달라진 파일": moved or "없음"}
        if miss:
            unread.append(out)
        if moved:
            stale.append(out)
    return {
        "🔴🔴 무엇": ("🔴 **값을 낸 뒤에 그 값을 내는 러너를 고치고 «안 다시 돌린» 산출물** --- "
                  "조항 66-② 를 「창」이 아니라 «상태»로 잰다. 창은 넓혀도 「고친 뒤 다시 "
                  "돌렸나」를 못 묻는데, 이 자는 그것을 직접 묻는다"),
        "🔴 분모: 생산자 표에 든 산출물": len(PRODUCER),
        "🔴 산출물별": rows,
        "🔴🔴🔴 낡은 산출물(고치고 안 다시 돌렸다)": stale or "없음",
        "🔴 못 읽은 것(= 「없다」가 아니다)": unread or "없음",
        "🔴🔴🔴 낡은 것이 있나": bool(stale),
    }


def clause66_2(cs0, cs1):
    """🔴🔴 **조항 66-② 신고** --- 🔴 **985 R5: 창을 「사이클 단위」로 넓혔다.**

    `cs0` 는 이 러너의 `t0` 도장이지만, **판정에 쓰는 것은 «사이클 시작» 도장**이다
    (`out985_window.json`). 둘을 **나란히** 싣는다 --- 좁은 창이 무엇을 놓치는지가
    그 차이에 그대로 보인다(조항 66-③: 자를 바꾸면 전후를 같이 싣는다).
    """
    keys = sorted(set(cs0) | set(cs1))
    moved_narrow = [k for k in keys if cs0.get(k) != cs1.get(k)]
    missing = [r for r in RAN_ALL if r not in cs1]
    win = cycle_start()
    #: 🔴 **키를 사이클 도중에 고쳤다**(`⑤′` 절 3 이 도장을 절로 세지 않게) --- 그래서
    #:  **옛 키도 읽는다.** 창을 다시 열면 「사이클 시작」이 뒤로 밀려 자가 약해지므로
    #:  파일을 안 갈아엎고 읽는 쪽에서 받는다. 🔴 이 사실을 여기 적어 둔다(조항 66-③).
    csw = ((win or {}).get("🔴 시작 code_stamp(파일별 sha256)")
           or (win or {}).get("🔴 시작 code_stamp") or {})
    if win is None:
        moved_wide, wide_known = None, False
    else:
        wide_known = True
        moved_wide = [k for k in sorted(set(csw) | set(cs1))
                      if csw.get(k) != cs1.get(k)]
    return {
        "🔴🔴 조항 66-② 신고": "🔴 **985 R5 --- 창은 「사이클 단위」다**(첫 단계 시작 ~ 지금)",
        "🔴 분모: `code_stamp` 가 덮는 파일 수": len(cs1),
        "🔴 분모: `RAN_ALL` 러너 수": len(RAN_ALL),
        "🔴🔴 분모가 못 덮은 `RAN_ALL` 항목(= 「없다」가 아니다 · 조항 59)":
            missing or "없음",
        "🔴 사이클 시작(UTC)": (win or {}).get("🔴 사이클 시작(UTC)")
        or "🔴 모른다 --- `out985_window.json` 이 없다(0 이 아니다)",
        "⚠ 좁은 창(984 판 · 이 러너의 t0~지금)에서 바뀐 파일": moved_narrow or "없음",
        "🔴🔴🔴 넓은 창(985 판 · 사이클 시작~지금)에서 바뀐 파일":
            (moved_wide or "없음") if wide_known else
            "🔴 모른다 --- 사이클 시작 도장이 없다",
        "🔴🔴🔴 측정 창 안에 러너를 고쳤나": (bool(moved_wide) if wide_known else None),
        "🔴🔴 좁은 창이 놓친 파일 수(= 984 판이 못 본 것)":
            (len(set(moved_wide or []) - set(moved_narrow)) if wide_known else None),
        "🔴🔴🔴 값을 낸 뒤 고치고 «안 다시 돌린» 산출물": stale_outputs(),
        "🔴 시작 요약(좁은 창)": hashlib.sha256(
            json.dumps(cs0, sort_keys=True).encode()).hexdigest(),
        "🔴 시작 요약(넓은 창)": hashlib.sha256(
            json.dumps(csw, sort_keys=True).encode()).hexdigest() if wide_known
        else "🔴 모른다",
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
            _known = v["🔴🔴🔴 측정 창 안에 러너를 고쳤나"] is not None
            _stale = (v.get("🔴🔴🔴 값을 낸 뒤 고치고 «안 다시 돌린» 산출물")
                      or {}).get("🔴🔴🔴 낡은 것이 있나")
            v["통과"] = bool(_known and _stale is False
                            and _miss and v[_miss[0]] == "없음")
            v["🔴 이 절의 `통과`"] = (
                "🔴🔴 **985 R5 --- `통과` 는 「창 안에 아무것도 안 고쳤나」가 아니라 "
                "「고친 러너를 «다시 돌렸나»」다.** 사이클 창은 몇 시간이라 러너 수정은 "
                "정상이고, 위반은 **고치고 안 다시 돌린 것**이다. 조건 셋: "
                "① 사이클 시작 도장을 읽었다(「모른다」가 아니다) · "
                "② 낡은 산출물 0 · ③ 분모가 `RAN_ALL` 을 전부 덮었다")
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
    KEY = "🔴🔴🔴 985 R4 봉인 감사(무엇을 봉했고 무엇을 뺐나)"
    raw[KEY] = audit
    #: 🔴🔴 **이 절 자신도 절이다** --- 리터럴 `True` 를 안 넣는다.
    #:  봉인 «뒤»에도 `통과` 가 없는 최상위 절이 남았나를 **세어** 판정한다.
    left = [k for k, v in raw.items()
            if isinstance(v, dict) and "통과" not in v and k != KEY
            and k not in seal_skip and not any(w in k for w in ("sha256", "시각"))]
    audit["🔴🔴 봉인 뒤에도 `통과` 가 없는 절(= `⑤′` 절 3 이 「모른다」로 셀 자리)"] = \
        left or "없음"
    audit["통과"] = bool(not left)
    audit["🔴 이 절의 `통과`"] = (
        "🔴 **봉인 뒤에 `통과` 키가 없는 최상위 절이 0 인가** --- 봉인 제외 키와 "
        "도장(`sha256`·`시각`)은 절이 아니라 세지 않는다. 🔴 이 자는 떨어질 수 있다")
    (ROOT / path).write_text(
        json.dumps(raw, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return raw


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--begin":
        print(json.dumps(begin(sys.argv[2],
                               force=("--force" in sys.argv)),
                         ensure_ascii=False)[:400])
        sys.exit(0)
    cs = code_stamp()
    print(json.dumps({
        "RAN_ALL": len(RAN_ALL),
        "RAN_985": len(RAN_985),
        "code_stamp 분모": len(cs),
        "못 덮은 항목": [r for r in RAN_ALL if r not in cs],
        "봉인 제외 기본값": list(SEAL_SKIP_DEFAULT),
    }, ensure_ascii=False))
