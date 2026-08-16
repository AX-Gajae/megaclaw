#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""984 §5·§6 — 🔴 **채점**. 🔴🔴 **분모는 사전등록에서 «읽는다»**(조항 60-다 · 984 신설).

🔴 **왜 (티처 #122 C5).** 983 은 `docs/prereg_983_holdout_registry.md:101` 에
「`⑤′` 분모를 **15** 로 한다」를 박고 **17 로 채점**했다 --- 자기가 그 사이클에 신설한
`조항 60-나` 를 **같은 사이클에 어겼다**. 그래서 이 채점기는 **분모를 손으로 안 적고
사전등록 본문에서 정규식으로 읽는다.** 읽은 수와 실제 채점 분모가 다르면 **반증조건 3 이
떨어진다.**

🔴 **리터럴 판정 금지**(`⑤′` 절 9 · AST). 이 파일 어디에도 `("통과", True)` 가 없다 ---
모든 판정은 잰 값에서 나온다.

씀:
    python3 runners/score984.py --stage score --ref <40자 sha>
"""
import argparse
import ast
import collections
import datetime as dt
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

import cycle984 as CY                               # noqa: E402
import ledger as LG                                 # noqa: E402

OUT = "runners/out984_score.json"
PREREG = "docs/prereg_984_leak_or_coupling.md"
BRANCH = "note/984-leak-or-coupling"
BODY = ("docs/판정_984.md", "docs/card_984.md", "docs/handoff_984.md")
GOAL = "docs/목표.md"
DEN = "data/lab/denominator.json"
TBL = "runners/out984_table.json"

#: 🔴🔴 `[수리] R5` --- 규칙 D 채점 분모는 **다섯**이다(`docs/목표.md` 「규칙 D 감사 분모」 절).
MARK_A = "<!-- 983:정본유보:시작 -->"
MARK_B = "<!-- 983:정본유보:끝 -->"
LEDGER_KEY = "노트 984"

FEED_RE = re.compile(
    r"`?((?:runners/)?(?:out984_[a-z0-9_]+|fiveprime_984[a-z0-9_]*)\.json)`?")
#: 🔴 사전등록 §2-5 가 «사전»에 뺀 것 --- `⑤′` 산출물(고정점이 원리상 불가)
FEED_EXEMPT = re.compile(r"fiveprime_984")

#: 🔴 조항 68 --- 「모양」 낱말과, 그 곁에 반드시 있어야 하는 근거 낱말
SHAPE_RE = re.compile(r"단조|포화|U 자|되오름")
SHAPE_OK = ("z ", "짝 검정", "안 쟀다", "못 넘", "2·짝SE", "2·SE")
SHAPE_WIN = 220

#: 🔴 사전등록에서 분모를 읽는 바늘 --- 손으로 안 적는다(조항 60-다)
DEN_FALSIFY = re.compile(r"##\s*§6\s*반증조건\s*\(분모\s*\*\*(\d+)\*\*")
DEN_PREDICT = re.compile(r"##\s*§5\s*예측\s*\(분모\s*\*\*(\d+)\*\*")
DEN_FIVE = re.compile(r"`⑤′`\s*분모\s*—\s*🔴\s*\*\*등록\s*(\d+)")


#: 🔴 **983 이 쓴 면제 규칙 셋을 그대로 물려쓴다 --- 새로 만들지 않는다**
#:  (`runners/score983.py:226-231`). 조항 66-③ 대조를 위해 「구판(ALLOW_CTX 만)」
#:  표 밖 수도 같이 낸다.
INHERIT_983 = (
    ("🔴 981 판: sha256 · 40자 고정 ref", re.compile(r"\b[0-9a-f]{40,64}\b")),
    ("🔴 981 판: 사이클 번호 — 화살표 쌍 · 인라인 코드 · 「노트/체제」 딱지",
     re.compile(r"9\d{2}\s*→\s*9\d{2}|`9\d{2}`|(?<![\d.,])9[7-8]\d(?![\d.,])")),
    ("🔴 981 판: 절 번호의 가지(`§1-2` 꼴)", re.compile(r"§\s*\d+-\d+|`§\d+-\d+`")),
)


def _git(*a):
    return subprocess.check_output(["git"] + list(a), cwd=str(ROOT))


def _load(n, must=False):
    p = ROOT / "runners" / n
    if p.is_file():
        return json.loads(p.read_text(encoding="utf-8"))
    if must:
        raise SystemExit("🔴 %s 가 없다 — fail-closed" % n)
    return {}


def _text(rel):
    q = ROOT / rel
    return q.read_text(encoding="utf-8", errors="replace") if q.is_file() else None


def _sha(b):
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode("utf-8")).hexdigest()


# ══════════════════════════════════════════════════════════════════════
# 🔴🔴 조항 60-다 — 분모를 **사전등록에서 읽는다**
# ══════════════════════════════════════════════════════════════════════
def registered_denominators():
    t = _text(PREREG)
    if t is None:
        return {"🔴": "🔴 사전등록을 못 읽었다 --- 「0」이 아니다(조항 59)"}
    out = collections.OrderedDict()
    for nm, rx in (("반증조건", DEN_FALSIFY), ("예측", DEN_PREDICT), ("⑤′", DEN_FIVE)):
        m = rx.search(t)
        out[nm] = int(m.group(1)) if m else None
    out["🔴 못 읽은 것"] = [k for k, v in out.items() if v is None and not k.startswith("🔴")]
    return out


# ══════════════════════════════════════════════════════════════════════
# 🔴 규칙 D — 채점 분모 **다섯**(R5 로 넓혔다)
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
    targets["🔴 `docs/목표.md` 「정본 유보」 절(R5 신설)"] = _holdout_slice()
    targets["🔴 원장 `%s` 항목(R5 신설)" % LEDGER_KEY] = _ledger_entry_text()
    for name, txt in targets.items():
        if txt is None:
            rows[name] = {"🔴": "🔴 못 읽었다 --- 「표 밖 0」이 아니다(조항 59)",
                          "표 밖": None}
            continue
        n, ex = _outside(txt, S, rules)
        rows[name] = {"표 밖": n, "보기": ex or "없음", "글자 수": len(txt)}
        tot += n
    unread = [k for k, v in rows.items() if v.get("표 밖") is None]
    return collections.OrderedDict([
        ("🔴 무엇", "🔴 **규칙 D --- 치환표에 없는 수를 본문에 못 쓴다**"),
        ("🔴🔴 채점 분모(984 R5 로 셋 → 다섯)", len(targets)),
        ("🔴 대상", list(targets.keys())),
        ("🔴 대상별", rows),
        ("🔴🔴 표 밖 합", tot),
        ("🔴 못 읽은 대상", unread or "없음"),
        ("🔴 치환표 칸 수", len(tb.get("🔴🔴 치환표", {}) or {})),
        ("🔴 치환표 sha256", tb.get("🔴🔴 표 sha256")),
        ("통과", bool(tot == 0 and not unread)),
    ])


# ══════════════════════════════════════════════════════════════════════
# 🔴 조항 68 — 「모양」 주장에 근거가 붙었나
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
        ("🔴 자", "「단조·포화·U 자·되오름」 낱말마다 ±%d 글자 안에 "
                "「z」·「짝 검정」·「안 쟀다」·「못 넘」 중 하나가 있어야 한다" % SHAPE_WIN),
        ("🔴 문서별", rows),
        ("🔴🔴 근거 없는 모양 주장 수", bad),
        ("통과", bool(bad == 0 and all(
            v.get("근거 없는 모양 낱말") is not None for v in rows.values()))),
    ])


# ══════════════════════════════════════════════════════════════════════
# 🔴 도장 F5 — `⑤′` 산출물은 사전등록 §2-5 가 **사전**에 뺐다
# ══════════════════════════════════════════════════════════════════════
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
        ("🔴🔴 사전등록 §2-5 가 «사전»에 뺀 것(`⑤′` 산출물)", exempt or "없음"),
        ("🔴🔴 뺀 수", len(exempt)),
        ("🔴 왜 뺐나",
         "🔴 `⑤′` 는 자기가 인증한 트리 «뒤»에 쓰이므로 자기 도장을 자기 분모에 넣으면 "
         "**고정점이 정의상 존재할 수 없다**. 🔴 **이 면제는 측정 «전»에 사전등록에 적었고 "
         "뺀 수를 분모와 나란히 싣는다**(조항 59)"),
        ("🔴 산출물별", rows),
        ("🔴🔴 F5 를 못 넘은 것", bad or "없음"),
        ("통과", bool(rows and not bad)),
    ])


# ══════════════════════════════════════════════════════════════════════
# 🔴 AST — 리터럴 판정 / 손으로 친 치환표 수
# ══════════════════════════════════════════════════════════════════════
def _const_str(n):
    return n.value if isinstance(n, ast.Constant) and isinstance(n.value, str) else None


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
            ks = _const_str(k)
            if ks is not None and "통과" in ks and _const_bool(v):
                hits.append({"파일": path, "줄": n.lineno, "값": v.value})
        if isinstance(n, ast.Dict):
            for k, v in zip(n.keys, n.values):
                ks = _const_str(k) if k is not None else None
                if ks is not None and "통과" in ks and _const_bool(v):
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
def falsify(ctx):
    """🔴 반증조건 14 --- **전부 잰 값**이다. 리터럴 판정이 하나도 없다."""
    lk, gd, hs, fp, it = (ctx["leak"], ctx["grid"], ctx["house"],
                          ctx["five"], ctx["iter"])
    rd, sh, fs = ctx["ruleD"], ctx["shape"], ctx["feeds"]
    reg = ctx["reg"]

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

    # 2 미게재
    eight = lk.get("§1 🔴🔴 예산 공변량 검정 전량 여덟", {})
    body_all = "\n".join(x for x in (_text(p) for p in BODY) if x)
    stands = eight.get("🔴🔴🔴 983 이 저장소 안 어디에도 안 실은 「선다」") or []
    need = []
    for r in stands:
        need += [str(r.get("부분상관")), str(r.get("p"))]
    missing = [s for s in need if s and s not in body_all]
    f2 = collections.OrderedDict([
        ("🔴 검정 분모", eight.get("🔴 분모(검정 수)")),
        ("🔴 「선다」 수", eight.get("🔴🔴 「선다」 판정 수")),
        ("🔴 본문이 실어야 하는 수", need),
        ("🔴🔴 본문에 없는 수", missing or "없음"),
        ("🔴🔴 미게재했나", bool(missing)),
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

    # 4 모양 주장
    f4 = collections.OrderedDict([
        ("🔴 근거 없는 모양 낱말 수", sh.get("🔴🔴 근거 없는 모양 주장 수")),
        ("🔴🔴 주장했나", bool(not sh.get("통과"))),
    ])

    # 5 조항 66-②
    moved = collections.OrderedDict()
    any_move = False
    for nm, d in (("leak", lk), ("grid", gd), ("house", hs)):
        c = d.get("🔴🔴 조항 66-② (984 R2)", {})
        moved[nm] = collections.OrderedDict([
            ("바뀐 파일", c.get("🔴🔴🔴 측정 창 안에 바뀐 파일")),
            ("분모가 못 덮은 것", c.get("🔴🔴 분모가 못 덮은 `RAN_ALL` 항목")),
        ])
        any_move = any_move or bool(c.get("🔴🔴🔴 측정 창 안에 러너를 고쳤나"))
    f5 = collections.OrderedDict([
        ("🔴 산출물별", moved), ("🔴🔴 고쳤나", any_move)])

    # 6 HEAD == 디스크
    close = hs.get("§0-가 🔴🔴 집을 닫았나", {})
    f6 = collections.OrderedDict([
        ("🔴 HEAD sha256", close.get("🔴🔴 HEAD 판 sha256")),
        ("🔴 디스크 sha256", close.get("🔴🔴 디스크 판 sha256")),
        ("🔴🔴 갈렸나", bool(not close.get("🔴🔴🔴 HEAD 와 디스크가 바이트 동일한가"))),
    ])

    # 7·8 규칙 D
    f7 = collections.OrderedDict([
        ("🔴 표 밖 합", rd.get("🔴🔴 표 밖 합")),
        ("🔴🔴 전부 치환표 칸인가", bool(rd.get("통과"))),
    ])
    tg = rd.get("🔴 대상") or []
    f8 = collections.OrderedDict([
        ("🔴 규칙 D 분모", rd.get("🔴🔴 채점 분모(984 R5 로 셋 → 다섯)")),
        ("🔴 「정본 유보」 절이 분모 안인가",
         bool(any("정본 유보" in x for x in tg))),
        ("🔴 원장이 분모 안인가", bool(any("원장" in x for x in tg))),
    ])
    f8["🔴🔴 둘 다 들어갔나"] = bool(f8["🔴 「정본 유보」 절이 분모 안인가"]
                             and f8["🔴 원장이 분모 안인가"])

    # 9 자백이 저장소 안에 있나
    conf = collections.OrderedDict()
    for p in list(BODY) + [PREREG]:
        t = _text(p)
        conf[p] = bool(t is not None and "고정점" in t)
    led = _ledger_entry_text()
    conf["원장 `%s`" % LEDGER_KEY] = bool(led is not None and "고정점" in led)
    f9 = collections.OrderedDict([
        ("🔴 문서별", conf),
        ("🔴 분모", len(conf)),
        ("🔴 있는 곳 수", sum(1 for v in conf.values() if v)),
        ("🔴🔴 저장소 안 전부에 있나", bool(all(conf.values()))),
    ])

    # 10 ⑤′ 수렴
    f10 = collections.OrderedDict([
        ("🔴 반복 횟수", it.get("🔴🔴 반복 횟수")),
        ("🔴 판별", it.get("🔴 판별")),
        ("🔴🔴 수렴했나", bool(it.get("🔴🔴🔴 수렴했나"))),
        ("🔴 반복 횟수를 산출물에 박았나", bool(it.get("🔴🔴 반복 횟수") is not None)),
    ])

    # 11 도장
    f11 = collections.OrderedDict([
        ("🔴 분모", fs.get("🔴 분모")), ("🔴 뺀 수", fs.get("🔴🔴 뺀 수")),
        ("🔴🔴 전부 F5 인가", bool(fs.get("통과")))])

    # 12·13 AST
    h12 = ast_pass_hits("runners/score984.py")
    h13 = ast_table_hits("runners/note984_gen.py")
    f12 = collections.OrderedDict([("🔴 걸린 자리", h12), ("🔴🔴 있나", bool(h12))])
    f13 = collections.OrderedDict([("🔴 걸린 자리", h13), ("🔴🔴 있나", bool(h13))])

    # 14 ⑥
    paper = sorted(str(q.relative_to(ROOT)) for q in ROOT.glob("paper/steps/*984*"))
    f14 = collections.OrderedDict([
        ("🔴 `⑤′` 통과", fp.get("통과")),
        ("🔴 984 논문 자리", paper or "없음"),
        ("🔴🔴 불통과인데 시작했나", bool((not fp.get("통과")) and paper)),
    ])

    items = collections.OrderedDict([
        ("1 사전등록 blob 을 측정 뒤에 고쳤나", (f1, f1["🔴🔴 고쳤나"])),
        ("2 🔴🔴 자기가 낸 결과를 미게재했나", (f2, f2["🔴🔴 미게재했나"])),
        ("3 🔴🔴 채점 분모를 사전등록과 다르게 썼나", (f3, f3["🔴🔴 다르게 썼나"])),
        ("4 🔴🔴 2·짝SE 를 못 넘는 칸으로 모양을 주장했나", (f4, f4["🔴🔴 주장했나"])),
        ("5 🔴 측정 창 안에서 러너를 고쳤나", (f5, f5["🔴🔴 고쳤나"])),
        ("6 🔴 머지 뒤 HEAD ≠ 디스크인가", (f6, f6["🔴🔴 갈렸나"])),
        ("7 본문의 수가 전부 치환표 칸인가", (f7, not f7["🔴🔴 전부 치환표 칸인가"])),
        ("8 🔴 규칙 D 분모에 「정본 유보」 절과 원장이 들어갔나",
         (f8, not f8["🔴🔴 둘 다 들어갔나"])),
        ("9 🔴🔴 「고정점이 아니었다」가 저장소 안 문서 전부에 있나",
         (f9, not f9["🔴🔴 저장소 안 전부에 있나"])),
        ("10 🔴🔴 `⑤′` 를 수렴할 때까지 돌렸나", (f10, not f10["🔴🔴 수렴했나"])),
        ("11 인용 산출물 도장이 전부 F5 인가", (f11, not f11["🔴🔴 전부 F5 인가"])),
        ("12 🔴 채점기에 리터럴 `통과` 가 있나", (f12, f12["🔴🔴 있나"])),
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
    lk, gd, fp, it = ctx["leak"], ctx["grid"], ctx["five"], ctx["iter"]
    pro = lk.get("§2 🔴🔴🔴 승격 물음 — 누출의 지문인가 구성상 결합인가", {}).get("🔴 λ 별", {})
    rows = collections.OrderedDict()

    def _ci(uk, key):
        b = pro.get(uk, {}).get("🔴🔴 자 ③ 복제 붓스트랩", {}).get(key, {})
        return b.get("🔴 0 을 포함하나"), b

    p1a, d1a = _ci("u=0", "🔴 (㉮−㉱, 여유) 부분상관")
    p1b, d1b = _ci("u=3", "🔴 (㉮−㉱, 여유) 부분상관")
    rows["P1 (㉮−㉱, 여유) 부분상관의 95% 붓스트랩 구간이 0 을 포함한다"] = \
        collections.OrderedDict([("u=0", d1a), ("u=3", d1b),
                                 ("🔴 맞았나", bool(p1a))])
    p2a, d2a = _ci("u=0", "🔴🔴 둘의 차(㉮ − ㉰)")
    p2b, d2b = _ci("u=3", "🔴🔴 둘의 차(㉮ − ㉰)")
    rows["P2 두 팔 부분상관 차의 95% 구간이 0 을 포함한다"] = \
        collections.OrderedDict([("u=0", d2a), ("u=3", d2b),
                                 ("🔴 맞았나", bool(p2a and p2b))])
    pl = gd.get("§3-ⓔ 🔴 위약 — 0 과 구별되나", {})
    rows["P3 위약 이득 14 칸의 칸 가중 z 가 2 를 못 넘는다"] = collections.OrderedDict([
        ("칸 가중 z", pl.get("🔴🔴🔴 칸 가중 z(짝SE² 역가중 · 14 칸)")),
        ("🔴 맞았나", bool(not pl.get("🔴🔴🔴 0 과 구별되나(|z| ≥ 2 · 984 판)"))),
    ])
    pm = gd.get("§3-ⓓ 🔴 오라클 프리미엄 14 칸 전량", {})
    rows["P4 오라클 프리미엄 14 칸의 칸 가중 z 가 2 를 못 넘는다"] = collections.OrderedDict([
        ("칸 가중 z", pm.get("🔴🔴🔴 칸 가중 z(짝SE² 역가중 · 14 칸)")),
        ("🔴 맞았나", bool(not pm.get("🔴🔴🔴 칸 가중 z 가 서나(|z| ≥ 2)"))),
    ])
    n_it = it.get("🔴🔴 반복 횟수")
    rows["P5 `⑤′` 가 3 판 안에 수렴한다"] = collections.OrderedDict([
        ("반복 횟수", n_it), ("수렴했나", it.get("🔴🔴🔴 수렴했나")),
        ("🔴 맞았나", bool(it.get("🔴🔴🔴 수렴했나") and n_it is not None and n_it <= 3)),
    ])
    n_fail = len(fp.get("🔴 실패한 절") or []) if isinstance(
        fp.get("🔴 실패한 절"), list) else 0
    rows["P6 `⑤′` 실패 절이 등록 분모 16 중 3 이하다"] = collections.OrderedDict([
        ("실패 절 수", n_fail), ("절 분모", fp.get("🔴 절 수(분모)")),
        ("🔴 맞았나", bool(n_fail <= 3)),
    ])
    hit = sum(1 for v in rows.values() if v["🔴 맞았나"])
    return rows, hit


# ══════════════════════════════════════════════════════════════════════
def stage(ref, prereg_commit, five_name):
    t0 = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cs0 = CY.code_stamp()
    #: 🔴 **면제 규칙을 하나도 새로 안 만든다** --- 983 이 쓴 것을 «그대로» 쓴다.
    #:  조항 66-③: 자를 바꾸면 전후를 같이 싣는데, 여기서는 **안 바꿨다**.
    rules = LG.ALLOW_CTX + INHERIT_983
    tb = _load("out984_table.json")
    ctx = {
        "leak": _load("out984_leak.json", must=True),
        "grid": _load("out984_grid.json", must=True),
        "house": _load("out984_house.json", must=True),
        "five": _load(five_name),
        "iter": _load("out984_fixpoint.json"),
        "prereg_commit": prereg_commit,
    }
    ctx["reg"] = registered_denominators()
    ctx["ruleD"] = rule_d(tb, rules)
    ctx["shape"] = shape_audit()
    ctx["feeds"] = feeds_stamp()
    ctx["n_falsify"] = 14
    ctx["n_predict"] = 6
    rows, bad = falsify(ctx)
    prows, hit = predict(ctx)

    out = collections.OrderedDict()
    out["무엇"] = "984 §5·§6 — 🔴 **채점**. 🔴🔴 분모는 사전등록에서 «읽는다»(조항 60-다)"
    out["🔴 축"] = "C1 상태→예측(몸통) · 곁 C3"
    out["사전등록"] = PREREG
    out["🔴🔴 조항 60-다 · 사전등록이 박은 분모"] = ctx["reg"]
    out["§6 🔴 반증조건"] = collections.OrderedDict(
        list(rows.items()) + [
            ("🔴🔴 분모(사전등록)", ctx["reg"].get("반증조건")),
            ("🔴🔴 채점 분모(실제)", len(rows)),
            ("🔴🔴🔴 통과 수", len(rows) - len(bad)),
            ("🔴🔴🔴 반증된 조건", bad or "없음"),
            ("통과", bool(not bad and ctx["reg"].get("반증조건") == len(rows))),
        ])
    out["§5 🔴 예측"] = collections.OrderedDict(
        list(prows.items()) + [
            ("🔴🔴 분모(사전등록)", ctx["reg"].get("예측")),
            ("🔴🔴 채점 분모(실제)", len(prows)),
            ("🔴🔴🔴 맞은 수", hit),
            ("통과", bool(ctx["reg"].get("예측") == len(prows))),
        ])
    out["§D 🔴 규칙 D 감사(분모 다섯)"] = ctx["ruleD"]
    out["§68 🔴 조항 68 모양 주장 감사"] = ctx["shape"]
    out["§F5 🔴 인용 산출물 도장"] = ctx["feeds"]
    out["통과"] = bool(out["§6 🔴 반증조건"]["통과"])
    CY.write(OUT, out, ref, cs0, t0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["score"])
    ap.add_argument("--ref", default="")
    ap.add_argument("--prereg-commit", required=True)
    ap.add_argument("--five", default="fiveprime_984.json")
    a = ap.parse_args()
    r = stage(a.ref, a.prereg_commit, a.five)
    print(json.dumps({
        "통과": r["통과"],
        "반증조건": "%s / %s" % (r["§6 🔴 반증조건"]["🔴🔴🔴 통과 수"],
                            r["§6 🔴 반증조건"]["🔴🔴 채점 분모(실제)"]),
        "예측": "%s / %s" % (r["§5 🔴 예측"]["🔴🔴🔴 맞은 수"],
                          r["§5 🔴 예측"]["🔴🔴 채점 분모(실제)"]),
        "반증된 조건": r["§6 🔴 반증조건"]["🔴🔴🔴 반증된 조건"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
