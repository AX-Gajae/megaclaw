# -*- coding: utf-8 -*-
"""**경로를 내는 git 호출**의 정본 검출기 --- 노트 947 (티처 #86 C1 처방).

## 왜 있나

946 은 「날 것 호출 **전수**」를 냈지만 바늘이 **넷**뿐이었다:

    PATH_TOKENS = ("ls-files", "ls-tree", "--name-only", "--name-status")

똑같이 8진 이스케이프해서 경로를 내는 ``git status --porcelain`` 과
``git grep -l`` 이 **통째로 분모 밖**이었다. 그 사각지대에 하필

* ⑤′ 의 명부·소비자 생산기 (``fiveprime902.py:147`` ``grep -lF``)
* ⑤′ 의 ⓪ 관문 (``fiveprime902.py:119`` ``status --porcelain``)
* 946 자신의 판정기 둘 (``out946_quotefix.py:258`` ``:365``)

이 들어 있었다. 즉 **「전수」를 세는 자가 자기를 못 봤다.**

## 🔴 바늘을 넓히기 전에 물은 것 --- 「내 새 바늘도 못 보는 자리는?」

946 의 AST 자는 **같은 파일에서 정의된 래퍼**만 봤다(``_git_wrappers``).
주 세션이 티처 #86 을 검증할 때 쓴 바늘도 「리스트 첫 원소 = 'git'」이라
래퍼 호출을 통째로 못 봐 **9 를 5 로 셌다.** 그래서 이 모듈은 넷을 다 훑는다:

===== ================================================================
갈래   무엇
===== ================================================================
①     **argv 리터럴** --- ``["git", …]`` / ``("git", …)``
②     **래퍼 호출** --- 같은 파일 **및 import 한 남의 모듈**의 git 래퍼
③     **f-string / % 조립** --- ``f"git log --name-only {ref}"``
④     **셸 문자열** --- ``subprocess.run("git status --porcelain", shell=True)``
       · ``os.system`` · ``os.popen``
⑤     🔴 **변수로 조립한 argv** --- ``args = ["grep", "-lF"]`` → ``args += ["-e", n]``
       → ``_git(args)``. **이 갈래를 만들기 전에 물어서 찾았다** ---
       티처가 지목한 ``fiveprime902.py:147`` 이 정확히 이 꼴이라, ①②③④ 만으로는
       **그 자리를 여전히 못 본다.** 「바늘을 넓혔다」가 또 좁을 뻔했다
===== ================================================================

## 🔴 그리고 자를 **둘** 쓴다 (조항 60 · 62)

자가 하나면 그 자의 사각지대가 그대로 「없다」가 된다.

* **자 A (AST)** --- 위 네 갈래. 정확하지만 **동적 조립을 못 본다**
* **자 B (텍스트)** --- 줄 단위 정규식. 넓지만 **주석·docstring 을 같이 센다**

두 자의 차는 **혼자 못 실린다**(조항 62) --- ``lab.keyspace.diff_report`` 로
**반대 방향 · 예시 다섯 · 심은 키**를 같이 낸다.

## 쓰는 법

    from lab import gitcall as gc

    cen = gc.census()          # 절 하나(`통과` 키를 낸다)
    gc.plant_check()           # 🔴 심어서 확인 --- 네 갈래를 다 잡나
"""
from __future__ import annotations

import ast
import re
import shlex
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

try:                                             # 러너에서든 라이브러리로든 돈다
    from lab import keyspace as ks
except ImportError:                              # pragma: no cover
    import sys
    sys.path.insert(0, str(ROOT))
    from lab import keyspace as ks

__all__ = [
    "ROOT", "PATH_SUBS_ALWAYS", "PATH_SUBS_COND", "PATH_FLAGS", "TOKENS",
    "emits_paths", "wrapper_registry", "sites_ast", "sites_regex",
    "census", "plant_check", "INTENTIONAL", "FROZEN_PREFIX",
    # 🔴 949 --- 도장/대조 가르기(티처 #88 C1)
    "CHECK_CRITERIA", "checkers", "check_cited", "plant_check_stamp",
    "SeedPadError", "diff62", "diff62_guarded", "board_imports", "exempt_rulers",
]

# ── 무엇이 「경로를 내는 git 명령」인가 ─────────────────────────────────────
#: 🔴 **하위명령만으로 경로를 내는 것.** 946 의 바늘 넷 중 둘(`ls-files`·`ls-tree`)이
#: 여기 있고, 나머지가 946 이 통째로 놓친 자리다.
#: * ``status`` --- 인용을 켠 채로 ``"경로"`` 를 낸다(``--porcelain`` 이어도 똑같다)
#: * ``grep`` --- ``-l`` 이든 ``-n`` 이든 **줄머리에 경로**를 낸다
#: * ``diff-tree``/``diff-index``/``diff-files`` --- 배관 명령이지만 경로를 낸다
#: * ``check-ignore``/``clean`` --- 경로 목록 그 자체
PATH_SUBS_ALWAYS = (
    "ls-files", "ls-tree", "status", "grep", "check-ignore", "clean",
    "diff-tree", "diff-index", "diff-files", "whatchanged", "ls-remote-nope",
)
#: 🔴 **플래그가 있어야 경로를 내는 것.** ``git log`` 는 맨몸이면 경로를 안 낸다.
PATH_SUBS_COND = ("diff", "log", "show", "format-patch", "stash")
#: 위 하위명령에 붙어 경로를 내게 하는 플래그. 946 의 나머지 바늘 둘이 여기 있다.
PATH_FLAGS = ("--name-only", "--name-status", "--raw", "--stat", "--numstat",
              "--summary", "--dirstat", "--porcelain")
#: 자 B(텍스트)가 쓰는 낱말 전량 --- 위 셋의 합집합
TOKENS = tuple(sorted(set(PATH_SUBS_ALWAYS) | set(PATH_SUBS_COND) | set(PATH_FLAGS)))

SAFE_Z = "-z"
SAFE_Q = ("core.quotepath=false", "core.quotePath=false")

#: 동결 --- 941~946 의 러너·산출물. **규약상** 안 고친다(동결물 수정 금지).
#:
#: 🔴🔴 **949 정정 (티처 #88 C1 --- 이 주석이 이 결함의 뿌리였다).**
#: 947~948 은 여기에 *"스탬프가 코드 sha256 을 담아 **주석 한 줄도 대조를 깬다**"* 라고
#: 적어 두었다. **거짓이다.** 산출물에 박힌 코드 sha256 은 「이 코드가 이 산출물을 냈다」는
#: **도장(stamp)** 이지 「이 코드가 안 바뀌었다」는 **대조(check)** 가 아니다 ---
#: 소스를 고쳐도 그 기록은 **그때의 sha 를 적은 것**이므로 여전히 참이고,
#: **아무 검사도 붉어지지 않는다.** 도장을 대조라고 못 박은 이 한 문장이
#: 「㉮ 원리상 못 고친다」를 **도장이 늘 때마다 느는 회계 숫자**로 만들었다.
#: 무엇이 진짜 대조인지는 아래 ``CHECK_CRITERIA`` 와 ``checkers()`` 가 정한다.
FROZEN_PREFIX = ("runners/out941", "runners/out942", "runners/out943",
                 "runners/out944", "runners/out945", "runners/out946")

#: 🔴 **의도적인 날 것 --- 동결 파일용**(941~946 은 고칠 수 없어 표지를 못 박는다).
#: 946 은 이 딕셔너리를 **파일 단위(`줄 = 0`)** 로 썼는데, 그러면 같은 파일의
#: **진짜 날 것까지 통째로 면제**된다. 실측: 그 규칙이면 `out946_quotefix.py` 의
#: `:258`·`:317`·`:365`(티처 #86 이 지목한 바로 그 셋)가 「의도적」으로 분류된다.
#: 🔴 그래서 947 은 **줄 단위로만** 면제한다.
INTENTIONAL: dict[tuple[str, int], str] = {
    ("runners/out946_quotefix.py", 386):
        "🔴 재현 --- `_raw_lstree_cache()` 는 **945 의 날 것 술어를 그대로 다시 돌린다**. "
        "여기서 인용을 끄면 「옛 자로 얼마가 나왔나」를 못 잰다(절 2 나)",
    ("runners/out946_recount.py", 367):
        "🔴 음성 대조 --- `_raw_two_ways()` 는 날 것을 quotepath 켜고/끄고 두 번 돌려 "
        "「날 것은 그 설정을 탄다」를 실측한다. 끄면 그 대조가 죽는다",
    ("runners/out946_recount.py", 369):
        "🔴 음성 대조 --- 같은 함수의 두 번째 호출(quotepath 를 켠 쪽)",
}

#: 🔴 **살아 있는 파일은 딕셔너리가 아니라 「표지」로 면제한다.**
#: 줄 번호를 러너 안에 손으로 박으면 그 파일을 고치는 순간 면제가 엉뚱한 줄로 옮는다
#: (946 이 그래서 `줄 = 0` 이라는 파일 단위 면제를 썼고, 그 대가로 진짜 날 것 셋을 놓쳤다).
#: 호출 자리 **위 여섯 줄 안**에 이 표지가 있으면 「의도적」이다.
INTENT_MARK = re.compile(r"#\s*날것허용\s*:\s*(.+)")
INTENT_LOOKBACK = 6

#: 🔴 **정본 판독기** --- 이 함수들을 부르는 자리는 argv 에 `-z` 가 안 보여도 안전하다
#: (함수가 안에서 붙인다). 이 표가 없으면 `ks.git_paths(...)` 호출 전부가
#: 「날 것」으로 잘못 세어진다 --- 946 은 그 자리를 아예 **호출 자리로도 안 셌다**.
CANON: set[tuple[str, str]] = {
    ("lab.keyspace", "git_paths"), ("lab.keyspace", "git_lines"),
    ("lab.gitcall", "grep_files"),
}


def emits_paths(vec: list[str]) -> tuple[bool, str]:
    """이 argv 벡터가 **경로를 내나** --- 참/거짓과 **왜**를 같이 낸다.

    🔴 「왜」를 같이 내는 이유: 946 은 바늘 넷을 상수 튜플로 박아서
    **무엇이 분모 밖인지 산출물만 봐서는 알 수 없었다.**

    >>> emits_paths(["git", "status", "--porcelain"])[0]
    True
    >>> emits_paths(["git", "log", "-1", "--format=%H"])[0]
    False
    >>> emits_paths(["git", "rev-parse", "HEAD"])[0]
    False
    """
    body = [x for x in vec if x != "git"]
    #: `-c core.quotePath=false` 같은 전역 옵션은 하위명령 앞에 온다 --- 건너뛴다
    i = 0
    while i < len(body) and (body[i].startswith("-") or
                             (i > 0 and body[i - 1] == "-c")):
        i += 1
    sub = body[i] if i < len(body) else ""
    flags = [x for x in body if x in PATH_FLAGS]
    if sub in PATH_SUBS_ALWAYS:
        return True, f"하위명령 `{sub}` 은 언제나 경로를 낸다"
    if sub in PATH_SUBS_COND and flags:
        return True, f"하위명령 `{sub}` + 경로 플래그 {flags}"
    #: 🔴 하위명령을 못 읽었는데 경로 플래그가 있으면 **「없다」가 아니라 「모른다」**다.
    #: 그런 자리는 세는 쪽에 넣는다(조항 59) --- 안 넣으면 조용히 사라진다.
    if flags:
        return True, f"🔴 하위명령을 못 읽었다(`{sub or '?'}`) · 경로 플래그 {flags} 는 있다"
    return False, f"경로를 내는 하위명령·플래그가 없다(`{sub or '?'}`)"


