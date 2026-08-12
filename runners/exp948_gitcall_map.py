# -*- coding: utf-8 -*-
"""[탐색] 948 --- `lab/gitcall.py` 검출기의 **사각지대 지도**.

🔴 **판정이 아니다.** 문턱·사전등록·BCa·⑤′ 를 안 쓴다. 지도만 그린다.
🔴 규칙 1: 이 러너가 내는 수는 **이 사이클의 결론·원장 표제·커밋 제목에 안 들어간다.**

무엇을 재나 (넷)

    가  저장소가 `git -C` 를 **얼마나 쓰나** --- 그리고 그 `-C` 인자가
        **문자열 리터럴**인가 아닌가. 리터럴이면 검출기가 빠져나가고,
        비리터럴이면 검출기가 **떨궈서 우연히** 살아난다
    나  심어서 확인 --- 열두 꼴을 심어 몇이 빠져나가나
    다  전 브랜치(지역 69) 에 그 꼴이 이미 들어와 있나
    라  유령 하위명령 `ls-remote-nope` 의 자취 --- 코드 11 대 문서 10

읽기 전용이다. 아무것도 안 고친다.
"""
from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lab import gitcall as gc          # noqa: E402
from lab import keyspace as ks         # noqa: E402

OUT = ROOT / "runners" / "exp948_gitcall_map.json"

#: 🔴 git 의 **전역 옵션 중 뒤에 인자를 하나 먹는 것**(분리형).
#: `emits_paths` 의 건너뛰기는 이 중 `-c` **하나만** 안다.
GLOBAL_OPTS_TAKING_ARG = ("-C", "-c", "--git-dir", "--work-tree", "--namespace",
                          "--exec-path", "--config-env", "--super-prefix")


def _git(*a) -> bytes:
    r = subprocess.run(["git", "-C", str(ROOT), "-c", "core.quotePath=false", *a],
                       capture_output=True)
    return r.stdout


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ── 가 · 저장소의 `-C` 관용구 ──────────────────────────────────────────────
def section_a() -> dict:
    pys = sorted(ks.git_paths("ls-files", "--", "*.py", root=ROOT))
    lit, nonlit = [], []
    for rel in pys:
        try:
            tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError, OSError):
            continue
        for n in ast.walk(tree):
            if not isinstance(n, (ast.List, ast.Tuple)):
                continue
            raw = [gc._str_of(e) for e in n.elts]
            if not raw or raw[0] != "git":
                continue
            for i, v in enumerate(raw):
                if v in GLOBAL_OPTS_TAKING_ARG and v != "-c" and i + 1 < len(raw):
                    row = {"파일:줄": "%s:%d" % (rel, n.lineno), "옵션": v,
                           "인자 꼴": type(n.elts[i + 1]).__name__}
                    (lit if raw[i + 1] is not None else nonlit).append(row)
    return {
        "🔴 분모 훑은 추적 `.py`": len(pys),
        "명령": "git ls-files -- '*.py' (작업 트리)",
        "🔴 `-C`/`--git-dir`/`--work-tree` 를 쓰는 argv 리터럴 자리": len(lit) + len(nonlit),
        "🔴 그중 인자가 **문자열 리터럴**(= 검출기를 빠져나간다)": len(lit),
        "리터럴 목록": lit,
        "🔴 그중 인자가 **비리터럴**(`str(ROOT)` --- 자 A 가 떨궈서 우연히 산다)": len(nonlit),
        "비리터럴 예시 다섯": nonlit[:5],
        "🔴 뜻": ("저장소의 관용구는 **`[\"git\", \"-C\", str(ROOT), …]`** 하나뿐이고, "
                "`_str_of` 가 `str(ROOT)` 에 `None` 을 내면 `sites_ast` 의 리스트 축약이 "
                "그 원소를 **조용히 지운다**(`lab/gitcall.py:376`). 그래서 하위명령이 "
                "제자리로 밀려 올라와 검출이 **맞는 답을 틀린 이유로** 낸다. "
                "🔴 인자를 f-string 이나 리터럴로 쓰는 순간 그 우연이 깨진다"),
    }


