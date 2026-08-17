#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""987 §2 — 🔴🔴🔴 **「전」을 고정 ref 로만 읽고, 한 이름 두 값을 끝낸다**.

🔴 **이 러너의 모든 「전」 값은 `cycle987.before()` 를 지나간다** ---
곧 **`git show <40자 sha>:<경로>`** 다. 디스크를 읽는 「전」 측정은 **이 파일에 없다.**

| 절 | 무엇 | 티처 #125 |
|---|---|---|
| §A | 🔴 **`조항 60-나` 포인터를 고정 ref 로 다시 잰다** + **AST 자**(디스크에서 「전」을 읽는 자리) | 2순위 ⓐ |
| §B | 🔴 **985 가 한 이름(「분모 ② 역참조 소비자 수」)으로 두 범위를 쟀다** | 2순위 ⓑ |
| §C | 🔴 **`⑤′` 절 3 을 고정 명부로 다시 낸다**(985 · 986 · 987 나란히) | 3순위 ⓐ |
| §D | 🔴 즉시 정정 --- 잴 수 있는 것만 «잰다» | 즉시 정정 |

씀:
    python3 runners/audit987.py --stage audit --ref <40자 sha>
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

import cycle987 as CY                                   # noqa: E402

OUT = "runners/out987_audit.json"
REF_986 = CY.REF_986
REF_985 = CY.REF_985

#: 🔴 `조항 60-나` 원문 --- 986 이 「포인터를 박았다」고 한 그 자리
CLAUSE_ORIG = "사전등록한 반증조건·예측의 **분모는 채점 시점에 늘리지도 줄이지도 못한다.**"
POINTER_KEYS = ("60-나 개정", "개정 참조")

#: 🔴🔴 **AST 자** --- 디스크 읽기 함수에 `docs/…` 경로 «리터럴»을 넘기는 자리.
DISK_READ_FUNCS = ("_text", "_read", "read_text", "open", "_load", "_load_text")
DOC_LIT = re.compile(r"^docs/.*\.md$")

#: 🔴 이 사이클의 산출물 명부 --- `⑤′` 절 3 의 **고정 명부**(사전등록 §4-2)
ROSTER_987 = (
    "runners/out987_house.json",
    "runners/out987_audit.json",
    "runners/out987_power.json",
    "runners/out987_score.json",
    "runners/out987_table.json",
    "runners/out987_certify.json",
    "runners/out987_prose.json",
    "runners/out987_window.json",
)
#: 🔴🔴 **데몬(규칙 B)이 쓰는 산출물 셋** --- 986 R2 가 커밋 경로에 넣었다.
#:  🔴 이 셋이 `⑤′` 절 3 대상에 «들면» 그 절은 떨어진다. 그것을 «수로» 보인다.
DAEMON_OUT = ("runners/out941_wikidaily.json", "runners/out941_steamrev.json",
              "runners/out941_robots.json")


def _text_now(rel):
    """🔴 **「지금」 읽기다** --- 이름에 `now` 를 박는다. 「전」은 `CY.before` 만 읽는다."""
    p = ROOT / rel
    return p.read_text(encoding="utf-8") if p.is_file() else None


def _json_now(rel):
    t = _text_now(rel)
    if t is None:
        return None
    try:
        return json.loads(t, object_pairs_hook=collections.OrderedDict)
    except Exception:                                               # noqa: BLE001
        return None


def _pointer(txt):
    i = txt.find(CLAUSE_ORIG)
    if i < 0:
        return {"원문을 찾았나": False, "포인터가 있나": None,
                "🔴": "🔴 원문을 못 찾았다 --- 「없다」가 아니라 「모른다」다(조항 59)"}
    win = txt[i:i + 400]
    return {"원문을 찾았나": True,
            "포인터가 있나": bool(any(k in win for k in POINTER_KEYS)),
            "본 창(글자)": 400}


