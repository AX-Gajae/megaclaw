#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""985 §1·§4 — 🔴🔴🔴 **984 의 채점을 다시 내고, 막힌 자리의 기전을 «잰다»**.

담는 것 다섯:
- **§A** 🔴🔴 `fiveprime902.repair_lanes` 를 **984 의 인자로 다시 물려** 절 8 을 다시 판정한다.
  984 의 사전등록 §8 「저장소 밖 레인: 0」이 거짓이라 **절 8 은 `False`** 이고,
  그러면 `⑤′` **4 / 16** · 예측 **4 / 6** 이다.
- **§B** 🔴 **「끊은 자리」를 갈라 센다** --- 통과로 바뀐 것 / 분모에서 뺀 것 / 다시 재니 붉은 것.
  그리고 **공통 17** 로 983 대 984 를 나란히 놓는다.
- **§C** 🔴 **`⑤′` 절 1 소비자 분모의 기전** --- 경로별 소비자 수와
  **「코드가 읽는가, 주석·산문이 언급하는가」**를 AST 로 가른다.
  🔴 **등록 결정: 원장을 소비자 분모에서 «빼지 않는다»**(사전등록 §4-6 · 근거 셋).
- **§D** 🔴 **984 반증조건 다섯을 「안 쟀다」로 재분류한다**(#4·#8·#9·#11·#12).
- **§E** 🔴 **즉시 정정** --- 낡은 디스크 판 sha · 인증 트리 · `cert` 인용 0 · 「더 세게」.

씀:
    python3 runners/audit985.py --stage audit --ref <40자 sha>
"""
import argparse
import ast
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

import cycle985 as CY                                  # noqa: E402
import fiveprime902 as F                               # noqa: E402

OUT = "runners/out985_audit.json"

#: 984 가 `⑤′` 인증 주행에 쓴 인자 그대로(`fiveprime_984_cert.json` 의 `🔴 인자(argv)`).
B984 = "eba25b8fc8d3461d4155719623ffcfdbb1f247b0"
H984 = "196c9e0ec908088464d27c7da4a53d966a204d42"
P984 = "docs/prereg_984_leak_or_coupling.md"
DEN = "data/lab/denominator.json"
BODY984 = ("docs/판정_984.md", "docs/card_984.md", "docs/handoff_984.md", P984)


def _git(*a):
    return subprocess.check_output(["git"] + list(a), cwd=str(ROOT))


def _sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def _load(rel):
    p = ROOT / rel
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def _text(rel):
    p = ROOT / rel
    return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else None


# ══════════════════════════════════════════════════════════════════════
# §A 🔴🔴 984 의 `⑤′` 절 8 을 다시 판정한다
# ══════════════════════════════════════════════════════════════════════
KEY_OUT = "🔴🔴 956 R2 ㉢ 저장소 밖 레인(955 가 인계 카드를 고쳤고 계수기가 원리상 못 봤다)"


def redo_lanes():
    cert = _load("runners/fiveprime_984_cert.json") or {}
    old = cert.get("8 🔴 `[수리]` 레인 계수(955 R6)") or {}
    new = F.repair_lanes(B984, H984, None, P984, "main", H984)
    old_o = old.get(KEY_OUT) or {}
    new_o = new.get(KEY_OUT) or {}
    fails_old = cert.get("🔴 실패한 절")
    fails_old = list(fails_old) if isinstance(fails_old, list) else []
    lane_key = "8 🔴 `[수리]` 레인 계수(955 R6)"
    fails_new = sorted(set(fails_old) | ({lane_key} if not new["통과"] else set()))
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴🔴 **`fiveprime902.repair_lanes` 를 984 의 인자로 다시 물렸다** --- "
                 "같은 함수 · 같은 `--base`/`--head`/`--prereg`. 바뀐 것은 «시각»뿐이다"),
        ("🔴 인자", {"base": B984, "head": H984, "prereg": P984, "mainref": "main"}),
        ("🔴 984 가 인증 주행에서 낸 값", collections.OrderedDict([
            ("절 8 통과", old.get("통과")),
            ("㉢ 저장소 밖 레인 통과", old_o.get("통과")),
            ("㉢ 이 가지가 갈라진 뒤 바뀐 것", old_o.get("🔴 이 가지가 갈라진 뒤 바뀐 것")),
            ("㉢ §8 이 신고한 저장소 밖 레인 수", old_o.get("🔴 §8 이 신고한 저장소 밖 레인 수")),
        ])),
        ("🔴🔴🔴 지금 다시 재면", collections.OrderedDict([
            ("절 8 통과", new.get("통과")),
            ("㉠ 실제 바뀐 파일 통과",
             (new.get("🔴🔴 956 R2 ㉠ 실제 바뀐 파일로 센다(커밋 제목 문자열이 아니다)") or {}
              ).get("통과")),
            ("㉡ 규칙 상한 통과",
             (new.get("🔴🔴 956 R2 ㉡ 규칙 상한(`docs/루프.md` 레인 규칙 4 · v3.10)") or {}
              ).get("통과")),
            ("🔴🔴🔴 ㉢ 저장소 밖 레인 통과", new_o.get("통과")),
            ("🔴 ㉢ 이 가지가 갈라진 뒤 바뀐 것",
             new_o.get("🔴 이 가지가 갈라진 뒤 바뀐 것")),
            ("🔴 ㉢ 미신고 저장소 밖 수리", new_o.get("🔴 미신고 저장소 밖 수리")),
            ("레인 수", new.get("🔴🔴 레인 수(분자 --- 이것이 「수리 레인」의 수다)")),
            ("표지 없는 `[수리]` 커밋", new.get("🔴 표지 없는 `[수리]` 커밋(레인을 못 센다)")),
        ])),
        ("🔴🔴 왜 갈렸나", (
            "🔴 **자는 그대로다.** `repair_lanes` 는 `outside_declared == 0` 일 때 "
            "`not 0 == True` 라 **미신고로 센다**. 984 의 인증 주행 시점에는 인계 카드 "
            "mtime 이 아직 가지 분기 시각보다 «앞»이라 `outside_touched` 가 비어 있었고, "
            "**984 가 인계 카드를 메모리 파일로 옮긴 것은 그 주행 «뒤»였다**. "
            "🔴 곧 **984 는 자기가 만들 위반을 재기 «전»에 채점을 끝냈다**")),
        ("🔴🔴🔴 연쇄", collections.OrderedDict([
            ("984 가 게재한 실패 절", fails_old),
            ("984 가 게재한 실패 수 / 분모",
             "%d / %s" % (len(fails_old), cert.get("🔴 절 수(분모)"))),
            ("🔴🔴 정정된 실패 절", fails_new),
            ("🔴🔴🔴 정정된 실패 수 / 분모",
             "%d / %s" % (len(fails_new), cert.get("🔴 절 수(분모)"))),
            ("🔴 예측 P6(「실패 3 이하」)이 참인가", bool(len(fails_new) <= 3)),
            ("🔴 984 가 게재한 예측 분자", 5),
            ("🔴🔴🔴 정정된 예측 분자", 5 - (0 if len(fails_new) <= 3 else 1)),
        ])),
        ("통과", bool(new.get("통과") is not None)),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **같은 함수를 다시 물려 «값이 나왔는가»** 하나다. 그 값이 참이든 거짓이든 통과다 "
         "--- 판정은 위 「연쇄」 칸이 진다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §B 🔴 「끊은 자리」를 갈라 센다 · 공통 17
# ══════════════════════════════════════════════════════════════════════
WT983 = "⓪ 관문(작업 트리 · 🔴 983 부터 절 분모 «안»)"
WT984 = "⓪ 관문(작업 트리 · 🔴 984 부터 절 분모 «밖» 진단)"


def broke_what(lane_fail):
    f983 = _load("runners/fiveprime_983_final.json") or {}
    f984 = _load("runners/fiveprime_984_cert.json") or {}
    fa = set(f983.get("🔴 실패한 절") or [])
    fb = set(f984.get("🔴 실패한 절") or [])
    lane_key = "8 🔴 `[수리]` 레인 계수(955 R6)"
    if lane_fail:
        fb = fb | {lane_key}
    # 🔴 공통 17 --- 983 의 절 이름을 기준으로 삼되 ⓪ 작업 트리 절은 이름이 달라 이어 준다
    wt_dirty = ((f984.get(WT984) or {}).get("더러운 경로 수"))
    fb17 = set(fb)
    #: 984 는 ⓪ 작업 트리 절을 분모 밖으로 내렸다 --- 공통 17 로 되돌리면 그 절은
    #: **원리상 통과 불가**(규칙 A + 규칙 B)라 «실패»로 센다. 잰 날 것을 같이 싣는다.
    fb17.add(WT983)
    green = sorted(fa - fb)                       # 983 붉음 → 984 초록
    still = sorted(fa & fb)                       # 둘 다 붉음
    newred = sorted(fb - fa - {WT983})            # 984 에서 새로 붉어진 것
    return collections.OrderedDict([
        ("🔴 무엇", "🔴 **984 가 「다섯 자리 중 셋을 끊었다」고 적었다 --- 갈라 센다**"),
        ("🔴 983 이 실패한 절(분모 17)", sorted(fa)),
        ("🔴 984 가 게재한 실패 절(분모 16)", sorted(f984.get("🔴 실패한 절") or [])),
        ("🔴🔴 정정된 984 실패 절(분모 16)", sorted(fb)),
        ("🔴🔴🔴 984 가 「끊었다」고 적은 셋을 갈라 세면", collections.OrderedDict([
            ("① 절이 붉음 → 초록으로 «실제로» 바뀐 자리", green),
            ("① 수", len(green)),
            ("② 분모에서 «뺀» 자리(끊은 것이 아니다)", [WT984]),
            ("② 수", 1),
            ("② 그 절이 잰 날 것(더러운 경로 수)", wt_dirty),
            ("③ 「끊었다」고 적었으나 다시 재니 붉은 자리",
             ["8 🔴 `[수리]` 레인 계수(955 R6)"] if lane_fail else []),
            ("③ 수", 1 if lane_fail else 0),
            ("🔴🔴 그래서 「셋」의 정체", "🔴 **통과 %d + 분모 제거 1 + 거짓 %d = 3**"
             % (len(green), 1 if lane_fail else 0)),
            ("🔴🔴🔴 티처 #123 이 적은 「둘」",
             "🔴 **통과 %d + 분모 제거 1 = %d** --- 셋이 아니다"
             % (len(green), len(green) + 1)),
        ])),
        ("🔴🔴 공통 17 기준(983 의 분모로 둘 다 센다)", collections.OrderedDict([
            ("983 실패 / 17", "%d / 17" % len(fa)),
            ("🔴 984 실패 / 17(정정 반영 · ⓪ 작업 트리를 되돌려 넣는다)",
             "%d / 17" % len(fb17)),
            ("🔴 984 실패 / 17(984 가 게재한 대로 · 레인 정정 «전»)",
             "%d / 17" % len(set(f984.get("🔴 실패한 절") or []) | {WT983})),
            ("🔴 순증(983 → 984)", "%+d 절" % (len(fa) - len(fb17))),
            ("🔴 둘 다 붉은 절", still),
            ("🔴 984 에서 새로 붉어진 절", newred or "없음"),
            ("⚠ 왜 ⓪ 작업 트리를 실패로 세나",
             "🔴 **공통 분모로 견주려면 같은 절을 둘 다 세야 한다.** 984 는 그 절을 "
             "«분모 밖»으로 내렸고(조항 60-나 개정판의 요건 셋을 다 밟았다 · 유효하다) "
             "그 절은 규칙 A + 규칙 B 아래서 **원리상 통과 불가**다 --- 그러므로 공통 17 "
             "에서는 **실패**로 센다. 🔴 **이것은 984 를 벌하는 것이 아니라 「같은 자로 "
             "재면 몇인가」를 적는 것이다**(조항 60)"),
        ])),
        # 🔴 **잰 값이다** --- 두 산출물의 실패 절 집합을 «읽었고» ⓪ 절의 날 것도 읽었나.
        #    산출물이 없거나 키가 비면 여기서 떨어진다(조항 59).
        ("통과", bool(fa and fb and isinstance(wt_dirty, int))),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **983·984 의 실패 절 집합을 둘 다 «읽었고» ⓪ 작업 트리 절의 잰 날 것(더러운 "
         "경로 수)도 읽었는가.** 하나라도 못 읽으면 「0 이다」가 아니라 「모른다」라 불통과다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §C 🔴 `⑤′` 절 1 소비자 분모의 «기전»
# ══════════════════════════════════════════════════════════════════════
def _doc_nodes(tree):
    """모듈·클래스·함수의 **독스트링 Constant 노드**를 모은다(주석과 같이 센다)."""
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef,
                          ast.AsyncFunctionDef)):
            body = getattr(n, "body", None)
            if body and isinstance(body[0], ast.Expr) \
                    and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                out.add(id(body[0].value))
    return out


def _mention_kind(rel, needles, tree_ref):
    """🔴 **「코드가 읽나, 산문이 언급하나」**를 AST 로 가른다.

    - **코드 리터럴**: 독스트링이 «아닌» 문자열 상수 안에 바늘이 있다.
    - **산문만**: 원문에는 있는데 코드 리터럴에는 없다(주석 · 독스트링 · 마크다운).
    🔴 「산문만」은 **「그 파일을 다시 돌릴 이유가 없다」**는 뜻이지 「소비자가 아니다」가 아니다.
    """
    st, txt = F.tree_text(rel, tree_ref, None)
    if st != "읽었다" or txt is None:
        return "🔴 못 읽었다"
    if not rel.endswith(".py"):
        return "비 .py"
    try:
        tree = ast.parse(txt)
    except SyntaxError:
        return "🔴 파싱 실패"
    docs = _doc_nodes(tree)
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) \
                and id(n) not in docs:
            if any(nd in n.value for nd in needles):
                return "코드 리터럴"
    return "산문만(주석·독스트링)"


def consumers(base, head, tree_ref):
    rc, out, err = F._git(["-c", "core.quotepath=false", "diff", "--name-only", "-z",
                           "%s..%s" % (base, head)])
    if rc != 0:
        return {"🔴": "git diff 종료 %d: %s" % (rc, err[:200]), "통과": False}
    changed = sorted(p for p in out.split("\0") if p)
    nd = F._needles(changed)
    allc, _ = F._grep_l(sorted(set(sum(nd.values(), []))), tree_ref)
    # 경로별 기여
    per = []
    for p in changed:
        ns = sorted(set(sum(F._needles([p]).values(), [])))
        got, _m = F._grep_l(ns, tree_ref)
        per.append((len(got), len([g for g in got if g.endswith(".py")]), p, ns))
    per.sort(reverse=True)
    # 원장을 뺀 판
    ch2 = [p for p in changed if p != DEN]
    c2, _ = F._grep_l(sorted(set(sum(F._needles(ch2).values(), []))), tree_ref)
    # 🔴 「코드가 읽나 / 산문이 언급하나」
    kinds = collections.Counter()
    kind_rows = {}
    needles_all = sorted(set(sum(nd.values(), [])))
    for c in allc:
        if not c.endswith(".py"):
            kinds["비 .py"] += 1
            continue
        k = _mention_kind(c, needles_all, tree_ref)
        kinds[k] += 1
        kind_rows.setdefault(k, []).append(c)
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴 **`⑤′` 절 1 이 왜 네 사이클째 붉은가** --- 기전을 «잰다»"),
        ("🔴 범위", "%s..%s (트리 %s)" % (base[:9], head[:9], tree_ref)),
        ("🔴 분모 ① 바뀐 경로 수", len(changed)),
        ("🔴 분모 ② 역참조 소비자 수", len(allc)),
        ("🔴 분모 ②-py 그중 .py", len([c for c in allc if c.endswith(".py")])),
        ("🔴🔴 경로별 소비자 수(내림차순)",
         [{"경로": p, "소비자": n, ".py": npy, "바늘": ns} for n, npy, p, ns in per]),
        ("🔴🔴🔴 원장(`%s`)을 소비자 분모에서 빼면" % DEN, collections.OrderedDict([
            ("소비자 수", len(c2)),
            ("그중 .py", len([c for c in c2 if c.endswith(".py")])),
            ("🔴 줄어드는 수", len(allc) - len(c2)),
            ("🔴🔴🔴 그래도 절 1 이 열리나",
             "🔴 **안 열린다** --- `.py` 가 %d 개 남고 그 전부를 다시 돌리거나 "
             "사유를 등록해야 통과다" % len([c for c in c2 if c.endswith(".py")])),
        ])),
        ("🔴🔴🔴 등록 결정(사전등록 §4-6): 원장을 빼지 «않는다»", (
            "🔴 근거 셋 --- ① **빼도 안 열린다**(위 칸) · ② 빼는 것은 **분모 축소**라 "
            "`조항 60-나` 개정판의 요건 셋을 다시 밟아야 하는데 **대가로 얻는 것이 0** 이다 · "
            "③ 🔴 **진짜 기전은 원장이 아니다** --- 아래 「언급의 정체」를 봐라")),
        ("🔴🔴🔴 언급의 정체(자: AST · 독스트링을 «주석»으로 센다)", collections.OrderedDict([
            ("🔴 갈래별 수", dict(kinds)),
            ("🔴 「산문만」 보기 열",
             sorted(kind_rows.get("산문만(주석·독스트링)", []))[:10]),
            ("🔴 「코드 리터럴」 보기 열", sorted(kind_rows.get("코드 리터럴", []))[:10]),
            ("🔴🔴🔴 그래서", (
                "🔴 **`⑤′` 절 1 의 「소비자」는 「그 이름을 아무 데서나 «언급»한 파일」이다** "
                "--- 주석 한 줄이나 독스트링의 인용도 소비자로 센다. 🔴 그리고 상위 넷"
                "(`docs/루프.md` · 원장 · `docs/목표.md` · `runners/fiveprime902.py`)은 "
                "**사이클마다 반드시 바뀌는 파일**이라 **그 언급의 총량이 곧 분모**가 된다. "
                "🔴🔴 **985 는 이 기전을 «재기만» 하고 자를 안 바꾼다** --- 자를 바꾸는 것은 "
                "사전등록한 상한 5 를 넘기는 수리이고, 「소비자」의 정의를 바꾸는 것은 "
                "**분모 바꿔치기**라 다음 사이클의 사전등록에서 해야 한다(조항 60-나 개정판)")),
        ])),
        # 🔴 **잰 값이다** --- 모든 소비자를 갈래로 «분류했나»(합이 분모와 같은가).
        #    파싱에 실패하거나 못 읽은 파일이 있으면 여기서 떨어진다.
        ("통과", bool(allc and sum(kinds.values()) == len(allc)
                    and "🔴 못 읽었다" not in kinds and "🔴 파싱 실패" not in kinds)),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **역참조 소비자 «전량»이 갈래로 분류됐는가**(갈래별 수의 합 == 분모) "
         "**그리고 못 읽거나 파싱 못 한 파일이 0 인가.** 절 1 이 열렸는지와 무관하다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §D 🔴 984 반증조건 다섯을 「안 쟀다」로 재분류한다
# ══════════════════════════════════════════════════════════════════════
def _const_bool(n):
    return isinstance(n, ast.Constant) and isinstance(n.value, bool)


def _pass_literals(rel):
    txt = _text(rel)
    if txt is None:
        return None
    hits = []
    for n in ast.walk(ast.parse(txt)):
        if isinstance(n, ast.Tuple) and len(n.elts) == 2:
            k, v = n.elts
            if isinstance(k, ast.Constant) and k.value == "통과" and _const_bool(v):
                hits.append({"파일": rel, "줄": n.lineno, "값": v.value})
        if isinstance(n, ast.Dict):
            for k, v in zip(n.keys, n.values):
                if isinstance(k, ast.Constant) and k.value == "통과" and _const_bool(v):
                    hits.append({"파일": rel, "줄": getattr(k, "lineno", None),
                                 "값": v.value})
    return hits


def reclassify():
    sc = _load("runners/out984_score.json") or {}
    fal = sc.get("§A 🔴 반증조건 14 / 14") or sc.get("§A 반증조건") or {}
    if not isinstance(fal, dict):
        fal = {}
    # #12 --- 분모를 984 러너 전량으로 넓힌다
    r984 = sorted(str(p.relative_to(ROOT)) for p in ROOT.glob("runners/*984*.py"))
    per, trues = {}, []
    for r in r984:
        h = _pass_literals(r)
        per[r] = h
        trues += [x for x in (h or []) if x["값"] is True]
    # #4 --- 창과 바늘
    import score984 as S984                              # noqa: E402
    # #9 --- 「고정점」 부분 문자열이 어디에 있나
    where = {}
    for p in BODY984:
        t = _text(p)
        if t is None:
            where[p] = "🔴 못 읽었다"
            continue
        idx = [i for i in range(len(t)) if t.startswith("고정점", i)]
        where[p] = {"히트 수": len(idx),
                    "보기": [t[max(0, i - 45):i + 45].replace("\n", " ")
                           for i in idx[:3]]}
    fs = _load("runners/out984_score.json") or {}
    feeds = fs.get("§F5 🔴 인용 산출물 도장") or {}
    return collections.OrderedDict([
        ("🔴 무엇", "🔴🔴 **984 의 반증조건 다섯을 「안 쟀다」로 재분류한다**(티처 #123 3순위 ⑤)"),
        ("#4 🔴 `2·짝SE` 를 못 넘는 칸으로 모양을 주장했나", collections.OrderedDict([
            ("🔴 자", "`score984.shape_audit` --- 「모양」 낱말 곁 ±%d 자 안에 근거 낱말이 "
                    "하나라도 있으면 통과" % S984.SHAPE_WIN),
            ("🔴 창(글자)", S984.SHAPE_WIN),
            ("🔴 근거 낱말(바늘)", list(S984.SHAPE_OK)),
            ("🔴🔴 왜 「안 쟀다」인가", (
                "🔴 **바늘에 `\"z \"` 가 있다.** 판정문에 `z` 가 붙은 수는 도처에 있고 "
                "창이 **±%d 자**라 「모양」 낱말 곁 440 자 안에 `z` 하나만 있으면 통과한다 "
                "--- **그 근거가 «그 모양의» 근거인지는 원리상 안 본다**" % S984.SHAPE_WIN)),
        ])),
        ("#8 🔴 규칙 D 분모에 「정본 유보」 절과 원장이 들어갔나", collections.OrderedDict([
            ("🔴 자", "`bool(any(\"정본 유보\" in x for x in tg))` --- `tg` 는 "
                    "**채점기 자신이 하드코딩한 대상 라벨 목록**이다"),
            ("🔴 라벨(채점기 안에 리터럴로 있다)",
             "🔴 `docs/목표.md` 「정본 유보」 절(R5 신설) · 원장 `노트 984` 항목(R5 신설)"),
            ("🔴🔴 왜 「안 쟀다」인가",
             "🔴 **구성상 참이다** --- 채점기가 자기가 지은 문자열에서 자기가 넣은 낱말을 "
             "찾는다. `rule_d()` 가 그 라벨을 안 바꾸는 한 이 조건은 «절대» 안 깨진다"),
        ])),
        ("#9 🔴 「고정점이 아니었다」가 저장소 안 문서 전부에 있나", collections.OrderedDict([
            ("🔴 자", "`\"고정점\" in t` --- **부분 문자열** grep"),
            ("🔴 문서별 히트와 맥락", where),
            ("🔴🔴 왜 「안 쟀다」인가",
             "🔴 **`docs/prereg_984_leak_or_coupling.md` 의 히트는 §2-5 의 «무관한» 문장"
             "(「고정점이 정의상 존재할 수 없다」)이다** --- 그 문장은 983 의 고정점 실패와 "
             "아무 상관이 없는데 조건을 통과시켰다. 🔴 **낱말 하나로 명제를 검사할 수 없다**"),
        ])),
        ("#11 🔴 인용 산출물 도장이 전부 F5 인가", collections.OrderedDict([
            ("🔴 분모", feeds.get("🔴 분모")),
            ("🔴🔴 사전 면제로 «뺀» 수", feeds.get("🔴🔴 뺀 수")),
            ("🔴🔴 왜 「안 쟀다」인가",
             "🔴 **면제로 뺀 수가 0 이다** --- 사전등록 §2-5 가 「`⑤′` 산출물을 뺀다」를 "
             "«사전»에 등록했는데 **실제로 빠진 파일이 하나도 없다.** 곧 그 면제는 "
             "**아무 일도 안 했고**, 조건은 그 면제 없이도 같은 값을 냈다"),
        ])),
        ("#12 🔴🔴 채점기에 리터럴 `(\"통과\", True)` 가 있나", collections.OrderedDict([
            ("🔴 984 가 쓴 분모", ["runners/score984.py"]),
            ("🔴🔴🔴 985 가 넓힌 분모(984 러너 전량)", r984),
            ("🔴 파일별 걸린 자리", per),
            ("🔴🔴🔴 984 가 새로 심은 리터럴 `(\"통과\", True)`", trues),
            ("🔴🔴🔴 그 수", len(trues)),
            ("🔴🔴 왜 「안 쟀다」인가",
             "🔴 **분모가 한 파일이라 나머지를 원리상 못 본다.** 984 는 「채점기」를 "
             "`score984.py` 로만 새겼는데, **`통과` 를 리터럴로 내는 자리는 값을 «내는» "
             "러너에 있었다**"),
            ("⚠ 티처 #123 은 「8 개」라 적었고 실측은",
             "🔴 **%d 개다**(티처가 «열거한» 자리도 %d 개다 --- 세는 말만 하나 어긋났다)"
             % (len(trues), len(trues))),
        ])),
        ("🔴🔴🔴 재분류한 조건 수", 5),
        ("🔴🔴🔴 984 의 등록 분모", 14),
        ("🔴🔴🔴 재분류 뒤 실질 분모", 14 - 5),
        ("🔴🔴🔴 재분류 결과", "🔴 **984 의 반증조건 14 중 다섯(#4·#8·#9·#11·#12)은 "
                       "「안 깨졌다」가 아니라 「안 쟀다」다**"),
        # 🔴 **잰 값이다** --- 다섯 조건의 자를 실제로 «읽어» 값을 냈나.
        #    특히 #12 는 984 러너 전량을 AST 로 훑어 **리터럴이 «있음»을 보였다** ---
        #    0 이 나오면 내 고발이 거짓이므로 여기서 떨어진다.
        ("통과", bool(r984 and all(v is not None for v in per.values())
                    and len(trues) > 0
                    and feeds.get("🔴 분모") is not None
                    and all(isinstance(v, dict) for v in where.values()))),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **다섯 조건의 자를 실제로 뜯어 값을 냈는가 · 그리고 #12 의 고발이 «참인가».** "
         "리터럴이 0 개면 내 고발이 거짓이라 **떨어진다** --- 🔴 이 자는 떨어질 수 있다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# §E 🔴 즉시 정정
# ══════════════════════════════════════════════════════════════════════
def corrections():
    # 낡은 디스크 판 sha
    stale = "caf51519c69dad81614e14cfb65b89581ef0694ac4578f3346dd9d787be88fce"
    gens = collections.OrderedDict()
    for c in ("8d7924bb7", "196c9e0ec", "14385b32e", "30937cb98"):
        try:
            gens[c] = _sha_bytes(_git("show", "%s:%s" % (c, DEN)))
        except subprocess.CalledProcessError:
            gens[c] = "🔴 못 읽었다"
    disk_now = _sha_bytes((ROOT / DEN).read_bytes())
    head_now = _sha_bytes(_git("show", "HEAD:" + DEN))
    # 인증 트리
    cert_commit = H984
    try:
        cert_tree = _git("rev-parse", cert_commit + "^{tree}").decode().strip()
    except subprocess.CalledProcessError:
        cert_tree = "🔴 못 읽었다"
    # cert 인용 0
    cited = {}
    for p in list(BODY984) + ["data/lab/denominator.json"]:
        t = _text(p)
        cited[p] = (t.count("fiveprime_984_cert") if t else None)
    led = json.loads((ROOT / DEN).read_text(encoding="utf-8"))
    e984 = led.get("노트 984") or {}
    feeds_list = None
    for k, v in (e984.items() if isinstance(e984, dict) else []):
        if isinstance(v, list) and any("out984_" in str(x) for x in v):
            feeds_list = (k, v)
    lk = _load("runners/out984_leak.json") or {}
    pro = (lk.get("§2 🔴🔴🔴 승격 물음 — 누출의 지문인가 구성상 결합인가") or {}
           ).get("🔴 λ 별", {}).get("u=0", {})
    ora = (pro.get("🔴🔴 자 ① 위약 팔 바꿔치기 — ㉮(미래를 본다)") or {})
    pre = (pro.get("🔴🔴 자 ① 위약 팔 바꿔치기 — ㉰(미래를 «안» 본다)") or {})
    return collections.OrderedDict([
        ("🔴 무엇", "🔴 **즉시 정정 --- 수리로 안 센다**(티처 #123)"),
        ("1 🔴🔴 「㉰ 가 더 세게 선다」 → 「같은 만큼 선다」", collections.OrderedDict([
            ("㉮ 부분상관 / p", [ora.get("🔴 부분상관"), ora.get("🔴 전수 순열 p")]),
            ("㉰ 부분상관 / p", [pre.get("🔴 부분상관"), pre.get("🔴 전수 순열 p")]),
            ("🔴🔴 ㉰ 의 부분상관이 더 «큰»가",
             bool((pre.get("🔴 부분상관") or 0) > (ora.get("🔴 부분상관") or 0))),
            ("🔴 전수 벌 수(7!)", 5040),
            ("🔴🔴 p 의 분자(순열 벌 수) — ㉮",
             int(round((ora.get("🔴 전수 순열 p") or 0) * 5040))),
            ("🔴🔴 p 의 분자(순열 벌 수) — ㉰",
             int(round((pre.get("🔴 전수 순열 p") or 0) * 5040))),
            ("🔴🔴🔴 옳은 문장",
             "🔴 **`㉰` 의 부분상관은 `0.967503` 으로 `㉮` 의 `0.971938` «보다 작다» --- "
             "곧 「더 세게」가 아니라 「더 약하게, 사실상 같은 만큼」 선다.** p 가 더 작은 것은 "
             "**4 벌 대 8 벌 / 5040** 의 이산성 잡음 안이다. 🔴 **산출물은 「같은 만큼」이라 "
             "옳게 적었고 판정문·원장이 「더 세게」로 과장했다**"),
        ])),
        ("2 🔴 낡은 디스크 판 sha", collections.OrderedDict([
            ("🔴 984 의 네 문서·원장·메모리 카드가 실은 값", stale),
            ("🔴 커밋별 실제 원장 sha256", gens),
            ("🔴 지금 디스크", disk_now), ("🔴 지금 `HEAD`", head_now),
            ("🔴🔴🔴 984 가 실은 값이 어느 세대인가",
             "🔴 **어느 세대도 아니다** --- `house984` 가 돈 시점의 값이고 그 뒤 "
             "`8d7924bb7`(`f64a4204…`) → `196c9e0ec`·`14385b32e`(`37cdf432…`) → "
             "`30937cb98`(`ff2530cf…`) 로 **세 번 더 바뀌었다.** "
             "🔴 **항목 수 `1190` 은 그 항목의 «내용»만 바뀌어 우연히 살아남았다**"),
            ("🔴🔴🔴 985 의 원리 정정",
             "🔴 **「원장 전량의 sha」는 이 사이클 자신의 항목을 쓰면 반드시 바뀌므로 "
             "«자기 문서에 실을 수 없다».** 985 는 문서가 싣는 정본 칸을 "
             "**「자기 항목을 뺀 판의 sha256」**으로 바꾼다 --- 그 값은 **고정점**이다"),
        ])),
        ("3 🔴 「인증 트리」는 커밋 sha 다", collections.OrderedDict([
            ("984 가 「인증 트리」라 적은 값", cert_commit),
            ("🔴 그것의 정체", "커밋 sha"),
            ("🔴🔴 그 커밋의 «트리» sha", cert_tree),
        ])),
        ("4 🔴 `fiveprime_984_cert.json` 인용 수", collections.OrderedDict([
            ("🔴 문서별 인용 횟수", cited),
            ("🔴 원장 `노트 984` 의 산출물 목록",
             (feeds_list[1] if feeds_list else "🔴 못 찾았다")),
            ("🔴 그 목록에 `cert` 가 있나",
             bool(feeds_list and any("cert" in str(x) for x in feeds_list[1]))),
            ("🔴🔴 그래서",
             "🔴 **이 사이클의 절차적 대표 성과(⑤′ 고정점 인증 주행)가 커밋 제목과 "
             "메모리 카드에만 있었다** --- 저장소 안 어느 문서도 그 파일을 안 가리킨다"),
        ])),
        # 🔴 **잰 값이다** --- 커밋별 원장 sha 를 전부 읽었고 · 인증 커밋의 트리를 풀었고 ·
        #    984 의 두 부분상관을 읽었나. 하나라도 못 읽으면 떨어진다(조항 59).
        ("통과", bool(all(v != "🔴 못 읽었다" for v in gens.values())
                    and cert_tree != "🔴 못 읽었다"
                    and ora.get("🔴 부분상관") is not None
                    and pre.get("🔴 부분상관") is not None
                    and all(v is not None for v in cited.values()))),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **정정 넷이 쓰는 값을 «전부 읽었는가».** 커밋별 원장 sha · 인증 커밋의 트리 · "
         "984 의 두 부분상관 · 문서별 인용 횟수 --- 하나라도 못 읽으면 불통과다(조항 59)"),
    ])


# ══════════════════════════════════════════════════════════════════════
def stage(ref):
    t0 = CY.now()
    CY.begin(ref)
    cs0 = CY.code_stamp()
    a = redo_lanes()
    lane_fail = (a["🔴🔴🔴 지금 다시 재면"]["절 8 통과"] is False)
    out = collections.OrderedDict()
    out["무엇"] = ("985 §1·§4 — 🔴🔴🔴 **984 의 채점을 다시 내고 막힌 자리의 기전을 «잰다»**")
    out["🔴 축"] = "자기 자(채점 재발행 · 분모 기전)"
    out["§A 🔴🔴🔴 984 `⑤′` 절 8 재판정"] = a
    out["§B 🔴 「끊은 자리」를 갈라 센다 · 공통 17"] = broke_what(lane_fail)
    out["§C 🔴🔴 `⑤′` 절 1 소비자 분모의 기전"] = consumers(
        B984, H984, H984)
    out["§D 🔴🔴 984 반증조건 다섯 재분류"] = reclassify()
    out["§E 🔴 즉시 정정"] = corrections()
    out["통과"] = bool(all(out[k].get("통과") for k in out
                         if k.startswith("§") and isinstance(out[k], dict)))
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
        "984 절 8 재판정": r["§A 🔴🔴🔴 984 `⑤′` 절 8 재판정"][
            "🔴🔴🔴 지금 다시 재면"]["절 8 통과"],
        "정정된 ⑤′": r["§A 🔴🔴🔴 984 `⑤′` 절 8 재판정"][
            "🔴🔴🔴 연쇄"]["🔴🔴🔴 정정된 실패 수 / 분모"],
        "정정된 예측 분자": r["§A 🔴🔴🔴 984 `⑤′` 절 8 재판정"][
            "🔴🔴🔴 연쇄"]["🔴🔴🔴 정정된 예측 분자"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
