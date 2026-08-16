#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""985 채점 — 🔴 **반증조건 14 · 예측 6 · 규칙 D 분모 5 · 조항 68 · F5 도장**.

🔴 **분모는 «사전등록에서 읽는다»**(조항 60-다) --- 손으로 안 적는다.
🔴 **리터럴 판정이 하나도 없다** --- 반증조건 12 가 이 파일 «과 985 러너 전량»을 AST 로 문다.
"""
import argparse
import ast
import collections
import json
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import cycle985 as CY                                   # noqa: E402
import ledger as LG                                     # noqa: E402

OUT = "runners/out985_score.json"
PREREG = "docs/prereg_985_specificity_power.md"
BODY = ("docs/판정_985.md", "docs/card_985.md", "docs/handoff_985.md")
GOAL = "docs/목표.md"
DEN = "data/lab/denominator.json"
TBL = "runners/out985_table.json"
CARD_OUT = os.path.expanduser(
    "~/.claude/projects/-Users-ax-world-model/memory/project-lab-state.md")

MARK_A = "<!-- 983:정본유보:시작 -->"
MARK_B = "<!-- 983:정본유보:끝 -->"
LEDGER_KEY = "노트 985"

FEED_RE = re.compile(
    r"`?((?:runners/)?(?:out985_[a-z0-9_]+|fiveprime_985[a-z0-9_]*)\.json)`?")
#: 🔴 사전등록 §6-11 이 «사전»에 뺀 것 --- `⑤′` 산출물(고정점이 원리상 불가)
FEED_EXEMPT = re.compile(r"fiveprime_985")

#: 🔴 조항 68 --- 「모양」 낱말과, 그 곁에 반드시 있어야 하는 근거 낱말
SHAPE_RE = re.compile(r"단조|포화|U 자|되오름")
SHAPE_OK = ("z ", "짝 검정", "안 쟀다", "못 넘", "2·짝SE", "2·SE")
SHAPE_WIN = 220

#: 🔴 사전등록에서 분모를 읽는 바늘 --- 손으로 안 적는다(조항 60-다)
DEN_FALSIFY = re.compile(r"##\s*§6\s*반증조건\s*\(분모\s*\*\*(\d+)\*\*")
DEN_PREDICT = re.compile(r"##\s*§5\s*예측\s*\(분모\s*\*\*(\d+)\*\*")
DEN_FIVE = re.compile(r"`⑤′`\s*분모\s*—\s*🔴\s*\*\*등록\s*(\d+)")

#: 🔴 983·984 가 쓴 면제 규칙 셋을 **그대로** 물려쓴다 --- 새로 안 만든다(조항 66-③)
INHERIT = (
    ("🔴 981 판: sha256 · 40자 고정 ref", re.compile(r"\b[0-9a-f]{40,64}\b")),
    ("🔴 981 판: 사이클 번호 — 화살표 쌍 · 인라인 코드 · 「노트/체제」 딱지",
     re.compile(r"9\d{2}\s*→\s*9\d{2}|`9\d{2}`|(?<![\d.,])9[7-8]\d(?![\d.,])")),
    ("🔴 981 판: 절 번호의 가지(`§1-2` 꼴)", re.compile(r"§\s*\d+-\d+|`§\d+-\d+`")),
)


def _git(*a):
    return subprocess.check_output(["git"] + list(a), cwd=str(ROOT))


def _load(n, must=False):
    p = ROOT / "runners" / n if not n.startswith("runners/") else ROOT / n
    if p.is_file():
        return json.loads(p.read_text(encoding="utf-8"))
    if must:
        raise SystemExit("🔴 %s 가 없다 — fail-closed" % n)
    return {}


def _text(rel):
    q = Path(rel) if os.path.isabs(rel) else ROOT / rel
    return q.read_text(encoding="utf-8", errors="replace") if q.is_file() else None


def _sha(b):
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode("utf-8")).hexdigest()


# ══════════════════════════════════════════════════════════════════════
def registered_denominators():
    t = _text(PREREG)
    if t is None:
        return {"🔴": "🔴 사전등록을 못 읽었다 --- 「0」이 아니다(조항 59)"}
    out = collections.OrderedDict()
    for nm, rx in (("반증조건", DEN_FALSIFY), ("예측", DEN_PREDICT), ("⑤′", DEN_FIVE)):
        m = rx.search(t)
        out[nm] = int(m.group(1)) if m else None
    out["🔴 못 읽은 것"] = [k for k, v in out.items()
                       if v is None and not k.startswith("🔴")]
    return out


# ══════════════════════════════════════════════════════════════════════
# 🔴 규칙 D — 채점 분모 **다섯**
# ══════════════════════════════════════════════════════════════════════
def _table_set(tb):
    S = set()
    for _k, v in (tb.get("🔴🔴 치환표", {}) or {}).items():
        S.add(LG._norm(str(v)))
        if isinstance(v, float):
            for n in range(0, 7):
                S.add(LG._norm("%.*f" % (n, v)))
        for m in LG.NUMPAT.finditer(str(v)):
            S.add(LG._norm(m.group()))
    return S


def _outside(text, S, rules):
    spans, _why = LG.allow_spans(text, rules)
    n, ex = 0, []
    for m in LG.NUMPAT.finditer(text):
        if any(x <= m.start() and m.end() <= y for x, y in spans):
            continue
        if LG._norm(m.group()) not in S:
            n += 1
            if len(ex) < 12:
                ex.append(m.group())
    return n, ex


def _holdout_slice():
    t = _text(GOAL)
    if t is None or MARK_A not in t or MARK_B not in t:
        return None
    i, j = t.index(MARK_A), t.index(MARK_B) + len(MARK_B)
    return t[i:j]


def _ledger_entry_text():
    q = ROOT / DEN
    if not q.is_file():
        return None
    d = json.loads(q.read_text(encoding="utf-8"))
    if LEDGER_KEY not in d:
        return None
    return json.dumps(d[LEDGER_KEY], ensure_ascii=False, indent=1)


def rule_d(tb, rules):
    S = _table_set(tb)
    rows, tot = collections.OrderedDict(), 0
    targets = collections.OrderedDict()
    for p in BODY:
        targets[p] = _text(p)
    targets["🔴 `docs/목표.md` 「정본 유보」 절"] = _holdout_slice()
    targets["🔴 원장 `%s` 항목" % LEDGER_KEY] = _ledger_entry_text()
    for name, txt in targets.items():
        if txt is None:
            rows[name] = {"🔴": "🔴 못 읽었다 --- 「표 밖 0」이 아니다(조항 59)",
                          "표 밖": None}
            continue
        n, ex = _outside(txt, S, rules)
        rows[name] = {"표 밖": n, "보기": ex or "없음", "글자 수": len(txt)}
        tot += n
    unread = [k for k, v in rows.items() if v.get("표 밖") is None]
    T = tb.get("🔴🔴 치환표", {}) or {}
    return collections.OrderedDict([
        ("🔴 무엇", "🔴 **규칙 D --- 치환표에 없는 수를 본문에 못 쓴다**"),
        ("🔴🔴 채점 분모", len(targets)),
        ("🔴 대상", list(targets.keys())),
        ("🔴 대상별", rows),
        ("🔴🔴 표 밖 합", tot),
        ("🔴 못 읽은 대상", unread or "없음"),
        ("🔴 치환표 칸 수", len(T)),
        ("🔴 치환표 sha256", tb.get("🔴🔴 표 sha256")),
        ("통과", bool(tot == 0 and not unread)),
    ])


# ══════════════════════════════════════════════════════════════════════
def shape_audit():
    rows, bad = collections.OrderedDict(), 0
    for p in BODY:
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
        ("🔴 무엇", "🔴🔴 **조항 68(984 신설)** --- `2·SE` 를 못 넘는 칸으로 모양을 주장했나"),
        ("🔴 자", "「단조·포화·U 자·되오름」 낱말마다 ±%d 글자 안에 근거 낱말" % SHAPE_WIN),
        ("⚠ 이 자의 한계(985 가 «잰» 것 · 티처 #123 3순위 ⑤)",
         "🔴 **바늘에 `\"z \"` 가 있어 창 안에 `z` 하나만 있으면 통과한다** --- "
         "「그 근거가 «그 모양의» 근거인가」는 원리상 안 본다. "
         "🔴 **985 는 이 자를 안 고치고 한계를 적는다**(조항 61 · 상한 5)"),
        ("🔴 문서별", rows),
        ("🔴🔴 근거 없는 모양 주장 수", bad),
        ("통과", bool(bad == 0 and all(
            v.get("근거 없는 모양 낱말") is not None for v in rows.values()))),
    ])


def _stamp(d):
    if not isinstance(d, dict):
        return None
    if "🔴 F5 통과" in d:
        return d
    for v in d.values():
        if isinstance(v, dict) and "🔴 F5 통과" in v:
            return v
    return None


def feeds_stamp():
    cited = collections.OrderedDict()
    for p in BODY:
        t = _text(p)
        if t is None:
            continue
        for m in FEED_RE.finditer(t):
            cited.setdefault(m.group(1).split("/")[-1], []).append(p)
    rows, bad, exempt = collections.OrderedDict(), [], []
    for nm in sorted(cited):
        if FEED_EXEMPT.search(nm):
            exempt.append(nm)
            continue
        d = _load(nm)
        st = _stamp(d)
        ok = bool(st and st.get("🔴 F5 통과"))
        rows[nm] = {"인용한 문서": cited[nm], "F5 통과": (st or {}).get("🔴 F5 통과"),
                    "도장이 있나": bool(st)}
        if not ok:
            bad.append(nm)
    return collections.OrderedDict([
        ("🔴 무엇", "🔴 **본문이 인용한 산출물의 도장이 전부 F5 통과인가**"),
        ("🔴 인용된 산출물(기계 추출)", sorted(cited)),
        ("🔴 분모", len(rows)),
        ("🔴🔴 사전등록 §6-11 이 «사전»에 뺀 것(`⑤′` 산출물)", exempt or "없음"),
        ("🔴🔴 뺀 수", len(exempt)),
        ("⚠ 984 는 이 자리에서 「뺀 수 0」이었다",
         "🔴 **면제를 등록해 놓고 실제로 빠진 파일이 하나도 없었다** --- 그 면제는 "
         "아무 일도 안 했고 조건은 면제 없이도 같은 값을 냈다(티처 #123 3순위 ⑤)"),
        ("🔴 산출물별", rows),
        ("🔴🔴 F5 를 못 넘은 것", bad or "없음"),
        ("통과", bool(rows and not bad)),
    ])


# ══════════════════════════════════════════════════════════════════════
# AST
# ══════════════════════════════════════════════════════════════════════
def _const_bool(n):
    return isinstance(n, ast.Constant) and isinstance(n.value, bool)


def _const_num(n):
    return isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) \
        and not isinstance(n.value, bool)


def ast_pass_hits(path):
    src = _text(path)
    if src is None:
        return None
    hits = []
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Tuple) and len(n.elts) == 2:
            k, v = n.elts
            if isinstance(k, ast.Constant) and isinstance(k.value, str) \
                    and "통과" in k.value and _const_bool(v):
                hits.append({"파일": path, "줄": n.lineno, "값": v.value})
        if isinstance(n, ast.Dict):
            for k, v in zip(n.keys, n.values):
                if k is not None and isinstance(k, ast.Constant) \
                        and isinstance(k.value, str) and "통과" in k.value \
                        and _const_bool(v):
                    hits.append({"파일": path, "줄": getattr(k, "lineno", None),
                                 "값": v.value})
    return hits


def ast_table_hits(path, names=("T",)):
    src = _text(path)
    if src is None:
        return None
    hits = []
    for n in ast.walk(ast.parse(src)):
        if not isinstance(n, ast.Assign):
            continue
        for tgt in n.targets:
            if isinstance(tgt, ast.Subscript) and isinstance(tgt.value, ast.Name) \
                    and tgt.value.id in names and _const_num(n.value):
                hits.append({"파일": path, "줄": n.lineno})
    return hits


# ══════════════════════════════════════════════════════════════════════
# 🔴 여섯 자리가 같은 수를 적나 (반증조건 9)
# ══════════════════════════════════════════════════════════════════════
def six_places(five):
    """🔴🔴 **저장소 안 넷 · 원장 · 메모리 카드 여섯이 같은 수를 적나.**

    바늘은 **세 수**다 --- `⑤′` 실패 수 · 예측 분자 · `⑤′` 분모.
    🔴 세 수를 «문자열»로 찾는 것이 아니라 **「그 수가 그 문서에 있나」**를 본다.
    """
    fails = five.get("🔴 실패한 절")
    n_fail = len(fails) if isinstance(fails, list) else 0
    n_den = five.get("🔴 절 수(분모)")
    tb = _load(TBL)
    T = tb.get("🔴🔴 치환표", {}) or {}
    n_hit = T.get("채.예측분자")
    needles = collections.OrderedDict([
        ("`⑤′` 실패 수", n_fail),
        ("예측 분자", n_hit),
        ("`⑤′` 분모", n_den),
    ])
    places = collections.OrderedDict()
    for p in BODY:
        places[p] = _text(p)
    places["원장 `%s` 항목" % LEDGER_KEY] = _ledger_entry_text()
    places["🔴 메모리 카드(저장소 «밖»)"] = _text(CARD_OUT)
    rows, bad = collections.OrderedDict(), []
    for name, txt in places.items():
        if txt is None:
            rows[name] = {"🔴": "🔴 못 읽었다 --- 「같다」가 아니다(조항 59)"}
            bad.append(name)
            continue
        cell = {}
        for nm, v in needles.items():
            cell[nm] = (str(v) in txt) if v is not None else None
        rows[name] = cell
        if any(x is not True for x in cell.values()):
            bad.append(name)
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴 **저장소 안 넷 · 원장 · 메모리 카드 여섯이 같은 수를 적나**"),
        ("🔴 바늘(세 수)", dict(needles)),
        ("🔴 분모(자리 수)", len(places)),
        ("🔴 자리별", rows),
        ("🔴🔴 세 수가 다 없는 자리", bad or "없음"),
        ("🔴 왜 이 조건이 있나",
         "🔴 **규칙 D: 저장소 안 문서와 메모리 카드가 「다른 사실」을 적으면 실패다.** "
         "984 의 C1 이 정확히 그것이었다 --- 자백이 메모리 카드에만 있었다"),
        ("통과", bool(not bad)),
    ])


# ══════════════════════════════════════════════════════════════════════
def falsify(ctx):
    au, pw, hs, fp = ctx["audit"], ctx["power"], ctx["house"], ctx["five"]
    ce, rd, sh, fs = ctx["certify"], ctx["ruleD"], ctx["shape"], ctx["feeds"]
    reg, sp = ctx["reg"], ctx["six"]

    # 1 사전등록 blob
    pre_disk = _sha((ROOT / PREREG).read_bytes())
    try:
        pre_git = _sha(_git("show", "%s:%s" % (ctx["prereg_commit"], PREREG)))
    except subprocess.CalledProcessError:
        pre_git = None
    f1 = collections.OrderedDict([
        ("🔴 사전등록 단독 커밋", ctx["prereg_commit"]),
        ("🔴 그 커밋의 blob sha256", pre_git), ("🔴 디스크 sha256", pre_disk),
        ("🔴🔴 고쳤나", bool(pre_git is None or pre_git != pre_disk)),
    ])

    # 2 조항 69 --- 막힌 명령 신고
    blocked = ctx["blocked"]
    body_all = "\n".join(x for x in (_text(p) for p in BODY) if x)
    led = _ledger_entry_text() or ""
    declared = bool(("막힌 명령" in body_all) and ("막힌 명령" in led))
    f2 = collections.OrderedDict([
        ("🔴 사전등록 §0-다 가 신고 절을 두었나",
         bool("막힌 명령 신고" in (_text(PREREG) or ""))),
        ("🔴 판정문·카드·handoff 에 「막힌 명령」 절이 있나",
         bool("막힌 명령" in body_all)),
        ("🔴 원장 항목에 있나", bool("막힌 명령" in led)),
        ("🔴🔴 이 사이클이 신고한 막힌 명령", blocked),
        ("🔴 「없었다」를 명시했나(빈칸이 아니다)",
         bool(blocked and str(blocked) != "[]")),
        ("🔴🔴🔴 신고를 안 했나", bool(not declared)),
    ])

    # 3 분모 일치
    used = collections.OrderedDict([("반증조건", ctx["n_falsify"]),
                                    ("예측", ctx["n_predict"]),
                                    ("⑤′", fp.get("🔴 절 수(분모)"))])
    mism = [k for k in ("반증조건", "예측", "⑤′")
            if reg.get(k) is None or reg.get(k) != used.get(k)]
    f3 = collections.OrderedDict([
        ("🔴 사전등록이 박은 분모(정규식으로 읽었다)",
         collections.OrderedDict([(k, reg.get(k)) for k in ("반증조건", "예측", "⑤′")])),
        ("🔴 실제로 쓴 분모", used),
        ("🔴🔴 어긋난 것", mism or "없음"),
        ("🔴🔴 다르게 썼나", bool(mism)),
    ])

    # 4 헤드라인을 죽이는 자를 판정 규칙에서 뺐나
    gate = (pw.get("§4 🔴🔴 자 ③(붓스트랩)을 판정 규칙 안으로") or {})
    per = gate.get("🔴 λ 별") or {}
    have = [k for k in ("🔴🔴🔴 관문 ㉠ 점추정 순열 p < 0.05",
                        "🔴🔴🔴 관문 ㉡ 붓스트랩 구간이 0 을 «안» 포함",
                        "🔴🔴🔴 관문 ㉢ 두 팔 차 구간이 0 을 «안» 포함")
            if all(k in (per.get(u) or {}) for u in ("u=0", "u=3"))]
    head_txt = (_text(BODY[0]) or "")
    one_liner = head_txt.split("## ")[1] if "## " in head_txt else head_txt
    reflects = bool("붓스트랩" in one_liner or "구간" in one_liner
                    or "못 잰다" in one_liner)
    f4 = collections.OrderedDict([
        ("🔴 판정 산출물에 있는 관문", have),
        ("🔴 분모(등록 관문 수)", 3),
        ("🔴 판정문 「한 줄」이 자 ③ 을 반영했나", reflects),
        ("🔴🔴 뺐나", bool(len(have) < 3 or not reflects)),
    ])

    # 5 조항 66-② --- 고치고 «안 다시 돌렸나»
    moved, stale_any, unknown = collections.OrderedDict(), False, False
    for nm, d in (("audit", au), ("power", pw), ("house", hs), ("certify", ce)):
        c = d.get("🔴🔴 조항 66-② (985 R5)", {})
        st = c.get("🔴🔴🔴 값을 낸 뒤 고치고 «안 다시 돌린» 산출물") or {}
        moved[nm] = collections.OrderedDict([
            ("넓은 창에서 바뀐 파일", c.get("🔴🔴🔴 넓은 창(985 판 · 사이클 시작~지금)에서 바뀐 파일")),
            ("좁은 창이 놓친 파일 수", c.get("🔴🔴 좁은 창이 놓친 파일 수(= 984 판이 못 본 것)")),
            ("낡은 산출물", st.get("🔴🔴🔴 낡은 산출물(고치고 안 다시 돌렸다)")),
        ])
        if st.get("🔴🔴🔴 낡은 것이 있나"):
            stale_any = True
        if c.get("🔴🔴🔴 측정 창 안에 러너를 고쳤나") is None:
            unknown = True
    f5 = collections.OrderedDict([
        ("🔴 산출물별", moved),
        ("🔴 사이클 시작 도장을 읽었나", bool(not unknown)),
        ("🔴🔴 고치고 안 다시 돌렸나", bool(stale_any or unknown)),
    ])

    # 6 HEAD == 디스크
    close = hs.get("§0-가 🔴🔴 집을 닫았나", {})
    f6 = collections.OrderedDict([
        ("🔴 원장 sha256(자기 항목 제외 · 고정점) — 디스크",
         close.get("🔴🔴🔴 원장 sha256(자기 항목 제외 · 🔴 이것이 «고정점»이다) — 디스크")),
        ("⚠ 엄격(바이트 동일)", close.get("🔴🔴🔴 HEAD 와 디스크가 바이트 동일한가")),
        ("🔴 갈렸다면 왜", close.get("🔴🔴 갈렸다면 왜")),
        ("🔴🔴 갈렸나", bool(not close.get(
            "🔴🔴🔴 머지 뒤 규칙 A-2 가 참인가(= 같거나, 갈린 것이 이 사이클 항목 하나뿐)"))),
    ])

    # 7 규칙 D
    f7 = collections.OrderedDict([
        ("🔴 표 밖 합", rd.get("🔴🔴 표 밖 합")),
        ("🔴 분모", rd.get("🔴🔴 채점 분모")),
        ("🔴🔴 전부 치환표 칸인가", bool(rd.get("통과"))),
    ])

    # 8 인증한 문서 == 실린 문서
    mine = ce.get("§가 🔴🔴🔴 985 자신") or {}
    f8 = collections.OrderedDict([
        ("🔴 다섯 칸", mine.get("🔴 다섯 칸")),
        ("🔴 어긋난 칸", mine.get("🔴🔴 어긋난 칸")),
        ("🔴🔴 다른가", bool(not mine.get("🔴🔴🔴 수렴했나(다섯 칸이 전부 같다)"))),
    ])

    # 9 여섯 자리
    f9 = collections.OrderedDict([
        ("🔴 자리별", sp.get("🔴 자리별")),
        ("🔴 분모", sp.get("🔴 분모(자리 수)")),
        ("🔴🔴 여섯이 같은 수를 적나", bool(sp.get("통과"))),
    ])

    # 10 ⑤′ 수렴
    it = ctx["iter"]
    f10 = collections.OrderedDict([
        ("🔴 반복 횟수", it.get("⑤′ 반복")),
        ("🔴 판별", it.get("⑤′ 판별")),
        ("🔴🔴 수렴했나", bool(it.get("⑤′ 수렴"))),
        ("🔴 반복 횟수를 산출물에 박았나", bool(it.get("⑤′ 반복") is not None)),
    ])

    # 11 도장
    f11 = collections.OrderedDict([
        ("🔴 분모", fs.get("🔴 분모")), ("🔴 뺀 수", fs.get("🔴🔴 뺀 수")),
        ("🔴🔴 전부 F5 인가", bool(fs.get("통과")))])

    # 12·13 AST
    per12 = collections.OrderedDict()
    trues = []
    for r in CY.RAN_985:
        h = ast_pass_hits(r)
        per12[r] = h if h else "없음"
        trues += [x for x in (h or []) if x["값"] is True]
    h13 = ast_table_hits("runners/note985_gen.py")
    f12 = collections.OrderedDict([
        ("🔴🔴🔴 분모(985 가 새로 쓴 러너 전량)", list(CY.RAN_985)),
        ("🔴 분모 크기", len(CY.RAN_985)),
        ("⚠ 984 가 쓴 분모", ["runners/score984.py"]),
        ("🔴 파일별", per12),
        ("🔴🔴 리터럴 `(\"통과\", True)` 자리", trues or "없음"),
        ("🔴🔴 있나", bool(trues)),
    ])
    f13 = collections.OrderedDict([("🔴 걸린 자리", h13 or "없음"),
                                   ("🔴🔴 있나", bool(h13))])

    # 14 ⑥
    paper = sorted(str(q.relative_to(ROOT)) for q in ROOT.glob("paper/steps/*985*"))
    f14 = collections.OrderedDict([
        ("🔴 `⑤′` 통과", fp.get("통과")),
        ("🔴 985 논문 자리", paper or "없음"),
        ("🔴🔴 불통과인데 시작했나", bool((not fp.get("통과")) and paper)),
    ])

    items = collections.OrderedDict([
        ("1 사전등록 blob 을 측정 뒤에 고쳤나", (f1, f1["🔴🔴 고쳤나"])),
        ("2 🔴🔴 막힌 명령을 우회하고 신고 안 했나(조항 69)",
         (f2, f2["🔴🔴🔴 신고를 안 했나"])),
        ("3 🔴 채점 분모를 사전등록과 다르게 썼나", (f3, f3["🔴🔴 다르게 썼나"])),
        ("4 🔴🔴 자기 헤드라인을 죽이는 자를 판정 규칙에서 뺐나", (f4, f4["🔴🔴 뺐나"])),
        ("5 🔴 사이클 창 안에 러너를 고치고 안 다시 돌렸나", (f5, f5["🔴🔴 고치고 안 다시 돌렸나"])),
        ("6 🔴 머지 뒤 HEAD ≠ 디스크인가", (f6, f6["🔴🔴 갈렸나"])),
        ("7 본문의 수가 전부 치환표 칸인가", (f7, not f7["🔴🔴 전부 치환표 칸인가"])),
        ("8 🔴🔴 인증한 문서와 실린 문서가 다른가", (f8, f8["🔴🔴 다른가"])),
        ("9 🔴🔴 여섯 자리가 같은 수를 적나", (f9, not f9["🔴🔴 여섯이 같은 수를 적나"])),
        ("10 🔴 `⑤′` 를 수렴할 때까지 돌렸나", (f10, not f10["🔴🔴 수렴했나"])),
        ("11 인용 산출물 도장이 전부 F5 인가", (f11, not f11["🔴🔴 전부 F5 인가"])),
        ("12 🔴🔴 이 사이클 러너 전량에 리터럴 `통과` 가 있나", (f12, f12["🔴🔴 있나"])),
        ("13 🔴 치환표 생성기에 손으로 친 수가 있나", (f13, f13["🔴🔴 있나"])),
        ("14 `⑤′` 불통과인데 ⑥ 을 시작했나", (f14, f14["🔴🔴 불통과인데 시작했나"])),
    ])
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
def predict(ctx):
    pw, fp, it, ce = ctx["power"], ctx["five"], ctx["iter"], ctx["certify"]
    p5 = (pw.get("§5 🔴🔴🔴 심은 누출 검정력 곡선(새 측정)") or {}).get("🔴 λ 별", {})
    g4 = (pw.get("§4 🔴🔴 자 ③(붓스트랩)을 판정 규칙 안으로") or {}).get("🔴 λ 별", {})
    rows = collections.OrderedDict()

    u0 = p5.get("u=0") or {}
    md = u0.get("🔴🔴🔴 발화율 0.5 를 처음 넘는 δ(= 최소 검출 크기)")
    obs = u0.get("🔴 관측된 max|㉮ρ − ㉰ρ|")
    ratio = (md / obs) if (isinstance(md, (int, float)) and obs) else None
    lower = u0.get("🔴 하한(범위 끝 δ ÷ 관측 팔 차)")
    rows["P1 최소 검출 δ 가 관측 팔 차(u=0)의 5 배를 넘는다"] = collections.OrderedDict([
        ("최소 검출 δ", md), ("관측 팔 차", obs), ("비", ratio),
        ("범위 끝에서의 하한 비", lower),
        ("🔴 맞았나", bool((ratio is not None and ratio > 5)
                        or (ratio is None and lower is not None and lower > 5))),
    ])
    fire = (g4.get("u=0") or {}).get("🔴🔴 복제에서 자 ① 규칙 「㉮ 만 선다」 발화율")
    rows["P2 관측 복제에서 「㉮ 만 선다」 발화율이 0.05 미만이다(u=0)"] = \
        collections.OrderedDict([("발화율", fire),
                                 ("🔴 맞았나", bool(fire is not None and fire < 0.05))])
    cen = [(u, (g4.get(u) or {}).get("🔴🔴🔴 버려진 것이 전부 완전 단조인가(= 정보성 검열)"),
            (g4.get(u) or {}).get("🔴🔴 버려진 복제 수"),
            (g4.get(u) or {}).get("🔴🔴🔴 버려진 복제 중 「어떤 계열이 `N_B` 의 완전 단조」인 것"))
           for u in ("u=0", "u=3")]
    rows["P3 버려진 복제는 전부 `N_B` 의 완전 단조다(정보성 검열)"] = \
        collections.OrderedDict([("λ 별", cen),
                                 ("🔴 맞았나", bool(all(x[1] for x in cen)))])
    n_it = it.get("⑤′ 반복")
    rows["P4 `⑤′` 가 3 판 안에 수렴한다"] = collections.OrderedDict([
        ("반복 횟수", n_it), ("수렴했나", it.get("⑤′ 수렴")),
        ("🔴 맞았나", bool(it.get("⑤′ 수렴") and n_it is not None and n_it <= 3)),
    ])
    d_it = it.get("문서 반복")
    rows["P5 문서↔채점 고리가 3 판 안에 수렴한다"] = collections.OrderedDict([
        ("반복 횟수", d_it),
        ("수렴했나", (ce.get("§가 🔴🔴🔴 985 자신") or {}).get(
            "🔴🔴🔴 수렴했나(다섯 칸이 전부 같다)")),
        ("🔴 맞았나", bool((ce.get("§가 🔴🔴🔴 985 자신") or {}).get(
            "🔴🔴🔴 수렴했나(다섯 칸이 전부 같다)") and d_it is not None and d_it <= 3)),
    ])
    fails = fp.get("🔴 실패한 절")
    fails = fails if isinstance(fails, list) else []
    lane = [x for x in fails if x.startswith("8 🔴 `[수리]`")]
    rows["P6 `⑤′` 실패 절이 3 이하이고 그중 레인 계수가 없다"] = collections.OrderedDict([
        ("실패 절 수", len(fails)), ("실패 절", fails or "없음"),
        ("레인 계수가 실패에 있나", bool(lane)),
        ("🔴 맞았나", bool(len(fails) <= 3 and not lane)),
    ])
    hit = sum(1 for v in rows.values() if v["🔴 맞았나"])
    return rows, hit


# ══════════════════════════════════════════════════════════════════════
def stage(ref, prereg_commit, five_name, blocked, it):
    t0 = CY.now()
    CY.begin(ref)
    cs0 = CY.code_stamp()
    #: 🔴 **면제 규칙을 하나도 새로 안 만든다** --- 983·984 가 쓴 것을 «그대로» 쓴다
    #:  (조항 66-③: 자를 바꾸면 전후를 같이 싣는데, 여기서는 **안 바꿨다**).
    rules = LG.ALLOW_CTX + INHERIT
    tb = _load(TBL)
    ctx = {
        "audit": _load("out985_audit.json", must=True),
        "power": _load("out985_power.json", must=True),
        "house": _load("out985_house.json"),
        "certify": _load("out985_certify.json"),
        "five": _load(five_name),
        "prereg_commit": prereg_commit,
        "blocked": blocked,
        "iter": it,
    }
    ctx["ruleD"] = rule_d(tb, rules)
    ctx["shape"] = shape_audit()
    ctx["feeds"] = feeds_stamp()
    ctx["reg"] = registered_denominators()
    ctx["six"] = six_places(ctx["five"])
    ctx["n_falsify"] = 14
    ctx["n_predict"] = 6
    rows, bad = falsify(ctx)
    prows, hit = predict(ctx)
    out = collections.OrderedDict()
    out["무엇"] = "985 채점 — 🔴 반증조건 14 · 예측 6 · 규칙 D 분모 5"
    out["🔴 축"] = "C1 상태→예측(몸통) · 곁 C3"
    out["사전등록"] = PREREG
    out["🔴🔴 조항 60-다 · 사전등록이 박은 분모"] = ctx["reg"]
    out["§6 🔴 반증조건"] = collections.OrderedDict([
        ("🔴 분모", len(rows)),
        ("🔴 조건별", rows),
        ("🔴🔴 반증된 조건", bad or "없음"),
        ("🔴🔴 분자 / 분모", "%d / %d" % (len(rows) - len(bad), len(rows))),
        ("통과", bool(not bad)),
    ])
    out["§5 🔴 예측"] = collections.OrderedDict([
        ("🔴 분모", len(prows)),
        ("🔴 예측별", prows),
        ("🔴🔴 분자 / 분모", "%d / %d" % (hit, len(prows))),
        ("🔴 분자", hit),
        ("통과", bool(hit == len(prows))),
    ])
    out["§D 🔴 규칙 D 감사(분모 다섯)"] = ctx["ruleD"]
    out["§68 🔴 조항 68 모양 주장 감사"] = ctx["shape"]
    out["§F5 🔴 인용 산출물 도장"] = ctx["feeds"]
    out["§9 🔴🔴 여섯 자리가 같은 수를 적나"] = ctx["six"]
    out["통과"] = bool(out["§6 🔴 반증조건"]["통과"] and ctx["ruleD"]["통과"])
    CY.write(OUT, out, ref, cs0, t0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["score"])
    ap.add_argument("--ref", required=True)
    ap.add_argument("--prereg-commit", required=True)
    ap.add_argument("--five", default="fiveprime_985.json")
    ap.add_argument("--blocked", default="[]",
                    help="🔴 조항 69 --- 막힌 명령 신고(JSON 배열). "
                         "없으면 `[\"없었다\"]` 를 준다")
    ap.add_argument("--five-iter", type=int, default=None)
    ap.add_argument("--five-conv", default=None)
    ap.add_argument("--five-why", default="")
    ap.add_argument("--doc-iter", type=int, default=None)
    a = ap.parse_args()
    it = {"⑤′ 반복": a.five_iter,
          "⑤′ 수렴": (None if a.five_conv is None else a.five_conv == "true"),
          "⑤′ 판별": a.five_why,
          "문서 반복": a.doc_iter}
    r = stage(a.ref, a.prereg_commit, a.five, json.loads(a.blocked), it)
    print(json.dumps({
        "반증조건": r["§6 🔴 반증조건"]["🔴🔴 분자 / 분모"],
        "반증된 것": r["§6 🔴 반증조건"]["🔴🔴 반증된 조건"],
        "예측": r["§5 🔴 예측"]["🔴🔴 분자 / 분모"],
        "규칙 D 표 밖": r["§D 🔴 규칙 D 감사(분모 다섯)"]["🔴🔴 표 밖 합"],
        "통과": r["통과"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
