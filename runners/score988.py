#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""988 채점 — 🔴 반증조건 **23**(식별자 `F01`~`F23`) · 예측 **4** · 규칙 D 대상 **여섯**.

🔴 **987 과 다른 것 다섯(사전등록이 측정 전에 박았다):**

1. 🔴🔴🔴 **예측을 «선언표 하나»로만 계산한다**(`PRED_DEF`) --- 그래야
   `certify988` 의 **여덟째 칸**이 「사전등록이 등록한 판정식 == 채점기가 평가한 식」을
   **키 경로 집합으로** 볼 수 있다. 🔴 987 은 그 자리에서 식을 갈아 끼웠다.
2. 🔴🔴 **`조항 59-나`** --- 「자리 0」은 「통과」가 아니라 **「미측정」**이다.
3. 🔴🔴 **`§K` 의 「값 대조」를 판정 분모로 «복귀»시킨다**(987 이 조용히 강등했다).
   그리고 **바늘을 2 → 12 로 늘린다.**
4. 🔴 **`F18`** 을 「이 사이클 대 «직전 사이클»」로 다시 쓴다(`R3`).
5. 🔴 **반증조건 키를 「식별자만」**(`F01`~`F23`)으로 낸다(`R4`) ---
   제목 문자열이 문서에 실려 자기 채점 결과가 자기 분모로 되먹는 고리를 끊는다.

씀:
    python3 runners/score988.py --stage score --ref <sha> --prereg-commit <sha> …
