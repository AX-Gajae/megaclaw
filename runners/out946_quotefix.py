"""노트 946 [수리] --- `core.quotePath` 전량 수리 + 네 사이클 정정.

## 무엇이 틀렸나

`git config core.quotepath` 가 **unset(기본 true)** 이라
`git log --name-only` · `git ls-files` · `git ls-tree --name-only` 가 비-ASCII 경로를
**8진 이스케이프**(`"…\\353\\257\\270…"`)해서 낸다. 그래서

> 「디스크에 있으나 어떤 ref 에도 없는 캐시 파일 **215**」

라는 수가 **네 사이클(943 · 944 · 티처 #84 · 945)에 걸쳐 출판됐는데
그 215 는 존재하지 않는다.** HEAD 에 추적돼 있고 origin/main 에 있고 clone 하면 따라온다.

## 이 러너가 내는 것

| 절 | 무엇 |
|---|---|
| **1** | 🔴 저장소 **전량**에서 날 것 호출 자리를 **AST 로** 전수 계수 --- 목록을 산출물에 싣는다 |
| **2** | `215 → 0` --- 🔴 **조항 61 형식**(반대 방향 차집합 · 예시 다섯 · 심은 키) |
| **3** | `data/state/obs_time946_cachemap.json` --- 945 지도의 **215 가짜 경로 + mtime null** 을 다시 쓴다 |
| **4** | **T3 와 945 후보 3 철회** --- 「215 에 사본을 준다」. 사본이 이미 있다 |
| **5** | 🔴 **심어서 확인** --- 옛 술어와 새 판독기에 두 번째 인코딩 키를 주입해 검정력을 잰다 |
| **6** | 🔴 **날 것 호출 게이트** --- ⑤′ 명부에 `통과` 키로 잡히는 자리(⑤′ 러너는 안 고친다 · 규칙 4) |

🔴 **941~945 산출물은 동결이다.** 이 러너는 그 파일들을 **한 바이트도 안 고친다** ---
읽고, 다시 세고, **새 파일**로 낸다.

    python3 runners/out946_quotefix.py            # → runners/out946_quotefix.json
                                                  #   + data/state/obs_time946_cachemap.json
"""
from __future__ import annotations

import ast
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lab import keyspace as ks                                    # noqa: E402

OUT = ROOT / "runners" / "out946_quotefix.json"
CACHEMAP_NEW = ROOT / "data" / "state" / "obs_time946_cachemap.json"
CACHEMAP_OLD = ROOT / "data" / "state" / "obs_time945_cachemap.json"

#: 경로를 내는 git 하위명령·플래그. 이 중 하나라도 args 벡터에 있으면 **경로 호출**이다.
PATH_TOKENS = ("ls-files", "ls-tree", "--name-only", "--name-status")
#: 인용을 끄는 두 자. 🔴 `-z` 하나만으로도 git 은 인용을 안 하지만, 둘 다 쓰는 것이 정본이다.
SAFE_Z = "-z"
SAFE_Q = ("core.quotepath=false", "core.quotePath=false")

#: 🔴 **의도적인 날 것** --- ⑤′ 의 음성 대조. 여기서 인용을 끄면 그 검사가 죽는다.
INTENTIONAL = {
    ("runners/fiveprime902.py", 178):
        "🔴 음성 대조 --- ⑤′ 가 **일부러** quotepath 를 안 꺼서 이스케이프 바늘로 한 번 "
        "더 센다(`out945_fiveprime.json:1 소비자 역참조/🔴 음성 대조…`). 고치면 그 검사가 죽는다",
    ("runners/out946_quotefix.py", 0):
        "🔴 재현 --- `_raw_lstree_cache()` 는 **945 의 날 것 술어를 그대로 다시 돌린다**. "
        "여기서 인용을 끄면 「옛 자로 얼마가 나왔나」를 못 잰다(절 2 나)",
    ("runners/out946_recount.py", 0):
        "🔴 음성 대조 --- `_raw_two_ways()` 는 날 것을 `quotepath` 켜고/끄고 두 번 돌려 "
        "「날 것은 그 설정을 탄다」를 실측한다. 끄면 그 대조가 죽는다",
}
#: 🔴 줄 번호를 손으로 못 박는 자리(파일이 이 사이클에 계속 바뀐다)는 `0` 으로 두고
#: **파일 단위**로 사유를 붙인다. 아래 census 가 그 규칙을 적는다.

#: 동결 --- 941~945 의 러너·산출물. 스탬프가 코드 sha256 을 담아 **주석 한 줄도** 대조를 깬다.
FROZEN_PREFIX = ("runners/out941", "runners/out942", "runners/out943",
                 "runners/out944", "runners/out945")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def stamp() -> dict:
    return {
        "시각(UTC · 시작)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "🔴 코드 sha256(이게 자다)": {
            "runners/out946_quotefix.py": sha(Path(__file__).resolve()),
            "lab/keyspace.py": sha(ROOT / "lab" / "keyspace.py"),
        },
        "🔴 입력 산출물 sha256": {
            r: (sha(ROOT / r) if (ROOT / r).exists() else "🔴 파일 없음")
            for r in ("data/state/obs_time945_cachemap.json",
                      "runners/out945_obstime.json",
                      "runners/out945_verify.json",
                      "runners/out943b_d2time.json")},
        "⚠ git HEAD(시작 시점 · 판정에 쓰지 마라)":
            ks.git_lines("rev-parse", "HEAD")[0],
    }


