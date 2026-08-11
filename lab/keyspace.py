"""외부 이름 공간의 **정본 판독기** --- 노트 946 (티처 #85 처방).

## 왜 있나

이 저장소가 세계를 재는 방식은 거의 전부 **「문자열 키 집합의 차집합」**이다:
``disk − map`` · ``roster − ran`` · ``names − readers`` · ``head or all``.
그런데 **키 공간은 항상 남이 만들고**(git 의 인용 여부 · npz ``names`` ·
JSON 중첩 깊이 · 도메인별 필드명) **거의 모든 외부 키 공간은 인코딩이 둘 이상이다.**

🔴 그래서 **차집합의 개수는 자기 실패와 구별되지 않는 유일한 출력 타입**이다 ---
술어가 두 번째 인코딩을 놓치면 결과가 예외가 아니라 **작고 그럴듯한 양수**로 나온다.
조항 59 는 0 을 막지만 **작은 양수는 아무도 안 막는다.**

실물: 노트 943·944·티처 #84·945 **네 사이클**이 「디스크에 있으나 어떤 ref 에도 없는
캐시 파일 **215**」를 출판했다. 그 215 는 **존재하지 않는다** ---
``core.quotepath`` 가 unset(기본 true) 이라 ``git ls-tree --name-only`` 가 비-ASCII
경로를 ``"…\\353\\257\\270…"`` 로 8진 이스케이프한 것이고, 그 파일들은 HEAD 에
추적돼 있고 origin/main 에 있고 clone 하면 따라온다.

## 무엇을 주나

1. **정본 판독기** --- 이름 공간마다 **하나**. ``git_paths()`` 는 **항상**
   ``-z`` 와 ``-c core.quotePath=false`` 를 **둘 다** 쓴다(둘 중 하나만으로도
   충분하지만 둘 다 쓰면 어느 git 판에서도 안 샌다).
2. **조항 61 의 받침** --- ``diff_report()`` 가 차집합을 낼 때
   **반대 방향 · 예시 다섯 · 심은 키 하나**를 같이 낸다.
   심은 키를 못 찾으면 개수 대신 **「모른다」**를 낸다.

## 쓰는 법

    from lab import keyspace as ks

    disk = {str(p.relative_to(ROOT)) for p in ...}
    tree = ks.git_paths("ls-tree", "-r", "HEAD", "--", "data/state")
    rep  = ks.diff_report("디스크", disk, "HEAD 트리", tree,
                          probe=ks.octal_escape)          # 두 번째 인코딩
    rep["🔴 A − B"] ; rep["🔴 B − A"] ; rep["A − B 예시 다섯"] ; rep["심은 키"]

🔴 **날 것 호출(``subprocess`` 로 ``git ls-files`` / ``ls-tree`` / ``--name-only``
를 직접 부르는 것)은 이 모듈로 갈음한다.** ⑤′ 가 grep 으로 잡는다
(``runners/out946_quotefix.py`` 의 절 1 이 전수 계수를 낸다).
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Callable, Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]

#: 🔴 이 둘은 **떼면 안 된다.** ``-c core.quotePath=false`` 는 인용을 끄고,
#: ``-z`` 는 개행을 품은 경로까지 안전하게 가른다. 하나만 쓰면 git 판·설정에
#: 따라 새는 자리가 남는다(945 는 **둘 다** 안 썼다).
QUOTE_OFF: tuple[str, ...] = ("-c", "core.quotePath=false")

__all__ = [
    "ROOT", "QUOTE_OFF", "GitError",
    "git_paths", "git_lines", "octal_escape", "octal_unescape",
    "json_stamp_keys", "npz_names", "schema_fields",
    "diff_report", "UNKNOWN",
]

#: 🔴 조항 59 --- 「없다」가 아니라 **「모른다」**. 검출기가 심은 키를 못 찾으면
#: 그 절은 수를 내지 않는다.
UNKNOWN = "🔴 모른다 --- 심은 키를 못 찾았다(검출기가 두 번째 인코딩을 못 본다)"


class GitError(RuntimeError):
    """git 이 0 이 아닌 코드로 죽었다. 🔴 조항 59 --- 빈 출력을 「없다」로 읽지 않는다."""


# ── git ────────────────────────────────────────────────────────────────────
def _run(args: Sequence[str], *, root: Path | None = None) -> bytes:
    r = subprocess.run(["git", "-C", str(root or ROOT), *args],
                       capture_output=True)
    if r.returncode != 0:
        raise GitError("git %s → rc=%d · %s"
                       % (" ".join(args), r.returncode,
                          r.stderr.decode("utf-8", "replace")[:400]))
    return r.stdout


def git_paths(*args: str, root: Path | None = None) -> set[str]:
    """git 이 내는 **경로 집합**을 인용 없이 읽는다 --- 이 저장소의 정본 판독기.

    ``args`` 는 하위 명령부터 준다(``"ls-files"`` · ``"ls-tree", "-r", "HEAD"``).
    🔴 ``-z`` 와 ``--name-only`` 는 **이 함수가 붙인다** --- 부르는 쪽이 잊을 수 없게.

    >>> git_paths("ls-files", "--", "lab")            # doctest: +SKIP
    {'lab/keyspace.py', ...}
    """
    argl = list(args)
    if not argl:
        raise ValueError("하위 명령이 없다")
    sub = argl[0]
    #: 🔴 ``--`` 뒤는 **경로지정자**다. 거기에 ``-z`` 를 붙이면 옵션이 아니라
    #: 「``-z`` 라는 이름의 파일」을 찾는다(첫 판이 실제로 그렇게 새서 222 → 1 이
    #: 나왔다). 그래서 옵션은 **``--`` 앞에만** 끼운다.
    cut = argl.index("--") if "--" in argl else len(argl)
    opts, rest = argl[1:cut], argl[cut:]
    if "-z" not in opts:
        opts.append("-z")
    if sub in ("ls-tree", "log", "show", "diff") and "--name-only" not in opts:
        opts.append("--name-only")
    out = _run([*QUOTE_OFF, sub, *opts, *rest], root=root)
    return {p for p in out.decode("utf-8", "surrogateescape").split("\0") if p}


def git_lines(*args: str, root: Path | None = None) -> list[str]:
    """경로가 **아닌** git 출력(해시·시각 …). 인용은 여전히 끈다."""
    out = _run([*QUOTE_OFF, *args], root=root)
    return [ln for ln in out.decode("utf-8", "surrogateescape").split("\n") if ln]


# ── 두 번째 인코딩 ─────────────────────────────────────────────────────────
def octal_escape(path: str) -> str:
    """git 이 ``core.quotepath=true`` 로 낼 때의 **두 번째 인코딩**.

    비-ASCII 바이트를 ``\\ooo`` 로 적고 전체를 큰따옴표로 감싼다. 이 함수가
    있어야 「심은 키」를 만들 수 있다 --- 검출기에게 **두 번째 인코딩의 키를
    하나 주입하고 찾는지** 보는 것이 조항 61 의 셋째 항이다.

    >>> octal_escape("a/미.html")
    '"a/\\\\353\\\\257\\\\270.html"'
    >>> octal_escape("a/b.html")
    'a/b.html'
    """
    b = path.encode("utf-8", "surrogateescape")
    if all(0x20 <= c < 0x7F and c not in (0x22, 0x5C) for c in b):
        return path
    return '"%s"' % "".join(
        chr(c) if 0x20 <= c < 0x7F and c not in (0x22, 0x5C) else "\\%03o" % c
        for c in b)


def octal_unescape(s: str) -> str:
    """``octal_escape`` 의 역. 인용이 아니면 그대로 돌려준다.

    >>> octal_unescape('"a/\\\\353\\\\257\\\\270.html"')
    'a/미.html'
    >>> octal_unescape("a/b.html")
    'a/b.html'
    """
    if not (len(s) >= 2 and s[0] == '"' and s[-1] == '"'):
        return s
    body, out, i = s[1:-1], bytearray(), 0
    while i < len(body):
        c = body[i]
        if c == "\\" and i + 3 < len(body) + 1 and body[i + 1:i + 4].isdigit():
            out.append(int(body[i + 1:i + 4], 8)); i += 4
        elif c == "\\" and i + 1 < len(body):
            out.append(ord(body[i + 1])); i += 2
        else:
            out.extend(c.encode("utf-8")); i += 1
    return out.decode("utf-8", "surrogateescape")


# ── 다른 이름 공간들 ───────────────────────────────────────────────────────
def json_stamp_keys(obj, *, deep: bool = True, _pre: str = "") -> set[str]:
    """JSON 산출물의 키 공간 --- 🔴 **기본이 ``deep=True``** 다.

    ``fiveprime902.py:373`` 이 도장을 **최상위 키에서만** 찾아 941~945 의
    ``"🔴 스탬프"`` **한 겹 아래**를 못 봤다(945 가 발견 · 티처 #85 M2·M3 가
    범위를 정정: 오늘 280 산출물 중 최상위 161 · 한 겹 30 · 두 겹 1 · 없음 88).
    **중첩 깊이가 바로 그 두 번째 인코딩이다.**

    깊은 키는 ``부모/자식`` 으로 낸다. ``deep=False`` 면 최상위만(옛 자).
    """
    keys: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.add(f"{_pre}{k}" if _pre else str(k))
            if deep:
                keys |= json_stamp_keys(v, deep=True,
                                        _pre=(f"{_pre}{k}/" if _pre else f"{k}/"))
    elif isinstance(obj, list) and deep:
        for v in obj:
            keys |= json_stamp_keys(v, deep=True, _pre=_pre)
    return keys


def npz_names(path) -> set[str]:
    """``.npz`` 의 배열 이름 공간. ``numpy`` 없이 zip 목록으로 읽는다."""
    import zipfile
    with zipfile.ZipFile(str(path)) as z:
        return {n[:-4] if n.endswith(".npy") else n for n in z.namelist()}


def schema_fields(path) -> set[str]:
    """JSONL/JSON 레코드의 **필드 이름 공간**(도메인마다 다른 그 키 공간).

    레코드가 리스트면 전량의 키 합집합, 한 줄씩이면 줄마다 합집합.
    """
    p = Path(path)
    fields: set[str] = set()
    if p.suffix == ".jsonl":
        with p.open(encoding="utf-8") as fh:
            for ln in fh:
                ln = ln.strip()
                if not ln:
                    continue
                rec = json.loads(ln)
                if isinstance(rec, dict):
                    fields |= set(rec)
        return fields
    obj = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(obj, dict):
        obj = list(obj.values())
    for rec in obj if isinstance(obj, list) else []:
        if isinstance(rec, dict):
            fields |= set(rec)
    return fields


# ── 🔴🔴 조항 61 --- 차집합은 홀로 못 선다 ─────────────────────────────────
def diff_report(a_name: str, a: Iterable[str],
                b_name: str, b: Iterable[str],
                *, probe: Callable[[str], str] | None = None,
                examples: int = 5) -> dict:
    """차집합을 **혼자 내보내지 않는다.** 조항 61 의 구현.

    같은 자리에 넷을 함께 낸다:

    ① ``A − B`` **와** ``B − A`` --- 🔴 인코딩 결함은 **양쪽에 대칭으로** 나온다.
       945 는 ``디스크 − 지도 = 215`` 만 실었다. ``지도 − 디스크 = 215`` 를 옆에
       놓았으면 **그 자리에서 터졌다** --- 두 집합 **크기가 같은데** 차가 양쪽
       215 면 그것은 「없는 파일」이 아니라 **「두 이름」**이다.
    ② **예시 다섯**(실제 원소) --- 이스케이프된 경로 다섯 줄을 사람이 봤으면 **1초**.
    ③ **두 이름 대조** --- ``A − B`` 의 원소 ``x`` 에 대해 ``probe(x) ∈ B`` 면
       그것은 「B 에 없는 것」이 아니라 **B 에 다른 이름으로 있는 것**이다.
       하나라도 있으면 🔴 **수를 내지 않고** ``UNKNOWN`` 을 낸다.
    ④ **심은 키 하나** --- ``A ∩ B`` 의 원소 하나를 골라 ``B`` 안의 그 이름을
       **두 번째 인코딩으로 바꿔 심고**, ③ 이 그것을 잡는지 본다.
       🔴 **못 잡으면 이 함수 자신이 눈이 없는 것이므로 역시 ``UNKNOWN``** 을 낸다.

    ``probe`` 를 안 주면 ③④ 는 「안 했다」로 적힌다(「없다」가 아니다 · 조항 59).

    ⚠ **③ 이 못 보는 자리**: 생산자가 두 번째 인코딩 줄을 **애초에 버린 경우**
    (945 의 ``startswith("data/state/cache_")`` 필터) 는 ``B`` 에 흔적이 안 남아
    원리상 여기서 못 본다. 그 자리는 **생산자에 직접 심어야** 한다
    (``runners/out946_quotefix.py`` 절 5 가 그 검사다).
    """
    A, B = set(a), set(b)
    ab, ba = sorted(A - B), sorted(B - A)
    rep: dict = {
        "조항": "🔴 조항 61 --- 차집합은 홀로 못 선다(반대 방향 · 예시 다섯 · 심은 키)",
        "A": a_name, "B": b_name,
        f"|{a_name}|": len(A), f"|{b_name}|": len(B),
        "🔴 A − B": len(ab),
        "🔴 B − A": len(ba),
        "A − B 예시 다섯": ab[:examples],
        "B − A 예시 다섯": ba[:examples],
        "🔴 두 크기가 같은가": len(A) == len(B),
        "🔴 양쪽 차가 같은가": len(ab) == len(ba),
    }
    #: 🔴 945 를 그 자리에서 터뜨렸을 경보. 크기가 같은데 양쪽 차가 같은 양수면
    #: 「없는 원소」가 아니라 **같은 것의 두 이름**일 수 있다.
    rep["🔴 경보(두 이름 의심 · 크기와 양쪽 차가 같다)"] = bool(
        ab and len(ab) == len(ba) and len(A) == len(B))

    if probe is None:
        rep["③ 두 이름 대조"] = "🔴 안 했다(probe 를 안 줬다 --- 「없다」가 아니다)"
        rep["④ 심은 키"] = "🔴 안 했다(probe 를 안 줬다)"
        rep["🔴 검출기가 두 번째 인코딩을 보나"] = UNKNOWN
        rep["🔴 A − B"] = UNKNOWN
        rep["🔴 B − A"] = UNKNOWN
        rep["통과"] = False
        return rep

    def _twin(x_side: list[str], other: set[str]) -> list[str]:
        return [x for x in x_side if probe(x) != x and probe(x) in other]

    tw_ab, tw_ba = _twin(ab, B), _twin([octal_unescape(y) for y in ba], A)
    rep["③ 두 이름 대조"] = {
        "🔴 A − B 중 B 에 두 번째 인코딩으로 있는 것": len(tw_ab),
        "🔴 B − A 중 A 에 첫 인코딩으로 있는 것": len(tw_ba),
        "예시 다섯": tw_ab[:examples] or tw_ba[:examples],
    }

    #: ④ 심은 키 --- ``A ∩ B`` 의 원소 하나의 **B 쪽 이름만** 두 번째 인코딩으로 바꾼다.
    #: 그 원소는 여전히 B 에 **있다**. ③ 이 그것을 잡아야 눈이 있는 것이다.
    seed = next((x for x in sorted(A & B) if probe(x) != x), None)
    if seed is None:
        rep["④ 심은 키"] = ("🔴 심을 수 없다 --- 두 인코딩이 갈리는 원소가 A∩B 에 "
                        "하나도 없다. 🔴 **그 자체가 신호다**: B 의 생산자가 두 번째 "
                        "인코딩 줄을 아예 버렸으면 심을 자리가 남지 않는다")
        rep["🔴 왜 수를 안 내나"] = (
            "③ 이 두 이름을 %d 개 잡았다 --- 이 차집합은 「없는 원소」가 아니라 **두 이름**이다"
            % (len(tw_ab) or len(tw_ba)) if (tw_ab or tw_ba) else
            "④ 심은 키를 못 심었다 --- 이 대조가 눈이 있는지 원리상 확인할 수 없다")
        rep["순 A − B(참고 · 판정에 쓰지 마라)"] = len(ab)
        rep["순 B − A(참고 · 판정에 쓰지 마라)"] = len(ba)
        rep["🔴 검출기가 두 번째 인코딩을 보나"] = UNKNOWN
        rep["🔴 A − B"] = UNKNOWN
        rep["🔴 B − A"] = UNKNOWN
        rep["통과"] = False
        return rep

    B2 = (B - {seed}) | {probe(seed)}
    caught = bool(_twin(sorted(A - B2), B2))
    rep["④ 심은 키"] = {"원본": seed, "심은 것(두 번째 인코딩)": probe(seed),
                    "🔴 심었나": True, "🔴 발화했나": caught,
                    "심은 뒤 순 A − B(대조 전)": len(A - B2)}

    blind = not caught
    dirty = bool(tw_ab or tw_ba)
    rep["🔴 검출기가 두 번째 인코딩을 보나"] = (
        UNKNOWN if blind else "✅ 본다 --- 심은 키를 ③ 이 잡았다")
    if blind or dirty:
        #: 🔴 **수를 내지 않는다.** 값을 지우고 「모른다」를 남긴다 --- 조항 61 의 핵심.
        rep["🔴 왜 수를 안 내나"] = (
            "③ 이 두 이름을 %d 개 잡았다 --- 이 차집합은 「없는 원소」가 아니라 "
            "**두 이름**이다" % (len(tw_ab) or len(tw_ba)) if dirty else
            "④ 심은 키를 못 잡았다(이 대조가 눈이 없다)")
        rep["순 A − B(참고 · 판정에 쓰지 마라)"] = len(ab)
        rep["순 B − A(참고 · 판정에 쓰지 마라)"] = len(ba)
        rep["🔴 A − B"] = UNKNOWN
        rep["🔴 B − A"] = UNKNOWN
    rep["통과"] = not (blind or dirty)
    return rep
