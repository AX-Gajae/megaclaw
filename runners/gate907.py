# -*- coding: utf-8 -*-
"""노트 907 — `ingest/doc_select.is_pre_open()` 이 정말 사후 문서를 막는가(팔 ㄱ) ·
레코드가 「완독했다」고 적어 둔 문서는 그 문을 지났는가(팔 ㄴ).

사전등록: `docs/prereg_907_docgate.md`
          (커밋 037f35410233f2813049f83452b9d65df24d6617 · 2026-08-11T10:57:48+09:00)

물음의 출처: 팔 ㄱ = 이슈 **#159**(티처 #69 · 한 팔만 먹는다) · 팔 ㄴ = **내가 골랐다**(사전등록 §1).

🔴 **채점기·측정 대상 코드를 한 글자도 안 고친다** — `ingest/doc_select.py` ·
   `ingest/calendar_features.py` · `ident901.py` · `ident902.py` · `inv901.py` 는 **읽기만** 한다.
   **등급·식1·식3 을 다시 안 채점한다.** 라벨이 아니라 **라벨이 서 있는 바닥**을 잰다.
🔴 **분모는 팝업 D1 380(레코드)과 그 레코드의 문서 전량이다. 짝 수(22·14)와 절대 안 잇는다**(조항 60).
🔴 **모든 분해에 「합 == 분모」 단언을 건다**(이슈 #158 처방 2) — `sumcheck()`.
🔴 **식별자에서 도메인을 안 버린다**(이슈 #158 처방 1) — 문서 식별자는 항상 `(record_id, doc_id)`.
🔴 **예측마다 순열 selectivity 를 자동으로 낸다**(티처 #69 의 메타 발견).
🔴 **효과 크기를 안 낸다** → 규약 47 의 구간이 없다(사전등록 ⓪-가 에 미리 못 박았다).
🔴 **ROOT 를 절대경로로 안 박는다**(티처 #69 M9).

실행: python3 runners/gate907.py
"""
from __future__ import annotations

import copy
import datetime as dt
import json
import random
import re
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]          # 🔴 절대경로 금지(티처 #69 M9)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runners"))

# 🔴 도장은 **실행 시작**에서 찍는다(티처 #64 C3)
T0 = time.time()
START = dt.datetime.now().isoformat(timespec="seconds")

from inv901 import sha                                          # noqa: E402  (읽기 전용)
from ingest.doc_select import (PRE_KINDS, POST_PAT, QUOTE_PAT,  # noqa: E402  (읽기 전용)
                               is_pre_open)
from ingest.calendar_features import _doc_dates                 # noqa: E402  (읽기 전용)

PREREG = {"파일": "docs/prereg_907_docgate.md",
          "커밋": "037f35410233f2813049f83452b9d65df24d6617",
          "커밋 시각": "2026-08-11T10:57:48+09:00"}

RECDIR = ROOT / "data/records"
DOCSALL = ROOT / "data/ingest/docs_all.json"
PREREG_MD = ROOT / "docs/prereg_907_docgate.md"
LEDGER = ROOT / "data/lab/denominator.json"
OUT = ROOT / "runners/out907_gate.json"
SCRATCH = ROOT / "runners" / ".907tmp"

PERM_N = 200
PERM_SEED = 907
BACKREF_L = 36            # 🔴 완독 명단이 제목을 ~40자에서 자른다 — 되짚기 접두사 길이
BACKREF_ALT = (30, 40)    # 🔴 자의 민감도를 같이 낸다

# 🔴 사후 어휘 — `POST_PAT` 과 **겹치지 않는** 것만(겹치면 이미 문이 막으므로 이중 계수다)
POSTWORD = re.compile(r"부속합의|변경계약|정산합의|추가합의|해지|원상복구|철수|종료보고|사후정산|최종보고")

# 🔴 확장 날짜 파서 — 사전등록 §1 이 미리 못 박은 6가지 꼴만 읽는다.
#    「YYYY-MM」·「YY년 M월」 꼴은 **그 달 1일**로 읽는다(제일 이른 날 = 사후 판정에 보수적).
EXT_PATS = [
    ("YYYY-MM-DD / YYYY.MM.DD", re.compile(r"(20\d{2})[-./](\d{1,2})[-./](\d{1,2})(?!\d)")),
    ("YYYY년 M월 D일", re.compile(r"(20\d{2})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일")),
    ("YY.MM.DD", re.compile(r"(?<![\d./-])(\d{2})[.-](\d{1,2})[.-](\d{1,2})(?![\d./-])")),
    ("YYYY-MM", re.compile(r"(20\d{2})[-.](\d{1,2})(?![\d./-])")),
    ("YYYY년 M월", re.compile(r"(20\d{2})\s*년\s*(\d{1,2})\s*월")),
    ("YY년 M월", re.compile(r"(?<!\d)(\d{2})\s*년\s*(\d{1,2})\s*월")),
]

REASONS = ("날짜를 읽어서", "날짜 부재", "open_from 없음", "open_from 파싱 실패")

# 🔴 생산 함수 진입 계수기 — 배선 검사가 그 함수를 **실제로 불렀다**는 유일한 증거
CALLS: Counter = Counter()
# 🔴 국소 시험용 — 이 집합에 든 검사 **하나만** 꺼진다
OFF: set[str] = set()


def _A(aid: str, cond: bool, msg: str) -> None:
    if aid in OFF:
        return
    if not cond:
        raise AssertionError(f"[{aid}] {msg}")


class Flaky(dict):
    """🔴 **입력 파손** — `get("title")` 이 호출마다 다른 값을 준다.

    내 재구현과 `is_pre_open()` 이 **같은 문서를 다르게 읽는** 상황을 실제로 만든다.
    """

    def __init__(self, base: dict, titles: list[str]):
        super().__init__(base)
        self._t = list(titles)
        self._i = 0

    def get(self, k, default=None):                     # noqa: A003
        if k == "title":
            v = self._t[min(self._i, len(self._t) - 1)]
            self._i += 1
            return v
        return dict.get(self, k, default)


# ══ 생산 함수 ══════════════════════════════════════════════════════════
def read_one(raw: dict, name: str) -> dict:
    """원천 레코드 하나를 검사하고 돌려준다.

    Q1 record_id 가 비어 있지 않은 문자열이 아니면 죽는다
    Q2 `docs` 가 리스트가 아니면 죽는다
    """
    CALLS["read_one"] += 1
    rid = raw.get("record_id")
    _A("Q1", isinstance(rid, str) and bool(rid), f"{name}: record_id 가 문자열이 아니다/비었다 — {rid!r}")
    _A("Q2", isinstance(raw.get("docs"), list),
       f"{rid}: docs 가 리스트가 아니다 — {type(raw.get('docs')).__name__}")
    return raw


def load_popup(dirpath: Path) -> list[dict]:
    """팝업 원천 레코드 전량. Q3 한 건도 못 읽으면 죽는다(「0건」이 아니라 「못 읽었다」 · 조항 59)."""
    CALLS["load_popup"] += 1
    recs = [read_one(json.loads(p.read_text()), p.name) for p in sorted(Path(dirpath).glob("*.json"))]
    _A("Q3", len(recs) > 0, f"{dirpath}: 원천 레코드를 한 건도 못 읽었다")
    return recs


def ext_dates(title) -> list[date]:
    """🔴 확장 날짜 파서 — `_doc_dates` 가 못 읽는 꼴을 읽는다. X1 제목이 문자열이 아니면 죽는다."""
    CALLS["ext_dates"] += 1
    _A("X1", isinstance(title, str), f"제목이 문자열이 아니다 — {type(title).__name__}")
    out: list[date] = []
    for _nm, pat in EXT_PATS:
        for m in pat.finditer(title):
            g = m.groups()
            try:
                y = int(g[0])
                y = y + 2000 if y < 100 else y
                mo = int(g[1])
                d = int(g[2]) if len(g) > 2 else 1
                out.append(date(y, mo, d))
            except ValueError:
                continue
    return out


def judge_post(title, open_from) -> dict:
    """② 안의 문서 하나를 **사후 / 사전 / 모른다** 셋으로 가른다(조항 59).

    J1 open_from 이 문자열도 None 도 아니면 죽는다
    J2 🔴 **구조상 영구 참** — 결과가 셋 중 하나. 심을 수 없다(§3-7 대로 신고한다)
    """
    CALLS["judge_post"] += 1
    ds = ext_dates(title)
    _A("J1", open_from is None or isinstance(open_from, str),
       f"open_from 이 문자열도 None 도 아니다 — {type(open_from).__name__}")
    f = None
    if open_from:
        try:
            f = date.fromisoformat(open_from)
        except ValueError:
            f = None
    late = bool(ds) and f is not None and min(ds) > f
    word = bool(POSTWORD.search(title))
    if late or word:
        r = "사후"
    elif ds and f is not None:
        r = "사전"
    else:
        r = "모른다"
    _A("J2", r in ("사후", "사전", "모른다"), f"판정이 셋 밖이다 — {r!r}")
    return {"판정": r, "확장 날짜 수": len(ds),
            "확장 날짜 최소": min(ds).isoformat() if ds else None,
            "근거": ("확장 날짜가 오픈일보다 뒤" if late else
                   ("사후 어휘" if word else ("확장 날짜가 오픈일 이하" if r == "사전" else
                                          "확장 날짜도 사후 어휘도 없다"))),
            "확장 날짜가 읽혔나": bool(ds)}