# ══════════════════════════════════════════════════ 절 1 · 날 것 호출 전수
SUBPROC = ("run", "Popen", "check_output", "getoutput", "call", "check_call")


def _git_wrappers(tree: ast.AST) -> set[str]:
    """🔴 **이 파일 안에서 정의된 git 래퍼**의 이름. 손 목록이 아니라 본문을 본다.

    본문 어딘가에서 `subprocess.*` 를 부르면서 `"git"` 을 argv 원소로 쓰는 함수
    (`gate940_wiring.git` · `ratio940_run.git` · `fiveprime902._git` …).
    이것을 안 보면 래퍼로 감싼 날 것이 **0** 으로 세어진다(조항 59 의 얼굴).
    """
    out = set()
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for n in ast.walk(fn):
            if isinstance(n, ast.Call) and (
                    getattr(n.func, "attr", None) in SUBPROC
                    or getattr(n.func, "id", None) in SUBPROC):
                if any(isinstance(c, ast.Constant) and c.value == "git"
                       for c in ast.walk(n)):
                    out.add(fn.name)
    return out


def _consts(node: ast.AST) -> list[str]:
    """이 노드의 **직속** 문자열 상수(리스트/튜플 인자는 한 겹 벗긴다)."""
    out = []
    for a in getattr(node, "args", []) or []:
        if isinstance(a, ast.Constant) and isinstance(a.value, str):
            out.append(a.value)
        elif isinstance(a, (ast.List, ast.Tuple)):
            out += [e.value for e in a.elts
                    if isinstance(e, ast.Constant) and isinstance(e.value, str)]
    return out


def _vectors(tree: ast.AST):
    """`(줄, [문자열 상수…], 자리 갈래)` --- 🔴 **argv 로 실제로 건너가는 자리만**.

    🔴 **docstring·주석·JSON 값 문자열은 안 잡는다** --- 그래서 「grep 히트」와
    「실제 호출 자리」가 갈린다(조항 60: 분모를 갈라 적는다).

    🔴 **그리고 「경로 토큰을 품은 모든 리터럴」도 안 잡는다.** 첫 판이 그렇게 셌더니
    `("ls-tree", "log", "show", "diff")` 같은 **소속 검사용 튜플**과
    `opts.append("--name-only")` 같은 **조립 한 조각**이 「날 것」으로 잡혔다 ---
    그것들은 프로세스로 안 건너간다. 세 갈래만 argv 로 본다:

    ① 첫 원소가 `"git"` 인 리스트/튜플 리터럴 ② `subprocess.*` 호출
    ③ **같은 파일에서 정의된 git 래퍼** 호출 (`_git_wrappers`)
    """
    wrappers = _git_wrappers(tree)
    for n in ast.walk(tree):
        if isinstance(n, (ast.List, ast.Tuple)):
            c = [e.value for e in n.elts
                 if isinstance(e, ast.Constant) and isinstance(e.value, str)]
            if c and c[0] == "git":
                yield n.lineno, c, "argv 리터럴(`[\"git\", …]`)"
        elif isinstance(n, ast.Call):
            fn = getattr(n.func, "id", None) or getattr(n.func, "attr", "?")
            if fn in SUBPROC:
                continue        # 안쪽 리스트 리터럴이 ① 로 이미 잡힌다
            if fn not in wrappers:
                continue        # 🔴 `ks.git_paths(…)` 같은 정본 판독기 호출은 argv 가 아니다
            c = _consts(n)
            if c:
                yield n.lineno, c, f"같은 파일의 git 래퍼 `{fn}(…)`"


def _scope_of(vec: list[str]) -> list[str]:
    """이 호출 자리의 **경로 범위**를 인자 벡터에서 뽑는다.

    `--` 뒤가 있으면 그것. 없으면 하위명령별로:
    `ls-files` 는 플래그가 아닌 나머지 전부, `ls-tree` 는 첫 비-플래그(ref)를 뺀 나머지.
    `log`/`show` 는 ref 와 경로가 섞여 원리상 못 가르므로 **빈 범위(=저장소 전량)** 로 둔다.
    🔴 「못 가른다」를 「없다」로 읽지 않으려고 이 규칙을 산출물에 적는다(조항 59).
    """
    if "--" in vec:
        return [x for x in vec[vec.index("--") + 1:] if x]
    body = [x for x in vec if x != "git"]
    if not body:
        return []
    sub, rest = body[0], [x for x in body[1:] if not x.startswith("-")]
    if sub == "ls-files":
        return rest
    if sub == "ls-tree":
        return rest[1:]
    return []


