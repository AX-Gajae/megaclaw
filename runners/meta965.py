# -*- coding: utf-8 -*-
"""🔴🔴 노트 965 — **못 떨어지는 검사를 손이 아니라 기계로 센다**.

962(W6) → 963(§3 W3′) → 964(§-1 · 절 회계 · W10) — **네 사이클 연속으로 항진명제가
새로 태어났다.** 964 는 이 병을 가장 정확하게 진단한 사이클이면서 동시에 **가장 많이(3개)
새로 만든** 사이클이다. 🔴 **손으로 세는 한 다섯 번째가 온다.**

그래서 이 파일은 **검사를 검사하는 기계**다. 등록된 러너의 `통과` 키를 **전수로 뽑아**,
그 값을 만든 코드를 **변조 입력으로 실제로 다시 돌려** 「상수를 내는 것」을 센다.

**자 셋** (사전등록 `docs/prereg_965_metataut.md` §3):

  **자 A (정적 · 리터럴)**  `통과` 표현식의 **자유 이름이 0개**면 항진명제.
                            → 티처 #103 **C1** (`checks964.py:1096`) 이 여기 걸린다.
  **자 B (동적 · 슬라이스 뿌리 변조)**  감싸는 함수 안에서 **뒤로 슬라이스**하고
                            **슬라이스의 뿌리**를 무작위로 갈아 값을 모은다. 전부 같으면 항진명제.
                            → 티처 #103 **C2** (`checks964.py:1252` · 같은 집합의 분할) 이 여기 걸린다.
  **자 C (정적 · 자기 재계산 대조)**  한 검사가 **같은 순수함수를 같은 인자로 두 번 부른
                            결과끼리** 견주면 항진명제.
                            → 티처 #103 **C3** (`curve961.py:601`) 이 여기 걸린다.

🔴 **티처 #103 이 964 의 하네스에서 잡아낸 함정을 이 파일은 피한다.**
964 의 「True 508 / False 1,492」는 분해하면 **op0(변조 없음) 508 → True 508 · op1/op2/op3
1,492 → True 0** 이었다. 즉 **판정을 오로지 「손으로 변조했나」가 결정하고 무작위 인자는
하나도 안 물었다.** 그래서 자 B 는 **뿌리별 감도**를 따로 낸다 —
**어느 뿌리를 갈았을 때 값이 실제로 변했나.** 감도가 0인 뿌리는 「안 물었다」로 신고한다.

🔴 **이 파일도 §0-나 등록 목록에 자기를 넣는다**(사전등록 §5 V4). 자기 `통과` 키가 상수면
**F1 로 이 사이클은 실패**다.
"""
from __future__ import annotations

import argparse
import ast
import builtins
import collections
import datetime as dt
import gzip
import hashlib
import importlib
import io
import json
import random
import signal
import sys
import types
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "runners" / "out965_meta.json"

# ── §0-나 등록 러너 집합 (사전등록에 못 박았다 — 이 목록이 분모다) ────────────
REGISTERED = [
    "runners/curve961.py",
    "runners/triples962.py",
    "runners/checks963.py",
    "runners/checks964.py",
    "runners/prose964.py",
    "runners/fiveprime902.py",
    "lab/adopt.py",
    "runners/checks965.py",
    "runners/meta965.py",
]

#: 🔴 **§4 F1 의 「내가 새로 만든 것」 집합.** 965 는 이것을 코드 안에 박아 뒀다 —
#: 그래서 **966 이 자기 러너에 F1 을 걸 수 없었다.** 이제 목록이고 `--mine` 로 바꾼다.
MINE = ["runners/meta965.py", "runners/checks965.py"]

# 산출물(있으면 `통과` 키를 전수로 센다 — 원문 대조용 분모)
REGISTERED_OUT = [
    "runners/out961_curve.json",
    "runners/out962_triples.json",
    "runners/out963_checks.json",
    "runners/out964_checks.json",
    "runners/out964_prose.json",
    "runners/out964_fiveprime.json",
    "runners/out965_checks.json",
]

SITE_SEC = 25          # 🔴 한 자리에 쓰는 총 시간 상한(초)
CALL_SEC = 2           # 🔴 슬라이스 한 번의 상한(초) — 넘으면 그 뽑기를 버린다
N_DRAWS = 200          # 자 B 동시 변조 뽑기 수
N_PER_ROOT = 60        # 자 B 뿌리별 감도 뽑기 수
N_MIN_OK = 20          # 🔴 성공 호출이 이보다 적으면 「모른다」 — `통과` 를 안 낸다
#: 🔴 **R2(노트 966 · 티처 #104 C4)** — 4단계(전역 변조)의 성공 호출이 이보다 적으면
#: 「전역이 판정을 무나」를 **못 갈랐다**로 떨어뜨린다. 이 상수가 없어서
#: `glob_bites = len(gseen2) > 1` 이 **공집합에서 False** 로 떨어졌고, 티처 #104 가
#: 잰 4단계 실측 판별력이 **1 / 125** 였다.
N_MIN_G = 20
#: 🔴 **R3(노트 966 · 티처 #104 C3)** — F1 분모에서 빼는 자리. 이 셋은 검사가 아니라
#: **자 B 의 무작위 생성기가 만드는 표본**의 리터럴이다(`"통과": rng.choice([...])`).
#: 분모에 넣으면 「내가 새로 만든 검사」를 3 만큼 부풀린다(조항 60).
#: 🔴 **진짜 새 검사 자리는 22 가 아니라 19 다.**
#: 🔴 **줄 번호로 걸지 않는다** — 줄은 편집으로 밀린다(티처 #104 가 준 447·451·457 은
#: 이 주석을 넣은 순간 이미 461·465·471 로 밀렸다). **감싸는 함수 이름**으로 건다.
F1_DENOM_EXEMPT_FUNCS = {
    "_gen_pool": "자 B 의 무작위 생성기가 만드는 **표본**의 리터럴 — 검사가 아니다",
}
#: 🔴 978 수리 3 — §4 F1 이 허용하는 항진명제 수. **등록값이고 0 이다.**
#: 옛 판은 이 0 이 `== 0` 안에 박혀 있어 생성기가 원리상 못 움직였다.
F1_ALLOWED_TAUT = 0
SEED = 965


# ══════════════════════════════════════════════════════════════════════════
# 쓰기 차단 (판 미접촉 · 산출물 오염 방지) — V10
# ══════════════════════════════════════════════════════════════════════════
_WRITE_MODES = set("wxa+")
OPENED: list = []


class WriteBlocked(RuntimeError):
    pass


class SliceTimeout(RuntimeError):
    """🔴 슬라이스가 무거운 진짜 계산(부트스트랩 등)을 부르면 한 뽑기가 몇 분을 먹는다.

    `timeout` 명령은 이 환경에 없다(제약). **`SIGALRM` 으로 판마다 끊는다.**
    끊긴 뽑기는 **성공으로 안 센다** — 그래서 「모른다」로 흘러간다(조항 59).
    """


def _alarm(_s, _f):
    raise SliceTimeout("슬라이스가 %d 초를 넘겼다" % CALL_SEC)


def call_capped(fn, kw):
    old = signal.signal(signal.SIGALRM, _alarm)
    signal.setitimer(signal.ITIMER_REAL, CALL_SEC)
    try:
        return fn(**kw)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


class _NoWrite:
    """임포트·슬라이스 실행 동안 **쓰기를 원리상 막는다.**

    🔴 ⚠ 러너 20개 이상이 `ROOT` 를 하드코딩하고 임포트만 해도 산출물을 쓴다
    (`runners/abscorr840.py:57`). 이 문지기가 없으면 메타 검사가 **남의 증거물을 덮어쓴다**.
    """

    def __enter__(self):
        self._b, self._i, self._g = builtins.open, io.open, gzip.open
        self._pw_t, self._pw_b = Path.write_text, Path.write_bytes
        self._po = Path.open

        def guard(orig, is_path=False):
            def f(*a, **k):
                target = a[1] if is_path and len(a) > 1 else (a[0] if a else None)
                mode = k.get("mode")
                if mode is None:
                    idx = 2 if is_path else 1
                    mode = a[idx] if len(a) > idx else "r"
                OPENED.append(str(target if not is_path else a[0]))
                if isinstance(mode, str) and (_WRITE_MODES & set(mode)):
                    raise WriteBlocked("쓰기 차단: %r %r" % (target, mode))
                return orig(*a, **k)
            return f

        builtins.open = guard(self._b)
        io.open = guard(self._b)
        gzip.open = guard(self._g)

        def _blocked(*a, **k):
            raise WriteBlocked("쓰기 차단(Path)")
        Path.write_text = _blocked
        Path.write_bytes = _blocked
        Path.open = guard(self._po, is_path=True)
        return self

    def __exit__(self, *e):
        builtins.open, io.open, gzip.open = self._b, self._i, self._g
        Path.write_text, Path.write_bytes, Path.open = self._pw_t, self._pw_b, self._po
        return False


# ══════════════════════════════════════════════════════════════════════════
# 통과 자리 뽑기 — AST 전수
# ══════════════════════════════════════════════════════════════════════════
BUILTIN_NAMES = set(dir(builtins))


def _parents(tree):
    p = {}
    for node in ast.walk(tree):
        for ch in ast.iter_child_nodes(node):
            p[ch] = node
    return p


def _enclosing_func(node, parents):
    cur = parents.get(node)
    while cur is not None:
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return cur
        cur = parents.get(cur)
    return None


class Site:
    """`통과` 값을 만드는 코드 한 자리."""

    def __init__(self, rel, lineno, expr, func, kind):
        self.rel, self.lineno, self.expr, self.func, self.kind = rel, lineno, expr, func, kind
        self.key = "%s:%d" % (rel, lineno)


#: 🔴🔴 **노트 971 신설 (티처 #109 m3)** — 자의 분모가 `"통과"` **정확 일치**만 세서
#: `"🔴 F1 통과"` 같은 키가 **분모 밖**에 있었다. 969 에서 물려받은 구멍이고,
#: 970 에서는 **그 사이클의 가장 중요한 검사(F1 — 내가 돌린 러너 ↔ 커밋 blob)가
#: 통째로 자의 사각지대**였다.
#: 🔴 **기본값은 `exact`(965 그대로)** — 옛 산출물의 뜻이 조용히 갈리면 안 된다(노트 898 규칙).
#: `suffix` 는 **접두어를 허용**한다(`k.endswith("통과")`). 🔴 `"🔴 통과 수"` 같은
#: **계수 키는 여전히 분모 밖**이다 — 그건 검사가 아니라 회계다.
PASSKEY = "exact"


def is_pass_key(k) -> bool:
    """🔴 `통과` 키인가. `exact` = 965 그대로 · `suffix` = 접미 허용(971) ·
    🔴 `contains` = **975 신설**(`"통과" in k`).

    🔴🔴 **975 가 이 갈래를 왜 더했나**(티처 #113 3순위 ⓒ): 974 의 러너 1,917 줄에
    `exact` 분모가 **0** 이었다(973 은 1). **분모 0 이면 그 채점은 죽은 것이다** ---
    항진명제 0 이 「깨끗하다」가 아니라 「아무것도 안 봤다」라는 뜻이 된다.
    러너들은 `"🔴 F5 통과"`·`"🔴 통과"`·`"🔴 A-2 위반"` 처럼 **꾸민 키**를 쓴다.
    🔴 **기본값은 여전히 `exact`** --- 옛 산출물의 뜻을 조용히 안 바꾼다(노트 898).
    """
    if not isinstance(k, str):
        return False
    mode = globals().get("PASSKEY", "exact")
    if mode == "contains":
        return "통과" in k
    if mode == "suffix":
        return k.endswith("통과")
    return k == "통과"