def classify(rid: str, d, open_from) -> dict:
    """문서 하나를 문에 먹인다. 🔴 `is_pre_open()` 을 **부른다 — 재구현으로 대체하지 않는다.**

    C1 제목이 문자열이 아니면 죽는다
    C2 doc_id 가 문자열이 아니면 죽는다 — 🔴 **식별자를 안 버린다**(이슈 #158 처방 1)
    C3 🔴 내 재구현이 `is_pre_open()` 과 어긋나면 죽는다
    """
    CALLS["classify"] += 1
    t = d.get("title") or d.get("name") or ""
    _A("C1", isinstance(t, str), f"{rid}: 제목이 문자열이 아니다 — {type(t).__name__}")
    did = d.get("doc_id")
    _A("C2", isinstance(did, str) and bool(did), f"{rid}: doc_id 가 문자열이 아니다/비었다 — {did!r}")
    passed = bool(is_pre_open(d, open_from))
    kind = d.get("kind")
    ds = _doc_dates([{"name": t}])
    post = bool(POST_PAT.search(t))

    # 🔴 재구현 — `doc_select.is_pre_open` 과 같은 답을 내야 한다(C3 이 그것을 강제한다)
    if post:
        mine, reason, route = False, "POST_PAT 에 걸렸다", "밖"
    elif kind in PRE_KINDS:
        route = "A"
        mine, reason = True, "날짜를 읽어서"
        if not open_from:
            reason = "open_from 없음"
        elif not ds:
            reason = "날짜 부재"
        else:
            try:
                if min(ds) > date.fromisoformat(open_from):
                    mine, reason = False, "PRE_KINDS 인데 날짜가 오픈 뒤다"
            except ValueError:
                reason = "open_from 파싱 실패"
    elif kind == "정산" and QUOTE_PAT.search(t) and open_from:
        route = "B"
        try:
            f = date.fromisoformat(open_from)
            mine = any(x <= f for x in ds)
            reason = "날짜를 읽어서" if mine else "정산·견적인데 날짜가 없거나 늦다"
        except ValueError:
            mine, reason = False, "정산·견적인데 open_from 파싱 실패"
    elif kind == "정산":
        route = "밖"
        mine, reason = False, ("정산인데 open_from 이 없다" if QUOTE_PAT.search(t)
                               else "정산인데 견적 어휘가 없다")
    else:
        route = "밖"
        mine, reason = False, "kind 가 문 밖이다"
    _A("C3", mine == passed,
       f"{rid}/{did}: 재구현 {mine} 과 is_pre_open {passed} 이 어긋난다 — kind={kind!r} 제목={t[:40]!r}")
    return {"record_id": rid, "doc_id": did, "제목": t, "kind": kind,
            "통과": passed, "경로": (route if passed else "불통과"),
            "🔴 경로(통과 무관)": route, "통과 사유": reason,
            "`_doc_dates` 가 읽은 날짜 수": len(ds), "open_from": open_from}


def sumcheck(name: str, decomp: dict, denom: int) -> dict:
    """🔴 이슈 #158 처방 2 — **모든 분해에 「합 == 분모」 단언.**

    U2 값이 전부 정수(bool 제외)가 아니면 죽는다
    U1 🔴 값의 합이 분모와 다르면 죽는다
    """
    CALLS["sumcheck"] += 1
    _A("U2", all(isinstance(v, int) and not isinstance(v, bool) for v in decomp.values()),
       f"{name}: 분해의 값이 정수가 아니다 — {[type(v).__name__ for v in decomp.values()]}")
    s = sum(decomp.values())
    _A("U1", s == denom, f"{name}: 분해의 합 {s} 이 분모 {denom} 과 다르다")
    return {"분해": dict(decomp), "🔴 합": s, "🔴 분모": denom, "🔴 합 == 분모": True}


NOTE_PAT = re.compile(r"완독 문서\s*(\d+)\s*건\s*:")


def readnotes(rec: dict) -> dict:
    """팔 ㄴ — `provenance.notes` 의 「완독 문서」 명단 조각을 뽑는다.

    N1 `provenance` 가 dict 가 아니면 죽는다
    N2 `notes` 가 문자열도 None 도 아니면 죽는다
    """
    CALLS["readnotes"] += 1
    p = rec.get("provenance")
    _A("N1", isinstance(p, dict), f"{rec.get('record_id')}: provenance 가 dict 가 아니다 — {type(p).__name__}")
    n = p.get("notes")
    _A("N2", n is None or isinstance(n, str),
       f"{rec.get('record_id')}: notes 가 문자열도 None 도 아니다 — {type(n).__name__}")
    if not n:
        return {"표기 건수": None, "명단 조각": "", "🔴 표기가 없다": True}
    m = NOTE_PAT.search(n)
    if not m:
        return {"표기 건수": None, "명단 조각": "", "🔴 표기가 없다": True}
    seg = n[m.end():]
    cut = re.search(r"미확실\s*:", seg)
    if cut:
        seg = seg[:cut.start()]
    return {"표기 건수": int(m.group(1)), "명단 조각": seg.strip(), "🔴 표기가 없다": False}


def perms(base: list, n: int, seed: int) -> list[list]:
    """🔴 순열 selectivity 용 — `open_from` 을 레코드 사이에서 섞는다.

    M1 순열 횟수가 1 미만이면 죽는다
    M2 🔴 만든 순열이 **전부 항등**이면 죽는다(항등이면 selectivity 0 이 공짜다)
    """
    CALLS["perms"] += 1
    _A("M1", n >= 1, f"순열 횟수가 1 미만이다 — {n}")
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        c = list(base)
        rng.shuffle(c)
        out.append(c)
    _A("M2", any(c != list(base) for c in out), "만든 순열이 전부 항등이다 — selectivity 0 이 공짜가 된다")
    return out


# ══ 배선 검사 ══════════════════════════════════════════════════════════
def _probe(fn, *args):
    try:
        fn(*args)
        return False, "", ""
    except AssertionError as e:
        return True, str(e)[:180], ""
    except Exception as e:                                       # noqa: BLE001
        return False, "", f"🔴 다른 예외({type(e).__name__}): {str(e)[:120]}"


def code_checks() -> dict:
    """🔴 러너가 **자기 소스에서** `_A(` 아이디를 전량 뽑는다 — 손 나열 금지(티처 #69 M6)."""
    src = Path(__file__).read_text(encoding="utf-8")
    ids = re.findall(r"_A\(\s*\"([A-Z]\d+)\"", src)
    seen: list[str] = []
    for i in ids:
        if i not in seen:
            seen.append(i)
    return {"🔴 코드의 검사 수(분모)": len(seen), "🔴 코드의 검사 아이디 전량": seen}