# ── 나 · 심어서 확인 ───────────────────────────────────────────────────────
PLANTS = [
    ("가 저장소 관용구 그대로 `str(ROOT)`", '''
import subprocess
from pathlib import Path
ROOT = Path(".")
def f():
    return subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"],
                          capture_output=True)
'''),
    ("나 같은 것을 **f-string** 으로", '''
import subprocess
ROOT = "/x"
def f():
    return subprocess.run(["git", "-C", f"{ROOT}", "status"], capture_output=True)
'''),
    ("다 리터럴 절대경로", '''
import subprocess
def f():
    return subprocess.run(["git", "-C", "/x/y", "ls-files"], capture_output=True)
'''),
    ("라 리터럴 상대경로 `.`", '''
import subprocess
def f():
    return subprocess.run(["git", "-C", ".", "status"], capture_output=True)
'''),
    ("마 절대경로 git · 셸 문자열", '''
import subprocess
def f():
    return subprocess.run("/usr/bin/git status --porcelain", shell=True)
'''),
    ("바 변수 접두 git · 셸 문자열", '''
import subprocess
GIT = "git"
def f():
    return subprocess.run(f"{GIT} status --porcelain", shell=True)
'''),
    ("사 앞 공백 셸 문자열", '''
import subprocess
def f():
    return subprocess.run(" git status --porcelain", shell=True)
'''),
    ("아 절대경로 git · argv 리터럴", '''
import subprocess
def f():
    return subprocess.run(["/usr/bin/git", "status", "--porcelain"],
                          capture_output=True)
'''),
    ("자 `--git-dir` 분리형", '''
import subprocess
def f():
    return subprocess.run(["git", "--git-dir", "/x/.git", "ls-files"],
                          capture_output=True)
'''),
    ("차 `--work-tree` 분리형", '''
import subprocess
def f():
    return subprocess.run(["git", "--work-tree", "/x", "status"],
                          capture_output=True)
'''),
    ("카 `-C` 를 변수 argv 로(갈래 ⑤)", '''
import subprocess
def _g(a):
    return subprocess.run(["git"] + a, capture_output=True)
def f():
    args = ["-C", "/x", "status"]
    return _g(args)
'''),
    ("타 `-C` + 경로 플래그(양성 대조)", '''
import subprocess
def f():
    return subprocess.run(["git", "-C", "/x", "status", "--porcelain"],
                          capture_output=True)
'''),
]


def section_b() -> dict:
    reg = gc.wrapper_registry(sorted(ks.git_paths("ls-files", "--", "*.py", root=ROOT)),
                              ROOT)
    rows, escaped = {}, []
    with tempfile.TemporaryDirectory() as td:
        for i, (name, src) in enumerate(PLANTS):
            rel = "p%d.py" % i
            (Path(td) / rel).write_text(src, encoding="utf-8")
            got = list(gc.sites_ast([rel], Path(td), reg))
            vecs = [v for _r, _l, v, _k in got]
            caught = [v for v in vecs if gc.emits_paths(v)[0]]
            rows[name] = {
                "🔴 잡았나": bool(caught),
                "자 A 가 만든 벡터": vecs,
                "왜": [gc.emits_paths(v)[1] for v in vecs] or
                     ["자 A 가 호출 자리 자체를 못 봤다"],
            }
            if not caught:
                escaped.append(name)
    return {
        "🔴 분모 심은 꼴": len(PLANTS),
        "🔴 빠져나간 꼴": len(escaped),
        "빠져나간 목록": escaped,
        "갈래별": rows,
        "🔴 주의(조항 59)": ("이 표는 **검출기의 성질**이지 저장소의 상태가 아니다. "
                       "오늘 저장소에 이 꼴이 몇 개 있나는 절 「가」·「다」에 있다"),
    }


# ── 다 · 전 브랜치에 이미 들어와 있나 ───────────────────────────────────────
BRANCH_PATTERNS = ('"-C", *"', '"--git-dir", *"', '"--work-tree", *"',
                   '/usr/bin/git', '/bin/git"', '"git -C ')


def section_c() -> dict:
    refs = [x for x in _git("for-each-ref", "--format=%(refname:short)",
                            "refs/heads").decode("utf-8", "surrogateescape").split("\n") if x]
    args = ["grep", "-n", "-z", "-I", "-E",
            "|".join(p.replace("|", r"\|") for p in BRANCH_PATTERNS)]
    r = subprocess.run(["git", "-C", str(ROOT), "-c", "core.quotePath=false",
                        *args, *refs, "--", "*.py"], capture_output=True)
    hits = [x for x in r.stdout.decode("utf-8", "surrogateescape").split("\0") if x.strip()]
    sh = subprocess.run(["git", "-C", str(ROOT), "-c", "core.quotePath=false",
                         "grep", "-n", "-z", "-I", "-E",
                         r"os\.system|os\.popen|shell=True", *refs, "--", "*.py"],
                        capture_output=True)
    #: `git grep -n -z` 는 `<ref>:<파일>\0<줄>\0<내용>\n` 를 낸다 --- 줄바꿈까지 끊는다
    shflat = []
    for chunk in sh.stdout.decode("utf-8", "surrogateescape").split("\0"):
        shflat += chunk.split("\n")
    shfiles = sorted({x.split(":", 1)[-1] for x in shflat if ":" in x and x.endswith(".py")})
    return {
        "🔴 분모 지역 브랜치 끝점": len(refs),
        "명령": "git grep -n -z -I -E <여섯 꼴> <브랜치 69> -- '*.py'",
        "🔴 여섯 꼴의 히트(필드 수 / 3 = 자리)": len(hits) // 3,
        "잰 꼴": list(BRANCH_PATTERNS),
        "🔴 셸 호출(`os.system`/`os.popen`/`shell=True`) 이 있는 파일": shfiles,
        "🔴 뜻(조항 59)": "0 은 **「안 걸렸다」**이지 **「못 걸린다」가 아니다**",
    }