def collect_sites(rel, tree, parents):
    """`{"통과": <expr>}` 와 `X["통과"] = <expr>` 를 **전수로** 뽑는다.

    🔴 **971** — 키 일치 규칙이 `PASSKEY` 에서 온다(`exact`|`suffix`).
    """
    sites = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and is_pass_key(k.value):
                    sites.append(Site(rel, v.lineno, v,
                                      _enclosing_func(node, parents), "딕트 리터럴"))
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if (isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant)
                        and is_pass_key(t.slice.value)):
                    sites.append(Site(rel, node.value.lineno, node.value,
                                      _enclosing_func(node, parents), "첨자 대입"))
    return sites


def passkey_census(rel, tree) -> dict:
    """🔴🔴 **971 신설 · 조항 66-③** — 구판(정확 일치)·신판(접미 일치)을 **한 산출물에** 싣는다.

    자를 고치면 전후를 반드시 같이 실어야 한다. 968 은 R1 으로 자기 점수를
    66.7% → 44.4% 로 옮겨 절반선을 넘겼는데 **한 번도 안 쟀다**.
    """
    exact, suffix, contains = [], [], []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    if k.value == "통과":
                        exact.append((v.lineno, k.value))
                    if k.value.endswith("통과"):
                        suffix.append((v.lineno, k.value))
                    if "통과" in k.value:
                        contains.append((v.lineno, k.value))
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if (isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant)
                        and isinstance(t.slice.value, str)):
                    if t.slice.value == "통과":
                        exact.append((node.value.lineno, t.slice.value))
                    if t.slice.value.endswith("통과"):
                        suffix.append((node.value.lineno, t.slice.value))
                    if "통과" in t.slice.value:
                        contains.append((node.value.lineno, t.slice.value))
    only = sorted({(ln, nm) for ln, nm in suffix} - {(ln, nm) for ln, nm in exact})
    only_c = sorted({(ln, nm) for ln, nm in contains} - {(ln, nm) for ln, nm in suffix})
    return {"🔴 분모(정확 일치 · 965 판)": len(exact),
            "🔴 분모(접미 일치 · 971 판)": len(suffix),
            "🔴 분모(포함 일치 · 975 판)": len(contains),
            "🔴 접미로만 잡히는 자리": ["%s:%d %s" % (rel, ln, nm) for ln, nm in only],
            "🔴 포함으로만 잡히는 자리": ["%s:%d %s" % (rel, ln, nm) for ln, nm in only_c],
            "🔴 늘어난 수": len(suffix) - len(exact),
            "🔴🔴 정확 일치 분모가 0 인가(= 이 파일에서 965 판 채점은 죽었다)":
                len(exact) == 0,
            "🔴🔴 포함 일치 분모도 0 인가": len(contains) == 0}


def literal_claim_census(rel, tree) -> dict:
    """🔴🔴🔴 **979 수리 3 — census 를 `통과` 키 밖으로.**

    지금까지의 census 는 **`통과` 키만** 봤다. 그래서 `ruler978.py:444·792·878` 의

        out["🔴 유보는 한 줄도 안 만졌다"] = True

    셋을 **원리상 못 봤다** --- 키에 「통과」라는 글자가 없기 때문이다. 티처 #117 치-7 이
    지목한 자리이고, 그 셋은 **반증조건 6 을 지는 주장**이었다.

    🔴 이 자는 **키 이름을 안 본다.** 딕트 값이 **맨 리터럴 `True`/`False`** 인 자리를
    전수로 세고, 그중 **`통과` 계열이 아닌 자리**를 따로 낸다 --- 옛 census 의 사각지대다.
    🔴 **계수 키(`"🔴 분자/분모"` 같은 문자열 값)는 분모 밖이다** --- 값이 참/거짓일 때만 센다.
    """
    #: 🔴 **조건 가지 안의 리터럴은 가르되 분모에서 빼지 않는다**(조항 60).
    #: `if p.is_file(): out = {"🔴 파일이 있나": True}` 는 **가지가 자다** —
    #: 무조건 자리와 **둘 다 센다**. 🔴 분모를 줄여서 붉은 수를 없애면 그게 부풀림이다.
    parents = _parents(tree)

    def _cond(node):
        cur = node
        while cur in parents:
            cur = parents[cur]
            if isinstance(cur, (ast.If, ast.While, ast.For, ast.Try,
                                ast.ExceptHandler, ast.IfExp)):
                return True
        return False

    lit, lit_pass, allkeys = [], [], 0

    def _take(key, node, lineno, owner):
        if not isinstance(key, str):
            return
        if isinstance(node, ast.Constant) and isinstance(node.value, bool):
            row = "%s:%d %s = %s" % (rel, lineno, key, node.value)
            lit.append((lineno, key, bool(node.value), _cond(owner)))
            if "통과" in key:
                lit_pass.append(row)
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    allkeys += 1
                    _take(k.value, v, getattr(v, "lineno", getattr(node, "lineno", 0)),
                          node)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if (isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant)
                        and isinstance(t.slice.value, str)):
                    allkeys += 1
                    _take(t.slice.value, node.value, node.value.lineno, node)
    blind = [r for r in lit if "통과" not in r[1]]
    blind_true = [r for r in blind if r[2]]
    uncond = [r for r in blind_true if not r[3]]
    cond = [r for r in blind_true if r[3]]
    return {
        "🔴 분모: 문자열 키를 가진 딕트 자리": allkeys,
        "🔴 분자: 값이 맨 리터럴 참/거짓인 자리": len(lit),
        "🔴🔴 그중 `통과` 계열이 아닌 자리(옛 census 의 사각지대)": len(blind),
        "🔴🔴🔴 그중 값이 리터럴 `True` 인 자리(= 근거 없는 주장 후보)": len(blind_true),
        "🔴🔴🔴 그중 **조건 가지 밖**(무조건 참) 자리": len(uncond),
        "🔴 그중 조건 가지 안(가지가 자다) 자리": len(cond),
        "🔴 그 자리 목록": ["%s:%d %s = True" % (rel, ln, k)
                       for ln, k, _v, _c in blind_true][:40],
        "🔴 무조건 참 자리 목록": ["%s:%d %s = True" % (rel, ln, k)
                          for ln, k, _v, _c in uncond][:40],
        "🔴 `통과` 계열의 리터럴 자리": lit_pass[:20],
        "🔴 이 자가 왜 생겼나": (
            "🔴 `ruler978.py:444·792·878` 의 「🔴 유보는 한 줄도 안 만졌다 = True」 셋을 "
            "옛 census 가 **키 이름 때문에 원리상 못 봤다**(티처 #117 치-7)"),
    }


def collect_delegations(rel, tree, parents):
    """`{**f(...)}` — 검사를 **다른 함수에 위임**한 자리.

    🔴 티처 #103 **C3** 가 정확히 이 꼴이다: `{**rt, **w10_check(rt, lambda: rulers(...))}`.
    `통과` 라는 **글자가 그 줄에 없어서** 딕트 리터럴 스캔으로는 **원리상 안 걸린다.**
    """
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if k is None and isinstance(v, ast.Call):
                    out.append((v, _enclosing_func(node, parents)))
    return out


def free_names(expr):
    """표현식이 **읽는** 이름 — 내부 컴프리헨션 바인딩은 뺀다."""
    bound, used = set(), set()
    for n in ast.walk(expr):
        if isinstance(n, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            for g in n.generators:
                for t in ast.walk(g.target):
                    if isinstance(t, ast.Name):
                        bound.add(t.id)
        if isinstance(n, ast.Lambda):
            for a in list(n.args.args) + list(n.args.kwonlyargs):
                bound.add(a.arg)
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
            used.add(n.id)
    return used - bound


# ══════════════════════════════════════════════════════════════════════════
# 자 A — 정적 · 리터럴 (자유 이름 0)
# ══════════════════════════════════════════════════════════════════════════
COND_NODES = (ast.If, ast.IfExp, ast.For, ast.While, ast.Try, ast.ExceptHandler)


def _conditional(site, parents):
    """🔴 **가지 안의 리터럴은 상수가 아니다.**

    `if 잘못됐다: return {"통과": False}` 의 `False` 는 **가지 자체가 자**다.
    반대로 **아무 가지에도 안 싸인 리터럴**은 어떤 입력에서도 같은 값을 낸다 — 그게 C1 이다.
    """
    cur, chain = parents.get(site.expr), []
    while cur is not None and not isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
        if isinstance(cur, COND_NODES):
            chain.append(type(cur).__name__)
        cur = parents.get(cur)
    return chain


def ruler_A(site, parents):
    """자유 이름이 0개면 **입력이 없다** → 원리상 상수. 단 **가지 안이면 아니다**."""
    fn = {n for n in free_names(site.expr) if n not in BUILTIN_NAMES}
    if fn:
        return {"항진명제": False, "자유 이름": sorted(fn)}
    try:
        shown = ast.literal_eval(site.expr)
    except Exception:                                              # noqa: BLE001
        shown = "리터럴 평가 불가(그러나 자유 이름 0)"
    chain = _conditional(site, parents)
    if chain:
        return {"항진명제": False, "자유 이름": [], "값": shown,
                "🔴 조건부 리터럴": chain,
                "🔴 왜 안 세나": ("이 리터럴은 **가지 안**에 있다 — 가지에 드는가/안 드는가가 자다. "
                            "「검사가 없다」가 아니라 「자가 가지다」")}
    return {"항진명제": True, "자유 이름": [], "값": shown, "🔴 조건부 리터럴": [],
            "🔴 왜": ("이 표현식은 **어떤 입력도 안 읽고 어떤 가지에도 안 싸여 있다** — "
                   "자료를 바꿔도 값이 안 변한다")}


# ══════════════════════════════════════════════════════════════════════════
# 자 B — 동적 · 슬라이스 뿌리 변조
# ══════════════════════════════════════════════════════════════════════════
def _assigned_names(stmt):
    out = set()
    tgts = []
    if isinstance(stmt, ast.Assign):
        tgts = stmt.targets
    elif isinstance(stmt, (ast.AugAssign, ast.AnnAssign)):
        tgts = [stmt.target]
    for t in tgts:
        for n in ast.walk(t):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                out.add(n.id)
    return out


MUTATORS = {"append", "extend", "update", "add", "setdefault", "insert",
            "pop", "clear", "sort", "remove", "discard", "popitem"}


def _opaque_names(stmt):
    """🔴 **슬라이스가 못 따라가는 이름** — 뿌리로 승격해 통째로 변조한다.

    셋이다: ① `X[...] = …` 로 **속이 바뀌는 그릇**(중첩된 곳까지 `ast.walk` 로 본다) ·
    ② `for`/`while`/`if`/`try`/`with` **가지 안에서 묶인 이름** ·
    ③ `x.append(…)`·`x.update(…)` 처럼 **메서드로 속이 바뀐 그릇**.
    🔴 이 승격이 이 자의 핵심이다 — 그래야 **같은 그릇에서 갈라 나온 수들끼리 견주는
    회계**(티처 #103 C2)와 **자기 분자를 분모로 쓰는 회계**(963 §3 W3′)가 드러난다.
    """
    out = set()
    for n in ast.walk(stmt):
        tgts = []
        if isinstance(n, ast.Assign):
            tgts = n.targets
        elif isinstance(n, (ast.AugAssign, ast.AnnAssign)):
            tgts = [n.target]
        for t in tgts:
            cur = t
            while isinstance(cur, (ast.Subscript, ast.Attribute)):
                cur = cur.value
            if isinstance(cur, ast.Name) and not isinstance(t, ast.Name):
                out.add(cur.id)
    # ③ `x.append(...)`/`x.update(...)` 처럼 **메서드로 속이 바뀐 그릇**
    for n in ast.walk(stmt):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr in MUTATORS and isinstance(n.func.value, ast.Name)):
            out.add(n.func.value.id)
    if not isinstance(stmt, (ast.Assign, ast.AugAssign, ast.AnnAssign, ast.Expr)):
        for n in ast.walk(stmt):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                out.add(n.id)
            elif isinstance(n, ast.alias):
                out.add((n.asname or n.name).split(".")[0])
    return out