def wiring(recs: list[dict]) -> dict:
    w = {"🔴 규약": ("검사는 생산 함수를 **부른다**(지역 복제본 금지). 증거는 진입 계수기 `CALLS`. "
                  "🔴 각 검사를 **하나만 꺼서** 다시 넣는다 — 다른 검사가 대신 발화하면 국소 시험 실패. "
                  "🔴 심는 결함은 **전부 입력 파손**이다. "
                  "🔴 ㉱ 는 국소 열 자체의 검정력이다 — 그 검사를 끈 채 **다른 검사가 잡도록 만든 입력**을 "
                  "넣는다. 못 만들면 **검정력 0 으로 신고**한다(사전등록 §3-4)"),
         "검사": {}}

    def one(aid, fn, fnname, broken, clean, 심은것, double=None, 못심은사유=None):
        before = CALLS[fnname]
        fired, msg, ex1 = _probe(fn, *broken)
        c1 = CALLS[fnname]
        OFF.add(aid)
        try:
            loc, locmsg, _ = _probe(fn, *broken)
        finally:
            OFF.discard(aid)
        c2 = CALLS[fnname]
        neg, negmsg, ex3 = _probe(fn, *clean)
        c3 = CALLS[fnname]
        pw, pwmsg = None, "🔴 이 검사엔 겹칠 짝 검사를 못 만들었다(검정력 안 쟀다)"
        if double is not None:
            OFF.add(aid)
            try:
                pw, pwmsg, _ = _probe(fn, *double)
            finally:
                OFF.discard(aid)
        w["검사"][aid] = {
            "부른 생산 함수": fn.__qualname__,
            "심은 결함(입력 파손)": 심은것,
            "㉮ 파손·전부 켬 — 발화": fired, "발화 메시지": msg or ex1,
            "🔴 ㉯ 파손·이 검사만 끔 — 발화": loc, "㉯ 메시지": locmsg,
            "🔴 국소 시험 통과(㉯ 가 발화 안 함)": (not loc),
            "㉰ 정상·전부 켬 — 발화": neg, "㉰ 메시지": (negmsg or ex3) if (neg or ex3) else "발화 안 함(정상)",
            "🔴 ㉱ 국소 열이 거짓이 되는 입력을 심었을 때 발화": pw,
            "㉱ 메시지": pwmsg,
            "🔴 ㉱ 국소 열의 검정력 > 0": bool(pw),
            "🔴 ㉱ 를 못 만든 사유": 못심은사유 or "",
            "🔴 결함을 지우면 통과로 바뀌나": (fired and not neg),
            "진입 계수기 증가(㉮/㉯/㉰)": [c1 - before, c2 - c1, c3 - c2],
            "🔴 계수기가 셋 다 늘었나": (c1 > before and c2 > c1 and c3 > c2),
        }

    r0 = recs[0]
    good = {"record_id": "RTEST", "docs": [], "provenance": {"notes": "완독 문서 1건: 가나다라마바사아자차."}}
    gooddoc = {"doc_id": "D1", "kind": "기획서", "title": "행사 기획안 20240101.pdf"}

    one("Q1", read_one, "read_one", ({"docs": []}, "x"), (dict(good), "x"),
        "레코드에서 `record_id` 를 지웠다", ({"docs": "nope"}, "x"))
    one("Q2", read_one, "read_one", ({"record_id": "R", "docs": "nope"}, "x"), (dict(good), "x"),
        "`docs` 를 리스트가 아닌 문자열로 바꿨다", ({"record_id": None, "docs": "nope"}, "x"))

    SCRATCH.mkdir(exist_ok=True)
    empty = SCRATCH / "empty"
    empty.mkdir(exist_ok=True)
    for p in empty.glob("*.json"):
        p.unlink()
    bad = SCRATCH / "bad"
    bad.mkdir(exist_ok=True)
    (bad / "x.json").write_text(json.dumps({"docs": []}, ensure_ascii=False))
    one("Q3", load_popup, "load_popup", (empty,), (RECDIR,),
        "레코드가 한 건도 없는 디렉터리를 넣었다", (bad,))

    one("X1", judge_post, "judge_post", (None, "2025-01-01"), ("계약서 2025-01-01", "2025-01-01"),
        "제목 자리에 `None` 을 넣었다", (None, 20250101))
    one("J1", judge_post, "judge_post", ("계약서", 20250101), ("계약서 2025-01-01", "2025-01-01"),
        "`open_from` 을 문자열이 아닌 정수로 바꿨다", (None, 20250101))

    one("C1", classify, "classify", ("R", {"doc_id": "D", "kind": "기획서", "title": 123}, "2025-01-01"),
        ("R", dict(gooddoc), "2025-01-01"),
        "문서의 `title` 을 정수로 바꿨다", ("R", {"kind": "기획서", "title": 123}, "2025-01-01"))
    one("C2", classify, "classify", ("R", {"kind": "기획서", "title": "기획안"}, "2025-01-01"),
        ("R", dict(gooddoc), "2025-01-01"),
        "🔴 문서에서 `doc_id` 를 지웠다 — 식별자를 버리는 자리(이슈 #158 처방 1)",
        ("R", {"kind": "기획서", "title": 123}, "2025-01-01"))
    one("C3", classify, "classify",
        ("R", Flaky({"doc_id": "D", "kind": "기획서"}, ["정산서 최종.pdf", "기획안.pdf"]), "2025-01-01"),
        ("R", dict(gooddoc), "2025-01-01"),
        "🔴 `get(\"title\")` 이 호출마다 다른 값을 주는 문서를 넣었다 — 재구현과 원 함수가 갈린다",
        ("R", Flaky({"kind": "기획서"}, ["정산서 최종.pdf", "기획안.pdf"]), "2025-01-01"))

    rows = [classify(r0["record_id"], d, (r0.get("conditions", {}).get("period") or {}).get("from"))
            for d in r0["docs"]]
    n0 = len(rows)
    bad_route = [dict(x) for x in rows]
    for x in bad_route:
        if x["통과"]:
            x["경로"] = "밖"
            break
    bad_reason = [dict(x) for x in rows]
    for x in bad_reason:
        if x["통과"] and x["경로"] == "A":
            x["통과 사유"] = "?"
            break
    one("S1", partition, "partition", (rows, n0 + 1), (rows, n0),
        "🔴 분모만 1 크게 넣었다 — 분류한 문서 수와 원천 문서 수가 어긋난다",
        (bad_route, n0 + 1))
    one("S3", partition, "partition", (bad_route, n0), (rows, n0),
        "통과한 문서 하나의 경로를 `밖` 으로 바꿨다", (bad_route, n0 + 1))
    one("S4", partition, "partition", (bad_reason, n0), (rows, n0),
        "통과한 경로 A 문서 하나의 통과 사유를 넷 밖 `?` 로 바꿨다", (bad_reason, n0 + 1))

    one("U1", sumcheck, "sumcheck", ("t", {"a": 1, "b": 2}, 4), ("t", {"a": 1, "b": 2}, 3),
        "🔴 분해의 합이 3 인데 분모를 4 로 넣었다", ("t", {"a": True, "b": 2}, 4))
    one("U2", sumcheck, "sumcheck", ("t", {"a": True, "b": 2}, 3), ("t", {"a": 1, "b": 2}, 3),
        "분해의 값 하나를 `True`(bool) 로 바꿨다", ("t", {"a": True, "b": 2}, 99))

    one("N1", readnotes, "readnotes", ({"record_id": "R", "provenance": "x"},), (dict(good),),
        "`provenance` 를 dict 가 아닌 문자열로 바꿨다", None,
        "🔴 `provenance` 가 dict 가 아니면 N2 가 `.get` 을 부르다 **AssertionError 가 아닌 예외**로 죽는다 "
        "— 겹칠 짝 검사를 만들 수 없다")
    one("N2", readnotes, "readnotes", ({"record_id": "R", "provenance": {"notes": 12}},), (dict(good),),
        "`notes` 를 문자열이 아닌 정수로 바꿨다", ({"record_id": "R", "provenance": "x"},))

    one("M1", perms, "perms", (["a"], 0, 1), (["a", "b"], 3, 1),
        "순열 횟수를 0 으로 넣었다", (["a"], 0, 1))
    one("M2", perms, "perms", (["a"], 3, 1), (["a", "b"], 3, 1),
        "🔴 원소가 하나인 목록을 넣었다 — 어떤 순열도 항등이다", (["a"], 0, 1))

    n = len(w["검사"])
    fired = sum(1 for v in w["검사"].values() if v["㉮ 파손·전부 켬 — 발화"])
    local = sum(1 for v in w["검사"].values() if v["🔴 국소 시험 통과(㉯ 가 발화 안 함)"])
    neg = sum(1 for v in w["검사"].values() if not v["㉰ 정상·전부 켬 — 발화"])
    flip = sum(1 for v in w["검사"].values() if v["🔴 결함을 지우면 통과로 바뀌나"])
    cnt = sum(1 for v in w["검사"].values() if v["🔴 계수기가 셋 다 늘었나"])
    powered = sum(1 for v in w["검사"].values() if v["🔴 ㉱ 국소 열의 검정력 > 0"])
    tried = sum(1 for v in w["검사"].values()
                if v["🔴 ㉱ 국소 열이 거짓이 되는 입력을 심었을 때 발화"] is not None)
    cc = code_checks()
    planted = list(w["검사"].keys())
    unplanted = [i for i in cc["🔴 코드의 검사 아이디 전량"] if i not in planted]
    STRUCT = {"J2": ("🔴 **구조상 영구 참** — `r` 은 바로 위에서 세 리터럴 중 하나로 대입되므로 "
                     "입력을 어떻게 파손해도 거짓이 될 수 없다. 심을 수 있는 결함이 **원리상 없다**. "
                     "지우지 않고 **신고한다**(티처 #69 M6 이 906 에서 잡은 자리)")}
    w.update({
        "🔴 분모(심은 결함 수)": n, "발화": fired, "🔴 국소 시험 통과": local,
        "음성 대조 통과": neg, "🔴 지우면 통과로 바뀐 수": flip, "🔴 계수기가 늘어난 수": cnt,
        "🔴 ㉱ 국소 열 검정력을 잰 검사 수(분모)": tried,
        "🔴 ㉱ 국소 열 검정력 > 0 인 검사 수": powered,
        "🔴 ㉱ 는 통과 조건이 아니다": "검정력이 0 이면 0 이라고 **신고**한다(사전등록 §3-4)",
    })
    w.update(cc)
    w["🔴 심은 검사 아이디 전량"] = planted
    w["🔴 안 심은 검사 아이디 전량"] = unplanted or "없다(전량 심었다)"
    w["🔴 구조상 영구 참으로 신고한 검사"] = {k: v for k, v in STRUCT.items() if k in unplanted}
    w["🔴 안 심었는데 사유도 없는 검사"] = [i for i in unplanted if i not in STRUCT] or "없다"
    w["🔴 검사 회계 (합 == 분모)"] = sumcheck(
        "배선 검사 회계", {"심은 수": n, "구조상 영구 참으로 신고한 수": len(w["🔴 구조상 영구 참으로 신고한 검사"]),
                    "안 심었고 사유도 없는 수": len([i for i in unplanted if i not in STRUCT])},
        cc["🔴 코드의 검사 수(분모)"])
    w["통과"] = (fired == n and local == n and neg == n and flip == n and cnt == n
                and not [i for i in unplanted if i not in STRUCT])
    w["⚠ 통과의 뜻"] = ("🔴 심은 것이 전부 발화·국소·음성·계수기를 통과했고, "
                   "**코드의 검사 전량이 「심었다」나 「구조상 영구 참」 둘 중 하나로 회계됐나**(티처 #69 M6)")
    return w


