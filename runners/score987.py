#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""987 채점 — 🔴 반증조건 **19** · 예측 **6** · 규칙 D 대상 **여섯**(+ 🔴 **한글 수사 갈래**).

🔴 **986 과 다른 것 넷(사전등록이 측정 전에 박았다):**

1. 🔴🔴 **`[수리] R3` --- 규칙 D 에 «한글 수사» 갈래를 붙인다**(§K).
   **「985 의 「다섯」 문서」의 잰 값이 `3` 인데 `NUMPAT` 이 아라비아 숫자만 봐서
   원리상 안 보였다.** 978 이 만든 `ledger.KNUMPAT`·`KOR_NUM` 을 여섯 대상 «전량»에 문다.
2. 🔴🔴 **`[수리] R5` --- 반증조건 8 의 바늘을 «이 사이클 산출물에서 자동 생성»한다.**
   `score986.py:473` 은 **985 의 두 리터럴만 grep** 해서 **986 자신의 수를 원리상 못 봤다.**
3. 🔴🔴🔴 **반증조건 넷 신설** --- 16 「전」을 디스크에서 읽었나 · 17 사전등록 정본이
   바뀌었나 · 18 대상이 줄어 초록이 됐는데 안 밝혔나 · 19 자기 논지를 자기가 어겼나.
4. **`certify` 칸이 일곱**이다(사전등록 §3-3).

씀:
    python3 runners/score987.py --stage score --ref <sha> --prereg-commit <sha> …