def _harm(vec: list[str], tracked_split: set[str]) -> dict:
    """🔴 이 자리에서 **실해가 나나** --- 주장이 아니라 측정.

    ① 범위 안에 **두 인코딩이 갈리는 추적 경로**가 몇인가(범위가 비면 저장소 전량).
    ② 인자 벡터가 **전부 상수인 읽기 전용 `ls-files`/`ls-tree`** 면 날 것과 정본을
       **둘 다 실제로 돌려** 결과 집합을 견준다.
    """
    scope = _scope_of(vec)
    if scope:
        try:
            in_scope = ks.git_paths("ls-files", "--", *scope)
        except ks.GitError as e:
            return {"범위": scope, "🔴 못 쟀다": str(e)[:200]}
    else:
        in_scope = tracked_split
    split = sorted(p for p in in_scope if ks.octal_escape(p) != p)
    out = {"범위": scope or ["(저장소 전량 --- ref/경로를 원리상 못 가르는 자리)"],
           "범위 안 추적 경로": len(in_scope),
           "🔴 그중 두 인코딩이 갈리는 것": len(split),
           "예시 다섯": split[:5]}

    body = [x for x in vec if x != "git"]
    if body and body[0] in ("ls-files", "ls-tree") and all(
            not x.startswith("\x01") for x in body):
        try:
            good = ks.git_paths(*body)
            r = subprocess.run(["git", "-C", str(ROOT), *body],
                               capture_output=True, text=True)
            bad = {x for x in r.stdout.splitlines() if x}
            out["🔴 실제로 둘 다 돌렸다"] = {
                "정본이 낸 수": len(good), "날 것이 낸 수": len(bad),
                "🔴 정본 − 날것": len(good - bad), "🔴 날것 − 정본": len(bad - good),
                "🔴 사라지는 경로 예시 다섯": sorted(good - bad)[:5]}
        except (ks.GitError, OSError) as e:
            out["🔴 실제로 둘 다 돌렸다"] = {"못 돌렸다": str(e)[:200]}
    else:
        out["🔴 실제로 둘 다 돌렸다"] = ("🔴 못 돌렸다 --- 인자에 동적 값(ref·경로)이 "
                              "섞여 이 자리를 재현할 수 없다. **「무해」가 아니라 "
                              "「못 쟀다」다**(조항 59)")
    return out


def _mine() -> set[str]:
    """🔴 **이 사이클이 만든 `.py`** --- 손 목록이 아니라 git 이력이 「모른다」고 하는 것.

    `git log -1 -- <경로>` 가 비면 그 파일은 **아직 어느 커밋에도 없다** = 이번 사이클 것.
    (커밋한 뒤 다시 돌리면 이 집합이 빈다 --- 그때는 아래 `946` 이름표로 갈음한다.)
    """
    out = set()
    for rel in ks.git_paths("ls-files", "--", "*.py"):
        if "946" in Path(rel).name:
            out.add(rel); continue
        r = subprocess.run(["git", "-C", str(ROOT), "log", "-1", "--format=%H",
                            "--", rel], capture_output=True, text=True)
        if not r.stdout.strip():
            out.add(rel)
    return out | {"lab/keyspace.py"}


def _sha_cited(rel: str) -> list[str]:
    """🔴 이 파일의 **지금 sha256** 을 인용하는 커밋된 산출물 --- 손 목록이 아니라 grep.

    인용하는 산출물이 있으면 이 파일을 고치는 순간 그 산출물의 코드 sha 대조가 깨진다
    --- 그래서 **㉮ 원리상 못 고친다**로 센다(티처 #78 M2 의 ㉮/㉯ 가르기).
    """
    p = ROOT / rel
    if not p.exists():
        return []
    h = sha(p)
    r = subprocess.run(["git", "-C", str(ROOT), "grep", "-lF", "--", h,
                        "--", "runners/*.json", "data/lab/*.json"],
                       capture_output=True, text=True)
    return [x for x in r.stdout.splitlines() if x.strip()]