def backward_slice(func, target_expr):
    """감싸는 함수의 **직선 문장**만 뒤로 슬라이스한다.

    🔴 규칙 하나가 핵심이다: **`X[...] = …` 로 속이 바뀌는 이름은 슬라이스하지 않고
    「뿌리」로 승격해 통째로 변조한다.** 그렇게 해야 `secs`/`n_ok`/`red` 처럼
    **같은 그릇에서 갈라 나온 수들끼리 견주는 회계**가 드러난다(티처 #103 **C2**).
    """
    if func is None:
        return None, None, "감싸는 함수가 없다"
    body = list(func.body)
    # 대상 표현식을 품은 최상위 문장의 위치
    idx = None
    for i, st in enumerate(body):
        for n in ast.walk(st):
            if n is target_expr:
                idx = i
                break
        if idx is not None:
            break
    if idx is None:
        return None, None, "대상 표현식이 함수 본문 최상위 문장 안에 없다"

    mutated = set()
    for st in body[:idx + 1]:
        mutated |= _opaque_names(st)

    need = {n for n in free_names(target_expr) if n not in BUILTIN_NAMES}
    keep = []
    for st in reversed(body[:idx]):
        if not isinstance(st, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            continue
        asg = _assigned_names(st)
        if not (asg & need):
            continue
        if asg & mutated:            # 🔴 속이 바뀌는 그릇 → 뿌리로 승격
            continue
        keep.append(st)
        rhs = ({n for n in free_names(st.value) if n not in BUILTIN_NAMES}
               if st.value else set())
        need |= rhs
        #: 🔴🔴 **R1 (노트 968)** — **자기참조 대입이 슬라이스를 끊고 있었다.**
        #: `P = P if isinstance(P, dict) else {}` 같은 문장에서 옛 판은 `need` 에
        #: `P` 를 넣었다가 `need -= (asg - mutated)` 로 **바로 다시 뺐다.** 그러면
        #: 그 앞의 `P = probes.get(...)` 이 `asg & need` 에 안 걸려 **체인이 끊기고**
        #: 뿌리가 0 이 된다 → 자 B 가 「뿌리가 0 — 자 A 가 볼 자리다」로 흘린다.
        #: 🔴 게다가 끊긴 슬라이스는 `P` 를 **정의 없이 읽는** 함수를 만든다(NameError).
        #: 실측(968): 이 한 줄로 `colaudit968.py` 의 자리 셋(`769`·`790`·`889`)이
        #: 「뿌리가 0 — 안 쟀다」에서 **실제로 슬라이스가 도는 자리**로 바뀌었다.
        #: 🔴 **티처 #106 은 「모른다」의 원인을 「생성기가 numpy·`Data` 를 못 만들어서」라
        #: 했는데, 968 이 `--genver 2` 로 그 생성기를 실제로 달았을 때 「모른다」는
        #: 8/9 그대로였다. 원인은 생성기가 아니라 이 슬라이서 결함이었다.**
        #: 🔴🔴 **R3-나 (노트 969 · 티처 #107 2순위-③)** — **구판을 지우지 않고 남긴다.**
        #:   「자기 자를 자기가 고치는」 자리에서는 **구판·신판을 같은 대상에 걸어 전후를
        #:   반드시 실어야 한다.** 968 은 R1 으로 §4 F1 「모른다」를 66.7% → 44.4% 로
        #:   옮겨 **절반선을 넘겼는데 한 번도 안 쟀다.** `--slicer old` 로 옛 판을 되살린다.
        #:   🔴 **기본값은 `new`(R1 적용)** --- 옛 산출물의 뜻이 조용히 갈리면 안 된다.
        if globals().get("SLICER", "new") == "old":
            need -= (asg - mutated)          # 🔴 968 이전 판(결함 있음 · 대조용)
        else:
            need -= (asg - mutated - rhs)    # 🔴 R1
    keep.reverse()
    return keep, sorted(need), None


def harvest_keys(tree):
    """🔴 **그 모듈이 실제로 쓰는 딕트 열쇠**를 소스에서 거둔다.

    무작위 문자열로 만든 딕트는 `r["🔴 항진명제인가"]` 같은 접근에서 **언제나 죽는다** —
    그러면 생성기가 검사의 유효 입력 영역에 원리상 못 닿고, 그 검사는 「상수」로 잘못 보인다.
    🔴 **자기 소스에서 열쇠를 거두면 변조가 진짜로 문다.**
    """
    keys = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant) \
                and isinstance(n.slice.value, str):
            keys.append(n.slice.value)
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                and n.func.attr in ("get", "setdefault") and n.args \
                and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str):
            keys.append(n.args[0].value)
        elif isinstance(n, ast.Dict):
            for k in n.keys:
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    keys.append(k.value)
    seen, out = set(), []
    for k in keys:
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out[:400]


def harvest_strings(tree):
    """🔴 그 모듈이 쓰는 **문자열 값** 전량(열쇠가 아니라 **값**).

    없으면 `r["파일"] in ("runners/meta965.py", …)` 같은 조건을 **원리상 못 맞힌다** —
    그러면 그 검사가 「상수」로 **잘못** 보인다. 🔴 이 저장소에서 실제로 그렇게 났다:
    §4(F1) 의 `통과` 가 두 번 상수로 잡혔고 **둘 다 생성기가 값을 못 만든 탓**이었다.
    """
    out, seen = [], set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value not in seen:
            seen.add(n.value)
            out.append(n.value)
    return out[:600]


#: 🔴🔴 **노트 968 신설 — 생성기 판.** 기본은 **1**(965·966·967 과 비트로 같다).
#: `--genver 2` 를 주면 **numpy 배열과 판 `Data` 객체 생성기**가 붙는다.
#: 왜: 966 은 자기 `통과` 자리 14 중 **13** 을, 967 은 18 중 **16(88.9%)** 를
#: 「모른다」로 흘렸고 **그 대부분이 「자 B 가 numpy 배열·판 `Data` 를 못 만들어서」**였다
#: (티처 #106 2순위 · 966·967 이 두 번 미룬 일).
#: 🔴 **기본값을 안 바꾼다** — 옛 산출물의 뜻이 조용히 갈리면 안 된다(노트 898 규칙).
GENVER = 1


def _np_pool(rng, pool):
    """🔴 **968 신설** — 「무거운 입력」 생성기. numpy 배열 · 판 `Data` · 마스크 짝."""
    import numpy as _np

    def _arr(n=None, kind="uniform"):
        n = n if n is not None else rng.randint(2, 60)
        st = _np.random.RandomState(rng.randint(0, 1 << 30))
        if kind == "uniform":
            return st.rand(n)
        if kind == "normal":
            return st.randn(n)
        if kind == "const":
            return _np.full(n, 0.5)
        if kind == "nan":
            return _np.full(n, _np.nan)
        if kind == "binary":
            return (st.rand(n) > 0.5).astype(float)
        if kind == "empty":
            return _np.array([], float)
        raise ValueError(kind)

    pool["numpy1차원"] = lambda: _arr()
    pool["numpy정규"] = lambda: _arr(kind="normal")
    pool["🔴 numpy상수열"] = lambda: _arr(kind="const")
    pool["🔴 numpy전부NaN"] = lambda: _arr(kind="nan")
    pool["🔴 numpy빈배열"] = lambda: _arr(kind="empty")
    pool["numpy이진"] = lambda: _arr(kind="binary")
    pool["numpy2차원"] = lambda: _np.random.RandomState(
        rng.randint(0, 1 << 30)).rand(rng.randint(2, 40), rng.randint(1, 6))
    pool["numpy정수"] = lambda: _np.arange(rng.randint(2, 40), dtype=float)

    def _data(empty=False):
        """판 `Data` 객체. 🔴 **빈 판(`dom={}`)도 뽑는다**(조항 64 개정 2 ⑦)."""
        try:
            from lab.harness import Data
        except Exception:                                          # noqa: BLE001
            return None
        if empty:
            return Data(dom={}, names={})
        doms = ["애니", "만화", "세계애니", "게임"][:rng.randint(1, 5)]
        dom, names = {}, {}
        for d in doms:
            n = rng.randint(3, 40)
            k = rng.randint(1, 5)
            st = _np.random.RandomState(rng.randint(0, 1 << 30))
            cols = ["wiki_level", "wiki_momentum", "cal_weekend", "tag_c1_모바일"][:k]
            A = st.rand(n, k)
            M = (st.rand(n, k) > 0.3).astype(float)
            if rng.random() < 0.35:            # 🔴 「죽은 열」을 일부러 섞는다
                A[:, 0] = 0.5
                M[:, 0] = 0.0
            dom[d] = (A, M, st.rand(n), 2020.0 + st.rand(n) * 6)
            names[d] = cols
        return Data(dom=dom, names=names)

    pool["🔴 판Data"] = lambda: _data()
    pool["🔴 판Data(빈 판)"] = lambda: _data(empty=True)
    return pool


def _gen_pool(rng, keypool=(), site_keys=(), str_pool=()):
    """뿌리에 먹일 무작위 값 생성기 — **꼴이 다른 열다섯**.

    🔴 `GENVER == 2` 면 **numpy 배열 · 판 `Data`** 생성기가 더 붙는다(노트 968).
    """
    sp = list(str_pool)

    def scal():
        base = [rng.randint(-5, 5), rng.random(), True, False, None,
                "".join(rng.choice("가나다abc") for _ in range(rng.randint(0, 4)))]
        if sp:                      # 🔴 그 모듈이 실제로 쓰는 문자열도 **값**으로 뽑는다
            base += [rng.choice(sp), rng.choice(sp)]
        return rng.choice(base)

    pool = collections.OrderedDict()
    pool["정수"] = lambda: rng.randint(-999, 999)
    pool["실수"] = lambda: rng.uniform(-10, 10)
    pool["불리언"] = lambda: bool(rng.getrandbits(1))
    pool["문자열"] = lambda: "".join(rng.choice("가나다abc통과") for _ in range(rng.randint(0, 6)))
    if sp:
        pool["모듈문자열"] = lambda: rng.choice(sp)
    pool["리스트"] = lambda: [scal() for _ in range(rng.randint(0, 6))]
    pool["평딕트"] = lambda: {("k%d" % i): scal() for i in range(rng.randint(0, 5))}
    pool["절딕트"] = lambda: {                      # 🔴 「절」 꼴 — 절 회계를 물게 하는 생성기
        ("절%d" % i): {"통과": rng.choice([True, False, "모른다", None]),
                       "값": scal()}
        for i in range(rng.randint(0, 7))}
    pool["섞인딕트"] = lambda: dict(
        [(("절%d" % i), {"통과": rng.choice([True, False, "모른다"])})
         for i in range(rng.randint(0, 5))]
        + [(("잡%d" % i), scal()) for i in range(rng.randint(0, 3))])
    pool["없음"] = lambda: None

    def _mkfun():
        payload = {("절%d" % i): {"통과": rng.choice([True, False, "모른다"]), "값": scal()}
                   for i in range(rng.randint(0, 5))}
        return lambda *a, **k: payload
    pool["함수→딕트"] = _mkfun          # 🔴 `recall()` 처럼 **부르는 인자**를 위한 생성기

    kp = list(keypool)
    if site_keys:
        sk = list(site_keys)

        def _sitedict():
            n = rng.randint(1, min(6, len(sk)))
            return {k: scal() for k in rng.sample(sk, n)}
        # 🔴🔴 **이 자리가 실제로 읽는 열쇠**로 만든 딕트. 모듈 전체 열쇠에서 무작위로 뽑으면
        #   `r["🔴 항진명제인가"]` 같은 접근을 거의 못 맞히고, 그러면 검사가 「상수」로 **잘못** 보인다.
        pool["자리키딕트"] = _sitedict
        pool["자리키딕트목록"] = lambda: [_sitedict() for _ in range(rng.randint(0, 6))]
        pool["자리키중첩"] = lambda: {("절%d" % i): _sitedict() for i in range(rng.randint(0, 5))}
    if kp:
        def _modkeys():
            n = rng.randint(1, min(5, len(kp)))
            return {rng.choice(kp): scal() for _ in range(n)}
        pool["모듈키딕트"] = _modkeys
        pool["모듈키딕트목록"] = lambda: [_modkeys() for _ in range(rng.randint(0, 5))]
        pool["모듈키중첩"] = lambda: {rng.choice(kp): _modkeys()
                                for _ in range(rng.randint(0, 4))}
    if GENVER >= 2:                     # 🔴 968 — 「무거운 입력」
        _np_pool(rng, pool)
    return pool