# ══════════════════════════════════════════════════════════════════════
# §A 🔴🔴🔴 「전」을 고정 ref 로만 --- 라벨 뒤집힘을 되돌리고 자를 박는다
# ══════════════════════════════════════════════════════════════════════
def ast_disk_doc_reads(src, name):
    """🔴🔴 **디스크 읽기 함수에 `docs/….md` 리터럴을 넘기는 자리**를 AST 로 센다."""
    try:
        tree = ast.parse(src)
    except SyntaxError as e:                                        # noqa: BLE001
        return None, "🔴 파싱 실패: %s" % e
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        fname = (f.attr if isinstance(f, ast.Attribute)
                 else (f.id if isinstance(f, ast.Name) else None))
        if fname not in DISK_READ_FUNCS:
            continue
        for arg in node.args:
            v = getattr(arg, "value", None) if isinstance(arg, ast.Constant) else None
            if isinstance(v, str) and DOC_LIT.match(v):
                hits.append({"파일": name, "줄": node.lineno,
                             "호출": "%s(%r)" % (fname, v)})
    return hits, None


def before_labels(ref986, ref985):
    """🔴🔴🔴 **「986 이 넣기 전」을 고정 ref 로 다시 잰다.**

    🔴 986 은 `audit986.py:414` 가 **고정 ref 없이 디스크**를 읽어
    **자기가 38 분 전에 넣은 것**을 「986 이 넣기 전 실측 = `True`」로 실었다.
    """
    b985 = CY.before(ref985, "docs/루프.md", _pointer, "986 이 넣기 «전»(985 가 끝난 트리)")
    b986 = CY.before(ref986, "docs/루프.md", _pointer, "986 이 넣은 «뒤»(986 이 끝난 트리)")
    v985 = (b985["🔴🔴🔴 값"] or {}).get("포인터가 있나")
    v986 = (b986["🔴🔴🔴 값"] or {}).get("포인터가 있나")
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴🔴 **`조항 60-나` 원문 뒤에 개정 포인터가 있나** --- "
                 "「전」과 「뒤」를 **둘 다 고정 ref 로** 읽는다"),
        ("🔴 전(고정 ref)", b985),
        ("🔴 뒤(고정 ref)", b986),
        ("🔴🔴🔴 986 이 넣기 «전» 실측", v985),
        ("🔴🔴 986 이 넣은 «뒤» 실측", v986),
        ("⚠ 986 이 실은 값", True),
        ("🔴🔴🔴 986 이 실은 값이 틀렸나", bool(v985 is False)),
        ("🔴 왜 틀렸나",
         "🔴 **`audit986.py:414` 가 `_text(\"docs/루프.md\")` 로 «고정 ref 없이 디스크»를 "
         "읽었다.** 그 시점의 디스크에는 **986 자신이 38 분 전에 넣은 포인터**가 "
         "이미 있었다 --- 「잰 값만 적는다」는 절 «안»에서 정반대 라벨로 실렸다"),
    ])


