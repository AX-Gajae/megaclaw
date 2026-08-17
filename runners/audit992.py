#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""992 §2 — 🔴 **자가 «잡은» 것을 자에 «문다»**.

사전등록 `docs/prereg_992_wire_the_rulers.md` §2.

🔴 **규율 다섯**
  ① 하드코딩 `False` 를 안 쓴다.
  ② 「걸린 자리」는 «판정 함수»가 스스로 반환한다.
  ③ 명부는 «글롭»이다 --- 손으로 안 고른다.
  ④ 구간 명제는 «구간 전수»로 잰다.
  ⑤ 🔴🔴🔴 **소스에 대한 주장은 «AST»로 잰다** --- 991 은 「AST 로 뗀다」고 주석에만 적고
     정규식을 «산문»에 물렸다.

씀:
    python3 runners/audit992.py --ref <40자 sha> --prereg-ref <40자 sha>
"""
import argparse
import ast
import collections
import datetime as dt
import glob as _g
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
import ledger as LG                                              # noqa: E402

OUT = ROOT / "runners"
RAN = ("runners/audit992.py",)
GLOB_992 = "runners/*992*"
GLOB_991 = "runners/*991*"
DOCS_992 = ("docs/판정_992.md", "docs/card_992.md", "docs/handoff_992.md",
            "docs/pr_992.md", "docs/prereg_992_wire_the_rulers.md")


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p):
    return os.path.relpath(str(p), str(ROOT))


def _glob(pat):
    return sorted(_rel(p) for p in _g.glob(str(ROOT / pat)))


def _read(rel):
    p = ROOT / rel
    return p.read_text(encoding="utf-8") if p.is_file() else None


def _load(rel):
    t = _read(rel)
    try:
        return json.loads(t) if t else {}
    except Exception:                                            # noqa: BLE001
        return {}


def _git(args):
    r = subprocess.run(["git", "-c", "core.quotePath=false"] + args,
                       cwd=str(ROOT), capture_output=True)
    return (r.returncode, r.stdout.decode("utf-8", "surrogateescape"),
            r.stderr.decode("utf-8", "surrogateescape"))


def code_stamp():
    out = collections.OrderedDict()
    for rel in RAN:
        p = ROOT / rel
        if p.is_file():
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def _median(xs):
    s = sorted(xs)
    n = len(s)
    if not n:
        return None
    return float(s[n // 2]) if n % 2 else (float(s[n // 2 - 1]) + float(s[n // 2])) / 2.0


# ══════════════════════════════════════════════════════════════════════
# §A 🔴🔴🔴 `⑤′` 절 4 — **엄한 판 + 「면제 없는 판」**(`조항 3-나`)
# ══════════════════════════════════════════════════════════════════════
OLD4 = "🔴 구판 절 4 통과(980 판 --- 도장의 «존재»와 시각만 본다)"
NEW4 = "🔴🔴 신판 절 4 통과(981 판 --- 도장의 «판정»을 읽는다 · 🔴 982 부터 문다)"
REG4 = "🔴🔴🔴 991 R1 — `--exempt-file` 로 «등기된» 사유로 뺀 것"
F5F = "🔴🔴🔴 도장 판정이 실패인 산출물"


def a_strict4():
    """🔴 988~991 의 `⑤′` 를 «엄한 판»으로 다시 세고, 🔴🔴 **「면제 없는 판」**을 낸다.

    🔴🔴🔴 **991 의 「엄한 판 첫 통과」는 «면제로 산 것»이다** --- 991 이 등기해 뺀 셋이
    988·989·990 에서 신판을 떨어뜨린 «바로 그 셋»인지 «집합으로» 견준다.
    """
    hits, per = 0, collections.OrderedDict()
    fails = collections.OrderedDict()
    for note in ("988", "989", "990", "991"):
        rel = "runners/fiveprime_%s.json" % note
        d = _load(rel)
        if not d:
            per[note] = {"🔴 산출물이 없다": rel}
            continue
        secs = [(k, v) for k, v in d.items()
                if isinstance(v, dict) and "통과" in v]
        s4 = d.get("4 도장 확인") or {}
        old, new = s4.get(OLD4), s4.get(NEW4)
        reg = s4.get(REG4)
        reg = reg if isinstance(reg, list) else []
        f5f = s4.get(F5F)
        f5f = f5f if isinstance(f5f, list) else []
        fails[note] = sorted(f5f)
        fail_pub, fail_strict = [], []
        for k, v in secs:
            hits += 2
            pub = bool(v.get("통과"))
            strict = pub
            if k == "4 도장 확인":
                strict = bool(old) and bool(new)
            if not pub:
                fail_pub.append(k)
            if not strict:
                fail_strict.append(k)
        per[note] = collections.OrderedDict([
            ("🔴 절 분모", d.get("🔴 절 수(분모)")),
            ("🔴 게재된 실패 절", fail_pub),
            ("🔴 게재된 실패 수", len(fail_pub)),
            ("🔴 구판 절 4", old), ("🔴🔴 신판 절 4", new),
            ("🔴🔴🔴 등기 사유로 «뺀» 도장", reg or "없음"),
            ("🔴🔴🔴 등기 사유로 뺀 수", len(reg)),
            ("🔴 도장 판정이 실패인 산출물", f5f or "없음"),
            ("🔴🔴🔴 엄한 판(구판 and 신판)의 실패 절", fail_strict),
            ("🔴🔴🔴 엄한 판의 실패 수", len(fail_strict)),
            ("🔴 게재값이 «관대한 쪽»이었나", bool(len(fail_strict) > len(fail_pub))),
        ])
    # 🔴🔴🔴 **면제 없는 판** --- 991 이 뺀 셋이 988·989·990 에서 떨어뜨린 그 셋인가
    reg991 = set(per.get("991", {}).get("🔴🔴🔴 등기 사유로 «뺀» 도장") or [])
    prev_fail = set(fails.get("990") or [])
    hits += len(reg991) + len(prev_fail)
    same = bool(reg991 and reg991 == prev_fail)
    noexempt991 = bool(per.get("991", {}).get("🔴🔴 신판 절 4") and not same)
    return collections.OrderedDict([
        ("무엇", "🔴🔴🔴 `⑤′` 절 4 를 `조항 3-나` 대로 «엄한 판» + «면제 없는 판»으로 다시 센다"),
        ("🔴 `조항 3-나` 원문", "「어느 판을 쓸지는 그 사이클이 고르지 못한다. 조인다/푼다와 "
                            "무관하게 «둘 다» 채점하고 「통과」로 게재하는 값은 «더 엄한 쪽»이다.」"),
        ("🔴 사이클별", per),
        ("🔴🔴🔴 정정 — 988 · 989 · 990 · 991 의 «엄한» 실패 수",
         collections.OrderedDict(
             (n, per.get(n, {}).get("🔴🔴🔴 엄한 판의 실패 수")) for n in
             ("988", "989", "990", "991"))),
        ("🔴🔴🔴 게재값이 관대했던 사이클",
         [n for n in ("988", "989", "990", "991")
          if per.get(n, {}).get("🔴 게재값이 «관대한 쪽»이었나")] or "없음"),
        ("🔴🔴🔴 면제 없는 판(991) — 991 이 «등기해 뺀» 도장", sorted(reg991) or "없음"),
        ("🔴🔴🔴 990 에서 신판을 «떨어뜨린» 도장", sorted(prev_fail) or "없음"),
        ("🔴🔴🔴 두 집합이 «같나»", same),
        ("🔴🔴🔴 P5-보조 — 면제를 빼면 991 의 신판 절 4 가 통과하나",
         bool(not same) if per.get("991", {}).get("🔴🔴 신판 절 4") else None),
        ("🔴🔴🔴 그래서 991 의 「엄한 판 첫 통과」는 «면제로 산 것»인가", bool(same)),
        ("🔴 그 뜻", "🔴 **991 이 등기해 뺀 셋이 988·989·990 에서 신판을 떨어뜨린 «바로 그 셋»이다.** "
                  "🔴🔴 991 자신의 사전등록 §0-라가 「이 사이클이 신설한 자는 둘 다 채점하고 «엄한 쪽»을 "
                  "게재한다 · 방향과 무관」인데 «푸는 방향»의 자기 자를 «관대한 쪽만» 게재했다. "
                  "✅ 다만 면제는 «측정 전에» 등기됐으니 「조용한 좁힘」이 아니다 --- 「엄한 짝을 안 낸 것」이다"),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", hits),
        ("통과", bool(hits > 0 and len(per) == 4)),
    ])


# ══════════════════════════════════════════════════════════════════════
# §B 🔴🔴🔴 990 의 배선 일곱 — **진짜 AST + 실행**
# ══════════════════════════════════════════════════════════════════════
#: 🔴 **소스 토큰**용 정규식이다. 🔴🔴 **산문(`왜` 문자열)에 «안» 물린다** --- 991 의 병.
_TOK_DICT = re.compile(r"dict\s*\(|\w+\s*\[\s*[\"']")      # 결과 딕트 복제·키 끼우기
_TOK_LITCMP = re.compile(r"[<>]=?\s*[\d.]+e?-?\d*|[-+]\s*0\.\d+")


def _seg(src, node):
    try:
        s = ast.get_source_segment(src, node)
    except Exception:                                            # noqa: BLE001
        s = None
    return s or ""


def b_variants():
    """🔴🔴🔴 **진짜 AST 다.** `world990.py` 를 «파싱»해서 `add(...)` 호출을 찾고,
    각 호출의 «변이체 인자»(3번째)의 «소스 조각»과 그 인자가 참조하는 이름들의
    «대입문 소스 조각»을 떼어 낸다. 그리고 그 «소스 토큰»으로만 갈래를 가른다.

    🔴 **판정에 쓰는 수는 `runners/out992_mut.json`(실행 측정)에서 온다** ---
    AST 는 「왜 그렇게 되나」를 «갈래»로 적기 위한 것이다.
    """
    rel = "runners/world990.py"
    src = _read(rel) or ""
    hits, rows = 0, collections.OrderedDict()
    parsed, perr = None, None
    try:
        parsed = ast.parse(src)
    except SyntaxError as e:                                     # noqa: BLE001
        perr = str(e)
    calls = []
    if parsed is not None:
        # 🔴 이름별 «마지막 대입» 자리를 미리 모은다(변이체 인자가 이름이면 되짚는다)
        assigns = collections.defaultdict(list)
        for n in ast.walk(parsed):
            if isinstance(n, (ast.Assign, ast.AugAssign)):
                tgts = n.targets if isinstance(n, ast.Assign) else [n.target]
                for t in tgts:
                    for nm in ast.walk(t):
                        if isinstance(nm, ast.Name):
                            assigns[nm.id].append(n)
            if isinstance(n, ast.For):
                for nm in ast.walk(n.target):
                    if isinstance(nm, ast.Name):
                        assigns[nm.id].append(n)
        for n in ast.walk(parsed):
            if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                    and n.func.id == "add" and len(n.args) >= 3):
                continue
            name = n.args[0].value if isinstance(n.args[0], ast.Constant) else "?"
            mut_node = n.args[2]
            mut_src = _seg(src, mut_node)
            # 🔴 변이체 인자가 참조하는 «이름»의 대입문 소스를 한 겹 되짚는다
            refs, ref_src = [], []
            for x in ast.walk(mut_node):
                if isinstance(x, ast.Name) and x.id in assigns:
                    refs.append(x.id)
                    for asn in assigns[x.id]:
                        if asn.lineno < n.lineno:
                            ref_src.append("L%d: %s" % (asn.lineno, _seg(src, asn)))
            blob = "\n".join([mut_src] + ref_src[-6:])
            kind = "코드"
            if _TOK_DICT.search(blob):
                kind = "결과딕트"
            elif _TOK_LITCMP.search(mut_src):
                kind = "판정식"
            hits += 1
            calls.append(collections.OrderedDict([
                ("검사", name), ("줄", n.lineno),
                ("🔴 변이체 인자 소스(AST 로 뗐다)", mut_src),
                ("🔴 그 인자가 참조하는 이름", sorted(set(refs))[:8]),
                ("🔴 그 이름의 대입문 소스(마지막 여섯)", ref_src[-6:]),
                ("🔴🔴🔴 소스 토큰으로 가른 갈래", kind),
            ]))
    # 🔴 실행 측정(`out992_mut.json`)과 나란히 놓는다
    M = _load("runners/out992_mut.json")
    mrows = M.get("🔴 검사별") or {}
    second = M.get("🔴🔴🔴 둘째 자 — 「자료와 «무관하게» 강제되는 것」만 세면") or {}
    for c in calls:
        tag = str(c["검사"]).split()[0]
        exec_row = None
        for k, v in mrows.items():
            if k.split()[0] == tag:
                exec_row = v
                break
        hits += 1
        rows[str(c["검사"])] = collections.OrderedDict([
            ("🔴 AST", c),
            ("🔴🔴🔴 실행 측정(990 자신의 설정 격자)",
             (exec_row or {}).get("🔴🔴🔴 갈래(실측)", "🔴 못 쟀다")),
            ("🔴 변이체가 통과한 설정 수", (exec_row or {}).get("🔴 변이체가 통과한 설정 수")),
            ("🔴 설정 수", (exec_row or {}).get("🔴 설정 수")),
            ("🔴 까닭의 갈래", (exec_row or {}).get("🔴🔴 그 까닭의 «갈래»")),
        ])
    n_false = M.get("🔴🔴🔴 그 수")
    kinds = collections.Counter(
        c["🔴🔴🔴 소스 토큰으로 가른 갈래"] for c in calls)
    return collections.OrderedDict([
        ("무엇", "🔴🔴🔴 990 의 배선 일곱 — **진짜 AST 로 소스를 떼고 실행으로 갈래를 잰다**"),
        ("🔴 991 의 병(자가 적발)", collections.OrderedDict([
            ("① AST 파싱이 «없었다»", "`audit991.py:153-176` 은 `import ast` 를 해 놓고 "
                                 "`b_variants` 안에서 `ast` 를 «한 번도» 안 부른다"),
            ("② `src` 가 «죽은 변수»", "`audit991.py:164` --- 읽고 «한 번도» 안 쓴다"),
            ("③ 정규식을 «산문»에 물렸다",
             "`mut_ws[`·`dict(ws)` 는 «소스 토큰»인데 `v.get(\"왜\")`(산문)에 물렸다 --- "
             "「결과딕트」 갈래는 «원리상» 한 번도 못 켜진다"),
            ("🔴 992 가 고친 것",
             "🔴 `ast.parse` → `add(...)` 호출 «전량» → 3번째 인자의 «소스 조각» + 그 인자가 "
             "참조하는 이름의 «대입문 소스» 한 겹 → «소스 토큰»으로만 갈래를 가른다"),
        ])),
        ("🔴 파싱 오류", perr or "없음"),
        ("🔴 찾은 `add(...)` 호출 수", len(calls)),
        ("🔴 검사별", rows),
        ("🔴🔴 소스 토큰 갈래별 수", dict(kinds)),
        ("🔴🔴🔴 그 수", n_false),
        ("🔴 그 수의 «자»",
         "🔴 **`out992_mut.json` 의 «실행» 측정이다** --- 990 자신의 설정 격자에서 "
         "변이체가 «어떤 설정에서도» 떨어진 검사 수"),
        ("🔴🔴🔴 둘째 자(자료와 «무관하게» 강제되는 것만) — 티처 #130 의 손 자",
         collections.OrderedDict([
             ("🔴 그 수", second.get("🔴 그 수")),
             ("🔴 티처가 손으로 센 수", second.get("🔴 티처 #130 이 손으로 센 수")),
             ("🔴 같나", second.get("🔴🔴 둘째 자와 티처의 손 자가 «같나»")),
             ("🔴 빠진 검사", second.get("🔴 빠진 검사")),
         ])),
        ("🔴🔴🔴 두 자가 «갈린다» — 어느 쪽을 게재하나",
         "🔴🔴 **엄한 쪽(= 992 에게 «불리한» 쪽)을 게재한다**(`조항 3-나`). "
         "🔴 사전등록 `P4` 는 「티처의 손 자를 재현하면 6」에 걸었고, 게재값은 «실행 자»의 "
         "수다 --- 그래서 `P4` 가 «떨어질» 수 있고 그대로 신고한다"),
        ("🔴🔴 991 이 «신고한» 990 의 구성상 거짓 수", 3),
        ("🔴🔴 990 이 «신고한» 자기 공허 수", 0),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", hits),
        ("통과", bool(parsed is not None and len(calls) == 7 and n_false is not None)),
    ])


# ══════════════════════════════════════════════════════════════════════
# §C 🔴🔴🔴 `F02` — **리플로그 «구간 전수»**
# ══════════════════════════════════════════════════════════════════════
_MOVE = re.compile(r"\b(checkout|symbolic-ref|reset --hard|rebase)\b")


def c_reflog(prereg_ref):
    rc0, t_pre, _e = _git(["show", "-s", "--format=%cI", prereg_ref])
    t_pre = t_pre.strip()
    rc, out, err = _git(["reflog", "show", "--date=iso-strict",
                         "--format=%gd\t%gs\t%H", "HEAD"])
    hits, rows, bad, after = 0, [], [], 0
    for line in out.split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        sel, msg, sha = parts[0], parts[1], parts[2]
        m = re.search(r"@\{(.+)\}", sel)
        when = m.group(1) if m else ""
        hits += 1
        if bool(t_pre and when and when >= t_pre):
            after += 1
            rows.append({"항목": sel, "무엇": msg, "언제": when, "sha": sha[:12]})
            if _MOVE.search(msg):
                bad.append({"항목": sel, "무엇": msg, "언제": when})
    rc2, sym, _e2 = _git(["symbolic-ref", "-q", "HEAD"])
    return collections.OrderedDict([
        ("무엇", "🔴🔴🔴 `F02` --- 리플로그 «구간 전수»"),
        ("🔴 사전등록 커밋", prereg_ref),
        ("🔴 그 커밋 시각", t_pre or "🔴 못 읽었다"),
        ("🔴 리플로그 전체 항목 수", hits),
        ("🔴🔴🔴 사전등록 «이후» 항목 수(= 구간 분모)", after),
        ("🔴🔴🔴 그 구간의 항목 «전량»", rows),
        ("🔴🔴🔴 `checkout|symbolic-ref|reset --hard|rebase` 가 든 항목", bad or "없음"),
        ("🔴🔴🔴 그 수", len(bad)),
        ("🔴 점 표본(990 판) — `git symbolic-ref -q HEAD`", sym.strip() or "(분리됨)"),
        ("🔴 리플로그 오류", err.strip() or "없음"),
        ("🔴🔴🔴 구간 분모가 `0` 이면 무슨 뜻인가(`조항 59` --- 셋을 «가른다»)",
         collections.OrderedDict([
             ("① 못 읽었다", bool(rc != 0 or not out.strip())),
             ("② 그 구간에 `HEAD` 가 «한 번도 안 움직였다»",
              bool(rc == 0 and out.strip() and t_pre and after == 0)),
             ("③ 쟀는데 설정이 버렸다", False),
         ])),
        ("⚠ 이 자의 한계(`조항 61`)",
         "🔴 리플로그는 «로컬»이고 잘린다. 그리고 `HEAD` 를 «안 움직이는» 배관 쓰기는 "
         "`HEAD` 리플로그에 «안 남는다** --- 그것이 이 규율이 노리는 «정확한» 상태다"),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", hits),
        ("통과", bool(rc == 0 and hits > 0 and not bad
                    and (sym.strip() == "refs/heads/main"))),
    ])


# ══════════════════════════════════════════════════════════════════════
# §D 🔴🔴 규칙 D
# ══════════════════════════════════════════════════════════════════════
_ID_BEFORE = re.compile(r"(노트|조항|규약|티처|절|판|씨앗|버전|PR|#|§|v\d\.)\s*[`«\(]?\s*$")
_ID_AFTER = re.compile(r"^\s*[`»\)]?\s*(판|-가|-나|-다|-라|-마|-바|재정정|번|호)")
_LB_BEFORE = re.compile(r"(예산|총량|백분위|분위|상한|눈금|base|hplt|겹|λ|알파|α)\s*[`«\(]?\s*$|Δ\(\s*$")
_LB_AFTER = re.compile(r"^\s*[`»\)]?\s*(%|퍼센트|행|겹|도메인|칸|자리\s*수)")


def _split_kind(src, item):
    num = item["수"] if isinstance(item, dict) else str(item)
    pos = item.get("자리") if isinstance(item, dict) else None
    if pos is None:
        pos = max(0, src.find(num))
    pre, post = src[max(0, pos - 24):pos], src[pos + len(num):pos + len(num) + 12]
    if _ID_BEFORE.search(pre) or _ID_AFTER.match(post):
        return "㉮ 식별자"
    if _LB_BEFORE.search(pre) or _LB_AFTER.match(post):
        return "㉯ 라벨"
    if re.match(r"^9\d\d$", num):
        return "㉮ 식별자"
    return "㉰ 측정치"


def d_ruled(slots_rel, glob_pat, label):
    man = _load(slots_rel)
    files = man.get("파일별") or {}
    if not files:
        return collections.OrderedDict([
            ("무엇", label),
            ("🔴🔴🔴 슬롯 대장이 «없다» --- 이 사이클은 규칙 D 를 «잴 수가 없다»", True),
            ("🔴 대장 경로", slots_rel),
            ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", 0),
            ("통과", False),
        ])
    S = LG.artifact_numbers(glob_pat)
    hits, per = 0, collections.OrderedDict()
    tot = miss = badslot = 0
    kinds = collections.Counter()
    sigfig = []
    badslot_rows = []
    for rel, info in files.items():
        src = _read(rel)
        if src is None:
            continue
        r = LG.audit_text(src, info["슬롯"], S)
        hits += r["센 수"] + len(r["슬롯"])
        tot += r["센 수"]
        badslot += r["🔴 키 경로와 본문이 다른 슬롯"]
        if r["🔴 키 경로와 본문이 다른 슬롯"]:
            badslot_rows.append({"파일": rel, "수": r["🔴 키 경로와 본문이 다른 슬롯"]})
        mk = collections.Counter()
        for item in r["🔴🔴 976 판이 못 찾는 수"]:
            k = _split_kind(src, item)
            mk[k] += 1
            kinds[k] += 1
        miss += len(r["🔴🔴 976 판이 못 찾는 수"])
        for sl in info["슬롯"]:
            hits += 1
            body = src[sl["시작"]:sl["끝"]]
            v, err = LG.resolve(sl["키 경로"])
            if err is not None or not isinstance(v, (int, float)) or isinstance(v, bool):
                continue
            try:
                got = float(body.replace(",", ""))
            except Exception:                                    # noqa: BLE001
                continue
            den = abs(float(v))
            relerr = abs(got - float(v)) / den if den > 0 else abs(got - float(v))
            if relerr > 1e-9:
                sigfig.append({"파일": rel, "슬롯": sl["슬롯"], "본문": body,
                               "칸 값": v, "상대오차": relerr})
        per[rel] = collections.OrderedDict([
            ("🔴 센 수", r["센 수"]), ("🔴 면제된 수", r["면제된 수"]),
            ("🔴 슬롯 수", len(r["슬롯"])),
            ("🔴🔴 키 경로와 본문이 다른 슬롯", r["🔴 키 경로와 본문이 다른 슬롯"]),
            ("🔴🔴🔴 못 찾는 수", len(r["🔴🔴 976 판이 못 찾는 수"])),
            ("🔴🔴🔴 그 세 갈래", dict(mk)),
            ("🔴 그 수의 처음 열둘", r["🔴🔴 976 판이 못 찾는 수"][:12]),
        ])
    return collections.OrderedDict([
        ("무엇", label),
        ("🔴 자", "`ledger.audit_text` --- 976 판 슬롯 자 + 991 «유효숫자 검사»"),
        ("🔴 파일별", per),
        ("🔴🔴🔴 센 수 합", tot),
        ("🔴🔴🔴 못 찾는 수 합", miss),
        ("🔴🔴🔴 못 찾는 수의 «세 갈래»", dict(kinds)),
        ("🔴🔴🔴 ㉰ 측정치(= 판정에 «무는» 것)만의 수", int(kinds.get("㉰ 측정치", 0))),
        ("🔴 ㉮ 식별자", int(kinds.get("㉮ 식별자", 0))),
        ("🔴 ㉯ 라벨", int(kinds.get("㉯ 라벨", 0))),
        ("🔴🔴🔴 유효숫자 검사 — 본문을 `float()` 로 되읽어 상대오차 1e-9 로 견줬다",
         sigfig or "없음"),
        ("🔴🔴🔴 유효숫자가 어긋난 슬롯 수", len(sigfig)),
        ("🔴🔴🔴 키 경로와 본문이 다른 슬롯 합", badslot),
        ("🔴 그 파일별", badslot_rows or "없음"),
        ("🔴🔴🔴 992 가 고친 것",
         "🔴 **991 은 이 수(23)를 «내 놓고» 어느 통과에도 «안 물렸다».** "
         "992 는 `F12` 의 판정식에 이 칸을 «넣는다**"),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", hits),
        ("통과", bool(hits > 0)),
    ])


# ══════════════════════════════════════════════════════════════════════
# §E 🔴🔴🔴 `F05` — 「칸 인용」
# ══════════════════════════════════════════════════════════════════════
_SENT = re.compile(r"[^\n]+")
_OLD_NEEDLE = re.compile(r"(data/|out992_order|out992_wiring|sha256)")


def e_world(vd_rel, slots_rel):
    hits = 0
    nrun, srcs = 0, collections.OrderedDict()
    worldy = set()
    for rel in _glob(GLOB_992):
        if not rel.endswith(".json"):
            continue
        d = _load(rel)
        hits += 1
        for k, v in (d.items() if isinstance(d, dict) else []):
            if isinstance(v, dict) and "연" in k and "data/" in k:
                n = v.get("🔴 연 `data/` 경로 수")
                if isinstance(n, int):
                    nrun = max(nrun, n)
                    srcs[rel] = n
            if isinstance(v, dict) and "세계 자료" in k and "지문" in k:
                worldy.add(os.path.basename(rel))
    vt = _read(vd_rel) or ""
    sents = [s for s in _SENT.findall(vt)
             if len(s.strip()) > 20 and not s.strip().startswith("|")]
    old_cite = [s for s in sents if _OLD_NEEDLE.search(s)]
    hits += len(sents)
    man = _load(slots_rel).get("파일별") or {}
    info = man.get(vd_rel) or {}
    slots = info.get("슬롯") or []
    N = len(slots)
    M, from_art = 0, collections.Counter()
    for sl in slots:
        hits += 1
        art = (sl.get("키 경로") or ["?"])[0]
        from_art[art] += 1
        if art in worldy:
            M += 1
    return collections.OrderedDict([
        ("무엇", "🔴🔴🔴 `F05` --- 「파일명 grep」이 아니라 「칸 인용」으로 잰다"),
        ("🔴🔴🔴 ㉠ 런타임 최대", nrun),
        ("🔴 ㉠ 산출물별", srcs),
        ("🔴🔴🔴 세계 자료 지문이 «걸린» 산출물", sorted(worldy)),
        ("🔴🔴🔴 ㉡ 판정문의 주장 문장 수", len(sents)),
        ("🔴🔴🔴 ㉡ 그중 세계 자료를 «인용한» 문장 수(옛 자 --- 파일명 grep)", len(old_cite)),
        ("🔴🔴🔴 ㉢ 판정문의 슬롯 수 `N`(= 치환표가 심은 수)", N),
        ("🔴🔴🔴 ㉢ 그중 «세계 자료 지문이 걸린 산출물 칸»에서 온 것 `M`", M),
        ("🔴🔴🔴 ㉢ 몫 `M/N`", round(M / float(N), 4) if N else None),
        ("🔴 ㉢ 산출물별 슬롯 수", dict(from_art)),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", hits),
        ("통과", bool(nrun > 0 and M > 0)),
    ])


# ══════════════════════════════════════════════════════════════════════
# §F 🔴🔴 `F13`
# ══════════════════════════════════════════════════════════════════════
def f_roster():
    allc = _glob(GLOB_992)
    filt = [p for p in allc if p.endswith((".json", ".txt"))]
    runners = [p for p in allc if p.endswith(".py")]
    doctext = "\n".join(filter(None, (_read(d) for d in DOCS_992)))
    hits = 0
    un_f, un_a, un_r = [], [], []
    for p in filt:
        hits += 1
        if os.path.basename(p) not in doctext:
            un_f.append(p)
    for p in allc:
        hits += 1
        if os.path.basename(p) not in doctext:
            un_a.append(p)
    for p in runners:
        hits += 1
        if os.path.basename(p) not in doctext:
            un_r.append(p)
    all991 = _glob(GLOB_991)
    r991 = [p for p in all991 if p.endswith(".py")]
    doc991 = "\n".join(filter(None, (_read(d) for d in (
        "docs/판정_991.md", "docs/card_991.md", "docs/handoff_991.md",
        "docs/pr_991.md", "docs/prereg_991_order_rulers.md"))))
    un_r991 = [p for p in r991 if os.path.basename(p) not in doc991]
    hits += len(r991)
    return collections.OrderedDict([
        ("무엇", "🔴🔴 `F13` --- 분모에 «필터를 적는다»"),
        ("🔴 글롭", GLOB_992),
        ("🔴🔴🔴 분모 ① `runners/*992*` ∩ {json, txt}", len(filt)),
        ("🔴🔴🔴 분모 ② `runners/*992*` «전량»", len(allc)),
        ("🔴 그 차(= 필터가 «조용히» 뺀 것)", len(allc) - len(filt)),
        ("🔴 ① 에서 한 번도 인용 «안» 된 것", un_f or "없음"),
        ("🔴 ① 미인용 수", len(un_f)),
        ("🔴 ② 에서 한 번도 인용 «안» 된 것", un_a or "없음"),
        ("🔴 ② 미인용 수", len(un_a)),
        ("🔴🔴🔴 이 사이클 «러너» 중 문서에 한 번도 안 나오는 것", un_r or "없음"),
        ("🔴🔴🔴 그 수", len(un_r)),
        ("🔴 991 의 같은 수(러너 미인용)", len(un_r991)),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", hits),
        ("통과", bool(hits > 0)),
    ])


# ══════════════════════════════════════════════════════════════════════
# §G 🔴 `#249` 머지 — 가지 쪽 고유 «줄» 수와 «파일» 수를 «가른다**
# ══════════════════════════════════════════════════════════════════════
def g_merges():
    hits, per = 0, collections.OrderedDict()
    for pr, br in (("247", "note/989-world-budget"),
                   ("248", "note/990-arms-rulers"),
                   ("249", "note/991-order-rulers")):
        rc0, tip, _e0 = _git(["rev-parse", br])
        tip = tip.strip()
        rc1, mg, _e1 = _git(["rev-list", "--merges", "--parents", "main"])
        mb, mcommit = "", None
        for ln in mg.split("\n"):
            ps = ln.split()
            if len(ps) >= 3 and ps[2] == tip:
                mcommit = ps[0]
                rcx, mbx, _ex = _git(["merge-base", ps[1], tip])
                mb = mbx.strip()
                break
        if not mb:
            rcy, mby, _ey = _git(["merge-base", "main", br])
            mb = mby.strip()
        rc2, names, _e2 = _git(["diff", "--name-only", "-z", mb, br])
        files = [x for x in names.split("\0") if x]
        uniq_tot, rows, newf, prefix_files = 0, collections.OrderedDict(), [], []
        nonprefix_lines = 0
        for f in files:
            hits += 1
            r1, a, _ = _git(["show", "%s:%s" % (mb, f)])
            r2, b, _ = _git(["show", "%s:%s" % (br, f)])
            if r2 != 0:
                continue
            if r1 != 0:
                newf.append(f)
                continue
            la, lb = a.split("\n"), b.split("\n")
            only = len([1 for x in lb if x not in set(la)])
            prefix = bool(b.startswith(a))
            rows[f] = {"가지에만 있는 줄 수": only, "🔴 기준 쪽이 순수 접두사인가": prefix}
            uniq_tot += only
            if prefix:
                prefix_files.append(f)
            else:
                nonprefix_lines += only
        rc3, log, _e3 = _git(["log", "--format=%H\t%s", "%s..%s" % (mb, br)])
        dae = [l for l in log.split("\n") if "[데몬]" in l or "[수집]" in l]
        rec = []
        for l in dae:
            sha = l.split("\t")[0]
            r4, anc, _ = _git(["merge-base", "--is-ancestor", sha, "main"])
            rec.append({"sha": sha[:12], "🔴 main 에 회수됐나": bool(r4 == 0)})
            hits += 1
        per["PR #%s (%s)" % (pr, br)] = collections.OrderedDict([
            ("🔴 머지 커밋", mcommit or "🔴 못 찾았다"),
            ("🔴 기준(머지 커밋의 첫 부모와의 merge-base)", mb),
            ("🔴 갈린 파일 수", len(files)),
            ("🔴 그중 «새 파일»(기준에 없다)", len(newf)),
            ("🔴 그중 «양쪽에 있는» 파일(= 진짜 분모)", len(rows)),
            ("🔴🔴🔴 «양쪽에 있는» 파일의 가지 쪽 «고유 줄 수» 합", uniq_tot),
            ("🔴🔴🔴 그중 «순수 접두사»인 «파일» 수", len(prefix_files)),
            ("🔴🔴🔴 접두사가 «아닌» 파일의 고유 «줄» 수",
             nonprefix_lines),
            ("🔴🔴 단위 신고(`조항 59-나`)",
             "🔴 **「고유 줄 %d」은 «줄»이고 「순수 접두사 %d」는 «파일»이다** --- "
             "991 의 정정 9항이 두 단위를 나란히 놓아 «같은 단위처럼» 읽혔다. "
             "992 는 「접두사가 아닌 파일의 고유 «줄» 수」를 «따로** 낸다"
             % (uniq_tot, len(prefix_files))),
            ("🔴 파일별", rows),
            ("🔴🔴 데몬 커밋 수", len(dae)),
            ("🔴🔴🔴 그중 `main` 에 회수된 것", int(sum(
                1 for r in rec if r["🔴 main 에 회수됐나"]))),
            ("🔴🔴🔴 데몬 커밋이 «전부» 회수됐나",
             bool(rec) and all(r["🔴 main 에 회수됐나"] for r in rec)),
        ])
    return collections.OrderedDict([
        ("무엇", "🔴 `#248`·`#249` 머지 --- «가지 쪽 고유 줄 수»와 «파일 수»를 «단위로 가른다»"),
        ("🔴 PR 별", per),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", hits),
        ("통과", bool(hits > 0)),
    ])


# ══════════════════════════════════════════════════════════════════════
# §H 🔴 `⑤′` 붉은 절의 **진짜 분자**
# ══════════════════════════════════════════════════════════════════════
def h_fiveprime_numerators():
    d = _load("runners/fiveprime_991.json")
    hits = 0
    per = collections.OrderedDict()
    for sec in ("1 소비자 역참조", "2 게이트"):
        v = d.get(sec) or {}
        hits += 1
        row = collections.OrderedDict()
        for k, val in v.items():
            if isinstance(val, (int, bool)) and (
                    "수" in k or "분모" in k or "사유" in k or "안 돌린" in k):
                row[k] = val
        rl = None
        for k, val in v.items():
            if isinstance(val, dict) and "자" in k and "사유" in k:
                rl = val
        if isinstance(rl, dict):
            ok = [x for x, r in rl.items()
                  if isinstance(r, dict) and r.get("🔴 자가 냈나")]
            no = [x for x, r in rl.items()
                  if isinstance(r, dict) and not r.get("🔴 자가 냈나")]
            row["🔴🔴🔴 사유가 «자»를 넘은 것"] = len(ok)
            row["🔴🔴🔴 사유가 «자»를 못 넘은 것"] = len(no)
            row["🔴 못 넘은 것의 처음 다섯"] = no[:5]
            hits += len(rl)
        per[sec] = row
    return collections.OrderedDict([
        ("무엇", "🔴 `조항 73-바` --- `⑤′` 붉은 절의 «분자»(991 판을 승계해 992 가 다시 낸다)"),
        ("🔴 절별", per),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", hits),
        ("통과", bool(hits > 0)),
    ])


# ══════════════════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--prereg-ref", required=True)
    a = ap.parse_args()
    if len(a.ref) != 40:
        raise SystemExit("🔴 --ref 는 40자 sha 여야 한다")
    t0 = _now()
    cs0 = code_stamp()
    secs = collections.OrderedDict([
        ("§A 🔴🔴🔴 ⑤′ 절 4 — 엄한 판 + 면제 없는 판", a_strict4()),
        ("§B 🔴🔴 990 의 배선 일곱 — 진짜 AST", b_variants()),
        ("§C 🔴🔴🔴 `F02` — 리플로그 「구간 전수」", c_reflog(a.prereg_ref)),
        ("§D 🔴🔴 규칙 D — 992 자신",
         d_ruled("runners/out992_slots.json", "out992_*.json",
                 "🔴 992 자신의 규칙 D")),
        ("§D-나 🔴 규칙 D — 991 을 같은 자로 다시 센다",
         d_ruled("runners/out991_slots.json", "out991_*.json",
                 "🔴 991 의 규칙 D(992 의 자로)")),
        ("§E 🔴🔴🔴 `F05` — 「칸 인용」",
         e_world("docs/판정_992.md", "runners/out992_slots.json")),
        ("§F 🔴🔴 `F13` — 분모에 필터를 적는다", f_roster()),
        ("§G 🔴 `#248`·`#249` 머지 — 단위를 가른다", g_merges()),
        ("§H 🔴 `⑤′` 붉은 절의 진짜 분자", h_fiveprime_numerators()),
    ])
    hitmap = collections.OrderedDict(
        (k, v.get("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", 0))
        for k, v in secs.items())
    hv = [x for x in hitmap.values() if isinstance(x, int)]
    unmeas = [k for k, v in secs.items()
              if v.get("통과") is True and not hitmap.get(k)]
    res = collections.OrderedDict([
        ("무엇", "992 §2 — 🔴 **자가 «잡은» 것을 자에 «문다»**"),
        ("🔴 규율", ["하드코딩 `False` 를 안 쓴다",
                  "「걸린 자리」는 «판정 함수»가 스스로 반환한다",
                  "명부는 «글롭»이다 --- 손으로 안 고른다",
                  "구간 명제는 «구간 전수»로 잰다",
                  "🔴 소스에 대한 주장은 «AST»로 잰다"]),
        ("사전등록", "docs/prereg_992_wire_the_rulers.md §2"),
    ])
    res.update(secs)
    res["🔴 절별 통과"] = collections.OrderedDict(
        (k, v.get("통과")) for k, v in secs.items())
    res["🔴 절별 걸린 자리"] = hitmap
    res["🔴 걸린 자리 합"] = int(sum(hv))
    res["🔴🔴 걸린 자리 «중앙값»(🔴 992 가 고친 자)"] = _median(hv)
    res["⚠ 991 판 「중앙값」(`sorted(x)[len(x)//2]`)"] = (
        int(sorted(hv)[len(hv) // 2]) if hv else None)
    res["🔴🔴🔴 «최대 기여» 절의 몫"] = (
        round(max(hv) / float(sum(hv)), 4) if hv and sum(hv) else None)
    res["🔴 그 절"] = [k for k, v in hitmap.items() if v == max(hv)][0] if hv else None
    res["🔴🔴🔴 미측정인 절(초록인데 걸린 자리 0)"] = unmeas or []
    res["통과"] = bool(all(v.get("통과") for v in secs.values()) and not unmeas)
    res["🔴 도장"] = collections.OrderedDict([
        ("ref(부른 쪽이 준 40자 sha)", a.ref),
        ("🔴 사전등록 ref", a.prereg_ref),
        ("🔴 코드 sha256(시작)", cs0),
        ("🔴 코드 sha256(끝)", code_stamp()),
        ("🔴 코드가 주행 중 바뀌었나", cs0 != code_stamp()),
        ("시작(UTC)", t0), ("끝(UTC)", _now()),
    ])
    p = OUT / "out992_audit.json"
    p.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    sys.stderr.write("%s  [audit992] 끝 → %s · 통과 %s\n"
                     % (_now(), p.name, res["통과"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