"""
import argparse
import collections
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import cycle987 as CY                                  # noqa: E402
import ledger as LG                                    # noqa: E402
import score985 as S5                                  # noqa: E402

SELF_DEP = ("채.반증분자모", "채.반증분모", "채.반증된", "채.반증통과",
            "채.예측분자모", "채.예측분자", "채.예측통과", "채.최상위통과")

OUT = "runners/out987_score.json"
PREREG = "docs/prereg_987_ceiling_identity_fixed_ref.md"
BODY = ("docs/판정_987.md", "docs/card_987.md", "docs/handoff_987.md")
PR_BODY = "docs/pr_987.md"
GOAL = "docs/목표.md"
DEN = "data/lab/denominator.json"
TBL = "runners/out987_table.json"
CARD_OUT = os.path.expanduser(
    "~/.claude/projects/-Users-ax-world-model/memory/project-lab-state.md")
MARK_A = S5.MARK_A
MARK_B = S5.MARK_B
LEDGER_KEY = "노트 987"
PR_MARK = "<!-- 987:pr:생성물 -->"

FEED_RE = re.compile(
    r"`?((?:runners/)?(?:out987_[a-z0-9_]+|fiveprime_987[a-z0-9_]*)\.json)`?")
FEED_EXEMPT = re.compile(r"fiveprime_987")

SHAPE_RE = S5.SHAPE_RE
SHAPE_OK = S5.SHAPE_OK
SHAPE_WIN = S5.SHAPE_WIN

DEN_FALSIFY = re.compile(r"##\s*§6\s*반증조건\s*\(분모\s*\*\*(\d+)\*\*")
DEN_PREDICT = re.compile(r"##\s*§5\s*예측\s*\(분모\s*\*\*(\d+)\*\*")
DEN_FIVE = re.compile(r"`⑤′`\s*분모\s*—\s*🔴\s*\*\*등록\s*(\d+)")
DEN_RULED = re.compile(r"규칙 D 대상 수\s*\|\s*\*\*(\d+)\*\*")
DEN_CERT = re.compile(r"`certify`\s*칸 수\s*\|\s*\*\*(\d+)\*\*")

INHERIT = S5.INHERIT

#: 🔴🔴🔴 **`[수리] R3` --- 한글 수사의 «앞말 바늘»**.
#:  바늘이 걸린 자리의 수사는 **치환표의 그 칸 값**과 같아야 한다.
#:  🔴 **바늘을 이름으로 여기 박고 산출물에 싣는다**(조항 60).
KOR_NEEDLES = collections.OrderedDict([
    ("985 문서 수", (re.compile(r"985\s*(?:의)?[\s*]*$"), "전.986문서수")),
    ("규칙 D 대상 수", (re.compile(r"규칙\s*D\s*(?:의)?\s*(?:대상)?[\s*]*$"), "채.규칙D분모")),
])


def _git(*a):
    return subprocess.check_output(["git"] + list(a), cwd=str(ROOT)).decode("utf-8")


def _text(rel):
    """🔴 **「지금」 읽기다** --- 규칙 D 채점은 디스크의 «지금» 문서를 봐야 한다.

    🔴 **사전등록 §3-1-가 가 이 파일을 AST 자에서 «등록 면제»로 박았다**(조용히 안 뺐다).
    「전」 값은 이 함수를 안 지나간다 --- `cycle987.before()` 만 지나간다.
    """
    p = ROOT / rel
    return p.read_text(encoding="utf-8") if p.is_file() else None


def _load(name, must=False):
    p = ROOT / ("runners/" + name if not name.startswith("runners/") else name)
    if not p.is_file():
        if must:
            raise SystemExit("🔴 없다: %s" % p)
        return None
    return json.loads(p.read_text(encoding="utf-8"),
                      object_pairs_hook=collections.OrderedDict)


def _sha(rel):
    return CY.sha_file(rel)


def _dig(obj, *keys):
    cur = obj
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def registered_denominators():
    t = _text(PREREG) or ""

    def _g(rx):
        m = rx.search(t)
        return int(m.group(1)) if m else None
    return collections.OrderedDict([
        ("🔴 반증조건 분모(사전등록에서 «읽었다»)", _g(DEN_FALSIFY)),
        ("🔴 예측 분모", _g(DEN_PREDICT)),
        ("🔴 `⑤′` 분모", _g(DEN_FIVE)),
        ("🔴 규칙 D 대상 수", _g(DEN_RULED)),
        ("🔴 `certify` 칸 수", _g(DEN_CERT)),
    ])


def _cells(tb):
    t = (tb or {}).get("🔴🔴 치환표") or {}
    return t.get("🔴 칸", t) if isinstance(t, dict) else {}


def _holdout_slice():
    t = _text(GOAL)
    if t is None or MARK_A not in t or MARK_B not in t:
        return None
    i, j = t.index(MARK_A), t.index(MARK_B) + len(MARK_B)
    return t[i:j]


def _ledger_entry_text(key=LEDGER_KEY):
    q = ROOT / DEN
    if not q.is_file():
        return None
    d = json.loads(q.read_text(encoding="utf-8"))
    if key not in d:
        return None
    return json.dumps(d[key], ensure_ascii=False, indent=1)


def _targets():
    t = collections.OrderedDict()
    for p in BODY:
        t[p] = _text(p)
    t["🔴 `docs/목표.md` 「정본 유보」 절"] = _holdout_slice()
    t["🔴 원장 `%s` 항목" % LEDGER_KEY] = _ledger_entry_text()
    t["🔴 PR 본문 `%s`" % PR_BODY] = _text(PR_BODY)
    return t


def rule_d(tb, rules):
    S = S5._table_set(tb)
    rows, tot = collections.OrderedDict(), 0
    targets = _targets()
    for name, txt in targets.items():
        if txt is None:
            rows[name] = {"🔴": "🔴 못 읽었다 --- 「표 밖 0」이 아니다(조항 59)", "표 밖": None}
            continue
        n, ex = S5._outside(txt, S, rules)
        rows[name] = {"표 밖": n, "보기": ex or "없음", "글자 수": len(txt)}
        tot += n
    unread = [k for k, v in rows.items() if v.get("표 밖") is None]
    T = _cells(tb) or {}
    return collections.OrderedDict([
        ("🔴 무엇", "🔴 **규칙 D(아라비아) --- 치환표에 없는 수를 본문에 못 쓴다**"),
        ("🔴🔴 채점 분모", len(targets)),
        ("🔴🔴 분모의 내력(조항 60)", {"985 판": 5, "986 판": 6, "987 판": len(targets),
                              "🔴 987 이 더한 것": "🔴 **대상이 아니라 «갈래»를 더했다** --- "
                                            "§K 의 한글 수사"}),
        ("🔴 대상", list(targets.keys())),
        ("🔴 대상별", rows),
        ("🔴🔴 표 밖 합", tot),
        ("🔴 못 읽은 대상", unread or "없음"),
        ("🔴 치환표 칸 수", len(T)),
        ("🔴 치환표 sha256", (tb or {}).get("🔴🔴 표 sha256")),
        ("통과", bool(tot == 0 and not unread)),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **여섯 대상 전부에서 치환표 밖의 «아라비아» 수가 0 인가.** "
         "🔴 **한글 수사는 §K 가 따로 진다**"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §K 🔴🔴 `[수리] R3` --- 규칙 D 의 «한글 수사» 갈래
# ══════════════════════════════════════════════════════════════════════
def rule_d_korean(tb):
    """🔴🔴🔴 **978 이 만든 한글 수사 패턴을 규칙 D 여섯 대상 «전량»에 문다.**

    🔴 **왜 (티처 #125 3순위 ⓒ).** 986 판정문의 **「985 의 「다섯」 문서」**의 잰 값은 `3` 인데
    **네 자리가 「다섯」**이었다. `note986_gen.py:343` 의 **손 전사 한글 수사**이고
    `NUMPAT` 이 아라비아 숫자만 봐서 **원리상 안 보인다** ---
    **978 이 만든 `ledger.KNUMPAT` 이 `score986.rule_d` 에 «안 물려 있었다».**
    """
    T = _cells(tb) or {}
    S = S5._table_set(tb)
    targets = _targets()
    rows, bad, out_of_table, seen = collections.OrderedDict(), [], [], 0
    for name, txt in targets.items():
        if txt is None:
            rows[name] = {"🔴": "🔴 못 읽었다(= 「0」이 아니다 · 조항 59)"}
            continue
        code = [(m.start(), m.end()) for m in re.finditer(r"`[^`\n]*`", txt)]
        hits, exempt, tied, miss, notab = [], 0, 0, [], []
        for m in LG.KNUMPAT.finditer(txt):
            if LG.KNUM_NOT.match(txt, m.start()):
                continue
            if any(a <= m.start() and m.end() <= b for a, b in code):
                exempt += 1
                continue
            word = m.group()
            val = LG.KOR_NUM[word]
            seen += 1
            ctx = re.sub(r"\s+", " ", txt[max(0, m.start() - 30):m.end() + 20])
            head = txt[max(0, m.start() - 16):m.start()]
            hits.append(word)
            for lab, (rx, cell) in KOR_NEEDLES.items():
                if not rx.search(head):
                    continue
                tied += 1
                want = T.get(cell)
                if want is None or val != want:
                    miss.append({"바늘": lab, "수사": word, "값": val,
                                 "치환표 칸": cell, "치환표 값": want, "맥락": ctx})
            if str(val) not in S:
                notab.append({"수사": word, "값": val, "맥락": ctx})
        rows[name] = {"🔴 센 한글 수사": len(hits),
                      "🔴 면제(인라인 코드 안)": exempt,
                      "🔴 바늘이 걸린 수사": tied,
                      "🔴🔴🔴 바늘 대조에서 어긋난 것": miss or "없음",
                      "⚠ 값이 치환표 밖인 수사(진단 · 판정에 안 쓴다)": len(notab),
                      "수사별": dict(collections.Counter(hits))}
        bad += miss
        out_of_table += notab
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴🔴 **`[수리] R3` --- 규칙 D 에 «한글 수사» 패턴을 물려 "
                 "여섯 대상 «전량»에 돌린다**"),
        ("🔴 자의 출처", "🔴 **978 수리 4 가 만든 `ledger.KNUMPAT`·`ledger.KOR_NUM`** --- "
                    "986 의 `score986.rule_d` 에는 안 물려 있었다"),
        ("🔴 등록한 수사 낱말", dict(LG.KOR_NUM)),
        ("🔴 뺀 규칙(수사가 아닌 자리)", LG.KNUM_NOT.pattern),
        ("🔴🔴 등록한 앞말 바늘(이름 · 정규식 · 치환표 칸)",
         {k: {"정규식": v[0].pattern, "치환표 칸": v[1], "치환표 값": (_cells(tb) or {}).get(v[1])}
          for k, v in KOR_NEEDLES.items()}),
        ("🔴🔴 채점 분모(대상)", len(targets)),
        ("🔴🔴 센 한글 수사 수", seen),
        ("🔴 대상별", rows),
        ("🔴🔴🔴 어긋난 수사 수", len(bad)),
        ("🔴 어긋난 자리", bad or "없음"),
        ("⚠ 값이 치환표 밖인 수사(진단 · 조항 61)", len(out_of_table)),
        ("⚠ 이 자의 한계(조항 61)",
         "🔴 **판정에 쓰는 것은 «앞말 바늘»뿐이다.** 「값이 치환표 안인가」는 "
         "**작은 수가 어느 긴 표에나 있어서** 사실상 항진명제라 **진단으로만** 싣는다. "
         "🔴 곧 **등록 안 한 앞말의 한글 수사는 이 자도 원리상 못 본다**"),
        ("통과", bool(len(bad) == 0 and seen > 0)),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **① 바늘 대조에서 어긋난 수사가 0 이고 ② 분모가 0 이 아닌가.** "
         "🔴 분모가 0 이면 「안 세었다」라 불통과다(조항 59)"),
    ])


def korean_power_demo(au):
    """🔴 **검정력 시연(조항 64)** --- 같은 갈래의 자가 986 문서에서 «떨어지나»."""
    sec = (au or {}).get("§B-나 🔴🔴 986 문서의 한글 수사 「985 의 다섯 문서」") or {}
    n = sec.get("🔴🔴🔴 어긋난 수사 수(= 예측 P4 의 분자)")
    return collections.OrderedDict([
        ("🔴 무엇", "🔴 **같은 한글 수사 자를 986 의 문서(고정 ref)에 문다**"),
        ("🔴🔴🔴 986 에서 잡은 어긋난 수사 수", n),
        ("🔴 잰 값", sec.get("🔴🔴🔴 잰 값(`out986_audit §A/①`)")),
        ("🔴 문서별", sec.get("🔴 문서별")),
        ("🔴🔴 986 에서 «떨어지나»", bool(n)),
        ("통과", bool(n)),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "🔴 **986 에서 떨어지는가** --- 안 떨어지면 자가 아니다"),
    ])


def shape_audit():
    rows, bad = collections.OrderedDict(), 0
    for p in list(BODY) + [PR_BODY]:
        t = _text(p)
        if t is None:
            rows[p] = {"🔴": "🔴 못 읽었다", "근거 없는 모양 낱말": None}
            continue
        miss = []
        for m in SHAPE_RE.finditer(t):
            w = t[max(0, m.start() - SHAPE_WIN):m.end() + SHAPE_WIN]
            if not any(k in w for k in SHAPE_OK):
                miss.append(m.group())
        rows[p] = {"모양 낱말 수": len(SHAPE_RE.findall(t)),
                   "근거 없는 모양 낱말": len(miss), "보기": miss[:8] or "없음"}
        bad += len(miss)
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴 **조항 68** --- `2·SE` 를 못 넘는 칸으로 모양을 주장했나"),
        ("🔴 자", "「단조·포화·U 자·되오름」 낱말마다 ±%d 글자 안에 근거 낱말" % SHAPE_WIN),
        ("🔴 분모(문서 + PR 본문)", len(rows)),
        ("⚠ 이 자의 한계(조항 61 · 985 가 «잰» 것)",
         "🔴 **바늘에 `\"z \"` 가 있어 창 안에 `z` 하나만 있으면 통과한다** --- "
         "「그 근거가 «그 모양의» 근거인가」는 원리상 안 본다. **987 도 이 자를 안 고쳤다**"),
        ("🔴 문서별", rows),
        ("🔴🔴 근거 없는 모양 주장 수", bad),
        ("통과", bool(bad == 0 and all(
            v.get("근거 없는 모양 낱말") is not None for v in rows.values()))),
    ])


def feeds_stamp():
    cited = collections.OrderedDict()
    for p in list(BODY) + [PR_BODY]:
        t = _text(p)
        if t is None:
            continue
        for m in FEED_RE.finditer(t):
            cited.setdefault(m.group(1).split("/")[-1], []).append(p)
    ent = _ledger_entry_text() or ""
    in_ledger = sorted(set(
        re.findall(r"(?:runners/)?((?:out987|fiveprime)_?[\w]*\.json)", ent)))
    universe = sorted(set(list(cited) + in_ledger))
    rows, bad, exempt, missing = collections.OrderedDict(), [], [], []
    for nm in universe:
        if FEED_EXEMPT.search(nm):
            exempt.append(nm)
            continue
        d = _load(nm)
        st = S5._stamp(d)
        ok = bool(st and st.get("🔴 F5 통과"))
        if d is None:
            missing.append(nm)
        rows[nm] = {"인용한 문서": cited.get(nm) or "🔴 인용 안 됐다(원장에만 있다)",
                    "원장이 싣나": nm in in_ledger,
                    "F5 통과": (st or {}).get("🔴 F5 통과"), "도장이 있나": bool(st)}
        if not ok:
            bad.append(nm)
    return collections.OrderedDict([
        ("🔴 무엇", "🔴 **본문·PR 본문·원장이 «싣는» 산출물의 도장이 전부 F5 통과인가**"),
        ("🔴 분모의 내력(조항 60)",
         "🔴 **985 는 7(인용된 것) · 986 부터 「원장이 싣는 산출물 전량」** --- "
         "🔴 **즉시 정정 ①: 985 의 「7 / 13 · 피한 5」는 7+5=12 로 안 맞는데 "
         "«사전등록 면제 1» 을 안 보여서다**(7 + 1 + 5 = 13)"),
        ("🔴 인용된 산출물(기계 추출)", sorted(cited)),
        ("🔴 원장 `%s` 항목이 싣는 산출물" % LEDGER_KEY, in_ledger),
        ("🔴🔴 인용 안 됐는데 원장이 싣는 것", sorted(set(in_ledger) - set(cited)) or "없음"),
        ("🔴 분모", len(rows)),
        ("🔴🔴 사전등록이 «사전»에 뺀 것(`⑤′` 산출물)", exempt or "없음"),
        ("🔴🔴 뺀 수", len(exempt)),
        ("🔴 산출물별", rows),
        ("🔴 파일이 없는 것(= 「통과」가 아니다 · 조항 59)", missing or "없음"),
        ("🔴🔴 F5 를 못 넘은 것", bad or "없음"),
        ("통과", bool(rows and not bad)),
    ])


def six_places(needles):
    places = collections.OrderedDict()
    for p in BODY:
        places[p] = _text(p)
    places[PREREG] = _text(PREREG)
    places["원장 `%s` 항목" % LEDGER_KEY] = _ledger_entry_text()
    places["🔴 메모리 카드(저장소 «밖»)"] = (
        Path(CARD_OUT).read_text(encoding="utf-8") if Path(CARD_OUT).is_file() else None)
    rows, strict_rows, bad = collections.OrderedDict(), collections.OrderedDict(), []
    for name, txt in places.items():
        if txt is None:
            rows[name] = {"🔴": "🔴 못 읽었다(= 「같다」가 아니다)"}
            strict_rows[name] = {"🔴": "🔴 못 읽었다"}
            bad.append(name)
            continue
        r, sr = {}, {}
        for lab, (val, anchor) in needles.items():
            s = str(val)
            r[lab] = s in txt
            hit = False
            for m in re.finditer(re.escape(anchor), txt):
                w = txt[max(0, m.start() - 80):m.end() + 80]
                if s in w:
                    hit = True
                    break
            sr[lab] = hit
        rows[name] = r
        strict_rows[name] = sr
        if not all(sr.values()):
            bad.append(name)
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴 **저장소 안 넷 · 원장 · 메모리 카드 여섯이 같은 수를 적나**"),
        ("🔴 바늘", {k: v[0] for k, v in needles.items()}),
        ("🔴 닻(±80 자 창의 중심)", {k: v[1] for k, v in needles.items()}),
        ("🔴 분모(자리 수)", len(places)),
        ("⚠ 느슨한 자(부분 문자열) — 진단", rows),
        ("🔴🔴🔴 엄격 자(판정에 쓴다)", strict_rows),
        ("🔴🔴 엄격 자로 못 채우는 자리", bad or "없음"),
        ("통과", bool(not bad)),
    ])


def ast_pass_all():
    rows, tot, unread = collections.OrderedDict(), 0, []
    for rel in CY.RAN_987:
        h = S5.ast_pass_hits(rel)
        if h is None:
            rows[rel] = {"🔴": "🔴 못 읽었다"}
            unread.append(rel)
            continue
        rows[rel] = {"자리 수": len(h), "자리": h or "없음"}
        tot += len(h)
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴 **리터럴 `(\"통과\", True)` 금지**(983 R1 · AST)"),
        ("🔴 분모(이 사이클 러너 전량)", len(CY.RAN_987)),
        ("🔴 러너별", rows),
        ("🔴🔴🔴 리터럴 자리 수", tot),
        ("🔴 못 읽은 러너(= 0 이 아니다)", unread or "없음"),
        ("통과", bool(tot == 0 and not unread)),
    ])


#: 🔴 손 전사 --- **자리표시자 «또는» 산술 리터럴**(986 은 「둘 다」를 요구해 스캔이 안 됐다)
_FMT_PLACE = re.compile(r"%[-+ #0-9.]*[sdifgr]|\{[^{}]*\}")
_FMT_NUM = re.compile(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])")


def hand_lit_all():
    """🔴 **손 전사 수 리터럴** --- 🔴 **즉시 정정 ⑥: 986 의 「자리 0」은 «범위 산물»이다.**

    986 의 `_fmt_literals` 는 **「자리표시자 + 산술 리터럴」을 «둘 다»** 요구했는데
    `note986_gen.py` 의 서식은 전부 `⟦⟧` 슬롯이라 **스캔 자체가 안 됐다** ---
    `0` 은 「깨끗하다」가 아니라 **「안 봤다」**였다.
    🔴 **987 판은 「서식 문자열 안의 수 리터럴」을 «자리표시자 유무와 무관하게» 센다.**
    """
    import ast
    rows, tot, unread = collections.OrderedDict(), 0, []
    for rel in CY.RAN_987:
        src = _text(rel)
        if src is None:
            rows[rel] = {"🔴": "🔴 못 읽었다"}
            unread.append(rel)
            continue
        try:
            tree = ast.parse(src)
        except SyntaxError as e:                                    # noqa: BLE001
            rows[rel] = {"🔴": "🔴 파싱 실패: %s" % e}
            unread.append(rel)
            continue
        hits = []
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Assign)
                    and isinstance(node.value, ast.Constant)
                    and isinstance(node.value.value, (int, float))
                    and not isinstance(node.value.value, bool)):
                continue
            for t in node.targets:
                if isinstance(t, ast.Subscript):
                    hits.append({"줄": node.lineno, "꼴": "T[...] = <숫자 리터럴>"})
        rows[rel] = {"자리 수": len(hits), "자리": hits or "없음"}
        tot += len(hits)
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴 **손 전사 수 리터럴 금지** --- 분모는 «이 사이클 러너 전량»"),
        ("🔴 분모", len(CY.RAN_987)),
        ("🔴 러너별", rows),
        ("🔴🔴🔴 987 러너의 손 전사 자리 수", tot),
        ("🔴 못 읽은 러너(= 0 이 아니다)", unread or "없음"),
        ("🔴🔴 즉시 정정 ⑥ — 986 의 「자리 0」이 «범위 산물»이었다",
         "🔴 **`_fmt_literals` 가 「자리표시자 + 산술 리터럴」을 «둘 다» 요구했는데 "
         "`note986_gen.py` 의 서식 다섯은 전부 `⟦⟧` 슬롯이라 스캔 자체가 안 됐다.** "
         "🔴 0 은 「깨끗하다」가 아니라 **「안 봤다」**다(조항 59)"),
        ("통과", bool(tot == 0 and not unread)),
    ])


# ══════════════════════════════════════════════════════════════════════
# §6 반증조건 (분모 19)
# ══════════════════════════════════════════════════════════════════════
def _undecided_literals(pw):
    """🔴🔴🔴 **`[수리] R5` --- 바늘을 «이 사이클 산출물»에서 자동 생성한다.**

    `score986.py:473` 은 **985 의 두 리터럴만** grep 해서 **986 자신의 `0.13`/`0.35` 를
    원리상 못 봤다**(통과 `True`). 987 은 **「식별됐나 = False」인 칸의 점추정 값**을
    산출물에서 뽑아 그 수를 바늘로 쓴다.
    """
    out = collections.OrderedDict()
    var = _dig(pw or {}, "§2 🔴🔴🔴 팔을 다시 짓는다 — V0 · V1 · V1′ · V2",
               "🔴🔴🔴 변이체별") or {}
    for v, blocks in var.items():
        for uk, blk in (blocks or {}).items():
            ident = blk.get("🔴🔴🔴 식별됐나(🔴 `[수리] R4` — 구간 두 끝이 격자에서 «이웃한 칸»인가)")
            pt = blk.get("🔴 처음 0.5 «이상»이 되는 δ(점추정)")
            if ident is not True and pt is not None:
                out["%s/%s" % (v, uk)] = pt
    sh = _dig(pw or {}, "§4 🔴🔴 983 모양 자 — 구간으로 · 확정 / 미확정", "🔴 λ 별") or {}
    for uk, blk in sh.items():
        for cell, row in (blk.get("🔴 칸 쌍별") or {}).items():
            key = [k for k in row if k.startswith("🔴 식별됐나")]
            if key and row[key[0]] is not True and row.get("🔴 최소 검출 모양 크기(점추정)") is not None:
                out["모양/%s/%s" % (uk, cell)] = row["🔴 최소 검출 모양 크기(점추정)"]
    return out


def falsify(ctx):
    items = collections.OrderedDict()

    pc = ctx["prereg_commit"]
    try:
        blob = _git("show", "%s:%s" % (pc, PREREG)).encode("utf-8")
        was = hashlib.sha256(blob).hexdigest()
    except Exception as e:                                         # noqa: BLE001
        was = "🔴 못 읽었다: %s" % e
    cur = _sha(PREREG)
    f1 = collections.OrderedDict([
        ("🔴 사전등록 커밋(정정 포함 · 측정 «전»)", pc),
        ("🔴 그 커밋의 blob sha256", was),
        ("🔴 디스크 sha256", cur),
        ("🔴🔴 고쳤나", bool(was != cur)),
    ])
    items["1 사전등록 blob 을 측정 뒤에 고쳤나"] = (f1, f1["🔴🔴 고쳤나"])

    t = _text(PREREG) or ""
    has_sec = "막힌 명령 신고" in t
    verd = _text(BODY[0]) or ""
    declared = ("막힌 명령" in verd)
    f2 = collections.OrderedDict([
        ("🔴 사전등록에 신고 절이 있나", has_sec),
        ("🔴 판정문에 신고가 있나", declared),
        ("⚠ 이 자의 한계(조항 61)",
         "🔴 **셸 이력은 저장소에 안 남으므로 기계가 「시도 자체」를 확인·부정할 수 없다.** "
         "이 자는 **「신고 절이 있나 · 적혔나」**뿐이다 --- 정직에 기대는 조항이다"),
        ("🔴🔴🔴 신고를 안 했나", bool(not (has_sec and declared))),
    ])
    items["2 막힌 명령을 우회하고 신고 안 했나(조항 69)"] = (f2, f2["🔴🔴🔴 신고를 안 했나"])

    reg = ctx["reg"]
    got = {"반증조건": ctx["n_falsify"], "예측": ctx["n_predict"],
           "규칙 D 대상": ctx["ruleD"]["🔴🔴 채점 분모"], "certify 칸": ctx["n_cert"]}
    want = {"반증조건": reg["🔴 반증조건 분모(사전등록에서 «읽었다»)"],
            "예측": reg["🔴 예측 분모"], "규칙 D 대상": reg["🔴 규칙 D 대상 수"],
            "certify 칸": reg["🔴 `certify` 칸 수"]}
    diff = sorted(k for k in got if got[k] != want[k])
    f3 = collections.OrderedDict([
        ("🔴 사전등록이 박은 분모", want), ("🔴 채점이 쓴 분모", got),
        ("🔴 어긋난 분모", diff or "없음"), ("🔴🔴 다르게 썼나", bool(diff)),
    ])
    items["3 등록 분모와 다른 수로 채점했나(조항 60-다)"] = (f3, f3["🔴🔴 다르게 썼나"])

    fp = ctx["five"] or {}
    n_sec = fp.get("🔴 절 수(분모)")
    f4 = collections.OrderedDict([
        ("🔴 사전등록이 박은 `⑤′` 분모", reg["🔴 `⑤′` 분모"]),
        ("🔴 `⑤′` 가 쓴 절 수", n_sec),
        ("🔴 명부 밖에서 `통과` 를 든 절", fp.get("🔴🔴 명부 밖(분모를 조용히 넓히는 자리)")),
        ("🔴🔴 뺐나", bool(n_sec is not None and reg["🔴 `⑤′` 분모"] is not None
                       and n_sec < reg["🔴 `⑤′` 분모"])),
    ])
    items["4 등록한 절을 분모에서 뺐나(조항 60-나)"] = (f4, f4["🔴🔴 뺐나"])

    st = CY.stale_outputs()
    f5 = collections.OrderedDict([
        ("🔴 낡은 산출물", st["🔴🔴🔴 낡은 산출물(고치고 안 다시 돌렸다)"]),
        ("🔴 못 읽은 것", st["🔴 못 읽은 것(= 「없다」가 아니다)"]),
        ("🔴🔴 고치고 안 다시 돌렸나", bool(st["🔴🔴🔴 낡은 것이 있나"])),
    ])
    items["5 값을 낸 뒤 러너를 고치고 안 다시 돌렸나"] = (f5, f5["🔴🔴 고치고 안 다시 돌렸나"])

    sd = CY.stale_docs()
    unknown6 = sd.get("🔴🔴🔴 낡은 문서가 있나") is None
    f6 = collections.OrderedDict([
        ("🔴🔴🔴 무엇", "🔴 **`[수리] R2`: 분모가 3 → %d 다** --- 판정문이 싣는 "
                   "`house`·`prose` 의 수가 986 에선 «밖»이었다" % len(CY.DOC_INPUTS)),
        ("🔴 분모", len(CY.DOC_INPUTS)),
        ("🔴 입력별", sd.get("🔴 입력별")),
        ("🔴 문서를 찍은 뒤 달라진 산출물", sd.get("🔴🔴🔴 문서를 찍은 뒤 달라진 산출물")),
        ("🔴 치환표가 sha 를 안 박은 입력",
         sd.get("🔴 치환표가 sha 를 안 박은 입력(= 「같다」가 아니다 · 조항 59)")),
        ("🔴 명시적으로 뺀 입력과 사유", sd.get("🔴🔴 «명시적으로» 뺀 입력과 사유(조용히 안 뺀다)")),
        ("🔴🔴🔴 안 다시 찍었나(「모른다」도 반증이다 · 조항 59)",
         bool(sd.get("🔴🔴🔴 낡은 문서가 있나") or unknown6)),
    ])
    items["6 채점기를 다시 돌리고 문서를 안 다시 찍었나(분모 5 · R2)"] = \
        (f6, f6["🔴🔴🔴 안 다시 찍었나(「모른다」도 반증이다 · 조항 59)"])

    rd = ctx["ruleD"]
    pr_row = None
    for k, v in (rd.get("🔴 대상별") or {}).items():
        if PR_BODY in k:
            pr_row = v
    prtxt = _text(PR_BODY) or ""
    f7 = collections.OrderedDict([
        ("🔴 PR 본문이 규칙 D 분모 안인가", bool(pr_row is not None)),
        ("🔴 PR 본문의 「표 밖」 수", (pr_row or {}).get("표 밖")),
        ("🔴 PR 본문이 치환표에서 «지어졌나»", bool(PR_MARK in prtxt)),
        ("🔴🔴 다른가", bool(pr_row is None or pr_row.get("표 밖") != 0
                        or PR_MARK not in prtxt)),
    ])
    items["7 PR 본문이 문서와 다른가"] = (f7, f7["🔴🔴 다른가"])

    # 🔴🔴🔴 8 `[수리] R5` --- 바늘을 이 사이클 산출물에서 «자동 생성»한다
    needles = _undecided_literals(ctx["power"])
    joined = "\n".join((_text(p) or "") for p in list(BODY) + [PR_BODY])
    naked = []
    for lab, val in needles.items():
        s = ("%g" % val)
        for m in re.finditer(re.escape(s) + r"(?![\d])", joined):
            w = joined[max(0, m.start() - 220):m.end() + 220]
            if not any(x in w for x in ("구간", "미확정", "식별", "못 박")):
                naked.append({"바늘": lab, "수": s})
                break
    old = sorted(set(re.findall(r"\b6\.380994\d*\b|\b23\.06539\d*\b", joined)))
    f8 = collections.OrderedDict([
        ("🔴🔴🔴 `[수리] R5` --- 바늘을 «이 사이클 산출물에서» 만들었다", True),
        ("🔴 바늘(미식별 칸의 점추정)", needles),
        ("🔴 바늘 수", len(needles)),
        ("⚠ 구판 자(985 의 두 리터럴만 grep) 결과", old or "없음"),
        ("🔴🔴 «구간·미확정 맥락 없이» 실린 수", naked or "없음"),
        ("🔴 왜 구판이 항진명제였나",
         "🔴 **`score986.py:473` 이 985 의 두 리터럴(`6.380994`·`23.06539`)만 grep 해서 "
         "986 «자신의» `0.13`/`0.35` 를 원리상 못 봤다**(통과 `True`)"),
        ("🔴🔴🔴 못 박았나", bool(naked)),
    ])
    items["8 식별되지 않는 수를 소수점으로 못 박았나(R5 — 바늘 자동 생성)"] = \
        (f8, f8["🔴🔴🔴 못 박았나"])

    f9 = collections.OrderedDict([
        ("🔴 표 밖 합", rd["🔴🔴 표 밖 합"]), ("🔴 채점 분모", rd["🔴🔴 채점 분모"]),
        ("🔴 못 읽은 대상", rd["🔴 못 읽은 대상"]),
        ("🔴🔴 전부 치환표 칸인가", bool(rd["통과"])),
    ])
    items["9 규칙 D(아라비아) — 여섯 대상의 수가 전부 치환표 칸인가"] = \
        (f9, not f9["🔴🔴 전부 치환표 칸인가"])

    kr = ctx["korean"]
    f10 = collections.OrderedDict([
        ("🔴 센 한글 수사 수", kr["🔴🔴 센 한글 수사 수"]),
        ("🔴 어긋난 수사 수", kr["🔴🔴🔴 어긋난 수사 수"]),
        ("🔴 어긋난 자리", kr["🔴 어긋난 자리"]),
        ("🔴🔴 어긋났나", bool(not kr["통과"])),
    ])
    items["10 규칙 D(한글 수사) — 여섯 대상의 수사가 바늘과 어긋나나(R3)"] = \
        (f10, f10["🔴🔴 어긋났나"])

    sx = ctx["six"]
    items["11 여섯 자리가 같은 수를 적나(엄격 자)"] = (sx, not sx["통과"])

    live = ctx["live_cert"]
    ct = ctx["certify"] or {}
    mine = ct.get("§가 🔴🔴🔴 987 자신") or {}
    f12 = collections.OrderedDict([
        ("🔴🔴🔴 지연 없는 자(채점기가 «지금» 낸 값 대 치환표)", live),
        ("🔴🔴 뺀 칸(자기 결과에 의존한다 · 조용히 안 뺀다 · 조항 60)", list(SELF_DEP)),
        ("🔴 왜 뺐나",
         "🔴 **디스크의 `out987_certify.json` 을 읽으면 한 회 뒤진 값을 읽고 "
         "«주기 4 의 진동»이 생겨 고정점에 원리상 도달 못 한다**(986 실측). "
         "🔴 전량 검사는 `certify987` 이 그대로 한다"),
        ("⚠ 즉시 정정 ⑧(`M2`)",
         "🔴 **뺀 여덟 중 `채.반증분자모`·`채.반증된` 은 «986 의 여섯째 칸이 985 를 잡은 그 칸»이다.** "
         "🔴 곧 **사이클 «안»에서 도는 이 자는 반증 칸을 원리상 못 본다** --- "
         "사유는 적혀 있으나 그 사실은 남는다"),
        ("⚠ 디스크 `certify` 가 적은 어긋난 칸(한 회 뒤질 수 있다 · 진단)",
         mine.get("🔴🔴 어긋난 칸")),
        ("🔴🔴 수렴했나", bool(live["🔴 전부 같은가"])),
    ])
    items["12 문서 고리가 수렴했나(certify 일곱 칸 · 지연 없는 자)"] = (f12, not f12["🔴🔴 수렴했나"])

    fs = ctx["feeds"]
    items["13 인용·원장 산출물이 전부 F5 도장을 넘나"] = (fs, not fs["통과"])

    ap = ctx["astpass"]
    items["14 이 사이클 러너에 리터럴 `(\"통과\", True)` 가 있나"] = (ap, not ap["통과"])

    hl = ctx["handlit"]
    items["15 이 사이클 러너에 손 전사 수 리터럴이 있나"] = (hl, not hl["통과"])

    # 🔴🔴🔴 16 「전」 값을 «고정 ref 없이» 디스크에서 읽었나 (987 신설)
    au = ctx["audit"] or {}
    astsec = au.get("§A-나 🔴🔴 AST 자 — 디스크에서 「전」을 읽는 자리") or {}
    n_hit = astsec.get("🔴🔴🔴 면제 밖에서 걸린 자리 수(= 반증조건 16 의 분자)")
    T = _cells(ctx["table"]) or {}
    before_cells = [k for k in T if k.startswith("전.") and not k.endswith(".ref")]
    noref = []
    for k in before_cells:
        rk = k + ".ref"
        v = T.get(rk)
        if not (isinstance(v, str) and len(v) == 40
                and all(c in "0123456789abcdef" for c in v)):
            noref.append(k)
    f16 = collections.OrderedDict([
        ("🔴🔴 AST 자 — 면제 밖에서 걸린 자리 수", n_hit),
        ("🔴 등록 면제와 사유", astsec.get("🔴🔴 등록 면제와 사유(조용히 안 뺀다 · 사전등록 §3-1-가)")),
        ("🔴 검정력 시연 — 986 에서 잡은 자리 수",
         _dig(astsec, "🔴🔴 검정력 시연(조항 64) — 같은 자를 `runners/audit986.py`(고정 ref)에 문다",
              "🔴🔴🔴 잡은 자리 수")),
        ("🔴🔴 치환표의 `전.` 칸 수", len(before_cells)),
        ("🔴🔴🔴 짝 `ref` 칸이 40 자 sha 가 «아닌» 칸", noref or "없음"),
        ("🔴🔴🔴 디스크에서 읽었나", bool((n_hit or 0) > 0 or noref)),
    ])
    items["16 「전」 값을 «고정 ref 없이» 디스크에서 읽었나(987 신설)"] = \
        (f16, f16["🔴🔴🔴 디스크에서 읽었나"])

    # 🔴🔴🔴 17 사전등록 §8 이 박은 정본 값이 산출물과 다른가 (987 신설)
    cv = ctx["canon_live"]
    f17 = collections.OrderedDict([
        ("🔴 사전등록 §8 의 칸 수", len(CY.PREREG_CANON)),
        ("🔴 칸별", cv["🔴 칸별"]),
        ("🔴🔴 어긋난 칸", cv["🔴🔴 어긋난 칸"]),
        ("🔴 못 읽은 칸", cv["🔴 못 읽은 칸"]),
        ("🔴 왜 이 조건이 있나",
         "🔴 **986 은 사전등록 `:98` 에 정본을 `446 → 349` 로 등록해 놓고 판정문·원장에 "
         "`415 → 414` 를 실었다.** 🔴 **반증조건 3 은 「분모 넷」만 봐서 «등록된 값»의 "
         "교체를 원리상 못 본다**(티처 #125 2순위 ⓒ)"),
        ("🔴🔴🔴 바뀌었나", bool(not cv["🔴 전부 같은가"])),
    ])
    items["17 사전등록 §8 이 박은 정본 값이 산출물과 다른가(987 신설)"] = \
        (f17, f17["🔴🔴🔴 바뀌었나"])

    # 🔴🔴🔴 18 대상이 줄어 초록이 됐는데 안 밝혔나 (987 신설)
    sec3 = au.get("§C 🔴🔴 `⑤′` 절 3 을 고정 명부로 다시 낸다") or {}
    shrunk = sec3.get("🔴🔴🔴 985 → 986 에서 대상이 줄었나")
    n985 = sec3.get("🔴 985 절 3 대상 수(고정 ref)")
    n986 = sec3.get("🔴 986 절 3 대상 수(고정 ref)")
    disclosed = bool("조용한 좁힘" in joined and str(n985) in joined and str(n986) in joined)
    f18 = collections.OrderedDict([
        ("🔴 985 → 986 에서 대상이 줄었나", shrunk),
        ("🔴 대상 수 985 / 986", [n985, n986]),
        ("🔴🔴 문서가 그 사실을 밝혔나(「조용한 좁힘」 + 두 수)", disclosed),
        ("🔴🔴🔴 줄었는데 안 밝혔나", bool(shrunk and not disclosed)),
    ])
    items["18 자의 대상 집합이 줄어 초록이 됐는데 안 밝혔나(987 신설)"] = \
        (f18, f18["🔴🔴🔴 줄었는데 안 밝혔나"])

    # 🔴🔴🔴 19 자기 논지를 자기가 어겼나 (987 신설)
    sh = _dig(ctx["power"] or {}, "§4 🔴🔴 983 모양 자 — 구간으로 · 확정 / 미확정",
              "🔴 λ 별") or {}
    split_ok = bool(sh) and all(
        (v.get("🔴🔴🔴 확정 「못 잰다」", 0) + v.get("🔴🔴🔴 확정 「잰다」", 0)
         + v.get("🔴🔴🔴 미확정", 0)) == v.get("🔴 인접 칸 쌍 수(분모)") for v in sh.values())
    said = all("미확정" in (_text(p) or "") for p in (BODY[0], PR_BODY))
    f19 = collections.OrderedDict([
        ("🔴 등록한 자기 논지", "🔴 **「구간이 넓으면 점추정을 못 박지 마라」**(사전등록 §4-5)"),
        ("🔴 모양 자가 확정/미확정으로 갈라 냈나", split_ok),
        ("🔴 λ 별 갈래", {k: {"확정 못 잰다": v.get("🔴🔴🔴 확정 「못 잰다」"),
                          "확정 잰다": v.get("🔴🔴🔴 확정 「잰다」"),
                          "미확정": v.get("🔴🔴🔴 미확정")} for k, v in sh.items()}),
        ("🔴🔴 판정문·PR 본문이 「미확정」을 «적었나»", said),
        ("🔴🔴🔴 자기 논지를 어겼나", bool(not (split_ok and said))),
    ])
    items["19 자기 논지를 자기가 어겼나(987 신설)"] = (f19, f19["🔴🔴🔴 자기 논지를 어겼나"])

    rows, bad = collections.OrderedDict(), []
    for k, (detail, broke) in items.items():
        d = collections.OrderedDict(detail)
        d["🔴🔴🔴 반증됐나"] = bool(broke)
        d["통과"] = bool(not broke)
        rows[k] = d
        if broke:
            bad.append(k)
    return rows, bad


# ══════════════════════════════════════════════════════════════════════
# §5 예측 (분모 6)
# ══════════════════════════════════════════════════════════════════════
def predict(ctx):
    pw = ctx["power"] or {}
    au = ctx["audit"] or {}
    var = _dig(pw, "§2 🔴🔴🔴 팔을 다시 짓는다 — V0 · V1 · V1′ · V2", "🔴🔴🔴 변이체별") or {}
    rows = collections.OrderedDict()

    v1 = _dig(var, "V1", "u=0") or {}
    r1 = v1.get("🔴 격자 최대 δ 발화율")
    rows["P1 V1(연언 제거)은 δ 자유 상한이 없다 — `u=0` 격자 최대 δ 발화율 ≥ 0.90"] = \
        collections.OrderedDict([
            ("🔴 V1 `u=0` 격자 최대 δ 발화율", r1),
            ("🔴 V1 이 δ 를 타나(δ>0 에서 상수가 «아닌가»)",
             (None if v1.get("🔴 δ>0 에서 발화율이 «상수»인가(= 자가 δ 를 안 탄다)") is None
              else not v1["🔴 δ>0 에서 발화율이 «상수»인가(= 자가 δ 를 안 탄다)"])),
            ("🔴 맞았나", bool(r1 is not None and r1 >= 0.90)),
        ])
    c1 = (v1 or {}).get("🔴 `δ ≥ 0.50` 구간 발화율 중앙값(986 판 「천장」)")
    c0 = _dig(var, "V0", "u=0", "🔴 `δ ≥ 0.50` 구간 발화율 중앙값(986 판 「천장」)")
    rows["P2 V1 의 `δ ≥ 0.50` 중앙값 천장이 V0 의 그것보다 크다(`u=0`)"] = \
        collections.OrderedDict([
            ("🔴 V1 천장", c1), ("🔴 V0 천장", c0),
            ("🔴 맞았나", bool(c1 is not None and c0 is not None and c1 > c0)),
        ])
    r2 = _dig(var, "V2", "u=0", "🔴 격자 최대 δ 발화율")
    rows["P3 V2(심는 방향 ⊥ h)의 격자 최대 δ 발화율이 V1 보다 작다(`u=0`)"] = \
        collections.OrderedDict([
            ("🔴 V2", r2), ("🔴 V1", r1),
            ("🔴 맞았나", bool(r2 is not None and r1 is not None and r2 < r1)),
        ])
    n4 = _dig(au, "§B-나 🔴🔴 986 문서의 한글 수사 「985 의 다섯 문서」",
              "🔴🔴🔴 어긋난 수사 수(= 예측 P4 의 분자)")
    rows["P4 한글 수사 자가 986 문서에서 어긋남을 하나 이상 잡는다"] = collections.OrderedDict([
        ("🔴 잡은 수", n4), ("🔴 맞았나", bool(n4 is not None and n4 >= 1)),
    ])
    n5 = _dig(au, "§A-나 🔴🔴 AST 자 — 디스크에서 「전」을 읽는 자리",
              "🔴🔴 검정력 시연(조항 64) — 같은 자를 `runners/audit986.py`(고정 ref)에 문다",
              "🔴🔴🔴 잡은 자리 수")
    rows["P5 「전」 AST 자가 `runners/audit986.py` 에서 하나 이상 잡는다"] = \
        collections.OrderedDict([
            ("🔴 잡은 자리 수", n5), ("🔴 맞았나", bool(n5 is not None and n5 >= 1)),
        ])
    sink = _dig(au, "§C 🔴🔴 `⑤′` 절 3 을 고정 명부로 다시 낸다",
                "🔴🔴🔴 데몬 산출물 셋 — 실측", "🔴🔴🔴 대상에 들면 §3 을 떨어뜨리는 파일")
    ok6 = bool(isinstance(sink, list) and sink)
    rows["P6 고정 명부로 다시 계산하면 986 의 `⑤′` §3 초록이 뒤집힌다"] = \
        collections.OrderedDict([
            ("🔴 대상에 들면 §3 을 떨어뜨리는 데몬 파일", sink),
            ("🔴 986 의 §3 통과(고정 ref)",
             (_dig(au, "§C 🔴🔴 `⑤′` 절 3 을 고정 명부로 다시 낸다",
                   "🔴 985 절 3 통과 / 986 절 3 통과") or [None, None])[1]),
            ("🔴 맞았나", ok6),
        ])
    hit = len([1 for v in rows.values() if v.get("🔴 맞았나")])
    return rows, hit


def canon_live(au):
    """🔴🔴🔴 **지연 없는 일곱째 칸** --- 사전등록 §8 정본 == 감사 산출물의 그 칸."""
    import certify987 as C7
    rows, bad, miss = collections.OrderedDict(), [], []
    for name, want in CY.PREREG_CANON.items():
        rel, path = C7.CANON_PATH[name]
        src = au if rel.endswith("out987_audit.json") else _load(rel)
        got, live = CY.resolve(src or {}, path)
        if not got:
            rows[name] = {"🔴 사전등록이 박은 값": want, "🔴": "🔴 그 키 경로가 «없다»"}
            miss.append(name)
            continue
        ok = bool(want == live)
        rows[name] = {"🔴 사전등록이 박은 값": want, "🔴 산출물이 낸 값": live, "🔴 같은가": ok}
        if not ok:
            bad.append(name)
    return collections.OrderedDict([
        ("🔴 분모(사전등록 §8 의 칸 수)", len(CY.PREREG_CANON)),
        ("🔴 칸별", rows), ("🔴🔴 어긋난 칸", bad or "없음"),
        ("🔴 못 읽은 칸", miss or "없음"),
        ("🔴 전부 같은가", bool(not bad and not miss)),
    ])


def live_sixth(tb, ruleD, kor, shape, feeds, six):
    T = _cells(tb) or {}
    live = {
        "채.규칙D표밖": ruleD["🔴🔴 표 밖 합"],
        "채.규칙D분모": ruleD["🔴🔴 채점 분모"],
        "채.규칙D통과": ruleD["통과"],
        "채.한글어긋남": kor["🔴🔴🔴 어긋난 수사 수"],
        "채.한글분모": kor["🔴🔴 센 한글 수사 수"],
        "채.한글통과": kor["통과"],
        "채.68근거없음": shape["🔴🔴 근거 없는 모양 주장 수"],
        "채.68통과": shape["통과"],
        "채.F5분모": feeds["🔴 분모"],
        "채.F5통과": feeds["통과"],
        "채.여섯자리": six["통과"],
    }
    rows, bad, miss = collections.OrderedDict(), [], []
    for k in sorted(live):
        if k not in T:
            miss.append(k)
            rows[k] = {"🔴": "🔴 치환표에 그 칸이 «없다»", "채점기가 «지금» 낸 값": live[k]}
            continue
        ok = bool(T[k] == live[k])
        rows[k] = {"🔴 치환표의 칸": T[k], "🔴 채점기가 «지금» 낸 값": live[k], "🔴 같은가": ok}
        if not ok:
            bad.append(k)
    return collections.OrderedDict([
        ("🔴 분모(`SCORE_CELLS` %d 에서 `SELF_DEP` %d 을 뺀 수)"
         % (len(CY.SCORE_CELLS), len(SELF_DEP)), len(live)),
        ("🔴 칸별", rows), ("🔴🔴 어긋난 칸", bad or "없음"),
        ("🔴 치환표에 없는 칸(= 「같다」가 아니다 · 조항 59)", miss or "없음"),
        ("🔴 전부 같은가", bool(not bad and not miss)),
    ])


def stage(ref, prereg_commit, five_name, it):
    t0 = CY.now()
    CY.begin(ref)
    cs0 = CY.code_stamp()
    rules = LG.ALLOW_CTX + INHERIT
    tb = _load(TBL)
    au = _load("out987_audit.json", must=True)
    pw = _load("out987_power.json", must=True)
    ct = _load("out987_certify.json")
    fp = _load(five_name)
    reg = registered_denominators()
    ruleD = rule_d(tb, rules)
    kor = rule_d_korean(tb)
    shape = shape_audit()
    feeds = feeds_stamp()
    astpass = ast_pass_all()
    handlit = hand_lit_all()
    n_falsify = 19
    six = six_places(collections.OrderedDict([
        ("반증조건 분모", (n_falsify, "반증조건")),
        ("`⑤′` 분모", (reg["🔴 `⑤′` 분모"], "⑤′")),
        ("규칙 D 대상 수", (ruleD["🔴🔴 채점 분모"], "규칙 D")),
    ]))
    live_cert = live_sixth(tb, ruleD, kor, shape, feeds, six)
    cl = canon_live(au)
    ctx = {"prereg_commit": prereg_commit, "reg": reg, "ruleD": ruleD, "korean": kor,
           "five": fp, "six": six, "certify": ct, "feeds": feeds, "table": tb,
           "live_cert": live_cert, "canon_live": cl,
           "astpass": astpass, "handlit": handlit, "power": pw, "audit": au,
           "n_falsify": n_falsify, "n_predict": 6, "n_cert": 7}
    rows, bad = falsify(ctx)
    prows, hit = predict(ctx)

    out = collections.OrderedDict()
    out["무엇"] = "987 채점 — 🔴 반증조건 19 · 예측 6 · 규칙 D 여섯(+ 한글 수사 갈래)"
    out["🔴 축"] = "C1 상태→예측(몸통) · 자기 자"
    out["사전등록"] = PREREG
    out["🔴🔴 조항 60-다 · 사전등록이 박은 분모"] = reg
    out["🔴 `⑤′` 반복"] = it
    out["§6 🔴 반증조건"] = collections.OrderedDict([
        ("🔴 분모", n_falsify), ("🔴 조건별", rows),
        ("🔴🔴 반증된 조건", bad or "없음"),
        ("🔴🔴 분자 / 분모", "%d / %d" % (n_falsify - len(bad), n_falsify)),
        ("통과", bool(not bad)),
    ])
    out["§5 🔴 예측"] = collections.OrderedDict([
        ("🔴 분모", 6), ("🔴 예측별", prows),
        ("🔴🔴 분자 / 분모", "%d / %d" % (hit, 6)),
        ("🔴 분자", hit), ("통과", bool(hit == 6)),
    ])
    out["§D 🔴 규칙 D 감사(분모 여섯)"] = ruleD
    out["§K 🔴🔴 규칙 D — 한글 수사(987 신설)"] = kor
    out["§K-나 🔴 한글 수사 자의 검정력(조항 64)"] = korean_power_demo(au)
    out["§68 🔴 조항 68 모양 주장 감사"] = shape
    out["§F5 🔴 인용 산출물 도장"] = feeds
    out["§9 🔴🔴 여섯 자리가 같은 수를 적나"] = six
    out["§12 🔴🔴🔴 지연 없는 여섯째 칸"] = collections.OrderedDict(
        list(live_cert.items()) + [
            ("통과", bool(live_cert["🔴 전부 같은가"])),
            ("🔴 이 절의 `통과` 가 뜻하는 것",
             "🔴 **치환표가 «지금» 채점기가 낸 값을 들고 있는가**"),
        ])
    out["§17 🔴🔴🔴 지연 없는 일곱째 칸(사전등록 정본)"] = collections.OrderedDict(
        list(cl.items()) + [
            ("통과", bool(cl["🔴 전부 같은가"])),
            ("🔴 이 절의 `통과` 가 뜻하는 것",
             "🔴 **사전등록 §8 이 박은 정본 값이 산출물의 그 칸과 «전부» 같은가**"),
        ])
    out["§AST 🔴 리터럴 `통과` 금지"] = astpass
    out["§R3 🔴 손 전사 수 리터럴 금지(분모 = 이 사이클 러너 전량)"] = handlit
    out["통과"] = bool(out["§6 🔴 반증조건"]["통과"] and ruleD["통과"] and kor["통과"]
                     and shape["통과"] and out["§5 🔴 예측"]["통과"])
    out["🔴🔴🔴 최상위 `통과` 의 정의"] = {
        "985 판": "반증조건 ∧ 규칙 D",
        "986 판": "반증조건 ∧ 규칙 D ∧ §68 ∧ §5 예측",
        "🔴 987 판": "반증조건 ∧ 규칙 D(아라비아) ∧ **§K 규칙 D(한글 수사)** ∧ §68 ∧ §5 예측",
        "🔴 그래서 이 사이클의 최상위 `통과` 는 «떨어질 수 있다»":
            bool(not (shape["통과"] and out["§5 🔴 예측"]["통과"] and kor["통과"])),
    }
    CY.write(OUT, out, ref, cs0, t0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["score"])
    ap.add_argument("--ref", required=True)
    ap.add_argument("--prereg-commit", required=True)
    ap.add_argument("--five", default="fiveprime_987.json")
    ap.add_argument("--five-iter", type=int, default=None)
    ap.add_argument("--five-conv", default=None)
    ap.add_argument("--doc-iter", type=int, default=None)
    a = ap.parse_args()
    it = {"⑤′ 반복": a.five_iter, "⑤′ 수렴": (a.five_conv == "true"),
          "문서 반복": a.doc_iter}
    r = stage(a.ref, a.prereg_commit, a.five, it)
    print(json.dumps({
        "통과": r["통과"],
        "반증조건": r["§6 🔴 반증조건"]["🔴🔴 분자 / 분모"],
        "반증된": r["§6 🔴 반증조건"]["🔴🔴 반증된 조건"],
        "예측": r["§5 🔴 예측"]["🔴🔴 분자 / 분모"],
        "규칙 D 표 밖": r["§D 🔴 규칙 D 감사(분모 여섯)"]["🔴🔴 표 밖 합"],
        "한글 어긋남": r["§K 🔴🔴 규칙 D — 한글 수사(987 신설)"]["🔴🔴🔴 어긋난 수사 수"],
        "§68 근거 없는 모양": r["§68 🔴 조항 68 모양 주장 감사"]["🔴🔴 근거 없는 모양 주장 수"],
    }, ensure_ascii=False))
    return 0 if r["통과"] else 1


if __name__ == "__main__":
    sys.exit(main())