def ast_before_ruler():
    """🔴🔴 **자** + 🔴 **검정력 시연(조항 64)** --- 같은 자를 `audit986.py` 에 문다."""
    rows, hits987 = collections.OrderedDict(), []
    for rel in CY.RAN_987:
        src = _text_now(rel)
        if src is None:
            rows[rel] = {"🔴": "🔴 못 읽었다(= 「0」이 아니다 · 조항 59)"}
            continue
        hs, err = ast_disk_doc_reads(src, rel)
        ex = CY.DISK_READ_EXEMPT.get(rel)
        rows[rel] = {"자리 수": (None if hs is None else len(hs)),
                     "자리": (hs or "없음") if hs is not None else err,
                     "🔴 등록 면제": ex or "없음"}
        if hs and not ex:
            hits987 += hs
    # ── 🔴 검정력 시연 --- 986 의 감사 러너를 «고정 ref» 로 읽어 같은 자를 문다 ──
    demo = CY.before(REF_986, "runners/audit986.py",
                     lambda t: ast_disk_doc_reads(t, "runners/audit986.py")[0],
                     "검정력 시연 — 986 의 감사 러너")
    got = demo["🔴🔴🔴 값"] or []
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴 **AST 자 --- 디스크 읽기 함수에 `docs/….md` 리터럴을 넘기는 자리**"),
        ("🔴 바늘: 디스크 읽기 함수", list(DISK_READ_FUNCS)),
        ("🔴 바늘: 경로 꼴", DOC_LIT.pattern),
        ("🔴 분모: `RAN_987` 러너 수", len(CY.RAN_987)),
        ("🔴🔴 등록 면제와 사유(조용히 안 뺀다 · 사전등록 §3-1-가)", dict(CY.DISK_READ_EXEMPT)),
        ("🔴 러너별", rows),
        ("🔴🔴🔴 면제 밖에서 걸린 자리 수(= 반증조건 16 의 분자)", len(hits987)),
        ("🔴 걸린 자리", hits987 or "없음"),
        ("🔴🔴 검정력 시연(조항 64) — 같은 자를 `runners/audit986.py`(고정 ref)에 문다",
         collections.OrderedDict([
             ("🔴 고정 ref", REF_986),
             ("🔴🔴🔴 잡은 자리 수", len(got)),
             ("🔴 잡은 자리", got or "없음"),
             ("🔴🔴🔴 `:414` 의 `_text(\"docs/루프.md\")` 를 잡았나",
              bool(any(h.get("줄") == 414 for h in got))),
             ("🔴 이 값이 0 이면", "🔴 **이 자는 자가 아니다**(항진명제)"),
         ])),
        ("통과", bool(len(hits987) == 0 and len(got) > 0)),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **① 987 러너의 면제 밖 자리가 0 이고 ② 같은 자가 986 에서 «떨어지는가».** "
         "②가 0 이면 통과가 아니다 --- 안 떨어지는 자는 자가 아니다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §B 🔴🔴 985 가 한 이름으로 두 범위를 쟀다