def partition(rows: list[dict], ndocs: int) -> dict:
    """🔴 문서 전량을 세 갈래로 가른다 + **합 == 분모** 단언(이슈 #158 처방 2).

    S1 분류한 문서 수가 원천 문서 수와 다르면 죽는다
    S3 통과한 문서의 경로가 A/B 밖이면 죽는다
    S4 통과한 경로 A 문서의 통과 사유가 넷 밖이면 죽는다
    """
    CALLS["partition"] += 1
    _A("S1", len(rows) == ndocs, f"분류한 문서 수 {len(rows)} 가 원천 문서 수 {ndocs} 와 다르다")
    pas = [r for r in rows if r["통과"]]
    _A("S3", all(r["경로"] in ("A", "B") for r in pas),
       f"통과 문서의 경로가 A/B 밖이다 — {sorted({r['경로'] for r in pas})}")
    A = [r for r in pas if r["경로"] == "A"]
    B = [r for r in pas if r["경로"] == "B"]
    _A("S4", all(r["통과 사유"] in REASONS for r in A),
       f"경로 A 통과 사유가 넷 밖이다 — {sorted({r['통과 사유'] for r in A})}")
    a1 = [r for r in A if r["통과 사유"] == "날짜를 읽어서"]
    a2 = [r for r in A if r["통과 사유"] != "날짜를 읽어서"]
    return {"전량": rows, "통과": pas, "A": A, "B": B, "①A": a1, "②": a2,
            "①": a1 + B, "불통과": [r for r in rows if not r["통과"]]}


# ══ 원장 훑기 ══════════════════════════════════════════════════════════
def _dead_values() -> list[str]:
    """🔴 은퇴값 목록을 **읽어 온다**(손 나열 금지 · `ingest/audit.py:DEAD_NUMBERS` 가 정본)."""
    from ingest.audit import DEAD_NUMBERS                        # noqa: PLC0415 (읽기 전용)
    return [str(r[0]) for r in DEAD_NUMBERS]


MASKED: Counter = Counter()


def mask_dead(s: str) -> str:
    for v in _dead_values():
        if v in s:
            MASKED[v] += s.count(v)
            s = s.replace(v, "<은퇴값 · ingest/audit.py:DEAD_NUMBERS 참조>")
    return s


def ledger_scan() -> dict:
    CALLS["ledger_scan"] += 1
    d = json.loads(LEDGER.read_text())
    needles = ["문서", "사전 문서", "사후", "마스크", "팝업"]
    out = {"원장 최상위 항목(분모)": len(d), "🔴 바늘": needles}
    hits = {}
    for nd in needles:
        h = [k for k, v in d.items() if nd in k or nd in json.dumps(v, ensure_ascii=False)]
        hits[nd] = h
        out[f"바늘 `{nd}` 에 걸린 항목 수"] = len(h)
    uni = sorted(set().union(*hits.values()) if hits else set())
    out["🔴 합집합(이 물음에 걸리는 옛 항목 수)"] = len(uni)
    core = sorted(set(hits["사전 문서"]) | set(hits["사후"]) | set(hits["마스크"]))
    out["🔴 좁은 바늘(사전 문서·사후·마스크) 합집합 수"] = len(core)
    out["🔴 좁은 바늘 목록"] = [mask_dead(x) for x in core]
    big = max(hits, key=lambda k: len(hits[k]))
    out["🔴 제일 넓은 바늘"] = big
    out["🔴 제일 넓은 바늘이 합집합에서 차지하는 비율"] = round(len(hits[big]) / max(len(uni), 1), 3)
    out["🔴 넓은 바늘은 잡음이다"] = "판정에 쓰는 것은 좁은 바늘 쪽이다"
    out["🔴 은퇴값 가리기"] = {"🔴 가린 값의 가짓수": len(MASKED), "🔴 가린 자리 합": sum(MASKED.values()),
                       "🔴 가린 값 자체는 안 싣는다": "`ingest/audit.py:DEAD_NUMBERS` 가 정본이다"}
    out["🔴 앞 사이클의 수와 안 잇는다"] = "903~906 은 바늘이 달랐다. **같은 이름의 다른 자다**(조항 60)"
    out["통과"] = True
    return out


# ══ §6 대조 ════════════════════════════════════════════════════════════
def check_wording(verdict: str, head: str) -> dict:
    md = PREREG_MD.read_text()
    i = md.find(head)
    if i < 0:
        return {"찾았나": False, "🔴 판정": "사전등록에서 그 갈래를 못 찾았다", "🔴 순서대로 다 들어 있나": False}
    seg = md[i + len(head):]
    j = seg.find("\n###")
    seg = seg[:j] if j > 0 else seg
    body = " ".join(ln.lstrip("> ").strip() for ln in seg.splitlines() if ln.strip().startswith(">"))

    def norm(s):
        return re.sub(r"\s+", " ", s.replace("**", "").replace("`", "")).strip()

    body, vn = norm(body), norm(verdict)
    frags = [f.strip(" .·,") for f in re.split(r"\{[^}]*\}", body)]
    frags = [f for f in frags if len(f) >= 6]
    pos, miss = 0, []
    for f in frags:
        k = vn.find(f, pos)
        if k < 0:
            miss.append(f)
        else:
            pos = k + len(f)
    return {"찾았나": True, "뼈대 조각 수(분모)": len(frags),
            "🔴 순서대로 다 들어 있나": not miss, "빠진 조각": miss}


def _walk(node, path, hits, needle, cap):
    if len(hits) >= cap:
        return
    if isinstance(node, dict):
        for k, v in node.items():
            if needle in str(k):
                hits.append(f"{path}/{k} (키 이름)")
            _walk(v, f"{path}/{k}", hits, needle, cap)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            _walk(v, f"{path}[{i}]", hits, needle, cap)
    else:
        if isinstance(node, bool):
            return
        if isinstance(node, (int, float)) and str(node) == needle:
            hits.append(path)
        elif isinstance(node, str) and needle in node:
            hits.append(f"{path} (문자열 안)")


def already_there(verdicts: list[str], srcs: dict, cap: int = 5) -> dict:
    CALLS["already_there"] += 1
    nums = sorted({n for v in verdicts for n in re.findall(r"\d+(?:\.\d+)?", v)}, key=lambda s: (len(s), s))
    loaded = {}
    for name, p in srcs.items():
        try:
            loaded[name] = json.loads(Path(p).read_text())
        except Exception:                                        # noqa: BLE001
            pass
    per = {}
    for n in nums:
        e = {}
        for name, d in loaded.items():
            h: list[str] = []
            _walk(d, "", h, n, cap)
            e[name] = {"찾은 수(상한 %d)" % cap: len(h), "경로": h}
        e["🔴 판정"] = ("입력에 이미 있다" if any(v["찾은 수(상한 %d)" % cap] for v in e.values()
                                          if isinstance(v, dict))
                     else "입력에서 못 찾았다(오늘 새로 잰 수다)")
        per[n] = e
    새것 = [n for n, e in per.items() if e["🔴 판정"].startswith("입력에서 못")]
    return {"판정문에서 뽑은 정수 가짓수(분모)": len(nums), "판정문에서 뽑은 정수": nums,
            "🔴 입력에서 못 찾은 수(오늘 새것)": 새것, "🔴 입력에서 못 찾은 수의 개수": len(새것),
            "🔴 입력에 이미 있는 수의 개수": len(nums) - len(새것),
            "⚠ 작은 정수는 어디에나 맞는다": "0·1·2 같은 수의 「이미 있다」는 증거가 약하다 — 경로를 보고 판단하라",
            "수별 되찾기": per, "통과": len(nums) > 0 and bool(loaded),
            "⚠ 통과의 뜻": "판정문에서 수를 실제로 뽑았고 입력을 실제로 열었나"}