def ruler_B(site, modns, rng, keypool=(), str_pool=()):
    """슬라이스를 **실제로 실행**하고 뿌리를 갈아 값을 모은다."""
    keep, need, why = backward_slice(site.func, site.expr)
    if why:
        return {"판정": "모른다", "🔴 왜": why}
    glb = dict(modns)
    # 🔴 모듈 전역(임포트·상수)은 **입력이 아니다** — 뿌리에서 뺀다. 뺀 것을 신고한다.
    globals_seen = sorted(n for n in need if n in modns)
    roots = [n for n in need if n not in modns]
    slice_src = ast.unparse(ast.Module(body=keep, type_ignores=[])) if keep else ""
    expr_src = ast.unparse(site.expr)
    if not roots:
        return {"판정": "모른다",
                "🔴 왜": "뿌리가 0 — 자유 이름이 전부 모듈 전역이거나 없다(자 A 가 볼 자리다)",
                "모듈 전역으로 뺀 이름": globals_seen, "슬라이스 문장 수": len(keep)}

    site_keys = harvest_keys(ast.Module(
        body=list(keep) + [ast.Expr(value=site.expr)], type_ignores=[]))
    fn_src = ("def _m965_slice(%s):\n" % ", ".join(roots)
              + "".join("    " + ln + "\n" for ln in slice_src.splitlines())
              + "    return (%s)\n" % expr_src)
    try:
        code = compile(fn_src, "<m965 %s>" % site.key, "exec")
        loc = {}
        exec(code, glb, loc)                                       # noqa: S102
        fnobj = loc["_m965_slice"]
    except BaseException as e:                                     # noqa: BLE001
        return {"판정": "모른다", "🔴 왜": "슬라이스를 못 만들었다: %s" % e,
                "뿌리": roots, "모듈 전역으로 뺀 이름": globals_seen,
                "슬라이스 문장 수": len(keep)}

    pool = _gen_pool(rng, keypool, site_keys, str_pool)
    names = list(pool)
    import time as _t
    deadline = _t.time() + SITE_SEC
    capped = {"판 시간 상한에 걸린 뽑기": 0, "자리 시간 상한에 걸렸나": False}

    def draw(assign):
        kw = {}
        for r in roots:
            kw[r] = pool[assign[r]]()
        return kw

    # ── 1단계 · 성공하는 바탕 배정을 찾는다 ──────────────────────────────
    base = None
    for _ in range(400):
        if _t.time() > deadline:
            capped["자리 시간 상한에 걸렸나"] = True
            break
        assign = {r: rng.choice(names) for r in roots}
        kw = draw(assign)
        try:
            v = call_capped(fnobj, kw)
        except (KeyboardInterrupt, WriteBlocked):
            raise
        except SliceTimeout:
            capped["판 시간 상한에 걸린 뽑기"] += 1
            continue
        except BaseException:                                      # noqa: BLE001
            continue
        base = (assign, kw, v)
        break
    if base is None:
        return {"판정": "모른다", "🔴 왜": "400 회 뽑기(또는 시간 상한)에서 슬라이스가 한 번도 안 돌았다",
                "🔴 시간 상한": capped,
                "뿌리": roots, "모듈 전역으로 뺀 이름": globals_seen,
                "슬라이스 문장 수": len(keep)}

    vals, ok = [], 0
    seen = collections.Counter()

    def record(v):
        nonlocal ok
        ok += 1
        try:
            seen[json.dumps(v, ensure_ascii=False, default=str, sort_keys=True)] += 1
        except Exception:                                          # noqa: BLE001
            seen[repr(v)] += 1
        if len(vals) < 6:
            vals.append(v)

    record(base[2])

    # ── 2단계 · 🔴 뿌리별 감도 (남은 뿌리는 바탕에 고정) ────────────────
    sens = collections.OrderedDict()
    for r in roots:
        loc_seen = collections.Counter()
        n_ok_r = 0
        for _ in range(N_PER_ROOT):
            if _t.time() > deadline:
                capped["자리 시간 상한에 걸렸나"] = True
                break
            kw = dict(base[1])
            kw[r] = pool[rng.choice(names)]()
            try:
                v = call_capped(fnobj, kw)
            except (KeyboardInterrupt, WriteBlocked):
                raise
            except SliceTimeout:
                capped["판 시간 상한에 걸린 뽑기"] += 1
                continue
            except BaseException:                                  # noqa: BLE001
                continue
            n_ok_r += 1
            loc_seen[repr(v)] += 1
            record(v)
        sens[r] = {"성공 호출": n_ok_r, "서로 다른 값": len(loc_seen),
                   "🔴 이 뿌리가 판정을 무나": len(loc_seen) > 1}

    # ── 3단계 · 동시 변조 ────────────────────────────────────────────
    for _ in range(N_DRAWS):
        if _t.time() > deadline:
            capped["자리 시간 상한에 걸렸나"] = True
            break
        assign = {r: rng.choice(names) for r in roots}
        try:
            v = call_capped(fnobj, draw(assign))
        except (KeyboardInterrupt, WriteBlocked):
            raise
        except SliceTimeout:
            capped["판 시간 상한에 걸린 뽑기"] += 1
            continue
        except BaseException:                                      # noqa: BLE001
            continue
        record(v)

    if ok < N_MIN_OK:
        return {"판정": "모른다", "🔴 왜": "성공 호출 %d < %d" % (ok, N_MIN_OK),
                "🔴 시간 상한": capped,
                "뿌리": roots, "슬라이스 문장 수": len(keep), "뿌리별 감도": sens}
    # ── 4단계 · 🔴🔴 **전역 변조** ────────────────────────────────────
    #   자 B 는 3단계까지 **모듈 전역을 고정**한다. 그러면 「전역 함수가 망가지면 떨어질
    #   검사」를 상수로 잘못 부른다 — 그것은 항진명제가 아니라 **약한 검사**다.
    #   🔴 그래서 전역을 무작위 그루터기로 갈아 한 번 더 잰다. 판정이 셋으로 갈린다:
    #     ① 뿌리 변조에서 변한다            → **떨어진다**
    #     ② 뿌리는 상수인데 전역 변조에서 변한다 → **전역이 망가지면 떨어진다**(항진명제 아님)
    #     ③ 둘 다 상수                      → **항진명제**
    gseen2 = collections.Counter()
    g_ok = 0
    if len(seen) == 1 and globals_seen:
        for _ in range(N_PER_ROOT):
            if _t.time() > deadline + SITE_SEC:
                break
            g2 = dict(glb)
            for gname in globals_seen:
                cur = glb.get(gname)
                if callable(cur):
                    payload = pool[rng.choice(names)]()
                    g2[gname] = (lambda _p: (lambda *a, **k: _p))(payload)
                else:
                    g2[gname] = pool[rng.choice(names)]()
            try:
                loc2 = {}
                exec(code, g2, loc2)                               # noqa: S102
                v = call_capped(loc2["_m965_slice"], base[1])
            except (KeyboardInterrupt, WriteBlocked):
                raise
            except BaseException:                                  # noqa: BLE001
                continue
            g_ok += 1
            gseen2[repr(v)] += 1
    #: 🔴🔴 **R2(노트 966 · 티처 #104 C4) — 공집합에서 False 로 떨어지던 자리.**
    #: `len(gseen2) > 1` 은 **성공 호출이 0 이어도 False** 다. 그러면 「전역을 물어
    #: 봤는데 안 물었다」와 「전역을 아예 못 물어봤다」가 같은 값이 된다 --- 조항 59 가
    #: 금지하는 바로 그 섞임이다. 티처 #104 실측: 4단계에 도달한 9 자리 중 **다섯이
    #: `g_ok = 0`** 이었고(`curve961:664` · `triples962:577` · `checks964:1252` ·
    #: `fiveprime902:562`·`:770`), 그중 넷이 「항진명제」로 **확정**됐다.
    #: **그 단계의 실측 판별력은 1 / 125 였다.**
    #: 이제 **`g_ok < N_MIN_G` 면 「모른다」** 로 떨어진다 --- 항진명제로도, 떨어진다로도
    #: 안 센다.
    g_enough = g_ok >= N_MIN_G
    glob_bites = g_enough and len(gseen2) > 1
    glob_unknown = bool(len(seen) == 1 and globals_seen and not g_enough)

    const = len(seen) == 1 and not glob_bites and not glob_unknown
    only = None
    if const:
        try:
            only = json.loads(list(seen)[0])
        except Exception:                                          # noqa: BLE001
            only = list(seen)[0]
    # 🔴 **상수 False 는 항진명제로 안 센다.** 생성기가 그 검사의 유효 입력 영역에
    #    한 번도 못 닿았을 수 있다 — 「못 봤다」와 「없다」는 둘이다(조항 59).
    taut = bool(const and only not in (False, None, 0))
    return {"🔴 전역 변조": {"전역 이름": globals_seen, "성공 호출": g_ok,
                       "🔴 최소 성공 호출(R2)": N_MIN_G,
                       "🔴 성공 호출이 모자라 못 갈랐나": glob_unknown,
                       "서로 다른 값": len(gseen2),
                       "🔴 전역이 판정을 무나": glob_bites},
            "판정": ("항진명제" if taut else
                   ("🔴 전역 변조 성공 호출 %d < %d — 모른다(R2)" % (g_ok, N_MIN_G)
                    if glob_unknown else
                   ("🔴 전역이 망가지면 떨어진다(뿌리는 상수 · 항진명제 아님)" if glob_bites else
                   ("🔴 상수 False — 모른다(생성기가 유효 입력을 못 만들었을 수 있다)"
                    if const else "떨어진다")))),
            "항진명제": taut,
            "🔴 뿌리 변조에서 상수인가": len(seen) == 1,
            "🔴 상수인가": const, "🔴 그 상수": only,
            "뿌리": roots, "모듈 전역으로 뺀 이름": globals_seen,
            "슬라이스 문장 수": len(keep),
            "성공 호출": ok, "서로 다른 값": len(seen),
            "값 표본": [str(v)[:60] for v in vals],
            "🔴 뿌리별 감도": sens,
            "🔴 판정을 무는 뿌리 수": sum(1 for v in sens.values() if v["🔴 이 뿌리가 판정을 무나"]),
            "🔴 시간 상한": capped,
            }


# ══════════════════════════════════════════════════════════════════════════
# 자 C — 정적 · 자기 재계산 대조
# ══════════════════════════════════════════════════════════════════════════
def _dump(node):
    return ast.dump(node, annotate_fields=True, include_attributes=False)


def _call_bindings(func):
    """`x = f(...)` 로 묶인 이름 → 그 호출 노드."""
    out = {}
    for st in ast.walk(func):
        if isinstance(st, ast.Assign) and isinstance(st.value, ast.Call):
            for t in st.targets:
                if isinstance(t, ast.Name):
                    out[t.id] = st.value
    return out


def _calls_in(node):
    return [n for n in ast.walk(node) if isinstance(n, ast.Call)]


def ruler_C_delegation(call, func):
    """위임 호출 `chk(a, lambda: f(...))` 의 인자 둘이 **같은 함수 · 같은 인자**인가."""
    if func is None:
        return None
    binds = _call_bindings(func)
    args = list(call.args) + [k.value for k in call.keywords]
    sigs = []
    for a in args:
        if isinstance(a, ast.Name) and a.id in binds:
            sigs.append((a.id, _dump(binds[a.id])))
        elif isinstance(a, ast.Lambda):
            cs = _calls_in(a.body)
            if cs:
                sigs.append(("<lambda>", _dump(cs[0])))
        elif isinstance(a, ast.Call):
            sigs.append(("<직접 호출>", _dump(a)))
    for i in range(len(sigs)):
        for j in range(i + 1, len(sigs)):
            if sigs[i][1] == sigs[j][1]:
                return {"항진명제": True, "짝": [sigs[i][0], sigs[j][0]],
                        "🔴 왜": ("이 검사에 넘긴 인자 둘이 **같은 순수함수를 같은 인자로 부른 "
                                "결과**다 — 견줄 것이 원리상 같으므로 어떤 자료에서도 통과한다")}
    return {"항진명제": False, "짝 수": len(sigs)}