def safety(vec: list[str]) -> tuple[bool, bool]:
    """``(-z 가 있나, core.quotePath=false 가 있나)``."""
    has_z = SAFE_Z in vec
    has_q = any(any(q in x for q in SAFE_Q) for x in vec)
    return has_z, has_q


# ── 자 A · AST ────────────────────────────────────────────────────────────
SUBPROC = ("run", "Popen", "check_output", "getoutput", "getstatusoutput",
           "call", "check_call", "system", "popen")


def _str_of(node) -> str | None:
    """이 노드가 내는 **문자열 리터럴 뼈대**. f-string·`%`·`+` 도 편다.

    🔴 동적 조각(`{ref}`)은 ``\\x00`` 자리표시로 남긴다 --- **「값을 모른다」와
    「없다」를 가른다**(조항 59). 뼈대만으로도 하위명령·플래그는 다 읽힌다.
    """
    if isinstance(node, ast.Constant):
        return node.value if isinstance(node.value, str) else None
    if isinstance(node, ast.JoinedStr):
        out = []
        for v in node.values:
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                out.append(v.value)
            else:
                out.append("\x00")
        return "".join(out)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Mod, ast.Add)):
        left = _str_of(node.left)
        if left is None:
            return None
        right = _str_of(node.right) if isinstance(node.op, ast.Add) else "\x00"
        return left + (right or "\x00")
    if isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "format":
        return _str_of(node.func.value)
    return None


def _shell_vec(s: str) -> list[str] | None:
    """``"git …"`` 로 시작하는 셸 문자열을 argv 로 편다. 아니면 ``None``."""
    if not isinstance(s, str) or not s.startswith("git ") or "\n" in s or len(s) > 400:
        return None
    try:
        return [x for x in shlex.split(s.replace("\x00", "PLACEHOLDER")) if x]
    except ValueError:
        return [x for x in s.split() if x]


def _consts(node) -> list[str]:
    """이 호출의 **직속** 문자열 상수(리스트/튜플 인자는 한 겹 벗긴다 · f-string 포함)."""
    out: list[str] = []
    for a in list(getattr(node, "args", []) or []):
        s = _str_of(a)
        if s is not None:
            out.append(s)
        elif isinstance(a, (ast.List, ast.Tuple)):
            for e in a.elts:
                es = _str_of(e)
                if es is not None:
                    out.append(es)
    return out


def _same_file_wrappers(tree: ast.AST) -> set[str]:
    """이 파일 안에서 정의된 **git 래퍼**의 이름(본문에 `subprocess.*` + `"git"`).

    두 바퀴 돈다 --- 래퍼를 다시 감싼 래퍼(`_git` → `git_lines`)도 잡는다.
    """
    names: set[str] = set()
    fns = [n for n in ast.walk(tree)
           if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    for _ in range(2):
        for fn in fns:
            if fn.name in names:
                continue
            for n in ast.walk(fn):
                if not isinstance(n, ast.Call):
                    continue
                callee = getattr(n.func, "attr", None) or getattr(n.func, "id", None)
                if callee in SUBPROC and any(
                        isinstance(c, ast.Constant) and c.value == "git"
                        for c in ast.walk(n)):
                    names.add(fn.name)
                elif callee in names:
                    names.add(fn.name)
    return names


def wrapper_registry(pys, root: Path = ROOT) -> dict[str, set[str]]:
    """🔴 **저장소 전량의 git 래퍼 등기부** --- `(모듈 점경로) → {함수 이름}`.

    946 의 자가 못 본 자리가 정확히 여기다: 래퍼가 **남의 파일**에 있으면
    같은 파일만 보는 자는 그 호출을 **0** 으로 센다.
    """
    reg: dict[str, set[str]] = {}
    for rel in pys:
        try:
            tree = ast.parse((root / rel).read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError, OSError):
            continue
        w = _same_file_wrappers(tree)
        if w:
            reg[rel[:-3].replace("/", ".")] = w
    return reg


def _alias_map(tree: ast.AST, reg: dict[str, set[str]]):
    """``import`` 을 읽어 **이름 → 래퍼**로 잇는다.

    ``from lab.x import _git`` · ``import lab.x as m`` · ``from lab import x``
    셋 다 본다. 🔴 이것이 없으면 남의 래퍼 호출이 조용히 사라진다.
    """
    direct: dict[str, str] = {}        # 지역 이름 → 모듈
    modal: dict[str, str] = {}         # 별칭 → 모듈
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                modal[a.asname or a.name.split(".")[0]] = a.name
        elif isinstance(n, ast.ImportFrom) and n.module:
            for a in n.names:
                full = f"{n.module}.{a.name}"
                if full in reg:                    # from lab import gitcall
                    modal[a.asname or a.name] = full
                elif n.module in reg and a.name in reg[n.module]:
                    direct[a.asname or a.name] = n.module
    return direct, modal


def _literal_strs(node) -> list[str]:
    """이 표현식이 **정적으로** 내는 문자열 원소들(리스트/튜플/`+`/삼항 다 편다)."""
    if node is None:
        return []
    s = _str_of(node)
    if s is not None:
        return [s]
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        out = []
        for e in node.elts:
            out += _literal_strs(e)
        return out
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _literal_strs(node.left) + _literal_strs(node.right)
    if isinstance(node, ast.IfExp):
        return _literal_strs(node.body) + _literal_strs(node.orelse)
    return []


def _var_consts(scope: ast.AST, name: str) -> tuple[list[str], int | None]:
    """🔴 **변수로 조립한 argv 를 되짚는다**(갈래 ⑤).

    ``args = ["grep", "-lF"]`` → ``args += ["-e", n]`` → ``args.append(tree)``
    를 한 벡터로 모은다. 🔴 **줄 번호는 첫 조립 자리**를 쓴다 --- 티처 #86 이
    지목한 ``fiveprime902.py:147`` 이 바로 그 줄이다.

    ⚠ **못 보는 것**: 이 변수가 **다른 함수에서** 조립되면 못 따라간다.
    「없다」가 아니라 **「이 자가 못 본다」**로 적는다(조항 59).
    """
    out: list[str] = []
    first: int | None = None

    def _mark(cs, ln):
        nonlocal first
        if cs:
            out.extend(cs)
            if first is None:
                first = ln
    for n in ast.walk(scope):
        if isinstance(n, ast.Assign) and any(
                getattr(t, "id", None) == name for t in n.targets):
            _mark(_literal_strs(n.value), n.lineno)
        elif isinstance(n, ast.AugAssign) and getattr(n.target, "id", None) == name:
            _mark(_literal_strs(n.value), n.lineno)
        elif isinstance(n, ast.Call) and \
                getattr(n.func, "attr", None) in ("append", "extend") and \
                getattr(getattr(n.func, "value", None), "id", None) == name:
            cs = []
            for a in n.args:
                cs += _literal_strs(a)
            _mark(cs, n.lineno)
    return out, first


def sites_ast(pys, root: Path = ROOT, reg: dict[str, set[str]] | None = None):
    """자 A --- **다섯** 갈래를 다 훑는다. ``(rel, line, vec, 갈래)`` 를 낸다."""
    if reg is None:
        reg = wrapper_registry(pys, root)
    for rel in pys:
        try:
            src = (root / rel).read_text(encoding="utf-8")
            tree = ast.parse(src)
        except (SyntaxError, UnicodeDecodeError, OSError):
            continue
        local = _same_file_wrappers(tree)
        direct, modal = _alias_map(tree, reg)
        seen: set[tuple[int, tuple[str, ...]]] = set()

        def _yield(line, vec, kind):
            key = (line, tuple(vec))
            if key in seen:
                return None
            seen.add(key)
            return (rel, line, vec, kind)

        for n in ast.walk(tree):
            # ① argv 리터럴
            if isinstance(n, (ast.List, ast.Tuple)):
                c = [s for s in (_str_of(e) for e in n.elts) if s is not None]
                if c and c[0] == "git":
                    r = _yield(n.lineno, c, "① argv 리터럴(`[\"git\", …]`)")
                    if r:
                        yield r
                continue
            if not isinstance(n, ast.Call):
                continue
            callee_id = getattr(n.func, "id", None)
            callee_at = getattr(n.func, "attr", None)
            owner = getattr(getattr(n.func, "value", None), "id", None)
            # ④ 셸 문자열 (`subprocess.run("git …", shell=True)` · `os.system`)
            if (callee_id in SUBPROC or callee_at in SUBPROC) and n.args:
                s = _str_of(n.args[0])
                v = _shell_vec(s) if s else None
                if v:
                    r = _yield(n.lineno, v, "④ 셸 문자열(`subprocess`/`os.system`)")
                    if r:
                        yield r
                continue                # 안쪽 리스트 리터럴은 ① 이 이미 잡는다
            # ② 래퍼 호출 --- 같은 파일 · self · 남의 모듈
            hit = None
            if callee_id and callee_id in direct and \
                    (direct[callee_id], callee_id) in CANON:
                hit = f"②′ 정본 판독기 `{direct[callee_id]}.{callee_id}(…)`"
            elif callee_at and owner and owner in modal and \
                    (modal[owner], callee_at) in CANON:
                hit = f"②′ 정본 판독기 `{modal[owner]}.{callee_at}(…)`"
            elif callee_id and callee_id in local:
                hit = f"② 같은 파일의 래퍼 `{callee_id}(…)`"
            elif callee_id and callee_id in direct:
                hit = f"② 🔴 남의 모듈에서 import 한 래퍼 `{direct[callee_id]}.{callee_id}(…)`"
            elif callee_at and owner and owner in modal and \
                    callee_at in reg.get(modal[owner], ()):
                hit = f"② 🔴 남의 모듈의 래퍼 `{modal[owner]}.{callee_at}(…)`"
            elif callee_at and callee_at in local and owner in (None, "self"):
                hit = f"② 같은 파일의 래퍼 `self.{callee_at}(…)`"
            if hit:
                c = _consts(n)
                if c:
                    r = _yield(n.lineno, ["git"] + c if c[0] != "git" else c, hit)
                    if r:
                        yield r

        # ⑤ 🔴 변수로 조립한 argv --- `args = [...]` / `args += [...]` → `_git(args)`
        #    🔴 **이 갈래가 없으면 `fiveprime902.py:147`(⑤′ 명부 생산기)을 여전히 못 본다.**
        scopes = [tree] + [f for f in ast.walk(tree)
                           if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))]
        for sc in scopes:
            for n in ast.walk(sc):
                if not isinstance(n, ast.Call) or not n.args:
                    continue
                callee_id = getattr(n.func, "id", None)
                callee_at = getattr(n.func, "attr", None)
                owner = getattr(getattr(n.func, "value", None), "id", None)
                is_sub = (callee_id in SUBPROC or callee_at in SUBPROC)
                is_wrap = bool(
                    (callee_id and (callee_id in local or callee_id in direct)) or
                    (callee_at and owner and owner in modal and
                     callee_at in reg.get(modal[owner], ())) or
                    (callee_at and callee_at in local and owner in (None, "self")))
                if not (is_sub or is_wrap):
                    continue
                var = getattr(n.args[0], "id", None)
                if not var:
                    continue
                vec, ln = _var_consts(sc, var)
                if not vec or ln is None:
                    continue
                #: ③ `cmd = f"git log {ref} --name-only"` → `run(cmd, shell=True)`
                if len(vec) == 1 and vec[0].startswith("git "):
                    sv = _shell_vec(vec[0])
                    if not sv:
                        continue
                    vec = sv
                if vec[0] != "git":
                    if is_sub:
                        continue        # subprocess 인데 git 이 아니다 --- 남의 명령
                    vec = ["git"] + vec
                r = _yield(ln, vec,
                           "⑤ 🔴 변수로 조립한 argv(`%s` --- 호출은 %d 줄)"
                           % (var, n.lineno))
                if r:
                    yield r

        # 🔴 **③ 을 「떠도는 f-string」으로 세지 않는다.** 첫 판이 그렇게 셌더니
        #    `raise GitError("git grep rc=%d · %s" % …)` 같은 **오류 문안**이
        #    「경로를 내는 호출」로 잡혔다(실측 2 자리). ③ 은 위 ⑤ 의 흐름 추적이
        #    **프로세스로 건너가는 것만** 잡는다 --- 「넓혔다」가 「부풀렸다」가 되면 안 된다.