"""
import argparse
import ast
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

import cycle988 as CY                                  # noqa: E402
import ledger as LG                                    # noqa: E402
import score985 as S5                                  # noqa: E402

SELF_DEP = ("채.반증분자모", "채.반증분모", "채.반증된", "채.반증통과",
            "채.예측분자모", "채.예측분자", "채.예측통과", "채.최상위통과")

OUT = "runners/out988_score.json"
PREREG = CY.PREREG
BODY = ("docs/판정_988.md", "docs/card_988.md", "docs/handoff_988.md")
PR_BODY = "docs/pr_988.md"
GOAL = "docs/목표.md"
DEN = "data/lab/denominator.json"
TBL = CY.TABLE
CARD_OUT = os.path.expanduser(
    "~/.claude/projects/-Users-ax-world-model/memory/project-lab-state.md")
MARK_A = S5.MARK_A
MARK_B = S5.MARK_B
LEDGER_KEY = "노트 988"
PR_MARK = "<!-- 988:pr:생성물 -->"

FEED_RE = re.compile(
    r"`?((?:runners/)?(?:out988_[a-z0-9_]+|fiveprime_988[a-z0-9_]*)\.json)`?")
FEED_EXEMPT = re.compile(r"fiveprime_988")

SHAPE_RE = S5.SHAPE_RE
SHAPE_OK = S5.SHAPE_OK
SHAPE_WIN = S5.SHAPE_WIN

DEN_FALSIFY = re.compile(r"##\s*§6\s*반증조건\s*\(분모\s*\*\*(\d+)\*\*")
DEN_PREDICT = re.compile(r"##\s*§5\s*예측\s*\(분모\s*\*\*(\d+)\*\*")
DEN_FIVE = re.compile(r"`⑤′`\s*분모\s*—\s*🔴\s*\*\*등록\s*(\d+)")
DEN_RULED = re.compile(r"규칙 D 대상 수\s*\|\s*\*\*(\d+)\*\*")
DEN_CERT = re.compile(r"`certify`\s*칸 수\s*\|\s*\*\*(\d+)\*\*")

INHERIT = S5.INHERIT

# ══════════════════════════════════════════════════════════════════════
# 🔴🔴🔴 예측의 «선언표» --- 채점기가 평가하는 식은 «이것 하나»뿐이다
# ══════════════════════════════════════════════════════════════════════
#: 🔴 **왜 표인가 (티처 #126 C1).** 987 은 `predict()` 안에서 P6 의 판정식을
#:  `bool(sink)` 로 «손으로» 지었고 등록 정의(`명부판 §3 통과 = False`)를 아예
#:  계산하지 않았다. **표로 두면 「등록한 키 경로」와 「평가한 키 경로」가
#:  기계로 대조된다.**
PRED_DEF = collections.OrderedDict([
    ("P1", ("out988_audit",
            ["§B 🔴🔴🔴 여덟째 칸 — 등록 판정식 대조", "🔴🔴 987 에서 어긋난 예측 수"],
            "==", 1)),
    ("P2", ("out988_audit",
            ["§C 🔴🔴 「자리 0」 감사", "🔴🔴🔴 미측정으로 재분류된 조건 수"],
            ">=", 3)),
    ("P3", ("out988_audit",
            ["§D 🔴🔴 늘린 한글 바늘을 987 문서에 문다", "🔴🔴🔴 바늘이 걸린 수사 수"],
            ">=", 10)),
    ("P4", ("out988_audit",
            ["§E 🔴🔴🔴 단조 불변(동어반복) 자", "🔴🔴🔴 발화한 변이체"],
            "==", ["V1"])),
])

_OPS = ("==", ">=", "<=", "!=", "≥", "≤", ">", "<")
PRED_ROW = re.compile(r"^\|\s*\*{0,2}(P\d+)\*{0,2}\s*\|", re.M)


def prereg_key_paths(txt):
    """🔴🔴🔴 **사전등록 §5 의 `판정식:` 줄을 «기계 판독»한다.**

    꼴: ``판정식: <산출물>#<키 경로를 ` | ` 로 이어붙인 것> <연산자> <값>``
    """
    out = collections.OrderedDict()
    if txt is None:
        return out
    for line in (txt or "").split("\n"):
        m = PRED_ROW.match(line)
        if not m:
            continue
        safe = line.replace("\\|", "\x00")
        cells = [c.strip().replace("\x00", "|") for c in safe.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        d = cells[-1].strip().strip("`")
        mm = re.search(r"판정식\s*:\s*(.+)$", d)
        if not mm:
            out[m.group(1)] = None
            continue
        body = mm.group(1).strip().strip("`")
        op = None
        for o in _OPS:
            i = body.rfind(" %s " % o)
            if i > 0:
                op, lhs, rhs = o, body[:i], body[i + len(o) + 2:]
                break
        if op is None:
            out[m.group(1)] = None
            continue
        src, _sep, path = lhs.partition("#")
        keys = [k.strip() for k in path.split("|")]
        try:
            val = json.loads(rhs.strip())
        except Exception:                                          # noqa: BLE001
            val = rhs.strip()
        out[m.group(1)] = [src.strip(), keys, op, val]
    return out


def declared_key_paths():
    """🔴 **채점기가 «실제로» 쓰는 선언표를 같은 꼴로 낸다.**"""
    return collections.OrderedDict(
        (k, [src, list(keys), op, val]) for k, (src, keys, op, val) in PRED_DEF.items())


def _cmp(op, got, want):
    if got is None:
        return False
    if op == "==":
        return bool(got == want)
    if op == "!=":
        return bool(got != want)
    try:
        if op in (">=", "≥"):
            return bool(got >= want)
        if op in ("<=", "≤"):
            return bool(got <= want)
        if op == ">":
            return bool(got > want)
        if op == "<":
            return bool(got < want)
    except TypeError:
        return False
    return False


# ══════════════════════════════════════════════════════════════════════
# 🔴🔴🔴 `[수리]` --- 한글 수사 «앞말 바늘» 열둘 (987 은 둘이었고 0 자리 걸렸다)
# ══════════════════════════════════════════════════════════════════════
KOR_NEEDLES = collections.OrderedDict([
    ("수리 레인 수", (re.compile(r"수리\s*(?:레인\s*)?\**\s*$"), "수.수리레인")),
    ("`certify` 칸 수", (re.compile(r"certify[^\n]{0,10}\**\s*$"), "채.certify칸")),
    ("예측 분모", (re.compile(r"예측\s*(?:분모\s*)?\**\s*$"), "채.예측분모")),
    ("규칙 D 대상 수", (re.compile(r"규칙\s*D\s*(?:대상\s*)?\**\s*$"), "채.규칙D분모")),
    ("`DOC_INPUTS` 분모", (re.compile(r"DOC_INPUTS[^\n]{0,10}\**\s*$"), "문.DOC분모")),
    ("정정을 얹는 자리 수", (re.compile(r"자리\s*\**\s*$"), "정.다섯자리")),
    ("데몬 셋 명부 수", (re.compile(r"데몬\s*(?:셋\s*)?\**\s*$"), "절3.명부수")),
    ("미측정 후보 조건 수", (re.compile(r"8·14·15·16\s*\**\s*$"), "정.미측정넷")),
    ("지연 없는 자가 뺀 칸 수", (re.compile(r"뺀\s*\**\s*$"), "정.지연없는뺀칸")),
    ("비맹검 이관 뒤 분모", (re.compile(r"이관\s*(?:뒤\s*)?\**\s*$"), "정.이관뒤분모")),
    ("미룬 사이클 수", (re.compile(r"985·986·987\s*\**\s*$"), "정.미룬사이클")),
    ("`⑤′` 실패 절 수", (re.compile(r"실패\s*절\s*\**\s*$"), "오프.실패절수")),
])

#: 🔴 **관용구 제외**(조항 60 --- 조용히 안 뺀다). 「하나도 없다」는 «수사»가 아니라
#:  「0」의 관용 표현이고, 「둘 다 / 셋 다 / 넷 다」도 계수가 아니라 지시어다.
KOR_IDIOM = re.compile(r"^(?:도\s*없|\s*다\b|\s*다\s)")


def _git(*a):
    return subprocess.check_output(["git"] + list(a), cwd=str(ROOT)).decode("utf-8")


def _text(rel):
    """🔴 **「지금」 읽기다** --- 규칙 D 채점은 디스크의 «지금» 문서를 봐야 한다(등록 면제)."""
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
        ("🔴 대상", list(targets.keys())),
        ("🔴 대상별", rows),
        ("🔴🔴 표 밖 합", tot),
        ("🔴 못 읽은 대상", unread or "없음"),
        ("🔴 치환표 칸 수", len(T)),
        ("🔴 치환표 sha256", (tb or {}).get("🔴🔴 표 sha256")),
        ("통과", bool(tot == 0 and not unread)),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **여섯 대상 전부에서 치환표 밖의 «아라비아» 수가 0 인가.** 한글 수사는 §K 가 진다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §K 🔴🔴 규칙 D --- 한글 수사(자 «둘»: 값 대조 + 바늘 대조 · `조항 59-나`)
# ══════════════════════════════════════════════════════════════════════
def rule_d_korean(tb):
    """🔴🔴🔴 **987 이 조용히 강등한 「값 대조」를 판정 분모로 «복귀»시킨다.**

    🔴 **왜 (티처 #126 C2).** 987 사전등록 §4-4 는 자를 **둘** 등록했는데
    `out987_score.json §K` 에서 「값 대조」가 **`판정에 안 쓴다` 라벨로 분모에서 빠졌고**
    판정문·사전등록·PR·handoff 어디에도 그 강등이 **없었다**(`조항 60-나` 위반).
    🔴 그리고 **남은 「바늘 대조」는 «0 자리» 걸렸다** --- `조항 59-나` 로 「미측정」이다.
    """
    T = _cells(tb) or {}
    S = S5._table_set(tb)
    targets = _targets()
    rows, bad, valbad, seen, tied = collections.OrderedDict(), [], [], 0, 0
    for name, txt in targets.items():
        if txt is None:
            rows[name] = {"🔴": "🔴 못 읽었다(= 「0」이 아니다 · 조항 59)"}
            continue
        code = [(m.start(), m.end()) for m in re.finditer(r"`[^`\n]*`", txt)]
        hits, exempt, t_n, miss, notab, idiom = [], 0, 0, [], [], 0
        for m in LG.KNUMPAT.finditer(txt):
            if LG.KNUM_NOT.match(txt, m.start()):
                continue
            if any(a <= m.start() and m.end() <= b for a, b in code):
                exempt += 1
                continue
            if KOR_IDIOM.match(txt[m.end():m.end() + 6]):
                idiom += 1
                continue
            word = m.group()
            val = LG.KOR_NUM[word]
            seen += 1
            ctx = re.sub(r"\s+", " ", txt[max(0, m.start() - 30):m.end() + 20])
            head = txt[max(0, m.start() - 24):m.start()]
            hits.append(word)
            for lab, (rx, cell) in KOR_NEEDLES.items():
                if not rx.search(head):
                    continue
                t_n += 1
                tied += 1
                want = T.get(cell)
                if want is None or val != want:
                    miss.append({"바늘": lab, "수사": word, "값": val,
                                 "치환표 칸": cell, "치환표 값": want, "맥락": ctx})
            if str(val) not in S:
                notab.append({"수사": word, "값": val, "맥락": ctx})
        rows[name] = {"🔴 센 한글 수사": len(hits),
                      "🔴 면제(인라인 코드 안)": exempt,
                      "🔴 면제(관용구)": idiom,
                      "🔴🔴 바늘이 걸린 수사": t_n,
                      "🔴🔴🔴 바늘 대조에서 어긋난 것": miss or "없음",
                      "🔴🔴🔴 값 대조에서 치환표 밖인 수사": notab or "없음",
                      "수사별": dict(collections.Counter(hits))}
        bad += miss
        valbad += notab
    m1 = CY.measured("바늘 대조", len(targets), tied, len(bad))
    m2 = CY.measured("값 대조", len(targets), seen, len(valbad))
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴🔴 **규칙 D(한글 수사) --- 등록한 자 «둘»을 «둘 다» 판정에 쓴다**"),
        ("🔴🔴🔴 987 이 무엇을 했나(조항 60-나 위반 · 티처 #126 C2)",
         "🔴 **987 사전등록 §4-4 는 자를 «둘» 등록**(1 값 대조 · 2 바늘 대조)**해 놓고 "
         "`out987_score.json §K` 에서 「값 대조」를 `판정에 안 쓴다` 라벨로 분모에서 뺐다.** "
         "🔴 **판정문·사전등록·PR·handoff 어디에도 그 강등이 없었다**(grep 0 건). "
         "🔴 **반증조건 4 는 `⑤′` 명부만 봐서 원리상 못 본다.** 988 이 «복귀»시킨다"),
        ("🔴 자의 출처", "🔴 978 수리 4 가 만든 `ledger.KNUMPAT`·`ledger.KOR_NUM`"),
        ("🔴 등록한 수사 낱말", dict(LG.KOR_NUM)),
        ("🔴 뺀 규칙 ①(수사가 아닌 자리)", LG.KNUM_NOT.pattern),
        ("🔴 뺀 규칙 ②(관용구 --- 「하나도 없다」·「둘 다」 · 조용히 안 뺀다)", KOR_IDIOM.pattern),
        ("🔴🔴 등록 바늘 수", len(KOR_NEEDLES)),
        ("🔴 987 의 등록 바늘 수", 2),
        ("🔴🔴 등록한 앞말 바늘(이름 · 정규식 · 치환표 칸)",
         {k: {"정규식": v[0].pattern, "치환표 칸": v[1], "치환표 값": T.get(v[1])}
          for k, v in KOR_NEEDLES.items()}),
        ("🔴🔴 채점 분모(대상)", len(targets)),
        ("🔴🔴 센 한글 수사 수", seen),
        ("🔴 대상별", rows),
        ("🔴🔴🔴 바늘이 걸린 수사 수", tied),
        ("🔴🔴🔴 바늘 대조 어긋난 수사 수", len(bad)),
        ("🔴 바늘 대조 어긋난 자리", bad or "없음"),
        ("🔴🔴🔴 값 대조 어긋난 수사 수", len(valbad)),
        ("🔴 값 대조 어긋난 자리", valbad or "없음"),
        ("🔴🔴🔴 자 ① 바늘 대조(조항 59-나)", m1),
        ("🔴🔴🔴 자 ② 값 대조(조항 59-나 · 🔴 987 이 강등한 자)", m2),
        ("⚠ 이 자의 한계(조항 61)",
         "🔴 **등록 안 한 앞말의 한글 수사는 이 자도 원리상 못 본다.** "
         "🔴 그리고 **「값이 치환표 안인가」는 작은 수가 어느 긴 표에나 있어 약한 자다** --- "
         "그래도 **약한 자를 «판정 밖으로 빼는 것»은 강등이고, 강등은 밝혀야 한다**(조항 60-나)"),
        ("통과", bool(m1["통과"] and m2["통과"])),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **자 «둘»이 «둘 다» `조항 59-나` 를 넘는가** --- "
         "곧 ① 분모 > 0 ② 걸린 자리 > 0 ③ 어긋남 0 을 «둘 다» 만족하는가"),
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
         "「그 근거가 «그 모양의» 근거인가」는 원리상 안 본다. **988 도 이 자를 안 고쳤다**"),
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
        re.findall(r"(?:runners/)?((?:out988|fiveprime)_?[\w]*\.json)", ent)))
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
    rows, tot, cand, unread = collections.OrderedDict(), 0, 0, []
    for rel in CY.RAN_988:
        h = S5.ast_pass_hits(rel)
        src = _text(rel)
        c = 0
        if src is not None:
            try:
                tree = ast.parse(src)
                for n in ast.walk(tree):
                    if isinstance(n, ast.Tuple) and len(n.elts) == 2 \
                            and isinstance(n.elts[0], ast.Constant) \
                            and n.elts[0].value == "통과":
                        c += 1
            except SyntaxError:
                c = 0
        if h is None:
            rows[rel] = {"🔴": "🔴 못 읽었다"}
            unread.append(rel)
            continue
        rows[rel] = {"후보 자리(`(\"통과\", …)`)": c, "리터럴 True 자리": len(h),
                     "자리": h or "없음"}
        tot += len(h)
        cand += c
    m = CY.measured("리터럴 `(\"통과\", True)` 금지", len(CY.RAN_988), cand, tot)
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴 **리터럴 `(\"통과\", True)` 금지**(983 R1 · AST)"),
        ("🔴 분모(이 사이클 러너 전량)", len(CY.RAN_988)),
        ("🔴 러너별", rows),
        ("🔴🔴 후보 자리 수(= 이 수가 0 이면 「미측정」이다 · 조항 59-나)", cand),
        ("🔴🔴🔴 리터럴 자리 수", tot),
        ("🔴 못 읽은 러너(= 0 이 아니다)", unread or "없음"),
        ("🔴🔴🔴 조항 59-나 판정", m),
        ("통과", bool(m["통과"] and not unread)),
    ])


def hand_lit_all():
    rows, tot, cand, unread = collections.OrderedDict(), 0, 0, []
    for rel in CY.RAN_988:
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
        hits, c = [], 0
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            for t in node.targets:
                if not isinstance(t, ast.Subscript):
                    continue
                c += 1
                v = node.value
                if isinstance(v, ast.Constant) and isinstance(v.value, (int, float)) \
                        and not isinstance(v.value, bool):
                    hits.append({"줄": node.lineno, "꼴": "T[...] = <숫자 리터럴>"})
        rows[rel] = {"후보 자리(`T[…] = …`)": c, "자리 수": len(hits), "자리": hits or "없음"}
        tot += len(hits)
        cand += c
    m = CY.measured("손 전사 수 리터럴 금지", len(CY.RAN_988), cand, tot)
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴 **손 전사 수 리터럴 금지** --- 분모는 «이 사이클 러너 전량»"),
        ("🔴 분모", len(CY.RAN_988)),
        ("🔴 러너별", rows),
        ("🔴🔴 후보 자리 수(= 이 수가 0 이면 「미측정」이다 · 조항 59-나)", cand),
        ("🔴🔴🔴 988 러너의 손 전사 자리 수", tot),
        ("🔴 못 읽은 러너(= 0 이 아니다)", unread or "없음"),
        ("🔴🔴🔴 조항 59-나 판정", m),
        ("통과", bool(m["통과"] and not unread)),
    ])


def disk_read_audit():
    """🔴🔴 **F16 --- 바늘을 `runners/`·`docs/` 전량 + 변수 경로로 넓힌다**(즉시 정정)."""
    import audit988 as A8                                          # noqa: E402
    rows, old, new, var = collections.OrderedDict(), 0, 0, 0
    for rel in CY.RAN_988:
        src = _text(rel)
        d = A8._count_disk_reads(src or "")
        rows[rel] = d
        if d:
            old += d["구판 바늘(`^docs/.*\\.md$`)에 걸린 인자"]
            new += d["🔴 신판 바늘(`runners/`·`docs/` 전량)에 걸린 인자"]
            var += d["🔴 변수 경로 인자(구판은 원리상 «못 본다»)"]
    exempt = dict(CY.DISK_READ_EXEMPT)
    outside = collections.OrderedDict()
    for rel, d in rows.items():
        if rel in exempt or not d:
            continue
        n = d["🔴 신판 바늘(`runners/`·`docs/` 전량)에 걸린 인자"]
        if n:
            outside[rel] = n
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴🔴 **「전」 값을 «고정 ref 없이» 디스크에서 읽었나** --- "
                 "🔴 **바늘을 `runners/`·`docs/` 전량 + «변수 경로»로 넓혔다**"),
        ("🔴 즉시 정정의 근거",
         "🔴 **987 의 바늘은 `^docs/.*\\.md$` 만 봤다** --- `조항 71-가` 는 「모든 「전」 값」인데 "
         "**`runners/*.json` 의 「전」이 원리상 안 보였다**(행동은 준수였다)"),
        ("🔴 러너별", rows),
        ("⚠ 구판 바늘로 걸린 인자 수", old),
        ("🔴🔴 신판 바늘로 걸린 인자 수", new),
        ("🔴🔴 변수 경로 인자 수", var),
        ("🔴 등록 면제와 사유(조용히 안 뺀다)", exempt),
        ("🔴🔴🔴 면제 «밖»에서 디스크 경로 리터럴을 읽는 러너", dict(outside) or "없음"),
        ("🔴🔴🔴 면제 밖에서 걸린 자리 수", sum(outside.values())),
    ])


# ══════════════════════════════════════════════════════════════════════
# §5 예측 --- 🔴🔴🔴 **선언표 하나로만 계산한다**
# ══════════════════════════════════════════════════════════════════════
def predict(ctx):
    """🔴🔴🔴 **`PRED_DEF` 밖에서 「맞았나」를 만들지 않는다.**

    987 은 여기서 등록 정의를 갈아 끼웠다. 988 은 **키 경로 · 연산자 · 값 셋을
    표에서만 읽고** `certify988` 의 여덟째 칸이 그 표를 사전등록과 대조한다.
    """
    srcs = {"out988_audit": ctx["audit"]}
    rows, hit = collections.OrderedDict(), 0
    for pid, (srcname, keys, op, want) in PRED_DEF.items():
        obj = srcs.get(srcname)
        ok, got = CY.resolve(obj or {}, keys)
        good = _cmp(op, got, want) if ok else False
        rows[pid] = collections.OrderedDict([
            ("🔴 산출물", srcname),
            ("🔴🔴 키 경로(사전등록 §5 가 등록한 그것)", list(keys)),
            ("🔴 연산자", op), ("🔴 등록한 값", want),
            ("🔴🔴 산출물이 낸 값", got),
            ("🔴 키 경로를 «풀었나»", ok),
            ("🔴 맞았나", bool(good)),
        ])
        hit += 1 if good else 0
    return rows, hit


# ══════════════════════════════════════════════════════════════════════
# §6 반증조건 (분모 23 · 🔴 문서에는 «식별자만»)
# ══════════════════════════════════════════════════════════════════════
def _undecided_literals(pw):
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
            if key and row[key[0]] is not True \
                    and row.get("🔴 최소 검출 모양 크기(점추정)") is not None:
                out["모양/%s/%s" % (uk, cell)] = row["🔴 최소 검출 모양 크기(점추정)"]
    return out


#: 🔴🔴🔴 **`R4`** --- 문서에 싣는 것은 «식별자만»이고 제목은 사전등록에서만 읽는다.
F_TITLE = collections.OrderedDict([
    ("F01", "사전등록 blob 을 측정 뒤에 고쳤다"),
    ("F02", "막힌 명령을 우회하고 신고를 안 했다"),
    ("F03", "등록 분모와 다른 수로 채점했다"),
    ("F04", "등록한 절을 분모에서 뺐다"),
    ("F05", "값을 낸 뒤 그 값을 내는 러너를 고치고 안 다시 돌렸다"),
    ("F06", "채점기를 다시 돌리고 문서를 안 다시 찍었다"),
    ("F07", "PR 본문이 문서와 다르다"),
    ("F08", "식별되지 않는 수를 소수점으로 못 박았다"),
    ("F09", "규칙 D(아라비아) 표 밖"),
    ("F10", "규칙 D(한글 수사) --- 바늘 대조 또는 값 대조가 어긋났다"),
    ("F11", "여섯 자리가 다른 수를 적는다"),
    ("F12", "문서 고리가 수렴 안 했다"),
    ("F13", "인용 산출물이 F5 도장을 못 넘었다"),
    ("F14", "이 사이클 러너에 리터럴 통과 True 가 있다"),
    ("F15", "이 사이클 러너에 손 전사 수 리터럴이 있다"),
    ("F16", "「전」 값을 고정 ref 없이 디스크에서 읽었다"),
    ("F17", "사전등록 정본 값이 채점 산출물과 다르다"),
    ("F18", "이 사이클의 자 대상 집합이 직전 사이클보다 줄었는데 안 밝혔다"),
    ("F19", "자기 논지를 자기가 어겼다 --- 점추정 합계를 실었다"),
    ("F20", "등록한 판정식과 채점기가 평가한 식이 다르다"),
    ("F21", "등록한 자를 판정 밖으로 강등하고 안 밝혔다"),
    ("F22", "「자리 0」을 「통과」로 셌다"),
    ("F23", "아는 red 를 명부에 안 넣었다"),
])


def falsify(ctx):
    items = collections.OrderedDict()
    au = ctx["audit"] or {}
    joined = "\n".join((_text(p) or "") for p in list(BODY) + [PR_BODY])

    pc = ctx["prereg_commit"]
    try:
        blob = _git("show", "%s:%s" % (pc, PREREG)).encode("utf-8")
        was = hashlib.sha256(blob).hexdigest()
    except Exception as e:                                         # noqa: BLE001
        was = "🔴 못 읽었다: %s" % e
    cur = _sha(PREREG)
    f = collections.OrderedDict([
        ("🔴 사전등록 커밋(측정 «전»)", pc),
        ("🔴 그 커밋의 blob sha256", was),
        ("🔴 디스크 sha256", cur),
        ("🔴🔴 고쳤나", bool(was != cur)),
    ])
    items["F01"] = (f, f["🔴🔴 고쳤나"])

    t = _text(PREREG) or ""
    has_sec = "막힌 명령 신고" in t
    verd = _text(BODY[0]) or ""
    declared = ("막힌 명령" in verd)
    f = collections.OrderedDict([
        ("🔴 사전등록에 신고 절이 있나", has_sec),
        ("🔴 판정문에 신고가 있나", declared),
        ("⚠ 이 자의 한계(조항 61)",
         "🔴 **셸 이력은 저장소에 안 남으므로 기계가 「시도 자체」를 확인·부정할 수 없다**"),
        ("🔴🔴🔴 신고를 안 했나", bool(not (has_sec and declared))),
    ])
    items["F02"] = (f, f["🔴🔴🔴 신고를 안 했나"])

    reg = ctx["reg"]
    got = {"반증조건": ctx["n_falsify"], "예측": ctx["n_predict"],
           "규칙 D 대상": ctx["ruleD"]["🔴🔴 채점 분모"], "certify 칸": ctx["n_cert"]}
    want = {"반증조건": reg["🔴 반증조건 분모(사전등록에서 «읽었다»)"],
            "예측": reg["🔴 예측 분모"], "규칙 D 대상": reg["🔴 규칙 D 대상 수"],
            "certify 칸": reg["🔴 `certify` 칸 수"]}
    diff = sorted(k for k in got if got[k] != want[k])
    f = collections.OrderedDict([
        ("🔴 사전등록이 박은 분모", want), ("🔴 채점이 쓴 분모", got),
        ("🔴 어긋난 분모", diff or "없음"), ("🔴🔴 다르게 썼나", bool(diff)),
    ])
    items["F03"] = (f, f["🔴🔴 다르게 썼나"])

    fp = ctx["five"] or {}
    n_sec = fp.get("🔴 절 수(분모)")
    f = collections.OrderedDict([
        ("🔴 사전등록이 박은 `⑤′` 분모", reg["🔴 `⑤′` 분모"]),
        ("🔴 `⑤′` 가 쓴 절 수", n_sec),
        ("🔴 명부 밖에서 `통과` 를 든 절", fp.get("🔴🔴 명부 밖(분모를 조용히 넓히는 자리)")),
        ("🔴🔴 뺐나", bool(n_sec is not None and reg["🔴 `⑤′` 분모"] is not None
                       and n_sec < reg["🔴 `⑤′` 분모"])),
    ])
    items["F04"] = (f, f["🔴🔴 뺐나"])

    st = CY.stale_outputs()
    f = collections.OrderedDict([
        ("🔴 낡은 산출물", st["🔴🔴🔴 낡은 산출물(고치고 안 다시 돌렸다)"]),
        ("🔴 못 읽은 것", st["🔴 못 읽은 것(= 「없다」가 아니다)"]),
        ("🔴🔴 고치고 안 다시 돌렸나", bool(st["🔴🔴🔴 낡은 것이 있나"])),
    ])
    items["F05"] = (f, f["🔴🔴 고치고 안 다시 돌렸나"])

    sd = CY.stale_docs()
    unknown6 = sd.get("🔴🔴🔴 낡은 문서가 있나") is None
    f = collections.OrderedDict([
        ("🔴 분모", len(CY.DOC_INPUTS)),
        ("🔴 입력별", sd.get("🔴 입력별")),
        ("🔴 문서를 찍은 뒤 달라진 산출물", sd.get("🔴🔴🔴 문서를 찍은 뒤 달라진 산출물")),
        ("🔴 치환표가 sha 를 안 박은 입력",
         sd.get("🔴 치환표가 sha 를 안 박은 입력(= 「같다」가 아니다 · 조항 59)")),
        ("🔴 명시적으로 뺀 입력과 사유", sd.get("🔴🔴 «명시적으로» 뺀 입력과 사유(조용히 안 뺀다)")),
        ("🔴🔴🔴 안 다시 찍었나(「모른다」도 반증이다 · 조항 59)",
         bool(sd.get("🔴🔴🔴 낡은 문서가 있나") or unknown6)),
    ])
    items["F06"] = (f, f["🔴🔴🔴 안 다시 찍었나(「모른다」도 반증이다 · 조항 59)"])

    rd = ctx["ruleD"]
    pr_row = None
    for k, v in (rd.get("🔴 대상별") or {}).items():
        if PR_BODY in k:
            pr_row = v
    prtxt = _text(PR_BODY) or ""
    f = collections.OrderedDict([
        ("🔴 PR 본문이 규칙 D 분모 안인가", bool(pr_row is not None)),
        ("🔴 PR 본문의 「표 밖」 수", (pr_row or {}).get("표 밖")),
        ("🔴 PR 본문이 치환표에서 «지어졌나»", bool(PR_MARK in prtxt)),
        ("🔴🔴 다른가", bool(pr_row is None or pr_row.get("표 밖") != 0
                        or PR_MARK not in prtxt)),
    ])
    items["F07"] = (f, f["🔴🔴 다른가"])

    needles = _undecided_literals(ctx["power987"])
    naked = []
    for lab, val in needles.items():
        s = ("%g" % val)
        for m in re.finditer(re.escape(s) + r"(?![\d])", joined):
            w = joined[max(0, m.start() - 220):m.end() + 220]
            if not any(x in w for x in ("구간", "미확정", "식별", "못 박")):
                naked.append({"바늘": lab, "수": s})
                break
    m8 = CY.measured("F08 미식별 점추정", 1, len(needles), len(naked))
    f = collections.OrderedDict([
        ("🔴 바늘(미식별 칸의 점추정 · 987 산출물에서 자동 생성)", needles),
        ("🔴 바늘 수", len(needles)),
        ("🔴🔴 «구간·미확정 맥락 없이» 실린 수", naked or "없음"),
        ("🔴🔴🔴 조항 59-나 판정", m8),
        ("🔴🔴🔴 못 박았나", bool(naked)),
    ])
    items["F08"] = (f, f["🔴🔴🔴 못 박았나"])

    f = collections.OrderedDict([
        ("🔴 표 밖 합", rd["🔴🔴 표 밖 합"]), ("🔴 채점 분모", rd["🔴🔴 채점 분모"]),
        ("🔴 못 읽은 대상", rd["🔴 못 읽은 대상"]),
        ("🔴🔴 전부 치환표 칸인가", bool(rd["통과"])),
    ])
    items["F09"] = (f, not f["🔴🔴 전부 치환표 칸인가"])

    kr = ctx["korean"]
    f = collections.OrderedDict([
        ("🔴 센 한글 수사 수", kr["🔴🔴 센 한글 수사 수"]),
        ("🔴 바늘이 걸린 수사 수", kr["🔴🔴🔴 바늘이 걸린 수사 수"]),
        ("🔴 바늘 대조 어긋난 수사 수", kr["🔴🔴🔴 바늘 대조 어긋난 수사 수"]),
        ("🔴 값 대조 어긋난 수사 수", kr["🔴🔴🔴 값 대조 어긋난 수사 수"]),
        ("🔴🔴 자 «둘»을 «둘 다» 썼나(강등 없음)", True),
        ("🔴🔴 어긋났나", bool(not kr["통과"])),
    ])
    items["F10"] = (f, f["🔴🔴 어긋났나"])

    sx = ctx["six"]
    items["F11"] = (sx, not sx["통과"])

    live = ctx["live_cert"]
    ct = ctx["certify"] or {}
    mine = ct.get("§가 🔴🔴🔴 988 자신") or {}
    f = collections.OrderedDict([
        ("🔴🔴🔴 지연 없는 자(채점기가 «지금» 낸 값 대 치환표)", live),
        ("🔴🔴 뺀 칸(자기 결과에 의존한다 · 조용히 안 뺀다 · 조항 60)", list(SELF_DEP)),
        ("🔴 왜 뺐나",
         "🔴 **디스크의 `out988_certify.json` 을 읽으면 한 회 뒤진 값을 읽고 "
         "«주기 4 의 진동»이 생겨 고정점에 원리상 도달 못 한다**(986 실측)"),
        ("⚠ 디스크 `certify` 가 적은 어긋난 칸(한 회 뒤질 수 있다 · 진단)",
         mine.get("🔴🔴 어긋난 칸")),
        ("🔴🔴 수렴했나", bool(live["🔴 전부 같은가"])),
    ])
    items["F12"] = (f, not f["🔴🔴 수렴했나"])

    fs = ctx["feeds"]
    items["F13"] = (fs, not fs["통과"])

    ap = ctx["astpass"]
    items["F14"] = (ap, not ap["통과"])

    hl = ctx["handlit"]
    items["F15"] = (hl, not hl["통과"])

    dr = ctx["diskread"]
    T = _cells(ctx["table"]) or {}
    before_cells = [k for k in T if k.startswith("전.") and not k.endswith(".ref")]
    noref = []
    for k in before_cells:
        v = T.get(k + ".ref")
        if not (isinstance(v, str) and len(v) == 40
                and all(c in "0123456789abcdef" for c in v)):
            noref.append(k)
    f = collections.OrderedDict([
        ("🔴🔴 넓힌 바늘 감사", dr),
        ("🔴🔴 치환표의 `전.` 칸 수", len(before_cells)),
        ("🔴🔴🔴 짝 `ref` 칸이 40 자 sha 가 «아닌» 칸", noref or "없음"),
        ("🔴🔴🔴 디스크에서 읽었나",
         bool(dr["🔴🔴🔴 면제 밖에서 걸린 자리 수"] > 0 or noref)),
    ])
    items["F16"] = (f, f["🔴🔴🔴 디스크에서 읽었나"])

    cv = ctx["canon_live"]
    f = collections.OrderedDict([
        ("🔴 사전등록 §8 의 칸 수", len(CY.PREREG_CANON)),
        ("🔴 칸별", cv["🔴 칸별"]),
        ("🔴🔴 어긋난 칸", cv["🔴🔴 어긋난 칸"]),
        ("🔴 못 읽은 칸", cv["🔴 못 읽은 칸"]),
        ("🔴🔴🔴 바뀌었나", bool(not cv["🔴 전부 같은가"])),
    ])
    items["F17"] = (f, f["🔴🔴🔴 바뀌었나"])

    # 🔴🔴🔴 F18 --- `R3`: 「이 사이클 대 «직전 사이클»」
    n_now = _dig(ctx["five"] or {}, "3 판정 키 규약", "🔴 파일 수(분모)")
    n_prev = _dig(ctx["five987"] or {}, "3 판정 키 규약", "🔴 파일 수(분모)")
    shrunk = bool(n_now is not None and n_prev is not None and n_now < n_prev)
    disclosed = bool(str(n_now) in joined and str(n_prev) in joined
                     and ("대상" in joined))
    old_shrunk = _dig(au, "§C 🔴🔴 「자리 0」 감사") is not None
    f = collections.OrderedDict([
        ("🔴🔴🔴 `R3` --- 무엇을 고쳤나",
         "🔴 **987 판 구현은 「985 → 986」만 봐서 987 «자신의» 대상 집합 변화가 "
         "분자에도 분모에도 안 들어갔다** --- 986 을 친 그 죄를 신설 조건에서 반복했다. "
         "🔴 **988 판은 「이 사이클(988) 대 직전 사이클(987)」을 본다**"),
        ("🔴🔴 988 `⑤′` §3 대상 수", n_now),
        ("🔴🔴 987 `⑤′` §3 대상 수", n_prev),
        ("🔴🔴🔴 줄었나", shrunk),
        ("🔴🔴 문서가 두 수를 «둘 다» 적었나", disclosed),
        ("⚠ 구판(985 → 986) 진단이 산출물에 있나", old_shrunk),
        ("🔴🔴🔴 줄었는데 안 밝혔나", bool(shrunk and not disclosed)),
    ])
    items["F18"] = (f, f["🔴🔴🔴 줄었는데 안 밝혔나"])

    # 🔴 F19 --- 🔴 즉시 정정: 「점추정 합계 리터럴」 grep 을 더한다
    sh = _dig(ctx["power987"] or {}, "§4 🔴🔴 983 모양 자 — 구간으로 · 확정 / 미확정",
              "🔴 λ 별") or {}
    sums = sorted({v.get("⚠ 986 이 실은 점추정 합계(「원리상 못 재는 칸 쌍 수」)")
                   for v in sh.values() if v.get("⚠ 986 이 실은 점추정 합계(「원리상 못 재는 칸 쌍 수」)")
                   is not None})
    sum_lit = []
    for s in sums:
        pat = r"(?<![\d.])%s\s*/\s*\d" % re.escape(str(s))
        for m in re.finditer(pat, joined):
            w = joined[max(0, m.start() - 200):m.end() + 200]
            if not any(x in w for x in ("확정", "미확정", "구간", "986 이 실은")):
                sum_lit.append({"합계": s, "자리": m.group()})
                break
    said = all("미확정" in (_text(p) or "") for p in (BODY[0], PR_BODY))
    f = collections.OrderedDict([
        ("🔴 등록한 자기 논지", "🔴 **「구간이 넓으면 점추정을 못 박지 마라」**"),
        ("🔴 986 이 실은 점추정 합계(바늘)", sums),
        ("🔴🔴🔴 즉시 정정 — 「합계 리터럴」 grep(987 구현엔 없었다)", sum_lit or "없음"),
        ("🔴🔴 판정문·PR 본문이 「미확정」을 «적었나»", said),
        ("🔴🔴🔴 자기 논지를 어겼나", bool(sum_lit or not said)),
    ])
    items["F19"] = (f, f["🔴🔴🔴 자기 논지를 어겼나"])

    # 🔴🔴🔴 F20 --- 등록한 판정식 == 채점기가 평가한 식
    cert = ctx["certify"] or {}
    eighth = cert.get("§마 🔴🔴🔴 ⑧ 등록한 판정식 == 채점기가 평가한 식(988 신설)") or {}
    mine8 = _dig(au, "§B 🔴🔴🔴 여덟째 칸 — 등록 판정식 대조", "🔴🔴 988 자신에 문다(㉠ 엄격)") or {}
    same = mine8.get("🔴🔴🔴 ㉠ 두 집합이 같은가")
    f = collections.OrderedDict([
        ("🔴🔴🔴 ㉠ 사전등록 §5 의 키 경로 집합 == 선언표 `PRED_DEF` 의 그것", same),
        ("🔴 사전등록에만 있는 키 경로", mine8.get("🔴 ㉠ 사전등록에만 있는 키 경로")),
        ("🔴 선언표에만 있는 키 경로", mine8.get("🔴 ㉠ 선언표에만 있는 키 경로")),
        ("🔴 988 자신에서 어긋난 예측", mine8.get("🔴🔴 어긋난 예측")),
        ("🔴🔴 `certify` 여덟째 칸이 낸 값", eighth.get("🔴🔴🔴 전부 같은가")),
        ("🔴🔴 검정력 시연 — 987 에서 어긋난 예측",
         _dig(au, "§B 🔴🔴🔴 여덟째 칸 — 등록 판정식 대조", "🔴🔴 987 에서 어긋난 예측")),
        ("🔴🔴🔴 다른가", bool(same is not True)),
    ])
    items["F20"] = (f, f["🔴🔴🔴 다른가"])

    # 🔴🔴🔴 F21 --- 등록한 자를 강등하고 안 밝혔나
    demoted_said = bool("강등" in joined and "값 대조" in joined)
    f = collections.OrderedDict([
        ("🔴 988 이 등록한 한글 수사 자 수", 2),
        ("🔴 988 이 «판정에 쓴» 자 수",
         len([1 for k in ("🔴🔴🔴 자 ① 바늘 대조(조항 59-나)",
                          "🔴🔴🔴 자 ② 값 대조(조항 59-나 · 🔴 987 이 강등한 자)")
              if k in kr])),
        ("🔴🔴 987 의 강등을 문서가 «밝혔나»", demoted_said),
        ("🔴🔴🔴 강등하고 안 밝혔나",
         bool(kr.get("🔴🔴🔴 자 ② 값 대조(조항 59-나 · 🔴 987 이 강등한 자)") is None
              or not demoted_said)),
    ])
    items["F21"] = (f, f["🔴🔴🔴 강등하고 안 밝혔나"])

    # 🔴🔴🔴 F22 --- 「자리 0」을 「통과」로 셌나
    zero = []
    for nm, blk in (("§K 자 ① 바늘 대조",
                     kr.get("🔴🔴🔴 자 ① 바늘 대조(조항 59-나)")),
                    ("§K 자 ② 값 대조",
                     kr.get("🔴🔴🔴 자 ② 값 대조(조항 59-나 · 🔴 987 이 강등한 자)")),
                    ("F14 리터럴 통과", ctx["astpass"].get("🔴🔴🔴 조항 59-나 판정")),
                    ("F15 손 전사", ctx["handlit"].get("🔴🔴🔴 조항 59-나 판정")),
                    ("F08 미식별 점추정", items["F08"][0].get("🔴🔴🔴 조항 59-나 판정"))):
        if isinstance(blk, dict) and blk.get("🔴🔴🔴 미측정인가"):
            zero.append(nm)
    f = collections.OrderedDict([
        ("🔴 자별 `조항 59-나` 갈래",
         {nm: (blk or {}).get("🔴🔴🔴 갈래(조항 59-나)")
          for nm, blk in (("§K 자 ① 바늘 대조", kr.get("🔴🔴🔴 자 ① 바늘 대조(조항 59-나)")),
                          ("§K 자 ② 값 대조",
                           kr.get("🔴🔴🔴 자 ② 값 대조(조항 59-나 · 🔴 987 이 강등한 자)")),
                          ("F14 리터럴 통과", ctx["astpass"].get("🔴🔴🔴 조항 59-나 판정")),
                          ("F15 손 전사", ctx["handlit"].get("🔴🔴🔴 조항 59-나 판정")),
                          ("F08 미식별 점추정", items["F08"][0].get("🔴🔴🔴 조항 59-나 판정")))}),
        ("🔴🔴🔴 「미측정」인 자", zero or "없음"),
        ("🔴🔴 987 의 「자리 0」 감사(§C)",
         _dig(au, "§C 🔴🔴 「자리 0」 감사", "🔴🔴🔴 미측정인 자")),
        ("🔴🔴🔴 「자리 0」을 「통과」로 셌나", bool(zero)),
    ])
    items["F22"] = (f, f["🔴🔴🔴 「자리 0」을 「통과」로 셌나"])

    # 🔴🔴🔴 F23 --- 아는 red 를 명부에 안 넣었나
    G = au.get("§G 🔴 `⑤′` §3 명부 — 데몬 셋(아는 red)") or {}
    sinks = G.get("🔴🔴🔴 대상에 들면 §3 을 떨어뜨리는 파일")
    sinks = sinks if isinstance(sinks, list) else []
    targets3 = _dig(ctx["five"] or {}, "3 판정 키 규약", "파일별") or {}
    inside = [s for s in sinks if s in targets3]
    f = collections.OrderedDict([
        ("🔴 아는 red(대상에 들면 §3 을 떨어뜨리는 파일)", sinks or "없음"),
        ("🔴🔴 이 사이클 `⑤′` §3 대상에 «들어 있나»", inside or "없음"),
        ("🔴 `⑤′` §3 대상 수", len(targets3)),
        ("🔴🔴 §3 이 «떨어졌나»", _dig(ctx["five"] or {}, "3 판정 키 규약", "통과") is False),
        ("🔴 987 이 무엇을 했나",
         "🔴 **987 은 데몬 셋의 통과 키를 0/0/0 으로 «재고도» 명부에 안 넣었다** --- "
         "아는 red 를 안 켰다. 🔴 **988 은 `--keyaudit` 로 전량 넘겨 «떨어진 채로» 계상한다**"),
        ("🔴🔴🔴 아는 red 를 명부에 «안 넣었나»", bool(sinks and len(inside) < len(sinks))),
    ])
    items["F23"] = (f, f["🔴🔴🔴 아는 red 를 명부에 «안 넣었나»"])

    rows, bad = collections.OrderedDict(), []
    for k, (detail, broke) in items.items():
        d = collections.OrderedDict(detail)
        d["🔴🔴🔴 반증됐나"] = bool(broke)
        d["통과"] = bool(not broke)
        rows[k] = d
        if broke:
            bad.append(k)
    return rows, bad


def canon_live(au, sc987, sc986, pr987):
    """🔴🔴🔴 **지연 없는 일곱째 칸** --- 사전등록 §8 정본 == 고정 ref 산출물의 그 칸."""
    src = {
        "987 예측 분자": _dig(sc987 or {}, "§5 🔴 예측", "🔴 분자"),
        "987 최상위 통과": (sc987 or {}).get("통과"),
        "987 audit §C 986 절 3 통과": (_dig(
            au or {}, "§A 🔴🔴🔴 987 의 최상위 통과를 등록 정의대로 다시 채점한다") or {}) and
        _dig(au or {}, "§A 🔴🔴🔴 987 의 최상위 통과를 등록 정의대로 다시 채점한다",
             "🔴 예측별", "P6 고정 명부로 다시 계산하면 986 의 `⑤′` §3 초록이 뒤집힌다",
             "🔴 987 채점기가 낸 값"),
        "987 §K 센 한글 수사 수": _dig(sc987 or {}, "§K 🔴🔴 규칙 D — 한글 수사(987 신설)",
                               "🔴🔴 센 한글 수사 수"),
        "987 §K 바늘이 걸린 수사 수": sum(
            (r.get("🔴 바늘이 걸린 수사") or 0)
            for r in (_dig(sc987 or {}, "§K 🔴🔴 규칙 D — 한글 수사(987 신설)",
                           "🔴 대상별") or {}).values() if isinstance(r, dict)),
        "987 §K 값 대조 어긋남 수": _dig(sc987 or {}, "§K 🔴🔴 규칙 D — 한글 수사(987 신설)",
                               "⚠ 값이 치환표 밖인 수사(진단 · 조항 61)"),
        "987 산문 등록 안 된 주장 문장 수": _dig(
            pr987 or {}, "§B 🔴🔴 뒤집은 자 — 분모를 «문서»가 정한다",
            "🔴🔴🔴 등록 안 된 주장 문장 수"),
        "986 예측 분자": _dig(sc986 or {}, "§5 🔴 예측", "🔴 분자"),
    }
    rows, bad, miss = collections.OrderedDict(), [], []
    for name, want in CY.PREREG_CANON.items():
        if name not in src:
            rows[name] = {"🔴 사전등록이 박은 값": want, "🔴": "🔴 그 키 경로가 «없다»"}
            miss.append(name)
            continue
        live = src[name]
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


def live_sixth(tb, ruleD, kor, shape, feeds, six, zero_n):
    T = _cells(tb) or {}
    live = {
        "채.규칙D표밖": ruleD["🔴🔴 표 밖 합"],
        "채.규칙D분모": ruleD["🔴🔴 채점 분모"],
        "채.규칙D통과": ruleD["통과"],
        "채.한글어긋남": kor["🔴🔴🔴 바늘 대조 어긋난 수사 수"],
        "채.한글값어긋남": kor["🔴🔴🔴 값 대조 어긋난 수사 수"],
        "채.한글분모": kor["🔴🔴 센 한글 수사 수"],
        "채.한글걸림": kor["🔴🔴🔴 바늘이 걸린 수사 수"],
        "채.한글바늘수": kor["🔴🔴 등록 바늘 수"],
        "채.한글통과": kor["통과"],
        "채.68근거없음": shape["🔴🔴 근거 없는 모양 주장 수"],
        "채.68통과": shape["통과"],
        "채.F5분모": feeds["🔴 분모"],
        "채.F5통과": feeds["통과"],
        "채.여섯자리": six["통과"],
        "채.미측정수": zero_n,
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
        ("🔴🔴🔴 반증조건 «제목»을 문서에 안 싣는다(`R4`)",
         "🔴 **988 은 반증조건 키를 `F01`~`F23` «식별자만»으로 낸다.** "
         "🔴 987 은 한글 수사 쪽만 닫았고 «아라비아»(조건 9·10·11·12)는 그대로여서 "
         "조건 하나라도 반증되면 **같은 주기 2 진동이 아라비아 쪽에서 난다**"),
    ])


def stage(ref, prereg_commit, five_name, it):
    t0 = CY.now()
    CY.begin(ref)
    cs0 = CY.code_stamp()
    rules = LG.ALLOW_CTX + INHERIT
    tb = _load(TBL)
    au = _load("out988_audit.json", must=True)
    ct = _load("out988_certify.json")
    fp = _load(five_name)
    fp7 = _load("fiveprime_987.json")
    _r7, sc987 = CY.fixed_ref_json(CY.REF_987, "runners/out987_score.json")
    _r8, pw987 = CY.fixed_ref_json(CY.REF_987, "runners/out987_power.json")
    _r9, pr987 = CY.fixed_ref_json(CY.REF_987, "runners/out987_prose.json")
    _r6, sc986 = CY.fixed_ref_json(CY.REF_986, "runners/out986_score.json")

    reg = registered_denominators()
    ruleD = rule_d(tb, rules)
    kor = rule_d_korean(tb)
    shape = shape_audit()
    feeds = feeds_stamp()
    astpass = ast_pass_all()
    handlit = hand_lit_all()
    diskread = disk_read_audit()
    n_falsify = 23
    six = six_places(collections.OrderedDict([
        ("반증조건 분모", (n_falsify, "반증조건")),
        ("`⑤′` 분모", (reg["🔴 `⑤′` 분모"], "⑤′")),
        ("규칙 D 대상 수", (ruleD["🔴🔴 채점 분모"], "규칙 D")),
    ]))
    zero_n = len([1 for blk in (kor.get("🔴🔴🔴 자 ① 바늘 대조(조항 59-나)"),
                                kor.get("🔴🔴🔴 자 ② 값 대조(조항 59-나 · 🔴 987 이 강등한 자)"),
                                astpass.get("🔴🔴🔴 조항 59-나 판정"),
                                handlit.get("🔴🔴🔴 조항 59-나 판정"))
                  if isinstance(blk, dict) and blk.get("🔴🔴🔴 미측정인가")])
    live_cert = live_sixth(tb, ruleD, kor, shape, feeds, six, zero_n)
    cl = canon_live(au, sc987, sc986, pr987)
    ctx = {"prereg_commit": prereg_commit, "reg": reg, "ruleD": ruleD, "korean": kor,
           "five": fp, "five987": fp7, "six": six, "certify": ct, "feeds": feeds,
           "table": tb, "live_cert": live_cert, "canon_live": cl, "diskread": diskread,
           "astpass": astpass, "handlit": handlit, "power987": pw987, "audit": au,
           "n_falsify": n_falsify, "n_predict": len(PRED_DEF), "n_cert": 8}
    rows, bad = falsify(ctx)
    prows, hit = predict(ctx)

    out = collections.OrderedDict()
    out["무엇"] = "988 채점 — 🔴 반증조건 23(식별자) · 예측 4(선언표) · 규칙 D 여섯(+ 한글 수사 자 «둘»)"
    out["🔴 축"] = "C1 상태→예측(곁) · 자기 자(몸통)"
    out["사전등록"] = PREREG
    out["🔴🔴 조항 60-다 · 사전등록이 박은 분모"] = reg
    out["🔴 `⑤′` 반복"] = it
    out["§6 🔴 반증조건"] = collections.OrderedDict([
        ("🔴 분모", n_falsify), ("🔴 조건별", rows),
        ("🔴🔴 반증된 조건(식별자만 · R4)", bad or "없음"),
        ("🔴🔴 분자 / 분모", "%d / %d" % (n_falsify - len(bad), n_falsify)),
        ("🔴 제목은 사전등록에서만 읽는다(`R4`)", dict(F_TITLE)),
        ("통과", bool(not bad)),
    ])
    out["§5 🔴 예측"] = collections.OrderedDict([
        ("🔴 분모", len(PRED_DEF)), ("🔴 예측별", prows),
        ("🔴🔴 분자 / 분모", "%d / %d" % (hit, len(PRED_DEF))),
        ("🔴 분자", hit),
        ("🔴🔴🔴 채점기는 «선언표 하나»로만 계산한다", dict(declared_key_paths())),
        ("통과", bool(hit == len(PRED_DEF))),
    ])
    out["§D 🔴 규칙 D 감사(분모 여섯)"] = ruleD
    out["§K 🔴🔴 규칙 D — 한글 수사(자 «둘»)"] = kor
    out["§59나 🔴🔴🔴 조항 59-나 — 「자리 0」 감사"] = collections.OrderedDict([
        ("🔴 무엇", "🔴🔴🔴 **「자리 0」은 「통과」가 아니라 「미측정」이다**(988 신설)"),
        ("🔴 자별", {"§K 자 ① 바늘 대조": kor.get("🔴🔴🔴 자 ① 바늘 대조(조항 59-나)"),
                  "§K 자 ② 값 대조":
                      kor.get("🔴🔴🔴 자 ② 값 대조(조항 59-나 · 🔴 987 이 강등한 자)"),
                  "F14 리터럴 통과": astpass.get("🔴🔴🔴 조항 59-나 판정"),
                  "F15 손 전사": handlit.get("🔴🔴🔴 조항 59-나 판정")}),
        ("🔴🔴🔴 미측정인 자 수", zero_n),
        ("🔴🔴 987 에서 미측정으로 재분류된 조건 수",
         _dig(au, "§C 🔴🔴 「자리 0」 감사", "🔴🔴🔴 미측정으로 재분류된 조건 수")),
        ("통과", bool(zero_n == 0)),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "🔴 **이 사이클의 자 중 「미측정」이 0 인가**"),
    ])
    out["§68 🔴 조항 68 모양 주장 감사"] = shape
    out["§F5 🔴 인용 산출물 도장"] = feeds
    out["§9 🔴🔴 여섯 자리가 같은 수를 적나"] = six
    out["§16 🔴🔴 넓힌 「전」 바늘 감사"] = collections.OrderedDict(
        list(diskread.items()) + [
            ("통과", bool(diskread["🔴🔴🔴 면제 밖에서 걸린 자리 수"] == 0)),
            ("🔴 이 절의 `통과` 가 뜻하는 것", "🔴 **면제 밖에서 디스크 경로를 읽는 자리가 0 인가**"),
        ])
    out["§12 🔴🔴🔴 지연 없는 여섯째 칸"] = collections.OrderedDict(
        list(live_cert.items()) + [
            ("통과", bool(live_cert["🔴 전부 같은가"])),
            ("🔴 이 절의 `통과` 가 뜻하는 것", "🔴 **치환표가 «지금» 채점기가 낸 값을 들고 있는가**"),
        ])
    out["§17 🔴🔴🔴 지연 없는 일곱째 칸(사전등록 정본)"] = collections.OrderedDict(
        list(cl.items()) + [
            ("통과", bool(cl["🔴 전부 같은가"])),
            ("🔴 이 절의 `통과` 가 뜻하는 것",
             "🔴 **사전등록 §8 이 박은 정본 값이 산출물의 그 칸과 «전부» 같은가**"),
        ])
    out["§AST 🔴 리터럴 `통과` 금지"] = astpass
    out["§R3 🔴 손 전사 수 리터럴 금지"] = handlit
    out["통과"] = bool(out["§6 🔴 반증조건"]["통과"] and ruleD["통과"] and kor["통과"]
                     and shape["통과"] and out["§5 🔴 예측"]["통과"]
                     and out["§59나 🔴🔴🔴 조항 59-나 — 「자리 0」 감사"]["통과"])
    out["🔴🔴🔴 최상위 `통과` 의 정의"] = {
        "985 판": "반증조건 ∧ 규칙 D",
        "986 판": "반증조건 ∧ 규칙 D ∧ §68 ∧ §5 예측",
        "987 판": "반증조건 ∧ 규칙 D(아라비아) ∧ §K(한글 수사) ∧ §68 ∧ §5 예측",
        "🔴 988 판": "987 판 ∧ **§59-나(「자리 0」이 0 개)**",
        "🔴 왜 넓혔나": "🔴 **987 의 `§K` 는 「바늘 0 자리」로 초록이었다** --- "
                  "「깨끗함」과 「안 봤음」을 안 가르면 최상위 `통과` 가 «안 봤음»을 «통과»로 센다",
    }
    CY.write(OUT, out, ref, cs0, t0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["score"])
    ap.add_argument("--ref", required=True)
    ap.add_argument("--prereg-commit", required=True)
    ap.add_argument("--five", default="fiveprime_988.json")
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
        "반증된": r["§6 🔴 반증조건"]["🔴🔴 반증된 조건(식별자만 · R4)"],
        "예측": r["§5 🔴 예측"]["🔴🔴 분자 / 분모"],
        "규칙 D 표 밖": r["§D 🔴 규칙 D 감사(분모 여섯)"]["🔴🔴 표 밖 합"],
        "한글 바늘 어긋남": r["§K 🔴🔴 규칙 D — 한글 수사(자 «둘»)"]["🔴🔴🔴 바늘 대조 어긋난 수사 수"],
        "한글 값 어긋남": r["§K 🔴🔴 규칙 D — 한글 수사(자 «둘»)"]["🔴🔴🔴 값 대조 어긋난 수사 수"],
        "미측정": r["§59나 🔴🔴🔴 조항 59-나 — 「자리 0」 감사"]["🔴🔴🔴 미측정인 자 수"],
    }, ensure_ascii=False))
    return 0 if r["통과"] else 1


if __name__ == "__main__":
    sys.exit(main())