def census() -> dict:
    pys = sorted(ks.git_paths("ls-files", "--", "*.py"))
    tracked = ks.git_paths("ls-files")
    tracked_split = {p for p in tracked if ks.octal_escape(p) != p}
    sites, bad_parse = [], []
    for rel in pys:
        try:
            src = (ROOT / rel).read_text(encoding="utf-8")
            tree = ast.parse(src)
        except (SyntaxError, UnicodeDecodeError, OSError) as e:
            bad_parse.append({"파일": rel, "왜": type(e).__name__})
            continue
        for line, vec, kind in _vectors(tree):
            if not any(t in vec for t in PATH_TOKENS):
                continue
            has_z = SAFE_Z in vec
            has_q = any(q in vec for q in SAFE_Q)
            frozen = rel.startswith(FROZEN_PREFIX)
            why = INTENTIONAL.get((rel, line)) or INTENTIONAL.get((rel, 0))
            cited = [] if (has_z or has_q) else _sha_cited(rel)
            sites.append({
                "파일:줄": f"{rel}:{line}", "자리": kind, "인자": vec,
                "-z": has_z, "core.quotePath=false": has_q,
                "갈래": ("안전(정본)" if has_z and has_q else
                       "안전(-z)" if has_z else
                       "안전(quotePath=false)" if has_q else
                       "🔴 의도적 날 것(음성 대조)" if why else "🔴 날 것"),
                "동결(941~945)": frozen,
                "사유": why,
                "🔴 지금 sha 를 인용하는 산출물": cited,
                "🔴 ㉮/㉯": (None if (has_z or has_q or why) else
                         "㉮ 원리상 못 고친다 --- 941~945 동결" if frozen else
                         "㉮ 원리상 못 고친다 --- 이 파일의 지금 sha 를 산출물 %d 개가 "
                         "인용한다(고치면 그 대조가 깨진다)" % len(cited) if cited else
                         "🔴 ㉯ 고칠 수 있다"),
                "🔴 실해": (_harm(vec, tracked_split)
                        if not (has_z or has_q) else "해당 없음(안전한 자리)"),
            })
    raw = [s for s in sites if s["갈래"] == "🔴 날 것"]
    intentional = [s for s in sites if s["갈래"].startswith("🔴 의도적")]
    safe = [s for s in sites if s["갈래"].startswith("안전")]
    raw_frozen = [s for s in raw if s["동결(941~945)"]]
    raw_live = [s for s in raw if not s["동결(941~945)"]]
    raw_b = [s for s in raw if s["🔴 ㉮/㉯"] and s["🔴 ㉮/㉯"].startswith("🔴 ㉯")]
    raw_a = [s for s in raw if s["🔴 ㉮/㉯"] and s["🔴 ㉮/㉯"].startswith("㉮")]

    #: 🔴 **이 사이클이 만든 파일을 분모에서 가른다**(규약 60 파생 · 티처 #80).
    #: 940 이 자기가 만든 언급을 남의 부채로 셌다. 946 도 `.py` 를 넷 더한다.
    mine = _mine()
    sites_mine = [s for s in sites if s["파일:줄"].split(":")[0] in mine]
    raw_mine = [s for s in raw if s["파일:줄"].split(":")[0] in mine]

    # 🔴 「grep 히트」와 「호출 자리」는 다른 분모다(조항 60).
    g = subprocess.run(["git", "-C", str(ROOT), "grep", "-n", "-E",
                        "|".join(PATH_TOKENS), "--", "*.py"],
                       capture_output=True, text=True)
    grep_hits = [ln for ln in g.stdout.splitlines() if ln.strip()]

    return {
        "검사": "1 날 것 호출 전수 --- 🔴 AST 로 센다(grep 히트가 아니다)",
        "🔴 세는 명령": ("git ls-files -z -- '*.py' 로 목록 → 각 파일을 `ast.parse` → "
                    "`List/Tuple` 원소와 `Call` 위치 인자의 문자열 상수 벡터 중 "
                    f"{list(PATH_TOKENS)} 를 품은 것"),
        "🔴 범위": "추적된 `*.py` 전량(확장자 하나 · 경로 제한 없음)",
        "🔴 트리": "인덱스(`git ls-files`)로 목록 · 내용은 작업 트리 --- 🔴 규약 60 이 "
                "금지한 혼합이다. 그래서 ⓪ 관문에서 `git status --porcelain` 이 "
                "비었음을 같이 신고한다(아래 `⓪ 작업 트리가 깨끗한가`)",
        "⓪ 작업 트리가 깨끗한가": _clean_tree(),
        "🔴 분모 ⓪ 이 사이클이 더한 .py(분모에서 가른다)": sorted(mine),
        "🔴 분모 ① 훑은 .py": len(pys),
        "🔴 분모 ①′ 그중 남의 것(이 사이클 밖)": len(pys) - len(mine & set(pys)),
        "🔴 분모 ② grep 히트(문서·주석 포함)": len(grep_hits),
        "🔴 분모 ③ 실제 호출 자리": len(sites),
        "🔴 분모 ③′ 그중 이 사이클이 만든 것": len(sites_mine),
        "🔴 분모 ③″ 남의 것": len(sites) - len(sites_mine),
        "🔴 분모 ④ 날 것": len(raw),
        "🔴 분모 ④′ 그중 이 사이클이 만든 것": len(raw_mine),
        "🔴 분모 ④-동결 날 것 중 941~945(못 고친다)": len(raw_frozen),
        "🔴 분모 ④-살아있는 날 것": len(raw_live),
        "🔴 분모 ④-㉮ 원리상 못 고친다": len(raw_a),
        "🔴 분모 ④-㉯ 고칠 수 있다(🔴 이 수가 0 이어야 통과)": len(raw_b),
        "🔴 ㉯ 목록": [s["파일:줄"] for s in raw_b],
        "㉮ 목록과 사유": {s["파일:줄"]: s["🔴 ㉮/㉯"] for s in raw_a},
        "분모 ⑤ 의도적 날 것(음성 대조)": len(intentional),
        "분모 ⑥ 안전": len(safe),
        "파싱 실패": bad_parse,
        "🔴 날 것 전량(목록)": raw,
        "의도적 날 것(목록)": intentional,
        "안전(목록)": safe,
        "⚠ ② 와 ③ 은 다른 분모다":
            f"grep 히트 {len(grep_hits)} 중 실제 호출 자리는 {len(sites)} 다. "
            "나머지는 docstring·주석·JSON 값 문자열이다 --- 「29 를 고쳤다」로 세면 틀린다",
        "통과": len(raw_b) == 0,
        "🔴 통과의 뜻": ("**㉯(고칠 수 있는데 안 고친 것)가 0** 이면 통과. 🔴 ㉮ 는 분모에 "
                    "남지만 통과를 막지 않는다 --- 동결된 941~945 러너와 **지금 sha 가 "
                    "산출물에 인용된 러너**는 고치는 순간 그 사이클의 스탬프 대조가 깨진다. "
                    "그것들은 「고쳤다」가 아니라 「정정문을 냈다」로 닫는다(티처 #78 M2 의 ㉮/㉯)"),
    }


def _clean_tree() -> dict:
    r = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"],
                       capture_output=True, text=True)
    lines = [x for x in r.stdout.splitlines() if x.strip()]
    return {"줄 수": len(lines), "예시 다섯": lines[:5], "깨끗한가": not lines}


# ══════════════════════════════════════════════════ 절 2 · 215 → 0
def _disk_cache() -> set[str]:
    out = set()
    base = ROOT / "data" / "state"
    for d in sorted(base.glob("cache_*")):
        if not d.is_dir():
            continue
        for p in d.rglob("*"):
            if p.is_file():
                out.add(str(p.relative_to(ROOT)))
    return out


