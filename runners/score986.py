#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""986 채점 — 🔴 반증조건 **14** · 예측 **6** · 규칙 D 대상 **여섯(+PR 본문)**.

🔴 **985 와 다른 것 넷(사전등록이 측정 전에 박았다):**

1. **규칙 D 대상이 여섯이다** --- 다섯에 **`docs/pr_986.md`(PR 본문)**를 더한다.
   **PR #243 본문이 네 곳에서 문서와 달랐다**(티처 #124 C2).
2. **`[수리] R5` --- 최상위 `통과` 에 `§68`·`§5 예측` 을 넣는다.**
   985 의 정의는 「반증조건 ∧ 규칙 D」뿐이라 **자기 헤드라인을 죽이는 자 둘이
   판정 규칙 밖**이었다(`§68` 불통과 · `§5` 불통과인데 최상위는 `True`).
3. **`[수리] R3` --- 손 전사 자의 분모가 「이 사이클 러너 전량」**이다.
4. **F5 도장의 분모가 「원장이 싣는 산출물 전량」**이다 ---
   **인용을 안 하면 도장 검사를 피한다**(티처 #124 즉시정정 ④).

씀:
    python3 runners/score986.py --stage score --ref <sha> --prereg-commit <sha> …
"""
import argparse
import ast
import collections
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

import cycle986 as CY                                  # noqa: E402
import ledger as LG                                    # noqa: E402
import score985 as S5                                  # noqa: E402
import audit986 as A6                                  # noqa: E402
import certify986 as C6                                # noqa: E402

#: 🔴🔴🔴 **여섯째 칸을 «지연 없이» 재려고 빼는 칸**(조항 60 --- 조용히 안 뺀다).
#:
#: 🔴 **왜 빼나.** 반증조건 11 이 «디스크의» `out986_certify.json` 을 읽으면
#: **한 회 뒤진 값**을 읽는다. 그러면 `채.반증분자모` 가 조건 11 의 결과에 «다시»
#: 의존해 **주기 4 의 진동**이 생기고 고정점에 원리상 도달 못 한다(986 실측).
#: 🔴 그래서 조건 11 은 **채점기 자신이 «지금» 계산한 값**과 치환표를 견주고,
#: **자기 결과에 의존하는 칸 여덟을 뺀다.** 뺀 이름을 여기 박고 산출물에 싣는다.
#: 🔴 **전량 16 칸 검사는 `certify986` 이 그대로 한다** --- 그것이 정본이고
#: 985 검정력 시연도 그 자로 낸다.
SELF_DEP = ("채.반증분자모", "채.반증분모", "채.반증된", "채.반증통과",
            "채.예측분자모", "채.예측분자", "채.예측통과", "채.최상위통과")

OUT = "runners/out986_score.json"
PREREG = "docs/prereg_986_sixth_cell_power_ci.md"
BODY = ("docs/판정_986.md", "docs/card_986.md", "docs/handoff_986.md")
PR_BODY = "docs/pr_986.md"
GOAL = "docs/목표.md"
DEN = "data/lab/denominator.json"
TBL = "runners/out986_table.json"
CARD_OUT = os.path.expanduser(
    "~/.claude/projects/-Users-ax-world-model/memory/project-lab-state.md")
MARK_A = S5.MARK_A
MARK_B = S5.MARK_B
LEDGER_KEY = "노트 986"

FEED_RE = re.compile(
    r"`?((?:runners/)?(?:out986_[a-z0-9_]+|fiveprime_986[a-z0-9_]*)\.json)`?")
#: 🔴 사전등록이 «사전»에 뺀 것 --- `⑤′` 산출물(고정점이 원리상 불가)
FEED_EXEMPT = re.compile(r"fiveprime_986")

SHAPE_RE = S5.SHAPE_RE
SHAPE_OK = S5.SHAPE_OK
SHAPE_WIN = S5.SHAPE_WIN

DEN_FALSIFY = re.compile(r"##\s*§6\s*반증조건\s*\(분모\s*\*\*(\d+)\*\*")
DEN_PREDICT = re.compile(r"##\s*§5\s*예측\s*\(분모\s*\*\*(\d+)\*\*")
DEN_FIVE = re.compile(r"`⑤′`\s*분모\s*—\s*🔴\s*\*\*등록\s*(\d+)")
DEN_RULED = re.compile(r"규칙 D 대상 수\s*\|\s*\*\*(\d+)\*\*")
DEN_CERT = re.compile(r"`certify`\s*칸 수\s*\|\s*\*\*(\d+)\*\*")

INHERIT = S5.INHERIT


def _git(*a):
    return subprocess.check_output(["git"] + list(a), cwd=str(ROOT)).decode("utf-8")


def _text(rel):
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


# ══════════════════════════════════════════════════════════════════════
# §D 규칙 D --- 🔴 **대상 여섯(+PR 본문)**
# ══════════════════════════════════════════════════════════════════════
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


def rule_d(tb, rules):
    S = S5._table_set(tb)
    rows, tot = collections.OrderedDict(), 0
    targets = collections.OrderedDict()
    for p in BODY:
        targets[p] = _text(p)
    targets["🔴 `docs/목표.md` 「정본 유보」 절"] = _holdout_slice()
    targets["🔴 원장 `%s` 항목" % LEDGER_KEY] = _ledger_entry_text()
    #: 🔴🔴🔴 **986 신설 --- 여섯째 대상은 PR 본문이다**(사전등록 §2-2)
    targets["🔴🔴🔴 PR 본문 `%s`(986 신설)" % PR_BODY] = _text(PR_BODY)
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
        ("🔴 무엇", "🔴 **규칙 D --- 치환표에 없는 수를 본문에 못 쓴다**"),
        ("🔴🔴 채점 분모", len(targets)),
        ("🔴🔴 분모의 내력(조항 60)", {"985 판": 5, "986 판": len(targets),
                              "🔴 더한 것": PR_BODY,
                              "🔴 왜": "🔴 **PR #243 본문이 네 곳에서 문서와 달랐다** --- "
                                     "985 는 다섯 자리를 완벽히 고쳤는데 **어떤 자도 "
                                     "안 덮는 여섯째 자리**를 남겼다(티처 #124 C2)"}),
        ("🔴 대상", list(targets.keys())),
        ("🔴 대상별", rows),
        ("🔴🔴 표 밖 합", tot),
        ("🔴 못 읽은 대상", unread or "없음"),
        ("🔴 치환표 칸 수", len(T)),
        ("🔴 치환표 sha256", (tb or {}).get("🔴🔴 표 sha256")),
        ("통과", bool(tot == 0 and not unread)),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **여섯 대상 전부에서 치환표 밖의 수가 0 인가.** 하나라도 못 읽으면 불통과다"),
    ])


def shape_audit():
    """🔴 조항 68 --- **PR 본문도 대상이다**(986)."""
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
         "「그 근거가 «그 모양의» 근거인가」는 원리상 안 본다. **986 도 이 자를 안 고쳤다**"),
        ("🔴 문서별", rows),
        ("🔴🔴 근거 없는 모양 주장 수", bad),
        ("통과", bool(bad == 0 and all(
            v.get("근거 없는 모양 낱말") is not None for v in rows.values()))),
        ("🔴🔴🔴 이 절이 최상위 `통과` 에 «든다»(986 R5)",
         "🔴 985 는 이 자가 **불통과(근거 없는 모양 주장 5)**인데 최상위 `통과` 를 `True` 로 "
         "게재했다 --- **자기 헤드라인을 죽이는 자를 판정 규칙에서 뺐다**(티처 #124 3순위 R5)"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §F5 도장 --- 🔴 **분모는 「원장이 싣는 산출물 전량」**
# ══════════════════════════════════════════════════════════════════════
def feeds_stamp():
    cited = collections.OrderedDict()
    for p in list(BODY) + [PR_BODY]:
        t = _text(p)
        if t is None:
            continue
        for m in FEED_RE.finditer(t):
            cited.setdefault(m.group(1).split("/")[-1], []).append(p)
    #: 🔴🔴🔴 **986 --- 분모를 「원장이 싣는 산출물 전량」으로.**
    #:  인용을 안 하면 도장 검사를 피하는 길을 막는다(티처 #124 즉시정정 ④).
    ent = _ledger_entry_text() or ""
    in_ledger = sorted(set(
        re.findall(r"(?:runners/)?((?:out986|fiveprime)_?[\w]*\.json)", ent)))
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
                    "F5 통과": (st or {}).get("🔴 F5 통과"),
                    "도장이 있나": bool(st)}
        if not ok:
            bad.append(nm)
    return collections.OrderedDict([
        ("🔴 무엇", "🔴 **본문·PR 본문·원장이 «싣는» 산출물의 도장이 전부 F5 통과인가**"),
        ("🔴🔴🔴 986 이 바꾼 것 — 분모가 「인용된 것」이 아니라 「원장이 싣는 산출물 전량」이다",
         "🔴 **985 는 분모가 7 인데 원장은 13 을 실었고 밖에 있는 다섯 중 넷이 미자백이었다** "
         "--- **인용을 안 하면 도장 검사를 피한다**(티처 #124 즉시정정 ④)"),
        ("🔴 인용된 산출물(기계 추출)", sorted(cited)),
        ("🔴 원장 `%s` 항목이 싣는 산출물" % LEDGER_KEY, in_ledger),
        ("🔴🔴 인용 안 됐는데 원장이 싣는 것(985 가 놓친 자리)",
         sorted(set(in_ledger) - set(cited)) or "없음"),
        ("🔴 분모", len(rows)),
        ("🔴🔴 사전등록이 «사전»에 뺀 것(`⑤′` 산출물)", exempt or "없음"),
        ("🔴🔴 뺀 수", len(exempt)),
        ("🔴 산출물별", rows),
        ("🔴 파일이 없는 것(= 「통과」가 아니다 · 조항 59)", missing or "없음"),
        ("🔴🔴 F5 를 못 넘은 것", bad or "없음"),
        ("통과", bool(rows and not bad)),
    ])


# ══════════════════════════════════════════════════════════════════════
# §9 여섯 자리 --- 🔴 **엄격 변이체로 «등록»했다**(985 handoff 가 요구했다)
# ══════════════════════════════════════════════════════════════════════
def six_places(five, needles):
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
        ("🔴🔴🔴 986 이 바꾼 것 — 판정을 «엄격 변이체»로 한다(985 handoff 가 요구했다)",
         "🔴 985 는 「부분 문자열」로 판정하고 엄격 변이체를 «진단»으로만 실었다 --- "
         "작은 수는 어느 긴 문서에나 우연히 있다. 986 은 **그 수가 «그 이름 곁» ±80 자 "
         "안에 있나**를 판정에 쓴다"),
        ("🔴 바늘", {k: v[0] for k, v in needles.items()}),
        ("🔴 닻(±80 자 창의 중심)", {k: v[1] for k, v in needles.items()}),
        ("🔴 분모(자리 수)", len(places)),
        ("⚠ 느슨한 자(985 판 · 부분 문자열) — 진단", rows),
        ("🔴🔴🔴 엄격 자(986 판 · 판정에 쓴다)", strict_rows),
        ("🔴🔴 엄격 자로 못 채우는 자리", bad or "없음"),
        ("통과", bool(not bad)),
    ])


# ══════════════════════════════════════════════════════════════════════
# AST --- 리터럴 `통과` · 손 전사
# ══════════════════════════════════════════════════════════════════════
def ast_pass_all():
    rows, tot, unread = collections.OrderedDict(), 0, []
    for rel in CY.RAN_986:
        h = S5.ast_pass_hits(rel)
        if h is None:
            rows[rel] = {"🔴": "🔴 못 읽었다"}
            unread.append(rel)
            continue
        rows[rel] = {"자리 수": len(h), "자리": h or "없음"}
        tot += len(h)
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴 **리터럴 `(\"통과\", True)` 금지**(983 R1 · AST)"),
        ("🔴 분모(이 사이클 러너 전량)", len(CY.RAN_986)),
        ("🔴 러너별", rows),
        ("🔴🔴🔴 리터럴 자리 수", tot),
        ("🔴 못 읽은 러너(= 0 이 아니다)", unread or "없음"),
        ("통과", bool(tot == 0 and not unread)),
    ])


def hand_lit_all(au):
    """🔴 `[수리] R3` --- 손 전사 자의 **결과를 `audit986` 에서 읽는다**(자는 거기 있다)."""
    sec = (au or {}).get("§C 🔴🔴🔴 R3 손 전사 자의 분모") or {}
    tot = sec.get("🔴🔴🔴 신판 --- 986 러너의 손 전사 자리 수")
    demo = sec.get("🔴🔴 검정력 시연(조항 64) — 같은 신판 자를 985 의 러너 전량에 문다") or {}
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴🔴 **손 전사 수 리터럴 금지** --- 분모는 «이 사이클 러너 전량»(R3)"),
        ("🔴 분모", sec.get("🔴 신판 분모(이 사이클 러너 전량)")),
        ("🔴🔴🔴 986 러너의 손 전사 자리 수", tot),
        ("🔴 러너별", sec.get("🔴 신판 --- 986 러너별")),
        ("🔴🔴 이 자가 985 의 `= 3` 을 잡았나(검정력 · 조항 64)",
         demo.get("🔴🔴🔴 `audit985.py` 의 `= 3` 을 잡았나")),
        ("🔴 985 러너의 자리 수", demo.get("🔴🔴🔴 985 러너의 손 전사 자리 수")),
        ("통과", bool(tot == 0)),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **986 러너에 손 전사 수 리터럴이 0 인가.** `None` 이면 「모른다」라 불통과다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §6 반증조건 (분모 14)
# ══════════════════════════════════════════════════════════════════════
def falsify(ctx):
    items = collections.OrderedDict()

    # 1 사전등록 blob 을 측정 뒤에 고쳤나
    pc = ctx["prereg_commit"]
    try:
        blob = _git("show", "%s:%s" % (pc, PREREG)).encode("utf-8")
        import hashlib
        was = hashlib.sha256(blob).hexdigest()
    except Exception as e:                                         # noqa: BLE001
        was = "🔴 못 읽었다: %s" % e
    cur = _sha(PREREG)
    f1 = collections.OrderedDict([
        ("🔴 사전등록 단독 커밋", pc),
        ("🔴 그 커밋의 blob sha256", was),
        ("🔴 디스크 sha256", cur),
        ("🔴🔴 고쳤나", bool(was != cur)),
    ])
    items["1 사전등록 blob 을 측정 뒤에 고쳤나"] = (f1, f1["🔴🔴 고쳤나"])

    # 2 막힌 명령을 우회하고 신고 안 했나 (조항 69)
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

    # 3 등록 분모와 다른 수로 채점했나 (조항 60-다)
    reg = ctx["reg"]
    got = {"반증조건": ctx["n_falsify"], "예측": ctx["n_predict"],
           "규칙 D 대상": ctx["ruleD"]["🔴🔴 채점 분모"],
           "certify 칸": ctx["n_cert"]}
    want = {"반증조건": reg["🔴 반증조건 분모(사전등록에서 «읽었다»)"],
            "예측": reg["🔴 예측 분모"], "규칙 D 대상": reg["🔴 규칙 D 대상 수"],
            "certify 칸": reg["🔴 `certify` 칸 수"]}
    diff = sorted(k for k in got if got[k] != want[k])
    f3 = collections.OrderedDict([
        ("🔴 사전등록이 박은 분모", want), ("🔴 채점이 쓴 분모", got),
        ("🔴 어긋난 분모", diff or "없음"),
        ("🔴🔴 다르게 썼나", bool(diff)),
    ])
    items["3 등록 분모와 다른 수로 채점했나(조항 60-다)"] = (f3, f3["🔴🔴 다르게 썼나"])

    # 4 등록한 절을 분모에서 뺐나 (조항 60-나)
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

    # 5 값을 낸 뒤 러너를 고치고 안 다시 돌렸나
    st = CY.stale_outputs()
    f5 = collections.OrderedDict([
        ("🔴 낡은 산출물", st["🔴🔴🔴 낡은 산출물(고치고 안 다시 돌렸다)"]),
        ("🔴 못 읽은 것", st["🔴 못 읽은 것(= 「없다」가 아니다)"]),
        ("🔴🔴 고치고 안 다시 돌렸나", bool(st["🔴🔴🔴 낡은 것이 있나"])),
    ])
    items["5 값을 낸 뒤 러너를 고치고 안 다시 돌렸나"] = (f5, f5["🔴🔴 고치고 안 다시 돌렸나"])

    # 🔴🔴🔴 6 채점기를 다시 돌리고 문서를 안 다시 찍었나 (986 신설)
    sd = CY.stale_docs()
    unknown6 = sd.get("🔴🔴🔴 낡은 문서가 있나") is None
    f6 = collections.OrderedDict([
        ("🔴🔴🔴 무엇", "🔴 **985 의 다섯 문서가 「13/14」를 싣고 정본 채점은 「14/14」였다** "
                   "--- 그 자리를 잇는 자가 이것이다"),
        ("🔴 입력별", sd.get("🔴 입력별")),
        ("🔴 문서를 찍은 뒤 달라진 채점 산출물", sd.get("🔴🔴🔴 문서를 찍은 뒤 달라진 채점 산출물")),
        ("🔴 치환표가 sha 를 안 박은 입력",
         sd.get("🔴 치환표가 sha 를 안 박은 입력(= 「같다」가 아니다 · 조항 59)")),
        ("🔴🔴🔴 안 다시 찍었나(「모른다」도 반증이다 · 조항 59)",
         bool(sd.get("🔴🔴🔴 낡은 문서가 있나") or unknown6)),
    ])
    items["6 🔴🔴🔴 채점기를 다시 돌리고 문서를 안 다시 찍었나(986 신설)"] = \
        (f6, f6["🔴🔴🔴 안 다시 찍었나(「모른다」도 반증이다 · 조항 59)"])

    # 🔴🔴 7 PR 본문이 문서와 다른가 (986 신설)
    rd = ctx["ruleD"]
    pr_row = None
    for k, v in (rd.get("🔴 대상별") or {}).items():
        if PR_BODY in k:
            pr_row = v
    f7 = collections.OrderedDict([
        ("🔴 PR 본문이 규칙 D 분모 안인가", bool(pr_row is not None)),
        ("🔴 PR 본문의 「표 밖」 수", (pr_row or {}).get("표 밖")),
        ("🔴 PR 본문이 치환표에서 «지어졌나»(생성기가 찍은 표지)",
         bool((_text(PR_BODY) or "").find("<!-- 986:pr:생성물 -->") >= 0)),
        ("🔴🔴 다른가", bool(pr_row is None or pr_row.get("표 밖") != 0
                        or "<!-- 986:pr:생성물 -->" not in (_text(PR_BODY) or ""))),
    ])
    items["7 🔴🔴 PR 본문이 문서와 다른가(986 신설)"] = (f7, f7["🔴🔴 다른가"])

    # 🔴🔴 8 식별되지 않는 수를 소수점으로 못 박았나 (986 신설)
    pw = ctx["power"] or {}
    b = (pw.get("§1 🔴🔴🔴 부트스트랩 감싼 δ 쓸기") or {}).get("🔴 λ 별") or {}
    ident = {k: v.get("🔴🔴 식별됐나(구간 폭이 δ 격자 한 칸 이하인가)") for k, v in b.items()}
    joined = "\n".join((_text(p) or "") for p in list(BODY) + [PR_BODY])
    dead = sorted(set(re.findall(r"\b6\.380994\d*\b|\b23\.06539\d*\b", joined)))
    #: 🔴 985 가 못 박은 두 수가 **자기 주장으로** 다시 실렸나. 「985 가 실었다」를
    #:  인용하는 것은 정정이라 허용하고, 그때는 곁에 「구간」이라는 낱말이 있어야 한다.
    naked = []
    for m in re.finditer(r"6\.380994\d*|23\.06539\d*", joined):
        w = joined[max(0, m.start() - 220):m.end() + 220]
        if not any(x in w for x in ("구간", "985 가", "못 박", "식별")):
            naked.append(m.group())
    f8 = collections.OrderedDict([
        ("🔴 λ 별 「식별됐나」", ident),
        ("🔴 문서에 실린 985 의 못 박은 수", dead or "없음"),
        ("🔴🔴 그중 «구간·정정 맥락 없이» 실린 것", naked or "없음"),
        ("🔴🔴🔴 못 박았나", bool(naked)),
    ])
    items["8 🔴🔴 식별되지 않는 수를 소수점으로 못 박았나(986 신설)"] = (f8, f8["🔴🔴🔴 못 박았나"])

    # 9 규칙 D
    f9 = collections.OrderedDict([
        ("🔴 표 밖 합", rd["🔴🔴 표 밖 합"]), ("🔴 채점 분모", rd["🔴🔴 채점 분모"]),
        ("🔴 못 읽은 대상", rd["🔴 못 읽은 대상"]),
        ("🔴🔴 전부 치환표 칸인가", bool(rd["통과"])),
    ])
    items["9 규칙 D — 여섯 대상의 수가 전부 치환표 칸인가"] = (f9, not f9["🔴🔴 전부 치환표 칸인가"])

    # 10 여섯 자리
    sx = ctx["six"]
    items["10 여섯 자리가 같은 수를 적나(엄격 자)"] = (sx, not sx["통과"])

    # 11 문서 고리 수렴 --- 🔴 **지연 없이** 잰다(위 `SELF_DEP` 주석을 읽어라)
    ct = ctx["certify"] or {}
    mine = ct.get("§가 🔴🔴🔴 986 자신") or {}
    live = ctx["live_cert"]
    f11 = collections.OrderedDict([
        ("🔴🔴🔴 지연 없는 자(채점기가 «지금» 낸 값 대 치환표)", live),
        ("🔴🔴 뺀 칸(자기 결과에 의존한다 · 조용히 안 뺀다 · 조항 60)", list(SELF_DEP)),
        ("🔴 왜 뺐나",
         "🔴 **디스크의 `out986_certify.json` 을 읽으면 한 회 뒤진 값을 읽고, "
         "그러면 `채.반증분자모` 가 이 조건의 결과에 다시 의존해 «주기 4 의 진동»이 "
         "생겨 고정점에 원리상 도달 못 한다**(986 실측). 🔴 전량 16 칸 검사는 "
         "`certify986` 이 그대로 한다"),
        ("⚠ 디스크 `certify` 가 적은 어긋난 칸(한 회 뒤질 수 있다 · 진단)",
         mine.get("🔴🔴 어긋난 칸")),
        ("⚠ 디스크 `certify` 의 수렴", mine.get("🔴🔴🔴 수렴했나(여섯 칸이 전부 같다)")),
        ("🔴🔴 수렴했나", bool(live["🔴 전부 같은가"])),
    ])
    items["11 문서 고리가 수렴했나(certify 여섯 칸 · 지연 없는 자)"] = \
        (f11, not f11["🔴🔴 수렴했나"])

    # 12 F5 도장 --- 분모는 원장이 싣는 산출물 전량
    fs = ctx["feeds"]
    items["12 인용·원장 산출물이 전부 F5 도장을 넘나"] = (fs, not fs["통과"])

    # 13 리터럴 `통과` (AST · RAN_986)
    ap = ctx["astpass"]
    items["13 이 사이클 러너에 리터럴 `(\"통과\", True)` 가 있나"] = (ap, not ap["통과"])

    # 14 손 전사 (AST · RAN_986 전량 · R3)
    hl = ctx["handlit"]
    items["14 🔴 이 사이클 러너에 손 전사 수 리터럴이 있나(R3)"] = (hl, not hl["통과"])

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
    b = (pw.get("§1 🔴🔴🔴 부트스트랩 감싼 δ 쓸기") or {}).get("🔴 λ 별") or {}
    c = (pw.get("§2 🔴🔴🔴 천장 — 「δ 를 아무리 키워도 발화율은 얼마인가」") or {}).get("🔴 λ 별") or {}
    sh = (pw.get("§3 🔴🔴🔴 983 에도 같은 자 — 「U 자 되오름」의 검정력") or {}).get("🔴 λ 별") or {}
    fp = ctx["five"] or {}
    rows = collections.OrderedDict()

    w = (b.get("u=0") or {}).get("🔴🔴🔴 처음 0.5 «이상»이 되는 δ") or {}
    width = w.get("🔴 구간 폭")
    rows["P1 `u=0` 최소 검출 δ 의 95% 구간이 두 칸 이상에 걸친다"] = collections.OrderedDict([
        ("🔴 구간", w.get("🔴🔴🔴 95% 구간(넘은 복제만)")), ("🔴 구간 폭", width),
        ("🔴 맞았나", bool(width is not None and width >= 0.02)),
    ])
    ceil0 = (c.get("u=0") or {}).get("🔴🔴🔴 천장(중앙값 · 점추정)")
    rows["P2 `u=0` 발화율에 천장이 있다(δ ≥ 0.50 중앙값 < 0.70)"] = collections.OrderedDict([
        ("🔴 천장", ceil0), ("🔴 천장 95% 구간", (c.get("u=0") or {}).get("🔴🔴🔴 천장 95% 구간")),
        ("🔴 맞았나", bool(ceil0 is not None and ceil0 < 0.70)),
    ])
    sw3 = (b.get("u=3") or {}).get("🔴 δ 쓸기(점추정 + 부트스트랩 95% 구간)") or {}
    over = [k for k, v in sw3.items()
            if v.get("🔴🔴 발화율(점추정)") is not None and v["🔴🔴 발화율(점추정)"] >= 0.5]
    rows["P3 `u=3` 은 δ = 2.00 까지도 발화율 0.5 를 한 번도 안 넘는다"] = collections.OrderedDict([
        ("🔴 0.5 이상인 δ 칸", over or "없음"), ("🔴 맞았나", bool(not over)),
    ])
    ok4 = []
    for uk, v in sh.items():
        ok4.append(v.get("🔴🔴🔴 최소 검출 크기(최솟값)가 관측 최대 차보다 큰가"))
    rows["P4 983 의 조항 68 짝 자의 최소 검출 모양 크기 > 관측 최대 인접 차"] = \
        collections.OrderedDict([
            ("🔴 λ 별", {uk: {"최소 검출(최솟값)": v.get("🔴🔴 최소 검출 모양 크기의 최솟값"),
                            "관측 최대 차": v.get("🔴🔴 983·984 가 실은 |인접 칸 차| 의 최댓값"),
                            "큰가": v.get("🔴🔴🔴 최소 검출 크기(최솟값)가 관측 최대 차보다 큰가")}
                       for uk, v in sh.items()}),
            ("🔴 맞았나", bool(ok4 and all(ok4))),
        ])
    s1 = fp.get("1 소비자 역참조") or {}
    rows["P5 새 소비자 정의(코드 리터럴)로 `⑤′` 절 1 이 통과한다"] = collections.OrderedDict([
        ("🔴 절 1 통과", s1.get("통과")), ("🔴 맞았나", bool(s1.get("통과"))),
    ])
    nf = fp.get("🔴 실패한 절")
    rows["P6 `⑤′` 실패 절이 3 이하로 준다"] = collections.OrderedDict([
        ("🔴 실패 절", nf), ("🔴 실패 수", len(nf) if isinstance(nf, list) else None),
        ("🔴 맞았나", bool(isinstance(nf, list) and len(nf) <= 3)),
    ])
    hit = len([1 for v in rows.values() if v.get("🔴 맞았나")])
    return rows, hit


def live_sixth(tb, ruleD, shape, feeds, six):
    """🔴🔴🔴 **지연 없는 여섯째 칸** --- 채점기가 «지금» 낸 값과 치환표를 견준다.

    🔴 `SELF_DEP` 여덟 칸은 뺀다(자기 결과에 의존한다 · 이유는 그 상수 곁에 있다).
    남는 여덟 칸은 **이 함수가 부르는 시점에 이미 «잰» 값**이라 지연이 0 이다.
    """
    T = _cells(tb) or {}
    live = {
        "채.규칙D표밖": ruleD["🔴🔴 표 밖 합"],
        "채.규칙D분모": ruleD["🔴🔴 채점 분모"],
        "채.규칙D통과": ruleD["통과"],
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
        rows[k] = {"🔴 치환표의 칸": T[k], "🔴 채점기가 «지금» 낸 값": live[k],
                   "🔴 같은가": ok}
        if not ok:
            bad.append(k)
    return collections.OrderedDict([
        ("🔴 분모(`SCORE_CELLS` 16 에서 `SELF_DEP` 8 을 뺀 수)", len(live)),
        ("🔴 칸별", rows),
        ("🔴🔴 어긋난 칸", bad or "없음"),
        ("🔴 치환표에 없는 칸(= 「같다」가 아니다 · 조항 59)", miss or "없음"),
        ("🔴 전부 같은가", bool(not bad and not miss)),
    ])


def stage(ref, prereg_commit, five_name, it):
    t0 = CY.now()
    CY.begin(ref)
    cs0 = CY.code_stamp()
    rules = LG.ALLOW_CTX + INHERIT
    tb = _load(TBL)
    au = _load("out986_audit.json", must=True)
    pw = _load("out986_power.json", must=True)
    ct = _load("out986_certify.json")
    fp = _load(five_name)
    reg = registered_denominators()
    ruleD = rule_d(tb, rules)
    shape = shape_audit()
    feeds = feeds_stamp()
    astpass = ast_pass_all()
    handlit = hand_lit_all(au)
    n_fail = len(fp.get("🔴 실패한 절") or []) if fp else None
    ctx_n_falsify = 14
    #: 🔴 **바늘 셋은 «사전등록이 박은 상수»다** --- 여섯 자리 모두가 원리상 실을 수
    #:  있는 수여야 자가 산다. 측정값(⑤′ 실패 수)을 바늘로 쓰면 **사전등록은 그것을
    #:  원리상 못 싣는다**(사전등록은 측정 전에 얼어 있다) --- 985 는 그걸 「부분 문자열」
    #:  로 덮었고 986 은 **엄격 자로 판정**하므로 바늘을 상수로 바꾼다.
    six = six_places(fp, collections.OrderedDict([
        ("반증조건 분모", (ctx_n_falsify, "반증조건")),
        ("`⑤′` 분모", (reg["🔴 `⑤′` 분모"], "⑤′")),
        ("규칙 D 대상 수", (ruleD["🔴🔴 채점 분모"], "규칙 D")),
    ]))
    live_cert = live_sixth(tb, ruleD, shape, feeds, six)
    ctx = {"prereg_commit": prereg_commit, "reg": reg, "ruleD": ruleD,
           "five": fp, "six": six, "certify": ct, "feeds": feeds,
           "live_cert": live_cert,
           "astpass": astpass, "handlit": handlit, "power": pw, "audit": au,
           "n_falsify": ctx_n_falsify, "n_predict": 6, "n_cert": 6}
    rows, bad = falsify(ctx)
    prows, hit = predict(ctx)

    out = collections.OrderedDict()
    out["무엇"] = "986 채점 — 🔴 반증조건 14 · 예측 6 · 규칙 D 대상 여섯(+PR 본문)"
    out["🔴 축"] = "C1 상태→예측(몸통) · 자기 자"
    out["사전등록"] = PREREG
    out["🔴🔴 조항 60-다 · 사전등록이 박은 분모"] = reg
    out["🔴 `⑤′` 반복"] = it
    out["§6 🔴 반증조건"] = collections.OrderedDict([
        ("🔴 분모", ctx["n_falsify"]), ("🔴 조건별", rows),
        ("🔴🔴 반증된 조건", bad or "없음"),
        ("🔴🔴 분자 / 분모", "%d / %d" % (ctx["n_falsify"] - len(bad), ctx["n_falsify"])),
        ("통과", bool(not bad)),
    ])
    out["§5 🔴 예측"] = collections.OrderedDict([
        ("🔴 분모", ctx["n_predict"]), ("🔴 예측별", prows),
        ("🔴🔴 분자 / 분모", "%d / %d" % (hit, ctx["n_predict"])),
        ("🔴 분자", hit), ("통과", bool(hit == ctx["n_predict"])),
    ])
    out["§D 🔴 규칙 D 감사(분모 여섯)"] = ruleD
    out["§68 🔴 조항 68 모양 주장 감사"] = shape
    out["§F5 🔴 인용 산출물 도장"] = feeds
    out["§9 🔴🔴 여섯 자리가 같은 수를 적나"] = six
    out["§11 🔴🔴🔴 지연 없는 여섯째 칸(986)"] = collections.OrderedDict(
        list(live_cert.items()) + [
            ("통과", bool(live_cert["🔴 전부 같은가"])),
            ("🔴 이 절의 `통과` 가 뜻하는 것",
             "🔴 **치환표가 «지금» 채점기가 낸 값을 들고 있는가** --- "
             "985 는 표가 한 회 뒤진 값을 들고 있었고 아무 자도 못 봤다"),
        ])
    out["§AST 🔴 리터럴 `통과` 금지"] = astpass
    out["§R3 🔴 손 전사 수 리터럴 금지(분모 = 이 사이클 러너 전량)"] = handlit
    # 🔴🔴🔴 **R5 --- 최상위 `통과` 에 `§68`·`§5 예측` 을 넣는다**
    out["통과"] = bool(out["§6 🔴 반증조건"]["통과"] and ruleD["통과"]
                     and shape["통과"] and out["§5 🔴 예측"]["통과"])
    out["🔴🔴🔴 최상위 `통과` 의 정의(986 R5 가 넓혔다)"] = {
        "985 판": "반증조건 ∧ 규칙 D",
        "🔴 986 판": "반증조건 ∧ 규칙 D ∧ **§68** ∧ **§5 예측**",
        "🔴 왜": "🔴 **985 는 `§68`(불통과 · 근거 없는 모양 주장 5)과 `§5 예측`(불통과)을 "
               "판정 규칙 밖에 두고 최상위 `통과` 를 `True` 로 게재했다** --- "
               "**자기 헤드라인을 죽이는 자를 판정 규칙에서 뺐다**(티처 #124 3순위 R5)",
        "🔴 그래서 이 사이클의 최상위 `통과` 는 «떨어질 수 있다»":
            bool(not (shape["통과"] and out["§5 🔴 예측"]["통과"])),
    }
    CY.write(OUT, out, ref, cs0, t0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["score"])
    ap.add_argument("--ref", required=True)
    ap.add_argument("--prereg-commit", required=True)
    ap.add_argument("--five", default="fiveprime_986.json")
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
        "§68 근거 없는 모양": r["§68 🔴 조항 68 모양 주장 감사"]["🔴🔴 근거 없는 모양 주장 수"],
    }, ensure_ascii=False))
    return 0 if r["통과"] else 1


if __name__ == "__main__":
    sys.exit(main())