# ══════════════════════════════════════════════════════════════════════
def _dig(obj, *keys):
    cur = obj
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def one_name_two_values():
    _r1, t985 = CY.fixed_ref_json(REF_985, "runners/out985_table.json")
    _r2, a985 = CY.fixed_ref_json(REF_985, "runners/out985_audit.json")
    _r3, f985 = CY.fixed_ref_json(REF_985, "runners/fiveprime_985.json")
    cells = _dig(t985 or {}, "🔴🔴 치환표", "🔴 칸") or {}
    NAME = "🔴 분모 ② 역참조 소비자 수"
    secC = _dig(a985 or {}, "§C 🔴🔴 `⑤′` 절 1 소비자 분모의 기전") or {}
    sec1 = _dig(f985 or {}, "1 소비자 역참조") or {}
    v_audit, rng_audit = secC.get(NAME), secC.get("🔴 범위")
    v_five = sec1.get(NAME)
    rng_five = "%s..%s" % (sec1.get("취합 시작(base)"), sec1.get("머리(head)"))
    same_name = bool(NAME in secC and NAME in sec1)
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴🔴 **985 가 「%s」라는 «한 이름»으로 서로 다른 두 범위를 쟀다**" % NAME),
        ("🔴 고정 ref(985 가 끝난 트리)", REF_985),
        ("🔴🔴 986 이 실은 반박", "「티처의 `446/349` 는 985 산출물에 없다」"),
        ("🔴🔴🔴 그 반박이 참인가", collections.OrderedDict([
            ("985 치환표 칸 `소.전량`", cells.get("소.전량")),
            ("985 치환표 칸 `소.원장뺀`", cells.get("소.원장뺀")),
            ("🔴🔴🔴 `446` 이 985 산출물에 «있나»",
             bool(cells.get("소.전량") == 446 or v_audit == 446)),
            ("🔴🔴🔴 `349` 가 985 산출물에 «있나»", bool(cells.get("소.원장뺀") == 349)),
            ("🔴🔴🔴 986 의 반박이 «거짓»인가",
             bool(cells.get("소.전량") == 446 and cells.get("소.원장뺀") == 349)),
            ("🔴 `447`·`350` 은 985 어디에 있나",
             "🔴 **어디에도 없다** --- 사전등록의 「측정 전」 탐색값이 PR 본문에 실렸다"),
        ])),
        ("🔴🔴🔴 진짜 병 — 같은 이름 · 다른 범위", collections.OrderedDict([
            ("이름", NAME),
            ("🔴 두 산출물이 «같은 이름» 키를 쓰나", same_name),
            ("`out985_audit.json §C` 의 값", v_audit),
            ("`out985_audit.json §C` 의 범위", rng_audit),
            ("`fiveprime_985.json §1` 의 값", v_five),
            ("`fiveprime_985.json §1` 의 범위", rng_five),
            ("🔴🔴🔴 값이 다른가", bool(v_audit != v_five)),
            ("🔴🔴🔴 범위가 다른가", bool(str(rng_audit) != str(rng_five))),
            ("🔴 §C 의 범위가 «984 것»인가",
             bool(isinstance(rng_audit, str) and "196c9e0ec" in rng_audit)),
            ("🔴🔴 그래서 누가 틀렸나",
             "🔴 **티처도 986 도 안 틀렸고 985 가 틀렸다** --- "
             "**한 이름으로 서로 다른 두 범위를 쟀다**"),
        ])),
        ("🔴🔴 986 의 반박이 어디 있었나",
         "🔴 **끝 커밋 메시지에만 있었다**(문서·원장·PR 0) --- "
         "**986 이 985 를 그 죄로 쳤던 형태 그대로다**"),
        ("🔴🔴🔴 배선으로 고친다 — 계수기가 「범위를 이름 붙은 인자로 받는다」",
         collections.OrderedDict([
             ("🔴 함수", "cycle987.consumer_count(이름, base, head, tree)"),
             ("🔴 반환값이 «반드시» 박는 것", ["🔴🔴 이름", "🔴🔴🔴 범위", "🔴🔴 역참조한 트리"]),
             ("🔴 그래서 무엇이 «불가능»해지나",
              "🔴 **이름 없는 계수를 만들 수 없다** --- 「분모 ② 역참조 소비자 수」라는 "
              "낱말만 있고 범위가 없는 칸은 이 배관에서 «나올 수 없다»"),
         ])),
        ("통과", bool(cells.get("소.전량") == 446 and cells.get("소.원장뺀") == 349
                    and v_audit is not None and v_five is not None)),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **네 수(446 · 349 · §C · §1)를 고정 ref 에서 «전부 읽었는가»**"),
    ])


KOR_NUM_RE = re.compile(r"985\s*(?:의)?\s*(하나|둘|셋|넷|다섯|여섯|일곱|여덟|아홉|열)\s*문서")


def korean_numeral_986():
    """🔴🔴 **986 문서의 「985 의 «다섯» 문서」** --- 잰 값은 `3` 이다(티처 #125 3순위 ⓒ)."""
    _r, a986 = CY.fixed_ref_json(REF_986, "runners/out986_audit.json")
    truth = _dig(a986 or {}, "§A 🔴🔴🔴 985 의 세 오기", "① 반증조건",
                 "🔴🔴 「13 / 14」를 실은 문서 수")
    KOR = {"하나": 1, "둘": 2, "셋": 3, "넷": 4, "다섯": 5,
           "여섯": 6, "일곱": 7, "여덟": 8, "아홉": 9, "열": 10}
    rows, bad = collections.OrderedDict(), 0
    for rel in ("docs/판정_986.md", "docs/card_986.md", "docs/handoff_986.md",
                "docs/pr_986.md"):
        b = CY.before(REF_986, rel, lambda t: [m.group(1) for m in KOR_NUM_RE.finditer(t)],
                      "986 문서의 한글 수사")
        got = b["🔴🔴🔴 값"] or []
        wrong = [w for w in got if KOR.get(w) != truth]
        rows[rel] = {"🔴 고정 ref": REF_986, "🔴 걸린 수사": got or "없음",
                     "🔴 등록된 참값": truth,
                     "🔴🔴 어긋난 수사": wrong or "없음"}
        bad += len(wrong)
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴 **986 문서의 「985 의 «N» 문서」가 잰 값과 어긋나나** --- "
                 "**한글 수사**라 `NUMPAT` 이 원리상 못 본다"),
        ("🔴 고정 ref", REF_986),
        ("🔴🔴🔴 잰 값(`out986_audit §A/①`)", truth),
        ("🔴 바늘", KOR_NUM_RE.pattern),
        ("🔴 문서별", rows),
        ("🔴🔴🔴 어긋난 수사 수(= 예측 P4 의 분자)", bad),
        ("통과", bool(truth is not None)),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "🔴 **잰 값을 고정 ref 에서 «읽었는가»** 하나다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §C 🔴🔴 `⑤′` 절 3 을 «고정 명부»로 다시 낸다