# ══ 측정 본체 ══════════════════════════════════════════════════════════
def open_of(rec: dict):
    return (rec.get("conditions", {}).get("period") or {}).get("from")


def run_pass(recs: list[dict], opens: list) -> dict:
    """레코드 전량 × 문서 전량을 문에 먹인다. `opens` 를 갈아 끼우면 순열 판본이 된다."""
    rows = []
    for rec, of in zip(recs, opens):
        rid = rec["record_id"]
        for d in rec["docs"]:
            rows.append(classify(rid, d, of))
    P = partition(rows, sum(len(r["docs"]) for r in recs))
    j = [dict(r, **{"사후 판정": judge_post(r["제목"], r["open_from"])}) for r in P["②"]]
    c = Counter(x["사후 판정"]["판정"] for x in j)
    return {"통과": len(P["통과"]), "①": len(P["①"]), "②": len(P["②"]),
            "③ 사후": c.get("사후", 0), "사전": c.get("사전", 0), "모른다": c.get("모른다", 0),
            "확장 날짜가 읽힌 ②": sum(1 for x in j if x["사후 판정"]["확장 날짜가 읽혔나"]),
            "_P": P, "_j": j}


def backref(recs: list[dict], L: int) -> dict:
    """팔 ㄴ — 완독 명단을 그 레코드의 `docs` 로 되짚는다(접두사 L 자 포함 여부)."""
    matched, per_rec, 표기합, 표기없음 = [], {}, 0, 0
    for rec in recs:
        nt = readnotes(rec)
        if nt["🔴 표기가 없다"]:
            표기없음 += 1
            continue
        표기합 += nt["표기 건수"]
        seg = nt["명단 조각"]
        hit = []
        for d in rec["docs"]:
            t = (d.get("title") or "").strip()
            if len(t) >= 8 and t[:L] in seg:
                hit.append(d)
        per_rec[rec["record_id"]] = {"표기 건수": nt["표기 건수"], "되짚힌 수": len(hit)}
        of = open_of(rec)
        for d in hit:
            matched.append(classify(rec["record_id"], d, of))
    return {"matched": matched, "per_rec": per_rec, "표기 합": 표기합, "표기 없음 레코드": 표기없음}


