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

#: 동결 --- 941~946 의 러너·산출물. 스탬프가 코드 sha256 을 담아 **주석 한 줄도** 대조를 깬다.
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
def _run_both(vec: list[str], root: Path = ROOT) -> dict:
    """같은 인자를 **날 것과 정본으로 둘 다** 돌려 차를 실측한다.

    🔴 이 함수의 날 것 쪽은 **의도적**이다(``INTENTIONAL``) --- 여기서 인용을
    끄면 「날 것은 그 설정을 탄다」를 못 잰다.
    """
    body = [x for x in vec if x != "git"]
    if not body or any("\x00" in x for x in body):
        return {"🔴 못 돌렸다": "인자에 동적 값이 섞여 이 자리를 재현할 수 없다 "
                          "--- **「무해」가 아니라 「못 쟀다」다**(조항 59)"}
    if body[0] not in ("ls-files", "ls-tree", "status", "grep"):
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


def _sha_cited(rel: str, root: Path = ROOT) -> list[str]:
    """이 파일의 **지금 sha256** 을 인용하는 커밋된 산출물(㉮ 판정의 근거).

    🔴 946 의 같은 함수는 ``git grep -lF`` 를 **날 것으로** 불렀다(티처 #86 C1).
    여기서는 ``lab.keyspace`` 정본을 지난다.
    """
    import hashlib
    p = root / rel
    if not p.exists():
        return []
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    try:
        return sorted(grep_files([h], root=root,
                                 pathspec=("runners/*.json", "data/lab/*.json")))
    except ks.GitError:
        return []


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


# ── 절 ────────────────────────────────────────────────────────────────────
def census(root: Path = ROOT, *, harm: bool = True) -> dict:
    """🔴 **경로를 내는 git 호출 전수** --- 자 둘 · 조항 62 로 차를 낸다."""
    pys = sorted(ks.git_paths("ls-files", "--", "*.py", root=root))
    src_cache: dict[str, list[str]] = {}
    sites = []
    for rel, line, vec, kind in sites_ast(pys, root):
        ok, why = emits_paths(vec)
        if not ok:
            continue
        canon = kind.startswith("②′")
        has_z, has_q = safety(vec)
        frozen = rel.startswith(FROZEN_PREFIX)
        intent = INTENTIONAL.get((rel, line)) or _marked(rel, line, root, src_cache)
        cited = [] if (has_z or has_q or canon) else _sha_cited(rel, root)
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
            "🔴 지금 sha 를 인용하는 산출물": cited,
            "🔴 ㉮/㉯": (None if (has_z or has_q or intent or canon) else
                     "㉮ 원리상 못 고친다 --- 941~946 동결" if frozen else
                     "㉮ 원리상 못 고친다 --- 이 파일의 지금 sha 를 산출물 %d 개가 "
                     "인용한다" % len(cited) if cited else "🔴 ㉯ 고칠 수 있다"),
            "🔴 실해": (_run_both(vec, root)
                    if (harm and not (has_z or has_q or canon))
                    else "해당 없음(안전한 자리)"),
        })

    raw = [s for s in sites if s["갈래"] == "🔴 날 것"]
    intent = [s for s in sites if s["갈래"].startswith("🔴 의도적")]
    safe = [s for s in sites if s["갈래"].startswith("안전")]
    raw_b = [s for s in raw if s["🔴 ㉮/㉯"].startswith("🔴 ㉯")]
    raw_a = [s for s in raw if s["🔴 ㉮/㉯"].startswith("㉮")]

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
        "🔴 분모 ④-㉮ 원리상 못 고친다": len(raw_a),
        "🔴 분모 ④-㉯ 고칠 수 있다(🔴 이 수가 0 이어야 통과)": len(raw_b),
        "🔴 ㉯ 목록": [s["파일:줄"] for s in raw_b],
        "㉮ 목록과 사유": {s["파일:줄"]: s["🔴 ㉮/㉯"] for s in raw_a},
        "분모 ⑤ 의도적 날 것(음성 대조)": len(intent),
        "분모 ⑥ 안전": len(safe),
        "🔴 자 A 와 자 B 의 차(조항 62 --- 혼자 못 싣는다)": rep,
        "🔴 날 것 전량(목록)": raw,
        "의도적 날 것(목록)": intent,
        "안전(목록)": safe,
        "통과": len(raw_b) == 0,
        "🔴 통과의 뜻": "**㉯(고칠 수 있는데 안 고친 것)가 0** 이면 통과. ㉮ 는 분모에 남는다",
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


def diff62(*args, **kw) -> dict:
    """`lab.keyspace.diff_report` 를 그대로 부르고 **번호만 62 로 고쳐** 낸다."""
    rep = ks.diff_report(*args, **kw)
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
