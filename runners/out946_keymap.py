"""노트 946 [탐색] --- **검출기가 자기 키공간을 볼 수 있나**. 전수 지도.

🔴 **이것은 탐색 레인이다**(`docs/루프.md` 레인 셋). **판정하지 않는다 · 판 ρ 를 안 부른다 ·
문턱도 사전등록도 없다.** 넷만 낸다: 무엇을 했나 · 무엇이 나왔나 · **분모** · 못 한 것.

## 물음

티처 #85 의 진단: 941~945 **여섯**이 「검출기가 못 본다」로 끝났고 **구조가 그 오류를 만든다**.
① 이 저장소가 세계를 재는 방식은 거의 전부 **「문자열 키 집합의 차집합」**
② **키 공간은 항상 남이 만들고** 거의 모든 외부 키 공간은 **인코딩이 둘 이상**이다
③ 🔴 차집합 개수는 **자기 실패와 구별되지 않는 유일한 출력 타입**이다

그래서 `out945_fiveprime.json` 절 2 의 **게이트 생산자 40** 각각에 대해 센다:
**외부 문자열 키 위에서 차집합·포함을 계산하면서 두 번째 인코딩을 안 가진 것이 몇인가.**

## 자 --- 세는 규칙(코드로 먼저 박고 값을 나중에 본다)

| 축 | 무엇을 AST 에서 찾나 |
|---|---|
| **가 · 외부 키 원천** | `subprocess`+`git` · 파일시스템 훑기(`glob`/`rglob`/`iterdir`/`listdir`/`walk`/`scandir`) · `json.load(s)` · `np.load`/`.files` · `os.environ`/`sys.argv` |
| **나 · 집합 셈** | `in`/`not in` · `-`/`&`/`|`/`^` · `.difference(`/`.issubset(`/`.intersection(`/`.union(` · 컴프리헨션의 `if … in …` |
| **다 · 두 번째 인코딩 방어** | `-z` · `quotePath` · `octal_unescape` · `os.fsdecode/fsencode` · `unicodedata.normalize`/`NFC`/`NFD` · `.casefold()`/`.lower()` · `.strip()`/`.rstrip()`/`.lstrip()` · `.replace(` · `deep=` · 별칭표(`ALIAS`/`정규화`/`normalize`/`canon`) |

🔴 **한계를 먼저 적는다**: 이 자는 **정적**이다. 「방어가 있다」는 *같은 파일 어딘가에*
정규화 낱말이 있다는 뜻이지, **그 키 경로에 걸려 있다는 뜻이 아니다.** 그러므로
**「방어 없음」은 셀 수 있고 「방어 있음」은 상한이다.** 이 비대칭을 산출물에 박는다.

    python3 runners/out946_keymap.py       # → runners/out946_keymap.json
"""
from __future__ import annotations

import ast
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab import keyspace as ks                                    # noqa: E402

OUT = ROOT / "runners" / "out946_keymap.json"
ROSTER_SRC = ROOT / "runners" / "out945_fiveprime.json"

#: 다 · 두 번째 인코딩 방어의 **표지 낱말**. 🔴 원문 그대로 소스에서 찾는다.
GUARDS = ("-z", "quotePath", "quotepath", "octal_unescape", "fsdecode", "fsencode",
          "unicodedata", "NFC", "NFD", "casefold", ".lower()", ".upper()",
          ".strip()", ".rstrip(", ".lstrip(", ".replace(", "deep=",
          "ALIAS", "alias", "normalize", "canon", "정규화")

FS_CALLS = ("glob", "rglob", "iterdir", "listdir", "walk", "scandir")
SET_METH = ("difference", "issubset", "issuperset", "intersection", "union",
            "symmetric_difference", "isdisjoint")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def roster() -> list[str]:
    """🔴 명부를 손으로 나열하지 않는다 --- 945 의 산출물에서 **읽는다**."""
    d = json.loads(ROSTER_SRC.read_text(encoding="utf-8"))
    return list(d["2 게이트"]["게이트 생산자"])