# ── 자 B · 텍스트 ──────────────────────────────────────────────────────────
_GIT_LINE = re.compile(r"\bgit\b|\b_git\b|git_paths|git_lines")


def sites_regex(pys, root: Path = ROOT) -> dict[str, str]:
    """자 B --- 줄 단위. ``{"rel:line": 줄 내용}``.

    🔴 **주석·docstring 을 같이 센다**(그게 이 자의 성질이다). 자 A 와의 차를
    조항 62 로 낸다 --- 어느 쪽이 맞다고 미리 정하지 않는다.
    """
    out: dict[str, str] = {}
    for rel in pys:
        try:
            src = (root / rel).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for i, ln in enumerate(src.split("\n"), 1):
            if not _GIT_LINE.search(ln):
                continue
            if any(t in ln for t in TOKENS):
                out[f"{rel}:{i}"] = ln.strip()[:200]
    return out


# ── 실해 ──────────────────────────────────────────────────────────────────
#: 🔴 949 탐색 --- 재현 가능한 **읽기 전용 하위명령**. `_run_both(wide=True)` 가 쓴다.
WIDE_SUBS = ("ls-files", "ls-tree", "status", "grep", "log", "show", "diff",
             "diff-tree", "diff-index", "diff-files", "whatchanged", "check-ignore")


def _run_both(vec: list[str], root: Path = ROOT, *, wide: bool = False) -> dict:
    """같은 인자를 **날 것과 정본으로 둘 다** 돌려 차를 실측한다.

    🔴 이 함수의 날 것 쪽은 **의도적**이다(``INTENTIONAL``) --- 여기서 인용을
    끄면 「날 것은 그 설정을 탄다」를 못 잰다.

    🔴🔴 **949 (티처 #88 3순위 · 탐색 레인)** --- ``wide=True`` 면 재현 대상을
    ``body[0]``(= argv 의 첫 낱말) 이 아니라 **실제로 읽힌 하위명령**으로 잡고
    ``log``·``show`` 까지 넣는다. 948 은 ``body[0]`` 이 옵션(``-c`` 따위)이면
    무조건 「못 돌렸다」를 냈다. ⚠ **기본값은 좁은 쪽 그대로다** --- 판정 레인의
    산출물에 탐색 수치가 섞이지 않게(규칙 1).
    """
    body = [x for x in vec if x != "git"]
    if not body or any("\x00" in x for x in body):
        return {"🔴 못 돌렸다": "인자에 동적 값이 섞여 이 자리를 재현할 수 없다 "
                          "--- **「무해」가 아니라 「못 쟀다」다**(조항 59)"}
    if wide:
        sub = next((x for x in body if x in WIDE_SUBS), None)
        if sub is None:
            return {"🔴 못 돌렸다": "읽힌 하위명령이 재현 대상 목록에 없다 "
                              "--- 읽은 낱말: %s" % body[:4]}
    elif body[0] not in ("ls-files", "ls-tree", "status", "grep"):
        return {"🔴 못 돌렸다": f"읽기 전용 재현 대상이 아니다(`{body[0]}`)"}
    try:
        raw = subprocess.run(["git", "-C", str(root), *body],
                             capture_output=True, timeout=600)
        good = subprocess.run(["git", "-C", str(root), "-c",
                               "core.quotePath=false", *body, "-z"],
                              capture_output=True, timeout=600)
    except (OSError, subprocess.SubprocessError) as e:
        return {"🔴 못 돌렸다": f"{type(e).__name__}: {e}"}
    if raw.returncode not in (0, 1) or good.returncode not in (0, 1):
        return {"🔴 못 돌렸다": f"rc 날것={raw.returncode} 정본={good.returncode}"}
    a = {x for x in raw.stdout.decode("utf-8", "surrogateescape").split("\n") if x}
    b = {x for x in good.stdout.decode("utf-8", "surrogateescape").split("\0") if x}
    return {"날 것이 낸 수": len(a), "정본이 낸 수": len(b),
            "🔴 날것 − 정본": len(a - b), "🔴 정본 − 날것": len(b - a),
            "🔴 날 것에서 이름이 바뀌는 예시 다섯":
                sorted(x for x in a if x.startswith('"'))[:5]}


#: 🔴 948 --- 947 이 쓰던 **좁은 자**. 이제 **음성 대조 전용**이다(판정에 쓰지 마라).
#: 티처 #87 m8: 이 pathspec 은 ``docs/**`` 의 sha 인용을 **원리상 안 본다**.
NARROW_CITE_PATHSPEC = ("runners/*.json", "data/lab/*.json")


def sha_cited(rel: str, root: Path = ROOT, *, tree: str = "HEAD",
              pathspec=()) -> list[str]:
    """이 파일의 **지금 sha256** 을 인용하는 **커밋된** 파일(㉮ 판정의 **유일한 증거원**).

    🔴 946 의 같은 함수는 ``git grep -lF`` 를 **날 것으로** 불렀다(티처 #86 C1).
    여기서는 ``lab.gitcall.grep_files`` 정본을 지난다.

    🔴🔴 **948 이 둘을 고쳤다** (티처 #87 C3 · m8):

    * **범위** --- 947 은 ``runners/*.json``·``data/lab/*.json`` 만 봤다.
      그 pathspec 은 ``docs/**`` 의 sha 인용을 **원리상 안 본다** ---
      「안 걸렸다」가 「못 걸린다」와 구별이 안 되는 자리다(조항 59).
      기본값을 **HEAD 전량**으로 넓힌다. 좁은 자는 ``NARROW_CITE_PATHSPEC`` 으로
      남겨 **음성 대조**에만 쓴다.
    * **트리** --- 947 은 인덱스/작업 트리를 봤다. 낱말이 「**커밋된** 산출물」이므로
      ``HEAD`` 를 본다(규약 60 --- 인덱스와 작업 트리를 섞어 읽는 계수 금지).
    """
    import hashlib
    p = root / rel
    if not p.exists():
        return []
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    try:
        return sorted(grep_files([h], root=root, tree=tree, pathspec=pathspec))
    except ks.GitError:
        return []


#: 뒤 이름(947 판). 남의 코드가 부르면 **넓은 자**가 나가도록 이름만 남긴다.
_sha_cited = sha_cited


def last_commit(rel: str, root: Path = ROOT) -> str:
    """이 경로의 **마지막 커밋 시각**(ISO). 래칫의 방향을 재는 자."""
    r = subprocess.run(["git", "-C", str(root), "log", "-1", "--format=%cI",
                        "--", rel], capture_output=True, text=True)
    return (r.stdout.strip() or "🔴 못 읽었다") if r.returncode == 0 else "🔴 못 읽었다"


def grep_files(needles, *, root: Path = ROOT, tree: str | None = None,
               untracked: bool = False, pathspec=()) -> set[str]:
    """🔴 ``git grep -l`` 의 **정본 판독기** --- ``-z`` 와 ``core.quotePath=false``.

    티처 #86 C2: ⑤′ 의 소비자 명부 **154 중 22 가 이스케이프된 가짜 이름**이었고
    ``endswith(".py")`` 가 그 22 를 「비-.py」로 조용히 재분류했다.
    ``git grep`` 은 ``-z`` 를 주면 파일 이름을 **NUL 로 끊고 인용하지 않는다.**
    """
    if not needles:
        return set()
    args = ["-c", "core.quotePath=false", "grep", "-lFz"]
    if untracked and not tree:
        args.append("--untracked")
    for n in needles:
        args += ["-e", n]
    if tree:
        args.append(tree)
    if pathspec:
        args += ["--", *pathspec]
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True)
    if r.returncode not in (0, 1):
        raise ks.GitError("git grep rc=%d · %s"
                          % (r.returncode, r.stderr.decode("utf-8", "replace")[:400]))
    out = set()
    for x in r.stdout.decode("utf-8", "surrogateescape").split("\0"):
        x = x.strip()
        if not x:
            continue
        if tree and x.startswith(tree + ":"):
            x = x[len(tree) + 1:]
        out.add(x)
    return out


# ── 🔴🔴 949 --- 도장(stamp) 과 대조(check) 를 가른다 (티처 #88 C1) ─────────
CHECK_CRITERIA = (
    "🔴 **대조(check)** 는 셋을 다 채우는 것만이다: HEAD 의 어떤 `.py` 가 "
    "① 그 산출물을 **읽고** ② 그 안에 **기록된 sha 를 꺼내어** "
    "③ **지금 파일에서 다시 계산한 sha** 와 견주어 참/거짓을 낸다. "
    "하나라도 빠지면 **도장(stamp)** --- 「이 코드가 이 산출물을 냈다」는 기록이고 "
    "소스를 고쳐도 **아무것도 안 깨진다**")