def _raw_lstree_cache() -> set[str]:
    """🔴 **옛 자 그대로** --- `-z` 도 `core.quotePath=false` 도 안 쓴다. 945 의 술어."""
    r = subprocess.run(["git", "-C", str(ROOT), "ls-tree", "-r", "--name-only",
                        "HEAD", "--", "data/state"], capture_output=True, text=True)
    return {x for x in r.stdout.splitlines() if x.startswith("data/state/cache_")}


def sec2(disk: set[str]) -> dict:
    new_tree = {p for p in ks.git_paths("ls-tree", "-r", "HEAD", "--", "data/state")
                if p.startswith("data/state/cache_")}
    old_tree = _raw_lstree_cache()

    rep_new = ks.diff_report("디스크", disk, "HEAD 트리(정본 판독기)", new_tree,
                             probe=ks.octal_escape)
    rep_old = ks.diff_report("디스크", disk, "HEAD 트리(945 의 날 것 술어)", old_tree,
                             probe=ks.octal_escape)

    #: 🔴 **945 가 옆에 놓았어야 할 수** --- 945 의 지도로 양방향을 재면 양쪽이 같은 215 다.
    old_map = json.loads(CACHEMAP_OLD.read_text(encoding="utf-8"))
    map945 = set(old_map["파일"])
    rep_945map = ks.diff_report("디스크", disk, "945 지도(obs_time945_cachemap.json)",
                                map945, probe=ks.octal_escape)

    quoted = sorted(k for k in map945 if k.startswith('"'))
    return {
        "검사": "2 `215 → 0` --- 🔴 조항 61 형식(반대 방향 · 예시 다섯 · 심은 키)",
        "🔴 세는 명령": ("정본: `git -c core.quotePath=false ls-tree -r -z --name-only "
                    "HEAD -- data/state` / 옛것: 같은 명령에서 `-z` 와 `-c` 를 뺀 것"),
        "🔴 범위": "`data/state/cache_*` 전량",
        "🔴 트리": "HEAD 끝 트리 대 디스크(작업 트리). 인덱스는 안 섞는다",
        "가 · 정본 판독기로": rep_new,
        "나 · 945 의 날 것 술어로(재현)": rep_old,
        "다 · 945 가 커밋한 지도로(🔴 양방향을 옆에 놓는다)": rep_945map,
        "🔴 전 / 후": {
            "옛 자 `디스크 − 트리`": rep_old["🔴 A − B"],
            "옛 자 `트리 − 디스크`": rep_old["🔴 B − A"],
            "새 자 `디스크 − 트리`": rep_new["🔴 A − B"],
            "새 자 `트리 − 디스크`": rep_new["🔴 B − A"],
            "🔴 945 지도 양방향": [rep_945map["🔴 A − B"], rep_945map["🔴 B − A"]],
        },
        "🔴 이스케이프된 키 수(945 지도)": len(quoted),
        "이스케이프된 키 예시 다섯": quoted[:5],
        "그 다섯을 풀면": [ks.octal_unescape(q) for q in quoted[:5]],
        "🔴 그 다섯이 디스크에 있나": [ks.octal_unescape(q) in disk for q in quoted[:5]],
        "🔴 그 다섯이 HEAD 트리에 있나": [ks.octal_unescape(q) in new_tree
                                for q in quoted[:5]],
        "통과": (rep_new["🔴 A − B"] == 0 and rep_new["🔴 B − A"] == 0
               and rep_new["통과"]),
    }


