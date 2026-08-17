#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""988 배관 — 🔴🔴🔴 **「등록한 판정식」을 대조하고, 「자리 0」을 「안 봤다」로 센다**.

🔴 **왜 (티처 #126).**

| 병 | 987 이 어떻게 걸렸나 | 988 의 배선 |
|---|---|---|
| 등록한 «판정식»이 갈아 끼워졌다 | `score987.py:812` 가 등록 정의(`명부판 §3 통과 = False`)를 **아예 계산하지 않고** `bool(sink)` 로 갈아 끼웠다 --- **일곱째 칸은 「값」만 봐서 원리상 못 본다** | `certify988` 의 **여덟째 칸** --- 사전등록 §5 의 「맞았다의 정의」를 **문자열로 읽고** 채점기의 **AST 키 경로 집합**과 대조 |
| 「자리 0」을 「통과」로 셌다 | `§K` 의 바늘이 **0 자리** 걸렸는데 초록 · 반증조건 8·14·15·16 도 전부 「자리 0」 | `조항 59-나` --- **분모 > 0 인데 걸린 자리가 0 이면 「미측정」**이고 `통과` 가 아니다 |
| 등록한 자를 조용히 강등했다 | 사전등록 §4-4 가 자를 **둘** 등록했는데 `§K` 가 「값 대조」를 `판정에 안 쓴다` 로 뺐다 | **값 대조를 판정 분모로 복귀**시키고 강등 사실을 원장에 적는다 |

🔴 **`DOC_INPUTS` 에서 «뺀» 둘과 사유**(987 그대로 · 조용히 안 뺀다 · 조항 60):
`out988_certify.json` 과 `out988_table.json` 은 **문서 자체의 함수**라
지문에 넣으면 이 자는 **원리상 고정점에 도달 못 한다**(자기 참조).
"""
import collections
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import ledger as LG                                   # noqa: E402

#: 🔴🔴🔴 **사이클 전체 러너 합집합.** 988 의 모든 산출물이 이 하나를 쓴다.
RAN_ALL = (
    # ㉠ 988 이 돌린다
    "runners/cycle988.py",
    "runners/house988.py",
    "runners/audit988.py",
    "runners/score988.py",
    "runners/note988_gen.py",
    "runners/certify988.py",
    "runners/prose988.py",
    "runners/plumb988.py",
    "runners/fiveprime902.py",
    # ㉡ 988 이 «값을 읽는» 러너 --- 🔴 조항 66-① 「잰 소스의 sha 를 산출물에 박는다」
    "runners/cycle987.py",
    "runners/audit987.py",
    "runners/power987.py",
    "runners/score987.py",
    "runners/certify987.py",
    "runners/note987_gen.py",
    "runners/prose987.py",
    "runners/house987.py",
    "runners/cycle986.py",
    "runners/score986.py",
    "runners/audit986.py",
    "runners/score985.py",
    "runners/stat983.py",
    "runners/checks964.py",
    "runners/meta965.py",
    "runners/daemonguard973.py",
    # ㉢ 그 둘이 import 한다
    "runners/ledger.py",
    "runners/house983.py",
    "runners/harvest_daemon.py",
)

#: 🔴🔴 **F14·F15 의 분모** --- 988 이 «새로 쓴» 러너 전량.
RAN_988 = (
    "runners/cycle988.py",
    "runners/house988.py",
    "runners/audit988.py",
    "runners/score988.py",
    "runners/note988_gen.py",
    "runners/certify988.py",
    "runners/prose988.py",
    "runners/plumb988.py",
)

DATA = dict(LG.DATA) if isinstance(getattr(LG, "DATA", None), dict) else {}

#: 988 이 값을 읽는 산출물
FEEDS_IN = (
    "runners/out987_score.json",
    "runners/out987_audit.json",
    "runners/out987_power.json",
    "runners/out987_prose.json",
    "runners/out987_table.json",
    "runners/out987_certify.json",
    "runners/fiveprime_987.json",
    "runners/out986_score.json",
    "runners/out986_table.json",
    "runners/out985_table.json",
    "runners/out983_reps.json",
)

SEAL_SKIP_DEFAULT = ("🔴🔴 치환표",)
WINDOW = "runners/out988_window.json"

SHARED = ("runners/cycle988.py", "runners/ledger.py")
PRODUCER = {
    "runners/out988_house.json": "runners/house988.py",
    "runners/out988_audit.json": "runners/audit988.py",
    "runners/out988_score.json": "runners/score988.py",
    "runners/out988_table.json": "runners/note988_gen.py",
    "runners/out988_certify.json": "runners/certify988.py",
    "runners/out988_prose.json": "runners/prose988.py",
}

# ══════════════════════════════════════════════════════════════════════
# 🔴🔴🔴 고정 ref --- 「전」을 «디스크에서» 읽는 길을 없앤다 (조항 71-가)
# ══════════════════════════════════════════════════════════════════════
#: 🔴 **987 이 끝난 트리**(#245 배관 머지 직후의 `main`). 「987 이 실은 것」은 전부 여기서 읽는다.
REF_987 = "35fba59115b6dfa24043612f028299c7c7994e24"
#: 🔴 **986 이 끝난 트리.**
REF_986 = "6b399dfc652b211fc0431bfb5259e2c496ddb757"
#: 🔴 **985 가 끝난 트리.**
REF_985 = "582444a856f6c573c7d5ebb34c5579497f5faee6"

#: 🔴 **AST 자의 등록 면제**(조용히 안 뺀다). 「지금」을 읽어야 하는 자리다.
DISK_READ_EXEMPT = {
    "runners/score988.py": "🔴 규칙 D 는 «지금»의 문서를 읽어야 한다(「전」이 아니다)",
    "runners/prose988.py": "🔴 산문 자는 «지금»의 판정문을 읽어야 한다",
    "runners/note988_gen.py": "🔴 문서 생산기는 «지금»의 문서를 쓴다",
}


class RefError(RuntimeError):
    pass


def _git(args, binary=False):
    p = subprocess.run(["git", "-c", "core.quotePath=false"] + args, cwd=str(ROOT),
                       capture_output=True)
    if p.returncode != 0:
        raise RefError("git %s -> %d: %s" % (args[:2], p.returncode,
                                             p.stderr.decode("utf-8", "replace")[:300]))
    return p.stdout if binary else p.stdout.decode("utf-8", "surrogateescape")


def fixed_ref_text(ref, rel):
    """🔴🔴🔴 **「전」 값을 읽는 «유일한» 문**(조항 71-가·나 · 987 이 만든 꼴 그대로)."""
    if not (isinstance(ref, str) and len(ref) == 40 and
            all(c in "0123456789abcdef" for c in ref)):
        raise RefError("🔴 고정 ref 가 40자 sha 가 아니다: %r" % (ref,))
    try:
        txt = _git(["show", "%s:%s" % (ref, rel)])
    except RefError as e:
        return {"🔴 고정 ref": ref, "🔴 경로": rel, "🔴 본문": None,
                "🔴 못 읽었다(= 「없다」가 아니다 · 조항 59)": str(e)[:200]}
    return {"🔴 고정 ref": ref, "🔴 경로": rel, "🔴 본문": txt,
            "🔴 sha256(그 트리의 blob)": hashlib.sha256(
                txt.encode("utf-8", "surrogateescape")).hexdigest()}


def fixed_ref_json(ref, rel):
    r = fixed_ref_text(ref, rel)
    if r["🔴 본문"] is None:
        return r, None
    try:
        return r, json.loads(r["🔴 본문"], object_pairs_hook=collections.OrderedDict)
    except Exception as e:                                          # noqa: BLE001
        r["🔴 JSON 이 아니다"] = str(e)[:200]
        return r, None


def before(ref, rel, fn, 이름):
    """🔴🔴 **「전」 측정의 «유일한» 꼴** --- 값과 ref 를 한 덩이로 낸다."""
    r = fixed_ref_text(ref, rel)
    txt = r["🔴 본문"]
    return collections.OrderedDict([
        ("🔴 이름", 이름),
        ("🔴🔴 고정 ref(= 이 값이 없으면 「전」이 아니다)", ref),
        ("🔴 경로", rel),
        ("🔴🔴🔴 값", (None if txt is None else fn(txt))),
        ("🔴 못 읽었다(= 「없다」가 아니다 · 조항 59)",
         r.get("🔴 못 읽었다(= 「없다」가 아니다 · 조항 59)", "없음")),
    ])


# ══════════════════════════════════════════════════════════════════════
# 🔴🔴🔴 조항 59-나 --- 「자리 0」은 「통과」가 아니라 「미측정」이다 (988 신설)
# ══════════════════════════════════════════════════════════════════════
def measured(이름, 분모, 걸린자리, 어긋남):
    """🔴🔴🔴 **`조항 59-나` 의 «유일한» 판정 꼴**.

    🔴 한 자가 「깨끗함」이려면 셋이 다 참이어야 한다:
      ① 대상 분모 > 0 · ② **걸린 자리가 «하나 이상»** · ③ 그중 어긋난 것이 0.
    🔴 **②가 0 이면 「미측정」**이고 `통과` 가 «아니다» --- 「깨끗함」과 「안 봤음」을 갈라 센다.
    """
    den_ok = bool((분모 or 0) > 0)
    hit_ok = bool((걸린자리 or 0) > 0)
    clean = bool((어긋남 or 0) == 0)
    if not den_ok:
        state = "🔴 분모 0 --- 안 쟀다"
    elif not hit_ok:
        state = "🔴🔴 미측정 --- 분모는 있는데 «걸린 자리가 0» 이다(= 「깨끗함」이 아니다)"
    elif clean:
        state = "🟢 깨끗함 --- 걸린 자리가 있고 어긋남이 0 이다"
    else:
        state = "🔴 어긋남 --- 걸린 자리에서 어긋난 것이 있다"
    return collections.OrderedDict([
        ("🔴 이름", 이름),
        ("🔴 분모(대상 수)", 분모),
        ("🔴🔴 걸린 자리 수(= 이 수가 0 이면 「미측정」이다)", 걸린자리),
        ("🔴 어긋난 수", 어긋남),
        ("🔴🔴🔴 갈래(조항 59-나)", state),
        ("🔴🔴🔴 미측정인가", bool(den_ok and not hit_ok)),
        ("통과", bool(den_ok and hit_ok and clean)),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **`조항 59-나`: 분모 > 0 ∧ 걸린 자리 > 0 ∧ 어긋남 0.** "
         "🔴 「걸린 자리 0」은 «통과»가 아니라 «미측정»이다(987 의 `§K` 가 그 자리였다)"),
    ])


# ══════════════════════════════════════════════════════════════════════
# 🔴🔴 여섯째 칸의 상수 + 일곱째(사전등록 정본) + 🔴🔴🔴 여덟째(등록 판정식)
# ══════════════════════════════════════════════════════════════════════
SCORE_CELLS = {
    "채.반증분자모": ["§6 🔴 반증조건", "🔴🔴 분자 / 분모"],
    "채.반증분모": ["§6 🔴 반증조건", "🔴 분모"],
    "채.반증된": ["§6 🔴 반증조건", "🔴🔴 반증된 조건(식별자만 · R4)"],
    "채.반증통과": ["§6 🔴 반증조건", "통과"],
    "채.예측분자모": ["§5 🔴 예측", "🔴🔴 분자 / 분모"],
    "채.예측분자": ["§5 🔴 예측", "🔴 분자"],
    "채.예측통과": ["§5 🔴 예측", "통과"],
    "채.규칙D표밖": ["§D 🔴 규칙 D 감사(분모 여섯)", "🔴🔴 표 밖 합"],
    "채.규칙D분모": ["§D 🔴 규칙 D 감사(분모 여섯)", "🔴🔴 채점 분모"],
    "채.규칙D통과": ["§D 🔴 규칙 D 감사(분모 여섯)", "통과"],
    "채.한글어긋남": ["§K 🔴🔴 규칙 D — 한글 수사(자 «둘»)", "🔴🔴🔴 바늘 대조 어긋난 수사 수"],
    "채.한글값어긋남": ["§K 🔴🔴 규칙 D — 한글 수사(자 «둘»)", "🔴🔴🔴 값 대조 어긋난 수사 수"],
    "채.한글분모": ["§K 🔴🔴 규칙 D — 한글 수사(자 «둘»)", "🔴🔴 센 한글 수사 수"],
    "채.한글걸림": ["§K 🔴🔴 규칙 D — 한글 수사(자 «둘»)", "🔴🔴🔴 바늘이 걸린 수사 수"],
    "채.한글바늘수": ["§K 🔴🔴 규칙 D — 한글 수사(자 «둘»)", "🔴🔴 등록 바늘 수"],
    "채.한글통과": ["§K 🔴🔴 규칙 D — 한글 수사(자 «둘»)", "통과"],
    "채.68근거없음": ["§68 🔴 조항 68 모양 주장 감사", "🔴🔴 근거 없는 모양 주장 수"],
    "채.68통과": ["§68 🔴 조항 68 모양 주장 감사", "통과"],
    "채.F5분모": ["§F5 🔴 인용 산출물 도장", "🔴 분모"],
    "채.F5통과": ["§F5 🔴 인용 산출물 도장", "통과"],
    "채.여섯자리": ["§9 🔴🔴 여섯 자리가 같은 수를 적나", "통과"],
    "채.미측정수": ["§59나 🔴🔴🔴 조항 59-나 — 「자리 0」 감사", "🔴🔴🔴 미측정인 자 수"],
    "채.최상위통과": ["통과"],
}

#: 🔴🔴🔴 **사전등록 §8 이 박은 「정본 값」** --- 채점에서 바뀌면 **F17**.
PREREG_CANON = collections.OrderedDict([
    ("987 예측 분자", 6),
    ("987 최상위 통과", True),
    ("987 audit §C 986 절 3 통과", True),
    ("987 §K 센 한글 수사 수", 39),
    ("987 §K 바늘이 걸린 수사 수", 0),
    ("987 §K 값 대조 어긋남 수", 0),
    ("987 산문 등록 안 된 주장 문장 수", 74),
    ("986 예측 분자", 3),
])

DOC_PRODUCER = {
    "docs/판정_988.md": "runners/note988_gen.py",
    "docs/card_988.md": "runners/note988_gen.py",
    "docs/handoff_988.md": "runners/note988_gen.py",
    "docs/pr_988.md": "runners/note988_gen.py",
}

DOC_INPUTS = (
    "runners/out988_score.json",
    "runners/out988_audit.json",
    "runners/out988_house.json",
    "runners/out988_prose.json",
    "runners/fiveprime_988.json",
)

DOC_INPUTS_EXCLUDED = collections.OrderedDict([
    ("runners/out988_certify.json",
     "🔴 `certify` 는 「표 ↔ 채점기 ↔ 디스크 문서 ↔ 사전등록」을 «검사»하는 자다. "
     "그 지문을 표에 박으면 문서가 자기 검사자의 지문을 싣는 «자기 참조»가 되어 "
     "이 자는 원리상 고정점에 도달 못 한다"),
    ("runners/out988_table.json",
     "🔴 치환표는 문서 «자신»이다 --- 표의 지문을 표 안에 박는 것은 정의상 불가능하다"),
])

TABLE = "runners/out988_table.json"
DOC_INPUT_KEY = "🔴🔴🔴 문서를 찍을 때 읽은 산출물 내용 지문(분모 5)"

DIGEST_SKIP = ("🔴 도장", "🔴🔴 조항 66-② (988)", "🔴 988 이 읽은 산출물 sha256",
               "🔴🔴🔴 988 봉인 감사(무엇을 봉했고 무엇을 뺐나)")

PREREG = "docs/prereg_988_registered_predicate.md"


def content_digest(rel):
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


def code_stamp():
    return LG.code_stamp(RAN_ALL)


def begin(ref, force=False):
    p = ROOT / WINDOW
    if p.is_file() and not force:
        return json.loads(p.read_text(encoding="utf-8"))
    d = {
        "무엇": "🔴🔴🔴 988 — **사이클 단위 측정 창**의 시작 도장",
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
        docs[d] = {"생산기": prod, "있나": p.is_file(), "지금 sha256": sha_file(d)}
    known = not miss
    return {
        "🔴🔴 무엇": "🔴🔴🔴 **채점기를 다시 돌리고 문서(·PR 본문)를 안 다시 찍었나**",
        "🔴🔴 분모: 문서가 인용하는 산출물": len(DOC_INPUTS),
        "🔴 분모의 내력(조항 60)": {"986 판": 3, "987 판": 5, "988 판": list(DOC_INPUTS)},
        "🔴🔴 «명시적으로» 뺀 입력과 사유(조용히 안 뺀다)": dict(DOC_INPUTS_EXCLUDED),
        "🔴 분모: 이 표가 덮는 문서": len(DOC_PRODUCER),
        "🔴 내용 지문에서 뺀 키(조항 59·60)": list(DIGEST_SKIP),
        "🔴 입력별": rows,
        "🔴 문서별": docs,
        "🔴 치환표가 sha 를 안 박은 입력(= 「같다」가 아니다 · 조항 59)": miss or "없음",
        "🔴🔴🔴 문서를 찍은 뒤 달라진 산출물": moved or "없음",
        "🔴🔴🔴 낡은 문서가 있나": (bool(moved) if known else None),
        "🔴 이 값이 `None` 이면": "🔴 **「낡지 않았다」가 아니라 「모른다」**다(조항 59)",
    }


def clause66_2(cs0, cs1):
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
        or "🔴 모른다 --- `out988_window.json` 이 없다(0 이 아니다)",
        "⚠ 좁은 창(이 러너의 t0~지금)에서 바뀐 파일": moved_narrow or "없음",
        "🔴🔴🔴 넓은 창(사이클 시작~지금)에서 바뀐 파일":
            (moved_wide or "없음") if wide_known else "🔴 모른다 --- 사이클 시작 도장이 없다",
        "🔴🔴🔴 측정 창 안에 러너를 고쳤나": (bool(moved_wide) if wide_known else None),
        "🔴🔴 좁은 창이 놓친 파일 수": (len(set(moved_wide or []) - set(moved_narrow))
                             if wide_known else None),
        "🔴🔴🔴 값을 낸 뒤 고치고 «안 다시 돌린» 산출물": stale_outputs(),
        "🔴🔴🔴 채점기를 다시 돌리고 «안 다시 찍은» 문서": stale_docs(),
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
            _sdoc = (v.get("🔴🔴🔴 채점기를 다시 돌리고 «안 다시 찍은» 문서")
                     or {}).get("🔴🔴🔴 낡은 문서가 있나")
            v["통과"] = bool(_known and _stale is False and _sdoc is False
                            and _miss and v[_miss[0]] == "없음")
            v["🔴 이 절의 `통과`"] = (
                "🔴🔴 **조건 넷**: ① 사이클 시작 도장을 읽었다 · ② 낡은 산출물 0 · "
                "③ 낡은 문서 0 · ④ 분모가 `RAN_ALL` 을 전부 덮었다. "
                "🔴 ③ 이 `None`(모른다)이면 «통과가 아니다»(조항 59)")
        else:
            v["통과"] = False
            v["🔴 이 절의 `통과`"] = (
                "🔴 **이 절은 `통과` 를 안 만들었다 --- 「모른다」다**(조항 59). `False` 로 센다")
        sealed.append(k)
    return {
        "🔴🔴🔴 988 봉인 감사": "🔴 봉인 대상은 «절 명부»이고 제외 키를 산출물에 싣는다",
        "🔴 봉인한 절": sealed or "없음",
        "🔴 이미 `통과` 가 있어 안 건드린 절": already or "없음",
        "🔴🔴 봉인에서 «명시적으로» 뺀 키(= 절이 아니라 자료다)": skipped or "없음",
        "🔴 제외 목록(인자로 받은 것)": list(skip),
    }


def write(path, obj, ref, cs0, t0, seal_skip=SEAL_SKIP_DEFAULT):
    cs1 = code_stamp()
    obj["🔴🔴 조항 66-② (988)"] = clause66_2(cs0, cs1)
    obj["🔴 988 이 읽은 산출물 sha256"] = feeds_in()
    LG.write_stamped(str(ROOT / path), obj, ref, cs0, t0, RAN_ALL, DATA)
    raw = json.loads((ROOT / path).read_text(encoding="utf-8"),
                     object_pairs_hook=collections.OrderedDict)
    audit = seal_sections(raw, seal_skip)
    KEY = "🔴🔴🔴 988 봉인 감사(무엇을 봉했고 무엇을 뺐나)"
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
    cur = obj
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return False, None
        cur = cur[k]
    return True, cur


def stamp_window(ref):
    p = ROOT / WINDOW
    if not p.is_file():
        return {"🔴": "🔴 창 파일이 없다"}
    d = json.loads(p.read_text(encoding="utf-8"),
                   object_pairs_hook=collections.OrderedDict)
    t0 = d.get("🔴 사이클 시작(UTC)") or now()
    cs0 = d.get("🔴 시작 code_stamp(파일별 sha256)") or code_stamp()
    d["⚠ 이 도장은 «사이클 끝»에 얹었다(988)"] = (
        "🔴 시작 시각과 시작 `code_stamp` 은 한 바이트도 «안» 바꿨다")
    LG.write_stamped(str(p), d, ref, cs0, t0, RAN_ALL, DATA)
    raw = json.loads(p.read_text(encoding="utf-8"),
                     object_pairs_hook=collections.OrderedDict)
    audit = seal_sections(raw, SEAL_SKIP_DEFAULT)
    KEY = "🔴🔴🔴 988 봉인 감사(무엇을 봉했고 무엇을 뺐나)"
    raw[KEY] = audit
    left = [k for k, v in raw.items()
            if isinstance(v, dict) and "통과" not in v and k != KEY
            and not any(w in k for w in ("sha256", "시각"))]
    audit["🔴🔴 봉인 뒤에도 `통과` 가 없는 절"] = left or "없음"
    audit["통과"] = bool(not left)
    audit["🔴 이 절의 `통과`"] = "봉인 뒤에 `통과` 키가 없는 최상위 절이 0 인가"
    p.write_text(json.dumps(raw, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return {"창": WINDOW, "도장": "얹었다", "봉인 뒤 `통과` 없는 절": left or "없음"}


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--stamp":
        print(json.dumps(stamp_window(sys.argv[2]), ensure_ascii=False))
        sys.exit(0)
    if len(sys.argv) > 2 and sys.argv[1] == "--begin":
        print(json.dumps(begin(sys.argv[2], force=("--force" in sys.argv)),
                         ensure_ascii=False)[:400])
        sys.exit(0)
    cs = code_stamp()
    print(json.dumps({
        "RAN_ALL": len(RAN_ALL),
        "RAN_988": len(RAN_988),
        "SCORE_CELLS": len(SCORE_CELLS),
        "PREREG_CANON": len(PREREG_CANON),
        "DOC_INPUTS": len(DOC_INPUTS),
        "code_stamp 분모": len(cs),
        "못 덮은 항목": [r for r in RAN_ALL if r not in cs],
    }, ensure_ascii=False))