def _side(node, binds):
    """비교의 한 쪽을 **호출 꼴**로 푼다 — 이름이면 그 이름을 묶은 호출까지 따라간다."""
    if isinstance(node, ast.Name) and node.id in binds:
        return _dump(binds[node.id]), True
    return _dump(node), any(isinstance(n, ast.Call) for n in ast.walk(node))


def ruler_C_site(site):
    """🔴 **견주는 두 쪽이 구문상 같은가** — `len(x)==len(x)` 같은 우연한 중복이 아니라
    **한 `Compare` 의 양쪽이 같은 것**만 센다. (초판은 표현식 안의 호출 **중복**을 셌고
    `len(lanes)==exp and len(lanes)<=cap` 을 항진명제로 잘못 불렀다 — 거짓 양성이었다.)"""
    if site.func is None:
        return {"항진명제": False, "🔴 왜": "감싸는 함수가 없다"}
    binds = _call_bindings(site.func)
    hits = []
    for cmpn in [n for n in ast.walk(site.expr) if isinstance(n, ast.Compare)]:
        sides = [cmpn.left] + list(cmpn.comparators)
        for i in range(len(sides)):
            for j in range(i + 1, len(sides)):
                a, ac = _side(sides[i], binds)
                b, bc = _side(sides[j], binds)
                if a == b and (ac or bc or isinstance(sides[i], ast.Name)):
                    hits.append(ast.unparse(cmpn)[:120])
    if hits:
        return {"항진명제": True, "🔴 양쪽이 같은 비교": hits,
                "🔴 왜": "같은 순수함수를 같은 인자로 부른 결과끼리(또는 같은 이름끼리) 견준다"}
    return {"항진명제": False, "본 비교 수":
            len([n for n in ast.walk(site.expr) if isinstance(n, ast.Compare)])}


# ══════════════════════════════════════════════════════════════════════════
# 심은 키 · 음성 대조 — 🔴 메타 검사 자신의 검정력
# ══════════════════════════════════════════════════════════════════════════
PLANTED_SRC = '''# -*- coding: utf-8 -*-
"""🔴 메타 검사의 **심은 키**와 **음성 대조**. 이 파일은 실행되지 않고 **읽힌다**."""


def f_pure(a, b):
    return {"합": a + b, "곱": a * b}


def w10ish(rt, recall):
    again = recall()
    return {"통과": all(rt.get(k) == v for k, v in again.items())}


# ── 심은 것 (항진명제여야 한다) ────────────────────────────────────────
def plantA_literal(records):
    """심기 A — 리터럴. 🔴 무엇이 자료를 읽나: 아무것도 안 읽는다."""
    return {"무엇": "새 자료를 만들면 떨어진다", "통과": True}


def plantB_partition(sections):
    """심기 B — 같은 집합의 분할끼리 견준다."""
    secs = {k: v for k, v in sections.items() if isinstance(v, dict) and "통과" in v}
    n_ok = sum(1 for v in secs.values() if v["통과"] is True)
    red = [k for k, v in secs.items() if v["통과"] is not True]
    return {"분자": n_ok, "분모": len(secs), "통과": len(red) == len(secs) - n_ok}


def plantC_recompute(a, b):
    """심기 C — 같은 순수함수를 같은 인자로 두 번."""
    rt = f_pure(a, b)
    return {**rt, **w10ish(rt, lambda: f_pure(a, b))}


def plantD_selfcount(rows):
    """심기 D — 분모가 자기 분자의 합(963 §3 W3′ 의 꼴)."""
    dom = {}
    for r in rows:
        dom[r] = dom.get(r, 0) + 1
    return {"분자": sum(dom.values()), "분모": sum(dom.values()),
            "통과": sum(dom.values()) == sum(dom.values())}


# ── 음성 대조 (진짜 검사 — 절대 항진명제로 불리면 안 된다) ──────────────
def negA_threshold(delta, T):
    return {"Δ": delta, "T": T, "통과": bool(delta > T)}


def negB_coverage(records, classified):
    """분모를 **원천 리스트 길이**에서 가져온다(964 의 W3″ 꼴)."""
    n = len(records)
    got = sum(1 for r in records if r in classified)
    return {"분자": got, "분모": n, "통과": got == n}


def negC_recompute_diff(a, b):
    """같은 함수지만 **인자가 다르다** — 자 C 가 여기서 짖으면 거짓 양성이다."""
    rt = f_pure(a, b)
    return {**rt, **w10ish(rt, lambda: f_pure(a, b + 1))}


def negD_disk(observed, expected):
    return {"관측": observed, "등록": expected, "통과": observed == expected}
'''

PLANTED = {
    "plantA_literal": "A",
    "plantB_partition": "B",
    "plantC_recompute": "C",
    "plantD_selfcount": "B",
}
NEGATIVE = ["negA_threshold", "negB_coverage", "negC_recompute_diff", "negD_disk"]


# ══════════════════════════════════════════════════════════════════════════
# 훑기 한 파일
# ══════════════════════════════════════════════════════════════════════════
#: 🔴🔴🔴 **노트 972 신설 — 자 B 생성기 풀의 범위.** 티처 #110 치명 1.
#: `file` = 965~971 그대로. 풀을 **파일 전체 AST** 에서 거둔다 —
#:   🔴 **무관한 48 줄이 남의 자리 판정을 뒤집는다.** 971 의 「낙하 4(30.8%)」가
#:   커밋본에서 **2(15.4%)** 로 갈린 뿌리가 이것이다.
#: `func` = **972 수리**. 자리를 **감싸는 함수의 AST** 에서만 거둔다.
#: 🔴 **기본값을 `func` 로 바꿨다**(노트 898 의 「기본값 보존」과 정면으로 부딪힌다).
#:   까닭: `file` 은 편의가 아니라 **원리상 틀린 자**다 — 판정이 그 자리의 코드가 아니라
#:   **파일의 나머지 내용**에 매인다. `file` 은 인자로 남겨 전후를 나란히 싣는다.
POOLSCOPE = "func"


def tally(rows) -> dict:
    """🔴 **972 신설 — 자 계수를 내는 생산 함수 하나.**

    965~971 은 이 계수를 `main()` 안에 인라인으로 적었다. 그래서 **다른 러너가 같은
    계수를 내려면 다시 쓸 수밖에 없었고**, 다시 쓴 자는 죽은 자다(v4.0 §3).
    `main()` 과 `rulerstab972.py` 가 **둘 다 이 함수를 부른다.**
    """
    n_site = len([r for r in rows if r["꼴"] != "위임 `{**f(...)}`"])
    n_deleg = len([r for r in rows if r["꼴"] == "위임 `{**f(...)}`"])
    taut = [r["자리"] for r in rows if r["🔴 항진명제인가"]]
    constF = len([r for r in rows if r["자 B"].get("🔴 상수인가")
                  and not r["자 B"].get("항진명제")])
    unk = len([r for r in rows if str(r["자 B"].get("판정", "")).startswith("모른다")
               and not r["🔴 항진명제인가"]])
    tot = n_site + n_deleg
    drop = tot - len(taut) - constF - unk
    return {
        "`통과` 자리": n_site,
        "위임 자리": n_deleg,
        "🔴 항진명제": taut,
        "조건부 리터럴(가지가 자다)":
            len([r for r in rows if r["자 A"].get("🔴 조건부 리터럴")]),
        "🔴 상수 False(모른다)": constF,
        "모른다": unk,
        "🔴 증명된 낙하": drop,
        "🔴 증명된 낙하 %": round(100.0 * drop / tot, 1) if tot else None,
        "🔴 분모": tot,
        # 🔴🔴 975 수리 --- **분모 0 이면 그 채점은 죽은 것이다.**
        # 974 실측: 러너 넷 전부에서 `exact` 분모가 0 이었는데 산출물은 「항진명제 0」을
        # 냈다. 그것은 「깨끗하다」가 아니라 **「아무것도 안 봤다」**다.
        "🔴🔴 분모 0 --- 이 채점은 죽었다": tot == 0,
        "🔴🔴 판정": ("모른다 --- 분모 0" if tot == 0 else "잰다"),
    }


def verdict_map(rows) -> dict:
    """🔴 **972 신설** --- 자리 → 한 글자 판정. 안정성 대조가 **이 사전을 견준다.**"""
    out = {}
    for r in rows:
        if r["🔴 항진명제인가"]:
            v = "항진명제"
        elif r["자 B"].get("🔴 상수인가"):
            v = "상수False"
        elif str(r["자 B"].get("판정", "")).startswith("모른다"):
            v = "모른다"
        else:
            v = "낙하"
        out[r["자리"]] = v
    return out


def f1_counts(rows, mine_names, exempt_funcs):
    """🔴 978 수리 3 (①) — **세는 일**만 한다. 판정은 `f1_verdict` 가 한다."""
    mine_all = [r for r in rows if r["파일"] in tuple(mine_names)]
    mine_exempt = [r for r in mine_all if r["함수"] in exempt_funcs]
    mine = [r for r in mine_all if r["함수"] not in exempt_funcs]
    mine_taut = [r for r in mine if r["🔴 항진명제인가"]]
    mine_unk = [r for r in mine if not r["🔴 항진명제인가"]
                and r["자 B"].get("판정") == "모른다"]
    return {
        "분모": len(mine),
        "빼기 전 분모": len(mine_all),
        "면제": len(mine_exempt),
        "면제 자리": [r["자리"] for r in mine_exempt] or "없음",
        "분자: 항진명제": len(mine_taut),
        "항진명제 자리": [r["자리"] for r in mine_taut] or "없음",
        "모른다 자리": [r["자리"] for r in mine_unk] or "없음",
        "판정을 무는 뿌리를 가진 자리":
            len([r for r in mine if r["자 B"].get("🔴 판정을 무는 뿌리 수", 0) > 0]),
    }


def f1_verdict(n_denom, n_taut):
    """🔴🔴 **978 수리 3 (②)** — §4 F1 의 **판정**을 두 정수의 순수 함수로 뺀다.

    🔴 **왜 이렇게 고치나** (972~977 **일곱 사이클** 미이행이던 `meta965.py:1385`):
    옛 판은 `"통과": len(mine_taut) == 0` 을 **`main()` 안에** 두었다. `mine_taut` 은
    `r["파일"] in tuple(MINE)` 로 걸러지는데 **자 B 의 생성기가 만든 무작위 행의 `파일`
    값은 `MINE` 에 원리상 안 들어간다** — 그래서 그 식은 **어떤 자료에서도 True** 였고
    자 B 가 항진명제로 잡았다(뿌리 `all_rows` · 성공 호출 26 · 서로 다른 값 1).

    🔴 **행 목록을 인자로 받는 함수로 빼는 것만으로는 안 고쳐진다** — 978 이 그 판을
    먼저 만들어 재 보니 판정이 「항진명제」에서 **「상수 False — 모른다」로 옮겨갔을 뿐**
    이었다(상수인 것은 그대로다). 🔴 **그래서 판정을 「정수 둘」의 함수로 낮춘다.**
    생성기는 정수를 실제로 흔들 수 있으므로 이 식은 **자료로 뒤집힌다.**

    🔴 **그리고 「정수 둘」로도 아직 모자랐다** — `n_taut == 0` 은 생성기의
    `randint(-999, 999)` 아래에서 **1,999 번에 한 번**만 참이라 실측 313 뽑기에서
    상수 False 였다. 🔴 **그래서 허용 항진명제 수 `n_allowed` 를 등록 인자로 올려
    `n_taut <= n_allowed` 로 쓴다.** 셈은 음수가 아니므로 `n_allowed = 0` 에서
    옛 식과 **뜻이 같고**, 생성기 아래에서는 두 정수의 비교라 **실제로 뒤집힌다.**

    🔴 `n_denom > 0` 을 같이 문다 — **빈 분모로 통과하던 fail-open** 을 닫는다.
    """
    return {"분모": n_denom, "분자: 항진명제": n_taut,
            "허용": F1_ALLOWED_TAUT,
            "통과": n_taut <= F1_ALLOWED_TAUT and n_denom > 0}