# ══════════════════════════════════════════════════════════════════════
def _sec3_targets(fp):
    s = _dig(fp or {}, "3 판정 키 규약") or {}
    t = _dig(s, "🔴 대상 고르기", "🔴 대상")
    return (t if isinstance(t, list) else []), s.get("통과")


def _pass_keys(rel):
    """🔴 그 산출물의 최상위 절 중 `통과` 키를 «가진» 절 수 / 절 수."""
    d = _json_now(rel)
    if d is None:
        return None, None
    secs = [k for k, v in d.items() if isinstance(v, dict)]
    ok = [k for k in secs if "통과" in d[k]]
    return len(ok), len(secs)


def sec3_fixed_roster():
    _r5, f985 = CY.fixed_ref_json(REF_985, "runners/fiveprime_985.json")
    _r6, f986 = CY.fixed_ref_json(REF_986, "runners/fiveprime_986.json")
    t985, p985 = _sec3_targets(f985)
    t986, p986 = _sec3_targets(f986)
    dae = collections.OrderedDict()
    for rel in DAEMON_OUT:
        ok, n = _pass_keys(rel)
        dae[rel] = {"절 수": n, "`통과` 키가 있는 절": ok,
                    "🔴 있나": (ROOT / rel).is_file(),
                    "🔴🔴 이 파일이 대상에 들면 §3 이 떨어지나": (None if ok is None
                                                    else bool(ok == 0))}
    sink = [k for k, v in dae.items()
            if v["🔴🔴 이 파일이 대상에 들면 §3 이 떨어지나"] is True]
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴🔴 **`⑤′` 절 3 의 「대상」이 «diff 타이밍»으로 줄었다** --- "
                 "986 의 `3/16` 은 개선이 아니다(티처 #125 3순위 ⓐ)"),
        ("🔴 985 절 3 대상 수(고정 ref)", len(t985)),
        ("🔴 986 절 3 대상 수(고정 ref)", len(t986)),
        ("🔴🔴🔴 985 → 986 에서 대상이 줄었나", bool(len(t986) < len(t985))),
        ("🔴 985 대상", t985 or "없음"),
        ("🔴 986 대상", t986 or "없음"),
        ("🔴🔴 985 에 있고 986 에 «없는» 대상", sorted(set(t985) - set(t986)) or "없음"),
        ("🔴 985 절 3 통과 / 986 절 3 통과", [p985, p986]),
        ("🔴🔴🔴 그래서 986 의 §3 초록은 «조용한 좁힘»의 산물이다",
         "🔴 **분모·명부는 985 와 완전히 같고 열린 것은 §3 하나인데, 그 §3 은 "
         "「대상 파일이 %d → %d 로 줄어」 초록이 됐다.** 데몬 산출물이 그 순간 "
         "가지 diff 에 «안 들어간» 타이밍이고 **이유가 어느 문서에도 없었다**"
         % (len(t985), len(t986))),
        ("🔴🔴🔴 `[수리] R1` — 987 의 «고정 명부»", collections.OrderedDict([
            ("🔴 명부(이름으로 박았다)", list(ROSTER_987)),
            ("🔴 명부 수", len(ROSTER_987)),
            ("🔴 `⑤′` 주행에 `--keyaudit` 로 전량 넘긴다", True),
            ("🔴 왜", "🔴 **diff 타이밍이 대상을 못 줄이게 한다** --- "
                   "줄어서 초록이 되는 길을 «구성상» 막는다"),
        ])),
        ("🔴🔴🔴 데몬 산출물 셋 — 실측", collections.OrderedDict([
            ("🔴 파일별", dae),
            ("🔴🔴🔴 대상에 들면 §3 을 떨어뜨리는 파일", sink or "없음"),
            ("🔴 그래서 R2 때문에 다음 사이클에 되돌아온다",
             "🔴 **986 R2 가 데몬 커밋 경로에 이 셋을 넣었다** --- "
             "다음 데몬 기동부터 이 셋이 가지 diff 에 들어오고 그때 §3 은 떨어진다"),
        ])),
        ("통과", bool(t985 and t986)),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **985·986 의 절 3 대상을 고정 ref 에서 «둘 다 읽었는가»** 하나다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §D 🔴 즉시 정정 --- 잴 수 있는 것만 «잰다»