# ══════════════════════════════════════════════════ 절 3 · 지도 정정
def sec3(disk: set[str]) -> dict:
    raw = subprocess.run(
        ["git", "-C", str(ROOT), "-c", "core.quotePath=false", "log", "--all",
         "--format=\x01%H %aI", "--name-only", "-z", "--diff-filter=A",
         "--", "data/state/cache_*"], capture_output=True)
    txt = raw.stdout.decode("utf-8", "surrogateescape")

    #: 🔴 옛 지도와 **같은 꼴**로 낸다(`{h, t, origin/main 에 있나}`) --- 그래야 두 지도를
    #: 나란히 견줄 수 있다. 형식을 바꾸면 「달라졌다」와 「틀렸다」가 안 갈린다.
    in_om = set()
    if ks.git_lines("rev-parse", "--verify", "-q", "origin/main"):
        in_om = set(ks.git_lines("rev-list", "origin/main"))
    commits: list[dict] = []
    idx: dict[str, int] = {}
    first: dict[str, int] = {}          # 경로 → 커밋 인덱스(가장 이른 = 나중에 덮어씀)
    for chunk in txt.split("\x01"):
        if not chunk.strip("\0 \n"):
            continue
        head, _, body = chunk.partition("\n")
        h, _, when = head.strip().partition(" ")
        if h not in idx:
            idx[h] = len(commits)
            commits.append({"h": h, "t": when.strip(),
                            "origin/main 에 있나": h in in_om})
        ci = idx[h]
        for p in body.split("\0"):
            p = p.strip("\n")
            if p:
                first[p] = ci                     # git log 는 최신→과거라 마지막 승자가 최초
    ordered = sorted(range(len(commits)), key=lambda i: commits[i]["t"])

    files: dict[str, list] = {}
    missing_mtime = []
    for p in sorted(disk | set(first)):
        fp = ROOT / p
        try:
            #: 🔴 945 와 **같은 반올림**(`round`)을 쓴다. `int()` 로 자르면 절반이
            #: 1 초씩 어긋나 「지도가 바뀌었다」가 20 개가 아니라 2만 개가 된다 ---
            #: **비교 규칙이 다르면 비교가 아니다**(조항 60).
            mt = round(os.stat(fp).st_mtime) if fp.exists() else None
        except OSError:
            mt = None
        if mt is None:
            missing_mtime.append(p)
        files[p] = [first.get(p), mt]

    old = json.loads(CACHEMAP_OLD.read_text(encoding="utf-8"))
    old_files = old["파일"]
    old_null = sorted(k for k, v in old_files.items() if v[1] is None)
    fixed = [ks.octal_unescape(k) for k in old_null]

    #: 🔴 옛 지도의 **안 바뀐 부분**이 정말 안 바뀌었나 --- 재생성이 옛 값을 뒤엎지 않았음을 센다.
    same, n_diff, diff = 0, 0, []
    for k, v in old_files.items():
        if k.startswith('"'):
            continue
        nv = files.get(k)
        if nv is None:
            n_diff += 1
            if len(diff) < 20:
                diff.append({"경로": k, "왜": "새 지도에 없다"})
            continue
        oc = old["커밋목록"][v[0]]["h"] if v[0] is not None else None
        nc = commits[nv[0]]["h"] if nv[0] is not None else None
        if oc == nc and v[1] == nv[1]:
            same += 1
        else:
            n_diff += 1                      # 🔴 예시는 20 까지만 싣되 **수는 전부 센다**
            if len(diff) < 20:
                diff.append({"경로": k, "옛": [oc, v[1]], "새": [nc, nv[1]]})

    CACHEMAP_NEW.write_text(json.dumps({
        "_meta": {
            "노트": 946, "레인": "수리",
            "만든 시각": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "만든 러너": "runners/out946_quotefix.py",
            "무엇": "data/state/cache_* 전량의 git 최초추가 커밋(모든 ref) + mtime",
            "🔴 무엇을 정정하나": (
                "`obs_time945_cachemap.json` 은 `core.quotepath` 가 켜져 있어 비-ASCII 경로 "
                "**215** 개를 `\"…\\353\\257\\270…\"` 로 이스케이프된 **가짜 키**로 실었고 "
                "그 215 전부의 `mtime` 이 `null` 이었다. 이 파일은 같은 지도를 "
                "`-c core.quotePath=false` + `-z` 로 다시 읽어 **참 경로와 참 mtime** 으로 쓴다"),
            "🔴 옛 파일을 지우지 않는다": "증거물이다. `obs_time945_cachemap.json` 은 그대로 둔다",
            "읽는 법": "파일[경로] = [커밋목록 인덱스, mtime(epoch초)]",
            "파일 수": len(files),
            "커밋 수": len(commits),
            "🔴 이스케이프된 키": 0,
            "🔴 mtime 이 null 인 파일": len(missing_mtime),
            "🔴 정정된 키 수": len(old_null),
        },
        "커밋목록": commits,
        "커밋목록(이른 순 인덱스)": ordered,
        "파일": files,
    }, ensure_ascii=False), encoding="utf-8")

    return {
        "검사": "3 지도 정정 --- `obs_time946_cachemap.json`",
        "🔴 세는 명령": ("git -c core.quotePath=false log --all --format='\\x01%H %aI' "
                    "--name-only -z --diff-filter=A -- data/state/cache_*"),
        "🔴 범위": "data/state/cache_*", "🔴 트리": "모든 ref 의 이력(--all) + 디스크 mtime",
        "새 파일": str(CACHEMAP_NEW.relative_to(ROOT)),
        "새 지도 파일 수": len(files),
        "새 지도 커밋 수": len(commits),
        "🔴 새 지도의 이스케이프된 키": len([k for k in files if k.startswith('"')]),
        "🔴 새 지도의 mtime null": len(missing_mtime),
        "🔴 옛 지도의 mtime null(=정정 대상)": len(old_null),
        "정정 예시 다섯(옛 키 → 새 키)": [
            {"옛": k, "새": ks.octal_unescape(k),
             "새 mtime": files.get(ks.octal_unescape(k), [None, None])[1]}
            for k in old_null[:5]],
        "🔴 정정된 215 가 전부 새 지도에 참 이름으로 있나":
            all(f in files for f in fixed),
        "🔴 정정된 215 가 전부 mtime 을 얻었나":
            all(files.get(f, [None, None])[1] is not None for f in fixed),
        "🔴 옛 지도의 안 바뀐 항목이 같은가(비-인용 키)": {
            "같은 것": same, "🔴 다른 것": n_diff, "다른 것 예시(20 까지)": diff,
            "🔴 분모(옛 지도의 비-인용 키)": len(old_files) - len(old_null)},
        "통과": (len([k for k in files if k.startswith('"')]) == 0
               and not missing_mtime
               and all(f in files for f in fixed)
               and n_diff == 0),
    }


