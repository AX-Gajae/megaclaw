#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""986 배관 — 🔴🔴🔴 **채점기와 문서를 잇는 여섯째 칸의 «상수»가 여기 있다**.

🔴 **왜 (티처 #124 C1).** 985 의 다섯 문서가 「반증조건 **13/14**」를 실었는데 정본 채점
산출물 `out985_score.json` 은 「**14/14** · 반증된 조건 없음」이었다. `note985_gen` 이
`09:40:04` 에 표·문서를 찍고 `score985` 가 `09:40:06` 에 다시 돌았는데 **아무도 문서를
다시 안 찍었다.** 🔴 **985 의 어떤 자도 이것을 못 본다**:

| 자 | 무엇을 보나 | 왜 못 보나 |
|---|---|---|
| 규칙 D | 문서의 수 ⊆ 표의 칸 | 표가 **13/14** 를 들고 있으니 통과한다 |
| `certify985` | 표 ↔ 디스크 문서 | 둘 다 **13/14** 라 수렴 `true` |
| 반증조건 9 | 여섯 자리가 같은 수를 적나 | 바늘이 **세 수**뿐이다 |

🔴 **「표 ↔ 채점기」를 잇는 자가 없다.** 986 은 그 고리를 **상수 하나**로 만든다 ---
`SCORE_CELLS` 를 `note986_gen`(표를 채우는 쪽)과 `certify986`(표를 검사하는 쪽)이
**같이 읽는다**. 그러면 「표와 채점기 중 무엇이 늦었나」를 **원리상** 잡는다.

그리고 985 의 R5(`stale_outputs`)를 **문서로 확장한다**(`stale_docs`):
🔴 **「채점기를 다시 돌렸으면 문서를 반드시 다시 찍는다」**를 배선으로 만든다.
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

#: 🔴🔴🔴 **사이클 전체 러너 합집합.** 986 의 모든 산출물이 이 하나를 쓴다.
#:  ㉠ 986 이 «돌리는» 러너 · ㉡ 986 이 «값을 읽는» 983·984·985 러너(조항 66-① 잰 소스) ·
#:  ㉢ 그 둘이 import 하는 실험실 러너.
RAN_ALL = (
    # ㉠ 986 이 돌린다
    "runners/cycle986.py",
    "runners/house986.py",
    "runners/audit986.py",
    "runners/power986.py",
    "runners/score986.py",
    "runners/note986_gen.py",
    "runners/certify986.py",
    "runners/prose986.py",
    "runners/plumb986.py",
    "runners/fiveprime902.py",
    # ㉡ 986 이 값을 읽는다 --- 🔴 조항 66-① 「잰 소스의 sha 를 산출물에 박는다」
    "runners/cycle985.py",
    "runners/audit985.py",
    "runners/power985.py",
    "runners/score985.py",
    "runners/note985_gen.py",
    "runners/certify985.py",
    "runners/house985.py",
    "runners/stat983.py",
    "runners/tgrid983.py",
    # ㉢ 그 둘이 import 한다
    "runners/ledger.py",
    "runners/alpha977.py",
    "runners/mix980.py",
    "runners/harvest_daemon.py",
)

#: 🔴🔴 **반증조건 13·14 의 분모** --- 986 이 «새로 쓴» 러너 전량.
#:  🔴 **R3**: 985 의 손 전사 자는 **치환표 생성기 한 파일**만 훑어
#:  `audit985.py:170` 의 하드코딩 `= 3` 을 **원리상 못 봤다**. 986 은 이 분모로 잰다.
RAN_986 = (
    "runners/cycle986.py",
    "runners/house986.py",
    "runners/audit986.py",
    "runners/power986.py",
    "runners/score986.py",
    "runners/note986_gen.py",
    "runners/certify986.py",
    "runners/prose986.py",
    "runners/plumb986.py",
)

#: 자료 지문 --- 규칙 C 「자료 파일을 분모에 넣어라」(티처 #110 중-14)
DATA = dict(LG.DATA) if isinstance(getattr(LG, "DATA", None), dict) else {}

#: 986 이 값을 읽는 산출물
FEEDS_IN = (
    "runners/out983_grid.json",
    "runners/out983_reps.json",
    "runners/out983_stat.json",
    "runners/out985_score.json",
    "runners/out985_table.json",
    "runners/out985_audit.json",
    "runners/out985_power.json",
    "runners/out985_certify.json",
    "runners/fiveprime_985_cert.json",
)

#: 🔴🔴🔴 봉인에서 «제외»하는 최상위 키(985 R4 를 물려받는다).
SEAL_SKIP_DEFAULT = ("🔴🔴 치환표",)

WINDOW = "runners/out986_window.json"

#: 🔴🔴 **산출물 → 그것을 «낸» 러너**(985 R5).
SHARED = ("runners/cycle986.py", "runners/ledger.py")
PRODUCER = {
    "runners/out986_house.json": "runners/house986.py",
    "runners/out986_audit.json": "runners/audit986.py",
    "runners/out986_power.json": "runners/power986.py",
    "runners/out986_score.json": "runners/score986.py",
    "runners/out986_table.json": "runners/note986_gen.py",
    "runners/out986_certify.json": "runners/certify986.py",
    "runners/out986_prose.json": "runners/prose986.py",
}

# ══════════════════════════════════════════════════════════════════════
# 🔴🔴🔴 여섯째 칸의 상수 --- 사전등록 §2-1
# ══════════════════════════════════════════════════════════════════════
#: **치환표 칸 이름 → `out986_score.json` 안의 키 경로.**
#:
#: 🔴 **`note986_gen` 은 이 표로 칸을 «채우고», `certify986` 은 이 표로 디스크의 채점
#: 산출물에서 그 경로를 «다시 해석해» 표의 칸과 견준다.** 두 러너가 같은 상수를 읽으므로
#: **「표와 채점기 중 무엇이 늦었나」를 원리상 잡는다.**
#:
#: ⚠ **이 자의 한계(조항 61)**: 표에 «안 실린» 채점 칸은 못 본다. 그래서 이 표의 길이를
#: 분모로 싣는다(조항 60).
SCORE_CELLS = {
    "채.반증분자모": ["§6 🔴 반증조건", "🔴🔴 분자 / 분모"],
    "채.반증분모": ["§6 🔴 반증조건", "🔴 분모"],
    "채.반증된": ["§6 🔴 반증조건", "🔴🔴 반증된 조건"],
    "채.반증통과": ["§6 🔴 반증조건", "통과"],
    "채.예측분자모": ["§5 🔴 예측", "🔴🔴 분자 / 분모"],
    "채.예측분자": ["§5 🔴 예측", "🔴 분자"],
    "채.예측통과": ["§5 🔴 예측", "통과"],
    "채.규칙D표밖": ["§D 🔴 규칙 D 감사(분모 여섯)", "🔴🔴 표 밖 합"],
    "채.규칙D분모": ["§D 🔴 규칙 D 감사(분모 여섯)", "🔴🔴 채점 분모"],
    "채.규칙D통과": ["§D 🔴 규칙 D 감사(분모 여섯)", "통과"],
    "채.68근거없음": ["§68 🔴 조항 68 모양 주장 감사", "🔴🔴 근거 없는 모양 주장 수"],
    "채.68통과": ["§68 🔴 조항 68 모양 주장 감사", "통과"],
    "채.F5분모": ["§F5 🔴 인용 산출물 도장", "🔴 분모"],
    "채.F5통과": ["§F5 🔴 인용 산출물 도장", "통과"],
    "채.여섯자리": ["§9 🔴🔴 여섯 자리가 같은 수를 적나", "통과"],
    "채.최상위통과": ["통과"],
}

#: 🔴🔴🔴 **문서 → 그 문서를 «찍은» 생산기**(사전등록 §2-3).
#:  985 의 `stale_outputs` 는 **산출물**만 봤다. 986 은 **문서**를 본다.
DOC_PRODUCER = {
    "docs/판정_986.md": "runners/note986_gen.py",
    "docs/card_986.md": "runners/note986_gen.py",
    "docs/handoff_986.md": "runners/note986_gen.py",
    "docs/pr_986.md": "runners/note986_gen.py",
}

#: 🔴 문서가 「그때 읽은」 채점 산출물. 치환표가 이 셋의 **내용 지문**을 박고
#:  `stale_docs` 가 지금 디스크의 내용 지문과 견준다.
DOC_INPUTS = (
    "runners/out986_score.json",
    "runners/out986_audit.json",
    "runners/out986_power.json",
)

TABLE = "runners/out986_table.json"
#: 치환표가 「문서를 찍을 때 읽은 입력의 내용 지문」을 적는 자리
DOC_INPUT_KEY = "🔴🔴🔴 문서를 찍을 때 읽은 채점 산출물 내용 지문(986 신설)"

#: 🔴🔴 **내용 지문에서 «빼는» 최상위 키** --- 도장·창 신고는 «돌 때마다» 바뀌므로
#:  그것까지 지문에 넣으면 이 자는 **원리상 언제나 「낡았다」**를 낸다(= 항진명제의 반대).
#:  🔴 **빼는 것을 여기 명시하고 산출물에 싣는다**(조용히 빼지 않는다 · 조항 59·60).
DIGEST_SKIP = ("🔴 도장", "🔴🔴 조항 66-② (986)", "🔴 986 이 읽은 산출물 sha256",
               "🔴🔴🔴 986 봉인 감사(무엇을 봉했고 무엇을 뺐나)")


def content_digest(rel):
    """🔴🔴🔴 **채점 «내용»의 지문** --- 도장·시각을 뺀 sha256.

    🔴 **왜 파일 sha 가 아닌가.** 산출물은 돌 때마다 도장의 시각이 바뀌어 파일 sha 가
    반드시 달라진다. 그러면 「채점이 바뀌었나」를 물을 수 없다.
    🔴 **뺀 키를 `DIGEST_SKIP` 에 명시**하고 산출물에 싣는다(조항 60).
    """
    p = ROOT / rel
    if not p.is_file():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:                                              # noqa: BLE001
        return None
    if isinstance(d, dict):
        d = {k: v for k, v in d.items() if k not in DIGEST_SKIP}
    return hashlib.sha256(
        json.dumps(d, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha_file(rel):
    p = ROOT / rel
    if not p.is_file():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()


_sha_file = sha_file


def code_stamp():
    """🔴 **분모는 언제나 `RAN_ALL`** --- 러너마다 다른 `RAN` 을 쓰지 않는다."""
    return LG.code_stamp(RAN_ALL)


def begin(ref, force=False):
    """🔴🔴 **사이클 창을 «연다»** --- 첫 단계가 한 번 부른다. 두 번째부터는 안 덮어쓴다."""
    p = ROOT / WINDOW
    if p.is_file() and not force:
        return json.loads(p.read_text(encoding="utf-8"))
    d = {
        "무엇": "🔴🔴🔴 986 --- **사이클 단위 측정 창**의 시작 도장(985 R5 를 물려받는다)",
        "🔴 사이클 시작(UTC)": now(),
        "🔴 기준 ref": ref,
        "🔴 시작 code_stamp(파일별 sha256)": code_stamp(),
    }
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return d


def cycle_start():
    p = ROOT / WINDOW
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def stale_outputs():
    """🔴🔴 **「값을 낸 뒤에 그 값을 내는 러너를 고치고 «안 다시 돌렸나»」**(985 R5 그대로)."""
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
            cur = sha_file(w)
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
        "🔴🔴 무엇": "🔴 **값을 낸 뒤에 그 값을 내는 러너를 고치고 «안 다시 돌린» 산출물**",
        "🔴 분모: 생산자 표에 든 산출물": len(PRODUCER),
        "🔴 산출물별": rows,
        "🔴🔴🔴 낡은 산출물(고치고 안 다시 돌렸다)": stale or "없음",
        "🔴 못 읽은 것(= 「없다」가 아니다)": unread or "없음",
        "🔴🔴🔴 낡은 것이 있나": bool(stale),
    }


def stale_docs():
    """🔴🔴🔴 **986 신설 — 「채점기를 다시 돌렸으면 문서를 반드시 다시 찍는다」**.

    🔴 **왜 (티처 #124 C1).** 985 의 R5 는 **산출물**만 봤다. 그래서
    `score985` 가 표·문서 «뒤»에 다시 돌아 `13/14 → 14/14` 로 바뀌었는데
    **아무 자도 안 떨어졌다.**

    **자**: 치환표가 문서를 찍을 때 읽은 채점 산출물의 sha256 을 박고
    (`cycle986.DOC_INPUT_KEY`), 이 함수가 그것을 **지금 디스크의 sha256** 과 견준다.
    🔴 「없다」와 「못 읽었다」와 「다르다」를 셋으로 가른다(조항 59).

    ⚠ **문서 파일 자체의 mtime 은 «안» 본다** --- mtime 은 되돌릴 수 있고,
    `git` 이 안 지키는 값이다. 보는 것은 **내용의 sha256** 하나다.
    """
    tp = ROOT / TABLE
    if not tp.is_file():
        return {
            "🔴🔴 무엇": "🔴 **채점기를 다시 돌리고 문서를 안 다시 찍었나**",
            "🔴": "🔴 치환표가 아직 없다 --- 「안 낡았다」가 아니라 **「모른다」**다(조항 59)",
            "🔴🔴🔴 낡은 문서가 있나": None,
        }
    try:
        tb = json.loads(tp.read_text(encoding="utf-8"))
    except Exception as e:                                          # noqa: BLE001
        return {"🔴": "🔴 치환표를 못 읽었다: %s" % e, "🔴🔴🔴 낡은 문서가 있나": None}
    was = tb.get(DOC_INPUT_KEY) or {}
    rows, moved, miss = {}, [], []
    for rel in DOC_INPUTS:
        w = was.get(rel)
        cur = content_digest(rel)
        if w is None:
            miss.append(rel)
            rows[rel] = {"🔴": "🔴 치환표가 이 입력의 내용 지문을 안 박았다(= 「같다」가 아니다)"}
            continue
        rows[rel] = {"문서를 찍을 때 내용 지문": w, "지금 내용 지문": cur,
                     "같은가": bool(w == cur)}
        if w != cur:
            moved.append(rel)
    docs = {}
    for d, prod in sorted(DOC_PRODUCER.items()):
        p = ROOT / d
        docs[d] = {"생산기": prod, "있나": p.is_file(),
                   "지금 sha256": sha_file(d)}
    known = not miss
    return {
        "🔴🔴 무엇": ("🔴🔴🔴 **채점기를 다시 돌리고 문서(·PR 본문)를 안 다시 찍었나** --- "
                  "985 의 R5 를 «문서»로 확장한다(사전등록 §2-3)"),
        "🔴 분모: 문서가 읽는 채점 산출물": len(DOC_INPUTS),
        "🔴 분모: 이 표가 덮는 문서": len(DOC_PRODUCER),
        "🔴 내용 지문에서 뺀 키(조용히 빼지 않는다 · 조항 60)": list(DIGEST_SKIP),
        "🔴 입력별": rows,
        "🔴 문서별": docs,
        "🔴 치환표가 sha 를 안 박은 입력(= 「같다」가 아니다 · 조항 59)": miss or "없음",
        "🔴🔴🔴 문서를 찍은 뒤 달라진 채점 산출물": moved or "없음",
        "🔴🔴🔴 낡은 문서가 있나": (bool(moved) if known else None),
        "🔴 이 값이 `None` 이면": "🔴 **「낡지 않았다」가 아니라 「모른다」**다(조항 59)",
    }


def clause66_2(cs0, cs1):
    """🔴🔴 **조항 66-② 신고** --- 창은 「사이클 단위」다(985 R5) + 🔴 **문서 갈래**(986 신설)."""
    keys = sorted(set(cs0) | set(cs1))
    moved_narrow = [k for k in keys if cs0.get(k) != cs1.get(k)]
    missing = [r for r in RAN_ALL if r not in cs1]
    win = cycle_start()
    csw = (win or {}).get("🔴 시작 code_stamp(파일별 sha256)") or {}
    if win is None:
        moved_wide, wide_known = None, False
    else:
        wide_known = True
        moved_wide = [k for k in sorted(set(csw) | set(cs1)) if csw.get(k) != cs1.get(k)]
    return {
        "🔴🔴 조항 66-② 신고": "🔴 **창은 「사이클 단위」다**(첫 단계 시작 ~ 지금)",
        "🔴 분모: `code_stamp` 가 덮는 파일 수": len(cs1),
        "🔴 분모: `RAN_ALL` 러너 수": len(RAN_ALL),
        "🔴🔴 분모가 못 덮은 `RAN_ALL` 항목(= 「없다」가 아니다 · 조항 59)": missing or "없음",
        "🔴 사이클 시작(UTC)": (win or {}).get("🔴 사이클 시작(UTC)")
        or "🔴 모른다 --- `out986_window.json` 이 없다(0 이 아니다)",
        "⚠ 좁은 창(984 판 · 이 러너의 t0~지금)에서 바뀐 파일": moved_narrow or "없음",
        "🔴🔴🔴 넓은 창(사이클 시작~지금)에서 바뀐 파일":
            (moved_wide or "없음") if wide_known else "🔴 모른다 --- 사이클 시작 도장이 없다",
        "🔴🔴🔴 측정 창 안에 러너를 고쳤나": (bool(moved_wide) if wide_known else None),
        "🔴🔴 좁은 창이 놓친 파일 수(= 984 판이 못 본 것)":
            (len(set(moved_wide or []) - set(moved_narrow)) if wide_known else None),
        "🔴🔴🔴 값을 낸 뒤 고치고 «안 다시 돌린» 산출물": stale_outputs(),
        "🔴🔴🔴 채점기를 다시 돌리고 «안 다시 찍은» 문서(986 신설)": stale_docs(),
        "🔴 시작 요약(좁은 창)": hashlib.sha256(
            json.dumps(cs0, sort_keys=True).encode()).hexdigest(),
        "🔴 시작 요약(넓은 창)": hashlib.sha256(
            json.dumps(csw, sort_keys=True).encode()).hexdigest() if wide_known
        else "🔴 모른다",
        "🔴 끝 요약": hashlib.sha256(
            json.dumps(cs1, sort_keys=True).encode()).hexdigest(),
    }


def feeds_in():
    return {p: sha_file(p) for p in FEEDS_IN}


def seal_sections(obj, skip=SEAL_SKIP_DEFAULT):
    """🔴 **모든 «절»에 `통과` 키가 있게 한다**(985 R4 판 그대로 · 리터럴 `True` 를 안 심는다)."""
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
            _sdoc = (v.get("🔴🔴🔴 채점기를 다시 돌리고 «안 다시 찍은» 문서(986 신설)")
                     or {}).get("🔴🔴🔴 낡은 문서가 있나")
            v["통과"] = bool(_known and _stale is False and _sdoc is False
                            and _miss and v[_miss[0]] == "없음")
            v["🔴 이 절의 `통과`"] = (
                "🔴🔴 **986 --- 조건 넷**: ① 사이클 시작 도장을 읽었다 · "
                "② 낡은 산출물 0 · ③ **낡은 문서 0**(986 신설) · "
                "④ 분모가 `RAN_ALL` 을 전부 덮었다. "
                "🔴 ③ 이 `None`(모른다)이면 «통과가 아니다»(조항 59)")
        else:
            v["통과"] = False
            v["🔴 이 절의 `통과`"] = (
                "🔴 **이 절은 `통과` 를 안 만들었다 --- 「모른다」다**(조항 59). `False` 로 센다")
        sealed.append(k)
    return {
        "🔴🔴🔴 986 봉인 감사": "🔴 봉인 대상은 «절 명부»이고 제외 키를 산출물에 싣는다(985 R4)",
        "🔴 봉인한 절": sealed or "없음",
        "🔴 이미 `통과` 가 있어 안 건드린 절": already or "없음",
        "🔴🔴 봉인에서 «명시적으로» 뺀 키(= 절이 아니라 자료다)": skipped or "없음",
        "🔴 제외 목록(인자로 받은 것)": list(skip),
    }


def write(path, obj, ref, cs0, t0, seal_skip=SEAL_SKIP_DEFAULT):
    """🔴 도장 + 조항 66-② 신고를 **같이** 붙여 쓴다(도장 없이 쓰는 길을 없앤다)."""
    cs1 = code_stamp()
    obj["🔴🔴 조항 66-② (986)"] = clause66_2(cs0, cs1)
    obj["🔴 986 이 읽은 산출물 sha256"] = feeds_in()
    LG.write_stamped(str(ROOT / path), obj, ref, cs0, t0, RAN_ALL, DATA)
    import collections as _c
    raw = json.loads((ROOT / path).read_text(encoding="utf-8"),
                     object_pairs_hook=_c.OrderedDict)
    audit = seal_sections(raw, seal_skip)
    KEY = "🔴🔴🔴 986 봉인 감사(무엇을 봉했고 무엇을 뺐나)"
    raw[KEY] = audit
    left = [k for k, v in raw.items()
            if isinstance(v, dict) and "통과" not in v and k != KEY
            and k not in seal_skip and not any(w in k for w in ("sha256", "시각"))]
    audit["🔴🔴 봉인 뒤에도 `통과` 가 없는 절"] = left or "없음"
    audit["통과"] = bool(not left)
    audit["🔴 이 절의 `통과`"] = (
        "🔴 **봉인 뒤에 `통과` 키가 없는 최상위 절이 0 인가** --- 이 자는 떨어질 수 있다")
    (ROOT / path).write_text(
        json.dumps(raw, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return raw


def resolve(obj, path):
    """🔴 키 경로 해석 --- **「없다」와 「널이다」를 가른다**(조항 59)."""
    cur = obj
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return False, None
        cur = cur[k]
    return True, cur


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--begin":
        print(json.dumps(begin(sys.argv[2], force=("--force" in sys.argv)),
                         ensure_ascii=False)[:400])
        sys.exit(0)
    cs = code_stamp()
    print(json.dumps({
        "RAN_ALL": len(RAN_ALL),
        "RAN_986": len(RAN_986),
        "SCORE_CELLS": len(SCORE_CELLS),
        "DOC_PRODUCER": len(DOC_PRODUCER),
        "code_stamp 분모": len(cs),
        "못 덮은 항목": [r for r in RAN_ALL if r not in cs],
    }, ensure_ascii=False))