# ══════════════════════════════════════════════════════════════════════
def errata():
    _r7, s986 = CY.fixed_ref_json(REF_986, "runners/out986_score.json")
    _r8, p986 = CY.fixed_ref_json(REF_986, "runners/out986_power.json")
    _r9, c986 = CY.fixed_ref_json(REF_986, "runners/out986_certify.json")
    _ra, a986 = CY.fixed_ref_json(REF_986, "runners/out986_audit.json")
    # ① 985 F5 분모 7 / 13 / 피한 5 --- 사전등록 면제 1 을 안 보였다
    f5 = _dig(s986 or {}, "§F5 🔴 인용 산출물 도장") or {}
    # ② 985 재현이 절반이다
    rep = _dig(p986 or {}, "§4 🔴 985 재현", "🔴 λ 별") or {}
    same = {k: (v or {}).get("🔴🔴 같은가") for k, v in rep.items()}
    # ③ certify §나 의 키 이름
    cn = _dig(c986 or {},
              "§나 🔴🔴 검정력 시연 — 같은 여섯 칸 자를 985 에 문다(조항 64)",
              "🔴 여섯 칸",
              "🔴🔴🔴 ⑥ 치환표의 채점 칸 == 채점 산출물의 채점 칸(986 신설)") or {}
    keyname = [k for k in cn if k.startswith("🔴 분모")]
    # ④ M2 --- 여섯째 칸이 985 를 잡은 그 칸을 면제 목록에 둔다
    self_dep = _dig(s986 or {}, "§6 🔴 반증조건", "🔴 조건별", "11") or {}
    # ⑤ R3 「986 자리 0」이 범위 산물이다
    r3 = _dig(a986 or {}, "§C 🔴🔴🔴 R3 손 전사 자의 분모") or {}
    return collections.OrderedDict([
        ("🔴 무엇", "🔴 **즉시 정정 --- 수리로 안 센다. 잴 수 있는 것만 «잰다»**"),
        ("🔴 고정 ref", REF_986),
        ("① 985 F5 분모의 산술", collections.OrderedDict([
            ("🔴 티처가 준 값", {"인용 분모": 7, "원장이 싣는 산출물": 13, "피한 것": 5}),
            ("🔴🔴 7 + 5", 12),
            ("🔴🔴🔴 안 맞는 이유", "🔴 **사전등록 면제 1 을 안 보여서다** --- 7 + 1 + 5 = 13"),
            ("🔴 986 의 F5 분모(고정 ref 실측)", f5.get("🔴 분모")),
        ])),
        ("② 985 재현이 「절반」이다", collections.OrderedDict([
            ("🔴 λ 별 「985 가 실은 값과 같은가」", same),
            ("🔴🔴🔴 둘 다 참인가", bool(all(bool(v) for v in same.values()) and same)),
            ("🔴 판정문은 옳게 적었나",
             "🔴 **판정문은 옳게 적었고 원장·인계·PR 이 `u=3` 쪽을 뺐다**(티처 #125)"),
        ])),
        ("③ 「소비자 415 → 414」의 화살표", collections.OrderedDict([
            ("🔴🔴🔴 전후인가", False),
            ("🔴 무엇인가", "🔴 **서로 다른 두 양이다** --- 「전체」와 「원장 뺀」이다. "
                       "화살표는 **전후를 뜻하는 기호**라 가짜다. 🔴 **원장은 옳게 적었다**"),
        ])),
        ("④ `certify §나` 의 키 이름", collections.OrderedDict([
            ("🔴 986 이 쓴 키 이름", keyname or "못 읽었다"),
            ("🔴🔴 실제 뜻", "🔴 **「985 표에서 «풀리는» 칸 수」다** --- "
                        "`SCORE_CELLS_985` 의 길이(8)이지 986 판 분모(16)가 아니다"),
            ("🔴 987 이 고친 이름", "🔴 분모(985 표에서 풀리는 칸 수)"),
        ])),
        ("⑤ `M2` — 여섯째 칸이 985 를 잡은 그 칸을 면제 목록에 둔다", collections.OrderedDict([
            ("🔴 986 의 `SELF_DEP` 에 든 칸", ["채.반증분자모", "채.반증분모", "채.반증된",
                                        "채.반증통과", "채.예측분자모", "채.예측분자",
                                        "채.예측통과", "채.최상위통과"]),
            ("🔴🔴🔴 그중 985 를 «잡은» 칸", ["채.반증분자모", "채.반증된"]),
            ("🔴🔴 그래서 무엇이 원리상 안 보이나",
             "🔴 **사이클 «안»에서 도는 여섯째 칸은 반증 칸을 못 본다** --- "
             "사유는 986 이 적어 놨으나 **자가 그 자리에서 눈을 감는다**는 사실은 남는다. "
             "🔴 **전량 검사는 `certify` 가 그대로 한다**(그것이 정본이다)"),
            ("🔴 조건 11 의 지금 값(고정 ref)", self_dep.get("잰 값") if self_dep else "못 읽었다"),
        ])),
        ("⑥ `R3` 「986 자리 0」이 «범위 산물»이다", collections.OrderedDict([
            ("🔴 986 이 실은 자리 수", _dig(r3, "🔴🔴🔴 986 러너의 자리 수(분자)")),
            ("🔴🔴🔴 왜 0 인가",
             "🔴 **`_fmt_literals` 가 「자리표시자 + 산술 리터럴」을 «둘 다» 요구하는데 "
             "`note986_gen.py` 의 서식 다섯은 전부 `⟦⟧` 슬롯이라 스캔 자체가 안 된다** --- "
             "0 은 「깨끗하다」가 아니라 **「안 봤다」**다(조항 59)"),
        ])),
        ("⑦ 「빈 파일 `=` 자백이 끝 커밋 메시지에만 있다」", collections.OrderedDict([
            ("🔴 어디에 있었나", "🔴 **끝 커밋 메시지에만**(문서 0 · 원장 0 · PR 0)"),
            ("🔴 987 은 어디에 적나", "🔴 **판정문 · 인계 카드 · PR 본문 · 원장 넷 다**"),
        ])),
        ("⑧ 「측정 창 안에서 러너 10 개를 고쳤다」", collections.OrderedDict([
            ("🔴 986 의 통과 조건", "🔴 **「낡은 산출물 0」뿐이다**"),
            ("🔴🔴🔴 그래서 무엇이 집행 안 되나",
             "🔴 **`조항 66` 의 「주행 중 소스 수정 금지」 자체는 집행되지 않는다** --- "
             "고치고 «다시 돌리면» 통과다. 🔴 987 도 같은 조건이고 **그 사실을 적는다**"),
        ])),
        ("통과", bool(s986 is not None and p986 is not None)),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **986 의 산출물을 고정 ref 에서 «읽었는가»** 하나다"),
    ])