# ══════════════════════════════════════════════════ 절 4 · 철회
def sec4(disk: set[str]) -> dict:
    head = {p for p in ks.git_paths("ls-tree", "-r", "HEAD", "--", "data/state")
            if p.startswith("data/state/cache_")}
    old_map = json.loads(CACHEMAP_OLD.read_text(encoding="utf-8"))
    ghosts = [ks.octal_unescape(k) for k in old_map["파일"] if k.startswith('"')]

    om = ks.git_lines("rev-parse", "--verify", "-q", "origin/main")
    in_om: set[str] = set()
    if om:
        in_om = {p for p in ks.git_paths("ls-tree", "-r", "origin/main",
                                         "--", "data/state/cache_aladin")}
    return {
        "검사": "4 🔴 철회 --- 945 의 T3 와 후보 3(「215 에 사본을 준다」)",
        "무엇을 철회하나": [
            "🔴 `docs/수리/945.md` T3 --- 「디스크에 있으나 어떤 ref 에도 없는 캐시 파일 215 · "
            "mtime 이 유일한 근거 · 사본이 없다」",
            "🔴 945 원장 항목의 P4 = 215 와 「어떤 ref 에도 없는 파일 215 는 사본 0」",
            "🔴 945 의 다음 후보 3 --- 「T3 의 215 에 사본을 준다」. **사본이 이미 있다**",
            "🔴 티처 #84 의 「cache_aladin 222 중 215 가 git 미추적」",
            "🔴 `docs/탐색/943.md:25` 의 「추적됨 54,661」 · `docs/탐색/944.md:147` 의 같은 문장",
        ],
        "🔴 왜 --- 사본이 이미 있다": {
            "그 215 가 HEAD 에 추적되나": sum(1 for g in ghosts if g in head),
            "🔴 분모(215)": len(ghosts),
            "origin/main 이 있나": bool(om),
            "cache_aladin 이 origin/main 에 몇 개": len(in_om),
            "cache_aladin 이 디스크에 몇 개":
                len([p for p in disk if p.startswith("data/state/cache_aladin/")]),
            "cache_aladin 이 HEAD 에 몇 개":
                len([p for p in head if p.startswith("data/state/cache_aladin/")]),
            "예시 다섯": ghosts[:5],
            "그 다섯이 HEAD 에 있나": [g in head for g in ghosts[:5]],
        },
        "🔴 남는 참된 문장": (
            "cache_aladin 222 는 **전부** 추적된다. 「mtime 이 유일한 근거인 캐시 파일」은 "
            "**0** 이다. 945 가 T3 로 낸 것은 파일의 성질이 아니라 **판독기의 성질**이었다"),
        "통과": len(ghosts) > 0 and all(g in head for g in ghosts),
    }


# ══════════════════════════════════════════════════ 절 5 · 심어서 확인
def sec5(disk: set[str]) -> dict:
    """🔴 검정력 --- 옛 술어와 새 판독기에 **두 번째 인코딩 키를 주입**하고 잡는지 본다."""
    sample = sorted(p for p in disk if ks.octal_escape(p) != p)
    checks = []

    # (가) 옛 술어: `startswith("data/state/cache_")` 로 거른다 --- 인용된 줄을 조용히 버린다
    esc_lines = [ks.octal_escape(p) for p in sample[:50]]
    old_keep = [x for x in esc_lines if x.startswith("data/state/cache_")]
    checks.append({"검사": "가 · 945 의 `startswith` 필터에 이스케이프 줄 50 을 먹인다",
                   "🔴 심었나": True, "심은 수": len(esc_lines),
                   "🔴 발화했나": len(old_keep) == 0,
                   "살아남은 수": len(old_keep),
                   "뜻": "🔴 50 이 **전부** 조용히 버려진다 --- 예외도 0 도 아니고 "
                        "**작고 그럴듯한 양수**만 남는다(티처 #85 의 진단 그대로)"})

    # (나) 새 판독기: 같은 50 을 정본으로 읽으면 전부 살아남는다
    new_tree = {p for p in ks.git_paths("ls-tree", "-r", "HEAD", "--", "data/state")
                if p.startswith("data/state/cache_")}
    checks.append({"검사": "나 · 정본 판독기가 그 50 을 참 이름으로 내나",
                   "🔴 심었나": True, "심은 수": len(sample[:50]),
                   "🔴 발화했나": all(p in new_tree for p in sample[:50]),
                   "잡은 수": sum(1 for p in sample[:50] if p in new_tree)})

    # (다) 🔴 음성 대조 --- ASCII 경로에는 두 인코딩이 안 갈린다. 여기선 아무 일도 안 나야 한다
    ascii_sample = sorted(p for p in disk if ks.octal_escape(p) == p)[:50]
    checks.append({"검사": "다 · 🔴 음성 대조 --- ASCII 경로 50 은 두 인코딩이 같다",
                   "🔴 심었나": False, "심은 수": len(ascii_sample),
                   "🔴 발화했나": False,
                   "두 인코딩이 다른 것": sum(1 for p in ascii_sample
                                     if ks.octal_escape(p) != p)})

    # (라) `diff_report` 자체의 검정력 --- 심은 키를 못 찾으면 수 대신 「모른다」를 내나
    A = set(sample[:10])
    B_bad = {ks.octal_escape(p) for p in sample[:10]}
    rep = ks.diff_report("A", A, "B(두 번째 인코딩)", B_bad, probe=ks.octal_escape)
    checks.append({"검사": "라 · `diff_report` 가 두 이름을 만나면 수를 안 내나",
                   "🔴 심었나": True, "심은 수": 10,
                   "🔴 발화했나": rep["🔴 A − B"] == ks.UNKNOWN,
                   "낸 것": rep["🔴 A − B"],
                   "③ 두 이름 대조": rep["③ 두 이름 대조"],
                   "🔴 경보(두 이름 의심)":
                       rep["🔴 경보(두 이름 의심 · 크기와 양쪽 차가 같다)"]})

    # (마) 🔴 음성 대조 --- A 와 B 가 **같은 인코딩**이면 ③ 은 아무것도 잡으면 안 된다
    ok = ks.diff_report("A", set(sample[:10]), "B(같은 인코딩)", set(sample[:10]),
                        probe=ks.octal_escape)
    checks.append({"검사": "마 · 🔴 음성 대조 --- 같은 인코딩 두 집합",
                   "🔴 심었나": False, "심은 수": 10,
                   "🔴 발화했나": ok["🔴 A − B"] == ks.UNKNOWN,
                   "낸 것": ok["🔴 A − B"], "통과": ok["통과"]})

    planted = [c for c in checks if c["🔴 심었나"]]
    fired = [c for c in planted if c["🔴 발화했나"]]
    return {
        "검사": "5 🔴 심어서 확인 --- 검출기가 두 번째 인코딩을 보나",
        "🔴 심은 수(분모)": len(planted),
        "🔴 발화한 수": len(fired),
        "음성 대조": [c for c in checks if not c["🔴 심었나"]],
        "검사들": checks,
        "🔴 두 인코딩이 갈리는 디스크 파일 수": len(sample),
        "통과": len(fired) == len(planted) and all(
            not c["🔴 발화했나"] for c in checks if not c["🔴 심었나"]),
    }