#: 「지금 다시 계산한다」쪽을 알아보는 이름들.
SHA_CALLS = ("sha", "sha256", "_sha", "sha_of", "file_sha", "hexdigest", "filesha")

#: 「기록된 값」쪽을 알아보는 이름들 --- JSON 을 읽어 이름에 묶는 호출.
JSON_LOADS = ("load", "loads", "jload", "read_json", "load_json")


def _head_sources(root: Path = ROOT, tree: str = "HEAD") -> dict:
    """``tree`` 의 ``*.py`` 를 **한 프로세스로** 읽는다(`git cat-file --batch`)."""
    #: 🔴 `ls-tree` 의 경로지정자는 `*.py` 를 **글롭으로 안 받는다**(실측: 0 이 나온다).
    #:    「0 = 없다」로 읽을 뻔한 자리다(조항 59) --- 파이썬에서 거른다.
    paths = sorted(p for p in _tracked(root, tree) if p.endswith(".py"))
    if not paths:
        return {}
    req = "".join("%s:%s\n" % (tree, p) for p in paths).encode()
    r = subprocess.run(["git", "-C", str(root), "cat-file", "--batch"],
                       input=req, capture_output=True)
    if r.returncode != 0:
        raise ks.GitError("git cat-file rc=%d" % r.returncode)
    out, i, res = r.stdout, 0, {}
    for p in paths:
        nl = out.find(b"\n", i)
        if nl < 0:
            break
        head = out[i:nl].split(b" ")
        if len(head) < 3:                       # missing 등
            i = nl + 1
            continue
        n = int(head[2])
        res[p] = out[nl + 1:nl + 1 + n].decode("utf-8", "surrogateescape")
        i = nl + 1 + n + 1
    return res


def _tracked(root: Path = ROOT, tree: str = "HEAD") -> set:
    return ks.git_paths("ls-tree", "-r", tree, root=root)


def _names(node) -> set:
    return {getattr(n, "id", None) for n in ast.walk(node) if isinstance(n, ast.Name)}


def _calls(node) -> set:
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            out.add(getattr(n.func, "id", None) or getattr(n.func, "attr", None))
    return out


def _json_bound(tree: ast.AST) -> set:
    """이 파일에서 **JSON 산출물을 읽어 담은 이름** 전량(2 패스 --- 파생까지)."""
    bound: set = set()
    for _ in range(3):                          # 파생(루프 변수 · 재대입)까지 훑는다
        grew = False
        for n in ast.walk(tree):
            tgts, src = [], None
            if isinstance(n, ast.Assign):
                tgts, src = n.targets, n.value
            elif isinstance(n, (ast.For, ast.comprehension)):
                tgts, src = [n.target], (n.iter if isinstance(n, ast.For) else n.iter)
            elif isinstance(n, ast.withitem) and n.optional_vars is not None:
                tgts, src = [n.optional_vars], n.context_expr
            if src is None:
                continue
            hit = bool(_calls(src) & set(JSON_LOADS)) or bool(_names(src) & bound)
            if not hit:
                continue
            for t in tgts:
                for nm in ast.walk(t):
                    if isinstance(nm, ast.Name) and nm.id not in bound:
                        bound.add(nm.id)
                        grew = True
        if not grew:
            break
    return bound


def _side_fresh(node) -> bool:
    return bool(_calls(node) & set(SHA_CALLS))


def _side_stored(node, bound: set) -> bool:
    if _names(node) & bound:
        return True
    for n in ast.walk(node):                    # `d["…sha…"]` 꼴
        if isinstance(n, ast.Subscript):
            k = n.slice.value if isinstance(getattr(n, "slice", None), ast.Constant) \
                else (n.slice if isinstance(n.slice, ast.Constant) else None)
            if isinstance(k, str) and "sha" in k.lower():
                return True
            if isinstance(getattr(n, "slice", None), ast.Constant) and \
                    isinstance(n.slice.value, str) and "sha" in n.slice.value.lower():
                return True
    return False