def main():
    out = {
        "노트": 907,
        "사전등록": PREREG,
        "시작 시각": START,
        "물음의 출처": {"팔 ㄱ": "이슈 #159 (티처 #69) — 한 팔만 먹는다",
                   "팔 ㄴ": "🔴 내가 골랐다 — 사전등록 §1. 인접성만큼 명부에서 뺐다(예측 2개)"},
        "🔴 효과 크기": "없음 — 원천 문서의 개수뿐. 그래서 규약 47 의 구간이 없다(사전등록 ⓪-가)",
        "🔴 채점기·측정 대상 무접촉": ("ingest/doc_select.py · ingest/calendar_features.py · ident901.py · "
                            "ident902.py · inv901.py · pairboot.py · quote901.py 를 한 글자도 안 고쳤다. "
                            "⚠ doc_select.py 전문과 calendar_features.py:59-70 을 **읽었다**(사전등록 §0)"),
        "🔴 자를 뗐다(⓪-가)": "판 ρ 를 안 썼다. 대신 쓴 자: 원천 레코드 수 · 문서 건수 · is_pre_open 반환값 · 제목 날짜 가독 여부",
        "🔴 헤드라인 분모": "팝업 D1 380(레코드)과 그 레코드의 문서 전량. 🔴 짝 수(22·14)와 절대 안 잇는다(조항 60)",
        "코드 sha256": {"runners/gate907.py": sha(Path(__file__)),
                     "ingest/doc_select.py": sha(ROOT / "ingest/doc_select.py"),
                     "ingest/calendar_features.py": sha(ROOT / "ingest/calendar_features.py")},
        "입력 sha256": {"docs/prereg_907_docgate.md": sha(PREREG_MD),
                     "data/lab/denominator.json": sha(LEDGER),
                     "data/ingest/docs_all.json": sha(DOCSALL)},
    }

    # ── ⓪ 입력 원천의 꼴 ───────────────────────────────────────────
    recs = load_popup(RECDIR)
    ndocs = sum(len(r["docs"]) for r in recs)
    kinds = Counter(d.get("kind") for r in recs for d in r["docs"])
    dkeys = Counter(tuple(sorted(d.keys())) for r in recs for d in r["docs"])
    labeled = {r["record_id"] for r in recs if isinstance((r.get("intervention") or {}).get("attributes"), dict)}
    da = json.loads(DOCSALL.read_text())
    src = {
        "🔴 무엇인가": "입력이 산출물이 아니라 **원천 디렉터리**다 — 그래서 꼴을 전량 찍는다(사전등록 §3-기계)",
        "원천 경로": "data/records/*.json",
        "🔴 팝업 원천 레코드 수(D1 · 분모)": len(recs),
        "🔴 문서 건수(분모)": ndocs,
        "문서 kind 가짓수": len(kinds), "문서 kind 분포": dict(sorted(kinds.items(), key=lambda x: -x[1])),
        "문서 dict 의 키 집합 가짓수": len(dkeys),
        "문서 dict 의 키 집합 전량": {str(k): v for k, v in dkeys.items()},
        "🔴 라벨(intervention.attributes) 보유 레코드 수": len(labeled),
        "🔴 곁: data/ingest/docs_all.json 항목 수": len(da),
        "🔴 곁의 차": len(da) - ndocs,
        "⚠ 곁의 차를 판정에 안 쓴다": ("`docs_all.json` 은 원천 목록이고 레코드에 실린 것과 분모가 다르다 — "
                            "차이를 **적기만 하고 잇지 않는다**(조항 60)"),
        "통과": len(recs) > 0 and ndocs > 0,
        "⚠ 통과의 뜻": "원천을 **실제로 열었고 분모를 냈나**(조항 59 — 못 읽으면 실패)",
    }
    src["🔴 kind 분해 (합 == 분모)"] = sumcheck("문서 kind", dict(kinds), ndocs)
    out["0-가 🔴 입력 원천의 꼴 (전량)"] = src
    out["0-다 원장이 이미 뭐라 했나"] = ledger_scan()

    # ── ② 배선 검사 (측정보다 먼저) ─────────────────────────────────
    before = dict(CALLS)
    w = wiring(recs)
    out["2 배선 검사"] = w
    out["2 배선 검사"]["검사 전 계수기"] = before
    if not w["통과"]:
        out["🔴 중단"] = "배선 검사가 통과 못 했다 — 사전등록 §8 대로 측정을 안 한다"
        OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str))
        raise SystemExit("🔴 배선 검사 실패 — 측정 중단")

    # ── ③ 측정 · 팔 ㄱ ────────────────────────────────────────────
    opens = [open_of(r) for r in recs]
    base = run_pass(recs, opens)
    P, J = base["_P"], base["_j"]
    npass, n1, n2 = base["통과"], base["①"], base["②"]

    g = {
        "🔴 물음": "`is_pre_open()` 이 통과시킨 문서 전량을 세고 ① 날짜를 읽어서 / ② 날짜를 못 읽어서 / ③ 그중 사후 로 가른다",
        "🔴 분모 ① 팝업 원천 레코드(D1)": len(recs),
        "🔴 분모 ② 문서 건수": ndocs,
        "🔴 통과한 문서 수": npass,
        "🔴 ① 날짜를 읽어서 통과": n1,
        "🔴🔴 ② 날짜를 못 읽어서 통과": n2,
        "🔴 통과/불통과 분해 (합 == 분모)": sumcheck("통과/불통과", {"통과": npass, "불통과": ndocs - npass}, ndocs),
        "🔴 통과의 경로 분해 (합 == 분모)": sumcheck(
            "경로", {"A(기획서·계약서)": len(P["A"]), "B(정산·견적)": len(P["B"])}, npass),
        "🔴 ①·② 분해 (합 == 분모)": sumcheck("①/②", {"① 날짜를 읽어서": n1, "② 날짜를 못 읽어서": n2}, npass),
        "🔴 ② 의 사유 분해 (합 == 분모)": sumcheck(
            "② 사유", dict(sorted(Counter(r["통과 사유"] for r in P["②"]).items())), n2),
        "🔴 ① 의 갈래 분해 (합 == 분모)": sumcheck(
            "①", {"경로 A 에서 날짜를 읽어서": len(P["①A"]), "경로 B(정산·견적 · 정의상 전량 날짜를 읽는다)": len(P["B"])}, n1),
    }
    c3 = Counter(x["사후 판정"]["판정"] for x in J)
    g["🔴🔴 ③ ② 안의 사후/사전/모른다 (합 == 분모)"] = sumcheck(
        "③", {"사후": c3.get("사후", 0), "사전": c3.get("사전", 0), "모른다": c3.get("모른다", 0)}, n2)
    g["🔴🔴 ③ 파일명만으로 사후"] = c3.get("사후", 0)
    g["🔴 ③ 의 근거 분해 (합 == 분모)"] = sumcheck(
        "③ 근거", dict(sorted(Counter(x["사후 판정"]["근거"] for x in J).items())), n2)
    g["🔴 ② 안에서 확장 파서로 날짜가 읽힌 수"] = base["확장 날짜가 읽힌 ②"]
    g["🔴 본문을 안 읽었다"] = ("⓪-나 — 문서 본문은 Drive 에 있고 저장소에 없다. **안 읽었다**(「없다」가 아니다). "
                     "그래서 ③ 은 **파일명 기반 하한**이다")
    g["🔴 ② 를 레코드로 되짚기 (합 == 분모)"] = sumcheck(
        "② 를 가진 레코드", {"② 를 1건 이상 가진 레코드": len({r["record_id"] for r in P["②"]}),
                     "② 가 0 건인 레코드": len(recs) - len({r["record_id"] for r in P["②"]})}, len(recs))
    g["🔴 ② 상위 20건 (record_id, doc_id 병기 — 식별자를 안 버린다)"] = [
        {"record_id": x["record_id"], "doc_id": x["doc_id"], "kind": x["kind"],
         "제목": x["제목"][:70], "open_from": x["open_from"],
         "사후 판정": x["사후 판정"]["판정"], "근거": x["사후 판정"]["근거"]}
        for x in J[:20]]
    g["🔴 ③ 사후로 판정된 것 전량 (record_id, doc_id 병기)"] = [
        {"record_id": x["record_id"], "doc_id": x["doc_id"], "kind": x["kind"],
         "제목": x["제목"][:70], "open_from": x["open_from"], "근거": x["사후 판정"]["근거"],
         "확장 날짜 최소": x["사후 판정"]["확장 날짜 최소"]}
        for x in J if x["사후 판정"]["판정"] == "사후"]
    ripu = [x for x in J if x["record_id"] == "RIPU2604"]
    g["🔴 티처 #69 가 든 사례 RIPU2604 는 어디에 있나"] = (
        [{"doc_id": x["doc_id"], "제목": x["제목"][:70], "사후 판정": x["사후 판정"]["판정"],
          "근거": x["사후 판정"]["근거"]} for x in ripu]
        or "🔴 RIPU2604 의 문서가 ② 에 없다(「그런 레코드가 없다」와 다르다 — 조항 59)")
    g["통과"] = True
    g["⚠ 통과의 뜻"] = "🔴 「② 가 0 이냐」가 아니다 — **모든 분해가 「합 == 분모」 단언을 통과했나**(이슈 #158 처방 2)"
    out["3-가 팔 ㄱ · is_pre_open() 이 통과시킨 문서 전량 (원천 레코드로 셌다)"] = g

    # ── ③ 측정 · 팔 ㄴ ────────────────────────────────────────────
    br = backref(recs, BACKREF_L)
    M = br["matched"]
    excl = [r for r in M if not r["통과"]]
    excl_lab = [r for r in excl if r["record_id"] in labeled]
    h = {
        "🔴 물음": "레코드가 「완독했다」고 적어 둔 문서는 그 문을 지났는가",
        "🔴 분모 ① 팝업 원천 레코드(D1)": len(recs),
        "🔴 분모 ② 완독 표기가 있는 레코드": len(recs) - br["표기 없음 레코드"],
        "🔴 분모 ③ 완독 표기 건수 합": br["표기 합"],
        "🔴 되짚힌 문서 수": len(M),
        "🔴 못 되짚은 수(=「배제 안 됐다」가 아니라 「모른다」 · 조항 59)": br["표기 합"] - len(M),
        "🔴 되짚기 분해 (합 == 분모)": sumcheck(
            "되짚기", {"되짚힌 수": len(M), "🔴 못 되짚은 수(모른다)": br["표기 합"] - len(M)}, br["표기 합"]),
        "🔴 표기 분해 (합 == 분모)": sumcheck(
            "완독 표기", {"표기 있는 레코드": len(recs) - br["표기 없음 레코드"],
                    "표기 없는 레코드": br["표기 없음 레코드"]}, len(recs)),
        "🔴🔴 되짚힌 것 중 is_pre_open() 이 배제하는 수": len(excl),
        "🔴 되짚힌 것의 통과/배제 분해 (합 == 분모)": sumcheck(
            "완독·통과", {"통과": len(M) - len(excl), "🔴 배제": len(excl)}, len(M)),
        "🔴 배제 사유 분해 (합 == 분모)": sumcheck(
            "배제 사유", dict(sorted(Counter(r["통과 사유"] for r in excl).items())), len(excl)),
        "🔴 배제 사유가 POST_PAT 이 아닌 수": sum(1 for r in excl if r["통과 사유"] != "POST_PAT 에 걸렸다"),
        "🔴🔴 그중 라벨(intervention.attributes) 보유 레코드에서": len(excl_lab),
        "🔴 라벨 보유 레코드 수(분모)": len(labeled),
        "🔴 배제된 완독 문서 상위 20건 (record_id, doc_id 병기)": [
            {"record_id": r["record_id"], "doc_id": r["doc_id"], "kind": r["kind"],
             "제목": r["제목"][:70], "사유": r["통과 사유"], "라벨 보유": r["record_id"] in labeled}
            for r in excl[:20]],
        "🔴 되짚기 자의 민감도(접두사 길이를 바꿔 다시 잰다)": {
            f"L={l}": {"되짚힌 수": len(backref(recs, l)["matched"]),
                       "배제 수": sum(1 for r in backref(recs, l)["matched"] if not r["통과"])}
            for l in BACKREF_ALT},
        "🔴 왜 이 팔이 정의에서 유도되지 않나": (
            "`is_pre_open()` 도 `select()` 도 **완독 명단에 무엇이 실릴지 결정하지 않는다** — "
            "명단은 다른 시각에 돈 다른 프로그램(`provenance.extracted_by`)이 남긴 기록이고 "
            "교집합이 0 인 세계와 양수인 세계가 둘 다 가능하다. "
            "🔴 `ingest/doc_select.py` 는 커밋이 **1개**뿐이라 이력으로도 못 때운다. "
            "🔴 유도되는 조각 하나(「하나 이상 있다」)는 사전등록 §0 ⑦ 에서 이미 봤으므로 **예측에서 뺐다**"),
        "통과": True,
        "⚠ 통과의 뜻": "🔴 모든 분해가 「합 == 분모」 단언을 통과했나",
    }
    out["3-나 팔 ㄴ · 완독 명단은 그 문을 지났는가 (`provenance.notes` — 어느 러너도 읽은 적 없다)"] = h

    # ── ④ 순열 selectivity + 예측 판정 ────────────────────────────
    PS = perms(opens, PERM_N, PERM_SEED)
    keys = ("통과", "①", "②", "③ 사후", "사전", "모른다")
    acc = {k: [] for k in keys}
    for p in PS:
        r = run_pass(recs, p)
        for k in keys:
            acc[k].append(r[k])
    sel = {}
    for k in keys:
        v = acc[k]
        mu = sum(v) / len(v)
        sel[k] = {"관측": base[k], "🔴 순열 평균": round(mu, 4),
                  "🔴 selectivity(관측 − 순열 평균)": round(base[k] - mu, 4),
                  "순열 최소": min(v), "순열 최대": max(v),
                  "🔴 순열에서 관측과 같은 값이 나온 비율": round(sum(1 for x in v if x == base[k]) / len(v), 4)}
    out["4-가 🔴 순열 selectivity (티처 #69 의 메타 발견 — 러너가 자동으로 낸다)"] = {
        "🔴 무엇인가": ("「라벨을 무작위로 섞어도 같은 답이 나오나」의 이 팔에서의 대응물. "
                   "🔴 **등급 라벨을 아예 안 쓰므로 등급 순열은 「해당 없음」이다** — 그러나 그 검사가 묻는 것은 "
                   "「이 수가 자료를 재는가, 추정기의 모양을 재는가」이고, 이 팔에서 그 역할을 하는 "
                   "자료의 축은 **`open_from`(오픈일)** 이다. 그래서 그것을 레코드 사이에서 섞는다"),
        "🔴 순열 횟수(분모)": PERM_N, "씨앗": PERM_SEED,
        "항목": sel,
        "🔴 사전등록이 미리 적은 예상": ("② 의 selectivity ≈ 0 — ② 의 정의가 `open_from` 을 안 본다. "
                            "🔴 **그 불변성이 결함이 아니라 이 팔의 발견 자체다**(사전등록 §1·§4)"),
        "통과": True,
        "⚠ 통과의 뜻": "🔴 순열을 실제로 돌렸나(항등이 아닌 순열을 `perms` 의 M2 가 강제한다)",
    }

    def P1_eval(st):
        return st["②"] >= 1

    def P2_eval(st):
        return st["③ 사후"] >= 1

    def P3_eval(st):
        return st["확장 날짜가 읽힌 ②"] >= 1

    def P0_eval(st):
        return st["통과"] >= 0

    def strip_dates(rs):
        out2 = []
        for r in rs:
            r2 = copy.deepcopy(r)
            for d in r2["docs"]:
                if d.get("kind") in PRE_KINDS:
                    d["title"] = "20240101_" + (d.get("title") or "")
            out2.append(r2)
        return out2

    def kill_post(rs):
        out2 = []
        for r in rs:
            r2 = copy.deepcopy(r)
            for d in r2["docs"]:
                t = d.get("title") or ""
                t = POSTWORD.sub("○○", t)
                for _nm, pat in EXT_PATS:
                    t = pat.sub("○", t)
                d["title"] = t
            out2.append(r2)
        return out2

    def kill_ext(rs):
        out2 = []
        for r in rs:
            r2 = copy.deepcopy(r)
            for d in r2["docs"]:
                d["title"] = re.sub(r"[-./년월일]", "", d.get("title") or "")
            out2.append(r2)
        return out2

    PRED_A = [
        ("P1", "② 날짜를 못 읽어서 통과한 문서가 1건 이상이다", "② 가 0 이면 반증",
         P1_eval, strip_dates, "모든 기획서·계약서 제목 앞에 `20240101_` 을 붙였다",
         "🔴 모른다 — 통과 문서의 제목 날짜 가독률을 안 봤다", True),
        ("P2", "③ ② 안에서 파일명만으로 사후로 판정되는 문서가 1건 이상이다", "③ 이 0 이면 반증",
         P2_eval, kill_post, "제목에서 사후 어휘와 확장 날짜 6꼴을 전부 지웠다",
         "🔴 모른다 — ②의 사후/사전/모른다 분해를 안 봤다", True),
        ("P3", "② 안에 확장 파서로는 날짜가 읽히는 문서가 1건 이상이다", "0 이면 반증",
         P3_eval, kill_ext, "제목에서 하이픈·점·「년월일」을 전부 지웠다",
         "🔴 모른다 — 확장 파서의 수확률을 안 봤다", True),
        ("🔴 P0(장치 시험 · 예측 아님 · 명부에 안 센다)", "통과 문서 수가 0 이상이다",
         "반증 불가능하다 — 장치가 이것을 명부에서 빼야 한다",
         P0_eval, kill_post, "제목에서 사후 어휘와 확장 날짜를 전부 지웠다",
         "🔴 반증 불가능(설계상)", False),
    ]
    per = {}
    for pid, sent, fals, ev, bk, plant, prior, counted in PRED_A:
        b = ev(base)
        st2 = run_pass(bk(recs), opens)
        bro = ev(st2)
        sens = not bool(bro)
        per[pid] = {"예측": sent, "반증 조건": fals,
                    "🔴 실측 판정": "확인" if b else "🔴 반증",
                    "🔴 심은 반증 입력": plant,
                    "🔴 심은 뒤 판정": "확인(안 뒤집혔다)" if bro else "반증(뒤집혔다)",
                    "🔴 반증 입력에서 평가기가 반증을 냈나(=반증 가능한가)": sens,
                    "🔴 명부 등재": bool(counted and sens),
                    "🔴 명부에서 빠진 사유": ("" if (counted and sens) else
                                      ("🔴 심은 반증 입력에서도 평가기가 「확인」을 냈다 — 반증 불가능하다"
                                       if not sens else "장치 시험이라 애초에 안 센다")),
                    "🔴 사전 난이도": prior}

    def P4_eval(rs):
        b = backref(rs, BACKREF_L)
        lab = {r["record_id"] for r in rs
               if isinstance((r.get("intervention") or {}).get("attributes"), dict)}
        return sum(1 for r in b["matched"] if not r["통과"] and r["record_id"] in lab) >= 1

    def P5_eval(rs):
        b = backref(rs, BACKREF_L)
        return sum(1 for r in b["matched"]
                   if not r["통과"] and r["통과 사유"] != "POST_PAT 에 걸렸다") >= 1

    def kill_labnotes(rs):
        out2 = []
        for r in rs:
            r2 = copy.deepcopy(r)
            if isinstance((r2.get("intervention") or {}).get("attributes"), dict):
                r2.setdefault("provenance", {})["notes"] = ""
            out2.append(r2)
        return out2

    def make_all_post(rs):
        out2 = []
        for r in rs:
            r2 = copy.deepcopy(r)
            for d in r2["docs"]:
                d["kind"] = "기획서"
                d["title"] = POSTWORD.sub("○○", d.get("title") or "")
            out2.append(r2)
        return out2

    for pid, sent, fals, ev, bk, plant, prior in [
        ("P4", "완독 명단에서 되짚힌 문서 중 is_pre_open()=False 인 것이 라벨 보유 레코드 안에도 1건 이상 있다",
         "0 이면 반증", P4_eval, kill_labnotes, "라벨 보유 레코드의 완독 명단을 전부 지웠다",
         "🔴 모른다 — 사전등록 §0 ⑦ 이 본 레코드는 라벨이 없는 레코드였다"),
        ("P5", "완독 명단의 배제 사유 분해에서 POST_PAT 이 아닌 사유가 1건 이상이다",
         "0 이면 반증", P5_eval, make_all_post,
         "배제된 완독 문서의 kind 를 전부 기획서로 바꾸고 사후 어휘를 지웠다",
         "⚠ 높다(확인될 가능성이 크다) — 문서의 절반 이상이 문 밖 kind 다. 약한 예측임을 미리 신고했다"),
    ]:
        b = ev(recs)
        bro = ev(bk(recs))
        sens = not bool(bro)
        per[pid] = {"예측": sent, "반증 조건": fals,
                    "🔴 실측 판정": "확인" if b else "🔴 반증",
                    "🔴 심은 반증 입력": plant,
                    "🔴 심은 뒤 판정": "확인(안 뒤집혔다)" if bro else "반증(뒤집혔다)",
                    "🔴 반증 입력에서 평가기가 반증을 냈나(=반증 가능한가)": sens,
                    "🔴 명부 등재": bool(sens),
                    "🔴 명부에서 빠진 사유": "" if sens else "🔴 심은 반증 입력에서도 「확인」을 냈다 — 반증 불가능하다",
                    "🔴 사전 난이도": prior}

    listed = [k for k, v in per.items() if v["🔴 명부 등재"]]
    conf = [k for k in listed if per[k]["🔴 실측 판정"] == "확인"]
    out["4-나 예측 판정 (🔴 예측마다 반증 입력을 심었다)"] = {
        "🔴 규약": "심어서 판정이 안 뒤집히면 그 예측은 **명부에서 자동으로 빠진다**",
        "항목": per,
        "🔴 심은 반증 입력 수(분모)": len(per),
        "🔴 반증 가능한 것으로 확인된 수": sum(
            1 for v in per.values() if v["🔴 반증 입력에서 평가기가 반증을 냈나(=반증 가능한가)"]),
        "🔴 명부에 남은 예측 수": len(listed), "🔴 명부에 남은 예측": listed,
        "🔴 그중 확인": len(conf), "🔴 그중 반증": len(listed) - len(conf),
        "🔴 장치가 실제로 뺀 것": [k for k, v in per.items() if not v["🔴 명부 등재"]],
        "🔴 예측 회계 (합 == 분모)": sumcheck(
            "예측", {"명부에 남은 수": len(listed), "장치가 뺀 수": len(per) - len(listed)}, len(per)),
        "통과": all(v["🔴 반증 입력에서 평가기가 반증을 냈나(=반증 가능한가)"] for k, v in per.items() if k in listed),
        "⚠ 통과의 뜻": "🔴 예측이 맞았냐가 아니다 — **명부에 남은 예측이 전부 반증 가능한가**다",
    }

    # ── ⑤ 판정 (사전등록 §6 어법 그대로) ────────────────────────────
    R, DOC, PASS, D2 = len(recs), ndocs, npass, n2
    D3, PRE, UNK = c3.get("사후", 0), c3.get("사전", 0), c3.get("모른다", 0)
    if D2 == 0:
        vA = (f"🔴 구멍은 있으나 안 샌다 — 팝업 원천 {R}레코드의 문서 {DOC}건 중 `is_pre_open()` 이 "
              f"통과시킨 것은 {PASS}건이고, 그 전부가 날짜를 읽어서 통과했다(날짜를 못 읽어서 통과한 것 {D2}건). "
              "주석이 적어 둔 구멍은 코드에 실재하지만 이 자료에서는 한 건도 그 경로로 안 지나간다. "
              "그러므로 `is_pre_open()` 을 근거로 삼은 식3 판정은 이 자료에 관한 한 시간 마스크가 "
              "실제로 작동한 결과다")
        갈래A, headA = "㉠", "### 팔 ㄱ — 갈래 ㉠ (② == 0)"
    elif D3 == 0:
        vA = (f"🔴 문은 샌다. 다만 파일명만으로는 사후가 안 잡힌다 — 통과 {PASS}건 중 {D2}건이 "
              f"날짜를 못 읽어서 통과했고(팝업 원천 {R}레코드 · 문서 {DOC}건), 그중 파일명에서 사후로 "
              f"판정되는 것은 {D3}건이다. 즉 그 {D2}건은 시간 검사를 한 번도 안 받은 채 통과했고, "
              f"무엇인지는 모른다 — 사후 {D3} · 사전 {PRE} · 🔴 모른다 {UNK}. "
              f"🔴 본문을 안 읽었으므로 이 {D3} 은 「사후가 이만큼이다」가 아니라 "
              "「파일명만으로도 이만큼이다」의 하한이다")
        갈래A, headA = "㉡", "### 팔 ㄱ — 갈래 ㉡ (② > 0 이고 ③ == 0)"
    else:
        vA = (f"🔴 문은 새고, 새는 것 중에 사후 문서가 있다 — 팝업 원천 {R}레코드의 문서 {DOC}건 중 "
              f"`is_pre_open()` 이 {PASS}건을 통과시켰고 그중 {D2}건은 날짜를 못 읽어서 통과했으며, "
              f"파일명만으로도 {D3}건이 사후다. 그 {D2}건은 시간 검사를 한 번도 안 받았다 — "
              f"사후 {D3} · 사전 {PRE} · 🔴 모른다 {UNK}. "
              "🔴 그러므로 「코드 강제 시간 마스크」라는 식3 근거는 이 경로에 관한 한 이름이다. "
              f"🔴 본문을 안 읽었으므로 {D3} 은 하한이다")
        갈래A, headA = "㉢", "### 팔 ㄱ — 갈래 ㉢ (② > 0 이고 ③ > 0)"

    M_, X_, XL_ = len(M), len(excl), len(excl_lab)
    MISS = br["표기 합"] - len(M)
    if X_ == 0:
        vB = (f"🔴 레코드가 읽었다고 적어 둔 문서는 전부 그 문을 지난다 — 완독 명단에서 되짚힌 {M_}건 중 "
              f"`is_pre_open()` 이 배제하는 것은 {X_}건이다. "
              "그러므로 문의 통과 여부는 라벨이 실제로 선 바닥과 어긋나지 않는다")
        갈래B, headB = "㉠", "### 팔 ㄴ — 갈래 ㉠ (배제 문서를 읽은 완독 건수 == 0)"
    else:
        vB = (f"🔴 문이 막는 문서를 레코드는 읽었다 — 완독 명단에서 되짚힌 {M_}건 중 {X_}건을 "
              f"`is_pre_open()` 이 배제한다(라벨 보유 레코드 안에서 {XL_}건). "
              "그러므로 팔 ㄱ 이 문의 누수를 0 으로 재더라도 그것만으로는 라벨의 사전성이 안 선다 — "
              "문이 길목에 없던 자리가 있다. "
              f"🔴 되짚기에 실패한 {MISS}건은 「배제 안 됐다」가 아니라 「모른다」다(조항 59)")
        갈래B, headB = "㉡", "### 팔 ㄴ — 갈래 ㉡ (> 0)"

    wa, wb = check_wording(vA, headA), check_wording(vB, headB)
    out["5 판정"] = {
        "팔 ㄱ 갈래": 갈래A, "팔 ㄱ 판정문": vA,
        "팔 ㄴ 갈래": 갈래B, "팔 ㄴ 판정문": vB,
        "🔴 사전등록 §6 뼈대와 기계 대조(팔 ㄱ)": wa,
        "🔴 사전등록 §6 뼈대와 기계 대조(팔 ㄴ)": wb,
        "🔴 커밋 제목에 그대로 쓸 문장": vA.split(". ")[0],
        "통과": bool(wa.get("🔴 순서대로 다 들어 있나") and wb.get("🔴 순서대로 다 들어 있나")),
        "⚠ 통과의 뜻": "판정문이 **사전등록 §6 의 뼈대를 순서대로 다 담았나**(어법은 측정 전에 얼어붙었다)",
    }

    out["0-나 🔴 오늘 낼 판정문의 수를 입력에서 되찾기"] = already_there(
        [vA, vB], {"runners/out906_grade.json": ROOT / "runners/out906_grade.json",
                   "runners/out902_identify.json": ROOT / "runners/out902_identify.json",
                   "data/lab/denominator.json": LEDGER})

    out["6 못 잰 것 (🔴 「없다」가 아니다)"] = [
        "🔴 문서 **본문** — 안 읽었다. Drive 에 있고 저장소에 없다(⓪-나). 그래서 ③ 은 파일명 기반 **하한**이다",
        "🔴 ② 안 「모른다」로 남은 문서가 실제로 사전인지 사후인지 — **모른다**(조항 59 · 본문이 있어야 갈린다)",
        "🔴 완독 명단에서 **못 되짚은** 건 — 「배제 안 됐다」가 아니라 **「모른다」**다(명단이 제목을 자른다)",
        "🔴 `is_pre_open()` 을 통과한 문서 중 `select()` 가 **실제로 프롬프트에 실은** 것 — 안 쟀다"
        "(`select()` 는 kind 별 상한과 cap 10 으로 또 자른다)",
        "🔴 T1 잔여 22짝·팝업 14짝과 이 사이클의 수의 관계 — **안 이었다**(분모가 다르다 · 조항 60). "
        "「관계가 없다」가 아니라 **「이 사이클이 안 이었다」**다",
        "이슈 #158 처방 1(`grade906.py:lodo()` 가 짝을 (도메인, 열) 로) — 🔴 **안 했다**"
        "(사전등록 §2 에 이유를 적었다 — 남의 사이클 러너를 고치면 906 산출물이 재현 불능이 된다)",
        "KOSTAT 격자 생활인구 — 🔴 **안 받았다**(「없다」가 아니다 · ⓪-나)",
        "구간 — 안 만들었다(⓪-가 에 미리 못 박았다 · 규약 47 해당 없음 · 전수 계수라 표본이 아니다)",
        "🔴 이 세션은 **탐색 팔을 안 띄웠다**(⓪-다) — 「없다」가 아니다",
    ]
    out["🔴 계수기(생산 함수 진입 총계)"] = dict(CALLS)
    out["끝 시각"] = dt.datetime.now().isoformat(timespec="seconds")
    out["초"] = round(time.time() - T0, 3)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str))
    print("완료 →", OUT)
    print("배선", w["발화"], "/", w["🔴 분모(심은 결함 수)"], "· 코드검사", w["🔴 코드의 검사 수(분모)"],
          "· ㉱", w["🔴 ㉱ 국소 열 검정력 > 0 인 검사 수"], "/", w["🔴 ㉱ 국소 열 검정력을 잰 검사 수(분모)"],
          "· 통과", w["통과"])
    print("레코드", R, "· 문서", DOC, "· 통과", PASS, "· ①", n1, "· ②", D2,
          "· 사후", D3, "· 사전", PRE, "· 모른다", UNK)
    print("팔 ㄴ 되짚힘", M_, "· 배제", X_, "· 라벨보유 안", XL_, "· 못되짚음", MISS)
    print("명부", out["4-나 예측 판정 (🔴 예측마다 반증 입력을 심었다)"]["🔴 명부에 남은 예측"])


if __name__ == "__main__":
    main()