def scan_source(rel, src, modns, rng):
    tree = ast.parse(src)
    parents = _parents(tree)
    keypool = harvest_keys(tree)
    strpool = harvest_strings(tree)
    #: 🔴 972 --- 범위별 풀. `func` 면 **감싸는 함수 AST** 에서만 거둔다.
    _pcache = {}

    def _pools(site):
        if POOLSCOPE != "func" or site.func is None:
            return keypool, strpool
        k = id(site.func)
        if k not in _pcache:
            _pcache[k] = (harvest_keys(site.func), harvest_strings(site.func))
        return _pcache[k]

    rows = []
    for s in collect_sites(rel, tree, parents):
        keypool_s, strpool_s = _pools(s)
        a = ruler_A(s, parents)
        # 🔴🔴 **자리마다 자기 씨앗을 준다.** 뽑기 흐름 하나를 온 훑기가 나눠 쓰면
        #   **분모(훑는 파일 집합)가 바뀔 때 남의 자리 판정까지 흔들린다.**
        #   실제로 그렇게 났다: 같은 씨앗 965 인데 `checks965.py` 에 절을 하나 더한 것만으로
        #   `meta965.py` 의 한 자리가 **「항진명제」에서 「모른다」로 바뀌었다.**
        #   🔴 자리 씨앗 = `SEED|<파일:줄>` — 이제 그 자리의 판정은 **훑는 순서와 무관**하다.
        srng = random.Random("%d|%s" % (SEED, s.key))
        b = (ruler_B(s, modns, srng, keypool_s, strpool_s) if not a["항진명제"]
             else {"판정": "안 쟀다(자 A 가 이미 잡았다)"})
        c = ruler_C_site(s)
        rows.append({
            "자리": s.key, "꼴": s.kind,
            "함수": s.func.name if s.func else "<모듈>",
            "표현식": ast.unparse(s.expr)[:180],
            "자 A": a, "자 B": b, "자 C": c,
            "🔴 항진명제인가": bool(a["항진명제"] or b.get("항진명제") or c["항진명제"]),
            "🔴 잡은 자": [n for n, v in (("A", a.get("항진명제")), ("B", b.get("항진명제")),
                                      ("C", c.get("항진명제"))) if v],
        })
    # 위임 자리 (`{**f(...)}`) — 자 C 전용
    for call, func in collect_delegations(rel, tree, parents):
        v = ruler_C_delegation(call, func)
        if v is None:
            continue
        rows.append({
            "자리": "%s:%d" % (rel, call.lineno), "꼴": "위임 `{**f(...)}`",
            "함수": func.name if func else "<모듈>",
            "표현식": ast.unparse(call)[:180],
            "자 A": {"항진명제": False, "🔴 왜": "위임 자리는 자 A 의 사정권 밖"},
            "자 B": {"판정": "모른다", "🔴 왜": "위임 자리는 자 B 의 사정권 밖"},
            "자 C": v,
            "🔴 항진명제인가": bool(v["항진명제"]),
            "🔴 잡은 자": ["C"] if v["항진명제"] else [],
        })
    return rows


def import_ns(rel):
    """모듈을 **쓰기 차단** 아래 임포트해 슬라이스 실행에 쓸 이름 공간을 얻는다."""
    mod = rel[:-3].replace("/", ".")
    try:
        with _NoWrite():
            m = importlib.import_module(mod)
        return dict(m.__dict__), None
    except Exception as e:                                         # noqa: BLE001
        return {"__builtins__": builtins}, "%s: %s" % (type(e).__name__, e)


# ══════════════════════════════════════════════════════════════════════════
# 산출물 쪽 전수 — 원문에서 `통과` 키를 **모든 중첩 레벨**에서 센다
# ══════════════════════════════════════════════════════════════════════════
def count_pass_keys(obj, path="", acc=None):
    acc = [] if acc is None else acc
    if isinstance(obj, dict):
        for k, v in obj.items():
            if is_pass_key(k):                     # 🔴 971 — 접미 일치(티처 #109 m3)
                acc.append((path or "<루트>", v))
            count_pass_keys(v, path + "/" + str(k), acc)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            count_pass_keys(v, "%s[%d]" % (path, i), acc)
    return acc