# ── 라 · 유령 하위명령 ─────────────────────────────────────────────────────
def section_d() -> dict:
    pys = sorted(ks.git_paths("ls-files", "--", "*.py", root=ROOT))
    b_with = set(gc.sites_regex(pys, ROOT))
    orig = gc.PATH_SUBS_ALWAYS
    orig_tok = gc.TOKENS
    try:
        gc.PATH_SUBS_ALWAYS = tuple(x for x in orig if x != "ls-remote-nope")
        gc.TOKENS = tuple(sorted(set(gc.PATH_SUBS_ALWAYS) | set(gc.PATH_SUBS_COND) |
                                 set(gc.PATH_FLAGS)))
        b_without = set(gc.sites_regex(pys, ROOT))
        missed_wo = sorted((set(gc.PATH_SUBS_ALWAYS) | set(gc.PATH_SUBS_COND) |
                            set(gc.PATH_FLAGS)) -
                           {"ls-files", "ls-tree", "--name-only", "--name-status"})
    finally:
        gc.PATH_SUBS_ALWAYS = orig
        gc.TOKENS = orig_tok
    missed_now = sorted((set(orig) | set(gc.PATH_SUBS_COND) | set(gc.PATH_FLAGS)) -
                        {"ls-files", "ls-tree", "--name-only", "--name-status"})
    carriers = [x for x in _git("grep", "-l", "-z", "-F", "ls-remote-nope",
                                "HEAD").decode("utf-8", "surrogateescape").split("\0") if x]
    return {
        "코드 `PATH_SUBS_ALWAYS` 의 수": len(orig),
        "`docs/루프.md:751-752` 의 표": 10,
        "🔴 차": sorted(set(orig) - {"ls-files", "ls-tree", "status", "grep",
                                    "check-ignore", "clean", "diff-tree",
                                    "diff-index", "diff-files", "whatchanged"}),
        "🔴 유령이 실려 나간 커밋된 파일": carriers,
        "🔴 산출물의 「946 이 통째로 못 본 것」": {"지금": len(missed_now),
                                    "유령을 빼면": len(missed_wo)},
        "🔴 유령이 자 B 히트를 바꾸나": {"유령 포함": len(b_with),
                              "유령 제거": len(b_without),
                              "차(양방향)": [len(b_with - b_without),
                                        len(b_without - b_with)]},
        "🔴 어느 쪽이 틀렸나": ("**코드가 틀렸다.** `git ls-remote` 는 실재하지만 **ref 를 내지 "
                       "경로를 안 낸다** --- 오타를 고쳐도 이 목록에 들 물건이 아니다. "
                       "그리고 `ls-remote-nope` 는 코드·산출물 밖 **어디에도** 없다"
                       "(주석 0 · 문서 0 · 노트 0 · 커밋 본문 0)"),
    }


def main() -> None:
    started = datetime.now(timezone.utc).isoformat()
    out = {
        "노트": "948 [탐색] --- `lab/gitcall.py` 사각지대 지도",
        "🔴 레인": "탐색 --- 판정 아님. 문턱·사전등록·BCa·⑤′ 를 안 썼다",
        "🔴 규칙 1": "이 수는 이 사이클의 결론·원장 표제·커밋 제목에 안 들어간다",
        "읽은 시점": started,
        "🔴 읽은 파일의 sha256(주 세션이 동시에 고치는 중 --- 흔들린다)": {
            "lab/gitcall.py": _sha(ROOT / "lab" / "gitcall.py"),
            "runners/fiveprime902.py": _sha(ROOT / "runners" / "fiveprime902.py"),
            "docs/루프.md": _sha(ROOT / "docs" / "루프.md"),
        },
        "가 저장소의 `-C` 관용구": section_a(),
        "나 심어서 확인": section_b(),
        "다 전 브랜치에 이미 들어와 있나": section_c(),
        "라 유령 하위명령 `ls-remote-nope`": section_d(),
        "끝난 시각": datetime.now(timezone.utc).isoformat(),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items()
                      if not isinstance(v, dict) or "sha256" in k}, ensure_ascii=False,
                     indent=2))
    print("→", OUT)


if __name__ == "__main__":
    main()