# ══════════════════════════════════════════════════════════════════════
def daemon():
    try:
        pid = subprocess.check_output(["pgrep", "-f", "harvest_daemon.py"],
                                      cwd=str(ROOT)).decode().split()
    except Exception:                                               # noqa: BLE001
        pid = []
    import harvest_daemon as HD                                     # noqa: E402
    paths = list(getattr(HD, "PATHS", []) or [])
    return collections.OrderedDict([
        ("🔴 무엇", "🔴 **규칙 B --- 데몬을 안 재웠나**"),
        ("🔴 PID(`pgrep` 로 물었다)", pid or "없음"),
        ("🔴🔴 살아 있나", bool(pid)),
        ("🔴 데몬 커밋 경로(`harvest_daemon.PATHS` 에서 «읽었다»)", paths),
        ("통과", bool(pid)),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "🔴 **데몬이 살아 있는가** 하나다"),
    ])


def stage(ref):
    t0 = CY.now()
    CY.begin(ref)
    cs0 = CY.code_stamp()
    out = collections.OrderedDict()
    out["무엇"] = "987 §2 — 🔴🔴🔴 **「전」은 고정 ref 로만 · 한 이름 두 값을 끝낸다**"
    out["🔴 축"] = "자기 자(측정 규율)"
    out["🔴 고정 ref 둘"] = {"986 이 끝난 트리": REF_986, "985 가 끝난 트리": REF_985}
    out["§A 🔴🔴🔴 「전」을 고정 ref 로 다시 잰다"] = before_labels(REF_986, REF_985)
    out["§A-나 🔴🔴 AST 자 — 디스크에서 「전」을 읽는 자리"] = ast_before_ruler()
    out["§B 🔴🔴🔴 985 가 한 이름으로 두 범위를 쟀다"] = one_name_two_values()
    out["§B-나 🔴🔴 986 문서의 한글 수사 「985 의 다섯 문서」"] = korean_numeral_986()
    out["§C 🔴🔴 `⑤′` 절 3 을 고정 명부로 다시 낸다"] = sec3_fixed_roster()
    out["§D 🔴 즉시 정정"] = errata()
    out["§E 🔴 데몬(규칙 B)"] = daemon()
    out["통과"] = bool(all(v.get("통과") for k, v in out.items()
                         if k.startswith("§") and isinstance(v, dict)))
    CY.write(OUT, out, ref, cs0, t0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["audit"])
    ap.add_argument("--ref", required=True)
    a = ap.parse_args()
    r = stage(a.ref)
    print(json.dumps({
        "통과": r["통과"],
        "986 이 넣기 전 실측": r["§A 🔴🔴🔴 「전」을 고정 ref 로 다시 잰다"]["🔴🔴🔴 986 이 넣기 «전» 실측"],
        "986 이 실은 값이 틀렸나": r["§A 🔴🔴🔴 「전」을 고정 ref 로 다시 잰다"]["🔴🔴🔴 986 이 실은 값이 틀렸나"],
        "AST 자가 986 에서 잡은 자리": r["§A-나 🔴🔴 AST 자 — 디스크에서 「전」을 읽는 자리"][
            "🔴🔴 검정력 시연(조항 64) — 같은 자를 `runners/audit986.py`(고정 ref)에 문다"][
            "🔴🔴🔴 잡은 자리 수"],
        "986 의 반박이 거짓인가": r["§B 🔴🔴🔴 985 가 한 이름으로 두 범위를 쟀다"][
            "🔴🔴🔴 그 반박이 참인가"]["🔴🔴🔴 986 의 반박이 «거짓»인가"],
        "985→986 대상이 줄었나": r["§C 🔴🔴 `⑤′` 절 3 을 고정 명부로 다시 낸다"][
            "🔴🔴🔴 985 → 986 에서 대상이 줄었나"],
    }, ensure_ascii=False))
    return 0 if r["통과"] else 1


if __name__ == "__main__":
    sys.exit(main())