# ══════════════════════════════════════════════════ 절 6 · 날 것 게이트
def sec6(cen: dict) -> dict:
    """🔴 ⑤′ 가 grep 으로 잡을 자리. **⑤′ 러너 자체는 안 고친다**(규칙 4).

    `git grep -lF -e '"통과":'` 가 게이트 명부를 뽑으므로, 이 러너가 `통과` 키를 내면
    **다음 ⑤′ 부터 명부에 자동으로 잡힌다.** `fiveprime902.py` 를 편집하면
    ① 수리 레인이 한 사이클에 둘이 되고 ② 이번 사이클 ⑤′ 의 코드 sha 가 도중에 바뀐다.
    """
    return {
        "검사": "6 날 것 호출 게이트(⑤′ 명부에 자동 편입)",
        "🔴 어떻게 명부에 드나": ("⑤′ 는 `git grep -lF -e '\"통과\":'` 로 게이트 생산자를 "
                          "뽑는다. 이 파일이 `통과` 키를 내므로 **다음 ⑤′ 부터 40 → 41 "
                          "명부에 잡힌다** --- 손 나열이 아니다"),
        "🔴 ⑤′ 러너를 고쳤나": False,
        "🔴 왜 안 고쳤나": ("규칙 4(수리 레인은 한 사이클에 하나) --- 이번 수리는 "
                      "`core.quotePath` 다. 그리고 `fiveprime902.py` 를 이 사이클 안에서 "
                      "고치면 ⑤′ 가 자기 코드 sha 가 바뀐 채로 돈다. **신고만 한다**"),
        "🔴 신고": ("`runners/fiveprime902.py` 에 이 게이트를 상설로 넣어야 한다 --- "
                  "지금은 이 러너가 있어야만 잡힌다. 다음 사이클 [수리] 후보"),
        "살아있는 날 것": cen["🔴 분모 ④-살아있는 날 것"],
        "㉮ 원리상 못 고친다": cen["🔴 분모 ④-㉮ 원리상 못 고친다"],
        "🔴 ㉯ 고칠 수 있는데 안 고친 것": cen["🔴 분모 ④-㉯ 고칠 수 있다(🔴 이 수가 0 이어야 통과)"],
        "통과": cen["🔴 분모 ④-㉯ 고칠 수 있다(🔴 이 수가 0 이어야 통과)"] == 0,
    }


# ══════════════════════════════════════════════════ main
def main() -> int:
    st = stamp()
    disk = _disk_cache()
    cen = census()
    s2 = sec2(disk)
    s3 = sec3(disk)
    s4 = sec4(disk)
    s5 = sec5(disk)
    s6 = sec6(cen)
    secs = {"1 날 것 호출 전수": cen, "2 `215 → 0`": s2, "3 지도 정정": s3,
            "4 철회": s4, "5 심어서 확인": s5, "6 날 것 게이트": s6}
    doc = {
        "무엇": ("노트 946 [수리] --- `core.quotePath` 전량 수리. "
               "「디스크에 있으나 어떤 ref 에도 없는 캐시 파일 215」는 존재하지 않는다"),
        "🔴 규약": ("조항 61(차집합은 홀로 못 선다) · 조항 59 · 조항 60(명령·범위·트리) · "
                 "규칙 4(수리 하나) · 941~945 동결"),
        "🔴 디스크 캐시 파일(분모)": len(disk),
        **secs,
        "🔴 절 수(분모)": len(secs),
        "🔴 `통과` 키를 가진 절": sum(1 for v in secs.values() if "통과" in v),
        "🔴 실패한 절": [k for k, v in secs.items() if v.get("통과") is not True],
        "통과": all(v.get("통과") is True for v in secs.values()),
        **st,
    }
    doc["시각(UTC · 끝)"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print("→", OUT.relative_to(ROOT), "· 통과", doc["통과"],
          "· 실패한 절", doc["🔴 실패한 절"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