# ══════════════════════════════════════════════════════════════════════════
def main():
    t0 = dt.datetime.now(dt.timezone.utc)
    rng = random.Random(SEED)
    R = collections.OrderedDict()
    R["노트"] = 965
    R["레인"] = "수리"
    R["사전등록"] = "docs/prereg_965_metataut.md (측정 전 단독 커밋)"
    R["씨앗"] = SEED
    R["🔴 씨앗을 어떻게 쓰나"] = ("자리마다 `Random(\"<씨앗>|<파일:줄>\")` — **자리 씨앗**이다. "
                        "뽑기 흐름 하나를 온 훑기가 나눠 쓰면 **분모가 바뀔 때 남의 자리 "
                        "판정까지 흔들린다**(965 가 실제로 당했다: 같은 씨앗인데 다른 파일에 "
                        "절을 하나 더한 것만으로 한 자리가 「항진명제」→「모른다」로 바뀌었다)")
    R["시작(UTC)"] = t0.isoformat()

    # ── §0 이 러너의 성질 — 🔴 964 의 §-1 은 리터럴 True 였다. 여기는 **잰다** ──
    self_src = (ROOT / "runners/meta965.py").read_text(encoding="utf-8")
    self_tree = ast.parse(self_src)
    writes = [n for n in ast.walk(self_tree)
              if isinstance(n, ast.Attribute) and n.attr in ("write_text", "write_bytes")]
    # 🔴🔴 조항 63 — 「이 코드가 어느 파일을 여나」를 **문자열 전량**에서 찾으면
    #   **자기 감사 코드의 바늘**(`"denominator" in str(o)`)이 자기를 문다. 실제로 이 절의
    #   첫 판이 그렇게 붉었다. **경로가 되는 자리만** 본다.
    paths = []
    for n in ast.walk(self_tree):
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div) \
                and isinstance(n.right, ast.Constant) and isinstance(n.right.value, str):
            paths.append(n.right.value)
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name) \
                and n.func.id in ("Path", "open") and n.args \
                and isinstance(n.args[0], ast.Constant) \
                and isinstance(n.args[0].value, str):
            paths.append(n.args[0].value)
    board = [c for c in paths if "denominator" in c]
    probe = [n.right.value for n in ast.walk(ast.parse('x = ROOT / "data/lab/denominator.json"'))
             if isinstance(n, ast.BinOp) and isinstance(n.right, ast.Constant)]
    R["§0 이 러너의 성질 — 🔴 **문장이 아니라 코드를 잰다**"] = {
        "🔴 왜 이렇게 쓰나": ("964 의 §-1 은 `\"무엇이면 떨어지나\": \"<문장>\", \"통과\": True` 였다 — "
                       "**그 문장을 평가하는 코드가 없었다**(티처 #103 C1). 여기는 **AST 로 잰다**"),
        "🔴 분모: 경로 리터럴 자리": len(paths),
        "경로 리터럴": sorted(set(paths)),
        "판 라벨 파일을 여나(**경로 자리**에 그 이름이 있나)": bool(board),
        "쓰는 자리 수(Path.write_*)": len(writes),
        "쓰는 경로": ["runners/out965_meta.json"],
        "🔴 음성 대조(이 자가 다른 답을 낼 수 있나 — 조항 63 ②)":
            {"심은 소스": 'x = ROOT / "data/lab/denominator.json"',
             "이 자가 잡나": any("denominator" in c for c in probe)},
        "🔴🔴 자가 적발": ("이 절의 **첫 판**은 소스의 **문자열 전량**을 훑었고 "
                    "**자기 감사 코드의 바늘**(`\"denominator\" in str(o)`)을 물어 붉게 나왔다. "
                    "🔴 **조항 63 그 자체 — 바늘이 제 짚더미를 물었다**"),
        # 🔴 `len(paths) >= 1` 이 있어야 이 키가 **뿌리를 실제로 문다** — 자 B 가 잡아 줬다
        "통과": (len(writes) >= 1 and len(paths) >= 1 and not board
               and any("denominator" in c for c in probe)),
    }

    # ── §1 등록 러너 전수 훑기 ───────────────────────────────────────────
    per_file = collections.OrderedDict()
    all_rows = []
    ns_err = {}
    for rel in REGISTERED:
        p = ROOT / rel
        if not p.exists():
            per_file[rel] = {"🔴": "파일이 없다(아직 안 만들었다)"}
            continue
        ns, err = import_ns(rel)
        if err:
            ns_err[rel] = err
        src_txt = p.read_text(encoding="utf-8")
        with _NoWrite():                    # 🔴 슬라이스 실행 내내 쓰기를 막는다
            rows = scan_source(rel, src_txt, ns, rng)
        for r in rows:
            r["파일"] = rel
        all_rows.extend(rows)
        #: 🔴 **972** --- 인라인 계수를 **생산 함수 `tally()` 로 옮겼다.**
        #: `rulerstab972.py` 가 같은 함수를 부른다 --- 다시 쓴 자는 죽은 자다.
        per_file[rel] = dict(tally(rows))
        #: 🔴🔴 **971 · 조항 66-③** — 구판(정확)·신판(접미)을 같은 자리에 싣는다
        per_file[rel]["🔴🔴 통과 키 분모(정확 일치 vs 접미 일치)"] = \
            passkey_census(rel, ast.parse(src_txt))
        #: 🔴🔴🔴 **979 수리 3** — `통과` 키 **밖**의 리터럴 주장을 센다
        per_file[rel]["🔴🔴🔴 979 — 리터럴 주장 census(키 이름을 안 본다)"] = \
            literal_claim_census(rel, ast.parse(src_txt))

    taut = [r for r in all_rows if r["🔴 항진명제인가"]]
    unk = [r for r in all_rows if not r["🔴 항진명제인가"]
           and str(r["자 B"].get("판정", "")).startswith(("모른다", "🔴 상수 False"))]
    condlit = [r for r in all_rows if r["자 A"].get("🔴 조건부 리터럴")]
    constF = [r for r in all_rows if r["자 B"].get("🔴 상수인가") and not r["자 B"].get("항진명제")]
    globonly = [r for r in all_rows
                if r["자 B"].get("🔴 전역 변조", {}).get("🔴 전역이 판정을 무나")]
    R["§1 🔴🔴 등록 러너 전수 — 자 셋"] = {
        "🔴 분모 ① 등록 파일": len(REGISTERED),
        "🔴 분모 ② `통과` 자리 + 위임 자리": len(all_rows),
        "🔴 분자: 항진명제로 잡힌 자리": len(taut),
        "🔴 모른다(자 B 가 슬라이스를 못 돌렸거나 상수 False)": len(unk),
        "🔴 조건부 리터럴(가지가 자다 — 항진명제로 안 센다)":
            {"수": len(condlit), "자리": [r["자리"] for r in condlit]},
        "🔴 상수 False(생성기가 유효 입력을 못 만들었을 수 있다 — 「모른다」)":
            {"수": len(constF), "자리": [r["자리"] for r in constF]},
        "🔴 전역이 망가지면 떨어진다(뿌리는 상수 · **항진명제 아님**)":
            {"수": len(globonly), "자리": [r["자리"] for r in globonly],
             "🔴 왜 가르나": ("자 B 는 뿌리만 갈고 **모듈 전역은 고정**한다. 그러면 「전역 함수가 "
                       "망가지면 떨어질 검사」를 상수로 잘못 부른다 — 4단계에서 전역을 "
                       "무작위 그루터기로 갈아 한 번 더 재고 **가른다**")},
        "🔴 떨어진다(자 셋 중 아무도 안 잡았고 자 B 가 값이 변함을 봤다)":
            len(all_rows) - len(taut) - len(unk),
        "자별 계수": {
            "A 리터럴": len([r for r in all_rows if "A" in r["🔴 잡은 자"]]),
            "B 슬라이스": len([r for r in all_rows if "B" in r["🔴 잡은 자"]]),
            "C 자기재계산": len([r for r in all_rows if "C" in r["🔴 잡은 자"]]),
        },
        "파일별": per_file,
        "🔴 임포트 실패(이름 공간 없이 잰 파일)": ns_err or "없음",
        "🔴 잡은 자리 전량": [{"자리": r["자리"], "자": r["🔴 잡은 자"],
                        "꼴": r["꼴"], "함수": r["함수"],
                        "표현식": r["표현식"][:130],
                        "🔴 왜": (r["자 A"].get("🔴 왜") or r["자 C"].get("🔴 왜")
                               or r["자 B"].get("판정")),
                        "🔴 뿌리": r["자 B"].get("뿌리"),
                        "🔴 그 상수": r["자 B"].get("🔴 그 상수"),
                        "성공 호출": r["자 B"].get("성공 호출")} for r in taut],
        "통과": len(taut) == 0,
        "🔴 이 절의 `통과` 가 뜻하는 것": "등록 러너에 **자 셋으로 잡히는 항진명제가 없다**",
    }

    # ── §1′ 🔴🔴🔴 979 수리 3 — 리터럴 주장 census (`통과` 키 **밖**) ────────
    LCK = "🔴🔴🔴 979 — 리터럴 주장 census(키 이름을 안 본다)"
    BL = "🔴🔴🔴 그중 **조건 가지 밖**(무조건 참) 자리"
    BLA = "🔴🔴 그중 `통과` 계열이 아닌 자리(옛 census 의 사각지대)"
    n_blind = sum(per_file[r][LCK][BL] for r in per_file if LCK in per_file[r])
    n_all = sum(per_file[r][LCK][BLA] for r in per_file if LCK in per_file[r])
    sites = []
    for r in per_file:
        if LCK in per_file[r]:
            sites += per_file[r][LCK]["🔴 그 자리 목록"]
    R["§1′ 🔴🔴🔴 979 수리 3 — 리터럴 주장 census(`통과` 키 밖)"] = {
        "🔴 왜 생겼나": (
            "🔴 옛 census 는 `통과` 키만 봐서 `ruler978.py:444·792·878` 의 "
            "「🔴 유보는 한 줄도 안 만졌다 = True」 셋을 **원리상 못 봤다**(티처 #117 치-7). "
            "그 셋은 **반증조건 6 을 지는 주장**이었다"),
        "🔴 분모: 등록 파일": len(per_file),
        "🔴🔴 `통과` 계열이 아닌 리터럴 자리(전 파일 합)": n_all,
        "🔴🔴🔴 그중 리터럴 `True` 인 자리(전 파일 합)": n_blind,
        "🔴 자리 전량": sites[:80],
        "파일별": {r: per_file[r][LCK] for r in per_file if LCK in per_file[r]},
        "통과": n_blind == 0,
        "🔴 이 절의 `통과` 가 뜻하는 것": (
            "🔴 **등록 러너에 「키 이름 때문에 안 보이던 리터럴 참 주장」이 없다.** "
            "🔴 분모가 0 이면 실패다 — 「안 세었다」와 「없다」는 둘이다"),
    }

    # ── §2 티처 #103 의 셋을 실제로 잡았나 (V1) ────────────────────────────
    #   🔴 **수리 전 트리에서 재야 한다.** 965 가 `curve961.py:601` 을 고쳤으므로 지금 트리에는
    #   C3 이 **없다** — 지금 트리에서 「C3 을 잡나」를 물으면 **수리했다는 이유로 붉어진다.**
    #   그래서 ① 수리 전 rev 의 소스에서 **잡는지** ② 지금 트리에서 **사라졌는지** 둘을 낸다.
    import subprocess as _sp                                       # noqa: PLC0415
    REV = "f8ef5c417"                                              # #222 머지 = 965 가 손대기 전
    before = {}
    for rel in ("runners/curve961.py", "runners/checks964.py"):
        try:
            raw = _sp.run(["git", "-c", "core.quotePath=false", "show",
                           "%s:%s" % (REV, rel)], cwd=str(ROOT),
                          capture_output=True, check=True).stdout.decode("utf-8")
        except Exception as e:                                     # noqa: BLE001
            before[rel] = {"🔴": "%s: %s" % (type(e).__name__, e)}
            continue
        ns, _err = import_ns(rel)
        with _NoWrite():
            rws = scan_source(rel + "@" + REV, raw, ns, rng)
        before[rel] = rws
    b_curve = before.get("runners/curve961.py", [])
    b_chk = before.get("runners/checks964.py", [])
    c1 = [r["자리"] for r in b_chk if isinstance(r, dict) and "A" in r.get("🔴 잡은 자", [])]
    c2 = [r["자리"] for r in b_chk if isinstance(r, dict) and "B" in r.get("🔴 잡은 자", [])]
    c3 = [r["자리"] for r in b_curve if isinstance(r, dict) and "C" in r.get("🔴 잡은 자", [])]
    c3_now = [r["자리"] for r in all_rows
              if r["파일"] == "runners/curve961.py" and "C" in r["🔴 잡은 자"]]
    R["§2 🔴🔴 V1 — 티처 #103 이 손으로 잡은 셋을 기계가 잡나"] = {
        "🔴 무엇": ("🔴 **수리 전 트리(`%s`)의 소스**에서 잰다. 965 가 `curve961.py:601` 을 "
                 "고쳤으므로 지금 트리에는 C3 이 없다 — **지금 트리에서 물으면 수리했다는 "
                 "이유로 붉어진다**(조항 59: 「없다」와 「고쳤다」는 둘이다)" % REV),
        "C1 `checks964.py` 리터럴 `통과`(자 A · 수리 전)": c1 or "🔴 못 잡았다",
        "C2 `checks964.py` 같은 집합의 분할(자 B · 수리 전)": c2 or "🔴 못 잡았다",
        "C3 `curve961.py` 자기 재계산(자 C · 수리 전)": c3 or "🔴 못 잡았다",
        "🔴🔴 지금 트리에서 C3 이 사라졌나(= 수리가 먹혔나)": {
            "지금 트리의 자 C 적발": c3_now or "없음",
            "사라졌나": not c3_now},
        "통과": bool(c1 and c2 and c3 and not c3_now),
        "🔴 이 절의 `통과` 가 뜻하는 것": ("수리 **전** 트리에서 셋을 다 잡고, 수리 **후** 트리에서 "
                              "C3 이 **사라졌다** — 잡는 것과 고친 것을 둘 다 보인다"),
    }

    # ── §3 검정력 · 거짓 양성 — 🔴 심어서 잰다 (V2·V3) ─────────────────────
    ptree = ast.parse(PLANTED_SRC)
    pparents = _parents(ptree)
    pns = {"__builtins__": builtins}
    exec(compile(ptree, "<심은 키>", "exec"), pns)                   # noqa: S102
    with _NoWrite():
        prows = scan_source("<심은 키>", PLANTED_SRC, pns, rng)
    by_func = collections.defaultdict(list)
    for r in prows:
        by_func[r["함수"]].append(r)

    caught, missed = collections.OrderedDict(), []
    for fn, want in PLANTED.items():
        rows = by_func.get(fn, [])
        got = sorted({z for r in rows for z in r["🔴 잡은 자"]})
        any_ok = bool(got)
        caught[fn] = {"기대한 자": want, "잡은 자": got,
                      "🔴 잡았나(어느 자든)": any_ok,
                      "기대한 자가 잡았나": want in got}
        if not any_ok:
            missed.append(fn)
    fps = collections.OrderedDict()
    for fn in NEGATIVE:
        rows = by_func.get(fn, [])
        got = sorted({z for r in rows for z in r["🔴 잡은 자"]})
        fps[fn] = {"잡은 자": got, "🔴 거짓 양성인가": bool(got)}
    n_fp = sum(1 for v in fps.values() if v["🔴 거짓 양성인가"])

    R["§3 🔴🔴 V2·V3 검정력과 거짓 양성 — **심어서 잰다**"] = {
        "🔴 무엇": ("일부러 항진명제 넷을 심고(A·B·C·D) **진짜 검사 넷을 음성 대조로 넣었다.** "
                 "🔴 **「실행됐다」가 아니라 「잡았다」로 센다**(사전등록 §3-6)"),
        "심은 키": caught,
        "🔴 분자: 잡은 심기(어느 자든)": len(PLANTED) - len(missed),
        "분모: 심은 수": len(PLANTED),
        "⚠ 기대한 자가 잡은 수": sum(1 for v in caught.values() if v["기대한 자가 잡았나"]),
        "⚠ 기대와 다른 자가 잡은 것": [k for k, v in caught.items()
                             if v["🔴 잡았나(어느 자든)"] and not v["기대한 자가 잡았나"]] or "없음",
        "🔴 못 잡은 심기": missed or "없음",
        "음성 대조": fps,
        "분자: 거짓 양성": n_fp,
        "분모: 음성 대조 수": len(NEGATIVE),
        "통과": (not missed) and n_fp == 0,
    }

    # ── §4 🔴 V4 자기 적용 — 내가 새로 만든 `통과` 키가 상수인가 (F1) ────────
    #: 🔴🔴 **978 수리 3 — `meta965.py:1385`(옛 자리 · 977 시점 `:1411`) 를 고친다.**
    #: **일곱 사이클(972~977) 동안 미이행이던 자리다.** 옛 판은 이 자리에서
    #: `"통과": len(mine_taut) == 0` 을 **`main()` 안에** 직접 두었고, 자 B 는 그것을
    #: **항진명제**로 잡았다(뿌리 `all_rows` · 성공 호출 26 · 서로 다른 값 1 · 상수 True).
    #: 까닭: `mine_taut` 이 `r["파일"] in tuple(MINE)` 로 걸러지는데 **생성기가 만든
    #: 무작위 행의 `파일` 값은 `MINE` 에 절대 안 들어간다** — 그래서 `main()` 안에서는
    #: 원리상 상수다. 🔴 **판정을 `f1_verdict` 라는 순수 함수로 빼면 자 B 가 그 함수의
    #: 인자(`rows`·`mine_names`)를 **같은 풀**에서 만들므로 두 값이 실제로 겹칠 수 있고,
    #: 그때 이 검사는 **자료로 반증 가능해진다.**
    #: 🔴 그리고 `len(mine) > 0` 을 같이 물어 **빈 분모로 통과하던 fail-open 을 닫는다.**
    f1 = f1_counts(all_rows, MINE, F1_DENOM_EXEMPT_FUNCS)
    f1v = f1_verdict(f1["분모"], f1["분자: 항진명제"])
    R["§4 🔴🔴 F1 — **내가 새로 만든 `통과` 키가 상수인가**"] = {
        "🔴 무엇": ("사전등록 §2 F1: **내가 새로 만든 `통과` 키 중 하나라도 변조에서 상수를 내면 "
                 "이 사이클은 실패다.** 분모는 `meta965.py` + `checks965.py` 의 `통과` 키 전량"),
        "🔴🔴 978 수리 3": ("판정을 `f1_verdict()` 순수 함수로 뺐다 — 옛 자리는 `main()` 안이라 "
                       "**생성기가 원리상 못 움직였고** 자 B 가 항진명제로 잡았다"),
        "🔴 분모: 내 `통과` 자리": f1["분모"],
        "🔴 R3 뺀 자리(생성기 리터럴 · 검사가 아니다)": {
            "수": f1["면제"], "자리": f1["면제 자리"], "왜": F1_DENOM_EXEMPT_FUNCS},
        "🔴 빼기 전 분모": f1["빼기 전 분모"],
        "🔴 분자: 상수인 자리": f1["분자: 항진명제"],
        "🔴 상수인 자리 목록": f1["항진명제 자리"],
        "🔴 모른다": f1["모른다 자리"],
        "🔴 판정을 무는 뿌리를 가진 자리": f1["판정을 무는 뿌리를 가진 자리"],
        "🔴 빈 분모로 통과하던 자리를 닫았나": True,
        "통과": f1v["통과"],
    }

    # ── §5 산출물 쪽 전수 — `통과` 키를 원문에서 모든 중첩 레벨로 센다 ────────
    outs = collections.OrderedDict()
    tot_keys = 0
    for rel in REGISTERED_OUT:
        p = ROOT / rel
        if not p.exists():
            outs[rel] = "🔴 없다(아직 안 냈다)"
            continue
        obj = json.loads(p.read_text(encoding="utf-8"))
        ks = count_pass_keys(obj)
        tot_keys += len(ks)
        outs[rel] = {"`통과` 키(모든 중첩 레벨)": len(ks),
                     "True": sum(1 for _, v in ks if v is True),
                     "True 아님": sum(1 for _, v in ks if v is not True)}
    R["§5 산출물 쪽 전수 — `통과` 키를 **모든 중첩 레벨**에서 센다"] = {
        "🔴 왜 코드 쪽 수와 다른가": ("코드 한 자리가 **여러 번 실행되어 여러 키**를 낼 수 있고, "
                             "`{**f(...)}` 위임은 코드에 글자가 없다. **두 분모는 다르다**(조항 60)"),
        "파일별": outs, "합": tot_keys,
        "통과": tot_keys > 0,
    }

    R["🔴 열린 파일(쓰기 차단 감사)"] = {
        "연 수": len(OPENED),
        "🔴 판 파일을 열었나": [o for o in OPENED if "denominator" in str(o)] or "없음",
    }
    R["끝(UTC)"] = dt.datetime.now(dt.timezone.utc).isoformat()
    R["코드 sha256"] = hashlib.sha256(self_src.encode("utf-8")).hexdigest()

    # ── 🔴🔴 R3 (노트 969 · 티처 #107 2순위-①) ─────────────────────────────
    #   **자가 「자기가 잰 소스의 sha」를 산출물에 박는다.**
    #   왜: 968 의 산출물은 `genver: 2` 라 적혀 있는데 그 수는 genver 1 이 낸다. 원인은
    #   **그 실행이 판 주행 도중이라 러너가 중간판**이었던 것인데, 산출물에 「잰 대상의
    #   sha」가 없어서 **원리상 사후에 가릴 수 없었다.** 이제 박는다 —
    #   커밋된 blob sha 와 대조하면 「커밋본에서 재현되나」가 **한 줄로** 판정된다.
    def _sha_rel(rel):
        p = ROOT / rel
        if not p.is_file():
            return None
        return hashlib.sha256(p.read_bytes()).hexdigest()   # 🔴 자르지 않는다

    R["🔴🔴 잰 소스 sha256 (R3 · 969)"] = {
        "🔴 자기 자신": {"runners/meta965.py": R["코드 sha256"]},
        "🔴 분모 ① 등록 러너": {rel: _sha_rel(rel) for rel in REGISTERED},
        "🔴 분모 ② 등록 산출물": {rel: _sha_rel(rel) for rel in REGISTERED_OUT},
        "🔴 「내 것」(§4 F1)": {rel: _sha_rel(rel) for rel in MINE},
        "🔴 합친 sha256": hashlib.sha256(json.dumps(
            {rel: _sha_rel(rel) for rel in sorted(set(REGISTERED) | set(MINE))},
            sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest(),
        "🔴 뜻": ("이 산출물의 수는 **위 sha 를 가진 바이트**에서 나왔다. "
                "`git hash-object` 가 아니라 **파일 내용의 sha256** 이다 --- "
                "`git show <ref>:<path> | shasum -a 256` 으로 대조하라. "
                "🔴 하나라도 커밋본과 다르면 **그 수는 커밋된 소스에서 재현 안 된다**"),
    }

    secs = collections.OrderedDict(
        (k, v) for k, v in R.items() if isinstance(v, dict) and "통과" in v)
    R["🔴 절 회계"] = {
        "분자: 통과한 절": sum(1 for v in secs.values() if v["통과"] is True),
        "분모: `통과` 키를 가진 절": len(secs),
        "🔴 붉은 절": [k for k, v in secs.items() if v["통과"] is not True] or "없음",
        # 🔴 964 의 절 회계는 `len(red) == len(secs) - n_ok` 였다 — **같은 집합의 분할**이라
        #    원리상 참(티처 #103 C2). 여기는 **전부 초록인가**를 낸다: 붉은 절이 하나 생기면 떨어진다.
        "🔴 이 절의 `통과` 가 뜻하는 것": "**모든 절이 초록인가** — 붉은 절이 하나라도 있으면 떨어진다",
        "통과": all(v["통과"] is True for v in secs.values()),
    }
    return R


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    #: 🔴 **노트 966** — 966 이 자기 러너에 F1 을 걸려면 분모와 「내 것」 집합을 바꿔야 한다.
    #: 🔴 **기본값은 965 그대로다** — 옛 산출물의 뜻이 조용히 갈리면 안 된다(노트 898 규칙).
    ap.add_argument("--only", default="", help="쉼표로 구분한 러너 목록으로 분모를 좁힌다")
    ap.add_argument("--mine", default="", help="쉼표로 구분한 「내가 새로 만든」 파일(§4 F1)")
    #: 🔴 **노트 968** — 생성기 판. 1 = 965 그대로(기본) · 2 = numpy 배열 · 판 `Data` 추가.
    ap.add_argument("--genver", type=int, default=1, choices=[1, 2],
                    help="자 B 생성기 판(1 = 965 그대로 · 2 = numpy·Data 추가)")
    #: 🔴 **노트 969** — 슬라이서 판. `new` = R1 적용(기본) · `old` = 968 이전(결함 판).
    #: 🔴 **자를 고치면 구판·신판을 같은 대상에 걸어 전후를 싣기 위한 것이다.**
    ap.add_argument("--slicer", default="new", choices=["new", "old"],
                    help="역슬라이서 판(new = R1 적용 · old = 968 이전 결함 판 · 대조용)")
    #: 🔴🔴 **노트 971 (티처 #109 m3)** — `통과` 키 일치 규칙.
    #: `exact` = 965 그대로(기본) · `suffix` = 접두어 허용(`"🔴 F1 통과"` 를 분모에 넣는다).
    #: 🔴🔴🔴 **노트 976 수리 5 (티처 #114 3순위 ⓓ)** — **기본값을 `contains` 로 올렸다.**
    #: 기본값 `exact` 에서 **975 자신의 러너 5/5 가 분모 0** 이었다 = 죽은 채점.
    #: 🔴 **노트 898 의 「기본값 보존」 규칙을 일부러 어겼고 그 사실을 산출물에 적는다**
    #: (972 가 `--poolscope` 에서 한 것과 같은 꼴).
    ap.add_argument("--passkey", default="contains",
                    choices=["exact", "suffix", "contains"],
                    help="통과 키 일치 규칙(exact = 965 그대로 · suffix = 접두어 허용 · 971 "
                         "· contains = 포함 일치 · 🔴 976 이 기본값으로 올렸다)")
    #: 🔴🔴🔴 **노트 972 (티처 #110 치명 1)** — 자 B 생성기 풀의 범위.
    #: 🔴 **기본값을 `func` 로 바꿨다** — `file` 은 원리상 틀린 자다(위 POOLSCOPE 주석).
    ap.add_argument("--poolscope", default="func", choices=["file", "func"],
                    help="자 B 풀 범위(file = 965~971 그대로 · func = 972 수리 · 기본)")
    a = ap.parse_args()
    globals()["GENVER"] = a.genver
    globals()["SLICER"] = a.slicer
    globals()["PASSKEY"] = a.passkey
    globals()["POOLSCOPE"] = a.poolscope
    if a.only:
        REGISTERED[:] = [s.strip() for s in a.only.split(",") if s.strip()]
    if a.mine:
        MINE[:] = [s.strip() for s in a.mine.split(",") if s.strip()]
    res = main()
    res["🔴 자 B 생성기 판(968)"] = {
        "genver": a.genver,
        "뜻": ("1 = 965·966·967 과 비트로 같다 · 2 = numpy 배열 · 판 `Data` "
              "생성기가 붙는다(노트 968 · 티처 #106 2순위)"),
        "🔴 기본값을 안 바꿨다": bool(GENVER == a.genver and ap.get_default("genver") == 1)}
    res["🔴🔴 역슬라이서 판(969)"] = {
        "slicer": a.slicer,
        "뜻": ("new = R1 적용(968 이 고친 것) · old = 968 이전 결함 판. "
              "🔴 **같은 대상에 둘 다 걸어 전후를 실어야 한다** --- 968 은 안 했다"),
        "🔴 기본값을 안 바꿨다": bool(ap.get_default("slicer") == "new")}
    res["🔴🔴🔴 통과 키 일치 규칙(971 · 티처 #109 m3)"] = {
        "passkey": a.passkey,
        "뜻": ("exact = 965·966·967·968·969·970 과 비트로 같다(`k == \"통과\"`) · "
              "suffix = **접두어를 허용**한다(`k.endswith(\"통과\")`). "
              "🔴 970 에서는 그 사이클의 **가장 중요한 검사**인 `\"🔴 F1 통과\"`(내가 돌린 "
              "러너 ↔ 커밋 blob)가 **자의 분모 밖**에 있었다 --- 969 에서 물려받은 구멍이다"),
        "🔴 계수 키는 여전히 분모 밖": "`\"🔴 통과 수\"` 는 검사가 아니라 회계라 접미로도 안 잡힌다",
        "🔴🔴🔴 976 수리 5 — 기본값을 `exact` → `contains` 로 올렸다": bool(
            ap.get_default("passkey") == "contains"),
        "🔴 왜 바꿨나": ("기본값 `exact` 에서 **975 자신의 러너 5/5 가 분모 0** 이었다 — "
                  "분모가 0 이면 그 채점은 **죽은 것**이다(티처 #114 3순위 ⓓ). "
                  "🔴 **노트 898 의 「기본값 보존」 규칙을 일부러 어겼다** — "
                  "972 가 `--poolscope` 에서 한 것과 같은 꼴이고, 옛 산출물은 "
                  "전부 `exact` 판이라는 것을 여기 적는다."),
        "🔴 옛 산출물": "965~975 의 `out*_meta.json` 은 전부 `passkey=exact` 판이다"}
    res["🔴🔴🔴 자 B 풀 범위(972 · 티처 #110 치명 1)"] = {
        "poolscope": a.poolscope,
        "뜻": ("file = 965~971 그대로 --- 풀을 **파일 전체 AST** 에서 거둔다. "
              "func = 972 수리 --- **감싸는 함수 AST** 에서만 거둔다"),
        "🔴🔴 기본값을 바꿨다": bool(ap.get_default("poolscope") == "func"),
        "🔴 왜 바꿨나": ("`file` 은 **원리상 틀린 자**다 --- 한 자리의 판정이 그 자리의 코드가 "
                  "아니라 **파일의 나머지 내용**에 매인다. 971 의 「낙하 4(30.8%)」가 "
                  "커밋본에서 갈린 뿌리가 이것이다(티처 #110 치명 1). "
                  "🔴 **노트 898 의 「기본값 보존」 규칙을 일부러 어겼고 그 사실을 여기에 적는다.**"),
        "🔴 옛 산출물": ("965~971 의 `out*_meta.json` 은 전부 `file` 범위다. "
                   "972 는 `file`·`func` 를 **둘 다** 내서 나란히 싣는다"),
    }
    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", a.out)