def scan(rel: str) -> dict:
    src = (ROOT / rel).read_text(encoding="utf-8")
    tree = ast.parse(src)

    srcs: dict[str, list[int]] = {}
    ops: dict[str, list[int]] = {}

    def add(d: dict, k: str, ln: int) -> None:
        d.setdefault(k, [])
        if ln not in d[k]:
            d[k].append(ln)

    for n in ast.walk(tree):
        # ── 가 · 외부 키 원천 ────────────────────────────────────────────
        if isinstance(n, ast.Call):
            fn = getattr(n.func, "attr", None) or getattr(n.func, "id", None) or ""
            consts = [a.value for a in n.args
                      if isinstance(a, ast.Constant) and isinstance(a.value, str)]
            if fn in ("run", "Popen", "check_output", "getoutput") and (
                    "git" in consts or any("git" in str(c)[:4] for c in consts)):
                add(srcs, "git", n.lineno)
            if fn in FS_CALLS:
                add(srcs, "파일시스템", n.lineno)
            if fn in ("load", "loads") and getattr(
                    getattr(n.func, "value", None), "id", "") == "json":
                add(srcs, "JSON", n.lineno)
            if fn == "load" and getattr(
                    getattr(n.func, "value", None), "id", "") in ("np", "numpy"):
                add(srcs, "npz", n.lineno)
            if fn in SET_METH:
                add(ops, f".{fn}()", n.lineno)
        #: 🔴 **감싼 호출도 잡는다** --- `_git("ls-tree", …)` 처럼 래퍼를 쓰면 위 규칙이
        #: 0 을 낸다(첫 판이 실제로 git 사용자 **0** 을 냈다 --- 조항 59 의 얼굴).
        #: 그래서 `"git"` 이라는 argv 원소가 파일 어디에든 있으면 git 사용자로 센다.
        if isinstance(n, ast.Constant) and n.value == "git":
            add(srcs, "git", n.lineno)
        if isinstance(n, ast.Attribute) and n.attr == "files":
            add(srcs, "npz", n.lineno)
        if isinstance(n, ast.Attribute) and n.attr in ("environ", "argv"):
            add(srcs, "환경/인자", n.lineno)
        # ── 나 · 집합 셈 ────────────────────────────────────────────────
        if isinstance(n, ast.Compare) and any(
                isinstance(o, (ast.In, ast.NotIn)) for o in n.ops):
            add(ops, "in / not in", n.lineno)
        if isinstance(n, ast.BinOp) and isinstance(
                n.op, (ast.Sub, ast.BitAnd, ast.BitOr, ast.BitXor)):
            add(ops, "− & | ^", n.lineno)

    guards = {g: src.count(g) for g in GUARDS if g in src}
    #: 🔴 「이 파일이 `git` 을 부르면서 `-z`/`quotePath` 를 안 쓴다」는 **키 경로에 직접
    #: 걸리는** 유일한 강한 신호다. 나머지 방어 표지는 상한이다.
    git_lines = srcs.get("git", [])
    git_guarded = any(g in src for g in ("-z", "quotePath", "quotepath"))

    return {
        "파일": rel,
        "가 · 외부 키 원천": {k: {"자리 수": len(v), "줄": v[:8]} for k, v in srcs.items()},
        "외부 원천 가짓수": len(srcs),
        "나 · 집합 셈": {k: {"자리 수": len(v), "줄": v[:8]} for k, v in ops.items()},
        "집합 셈 자리 합": sum(len(v) for v in ops.values()),
        "다 · 방어 표지(🔴 상한이다)": guards,
        "방어 표지 가짓수": len(guards),
        "🔴 git 을 부르나": bool(git_lines),
        "🔴 git 을 부르면서 인용을 끄나": git_guarded if git_lines else None,
    }


def _rho_check() -> dict:
    """🔴 **import 문으로** 확인한다 --- 소스 문자열을 grep 하면 이 검사 자신의 문장이
    걸려 「확인 실패」가 난다(첫 판이 실제로 그랬다). 자기 언급과 실제 배선은 둘이다."""
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    mods = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            mods |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            mods.add(n.module or "")
            mods |= {f"{n.module}.{a.name}" for a in n.names}
    banned = sorted(m for m in mods
                    if any(b in m for b in ("board", "harness", "pairboot", "numpy")))
    return {"세는 법": "이 파일의 `import` 문 전량을 AST 로 뽑아 판 관련 모듈을 찾는다",
            "import 한 모듈": sorted(mods),
            "🔴 판 관련 import": banned,
            "🔴 판 ρ 를 불렀나": bool(banned)}