def _pathish(node, consts: dict):
    """``ROOT / "runners/x.json"`` · ``"a/b.py"`` · ``Path(X)`` 를 rel 문자열로."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return consts.get(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        r = _pathish(node.right, consts)
        if r is None:
            return None
        l = _pathish(node.left, consts)
        return r if not l else (l.rstrip("/") + "/" + r)
    if isinstance(node, ast.Call):
        fn = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
        if fn in ("Path", "str") and node.args:
            return _pathish(node.args[0], consts)
    return None


def _rel(p, root: Path = ROOT):
    """절대 경로를 저장소 기준 상대 경로로. 🔴 안 하면 ``ROOT = Path("/Users/…")`` 인
    러너의 대상이 **전부 「못 풀었다」로 샌다**(첫 판이 실제로 그랬다)."""
    if not p:
        return p
    pre = str(root).rstrip("/") + "/"
    return p[len(pre):] if p.startswith(pre) else p


def _sub_chain(node):
    """``st["a"]["b"]`` → ``("st", ["a", "b"])`` · 못 풀면 ``(None, [])``."""
    keys = []
    while isinstance(node, ast.Subscript):
        k = node.slice
        if isinstance(k, ast.Index):                       # py<3.9 호환
            k = k.value
        if not (isinstance(k, ast.Constant) and isinstance(k.value, str)):
            return None, []
        keys.append(k.value)
        node = node.value
    if isinstance(node, ast.Name):
        return node.id, list(reversed(keys))
    return None, []


def checkers(root: Path = ROOT, tree: str = "HEAD") -> dict:
    """🔴 **커밋된 트리에서 「대조」를 찾는다** --- ``CHECK_CRITERIA`` 그대로.

    낸다: 대조 자리 목록 · **각 자리가 덮을 수 있는 파일의 상한 집합** ·
    이 자로 **안 센 갈래**(rev 기준 비교)의 수.

    🔴 **대상은 정밀하게 푼다**: ``sha(PREREG)`` 같은 상수 경로 · ``for f, r in
    st["…"].items(): … sha(ROOT / f)`` 같은 **산출물 키 순회** · 산출물 자신의 내용을
    다시 해싱하는 꼴 셋을 푼다. **못 푸는 자리는 「모른다」로 따로 센다** ---
    그 수가 0 이 아니면 ``㉮ = 0`` 은 그만큼 구멍이 있다(조항 59).
    """
    import json as _j
    srcs = _head_sources(root, tree)
    tracked = _tracked(root, tree)
    sites, covered, revonly, unresolved, jsoncache = [], {}, [], [], {}

    def _load(rel_json: str):
        if rel_json not in jsoncache:
            p = root / rel_json
            try:
                jsoncache[rel_json] = _j.loads(p.read_text(encoding="utf-8"))
            except Exception:                                     # noqa: BLE001
                jsoncache[rel_json] = None
        return jsoncache[rel_json]

    for rel, src in sorted(srcs.items()):
        try:
            t = ast.parse(src)
        except SyntaxError:
            continue
        bound = _json_bound(t)
        # ── 이름 → 경로 상수 · 이름 → 읽은 JSON 파일 ────────────────────
        consts: dict = {}
        for n in ast.walk(t):
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and \
                    isinstance(n.targets[0], ast.Name):
                s = _rel(_pathish(n.value, consts), root)
                if s and ("/" in s or s.endswith((".py", ".json", ".md"))):
                    consts[n.targets[0].id] = s
        jvar: dict = {}
        for _pass in range(3):                  # 파생(`a, b = d["x"], d["y"]`)까지
            for n in ast.walk(t):
                if not isinstance(n, ast.Assign):
                    continue
                # 값 쪽이 **어느 JSON 파일**에서 왔나
                got = None
                for c in ast.walk(n.value):
                    if isinstance(c, ast.Call):
                        fn = getattr(c.func, "attr", None) or getattr(c.func, "id", None)
                        if fn in JSON_LOADS:
                            for sub in ast.walk(c):
                                q = _rel(_pathish(sub, consts), root)
                                if q and q.endswith(".json"):
                                    got = q
                                    break
                    if isinstance(c, ast.Name) and c.id in jvar:
                        got = got or jvar[c.id]
                if not got:
                    continue
                for tg in n.targets:
                    for nm in ast.walk(tg):
                        if isinstance(nm, ast.Name):
                            jvar.setdefault(nm.id, got)
        # ── 루프 변수 → (그 JSON 파일, 그 자리의 키들) ────────────────────
        loopvar: dict = {}
        for n in ast.walk(t):
            it = getattr(n, "iter", None)
            tgt = getattr(n, "target", None)
            if it is None or tgt is None:
                continue
            base = it
            if isinstance(base, ast.Call) and getattr(base.func, "attr", None) in (
                    "items", "keys", "values"):
                base = base.func.value
            rootname, keys = _sub_chain(base)
            if rootname not in jvar:
                continue
            d = _load(jvar[rootname])
            for k in keys:
                d = d.get(k) if isinstance(d, dict) else None
            ks_ = sorted(d) if isinstance(d, dict) else (
                [x for x in d if isinstance(x, str)] if isinstance(d, list) else [])
            names = ([e.id for e in tgt.elts if isinstance(e, ast.Name)]
                     if isinstance(tgt, ast.Tuple) else
                     ([tgt.id] if isinstance(tgt, ast.Name) else []))
            if names:
                loopvar[names[0]] = (jvar[rootname], ks_)
            for nm in names[1:]:                     # 값 쪽도 그 파일을 가리킨다
                loopvar.setdefault(nm, (jvar[rootname], []))
        lines = src.split("\n")
        for n in ast.walk(t):
            if not isinstance(n, ast.Compare):
                continue
            if not any(isinstance(o, (ast.Eq, ast.NotEq)) for o in n.ops):
                continue
            side = [n.left] + list(n.comparators)
            if not any(_side_fresh(s) for s in side):
                continue
            stored = [s for s in side
                      if _side_stored(s, bound) and not _side_fresh(s)]
            row = {"파일:줄": "%s:%d" % (rel, n.lineno),
                   "줄": lines[n.lineno - 1].strip()[:160]}
            if not stored:
                #: 🔴 **이 자로 안 세는 갈래** --- sha 를 내는데 견주는 상대가
                #: 기록된 상수가 아니다(`git show <rev>:` 꼴). 진단으로만 싣는다.
                revonly.append(row)
                continue
            # ── 🔴 대상 파일을 **정밀하게** 푼다(상한이 아니라 실제 대상) ──
            tgts, why = set(), []
            for c in ast.walk(n):
                if not isinstance(c, ast.Call):
                    continue
                fn = getattr(c.func, "id", None) or getattr(c.func, "attr", None)
                if fn not in SHA_CALLS or not c.args:
                    continue
                arg = c.args[0]
                p = _rel(_pathish(arg, consts), root)
                if p and p in tracked:
                    tgts.add(p)
                    why.append("상수 경로 `%s`" % p)
                    continue
                allnm = [x.id for x in ast.walk(arg) if isinstance(x, ast.Name)]
                nm = next((x for x in allnm if x in loopvar), None)
                if nm in loopvar:
                    f, ks_ = loopvar[nm]
                    hit = [k for k in ks_ if k in tracked]
                    if hit:
                        tgts |= set(hit)
                        why.append("`%s` 의 키 %d 개" % (f, len(hit)))
                    else:
                        tgts.add(f)
                        why.append("그 산출물 자신 `%s`" % f)
                    continue
                nm2 = next((x for x in allnm if x in jvar), None)
                if nm2:
                    tgts.add(jvar[nm2])
                    why.append("그 산출물 자신 `%s`" % jvar[nm2])
                    continue
                why.append("🔴 못 풀었다(`%s`)" % ast.dump(arg)[:60])
            row["🔴 대상"] = sorted(tgts)
            row["대상을 어떻게 풀었나"] = why
            row["🔴 못 푼 자리인가"] = any(w.startswith("🔴") for w in why)
            if row["🔴 못 푼 자리인가"]:
                unresolved.append(row)
            sites.append(row)
            for f in tgts:
                covered.setdefault(f, []).append(row["파일:줄"])
    return {
        "무엇": "🔴 대조(check) 전수 --- 도장(stamp) 과 가른다",
        "자": CHECK_CRITERIA,
        "트리": tree,
        "🔴 훑은 `.py`(분모)": len(srcs),
        "🔴 대조 자리 수": len(sites),
        "🔴 대조가 덮는 파일 수": len(covered),
        "🔴 대상을 못 푼 자리 수(「모른다」 --- 「없다」가 아니다)": len(unresolved),
        "대상을 못 푼 자리": unresolved or "없음",
        "대조 자리": sites,
        "덮인 파일 → 그 대조 자리": {k: v for k, v in sorted(covered.items())},
        "🔴 이 자로 안 센 갈래(rev 기준 비교 · 기록된 상수와 안 견준다)": {
            "수": len(revonly), "자리": revonly,
            "⚠": ("`git show <rev>:파일` 대 지금을 견주는 꼴이다. **고쳐서 커밋하면 "
                  "그대로 통과**하므로 「고치면 깨진다」의 증거가 못 된다 "
                  "--- 티처 #88 C1 이 `out946_recount.py:337-342` 에서 지목한 자리"),
        },
        "🔴 안 본 것(조항 59 --- 「없다」가 아니다)": [
            "16자리 축약 sha 인용(티처 #87 m5 · #88 m2) --- 이 자는 원리상 안 본다",
            "대상을 정적으로 못 푸는 자리는 **「모른다」로 따로 센다** --- 0 이 아니면 "
            "그만큼 이 판정에 구멍이 있다(조항 59)",
        ],
    }


def check_cited(rel: str, idx: dict) -> list:
    """``rel`` 을 **대조**하는 자리 목록(``checkers()`` 의 색인을 받는다)."""
    return list(idx.get("덮인 파일 → 그 대조 자리", {}).get(rel, []))


#: 🔴 심어서 확인 --- 대조 자를 **양성 셋 · 음성 둘**로 잰다(말이 아니라 발화).
CHECK_PLANTS = [
    ("양성 ① 상수 경로를 다시 sha 내어 견준다", True, '''
import json, hashlib
from pathlib import Path
ROOT = Path(".")
TARGET = "lab/gitcall.py"
def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def check():
    st = json.loads(Path("runners/plantstamp.json").read_text())
    return st["sha256"] == sha(ROOT / TARGET)
'''),
    ("양성 ② 산출물 dict 를 순회하며 견준다", True, '''
import json, hashlib
from pathlib import Path
ROOT = Path(".")
def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def check():
    st = json.loads(Path("runners/plantstamp.json").read_text())
    return {f: (r["sha256"] == sha(ROOT / f)) for f, r in st["남의 파일"].items()}
'''),
    ("양성 ③ `!=` 로 견준다(어긋나면 붉어진다)", True, '''
import json, hashlib
from pathlib import Path
def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def check():
    d = json.loads(Path("runners/plantstamp.json").read_text())
    if d["코드 sha256"] != sha("lab/keyspace.py"):
        raise SystemExit("바뀌었다")
'''),
    ("음성 ① sha 를 **쓰기만** 하는 도장 생산기", False, '''
import json, hashlib
from pathlib import Path
def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def stamp():
    Path("runners/plantstamp.json").write_text(
        json.dumps({"코드 sha256": sha("lab/gitcall.py")}))
'''),
    ("음성 ② 기록된 sha 를 읽어 **인쇄만** 한다", False, '''
import json
from pathlib import Path
def show():
    d = json.loads(Path("runners/plantstamp.json").read_text())
    print(d["코드 sha256"])
'''),
]


def plant_check_stamp(root: Path = ROOT) -> dict:
    """🔴 대조 자의 **검정력** --- 심은 양성 셋을 잡고 음성 둘을 안 잡나."""
    import tempfile
    rows, missed, false_fire = {}, [], []
    with tempfile.TemporaryDirectory() as td:
        for i, (name, want, src) in enumerate(CHECK_PLANTS):
            t = ast.parse(src)
            bound = _json_bound(t)
            got = []
            for n in ast.walk(t):
                if not isinstance(n, ast.Compare):
                    continue
                if not any(isinstance(o, (ast.Eq, ast.NotEq)) for o in n.ops):
                    continue
                side = [n.left] + list(n.comparators)
                if any(_side_fresh(s) for s in side) and \
                        any(_side_stored(s, bound) and not _side_fresh(s) for s in side):
                    got.append(n.lineno)
            fired = bool(got)
            rows[name] = {"잡아야 하나": want, "🔴 잡았나": fired, "줄": got}
            if want and not fired:
                missed.append(name)
            if (not want) and fired:
                false_fire.append(name)
        _ = td
    return {
        "검사": "🔴 대조 자의 검정력(심어서 확인) --- 양성 셋 · 음성 둘",
        "자": CHECK_CRITERIA,
        "🔴 심은 양성(분모)": sum(1 for _n, w, _s in CHECK_PLANTS if w),
        "🔴 양성 중 잡은 수": sum(1 for _n, w, _s in CHECK_PLANTS if w) - len(missed),
        "🔴 심은 음성(분모)": sum(1 for _n, w, _s in CHECK_PLANTS if not w),
        "🔴 음성 오발 수": len(false_fire),
        "🔴 놓친 양성": missed or "없음",
        "🔴 오발한 음성": false_fire or "없음",
        "갈래별": rows,
        "통과": (not missed) and (not false_fire),
    }


# ── 🔴 949 --- 「면제 사유」에 붙이는 자 (티처 #88 M5 · ㄷ) ─────────────────
#: 판 계산 모듈로 치는 낱말 --- **947 의 P9 와 같은 자**(자를 갈면 채점이 안 이어진다).
BOARD_WORDS = ("board", "denominator", "verdict", "thresh")


def board_imports(rels, root: Path = ROOT) -> dict:
    """이 `.py` 들이 **판 계산 모듈을 import 하나** --- 사유 「판 계산 import 0」의 자.

    🔴 948 은 18 자리를 이 문자열로 닫아 놓고 **그 검사를 이 사이클에 안 돌렸다**
    (티처 #88 M5). 사유로 쓰려면 **그 실행 안에서 돌려 참을 내야** 한다.
    """
    out: dict = {}
    for rel in rels:
        p = root / rel
        if not p.exists():
            out[rel] = "🔴 파일 없음(「import 0」이 아니다 --- 조항 59)"
            continue
        try:
            t = ast.parse(p.read_text(encoding="utf-8"))
        except (SyntaxError, OSError, UnicodeDecodeError) as e:
            out[rel] = "🔴 못 읽었다: %s" % type(e).__name__
            continue
        mods = []
        for n in ast.walk(t):
            names = ([a.name for a in n.names] if isinstance(n, ast.Import) else
                     ([n.module] if isinstance(n, ast.ImportFrom) and n.module else []))
            mods += [m for m in names if any(w in m for w in BOARD_WORDS)]
        out[rel] = sorted(set(mods))
    return out


#: 🔴 **사유에 붙는 자의 등기부.** 사유 문자열이 ``[자:<이름>]`` 으로 시작하면 그 자를
#: 이 실행 안에서 돌린다. 없으면 ``🔴 자가 없다`` --- **그 자체가 신고할 값이다**.
RULER_MARK = re.compile(r"^\s*\[자:([^\]]+)\]\s*")


def exempt_rulers(exempt: dict, *, consumers=(), root: Path = ROOT) -> dict:
    """면제 사유마다 **자를 돌려** 참/거짓을 낸다(티처 #88 ㄷ · ㄹ).

    낸다: ``{경로: {"사유", "자", "🔴 자가 냈나"}}``. ``🔴 자가 냈나`` 가 ``True`` 인
    것만 「사유가 등록됐다」로 세야 한다 --- 그것이 ㉡ 대조의 새 ``B`` 다.
    """
    cons = set(consumers)
    def _tag(v):
        m = RULER_MARK.match(v or "")
        return m.group(1).strip() if m else None

    need = [p for p, v in exempt.items() if _tag(v) == "판import0"]
    imp = board_imports(need, root)
    out: dict = {}
    for p, v in sorted(exempt.items()):
        name = _tag(v)
        if name == "판import0":
            got = imp.get(p)
            ok = isinstance(got, list) and not got
            out[p] = {"사유": v, "자": "판 계산 모듈 import 0(AST · **이 실행 안에서**)",
                      "실측": got, "🔴 자가 냈나": bool(ok)}
        elif name == "모듈":
            #: 🔴 실행 진입점이 없으면 「안 돌렸다」가 아니라 **「돌릴 수 없다」**다.
            #: 🔴 문자열 검색이면 **자기 소스에 그 낱말을 적은 파일**이 걸린다
            #:    (첫 판이 `lab/gitcall.py` 에서 실제로 그렇게 샜다). AST 로 본다.
            has = True
            try:
                tt = ast.parse((root / p).read_text(encoding="utf-8"))
                has = any(isinstance(x, ast.If) and "__main__" in ast.dump(x.test)
                          for x in tt.body)
            except (OSError, UnicodeDecodeError, SyntaxError):
                pass
            out[p] = {"사유": v, "자": "실행 진입점(`__main__`)이 없다 --- 모듈이다",
                      "실측": {"`__main__` 이 있나": has}, "🔴 자가 냈나": not has}
        elif name == "자기자신":
            out[p] = {"사유": v, "자": "이 실행 자신이다(지금 도는 러너)",
                      "실측": p, "🔴 자가 냈나": True}
        elif name == "소비자아님":
            out[p] = {"사유": v, "자": "1 절 역참조 소비자 목록에 없다",
                      "실측": p in cons, "🔴 자가 냈나": p not in cons}
        else:
            out[p] = {"사유": v,
                      "자": "🔴 자가 없다 --- 사유는 문자열일 뿐이고 아무것도 안 잰다",
                      "🔴 자가 냈나": False}
    return out


# ── 절 ────────────────────────────────────────────────────────────────────
def census(root: Path = ROOT, *, harm: bool = True, chk: dict | None = None) -> dict:
    """🔴 **경로를 내는 git 호출 전수** --- 자 둘 · 조항 62 로 차를 낸다.

    🔴🔴 **949 (티처 #88 C1)**: ``㉮`` 의 증거를 **도장에서 대조로** 바꿨다.
    947~948 은 ``sha_cited``(= 산출물에 박힌 코드 sha256 **인용**)를 「고치면 깨지는
    대조」로 읽었다. 그것은 **도장**이다 --- 소스를 고쳐도 그 기록은 그때의 sha 를
    적은 것이라 여전히 참이고 **아무 검사도 안 붉어진다.** 이제 ``checkers()`` 가
    ``CHECK_CRITERIA`` 셋을 다 채우는 자리만 세고, **도장 수는 따로** 싣는다.
    """
    pys = sorted(ks.git_paths("ls-files", "--", "*.py", root=root))
    if chk is None:
        chk = checkers(root)
    src_cache: dict[str, list[str]] = {}
    cite_cache: dict[str, tuple] = {}
    sites = []
    for rel, line, vec, kind in sites_ast(pys, root):
        ok, why = emits_paths(vec)
        if not ok:
            continue
        canon = kind.startswith("②′")
        has_z, has_q = safety(vec)
        frozen = rel.startswith(FROZEN_PREFIX)
        intent = INTENTIONAL.get((rel, line)) or _marked(rel, line, root, src_cache)
        # 🔴🔴 **948 --- 증거를 먼저 본다**(티처 #87 C3).
        #    947 은 `frozen`(이름 접두사)을 `cited`(증거)보다 **먼저** 판정했다.
        #    그래서 **동결 접두사만 맞으면 증거를 안 보고 ㉮**(원리상 못 고친다)가 됐고
        #    ㉯ 가 이름만으로 0 이 됐다. 순서를 뒤집는다.
        if (has_z or has_q or canon):
            cited, cited_narrow = [], []
        else:
            if rel not in cite_cache:
                cite_cache[rel] = (sha_cited(rel, root),
                                   sha_cited(rel, root,
                                             pathspec=NARROW_CITE_PATHSPEC))
            cited, cited_narrow = cite_cache[rel]
        checked = ([] if (has_z or has_q or canon) else check_cited(rel, chk))
        sites.append({
            "파일:줄": f"{rel}:{line}", "자리": kind, "인자": vec,
            "왜 경로를 내나": why,
            "-z": has_z, "core.quotePath=false": has_q,
            "갈래": ("안전(정본 판독기 --- `-z`·quotePath 를 함수가 붙인다)" if canon else
                   "안전(정본)" if has_z and has_q else
                   "안전(-z)" if has_z else
                   "안전(quotePath=false)" if has_q else
                   "🔴 의도적 날 것(음성 대조)" if intent else "🔴 날 것"),
            "동결(941~946)": frozen,
            "사유": intent,
            # 🔴 949 --- **도장**과 **대조**를 두 칸으로 갈라 싣는다(티처 #88 C1)
            "⚠ 도장(stamp) --- 지금 sha 를 인용하는 커밋된 파일(HEAD 전량)": cited,
            "🔴 대조(check) --- 고치면 실제로 깨지는 자리": checked,
            "⚠ 947 의 좁은 자로 세면(음성 대조 · 판정에 쓰지 마라)": cited_narrow,
            # 🔴🔴 **낱말 셋은 그대로**(티처 #87 C3). 🔴 949 가 바꾼 것은 **㉮ 의 증거**다:
            #    ㉮ = **원리상** 못 고친다(증거: **대조** ≥1 --- 고치면 그 검사가 붉어진다)
            #    ㉲ = **규약상** 안 고친다(동결물 수정 금지 --- 그러나 깨지는 대조는 없다)
            #    ㉯ = 고칠 수 있다. 🔴 **㉲ 는 ㉯ 의 부분집합이다** --- 분모에서 안 뺀다.
            "🔴 ㉮/㉯/㉲": (
                None if (has_z or has_q or intent or canon) else
                "㉮ 원리상 못 고친다 --- 이 파일을 **대조**하는 자리가 %d 개다"
                "(고치면 그 검사가 실제로 붉어진다)" % len(checked) if checked else
                "🔴 ㉯-㉲ 규약상 안 고친다 --- 941~946 동결이라 「동결물 수정 금지」가 "
                "막는다. 🔴 **그러나 깨지는 대조는 0 이다**(도장 %d 개는 대조가 아니다) "
                "--- 원리상 못 고치는 것이 아니다(티처 #87 C3 · #88 C1)" % len(cited)
                if frozen else
                "🔴 ㉯ 고칠 수 있다 --- 막는 것이 아무것도 없다(도장 %d · 대조 0)"
                % len(cited)),
            "🔴 실해": (_run_both(vec, root)
                    if (harm and not (has_z or has_q or canon))
                    else "해당 없음(안전한 자리)"),
        })

    raw = [s for s in sites if s["갈래"] == "🔴 날 것"]
    intent = [s for s in sites if s["갈래"].startswith("🔴 의도적")]
    safe = [s for s in sites if s["갈래"].startswith("안전")]
    raw_b = [s for s in raw if s["🔴 ㉮/㉯/㉲"].startswith("🔴 ㉯")]      # ㉯ 전량(㉲ 포함)
    raw_a = [s for s in raw if s["🔴 ㉮/㉯/㉲"].startswith("㉮")]
    raw_d = [s for s in raw_b if s["🔴 ㉮/㉯/㉲"].startswith("🔴 ㉯-㉲")]  # ㉯ 안의 ㉲
    raw_pure = [s for s in raw_b if s not in raw_d]

    # ── 🔴🔴 래칫 --- 티처 #87 C3 이 「그 성질이 산출물 어디에도 안 적혔다」로 잡은 것
    ratchet = {}
    for s in raw:
        rel = s["파일:줄"].rsplit(":", 1)[0]
        if rel in ratchet:
            continue
        cs = s["⚠ 도장(stamp) --- 지금 sha 를 인용하는 커밋된 파일(HEAD 전량)"]
        ratchet[rel] = {
            "도장 수": len(cs), "도장을 찍은 파일": cs,
            "🔴 대조 수": len(s["🔴 대조(check) --- 고치면 실제로 깨지는 자리"]),
            "인용 수": len(cs), "인용한 파일": cs,
            "이 소스의 마지막 커밋": last_commit(rel, root),
            "인용 파일의 마지막 커밋": {c: last_commit(c, root) for c in cs},
        }

    # ── 🔴 자 둘의 차 --- 조항 62 (혼자 못 실린다) ──────────────────────
    a_set = {s["파일:줄"] for s in sites}
    b_set = set(sites_regex(pys, root))
    rep = diff62("자 A(AST · 실제 호출 자리)", a_set,
                 "자 B(텍스트 · 줄 단위)", b_set,
                 probe=lambda x: _escape_path_part(x))
    return {
        "검사": "1-나 🔴 경로를 내는 git 호출 전수 --- 자 둘(AST · 텍스트) · 조항 62",
        "🔴 바늘": {
            "하위명령만으로 경로를 내는 것": list(PATH_SUBS_ALWAYS),
            "플래그가 있어야 내는 하위명령": list(PATH_SUBS_COND),
            "경로 플래그": list(PATH_FLAGS),
            "🔴 946 의 바늘(넷)": ["ls-files", "ls-tree", "--name-only", "--name-status"],
            "🔴 946 이 통째로 못 본 것": sorted(
                (set(PATH_SUBS_ALWAYS) | set(PATH_SUBS_COND) | set(PATH_FLAGS))
                - {"ls-files", "ls-tree", "--name-only", "--name-status"}),
        },
        "🔴 자 A 가 보는 갈래 넷": ["① argv 리터럴", "② 래퍼 호출(같은 파일 **및 남의 모듈**)",
                          "③ f-string/`%` 조립", "④ 셸 문자열"],
        "🔴 분모 ① 훑은 .py": len(pys),
        "🔴 분모 ② 자 A 호출 자리(경로를 내는 것만)": len(sites),
        "🔴 분모 ③ 자 B 줄 히트": len(b_set),
        "🔴 분모 ④ 날 것": len(raw),
        "🔴 분모 ④-㉮ 원리상 못 고친다(🔴 **대조** ≥ 1 · 949 가 도장에서 갈아탄 자)": len(raw_a),
        "⚠ 참고 --- 947~948 의 옛 자(도장 ≥ 1)로 세면 ㉮ 는": len(
            [s for s in raw if s["⚠ 도장(stamp) --- 지금 sha 를 인용하는 커밋된 파일(HEAD 전량)"]]),
        "🔴 분모 ④-㉯ 고칠 수 있다(🔴 이 수가 0 이어야 통과)": len(raw_b),
        "🔴 분모 ④-㉲ 그중 규약상 안 고친다(동결 · ㉯ 의 부분집합)": len(raw_d),
        "🔴 분모 ④-순㉯ 막는 것이 아무것도 없는 것": len(raw_pure),
        "🔴 ㉯ 목록(㉲ 포함)": [s["파일:줄"] for s in raw_b],
        # 🔴 **dict 가 아니라 목록이다**(티처 #87 M8). 같은 `파일:줄` 이 두 갈래로
        #    잡히면 dict 는 **조용히 하나를 삼킨다** --- 947 실물: 날 것 15 대 dict 13.
        "㉮ 목록과 사유": [{"파일:줄": s["파일:줄"], "자리": s["자리"],
                      "사유": s["🔴 ㉮/㉯/㉲"]} for s in raw_a],
        "🔴 ㉯/㉲ 목록과 사유": [{"파일:줄": s["파일:줄"], "자리": s["자리"],
                          "사유": s["🔴 ㉮/㉯/㉲"]} for s in raw_b],
        "🔴🔴 래칫(티처 #87 C3 --- 이 성질을 산출물에 적는다)": {
            "무엇": ("㉮ 의 유일한 증거는 **sha 인용**이고, 인용은 산출물이 커밋될 때마다 "
                   "**늘기만 한다**. 그러므로 ㉮ 는 **단조 증가**하고 되돌아오는 길이 "
                   "없다 --- 🔴 **고칠수록 못 고칠 자리가 는다**"),
            "🔴 왜 되돌아오는 길이 없나": (
                "인용을 지우려면 **커밋된 산출물을 고쳐야** 하는데 산출물은 증거물이라 "
                "안 고친다. 그래서 ㉮ → ㉯ 로 가는 문은 **규약상 닫혀 있다**"),
            "🔴🔴 949 정정 --- 그 인용은 「대조」가 아니라 전부 「도장」이었다": (
                "산출물에 박힌 코드 sha256 은 **「이 코드가 이 산출물을 냈다」는 기록**이지 "
                "**「이 코드가 안 바뀌었다」는 대조**가 아니다. 소스를 고쳐도 그 기록은 "
                "여전히 참이다(그때의 sha 를 적은 것이므로). 948 은 둘을 안 갈랐고 "
                "🔴 **949 가 `checkers()` 로 갈랐다** --- 그러자 **래칫은 ㉮ 에 안 걸린다**. "
                "도장은 늘기만 하지만 **도장은 아무것도 막지 않으므로** 「고칠수록 못 고칠 "
                "자리가 는다」는 **거짓**이다. 🔴 되돌아오는 길은 **처음부터 열려 있었다**"),
            "🔴 오늘의 눈금": {
                "날 것 자리 수": len(raw),
                "도장 ≥ 1 인 소스 파일 수": len([r for r in ratchet.values() if r["도장 수"]]),
                "도장 0 인 소스 파일 수": len([r for r in ratchet.values() if not r["도장 수"]]),
                "🔴 대조 ≥ 1 인 소스 파일 수":
                    len([r for r in ratchet.values() if r["🔴 대조 수"]]),
                "소스 파일 수(분모)": len(ratchet),
                "도장 총 수": sum(r["도장 수"] for r in ratchet.values()),
                "🔴 대조 총 수": sum(r["🔴 대조 수"] for r in ratchet.values()),
            },
            "파일별": ratchet,
            "🔴 안 쟀다": ("옛 트리들에서 이 눈금을 다시 재면 **래칫이 실제로 단조 증가했는지**를 "
                       "보일 수 있다. 오늘은 **안 쟀다**(한 트리의 한 값뿐이다 --- 조항 60: "
                       "한 표본으로 원천의 성질을 말하지 마라). **「단조 증가한다」는 기제의 "
                       "주장이지 오늘 잰 값이 아니다**"),
        },
        "분모 ⑤ 의도적 날 것(음성 대조)": len(intent),
        "분모 ⑥ 안전": len(safe),
        "🔴🔴 949 --- 도장/대조 가르기": {
            "자": CHECK_CRITERIA,
            "🔴 대조 자리 수(트리 전량)": chk["🔴 대조 자리 수"],
            "🔴 대조가 덮는 파일 수": chk["🔴 대조가 덮는 파일 수"],
            "🔴 대상을 못 푼 대조 자리 수(「모른다」)":
                chk["🔴 대상을 못 푼 자리 수(「모른다」 --- 「없다」가 아니다)"],
            "🔴 날 것 소스 중 대조로 덮인 것": sorted(
                {s["파일:줄"].rsplit(":", 1)[0] for s in raw
                 if s["🔴 대조(check) --- 고치면 실제로 깨지는 자리"]}),
            "이 자로 안 센 갈래(rev 기준)":
                chk["🔴 이 자로 안 센 갈래(rev 기준 비교 · 기록된 상수와 안 견준다)"]["수"],
        },
        "🔴 자 A 와 자 B 의 차(조항 62 --- 혼자 못 싣는다)": rep,
        "🔴 날 것 전량(목록)": raw,
        "의도적 날 것(목록)": intent,
        "안전(목록)": safe,
        "통과": len(raw_b) == 0,
        "🔴 통과의 뜻": ("**㉯(고칠 수 있는데 안 고친 것)가 0** 이면 통과. ㉮ 는 분모에 남는다. "
                   "🔴 **㉲(규약상 안 고친다)는 ㉯ 안에 있다** --- 947 은 그것을 ㉮ 로 "
                   "옮겨 분모를 비웠고, 그것이 티처 #87 C3 이 잡은 것이다"),
    }


#: 🔴🔴 **번호 충돌을 닫는 자리** --- 티처 #86 M1.
#:
#: 「조항 61」은 **세 뜻**으로 쓰이고 있었다:
#: ① **규약 61**(「`T` 는 문턱이 아니라 민감도 비 `r`」) ② **옛 조항 61**(「증거력의
#: 한계를 먼저 적는다」 · `docs/prereg_918_interval.md:7`·`prereg_922_permfix.md:13`
#: 이 인용하는데 **정의가 어디에도 없었다**) ③ **새 조항 61**(「차집합은 홀로 못 선다」
#: · 946 신설). 셋 중 옮기는 값이 가장 싼 것이 ③ 이라 **조항 62** 로 옮긴다.
#:
#: 🔴 **그런데 구현(`lab/keyspace.diff_report`)의 글자는 못 고친다** ---
#: `lab/keyspace.py` 의 지금 sha 를 `out946_quotefix.json`·`out946_recount.json`
#: **둘이 인용**한다(실측). 고치면 그 대조가 깨진다 = ㉮ 다.
#: 그래서 **글자를 고치는 대신 이 껍데기를 지나게 한다** --- 앞으로 나오는 산출물은
#: 전부 「조항 62」로 적힌다. 옛 산출물은 「조항 61」로 남고, 그 지도는
#: `docs/루프.md` 의 이름 지도 표에 있다.
ARTICLE62 = "🔴 조항 62 --- 차집합은 홀로 못 선다(반대 방향 · 예시 다섯 · 심은 키)"


#: 🔴 **양쪽에 넣는 대조 원소.** 두 인코딩이 갈리는(비-ASCII) 추적 경로 하나 ---
#: 947 이 이 검사를 위해 분모를 0 → 1 로 올린 그 파일이다.
CONTROL_SEED = "lab/fixtures/한글이름_고정물.py"


class SeedPadError(ValueError):
    """🔴 대조 원소를 양쪽에 넣으면 **판정용 차집합이 바뀐다**(티처 #88 C2)."""


def diff62_guarded(a_name, A, b_name, B, *, seed_pad: str = "", **kw) -> dict:
    """``diff62`` 를 부르되 ``SeedPadError`` 를 **삼키지 않고 붉게 싣는다**.

    🔴 여기서 대조 원소를 **안 넣고** 다시 부른다 --- 그래야 ``A−B`` 가 참값으로
    나온다. 대신 ④ 심은 키를 못 심어 ``통과`` 가 ``False`` 가 될 수 있는데,
    **그것이 옳다**: 「심을 자리가 없다」를 「심었다」로 만드는 길이 바로
    948 이 걸린 병이다(검사를 통과시키려고 입력을 바꾸는 것).
    """
    if not seed_pad:
        return diff62(a_name, A, b_name, B, **kw)
    try:
        return diff62(a_name, A, b_name, B, seed_pad=seed_pad, **kw)
    except SeedPadError as e:
        rep = diff62(a_name, A, b_name, B, **kw)
        rep["🔴🔴 대조 원소를 못 심었다(949 · 티처 #88 C2)"] = {
            "왜": str(e),
            "🔴 그래서 무엇을 했나": ("대조 원소를 **안 넣고** 다시 쟀다. 위 `A−B`·`B−A` 는 "
                             "**참값**이다 --- 948 은 여기서 원소 하나를 조용히 지웠다"),
            "⚠ 대가": ("④ 심은 키를 못 심으면 이 대조는 `모른다` 를 내고 `통과 False` 가 "
                     "된다. **붉은 채로 싣는다**"),
        }
        return rep


def diff62(a_name, A, b_name, B, *, seed_pad: str = "", **kw) -> dict:
    """`lab.keyspace.diff_report` 를 부르고 **번호만 62 로 고쳐** 낸다.

    🔴 **948 이 더한 것 둘** (티처 #87 M3 · m3):

    **① `seed_pad`** --- ``diff_report`` 의 ④ 심은 키는 **``A∩B`` 에 두 인코딩이
    갈리는 원소가 있어야** 심을 수 있다. 없으면 그 절은 영원히 ``모른다`` 를 내고,
    그러면 **구조적으로 영원히 붉은 절**이 하나 는다(티처 #87 M2 가 규탄한 모양).
    🔴 그래서 **같은 원소를 양쪽에 하나 넣는다** --- 집합 항등으로
    ``A−B`` 와 ``B−A`` 는 **한 원소도 안 바뀐다.** 바뀌는 것은 ``|A|``·``|B|``
    각각 **+1** 뿐이고, 그 사실을 산출물에 적는다. 판정에 쓰는 차집합은 그대로다.

    **② ``모른다`` 문안의 정정** --- ``keyspace`` 의 ``UNKNOWN`` 은
    *"심은 키를 못 찾았다(검출기가 두 번째 인코딩을 못 본다)"* 한 문장인데,
    ③ 이 두 이름을 **잡았을 때도** 그 문장이 찍힌다(947 산출물에 **세 번** 찍혔다).
    🔴 **잡은 것을 「못 본다」로 인쇄하는 것**이라 뜻이 반대다. 글자(``lab/keyspace.py``)는
    그 sha 를 946·947 산출물 셋이 인용해서 못 고치므로 **이 껍데기에서 덮어쓴다** ---
    947 이 **번호에는 쓴 길을 뜻에는 안 썼다**(티처 #87 m3).
    """
    A, B = set(A), set(B)
    pad = None
    if seed_pad:
        # 🔴🔴 **949 (티처 #88 C2)** --- 948 은 여기에 「집합 항등이라 `A−B`·`B−A` 는
        #    한 원소도 안 바뀐다」고 **단언**했다. **거짓이다**:
        #        (A∪{s}) − (B∪{s}) = (A−B) − {s}
        #    이므로 `s ∈ A△B` 이면 **원소 하나가 조용히 사라진다.**
        #    948 은 실제로 그 길로 판정용 차집합을 162 → 161 로 바꿨다.
        if seed_pad in (A ^ B):
            raise SeedPadError(
                "🔴 대조 원소 `%s` 가 A△B 에 있다 --- 양쪽에 넣으면 `A−B`(또는 `B−A`)에서 "
                "**원소 하나가 사라진다**(`(A∪{s})−(B∪{s}) = (A−B)−{s}`). "
                "A=%s · B=%s · A 에 있나=%s · B 에 있나=%s"
                % (seed_pad, a_name, b_name, seed_pad in A, seed_pad in B))
        pad = {"🔴 무엇": ("④ 심은 키를 심을 자리(`A∩B` 안의 두 인코딩이 갈리는 원소)가 "
                        "없어서 **대조 원소 하나를 양쪽에** 넣었다"),
               "원소": seed_pad,
               "🔴 A−B · B−A 가 바뀌나": ("아니다 --- 🔴 **949 가 이것을 검사로 바꿨다**: "
                                  "`seed_pad ∈ A△B` 면 예외를 던진다. 여기까지 왔다는 "
                                  "것은 그 원소가 양쪽에 다 있거나 양쪽에 다 없다는 뜻이다"),
               "⚠ |A|·|B| 는 각각 +1 이다": True,
               "🔴 A△B 에 있었나(있으면 예외)": False,
               "이미 A 에 있었나": seed_pad in A, "이미 B 에 있었나": seed_pad in B}
        A = A | {seed_pad}
        B = B | {seed_pad}
    rep = ks.diff_report(a_name, A, b_name, B, **kw)
    if pad is not None:
        rep["🔴 양쪽에 넣은 대조 원소"] = pad
    # ── ② 「모른다」 문안 정정 -------------------------------------------
    seen = rep.get("③ 두 이름 대조")
    twins = (isinstance(seen, dict) and
             (seen.get("🔴 A − B 중 B 에 두 번째 인코딩으로 있는 것", 0) or
              seen.get("🔴 B − A 중 A 에 첫 인코딩으로 있는 것", 0)))
    plant = rep.get("④ 심은 키")
    fired = isinstance(plant, dict) and bool(plant.get("🔴 발화했나"))
    if twins:
        fixed = ("🔴 모른다 --- **검출기는 두 번째 인코딩을 봤다**(③ 이 잡았다%s). "
                 "수를 안 내는 이유는 이 차집합이 「없는 원소」가 아니라 **두 이름**이기 "
                 "때문이다 --- 947 은 여기에 「검출기가 못 본다」를 찍었다(티처 #87 m3)"
                 % (" · ④ 심은 키도 발화했다" if fired else
                    " · 🔴 다만 ④ 심은 키는 **발화 안 했다** --- 눈이 있는지는 모른다"))
        for k, v in list(rep.items()):
            if v == ks.UNKNOWN:
                rep[k] = fixed
    rep["조항"] = ARTICLE62
    rep["⚠ 옛 이름"] = ("이 조항은 946 이 **조항 61** 로 신설했고 947 이 **조항 62** 로 "
                   "옮겼다(티처 #86 M1 --- 「조항 61」이 세 뜻으로 쓰이고 있었다). "
                   "구현 파일 `lab/keyspace.py` 의 글자는 그 sha 를 946 산출물 둘이 "
                   "인용해서 못 고친다(㉮) --- 이 껍데기가 번호를 갈음한다")
    return rep


def _marked(rel: str, line: int, root: Path, cache: dict) -> str | None:
    """호출 자리 **위 여섯 줄 안**의 `# 날것허용: …` 표지를 읽는다.

    🔴 줄 번호를 러너에 손으로 박는 대신 **소스에 표지를 둔다** ---
    파일을 고쳐도 표지가 같이 움직인다(946 의 `줄 = 0` 파일 단위 면제가
    진짜 날 것 셋을 통째로 면제한 그 병의 수리).
    """
    if rel not in cache:
        try:
            cache[rel] = (root / rel).read_text(encoding="utf-8").split("\n")
        except (UnicodeDecodeError, OSError):
            cache[rel] = []
    lines = cache[rel]
    for i in range(max(0, line - 1 - INTENT_LOOKBACK), min(len(lines), line + 1)):
        m = INTENT_MARK.search(lines[i])
        if m:
            return m.group(1).strip()
    return None


def _escape_path_part(s: str) -> str:
    """``rel:line`` 의 **경로 부분만** 두 번째 인코딩으로 바꾼다(심은 키용).

    🔴 두 자가 같은 파일을 **다른 이름**으로 부를 수 있다 --- 한쪽이 ``git grep``
    출력(이스케이프)에서, 다른 쪽이 정본에서 왔을 때. 그것이 여기서 잴 두 번째 인코딩이다.
    """
    rel, _, line = s.rpartition(":")
    if not rel:
        return ks.octal_escape(s)
    e = ks.octal_escape(rel)
    return f"{e}:{line}" if e != rel else s


# ── 🔴 심어서 확인 (검정력) ────────────────────────────────────────────────
PLANTS = [
    ("① argv 리터럴", '''
import subprocess
def f():
    return subprocess.run(["git", "status", "--porcelain"], capture_output=True)
'''),
    ("② 같은 파일의 래퍼", '''
import subprocess
def _g(a):
    return subprocess.run(["git"] + a, capture_output=True)
def f():
    return _g(["grep", "-l", "-e", "x"])
'''),
    ("③ 🔴 남의 모듈에서 import 한 래퍼", '''
from runners.fiveprime902 import _git
def f():
    return _git(["status", "--porcelain"])
'''),
    ("④ 셸 문자열", '''
import subprocess
def f():
    return subprocess.run("git ls-files --name-only", shell=True)
'''),
    ("⑤ f-string 조립", '''
import subprocess
def f(ref):
    cmd = f"git log {ref} --name-only"
    return subprocess.run(cmd, shell=True)
'''),
]

#: 946 의 옛 바늘 --- 음성 대조용. 이것으로 몇을 잡나를 같이 낸다.
OLD_TOKENS = ("ls-files", "ls-tree", "--name-only", "--name-status")

#: 🔴 **옛 바늘의 양성 대조.** 위 다섯에서 옛 바늘이 **0** 을 내는데, 그것이
#: 「사각지대」인지 「내가 옛 바늘을 잘못 재현했다」인지 갈라야 한다(조항 59 ---
#: 빈 것을 부정으로 읽지 마라). 이 자리는 **옛 바늘이 반드시 잡아야 한다.**
OLD_CONTROL = ("🔴 옛 바늘의 양성 대조(946 이 실제로 잡던 꼴)", '''
import subprocess
def f():
    return subprocess.run(["git", "ls-tree", "-r", "HEAD", "--name-only"],
                          capture_output=True)
''')


def plant_check(root: Path = ROOT) -> dict:
    """🔴 **심어서 확인** --- 새 바늘이 다섯 갈래를 다 잡나 · 옛 바늘은 몇을 잡나.

    「넓혔다」를 말로 하지 않는다. **심고 발화를 센다**(조항 59).
    """
    import tempfile
    #: 🔴 **저장소의 래퍼 등기부를 넘겨준다** --- 안 넘기면 갈래 ③(남의 모듈에서
    #: import 한 래퍼)이 임시 파일 하나만 보는 등기부로는 원리상 안 잡힌다.
    #: 「안 잡혔다」를 「그 갈래가 없다」로 읽을 뻔한 자리다(조항 59).
    reg = wrapper_registry(sorted(ks.git_paths("ls-files", "--", "*.py", root=root)), root)
    rows, missed, old_hit = {}, [], []
    with tempfile.TemporaryDirectory() as td:
        for i, (name, src) in enumerate(PLANTS):
            p = Path(td) / ("plant%d.py" % i)
            p.write_text(src, encoding="utf-8")
            got = [(l, v, k) for _r, l, v, k in
                   sites_ast(["plant%d.py" % i], Path(td), reg)]
            path_sites = [(l, v, k) for l, v, k in got if emits_paths(v)[0]]
            new_ok = bool(path_sites)
            # 옛 바늘 재현: 리스트 첫 원소 "git" + 같은 파일 래퍼 + 토큰 넷
            old_ok = _old_needle(p)
            rows[name] = {"🔴 새 바늘이 잡았나": new_ok,
                          "옛 바늘(946)이 잡았나": old_ok,
                          "잡은 자리": [f"{l}:{k}:{v}" for l, v, k in path_sites]}
            if not new_ok:
                missed.append(name)
            if old_ok:
                old_hit.append(name)

        # 🔴 음성 대조 --- **안전한** 자리를 날 것으로 오분류하나
        ctl = Path(td) / "ctl.py"
        ctl.write_text('''
import subprocess
def f():
    return subprocess.run(["git", "-c", "core.quotePath=false",
                           "status", "--porcelain", "-z"], capture_output=True)
''', encoding="utf-8")
        cvec = [v for _r, _l, v, _k in sites_ast(["ctl.py"], Path(td), reg)]
        ctl_raw = [v for v in cvec if emits_paths(v)[0] and not any(safety(v))]

        # 🔴 옛 바늘의 **양성 대조** --- 위의 0/5 가 「사각지대」인지
        #    「내가 옛 바늘을 잘못 재현했다」인지 가른다(조항 59).
        oc = Path(td) / "oldctl.py"
        oc.write_text(OLD_CONTROL[1], encoding="utf-8")
        old_ctl = _old_needle(oc)
        new_ctl = any(emits_paths(v)[0]
                      for _r, _l, v, _k in sites_ast(["oldctl.py"], Path(td), reg))
    return {
        "검사": "1-다 🔴 심어서 확인 --- 새 바늘의 검정력(말이 아니라 발화)",
        "🔴 심은 갈래(분모)": len(PLANTS),
        "🔴 새 바늘이 잡은 수": len(PLANTS) - len(missed),
        "🔴 새 바늘이 놓친 것": missed or "없음",
        "🔴 옛 바늘(946)이 잡은 수": len(old_hit),
        "옛 바늘이 잡은 것": old_hit,
        "🔴 옛 바늘이 못 본 갈래": [n for n, _ in PLANTS if n not in old_hit],
        "갈래별": rows,
        "🔴 음성 대조(안전한 자리를 날 것으로 오분류하나)": {
            "오분류 수": len(ctl_raw), "예시": ctl_raw[:2],
            "⚠": "0 이어야 한다 --- 아니면 이 자는 「전부 날 것」을 내는 눈먼 자다"},
        "🔴 옛 바늘의 양성 대조": {
            "심은 것": OLD_CONTROL[0],
            "🔴 옛 바늘이 잡았나": old_ctl, "새 바늘이 잡았나": new_ctl,
            "⚠ 왜 이게 있나": ("위 다섯에서 옛 바늘이 **0** 을 냈다. 그 0 이 "
                        "「사각지대」인지 「내가 옛 바늘을 잘못 재현했다」인지 "
                        "가르는 자리다 --- **「없다」와 「못 봤다」는 둘이다**(조항 59). "
                        "🔴 여기서 옛 바늘이 False 면 위의 0/5 는 **판정에 못 쓴다**")},
        "통과": (not missed) and (not ctl_raw) and old_ctl and new_ctl,
    }


def _old_needle(p: Path) -> bool:
    """946 의 자를 **그대로 재현**한다(같은 파일 래퍼 + 토큰 넷 + 리스트 리터럴)."""
    try:
        tree = ast.parse(p.read_text(encoding="utf-8"))
    except (SyntaxError, OSError):
        return False
    wrappers = set()
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for n in ast.walk(fn):
            if isinstance(n, ast.Call) and (
                    getattr(n.func, "attr", None) in ("run", "Popen", "check_output",
                                                      "getoutput", "call", "check_call")
                    or getattr(n.func, "id", None) in ("run", "Popen")):
                if any(isinstance(c, ast.Constant) and c.value == "git"
                       for c in ast.walk(n)):
                    wrappers.add(fn.name)
    for n in ast.walk(tree):
        vec = None
        if isinstance(n, (ast.List, ast.Tuple)):
            c = [e.value for e in n.elts
                 if isinstance(e, ast.Constant) and isinstance(e.value, str)]
            if c and c[0] == "git":
                vec = c
        elif isinstance(n, ast.Call):
            fn = getattr(n.func, "id", None) or getattr(n.func, "attr", "?")
            if fn in wrappers:
                vec = _consts(n)
        if vec and any(t in vec for t in OLD_TOKENS):
            return True
    return False