def main() -> int:
    t0 = dt.datetime.now(dt.timezone.utc)
    names = roster()
    rows, missing = [], []
    for rel in names:
        if not (ROOT / rel).exists():
            missing.append(rel); continue
        try:
            rows.append(scan(rel))
        except (SyntaxError, UnicodeDecodeError, OSError) as e:
            missing.append(f"{rel} ({type(e).__name__})")

    ext = [r for r in rows if r["외부 원천 가짓수"] > 0]
    both = [r for r in ext if r["집합 셈 자리 합"] > 0]
    naked = [r for r in both if r["방어 표지 가짓수"] == 0]
    git_users = [r for r in rows if r["🔴 git 을 부르나"]]
    git_naked = [r for r in git_users if r["🔴 git 을 부르면서 인용을 끄나"] is False]

    #: 원천별 분해 --- 어느 이름 공간이 제일 많이 쓰이나
    by_src: dict[str, int] = {}
    for r in ext:
        for k in r["가 · 외부 키 원천"]:
            by_src[k] = by_src.get(k, 0) + 1

    doc = {
        "무엇": ("노트 946 [탐색] --- 게이트 생산자 40 각각이 **외부 문자열 키 위에서 "
               "차집합·포함을 계산하면서 두 번째 인코딩을 가졌나**. 🔴 지도이지 판정이 아니다"),
        "🔴 레인": "탐색 --- 판정 없음 · 문턱 없음 · 사전등록 없음 · 🔴 판 ρ 를 안 불렀다",
        "🔴 명부를 어디서 읽었나": "runners/out945_fiveprime.json:2 게이트/게이트 생산자 (손 나열 아님)",
        "🔴 세는 명령": "각 파일을 `ast.parse` → 가/나/다 세 축의 노드를 센다",
        "🔴 범위": "게이트 생산자 40 (=`git grep -lF -e '\"통과\":'` 로 945 가 뽑은 명부)",
        "🔴 트리": "작업 트리(커밋된 파일을 그대로 읽는다)",

        "🔴 분모 ① 명부": len(names),
        "🔴 분모 ② 읽은 파일": len(rows),
        "못 읽은 것": missing,
        "🔴 분모 ③ 외부 키 원천을 하나라도 쓰는 것": len(ext),
        "🔴 분모 ④ 외부 키 + 집합 셈 둘 다 하는 것": len(both),
        "🔴 ⑤ 그중 방어 표지가 **하나도 없는 것**": len(naked),
        "🔴 ⑤ 목록": [r["파일"] for r in naked],
        "🔴 ⑥ git 을 부르는 것": len(git_users),
        "🔴 ⑦ 그중 인용을 안 끄는 것": len(git_naked),
        "🔴 ⑦ 목록": [r["파일"] for r in git_naked],
        "원천별(파일 수 · 중복 셈)": by_src,

        "🔴 이 자의 비대칭(먼저 적는다)": (
            "「방어 없음」은 셀 수 있고 **「방어 있음」은 상한이다** --- 정적 표지가 그 키 "
            "경로에 걸려 있는지는 원리상 못 본다. 그러므로 ⑤ 는 **하한**이고, "
            "「⑤ 밖은 안전하다」는 문장은 **이 자로 못 쓴다**(조항 59)"),
        "🔴 못 한 것": [
            "동적 경로를 안 봤다 --- 키가 함수 인자로 건너오면 이 자는 못 따라간다",
            "「방어가 그 키에 걸렸나」를 **안 쟀다**(정적 표지의 존재만 봤다)",
            "게이트 생산자 40 **밖**은 안 봤다 --- 저장소 `.py` 750 중 40 이 분모다",
            "🔴 심은 키를 **각 생산자에 실제로 주입해 보지 않았다** --- 그건 판정 레인의 일이고 "
            "이 팔은 지도만 그린다",
            "인코딩이 둘 이상인지를 **원천별로 실측하지 않았다**(git 만 실측했다)",
        ],
        "파일별": rows,
        "🔴 절 수(분모)": 1,
        "통과": None,
        "🔴 `통과` 가 왜 None 인가": ("탐색 레인은 **판정하지 않는다**(`docs/루프.md` 규칙 2). "
                              "🔴 `통과: null` 은 「모른다」가 아니라 「이 팔은 안 잰다」다"),
        "시각(UTC · 시작)": t0.isoformat(timespec="seconds"),
        "시각(UTC · 끝)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "🔴 코드 sha256(이게 자다)": {"runners/out946_keymap.py": sha(Path(__file__).resolve())},
        "🔴 입력 산출물 sha256": {"runners/out945_fiveprime.json": sha(ROSTER_SRC)},
        "⚠ git HEAD(시작 시점 · 판정에 쓰지 마라)": ks.git_lines("rev-parse", "HEAD")[0],
        "🔴 판 ρ 를 불렀나": _rho_check(),
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print("→", OUT.relative_to(ROOT), "· 분모", len(names), len(both), "· 방어 없음", len(naked))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
