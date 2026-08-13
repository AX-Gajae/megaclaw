#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""🔴 **⑤′ 취합 검사를 손 절차가 아니라 러너로 만든다** --- 이슈 #140 M3.

## 왜 러너인가

`docs/루프.md` 의 ⑤′ 는 v3.1·v3.2 두 번 개정되고도 **데뷔전마다 자기 항목에 걸렸다.**
v3.2 의 첫 정식 운용(커밋 `765c7e6f6`)에서 티처 #64 M3 가 센 것:

1. **(가) 소비자 목록을 파일로 안 남겼다.** `docs/루프.md:249-253` 이 `grep -rl` 역참조로
   *"소비자 후보를 **파일로 남긴다**"* 를 요구하는데 커밋이 실은 것은 산출물 넷뿐이다.
2. 🔴 **(나) 분모가 바뀌었다.** 커밋이 *"바뀐 경로 **26**. 그중 실제로 돌린 것은 **셋**"* 이라
   적었다. **26 은 맞다.** 그러나 ⑤′ 의 대상은 「바뀐 경로」가 아니라 **역참조한 소비자 전량**
   이고, 티처가 역참조를 돌리니 **102개(그중 `.py` 52)** 였다.
   **「셋/26」과 「셋/102」는 다른 문장이다**(조항 60). ⑤′ 를 만든 목적이 정확히 이 바꿔치기다.
3. **(다) 판정 키 규약화가 0.** `docs/루프.md:256-258` 이 *"판정 키 이름을 `통과` 하나로
   규약화하라"* 고 적었는데 `runners/out899a_gates.json` 의 절 아홉 중 `통과` 키를 가진 것이
   **0개**다. 키 이름이 자리마다 다르면 **「없다」를 「통과」로 읽는 길이 영구히 열려 있다.**

**셋 다 「사람이 그때그때 하는 일」이라서 안 지켜졌다.** 그래서 러너로 내린다 ---
⓪ 관문 → 소비자 **기계 역참조** → **목록을 산출물에 남김** → 게이트 실행 → 판정 키 감사 →
도장 확인 → `quote901` 무변 확인 → D1 실측. **일곱 절 전부 `통과` 키를 갖는다.**

## 🔴 분모를 산출물에 박는다 (조항 59·60)

`1 소비자 역참조` 절은 넷을 **따로** 낸다: **바뀐 경로 수 · 역참조 소비자 수 ·
실제로 돌린 수 · 🔴 안 돌린 수**. 그리고 **안 돌린 것의 목록 전량**을 싣는다 ---
「안 돌렸다」를 「없다」로 읽을 길을 없앤다.

역참조의 **자를 셋** 쓴다(각 자의 수를 따로 적는다). 자가 하나면 그 자의 사각지대가
그대로 「없다」가 된다:

| 자 | 바늘 | 무엇을 잡나 |
|---|---|---|
| 전체 경로 | `ingest/audit.py` | 경로 문자열로 부르는 곳 |
| 파일명 | `audit.py` | 경로 없이 이름만 적은 곳 |
| 모듈 점경로 | `ingest.audit` | 🔴 `import` --- **앞의 둘이 원리상 못 잡는다** |

🔴 **`git diff --name-only` 는 한글 경로를 `"docs/\353\243..."` 로 이스케이프해서 낸다.**
그 문자열을 그대로 바늘로 쓰면 **한 곳도 안 맞고 종료 0 이 난다**(조항 59 그 자체).
그래서 `-c core.quotepath=false` 와 `-z` 를 쓴다. 실측: 이스케이프본 75 대 정상본 78.

## 쓰기

    python3 runners/fiveprime902.py --base <취합 시작 rev> [--head HEAD]
        [--tree <rev>]            # 🔴 기본은 **커밋된 트리**(= --head) · `작업트리` 로 옛 동작
        [--ran <경로> ...]        # 이번에 실제로 다시 돌린 소비자
        [--exempt <경로>=<사유>]  # 🔴 안 돌린 `.py` 에 사유를 단다(사유 없으면 실패다)
        [--gates]                 # 게이트를 실제로 돌린다(안 주면 「안 돌렸다」로 적는다)
        [--expected-repairs N]    # 🔴 955 R6 · 사전등록이 예고한 `[수리]` 레인 수
        [--prereg docs/prereg_955_D.md]   # 그 수를 §8 표에서 읽는다(인자가 이긴다)
        [--out runners/out902b_fiveprime.json]

🔴 **`timeout` 은 이 환경에 없다(rc=127).** 이 러너는 `subprocess` 의 `timeout=` 만 쓴다.

## 🔴 955 수리 셋 (티처 #93)

- **R4 (C3)** --- ⑤′ 가 **자기 산출물**(`out*_fiveprime.json`)을 자기 채점에 넣었다.
  954 실측: 원장 **18/27**(66.7%) 이 커밋 제목엔 **30/39**(76.9%) --- 차이는 통째로
  `out954_fiveprime.json` 자기 자신(절 12 · 전부 `통과`)이었다. 이제 **이름으로 뺀다**
  (`SELF_OUT_RE`) 그리고 **「뺀 것」 칸에 그 사실을 적는다**(954 엔 「없음」이라 적혀 있었다).
- **R5 (M5)** --- `docs/루프.md:148`(v3.2) 은 **커밋된 트리**를 되짚으라고 적는데 ⑤′ 가
  작업 트리를 봤다(티처 #63 C1 이 v3.1 에서 고친 병의 재발). 이제 절 3·4·7·8 이
  `git ls-tree -r` + `git cat-file blob` 으로 읽고, **커밋 안 된 파일은 「없다」가 아니라
  「커밋 안 됨」으로 따로 센다**(조항 59). 어느 트리·어느 sha 인지를 산출물에 박는다.
- **R6 (C4·㉤)** --- 954 는 「수리 레인 하나를 썼다」고 적고 `[수리]` 커밋을 **셋** 했다.
  이제 **절 8** 이 `git log <merge-base main HEAD>..HEAD` 에서 그 수를 세고 **명령·범위·
  트리를 같이 적고**(규약 60) 사전등록 §8 의 예고 수와 견준다.
"""
import argparse
import ast
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lab import gitcall as gc                                       # noqa: E402
from lab import keyspace as ks                                      # noqa: E402

OUT_DEFAULT = ROOT / "runners/out902b_fiveprime.json"

#: 🔴 **이 러너가 자기 판정에 쓰는 코드** --- 도장 ④ 가 이것들의 sha256 이다.
STAMP_CODE = ["runners/fiveprime902.py", "runners/quote901.py",
              "lab/gitcall.py", "lab/keyspace.py"]

#: 🔴 **953 --- 이 한 줄이 22 사이클 붉음의 원인이었다**(티처 #90 처방 · #91 이 확정).
#:
#: 옛 값은 ``["runners/out899a_gates.json"]`` --- **파일 하나 하드코딩**이었다. 그 파일은
#: ① 절 5 중 `통과` 키가 **0** 이고 ② **남의 소유라 「고치지 않고 센다」**로 이 검사가 스스로
#: 선언했고 ③ 생산자는 「다른 팔 소유」라 **돌리는 것이 금지**돼 있다.
#: 🔴 **즉 초록이 도달 불가능하게 정의돼 있었다.** `3 판정 키 규약` **22/22 붉음**은
#: 게으름이 아니라 **정의의 기록**이었고, 스물세 번째로 세는 것은 이제 정보가 아니다.
#:
#: 🔴 **끈 것이 아니라 자리를 옮겼다.** 대상은 이제 **이 사이클이 찍은 산출물**
#: (`--base`..작업트리에서 바뀐 `runners/out*.json`)이고, 그건 **내가 고칠 수 있는 것**이다 ---
#: 규약(「모든 절이 `통과` 키를 갖는다」)은 **자기 산출물에 걸릴 때만** 자다.
#: 옛 파일은 ``--keyaudit runners/out899a_gates.json`` 로 언제든 다시 넣을 수 있다.
KEYAUDIT_MUST: list = []

#: 🔴 대상에서 **빼는** 것: 이 러너 자신의 산출물(자기 자신을 채점하는 순환)과 도장 파일.
KEYAUDIT_SKIP = ("out902b_fiveprime", "out952_docstamp", "out953_docstamp")

#: 🔴🔴 **955 R4 (티처 #93 C3)** --- **이 러너 자신의 산출물을 이름으로 배제한다.**
#:
#: 954 실측: 커밋 제목은 `0/27 → 30/39`, 원장은 `0/27 → 18/27` 이었고 **원장이 맞았다.**
#: 차이의 정체는 `runners/out954_fiveprime.json` **자기 자신**이 대상에 들어간 것이다 ---
#: 그 파일은 절 12 를 갖고 그 12 가 **전부 `통과`** 라서 분자·분모가 **동시에** 부풀었다
#: (18+12=30 · 27+12=39). 즉 **66.7% 가 76.9% 로 보였다.**
#: 🔴 이름 하나(`out902b_fiveprime`)를 하드코딩하던 위 `KEYAUDIT_SKIP` 으로는 못 막는다 ---
#: `--out` 이 사이클마다 바뀌기 때문이다(`out954_fiveprime.json`). **꼴로 배제한다.**
#: ⚠ 꼬리를 열어 둔다(`out902b_fiveprime_901.json` 같은 **보관본**도 자기 산출물이다).
SELF_OUT_RE = re.compile(r"(?:^|/)out[^/]*_fiveprime[^/]*\.json$")


def is_self_out(rel: str) -> bool:
    """🔴 이 러너 자신의 산출물인가(`out*_fiveprime.json`) --- **이름으로만** 판정한다."""
    return bool(SELF_OUT_RE.search(str(rel)))


# ── 🔴 커밋된 트리 판독기 (955 R5 · `docs/루프.md` v3.2 §148) ─────────────
#: `docs/루프.md:148` 은 ⑤′ 를 **「커밋된 트리에서」** 되짚으라고 적는다. 954 까지 이 러너는
#: 절 3·4·7 에서 **작업 트리**를 읽었다(티처 #63 C1 이 v3.1 에서 고친 병의 재발 · #93 M5).
#: 🔴 **「커밋 안 됨」은 「없다」가 아니다**(조항 59) --- 아래 판독기는 셋을 **갈라서** 낸다.
TREE_READ = ("읽었다", "커밋 안 됨", "없다", "못 읽었다")


def tree_paths(tree: str = "HEAD") -> tuple:
    """커밋된 트리의 경로 전량. 🔴 `-z` + `core.quotepath=false`(946 이 잡은 병)."""
    rc, out, err = _git(["-c", "core.quotepath=false", "ls-tree", "-r", "--name-only",
                         "-z", tree])
    if rc != 0:
        return set(), err[:200]
    return {p for p in out.split("\0") if p}, "없음"


def tree_blob(rel: str, tree: str = "HEAD", known=None):
    """🔴 커밋된 트리에서 **바이트**를 꺼낸다 --- `(상태, bytes|None)`.

    상태는 넷 중 하나다(조항 59): `읽었다` · **`커밋 안 됨`**(작업 트리엔 있는데 그 트리엔
    없다) · `없다`(양쪽 다 없다) · `못 읽었다`(git 이 화냈다).
    """
    if known is not None and rel not in known:
        return ("커밋 안 됨" if (ROOT / rel).exists() else "없다"), None
    r = subprocess.run(["git", "-C", str(ROOT), "cat-file", "blob",
                        "%s:%s" % (tree, rel)], capture_output=True, timeout=600)
    if r.returncode != 0:
        if (ROOT / rel).exists():
            return "커밋 안 됨", None
        return "없다", None
    return "읽었다", r.stdout


def tree_text(rel: str, tree: str = "HEAD", known=None):
    st, b = tree_blob(rel, tree, known)
    return st, (None if b is None else b.decode("utf-8", "surrogateescape"))


def keyaudit_targets(base: str, head: str) -> dict:
    """🔴 **이 사이클이 찍은 산출물**을 대상으로 삼는다(953 · 티처 #90 처방).

    분모를 나란히 박는다(조항 60): 바뀐 경로 · 그중 `runners/out*.json` · 뺀 것 · 남은 것.
    🔴 `-c core.quotepath=false` 를 쓴다 --- 946 이 잡은 병(이스케이프 바늘은 **종료 0** 으로
    「0개」를 낸다)이 여기서도 그대로 돈다.

    🔴 **955 R4** --- 후보에서 `out*_fiveprime.json`(자기 산출물)을 **이름으로 뺀다.**
    🔴 **955 R5** --- 대상은 **커밋된 것만**이다. 작업 트리에만 있는 후보는 「없다」로 세지
    않고 **「커밋 안 됨」으로 따로 센다**(조항 59).
    """
    rc, out, err = _git(["-c", "core.quotepath=false", "diff", "--name-only", "-z",
                         "%s..%s" % (base, head)])
    committed = sorted(p for p in out.split("\0") if p) if rc == 0 else []
    rc2, out2, _ = _git(["-c", "core.quotepath=false", "status", "--porcelain", "-z"])
    worktree = sorted(x[3:] for x in out2.split("\0") if len(x) > 3) if rc2 == 0 else []
    changed = sorted(set(committed) | set(worktree))

    def _cand(paths):
        return [p for p in paths if p.startswith("runners/out") and p.endswith(".json")]

    cand = _cand(changed)
    cand_committed = _cand(committed)
    self_out = sorted(p for p in cand if is_self_out(p))
    by_name = sorted(p for p in cand
                     if not is_self_out(p) and any(s in p for s in KEYAUDIT_SKIP))
    dropped = set(self_out) | set(by_name)
    keep = [p for p in cand_committed if p not in dropped]
    uncommitted = sorted(p for p in cand if p not in dropped and p not in set(committed))
    return {
        "🔴 왜 이 대상인가": ("옛 하드코딩(`out899a_gates.json`)은 **고칠 수 없는 남의 파일**이라 "
                       "초록이 도달 불가능했다. 자는 **자기 산출물**에 걸어야 자다"),
        "🔴 어느 트리인가(955 R5)": "**커밋된 트리** `%s` --- 대상은 커밋된 것만이다" % head,
        "바뀐 경로(커밋+작업트리)": len(changed),
        "그중 runners/out*.json": len(cand),
        # 🔴 955 R4 --- 이 칸이 954 에 「없음」이라 적혀 있었다. **무엇을 왜 뺐는지 적는다.**
        "🔴 뺀 것(자기 채점 순환·도장)": {
            "🔴 뺀 수(분자) / 후보 수(분모)": "%d / %d" % (len(dropped), len(cand)),
            "🔴 자기 산출물(`out*_fiveprime.json` · 이름으로 뺐다 · 955 R4)": self_out or "없음",
            "이름 목록(`KEYAUDIT_SKIP`)으로 뺀 것": by_name or "없음",
            "🔴 왜": ("954 는 `runners/out954_fiveprime.json` **자기 자신**을 대상에 넣었다 --- "
                   "그 파일의 절 12 가 **전부 `통과`** 라 분자·분모가 동시에 부풀어 "
                   "**18/27(66.7%) 이 30/39(76.9%) 로** 보였다(티처 #93 C3)"),
        },
        "🔴 커밋 안 된 후보(= 「없다」가 아니다 · 조항 59 · 955 R5)": uncommitted or "없음",
        "🔴 커밋 안 된 후보 수": len(uncommitted),
        "🔴 대상": keep,
        "🔴 대상 수": len(keep),
        "🔴 git 오류": err[:200] if rc != 0 else "없음",
    }


# ── 도장 ────────────────────────────────────────────────────────────────
def sha(p: Path) -> str:
    """🔴 **951** --- 64자리 전량을 낸다.

    947~950 은 ``[:16]`` 로 잘랐다(티처 #87 m5 · #88 m2 · #90 m5 --- **세 번 지적**).
    🔴 950 은 **바로 이 러너를 고치면서** 이 줄을 안 고쳤다. 축약 sha 는 도장의 값을
    깎는다 --- 견주는 쪽(`doc_check`)은 이미 64자리를 쓰고 있어 **두 자리가 달랐다**.
    """
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def stamp(inputs) -> dict:
    """🔴 **실행 「시작」에서 부른다**(티처 #64 C3).

    노트 901 실물: `out899a_gates.py` 가 `stamp_close(stamp())` 로 **끝에서 둘 다** 불러서
    **116.9초 실행의 시작 == 끝**이었다. 「시작 시각」이 실은 끝 시각이었다.
    코드 sha 도 끝에서 읽히면 **실행에 쓰인 코드가 아니라 끝난 뒤의 코드**를 증언한다.
    """
    head = _git(["rev-parse", "HEAD"])[1].strip()
    return {
        "시각(UTC · 시작)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "🔴 코드 sha256(이게 자다)": {c: (sha(ROOT / c) if (ROOT / c).exists() else "🔴 파일 없음")
                              for c in STAMP_CODE},
        "🔴 입력 산출물 sha256": {i: (sha(ROOT / i) if (ROOT / i).exists() else "🔴 파일 없음")
                          for i in inputs},
        "⚠ git HEAD(시작 시점 · 판정에 쓰지 마라)": head,
    }


def stamp_close(st: dict, t0: float) -> dict:
    st["시각(UTC · 끝)"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    st["초"] = round(time.time() - t0, 1)
    return st


def _git(args, timeout=600):
    r = subprocess.run(["git", "-C", str(ROOT)] + args,
                       capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def _rev(ref: str) -> str:
    """🔴 **어느 커밋을 읽었나** --- 955 R5 는 이 sha 를 산출물에 박으라고 요구한다."""
    rc, out, _ = _git(["rev-parse", ref])
    return out.strip() if rc == 0 else "🔴 모른다(`git rev-parse %s` 가 죽었다)" % ref


# ── ⓪ 관문 ──────────────────────────────────────────────────────────────
def gate_worktree() -> dict:
    """`git status --porcelain` 이 비어야 ⑤′ 를 시작한다. 900 은 정확히 여기서 샜다.

    🔴 **947 수리(티처 #86 C1)**: 이 자리는 946 의 「날 것 전수」 바늘 **밖**이었다
    --- 바늘이 `ls-files`·`ls-tree`·`--name-only`·`--name-status` 넷뿐이라
    `status --porcelain` 은 통째로 분모 밖이었고, 그래서 **⑤′ 의 ⓪ 관문 자신이
    안 세어졌다.** `-z` 와 `core.quotePath=false` 를 붙인다.

    ⚠ `-z` 를 주면 항목이 NUL 로 끊기고 **이름 바꾸기는 `XY 새\\0옛\\0`** 로 나온다
    --- 그래서 아래 목록에는 옛 이름이 **표지 없는 한 줄**로 섞인다. 「줄 수」가
    아니라 「항목 수」로 읽어라.
    """
    rc, out, err = _git(["-c", "core.quotePath=false", "status", "--porcelain", "-z"])
    dirty = [l for l in out.split("\0") if l.strip()]
    return {
        "검사": "⓪ 관문 --- 작업 트리가 비었나(⑤′ 는 커밋된 트리를 검사한다)",
        "git status --porcelain 종료": rc,
        "더러운 경로 수": len(dirty),
        "더러운 경로": dirty or "없음",
        "⚠": ("🔴 안 비었다 --- ⑤′ 는 실패다. 이 목록을 보고서에 그대로 싣는다"
              if dirty else "비었다"),
        "통과": (rc == 0) and (not dirty),
    }


# ── 1 소비자 역참조 ─────────────────────────────────────────────────────
def _needles(paths):
    """🔴 자 셋. 하나만 쓰면 그 자의 사각지대가 그대로 「없다」가 된다."""
    full = sorted(set(paths))
    base = sorted(set(os.path.basename(p) for p in paths))
    mod = sorted(set(p[:-3].replace("/", ".") for p in paths if p.endswith(".py")))
    return {"전체 경로": full, "파일명": base, "모듈 점경로": mod}


def _grep_l(needles, tree=None):
    """`git grep -l` 로 역참조한다. 🔴 못 돌면 빈 목록이 아니라 예외를 들고 온다.

    🔴🔴 **947 수리 (티처 #86 C2)** --- 이 함수는 ⑤′ 의 **건초더미 생산기**다.
    946 은 **바늘 쪽** 음성 대조(107 대 144)만 보고 이겼다고 했고 **출력 쪽은
    아무도 안 봤다.** 실측: `out946_fiveprime.json` 의 역참조 소비자 **154 중 22**
    가 `"data/state/cache_aladin/…\\353\\257\\270…"` 꼴의 **이스케이프된 가짜
    이름**이었고, 반대 방향(참 이름 비-ASCII 소비자)은 **0** 이었다.

    잠복 결함: 아래 `backref`·`gate_roster` 가 `endswith(".py")` 로 가르는데
    이스케이프된 이름은 `.py"` 로 끝난다 --- **한글 `.py` 는 「비-.py」로 조용히
    재분류된다.** 오늘 안 터진 이유는 추적 `.py` 754 중 비-ASCII 이름이 0 이라서다
    (「못 걸린다」가 아니라 **「안 걸렸다」**). 947 이 그 분모를 1 로 만들었다
    (`lab/fixtures/한글이름_고정물.py`).

    이제 `lab.gitcall.grep_files` 정본 판독기를 지난다(`-z` + `core.quotePath=false`).
    """
    if not needles:
        return [], {"rc": None, "왜": "바늘이 0개다 --- 「소비자 없음」이 아니다"}
    # 🔴 `--untracked` 는 rev 와 못 섞인다(`fatal: … no such path in the working tree`).
    #    작업 트리를 볼 때만 붙인다 --- 안 붙이면 아직 커밋 안 된 소비자가 **조용히 사라진다**.
    try:
        files = gc.grep_files(needles, tree=tree, untracked=(tree is None))
    except ks.GitError as e:
        raise RuntimeError(str(e))
    return sorted(files), {"rc": 0, "바늘 수": len(needles),
                           "판독기": "lab.gitcall.grep_files(`-z` + core.quotePath=false)"}


def _grep_l_old(needles, tree=None):
    """🔴 **946 판 그대로** --- 음성 대조 전용(판정에 쓰지 마라).

    「고쳤다」를 말로 하지 않으려면 **고치기 전 판이 같은 자리에서 무엇을 냈는지**를
    같은 실행 안에서 재야 한다. 이 함수는 그 기준본이다.
    """
    if not needles:
        return []
    # 날것허용: 🔴 음성 대조 --- 946 판 `git grep -lF` 를 **일부러 그대로** 돌린다.
    #           여기서 인용을 끄면 「고치기 전에 무엇이 나왔나」를 못 잰다.
    args = ["grep", "-lF"] + ([] if tree else ["--untracked"])
    for n in needles:
        args += ["-e", n]
    if tree:
        args += [tree]
    rc, out, err = _git(args, timeout=900)
    if rc not in (0, 1):
        raise RuntimeError("git grep 종료 %d: %s" % (rc, err[:400]))
    files = []
    for l in out.split("\n"):
        l = l.strip()
        if not l:
            continue
        if tree and l.startswith(tree + ":"):
            l = l[len(tree) + 1:]
        files.append(l)
    return sorted(set(files))


def backref(base, head, tree, ran, exempt) -> dict:
    rc, out, err = _git(["-c", "core.quotepath=false", "diff", "--name-only", "-z",
                         "%s..%s" % (base, head)])
    if rc != 0:
        return {"검사": "1 소비자 역참조", "🔴 예외": "git diff 종료 %d: %s" % (rc, err[:300]),
                "통과": False}
    changed = sorted(p for p in out.split("\0") if p)
    nd = _needles(changed)

    # 🔴 **음성 대조** --- `-c core.quotepath=false` 를 **안 쓴** 바늘로도 한 번 센다.
    #    한글 경로가 `"docs/\353\243…"` 로 이스케이프되어 **한 곳도 안 맞는데 종료 0** 이
    #    나는 길이 실재한다. 그 차를 수로 남기지 않으면 다음 사람이 또 밟는다.
    # 날것허용: 🔴 음성 대조 --- **일부러** quotepath 를 안 끈 바늘을 만든다.
    #           여기서 인용을 끄면 이 대조가 죽는다(946 부터 이어지는 자리).
    rc_q, out_q, _ = _git(["diff", "--name-only", "%s..%s" % (base, head)])
    esc = sorted(p for p in out_q.split("\n") if p.strip())
    esc_hit, _m = _grep_l(sorted(set(esc)), tree)

    per, cons = {}, set()
    for label, ns in nd.items():
        got, meta = _grep_l(ns, tree)
        per[label] = {"바늘 수": len(ns), "소비자 수": len(got),
                      "그중 .py": len([g for g in got if g.endswith(".py")]), **meta}
        cons |= set(got)
    consumers = sorted(cons)
    py = [c for c in consumers if c.endswith(".py")]

    ran = sorted(set(ran))
    ran_in = [r for r in ran if r in cons]
    ran_out = [r for r in ran if r not in cons]
    notrun = [c for c in consumers if c not in set(ran)]
    notrun_py = [c for c in notrun if c.endswith(".py")]
    notrun_other = [c for c in notrun if not c.endswith(".py")]
    no_reason = [c for c in notrun_py if c not in exempt]

    # ── 🔴 조항 62 --- 「안 돌린 172 · .py 30 · 사유 없이 0」은 **차집합 개수**다.
    #    티처 #87 M3: 947 은 `fiveprime902.py` 를 143줄 고치면서 **새 절 셋에만**
    #    `diff62` 를 걸고 **원래 절 1·2 는 안 걸었다**. 여기가 그 둘 중 하나다.
    #    🔴 이 자리는 진짜로 위험하다 --- A(소비자)는 `git grep -z` 가 낸 **참 이름**이고
    #    B(`--ran`)는 **사람이 손으로 친 문자열**이라 두 인코딩이 갈릴 수 있다.
    d62_notrun = gc.diff62_guarded("역참조 소비자(전량)", set(consumers),
                           "돌렸다(--ran)", set(ran),
                           probe=ks.octal_escape, seed_pad=gc.CONTROL_SEED)
    d62_noreason = gc.diff62_guarded("안 돌린 .py", set(notrun_py),
                             "사유가 등록된 것(--exempt)", set(exempt),
                             probe=ks.octal_escape, seed_pad=gc.CONTROL_SEED)
    # 🔴🔴 **949 (티처 #88 ㄷ·ㄹ)** --- 사유에 **자**를 붙인다. 문자열이 아니라 값이다.
    rulers = gc.exempt_rulers({k: v for k, v in exempt.items() if k in set(notrun_py)},
                              consumers=consumers)
    ruled = {k for k, v in rulers.items() if v["🔴 자가 냈나"]}
    d62_ruled = gc.diff62_guarded(
        "안 돌린 .py", set(notrun_py), "🔴 사유가 **자를 통과한** 것", set(ruled),
        probe=ks.octal_escape, seed_pad=gc.CONTROL_SEED)

    return {
        "검사": "1 소비자 역참조 --- 🔴 사람이 고르지 않는다(`docs/루프.md:249-253`)",
        "취합 시작(base)": base, "머리(head)": head,
        "역참조한 트리": tree or "작업 트리",
        # ── 🔴 분모 넷을 나란히 박는다 (조항 60) ──────────────────────
        "🔴 분모 ① 바뀐 경로 수": len(changed),
        "🔴 분모 ② 역참조 소비자 수": len(consumers),
        "🔴 분모 ②-py 역참조 소비자 중 .py": len(py),
        "🔴 분모 ③ 실제로 돌린 수": len(ran_in),
        "🔴 분모 ④ 안 돌린 수": len(notrun),
        "🔴 분모 ④-py 안 돌린 .py 수": len(notrun_py),
        "🔴 분모 ④-사유없음 안 돌린 .py 중 사유 없는 것": len(no_reason),
        "⚠ 분모 ① 과 ② 는 다른 자다": (
            "「돌린 셋 / 바뀐 경로 %d」과 「돌린 셋 / 소비자 %d」는 다른 문장이다. "
            "⑤′ 의 대상은 ② 다(티처 #64 M3 나)." % (len(changed), len(consumers))),
        "🔴 음성 대조(quotepath 를 안 끈 바늘)": {
            "왜": "`git diff --name-only` 는 한글 경로를 이스케이프한다 --- 그 바늘은 한 곳도 "
                  "안 맞는데 **종료 0** 이 난다(조항 59 그 자체)",
            "이스케이프된 경로 수": len([p for p in esc if p.startswith('"')]),
            "이스케이프 바늘로 센 소비자 수": len(esc_hit),
            "정상 바늘(전체 경로)로 센 소비자 수": per["전체 경로"]["소비자 수"],
            "🔴 차(이스케이프 때문에 사라지는 소비자 수)":
                per["전체 경로"]["소비자 수"] - len(esc_hit),
        },
        "바뀐 경로": changed,
        "자별 역참조": per,
        "역참조 소비자(전량)": consumers,
        "돌렸다": ran_in,
        "⚠ 돌렸다고 적었지만 소비자 목록에 없는 것": ran_out or "없음",
        "🔴 안 돌렸다(= 「없다」가 아니다 · 조항 59)": notrun_py,
        "안 돌렸다(비 .py · 실행 대상 아님)": notrun_other,
        "안 돌린 .py 의 사유": {k: v for k, v in exempt.items() if k in set(notrun_py)},
        "🔴 사유 없이 안 돌린 .py": no_reason,
        "🔴 조항 62 ㉠ 안 돌린 것(= 소비자 − 돌린 것)": d62_notrun,
        "🔴 조항 62 ㉡ 사유 없이 안 돌린 .py(= 안 돌린 .py − 사유 등록)": d62_noreason,
        # 🔴 949 --- 사유의 **자**. 「사유가 있다」와 「사유가 참이다」는 둘이다
        "🔴 사유의 자(949 · 티처 #88 ㄷ)": {
            "🔴 자가 붙은 사유 수": len([v for v in rulers.values()
                                if not v["자"].startswith("🔴 자가 없다")]),
            "🔴 자가 없는 사유 수": len([v for v in rulers.values()
                                if v["자"].startswith("🔴 자가 없다")]),
            "🔴 자를 통과한 사유 수": len(ruled),
            "사유별": rulers,
        },
        "🔴 조항 62 ㉡′ 자를 통과한 사유만 B 로(949 · ㉡ 은 구성상 항등이라 자를 바꿨다)":
            d62_ruled,
        "🔴 사유가 **자를 못 넘은** 안 돌린 .py": sorted(set(notrun_py) - ruled),
        # 🔴 티처 #87 M4 --- `diff62` 가 낸 판정을 **바깥에서 감싸지 않는다**
        # 🔴 949 --- 「사유가 있다」가 아니라 **「사유가 참이다」**를 요구한다(티처 #88 ㄷ)
        "통과": ((not no_reason) and d62_notrun["통과"] and d62_noreason["통과"]
                and not (set(notrun_py) - ruled)),
        "⚠ 통과의 뜻": ("역참조 소비자 중 **실행 가능한 `.py` 가 전부 다시 돌았거나 "
                   "사유가 등록됐나**. 「안 돌렸다」가 하나라도 사유 없이 남으면 실패다. "
                   "🔴 **그리고 위 조항 62 대조 둘이 「모른다」가 아니어야 한다**(티처 #87 M3·M4)"),
    }


# ── 1-나/다/라 🔴 날 것 git 호출 (947 · 티처 #86 C1·C2·M2 상설 배선) ──────
def rawgit_gate() -> dict:
    """🔴 **「날 것 호출은 ⑤′ 가 잡는다」를 배선으로 만든다**(티처 #86 M2).

    `docs/루프.md:698` 은 그 문장을 **절 제목으로 단언**하는데, 946 까지 ⑤′ 에는
    그 배선이 **없었다**(946 의 게이트는 자기 사이클 러너 안에 있었고 그 러너는
    동결됐다). 이 절이 그 문장을 참으로 만든다.
    """
    return gc.census()


def rawgit_power() -> dict:
    """🔴 이 게이트가 **실제로 붉어지나** --- 다섯 갈래를 심어서 잰다."""
    return gc.plant_check()


def grepl_regress(base, head, tree=None) -> dict:
    """🔴 **건초더미 대조** --- `_grep_l` 의 새 판독 대 946 판독 (티처 #86 C2).

    조항 62 로 낸다: **반대 방향 · 예시 다섯 · 심은 키**를 같이 싣는다.
    심은 키는 `lab/fixtures/한글이름_고정물.py` --- 947 이 이 검사를 위해
    분모를 0 에서 1 로 올린 그 파일이다.
    """
    rc, out, err = _git(["-c", "core.quotepath=false", "diff", "--name-only", "-z",
                         "%s..%s" % (base, head)])
    if rc != 0:
        return {"검사": "1-라 `_grep_l` 건초더미 대조", "🔴 예외": err[:300], "통과": False}
    needles = sorted({p for p in out.split("\0") if p})
    if not needles:
        return {"검사": "1-라 `_grep_l` 건초더미 대조",
                "🔴 못 쟀다": "바뀐 경로가 0 --- 「같다」가 아니라 **「못 쟀다」**다(조항 59)",
                "통과": False}
    new, _m = _grep_l(needles, tree)
    old = _grep_l_old(needles, tree)
    #: 🔴🔴 **956 R3 --- 자를 바꿨다**(949·953·954·955 네 사이클 미상환 · 티처 #92 가
    #:    「유일하게 참으로 구조적」이라 한 절). 옛 자는 **날 것 판독**과 **새 판독**을
    #:    그대로 견줬는데, 두 판독은 **인코딩이 다르므로** `A−B` 가 **같은 파일의 두 이름**
    #:    으로 가득 찬다 --- 조항 62 는 그럴 때 옳게도 **수를 안 낸다**. 그래서 이 절은
    #:    **구조적으로 붉었다**. 러너 자신이 독스트링에 *「정규화 대조로 바꿔야 한다」* 고
    #:    적어 두고 네 사이클을 안 했다.
    #:    🔴 **고침**: 옛 판독을 `octal_unescape` 로 **같은 자리에 놓고** 견준다.
    #:    그러면 조항 62 가 **수를 낼 수 있고**, 「가짜 이름이 0 인가」라는 실질 주장은
    #:    아래 칸에 **그대로 따로** 남는다(정보를 안 잃는다).
    old_norm = {ks.octal_unescape(x) for x in old}
    rep = gc.diff62_guarded("새 판독(`-z`+quotePath=false)", set(new),
                            "946 판독(날 것) --- 🔴 956 R3: `octal_unescape` 로 정규화했다",
                            old_norm, probe=ks.octal_escape,
                            seed_pad=gc.CONTROL_SEED)
    #: 🔴 옛 자를 **버리지 않는다** --- 정규화 전 대조도 같이 낸다(무엇이 바뀌었는지 보이게).
    rep_raw = gc.diff62_guarded("새 판독", set(new), "946 판독(정규화 안 함)", set(old),
                                probe=ks.octal_escape, seed_pad=gc.CONTROL_SEED)

    #: 🔴 **심은 키 --- `.py` 재분류가 실제로 일어나나**(티처 #86 C2 의 잠복 결함).
    fx = "lab/fixtures/한글이름_고정물.py"
    fx_esc = ks.octal_escape(fx)
    return {
        "검사": "1-라 🔴 `_grep_l` 건초더미 대조 --- 새 판독 대 946 판독(조항 62)",
        "🔴 왜": ("946 은 **바늘 쪽** 음성 대조만 보고 이겼다고 했다. **출력 쪽은 "
               "아무도 안 봤다** --- 소비자 154 중 22 가 이스케이프된 가짜 이름이었다"),
        "🔴 바늘 수": len(needles),
        "🔴 새 판독이 낸 소비자 수": len(new),
        "🔴 946 판독이 낸 소비자 수": len(old),
        "🔴 946 판독 중 `\"` 로 시작하는 가짜 이름": len([x for x in old if x.startswith('"')]),
        "🔴 새 판독 중 `\"` 로 시작하는 가짜 이름": len([x for x in new if x.startswith('"')]),
        "🔴 새 판독 중 비-ASCII 참 이름": len([x for x in new if not x.isascii()]),
        "🔴🔴 956 R3 --- 자를 바꿨다(정규화 대조)": {
            "무엇": ("옛 자는 인코딩이 다른 두 판독을 그대로 견줬다 --- `A−B` 가 **같은 파일의 "
                   "두 이름**으로 가득 차서 조항 62 가 옳게도 수를 안 냈다. **구조적으로 붉었다**"),
            "고침": "옛 판독을 `lab.keyspace.octal_unescape` 로 정규화해 같은 자리에 놓는다",
            "정규화 전 946 판독 수": len(old),
            "정규화 후 946 판독 수": len(old_norm),
            "🔴 정규화가 실제로 바꾼 이름 수": len(set(old) - old_norm),
            "미상환 사이클": "949 · 953 · 954 · 955 --- 956 이 갚는다",
        },
        "조항 62 대조(🔴 정규화 대조 --- 956 R3)": rep,
        "조항 62 대조(정규화 안 함 --- 옛 자 · 비교용)": rep_raw,
        "🔴 심은 키 --- `endswith('.py')` 재분류": {
            "심은 것": fx, "두 번째 인코딩": fx_esc,
            "새 판독은 `.py` 로 보나": fx.endswith(".py"),
            "🔴 946 판독은 `.py` 로 보나": fx_esc.endswith(".py"),
            "🔴 발화했나": fx.endswith(".py") and not fx_esc.endswith(".py"),
            "⚠": ("이 심은 키가 없으면 이 검사는 **영원히 초록**이다 --- 946 당시 "
                  "추적 `.py` 754 중 비-ASCII 이름이 **0** 이었다"),
        },
        "🔴 새 판독 출력에 가짜 이름이 0 인가(이 절의 실질 주장)":
            len([x for x in new if x.startswith('"')]) == 0,
        "🔴 조항 62 대조가 수를 냈나": rep["통과"],
        # 🔴 949 --- `rep["통과"]` 를 **읽는다**(948 은 한 번도 안 읽었다 · 티처 #88 C3)
        "통과": (len([x for x in new if x.startswith('"')]) == 0) and rep["통과"],
        "⚠ 통과의 뜻": ("🔴 **둘의 AND** --- ① 새 판독 출력에 가짜 이름이 0 이고 "
                  "② 조항 62 대조가 「모른다」가 아니어야 한다. "
                  "🔴🔴 **956 R3 로 ② 의 자를 바꿨다** --- 옛 자는 인코딩이 다른 두 판독을 "
                  "그대로 견줘서 `A−B` 가 **같은 파일의 두 이름**으로 가득 찼고, 조항 62 는 "
                  "그럴 때 **옳게도** 수를 안 냈다. 그래서 이 절은 **구조적으로 붉었다**"
                  "(949·953·954·955 네 사이클). 이제 옛 판독을 `octal_unescape` 로 "
                  "**같은 자리에 놓고** 견준다. 🔴 **정규화 안 한 대조도 같이 싣는다** --- "
                  "자를 바꿔서 초록이 된 것이지 자료가 바뀐 것이 아니라는 사실을 "
                  "다음 사람이 보게 하려고"),
    }


# ── 2 게이트 ────────────────────────────────────────────────────────────
def gate_roster(tree) -> dict:
    """🔴 **게이트 명부를 손으로 나열하지 마라**(`docs/루프.md:254-258`).

    「허가 목록이 곧 검사 목록」병을 피하려면 명부가 **기계로** 나와야 한다.
    자: `"통과"` 를 **키로 내는** `.py` 전량. 새 게이트를 넣는 사람이 이 줄을 몰라도 잡힌다.
    """
    got, meta = _grep_l(['"통과":', "'통과':", '"통과" :'], tree)
    return sorted(p for p in got if p.endswith(".py")), meta


#: 🔴 **950 --- 문서에 도장 말고 대조를 박는다**(티처 #89 M1 · 3순위).
#: 🔴 **951** --- 950 은 이 상수를 하드코딩했다. 매 사이클 자기 도장 파일을 가리켜야
#: 하므로 CLI 로 받는다(기본은 이번 사이클 것).
DOCSTAMP = "runners/out951_docstamp.json"


def doc_check(docstamp: str = None, tree: str = "HEAD") -> dict:
    """🔴 **대조** --- 찍힌 문서의 **입력 sha 를 지금 다시 계산해 견준다**.

    `CHECK_CRITERIA` 셋을 그대로 채운다: ① `runners/out950_docstamp.json` 을 **읽고**
    ② 그 안에 **기록된 sha 를 꺼내어** ③ **지금 파일에서 다시 계산한 sha** 와 견준다.

    🔴 **이것이 M1 의 재발을 막는 자다** --- 949 는 `exp949_harm.json` 이 107줄 바뀌고도
    `docs/판정/949_수.md` 를 다시 안 찍었는데 **아무것도 안 붉어졌다.**
    ⚠ **한계(조항 61)**: 낡음만 잡는다. **문서의 수가 옳은지는 안 본다.**
    """
    ds = docstamp or DOCSTAMP
    known, ls_err = tree_paths(tree)
    st_state, st_txt = tree_text(ds, tree, known)
    if st_state != "읽었다":
        return {"검사": "7 문서 대조", "통과": False,
                "🔴 읽은 트리(955 R5)": {"기준": "커밋된 트리", "트리": tree,
                                  "커밋 sha": _rev(tree)},
                "🔴": "모른다 --- `%s` 를 **%s**(「대조가 초록」이 아니다 · 조항 59)" % (ds, st_state)}
    st = json.loads(st_txt)
    rows, bad, unknown, nocommit = {}, [], [], []
    want = dict(st.get("🔴 입력별 sha256(대조의 기록 쪽)", {}))
    want.update(st.get("🔴 문서 sha256", {}))
    want.update(st.get("🔴 생산기 sha256", {}))
    for rel, rec in sorted(want.items()):
        state, blob = tree_blob(rel, tree, known)
        if state == "커밋 안 됨":
            # 🔴 955 R5 --- 「커밋 안 됨」은 「없다」가 아니다(조항 59)
            rows[rel] = {"🔴 커밋 안 됨": "작업 트리엔 있는데 `%s` 에 없다 --- 견줄 수 없다" % tree}
            nocommit.append(rel)
            continue
        if state != "읽었다":
            rows[rel] = {"🔴": "모른다 --- 파일이 없다(「같다」가 아니다)"}
            unknown.append(rel)
            continue
        now = hashlib.sha256(blob).hexdigest()
        same = (now == rec)
        rows[rel] = {"기록된 sha256": rec, "🔴 커밋된 트리에서 다시 계산한 sha256": now,
                     "같은가": same}
        if not same:
            bad.append(rel)
    return {
        "검사": "7 🔴 문서 대조 --- 찍힌 문서의 **입력이 그 뒤로 바뀌었나**(티처 #89 M1)",
        # 🔴 955 R5 (티처 #93 M5) --- 954 까지 이 절은 **작업 트리**를 해싱했다.
        #    `docs/루프.md:148` 은 ⑤′ 를 **커밋된 트리**에서 하라고 적는다.
        "🔴 읽은 트리(955 R5)": {
            "기준": "🔴 **커밋된 트리**(`git cat-file blob <tree>:<경로>` 를 해싱한다)",
            "트리": tree, "커밋 sha": _rev(tree),
            "🔴 `git ls-tree` 오류": ls_err,
            "⚠ 954 까지": "작업 트리를 해싱했다 --- 커밋 안 된 편집이 이 절을 붉히거나 숨겼다",
        },
        "자": gc.CHECK_CRITERIA,
        "도장 파일": ds,
        "🔴 견준 수(분모)": len(want),
        "🔴 다른 것": bad or "없음",
        "🔴 모르는 것": unknown or "없음",
        "🔴 커밋 안 된 것(= 「없다」가 아니다 · 조항 59)": nocommit or "없음",
        "🔴 커밋 안 된 것 수": len(nocommit),
        "파일별": rows,
        "통과": (not bad) and (not unknown) and (not nocommit) and len(want) > 0,
        "🔴 통과의 뜻": ("찍힌 문서의 입력·생산기·문서 자신이 **그 뒤로 한 바이트도 안 바뀌었다**. "
                   "🔴 하나라도 바뀌었으면 **문서를 다시 찍어야 한다** --- 949 가 안 한 그것이다"),
        "⚠ 한계(조항 61)": "낡음만 잡는다. **문서의 수가 옳은지는 안 본다**",
    }


def run_gates(do_run, tree, consumers, ran_hand=(), exempt=None) -> dict:
    """🔴🔴 **948 수리 (티처 #87 M2)** --- `exempt` 를 **받는다**.

    947 은 이 절이 「`--gate-exempt` CLI 가 없어서 **구조적으로 영원히 붉다**」고
    적었다. **거짓이었다** --- 사유 딕셔너리는 같은 실행 안에 **이미 만들어져 있었고**
    이 함수가 그것을 **파라미터로 안 받았을 뿐**이다. 실측(티처가 두 절을 교차해 셌다):
    `2 게이트` 의 「사유 없이 안 돌린 **9**」가 **9/9 전부 절 1 에 이미 사유가 달려 있다**.
    티처 #80 의 *"「배선을 못 넣었다」가 거짓이었다 --- 길은 3줄"* 이 같은 러너에서 재발했다.

    🔴 **그리고 그 길을 열면 구멍이 하나 생긴다**: 사유를 넘겨 게이트를 끌 수 있다.
    그래서 **CLI 사유로 닫힌 수를 따로 센다**(`🔴 그중 CLI 사유(`--exempt`)로 닫힌 수`).
    안 세면 「사유 없이 안 돌린 것 0」이 무슨 뜻인지 다음 세션이 못 읽는다.
    """
    exempt = dict(exempt or {})
    roster, meta = gate_roster(tree)
    # 🔴 무엇을 왜 안 돌리는지 **여기 적는다**. 안 적으면 「없다」가 된다.
    #    🔴 사유 하나는 **기계로 나온다**: 이번 취합의 역참조에 안 걸린 게이트는
    #    ⑤′ 의 대상이 아니다. 사람이 손으로 봐주는 사유가 아니라 1 절의 결과다.
    # 🔴 949 --- 기계 사유에도 **자 표지**를 붙인다(`[자:소비자아님]`). 그래야
    #    아래 ㉡′ 가 「사유가 있다」와 「사유가 참이다」를 가를 수 있다.
    skip = {p: "[자:소비자아님] 이번 취합의 소비자가 아니다(1 절 역참조에 안 걸렸다)"
            for p in roster if p not in set(consumers)}
    skip.update({
        "runners/out899a_gates.py": (
            "다른 팔 소유 · 돌리면 `runners/out899a_gates.json` 을 덮어써서 동시에 도는 팔의 "
            "산출물을 깨뜨린다. 대신 **3 절이 그 산출물을 읽어 판정 키를 감사한다**"),
    })
    # 🔴 CLI 사유가 **더 구체적**이므로 기계 사유를 덮는다(어느 쪽인지 아래에서 센다).
    from_cli = sorted(p for p in roster if p in exempt)
    skip.update({p: exempt[p] for p in from_cli})
    # 손으로 다시 돌린 게이트(`--ran`)도 「돌렸다」다 --- 안 세면 「안 돌렸다」가 부풀고,
    # 부푼 분모도 분모 바꿔치기다(조항 60).
    ran = [p for p in ran_hand if p in set(roster)]
    results, exc = {}, {}
    if do_run:
        t = time.time()
        try:
            r = subprocess.run([sys.executable, "-m", "ingest.audit", "--json"],
                               cwd=str(ROOT), capture_output=True, text=True, timeout=1800)
            if r.returncode != 0:
                exc["ingest/audit.py"] = "종료 %d · %s" % (r.returncode, r.stderr[-400:])
            else:
                d = json.loads(r.stdout)
                # 🔴 손 나열 금지 --- `통과` 키를 가진 절을 **전부 자동 수집**한다
                results = {k: v["통과"] for k, v in d.items()
                           if isinstance(v, dict) and "통과" in v}
                ran.append("ingest/audit.py")
        except Exception as e:                                    # noqa: BLE001
            exc["ingest/audit.py"] = "%s: %s" % (type(e).__name__, e)
        results["_초"] = round(time.time() - t, 1)
    ran = sorted(set(ran))
    notrun = [p for p in roster if p not in set(ran)]
    no_reason = [p for p in notrun if p not in skip]
    failed = [k for k, v in results.items() if v is False]
    # ── 🔴 조항 62 --- 「안 돌린 40 · 사유 없이 9」는 **차집합 개수**다 (티처 #87 M3)
    #    947 은 이 러너를 143줄 고치면서 **새 절 셋에만** `diff62` 를 걸고
    #    원래 절 1·2 는 안 걸었다. 여기가 그 둘 중 하나다.
    d62_notrun = gc.diff62_guarded("게이트 명부(roster)", set(roster),
                           "돌렸다(ran)", set(ran),
                           probe=ks.octal_escape, seed_pad=gc.CONTROL_SEED)
    d62_noreason = gc.diff62_guarded("안 돌린 게이트", set(notrun),
                             "사유가 등록된 것(skip)", set(skip),
                             probe=ks.octal_escape, seed_pad=gc.CONTROL_SEED)
    # 🔴🔴 **949 (티처 #88 ㄹ)** --- 위 ㉡ 은 `skip = roster − ran` 이라 `notrun` 과
    #    **구성상 항등**이고 **원리상 0/0 말고 다른 값을 못 낸다**. 자를 바꾼다:
    #    B 를 「사유가 **자를 통과한** 것」으로. 그러면 이 대조가 처음으로 값을 낸다.
    rulers = gc.exempt_rulers({k: v for k, v in skip.items() if k in set(notrun)},
                              consumers=consumers)
    ruled = {k for k, v in rulers.items() if v["🔴 자가 냈나"]}
    d62_ruled = gc.diff62_guarded(
        "안 돌린 게이트", set(notrun), "🔴 사유가 **자를 통과한** 것", set(ruled),
        probe=ks.octal_escape, seed_pad=gc.CONTROL_SEED)
    return {
        "검사": "2 게이트 --- 🔴 명부를 기계로 뽑는다(손 나열 금지)",
        "명부를 어떻게 뽑았나": '`git grep -lF -e \'"통과":\'` 로 **`통과` 를 키로 내는 `.py` 전량**',
        "🔴 게이트 생산자 수(분모)": len(roster),
        "🔴 그중 이번 취합의 소비자인 것": len([p for p in roster if p in set(consumers)]),
        "게이트 생산자": roster,
        "🔴 돌린 수": len(ran), "돌렸다": ran,
        "🔴 안 돌린 수": len(notrun),
        "🔴 안 돌렸다(= 「없다」가 아니다)": notrun,
        "안 돌린 사유": {k: v for k, v in skip.items() if k in set(notrun)},
        "🔴 사유 없이 안 돌린 것": no_reason,
        # 🔴 948 --- 사유의 **출처**를 센다. 안 세면 「0」이 무슨 뜻인지 못 읽는다
        "🔴 사유의 출처(948 신설 · 티처 #87 M2 가 연 길의 구멍을 센다)": {
            "🔴 CLI 사유(`--exempt`)로 닫힌 게이트 수": len([p for p in notrun if p in set(from_cli)]),
            "그 목록": [p for p in notrun if p in set(from_cli)],
            "기계 사유(1 절 역참조에 안 걸렸다)로 닫힌 수":
                len([p for p in notrun if p in skip and p not in set(from_cli)]),
            "⚠": ("🔴 CLI 사유는 **사람이 넘긴 것**이다 --- 이 수가 크면 이 절은 "
                  "「검사」가 아니라 「장식」에 가까워진다. **그 판단을 하려고 센다**"),
        },
        "🔴 조항 62 ㉠ 안 돌린 것(= 명부 − 돌린 것)": d62_notrun,
        "🔴 조항 62 ㉡ 사유 없이 안 돌린 것(= 안 돌린 것 − 사유 등록)": d62_noreason,
        "⚠ 위 ㉡ 은 구성상 항등이다(949 · 티처 #88 C4)":
            "`skip = roster − ran` 이고 `notrun = roster − ran` 이라 **원리상 0/0 말고 "
            "다른 값을 못 낸다**. 아래 ㉡′ 가 그것을 갈음한다",
        "🔴 사유의 자(949 · 티처 #88 ㄷ)": {
            "🔴 자가 붙은 사유 수": len([v for v in rulers.values()
                                if not v["자"].startswith("🔴 자가 없다")]),
            "🔴 자가 없는 사유 수": len([v for v in rulers.values()
                                if v["자"].startswith("🔴 자가 없다")]),
            "🔴 자를 통과한 사유 수": len(ruled),
            "사유별": rulers,
        },
        "🔴 조항 62 ㉡ 자를 통과한 사유만 B 로(949)": d62_ruled,
        "돌린 게이트의 절별 판정": results or "안 돌렸다(--gates 를 안 줬다)",
        "🔴 실패한 절": failed or "없음",
        "🔴 예외": exc or "없음",
        # 🔴 티처 #87 M4 --- `diff62` 가 「모른다」·`통과 False` 를 낸 절을
        #    **바깥에서 `통과 True` 로 감싸지 않는다**. 그래서 AND 로 엮는다.
        "🔴 사유가 **자를 못 넘은** 안 돌린 게이트": sorted(set(notrun) - ruled),
        # 🔴 949 --- 「사유가 있다」가 아니라 **「사유가 참이다」**를 요구한다(티처 #88 ㄷ·C4)
        "통과": (bool(do_run) and (not failed) and (not exc) and (not no_reason)
                and d62_notrun["통과"] and d62_noreason["통과"]
                and not (set(notrun) - ruled)),
        "🔴 통과의 뜻": ("게이트를 돌렸고 · 실패한 절이 없고 · 예외가 없고 · 사유 없이 안 "
                   "돌린 것이 없고 · 🔴 **위 조항 62 대조 둘이 「모른다」가 아니어야** 통과"),
    }


# ── 3 판정 키 규약 ──────────────────────────────────────────────────────
def keyaudit(extra, targets=None, tree="HEAD") -> dict:
    """🔴 **`통과` 키가 없는 절을 「모른다」로 세어 드러낸다**(`docs/루프.md:256-258`).

    대상 파일은 **남의 소유라 고치지 않는다.** 고치는 대신 **읽는 쪽에서** 센다 ---
    900 의 첫 훑기가 동적 게이트 다섯에서 전부 `None` 을 받고도 초록이었던 길이 그것이다.
    🔴 `None` 은 「통과」가 아니라 **「모른다」**다(조항 59).

    🔴 **955 R5** --- 파일을 **커밋된 트리**에서 읽는다(`git cat-file blob <tree>:<경로>`).
    작업 트리에만 있는 파일은 「없다」가 아니라 **「커밋 안 됨」**으로 따로 센다(조항 59).
    🔴 **955 R4** --- `out*_fiveprime.json`(자기 산출물)은 **이름으로 뺀다.** `--keyaudit`
    으로 손수 넣어도 뺀다 --- 자기 채점 순환은 인자로도 열지 않는다.
    """
    tg = targets or {}
    per, tot, has, unk = {}, 0, 0, 0
    nocommit, missing, unread, selfskip = [], [], [], []
    known, ls_err = tree_paths(tree)
    for rel in list(dict.fromkeys(KEYAUDIT_MUST + list(tg.get("🔴 대상") or []) + list(extra))):
        if is_self_out(rel):
            # 🔴 955 R4 --- 자기 산출물은 대상이 아니다. **뺐다는 사실을 남긴다.**
            selfskip.append(rel)
            per[rel] = {"🔴 뺐다(955 R4)": "이 러너 자신의 산출물(`out*_fiveprime.json`)이다 "
                                       "--- 자기 채점 순환(티처 #93 C3)"}
            continue
        st, txt = tree_text(rel, tree, known)
        if st == "커밋 안 됨":
            per[rel] = {"🔴 커밋 안 됨": "작업 트리엔 있는데 `%s` 에 없다 --- 「없다」가 "
                                   "아니라 **「못 봤다」**다(조항 59)" % tree}
            nocommit.append(rel)
            continue
        if st == "없다":
            per[rel] = {"🔴": "그 파일이 없다(「절이 없다」가 아니다)"}
            missing.append(rel)
            continue
        try:
            d = json.loads(txt)
        except Exception as e:                                    # noqa: BLE001
            per[rel] = {"🔴": "못 읽었다: %s" % e}
            unread.append(rel)
            continue
        # 🔴 957 --- 최상위가 dict 가 아닌 산출물(목록 등)에서 죽지 않는다.
        #    「죽었다」와 「절이 없다」와 「통과」는 셋이다(조항 59).
        if not isinstance(d, dict):
            per[rel] = {"🔴": "최상위가 dict 가 아니다(%s) --- 절 규약 밖" % type(d).__name__,
                        "통과": False}
            continue
        # 🔴 **도장은 절이 아니다.** `코드 sha256`·`시각` 같은 도장 dict 를 절로 세면
        #    분모가 부풀고, 그러면 「모른다 10/10」이 티처가 손으로 센 **9** 와 어긋난다.
        #    분모를 부풀리는 것도 분모 바꿔치기다(조항 60).
        stampish = sorted(k for k, v in d.items()
                          if isinstance(v, dict) and any(w in k for w in ("sha256", "시각")))
        secs = {k: v for k, v in d.items()
                if isinstance(v, dict) and k not in set(stampish)}
        ok = sorted(k for k, v in secs.items() if "통과" in v)
        no = sorted(k for k in secs if k not in set(ok))
        # 절이 아닌 최상위 불리언(판정처럼 보이는 것)도 드러낸다
        loose = sorted(k for k, v in d.items() if isinstance(v, bool))
        per[rel] = {
            "🔴 절 수(분모)": len(secs),
            "`통과` 키가 있는 절": len(ok), "그 목록": ok or "없음",
            "🔴 `통과` 키가 없는 절 = 모른다": len(no), "모른다 목록": no,
            "⚠ 절 밖의 최상위 판정 불리언(규약 밖)": loose or "없음",
            "⚠ 절로 세지 않은 도장 dict": stampish or "없음",
            "통과": (len(no) == 0),
        }
        tot += len(secs)
        has += len(ok)
        unk += len(no)
    return {
        "검사": "3 판정 키 규약 --- `통과` 하나로 규약화됐나",
        "🔴 953 --- 대상이 바뀌었다": (
            "옛 대상은 `out899a_gates.json` **하나 하드코딩**이었고 그건 **고칠 수 없는 남의 파일**이라 "
            "**초록이 도달 불가능**했다(22/22 붉음 = 정의의 기록 · 티처 #90·#91). "
            "이제 대상은 **이 사이클이 찍은 산출물**이다 --- 자는 자기 산출물에 걸릴 때만 자다"),
        "🔴 대상 고르기": tg or "🔴 안 넘어왔다(옛 방식)",
        "🔴 왜 읽는 쪽에서 하나": "남의 산출물을 소비할 땐 고치지 않고 **세어 드러낸다**(그 규율은 그대로다)",
        # 🔴 955 R5 --- 어느 기준으로 읽었는지 **산출물에 박는다**
        "🔴 읽은 트리(955 R5)": {
            "기준": "커밋된 트리(`git cat-file blob <tree>:<경로>`)",
            "트리": tree,
            "커밋 sha": _rev(tree),
            "그 트리의 경로 수(분모)": len(known),
            "🔴 `git ls-tree` 오류": ls_err,
        },
        # 🔴 955 R4 --- 자기 배제를 **여기서도** 센다(대상 고르기 밖으로 들어온 길을 막는다)
        "🔴 자기 산출물이라 뺀 것(955 R4)": selfskip or "없음",
        "🔴 파일 수(분모)": len(per),
        "🔴 커밋 안 된 파일(= 「없다」가 아니다 · 조항 59)": nocommit or "없음",
        "🔴 커밋 안 된 파일 수": len(nocommit),
        "🔴 커밋된 트리에도 작업 트리에도 없는 파일": missing or "없음",
        "🔴 못 읽은 파일(JSON 이 아니다)": unread or "없음",
        "🔴 절 수 합(분모)": tot,
        "`통과` 키가 있는 절 합": has,
        "🔴 모른다(=`통과` 키 없음) 합": unk,
        "파일별": per,
        "통과": (tot > 0 and unk == 0 and not nocommit and not missing and not unread),
        "⚠ 통과의 뜻": "🔴 `통과 == False` 는 「게이트가 실패했다」가 아니라 **「판정을 못 읽는다」**다",
        "⚠ 대상이 0 이면": ("`통과` 는 **False** 다. 「검사할 게 없다」가 아니라 "
                       "**「이 사이클이 산출물을 안 찍었다」**로 읽는다(조항 59)"),
    }


# ── 4 도장 확인 ─────────────────────────────────────────────────────────
def stamp_audit(tree="HEAD") -> dict:
    """🔴 `git HEAD` 스탬프는 판정에 쓰지 않는다(v3.2 가 폐기). 도장 넷을 본다.

    🔴 **955 R5** --- 훑는 목록도 읽는 내용도 **커밋된 트리**에서 온다(`git ls-tree -r` +
    `git cat-file blob`). 작업 트리에만 있는 산출물은 「없다」가 아니라 **「커밋 안 됨」**
    으로 따로 센다(조항 59).
    🔴 **955 R4** --- `out*_fiveprime.json`(자기 산출물)은 **이름으로 뺀다**(티처 #93 C3).
    """
    want = ("시각", "sha256")
    known, ls_err = tree_paths(tree)
    in_tree = sorted(p for p in known
                     if p.startswith("runners/out") and p.endswith(".json"))
    on_disk = sorted((q.relative_to(ROOT).as_posix())
                     for q in (ROOT / "runners").glob("out*.json"))
    selfskip = sorted(p for p in set(in_tree) | set(on_disk) if is_self_out(p))
    scan = [p for p in in_tree if not is_self_out(p)]
    nocommit = sorted(p for p in on_disk
                      if p not in known and not is_self_out(p))
    rows, nost, bad = {}, [], []
    for rel in scan:
        st, txt = tree_blob(rel, tree, known)
        try:
            d = json.loads(txt.decode("utf-8", "surrogateescape"))
        except Exception as e:                                    # noqa: BLE001
            rows[rel] = {"🔴": "못 읽었다: %s" % type(e).__name__}
            bad.append(rel)
            continue
        if not isinstance(d, dict):
            rows[rel] = {"⚠": "최상위가 dict 가 아니다"}
            nost.append(rel)
            continue
        keys = [k for k in d if any(w in k for w in want)]
        t_open = [k for k in d if "시각" in k and "시작" in k]
        t_shut = [k for k in d if "시각" in k and "끝" in k]
        if not keys:
            nost.append(rel)
            continue
        rows[rel] = {"도장 키": keys,
                     "시작 시각": (d[t_open[0]] if t_open else "🔴 없다"),
                     "끝 시각": (d[t_shut[0]] if t_shut else "🔴 없다"),
                     "초": d.get("초", "모른다"),
                     "시작<끝": ((d[t_open[0]] < d[t_shut[0]]) if (t_open and t_shut) else None)}
    # 🔴 **초 단위 도장에서 「시작 == 끝」은 두 가지다**: ① 901 의 그 병(긴 실행인데 끝에서
    #    둘 다 찍었다) ② 진짜로 1초 안에 끝난 실행. 둘을 갈라 센다 --- 안 가르면 이 절이
    #    영구 False 게이트가 되고, 그러면 아무도 안 본다.
    def _long(v):
        s = v.get("초")
        return isinstance(s, (int, float)) and s > 1.5
    same = [k for k, v in rows.items() if v.get("시작<끝") is False and _long(v)]
    short = [k for k, v in rows.items() if v.get("시작<끝") is False and not _long(v)]
    return {
        "검사": "4 도장 확인 --- ① 시작 ② 끝 ③ 입력 sha ④ 코드 sha",
        # 🔴 955 R5 --- 어느 트리를 훑었는지 박는다
        "🔴 훑은 트리(955 R5)": {
            "기준": "커밋된 트리(`git ls-tree -r <tree>` + `git cat-file blob`)",
            "트리": tree, "커밋 sha": _rev(tree),
            "🔴 `git ls-tree` 오류": ls_err,
        },
        "🔴 훑은 산출물 수(분모)": len(scan),
        "⚠ 그 트리의 `runners/out*.json` 전량": len(in_tree),
        # 🔴 955 R4 --- 자기 산출물을 뺐다는 사실을 **수와 목록으로** 남긴다
        "🔴 뺀 것(자기 산출물 · 955 R4)": selfskip or "없음",
        "🔴 뺀 수": len(selfskip),
        "🔴 커밋 안 된 산출물(= 「없다」가 아니다 · 조항 59)": nocommit or "없음",
        "🔴 커밋 안 된 산출물 수": len(nocommit),
        "도장이 있는 산출물 수": len(rows) - len(bad),
        "🔴 도장이 하나도 없는 산출물 수": len(nost),
        "🔴 도장이 하나도 없는 산출물": nost,
        "🔴 못 읽은 산출물": bad or "없음",
        "🔴 시작 == 끝 인데 초 > 1.5 인 산출물(901 의 그 병)": same or "없음",
        "⚠ 시작 == 끝 이지만 1.5초 안에 끝난 산출물(병 아님)": short or "없음",
        "도장별": rows,
        "통과": (not same) and (not bad),
        "⚠": ("도장 없음을 「실패」로 세지 않는다 --- 옛 산출물이 많다. **수를 드러내는 것**이 이 절의 일이다"),
    }


# ── 5 quote901 기존 동작 무변 ───────────────────────────────────────────
#: 🔴 이슈 #140 M4 --- `--selftest` 를 JSON 산출물로 내되 **기존 동작을 하나도 바꾸지 마라**.
#: 「안 바꿨다」를 말로 하면 그게 바로 이 사이클이 걸린 병이다. **바꾸기 전 동작을 기록해
#: 두고 대조한다** --- 기준본은 `git show <rev>:runners/quote901.py`.
_SCRUB = re.compile(r"(/[^\s'\"]*/)?(tmp|T/)[A-Za-z0-9_]{6,}")


#: 🔴 `--selftest` 는 **자기 파일 위치 기준**으로 산출물 경로를 정한다. 기준본은 임시
#: 디렉터리에서 돌므로 그 한 줄이 반드시 다르다 --- 코드가 같아도 다르다.
#: ⚠ 이 규칙은 수리 B 가 보고에 *"「산출물: …」 한 줄을 떼고 견줬다"* 라고 적었지만
#: **실제로는 안 걸려 있었다**(주 세션이 5절·5-나가 False 로 뒤집힌 것을 보고 잡았다).
#: 🔴 **「고쳤다」와 「고쳐졌다」는 둘이다** --- 그래서 아래 `_OUTLINE` 이 실물이고,
#: 음성 대조(안 바꾼 사본이 통과하나)가 이 규칙의 시험이다.
_OUTLINE = re.compile(r"^산출물: .*$", re.M)


def _scrub(s: str) -> str:
    """🔴 실행마다/자리마다 달라지는 것만 지운다. **그 밖은 한 글자도 안 건드린다.**

    지우는 것 둘: ① 임시 디렉터리 이름 ② `--selftest` 의 「산출물:」 경로 한 줄.
    """
    return _OUTLINE.sub("산출물: <경로>", _SCRUB.sub("<TMP>", s))


def quote_regress(ref, now=None) -> dict:
    """🔴 `now` 로 **딴 파일을 심어 이 절이 실제로 붉어지는지** 확인한다(검정력 측정).

    티처 #64 m4 --- *"자기시험 3점의 검정력이 사실상 0"* 이었다(원점을 1km 옮겨도 통과).
    **시험을 세울 때 「무엇을 못 가르는지」를 먼저 재라.** 그래서 심는 길을 열어 둔다.
    """
    import tempfile
    rc, src, err = _git(["show", "%s:runners/quote901.py" % ref])
    if rc != 0:
        return {"검사": "5 quote901 무변", "🔴 예외": "기준본을 못 꺼냈다: %s" % err[:200],
                "통과": False}
    with tempfile.TemporaryDirectory() as td:
        old = Path(td) / "quote_old.py"
        old.write_text(src, encoding="utf-8")
        j = Path(td) / "t.json"
        j.write_text(json.dumps({"수": 633, "널": None, "묶음": {"가/나": 2}},
                                ensure_ascii=False), encoding="utf-8")
        cases = [
            ("값", [str(j), "수"]),
            ("--cite", ["--cite", str(j), "수"]),
            ("--check 맞음", ["--check", "633", str(j), "수"]),
            ("🔴 --check 어긋남", ["--check", "629", str(j), "수"]),
            ("🔴 파일 없다", [str(Path(td) / "없다.json"), "수"]),
            ("🔴 JSON 아니다", [str(old), "수"]),
            ("🔴 키 없다", [str(j), "없는키"]),
            ("🔴 null", [str(j), "널"]),
            ("🔴 키 경로 없음", [str(j)]),
            ("--list", ["--list", str(j)]),
            ("🔴 구분자 품은 키", [str(j), "묶음/가/나"]),
            ("--help", ["--help"]),
            ("--selftest", ["--selftest"]),
        ]
        # 🔴 **작업본을 저장소에서 그대로 돌리면 안 된다**(티처 #65 M16).
        #    `--selftest` 는 **자기 파일 위치 기준**으로 `runners/out902b_selftest.json` 을
        #    **쓴다**(도장에 시각이 들어가 내용이 매번 바뀐다). 그래서 ⑤′ 를 돌리는 것만으로
        #    작업 트리가 더러워지고 --- 🔴 **⓪ 관문(트리가 비어야 한다)을 5절이 깨뜨렸다.**
        #    실측: 커밋된 ⓪ 의 더러운 7 안에 `out902b_selftest.json` 이 있었다.
        #    그래서 **작업본도 사본을 임시 디렉터리에 두고 돌린다** --- 기준본과 같은 조건이 되고
        #    저장소는 안 더러워진다. ⚠ 그 대가로 산출물 경로가 둘 다 임시라 `_scrub` 이
        #    양쪽을 `<경로>` 로 뭉갠다(그 사각지대는 아래 `⚠ 못 재는 것` 에 적었다).
        if now:
            new = Path(now)
            _new_tmp = None
        else:
            _new_tmp = tempfile.mkdtemp(prefix="fp902new_")
            new = Path(_new_tmp) / "quote901.py"
            new.write_text((ROOT / "runners/quote901.py").read_text(), encoding="utf-8")
        diff, per = [], {}
        for name, argv in cases:
            a = subprocess.run([sys.executable, str(old)] + argv,
                               cwd=str(ROOT), capture_output=True, text=True, timeout=300)
            b = subprocess.run([sys.executable, str(new)] + argv,
                               cwd=str(ROOT), capture_output=True, text=True, timeout=300)
            # 🔴 임시 디렉터리 이름은 **매 실행 다르다**. 그걸 안 지우면 「달라졌다」가
            #    영원히 참이 되어 이 절이 아무것도 못 잰다. 무엇을 지웠는지 여기 적는다.
            ao, bo = _scrub(a.stdout), _scrub(b.stdout)
            ae, be = _scrub(a.stderr), _scrub(b.stderr)
            note = ""
            if name == "--selftest":
                # 🔴 **한쪽만 떼면 안 된다.** 초판은 `bo`(작업본)에서만 「산출물:」 줄을
                #    떼었는데, 기준본이 이미 새 판이면 **양쪽 다 그 줄을 찍으므로**
                #    비대칭이 생겨 「달라졌다」가 영원히 참이 된다(주 세션이 실측으로 잡았다).
                #    이제 `_scrub` 이 **양쪽 모두** `산출물: <경로>` 로 정규화한다.
                # 🔴 그리고 그 경로는 **자기 파일 위치 기준**이라 기준본(임시 디렉터리)과
                #    작업본(저장소)이 원리상 다르다 --- 코드가 같아도 다르다.
                note = ("🔴 `산출물:` 경로 한 줄을 **양쪽 다** `<경로>` 로 정규화하고 견줬다 "
                        "--- 그 경로는 자기 파일 위치 기준이라 기준본과 작업본이 원리상 다르다")
            same = (a.returncode == b.returncode and ao == bo and ae == be)
            per[name] = {"기준 종료": a.returncode, "지금 종료": b.returncode,
                         "stdout 같나": ao == bo, "stderr 같나": ae == be,
                         "같나": same, **({"⚠": note} if note else {})}
            if not same:
                diff.append(name)
        if _new_tmp:
            shutil.rmtree(_new_tmp, ignore_errors=True)
        return {
            "검사": "5 quote901 기존 동작 무변 --- 기준본 대 작업본",
            "기준본": "git show %s:runners/quote901.py" % ref,
            "작업본": (now or "runners/quote901.py"),
            "🔴 견준 가짓수(분모)": len(cases),
            "🔴 같은 것": len(cases) - len(diff),
            "🔴 다른 것": diff or "없음",
            "가짓수별": per,
            "⚠ 지운 것": ("임시 디렉터리 이름과 `--selftest` 의 「산출물:」 경로 **한 줄**. "
                          "그 밖은 한 글자도 안 지웠다"),
            "🔴 ⚠ 못 재는 것": ("`--selftest` 가 **어느 파일에 쓰는지**가 바뀌어도 이 시험은 "
                            "못 잡는다 --- 양쪽 경로를 `<경로>` 로 뭉개기 때문이다(티처 #65 M15). "
                            "그 사각지대를 5-나 에 심어서 재야 한다(아직 안 했다)"),
            "통과": (not diff),
        }


#: 🔴 **이 시험이 무엇을 못 가르는지 먼저 잰다**(티처 #64 m4). 「안 바꿨다」를 증명하려면
#: 그 시험이 **바꿨을 때 붉어진다**는 것부터 보여야 한다.
MUTANTS = [
    ("종료 코드 갈래를 흔든다(E_MISMATCH 6→7)",
     "E_OK, E_NOFILE, E_NOTJSON, E_NOKEY, E_NULL, E_MISMATCH = 0, 2, 3, 4, 5, 6",
     "E_OK, E_NOFILE, E_NOTJSON, E_NOKEY, E_NULL, E_MISMATCH = 0, 2, 3, 4, 5, 7"),
    ("--cite 의 출처 꼴에서 백틱을 뗀다",
     'cite = "`%s:%s`" % (a.file, a.sep.join(path))',
     'cite = "%s:%s" % (a.file, a.sep.join(path))'),
    ("--check 를 관대하게 만든다(어긋나도 안 죽는다)",
     "        if not same:\n            die(E_MISMATCH,",
     "        if False:\n            die(E_MISMATCH,"),
]


def quote_power(ref) -> dict:
    """🔴 이 무변 시험이 **실제로 붉어지나**(검정력)를 심어서 잰다.

    ⚠ **씨앗은 기준본이어야 한다**(티처 #65 C1 수리의 곁가지 · 주 세션 실측).
    작업본을 씨앗으로 쓰면 「안 바꾼 사본」이 **기준본과 실제로 달라서**
    음성 대조가 영원히 False 가 된다 --- 그러면 이 절도 아무것도 못 잰다.
    「안 바꿨으면 통과」가 성립하려면 사본이 **견줄 대상과 같은 판**이어야 한다.
    """
    import tempfile
    rc0, base_src, err0 = _git(["show", "%s:runners/quote901.py" % ref])
    if rc0 != 0 or not base_src.strip():
        return {"검사": "5-나 심어서 확인", "🔴 예외": "씨앗(기준본)을 못 꺼냈다: %s" % err0[:200],
                "통과": False}
    src = base_src
    rows, missed, unplanted = {}, [], []
    with tempfile.TemporaryDirectory() as td:
        for name, old, new in MUTANTS:
            if old not in src:
                unplanted.append(name)
                rows[name] = {"🔴": "못 심었다 --- 그 문자열이 없다(「잡았다」가 아니다 · 조항 59)"}
                continue
            p = Path(td) / ("m%d.py" % len(rows))
            p.write_text(src.replace(old, new), encoding="utf-8")
            r = quote_regress(ref, str(p))
            caught = not r["통과"]
            rows[name] = {"잡았나": caught, "붉어진 가짓수": r["🔴 다른 것"]}
            if not caught:
                missed.append(name)
        ctl = Path(td) / "ctl.py"
        ctl.write_text(src, encoding="utf-8")
        c = quote_regress(ref, str(ctl))
    return {
        "검사": "5-나 🔴 **심어서 확인** --- 이 무변 시험이 실제로 붉어지나(검정력)",
        "🔴 심은 가짓수(분모)": len(MUTANTS),
        "🔴 잡은 수": len(MUTANTS) - len(missed) - len(unplanted),
        "🔴 놓친 것": missed or "없음",
        "🔴 못 심은 것(=「잡았다」가 아니다)": unplanted or "없음",
        "심은 것별": rows,
        "음성 대조(안 바꾼 사본)": {"통과": c["통과"], "다른 것": c["🔴 다른 것"]},
        "통과": (not missed) and (not unplanted) and c["통과"],
    }


# ── 6 D1 실측 (이슈 #140 M6) ────────────────────────────────────────────
def d1_census() -> dict:
    """🔴 사전등록 `docs/prereg_901_intervention.md:101` 은 **D1 = 원천 「파일 수」**라 적었다.

    그 정의가 맞는 도메인은 셋뿐이다. **사전등록은 증거물이라 고치지 않는다** ---
    대신 **세어서 산출물에 남기고** 정정문을 원장으로 보낸다.

    🔴 `SRC` 표를 **손으로 옮겨 적지 않는다** --- `runners/inv901.py` 를 `ast` 로 읽는다
    (import 하면 그 러너의 무거운 본문이 돈다).
    """
    src_py = (ROOT / "runners/inv901.py").read_text(encoding="utf-8")
    tree = ast.parse(src_py)
    SRC = None
    for n in tree.body:
        if isinstance(n, ast.Assign) and any(
                getattr(t, "id", None) == "SRC" for t in n.targets):
            SRC = ast.literal_eval(n.value)
    if SRC is None:
        return {"검사": "6 D1 실측", "🔴": "`runners/inv901.py` 에서 SRC 를 못 찾았다", "통과": False}

    rows, multi, single, exc = {}, [], [], {}
    for dom, (kind, p, _ax, _o) in SRC.items():
        fp = ROOT / p
        try:
            if kind == "dir":
                fs = sorted(fp.glob("*.json"))
                nf, nr = len(fs), len(fs)          # dir 은 파일 하나 = 레코드 하나
            elif kind == "jsonl":
                nf = 1
                nr = sum(1 for l in open(fp, encoding="utf-8") if l.strip())
            else:
                nf = 1
                d = json.loads(fp.read_text(encoding="utf-8"))
                nr = len(d) if isinstance(d, (dict, list)) else 0
        except Exception as e:                                    # noqa: BLE001
            exc[dom] = "%s: %s" % (type(e).__name__, e)
            continue
        rows[dom] = {"원천 종류": kind, "원천": p, "원천 파일 수": nf, "레코드 수": nr,
                     "🔴 「파일 수」 정의가 맞나": (nf == nr)}
        (multi if nf > 1 else single).append(dom)
    return {
        "검사": "6 D1 실측 --- 사전등록의 「원천 파일 수」가 실제와 맞나(이슈 #140 M6)",
        "🔴 사전등록은 고치지 않는다": "`docs/prereg_901_intervention.md` 는 증거물이다. 정정문으로 닫는다",
        "🔴 도메인 수(분모)": len(SRC),
        "🔴 파일이 여럿인 도메인 수": len(multi), "그 목록": sorted(multi),
        "🔴 파일이 하나인 도메인 수": len(single), "그 목록": sorted(single),
        "🔴 「파일 수 == 레코드 수」가 성립하는 도메인 수": len([d for d in rows if rows[d]["🔴 「파일 수」 정의가 맞나"]]),
        "도메인별": rows,
        "🔴 예외": exc or "없음",
        "🔴 정정문(원장용)": (
            "정정 — `docs/prereg_901_intervention.md:101` 의 **D1 = 「원천 파일 수」**는 틀렸다. "
            "그 정의가 맞는 도메인은 **셋**(디렉터리 원천: 팝업·시장팝업·아이돌)뿐이고 "
            "나머지 **아홉**은 원천이 **파일 하나**다. 실제로 측정된 D1 은 "
            "**전 도메인에서 레코드 수**이며, 구현이 그렇게 적혀 있다"
            "(`runners/inv901.py:6` *「D1 원천 레코드 수」* · `:392` `D1 = len(recs)`). "
            "🔴 **사전등록 파일은 증거물이라 고치지 않는다** --- 이 정정문이 딱지의 정본이다."),
        "통과": (not exc) and (len(rows) == len(SRC)),
    }


# ── 8 🔴 [수리] 레인 계수 (955 R6 · 티처 #93 C4·㉤) ─────────────────────
#: 🔴 954 는 원장·노트·인계 카드 **셋 다**에 *「수리 레인은 한 사이클에 하나이고 그 하나를
#: 썼다」* 고 적고 실제로는 `[수리]` 커밋을 **셋** 했다. 말로 적는 한 또 어긋난다 ---
#: **기계가 센다.** 사전등록(`docs/prereg_9NN_*.md` §8 표)이 예고한 수와 견준다.
REPAIR_TAG = "[수리]"
#: §8 표의 레인 줄: `| R1 | 무엇 | 파일 |`
PREREG_ROW = re.compile(r"^\|\s*\*{0,2}R(\d+)\*{0,2}\s*\|", re.M)
#: §8 의 머리(다른 절의 표를 세지 않게 §8 안으로만 자른다).
PREREG_SEC = re.compile(r"^##\s*8\.", re.M)
#: 🔴🔴 **956 R2** --- 개정된 `docs/루프.md` 레인 규칙 4 의 **상한**을 사전등록 §8 에서 읽는다.
#:    「상한: N」 줄이 없으면 **「모른다」**다 --- **규칙 기본 1 을 조용히 넣지 않는다**(조항 59).
PREREG_CAP = re.compile(r"^\s*[>*\-|\s]*상한\s*[:：]\s*(\d+)", re.M)
#: 🔴 **저장소 밖 레인 신고** --- 955 가 인계 카드를 고쳤는데 계수기가 원리상 못 봤다(티처 #94 C4).
PREREG_OUTSIDE = re.compile(r"저장소 밖 레인\s*[:：]\s*(\d+)", re.M)
#: 🔴 계수기가 눈으로 보는 **저장소 밖** 파일(고치면 레인이다).
OUTSIDE_FILES = [
    os.path.expanduser(
        "~/.claude/projects/-Users-ax-world-model/memory/project-lab-state.md"),
]


def prereg_expected(prereg: str, tree: str = "HEAD", known=None) -> dict:
    """🔴 사전등록 §8 표에서 **예고한 [수리] 레인 수**를 읽는다(955 R6).

    🔴 못 읽으면 **「모른다」**를 낸다. **0 을 내지 않는다**(조항 59) --- 0 은
    「레인을 안 열었다」는 **주장**이고, 못 읽은 것은 **주장이 아니다**.
    """
    if not prereg:
        return {"수": None, "🔴": "사전등록을 안 줬다(`--prereg`) --- 「모른다」다"}
    st, txt = tree_text(prereg, tree, known)
    if st != "읽었다":
        return {"수": None, "🔴": "`%s` 를 **%s**(「0 개」가 아니다)" % (prereg, st), "상태": st}
    m = PREREG_SEC.search(txt)
    if not m:
        return {"수": None, "🔴": "`%s` 에서 `## 8.` 절을 못 찾았다" % prereg}
    body = txt[m.end():]
    nxt = re.search(r"^##\s", body, re.M)
    body = body[:nxt.start()] if nxt else body
    ids = PREREG_ROW.findall(body)
    if not ids:
        return {"수": None, "🔴": "`## 8.` 안에서 `| R<n> |` 줄을 하나도 못 찾았다"}
    # 🔴🔴 956 R2 --- 예고한 **파일**도 같이 읽는다(레인 줄의 마지막 칸).
    #    「커밋 제목 문자열이 아니라 실제 바뀐 파일을 세라」(티처 #94 C4) 의 자다.
    files = set()
    for line in body.split("\n"):
        if not PREREG_ROW.match(line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 3:
            for tok in re.findall(r"`([^`]+)`", cells[-1]):
                if "/" in tok or tok.startswith("."):
                    files.add(tok)
    cap = PREREG_CAP.search(body)
    outside = PREREG_OUTSIDE.search(body)
    return {"수": len(ids), "레인 번호": ["R%s" % i for i in ids],
            "🔴 예고한 파일": sorted(files) or "없음",
            "🔴 상한(사전등록 §8 의 「상한: N」 줄)":
                int(cap.group(1)) if cap else None,
            "🔴 상한을 못 읽었을 때": ("🔴 모른다 --- §8 에 「상한: N」 줄이 없다. "
                            "**규칙 기본 1 을 조용히 넣지 않는다**(조항 59). "
                            "`docs/루프.md` 레인 규칙 4 는 「지시가 시킨 건수」를 상한으로 "
                            "삼으라 하고, 그 수는 사람이 §8 에 적어야 기계가 읽는다"
                            if not cap else "읽었다"),
            "🔴 저장소 밖 레인 신고(§8 의 「저장소 밖 레인: N」 줄)":
                int(outside.group(1)) if outside else None,
            "출처": "%s §8 표(`| R<n> |` 줄)" % prereg, "트리": tree}


def repair_lanes(base, head, expected=None, prereg=None, mainref="main",
                 tree="HEAD") -> dict:
    """🔴 **이 가지에서 연 `[수리]` 커밋을 센다**(955 R6 · 티처 #93 C4).

    🔴 규약 60 --- **명령 · 범위 · 트리 셋을 같이 적는다.** 수만 적으면 다음 사람이
    「무엇을 센 수인지」를 못 읽고, 그러면 이 절도 954 의 그 문장과 같아진다.
    """
    head_sha = _rev(head)
    rc_m, mb_out, mb_err = _git(["merge-base", mainref, head])
    mb = mb_out.strip()
    why = ""
    if rc_m != 0 or not mb:
        rng = _rev(base)
        why = ("🔴 `git merge-base %s %s` 가 죽었다(%s) --- 범위를 취합 시작(`--base`)으로 "
               "갈음했다" % (mainref, head, (mb_err or "").strip()[:120]))
    elif mb == head_sha:
        rng = _rev(base)
        why = ("🔴 `git merge-base %s %s` 가 **머리 자신**이다 --- 머리가 `%s` 위에 있다"
               "(가지를 이미 머지했거나 `%s` 에서 돌린다). 그러면 가지 범위가 빈다 · "
               "범위를 **취합 시작(`--base`)**으로 갈음했다" % (mainref, head, mainref, mainref))
    else:
        rng = mb
        why = "`git merge-base %s %s` --- 이 가지가 갈라진 자리" % (mainref, head)
    cmd_mb = "git merge-base %s %s" % (mainref, head)
    cmd_log = "git log --format=%%s %s..%s" % (rng[:9], head_sha[:9])
    rc, out, err = _git(["log", "--format=%H%x1f%s", "%s..%s" % (rng, head)])
    if rc != 0:
        return {"검사": "8 🔴 `[수리]` 레인 계수(955 R6)", "통과": False,
                "🔴 명령": [cmd_mb, cmd_log],
                "🔴": "모른다 --- `git log` 가 종료 %d 다: %s" % (rc, err[:200])}
    rows = [l.split("\x1f", 1) for l in out.split("\n") if l.strip()]
    subs = [(r[0], r[1] if len(r) > 1 else "") for r in rows]
    repairs = [(h, s) for h, s in subs if s.startswith(REPAIR_TAG)]
    # 🔴 955 R6 --- 커밋 제목에서 **레인 표지 `R<n>`** 를 뽑는다(`[수리] R7·R8 …`).
    #    `\bR\d+\b` 를 제목 **앞부분**에서만 찾는다(본문 인용의 `R5` 같은 것을 안 센다).
    lanes = set()
    untagged = []
    for _h, s in repairs:
        head_part = s.split("—")[0].split("---")[0]
        found = re.findall(r"\bR(\d+)\b", head_part)
        if found:
            lanes.update("R%s" % i for i in found)
        else:
            untagged.append(s)
    tags = {}
    for _h, s in subs:
        t = s.split("]")[0] + "]" if s.startswith("[") and "]" in s else "(표지 없음)"
        tags[t] = tags.get(t, 0) + 1

    # 🔴🔴 **956 R2 (티처 #94 C4)** --- 「커밋 제목 문자열」이 아니라 **실제 바뀐 파일**을 센다.
    #    ① 표지 없는 `[수리]` 커밋도 **파일로는 세어진다** ② 예고한 파일과 실제 바꾼 파일을
    #    대조한다 ③ 데몬 커밋(`[데몬]`·`[수집]`)이 만진 자료 경로는 레인이 아니므로 뺀다.
    def _files_of(sha):
        rc2, o2, _e2 = _git(["-c", "core.quotePath=false", "diff-tree", "--no-commit-id",
                             "--name-only", "-r", "-z", sha])
        return {p for p in o2.split("\0") if p.strip()} if rc2 == 0 else set()

    DATA_PREFIX = ("data/ingest/", "data/state/")
    repair_files, per_commit_files = set(), []
    for h, s in repairs:
        fs = _files_of(h)
        per_commit_files.append({"sha": h[:9], "제목": s,
                                 "🔴 바꾼 파일": sorted(fs) or "없음",
                                 "바꾼 파일 수": len(fs)})
        repair_files |= {f for f in fs if not f.startswith(DATA_PREFIX)}

    src = "--expected-repairs"
    pre = prereg_expected(prereg, tree) if expected is None else None
    exp = expected if expected is not None else (pre or {}).get("수")
    if expected is None:
        src = (pre or {}).get("출처") or "🔴 못 읽었다"
    n = len(repairs)

    # 🔴 956 R2 --- 상한 · 예고 파일 · 저장소 밖 레인
    cap = (pre or {}).get("🔴 상한(사전등록 §8 의 「상한: N」 줄)")
    want_files = set((pre or {}).get("🔴 예고한 파일") or [])
    if want_files == {"없음"}:
        want_files = set()
    outside_declared = (pre or {}).get("🔴 저장소 밖 레인 신고(§8 의 「저장소 밖 레인: N」 줄)")
    # 🔴 저장소 밖 파일이 이 가지의 첫 커밋 뒤에 바뀌었나(955 가 인계 카드를 고쳤다 · 티처 #94 C4)
    rc_t, t_out, _ = _git(["log", "--format=%ct", "-1", rng])
    base_epoch = int(t_out.strip()) if rc_t == 0 and t_out.strip() else None
    outside_touched = []
    for p in OUTSIDE_FILES:
        try:
            mt = os.path.getmtime(p)
        except OSError:
            outside_touched.append({"파일": p, "🔴": "못 읽었다(「안 바뀌었다」가 아니다)"})
            continue
        if base_epoch is not None and mt > base_epoch:
            try:
                sha = hashlib.sha256(open(p, "rb").read()).hexdigest()
            except OSError:
                sha = "🔴 못 읽었다"
            outside_touched.append({
                "파일": p, "mtime(UTC)": dt.datetime.utcfromtimestamp(mt).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"),
                # 🔴 다음 사이클이 **내용**으로 견줄 수 있게 sha 를 남긴다.
                #    mtime 만으로는 「내가 안 고쳤다」와 「안 바뀌었다」를 못 가른다.
                "sha256(다음 사이클의 대조 기준)": sha,
                "🔴 이 가지가 갈라진 뒤에 바뀌었다": True})
    outside_unreported = (len(outside_touched) > 0 and not outside_declared)

    return {
        "검사": "8 🔴 `[수리]` 레인 계수 --- 기계가 센다(955 R6 · 🔴 956 R2 로 자를 바꿨다)",
        "🔴 왜": ("954 는 원장·노트·카드 **셋 다**에 「수리 레인 하나를 썼다」고 적고 실제로 "
               "`[수리]` 커밋을 **셋** 했다. 말로 적으면 또 어긋난다"),
        # 🔴 규약 60 --- 명령 · 범위 · 트리 셋
        "🔴 명령": [cmd_mb, cmd_log],
        "🔴 범위": "%s..%s" % (rng, head_sha),
        "🔴 범위의 기준(base)": {"rev": rng, "왜": why, "mainref": mainref,
                          "취합 시작(--base)": _rev(base)},
        "🔴 트리": {"기준": "커밋된 트리", "머리": head, "커밋 sha": head_sha},
        "🔴 이 범위의 커밋 수(분모)": len(subs),
        "🔴 그중 `[수리]` 커밋 수(분자)": n,
        "🔴 `[수리]` 커밋 제목": [s for _h, s in repairs] or "없음",
        "`[수리]` 커밋 sha": [h[:9] for h, _s in repairs] or "없음",
        "표지별 커밋 수": dict(sorted(tags.items())),
        # 🔴🔴 **레인 ≠ 커밋**. 한 커밋이 레인 둘을 나를 수 있고(`R7·R8`), 한 레인이
        #    커밋 둘로 갈릴 수도 있다. 954 의 병은 「레인 하나」라 적고 커밋 셋을 한 것인데,
        #    커밋만 세면 그 병을 **뒤집어서** 다시 못 잡는다.
        #    → 커밋 제목의 **`R<n>` 표지**를 세어 **레인을 직접** 센다.
        "🔴🔴 레인 표지(`R<n>`)로 센 레인": sorted(lanes, key=lambda x: int(x[1:])) or "없음",
        "🔴🔴 레인 수(분자 --- 이것이 「수리 레인」의 수다)": len(lanes),
        "🔴 표지 없는 `[수리]` 커밋(레인을 못 센다)": [s for s in untagged] or "없음",
        "🔴 사전등록이 예고한 레인 수": (exp if exp is not None else
                            "🔴 모른다 --- `--expected-repairs` 도 `--prereg` 도 못 읽었다"
                            "(**0 이 아니다** · 조항 59)"),
        "예고 수의 출처": src,
        "예고한 레인 번호": (pre or {}).get("레인 번호", "안 읽었다"),
        "🔴 예고했는데 안 연 레인": sorted(set((pre or {}).get("레인 번호", [])) - lanes,
                                key=lambda x: int(x[1:])) or "없음",
        "🔴 안 예고했는데 연 레인": sorted(lanes - set((pre or {}).get("레인 번호", [])),
                                key=lambda x: int(x[1:])) or "없음",
        "사전등록 파싱": pre or "안 했다(`--expected-repairs` 를 받았다)",
        "🔴 센 레인 − 예고 레인": (len(lanes) - exp) if exp is not None else "🔴 모른다",
        "🔴 센 커밋 − 예고 레인(참고 --- 954 가 어긴 자리)":
            (n - exp) if exp is not None else "🔴 모른다",

        # ── 🔴🔴 956 R2 --- 실제 바뀐 파일 · 규칙 상한 · 저장소 밖 ──────────────
        "🔴🔴 956 R2 ㉠ 실제 바뀐 파일로 센다(커밋 제목 문자열이 아니다)": {
            "커밋별": per_commit_files or "없음",
            "🔴 `[수리]` 가 바꾼 파일 전량(자료 경로 제외)": sorted(repair_files) or "없음",
            "🔴 파일 수": len(repair_files),
            "🔴 예고한 파일": sorted(want_files) or "🔴 못 읽었다",
            "🔴 예고했는데 안 바꾼 파일": sorted(want_files - repair_files) or "없음",
            "🔴 예고 안 했는데 바꾼 파일": sorted(repair_files - want_files) or "없음",
            "⚠ 뺀 것": "`data/ingest/` · `data/state/`(상시 데몬 감시 구역 --- 레인이 아니다)",
            "통과": bool(want_files and not (want_files - repair_files)
                       and not (repair_files - want_files)),
        },
        "🔴🔴 956 R2 ㉡ 규칙 상한(`docs/루프.md` 레인 규칙 4 · v3.10)": {
            "🔴 상한": cap if cap is not None else
                     "🔴 모른다 --- 사전등록 §8 에 「상한: N」 줄이 없다(**0 도 1 도 아니다**)",
            "🔴 왜 기본값을 안 넣나": ("954·955 의 통과 조건이 `센 레인 == 자기 예고` 라 "
                              "**규칙이 아니라 자기 예고를 자로 삼았다**(티처 #94 C4). "
                              "여기서 규칙 기본 1 을 조용히 넣으면 같은 병의 다른 얼굴이 된다 --- "
                              "**사람이 §8 에 근거와 함께 적어야 기계가 읽는다**"),
            "센 레인 수": len(lanes),
            "🔴 상한 안인가": (None if cap is None else bool(len(lanes) <= cap)),
            "통과": bool(cap is not None and len(lanes) <= cap),
        },
        "🔴🔴 956 R2 ㉢ 저장소 밖 레인(955 가 인계 카드를 고쳤고 계수기가 원리상 못 봤다)": {
            "본 파일": OUTSIDE_FILES,
            "🔴 이 가지가 갈라진 뒤 바뀐 것": outside_touched or "없음",
            "🔴 §8 이 신고한 저장소 밖 레인 수": (outside_declared if outside_declared is not None
                                    else "🔴 신고 없음"),
            "🔴 미신고 저장소 밖 수리": outside_unreported,
            "⚠ 자의 한계": ("mtime 만 본다 --- **무엇이 바뀌었는지는 안 본다**. "
                       "git 밖이라 내용 대조를 할 자가 없다(조항 61)"),
            "통과": bool(not outside_unreported),
        },

        "통과": bool((exp is not None) and (len(lanes) == exp) and not untagged
                   and cap is not None and len(lanes) <= cap
                   and not outside_unreported),
        "🔴 통과의 뜻": ("🔴 **956 R2 로 자를 바꿨다.** 넷을 전부 만족해야 통과다 --- "
                   "① `R<n>` 레인 수 == 사전등록 §8 예고 · ② 표지 없는 `[수리]` 커밋 0 · "
                   "🔴 ③ **개정된 규칙(`docs/루프.md` 레인 규칙 4 · v3.10)의 상한 안** "
                   "(상한을 못 읽으면 **불통과** --- 「모른다」는 「통과」가 아니다) · "
                   "🔴 ④ **저장소 밖 수리가 있으면 §8 이 신고했을 것**. "
                   "954·955 는 ①만 봤고 그래서 **자기 예고가 곧 자였다**"),
    }


# ── 엮기 ────────────────────────────────────────────────────────────────
def main(argv=None):
    ap = argparse.ArgumentParser(prog="fiveprime902.py", description=__doc__.split("\n")[0])
    ap.add_argument("--base", required=True, help="취합 시작 rev")
    ap.add_argument("--head", default="HEAD")
    # 🔴 **955 R5** --- 기본을 **커밋된 트리**로 바꿨다(`docs/루프.md:148` v3.2 · 티처 #93 M5).
    #    954 까지 기본이 「작업 트리」라 ⑤′ 가 **커밋 안 된 편집**을 검사했다.
    #    작업 트리를 일부러 보고 싶으면 `--tree 작업트리`(또는 `worktree`).
    ap.add_argument("--tree", default=None,
                    help="역참조·읽기를 이 rev 트리에서 한다(기본: --head = **커밋된 트리** · "
                         "`작업트리`/`worktree` 를 주면 옛 동작)")
    ap.add_argument("--ran", action="append", default=[], help="이번에 실제로 다시 돌린 소비자 경로")
    ap.add_argument("--exempt", action="append", default=[], help="경로=사유")
    ap.add_argument("--keyaudit", action="append", default=[], help="판정 키를 감사할 산출물 추가")
    ap.add_argument("--gates", action="store_true", help="게이트를 실제로 돌린다")
    # 🔴 **기준본이 `HEAD` 면 이 절은 원리상 아무것도 못 잰다**(티처 #65 C1).
    #    ⑤′ 는 **⑤ 취합 뒤**에 돌므로 그때 HEAD 는 이미 **그 편집을 담은 커밋**이다.
    #    실측: 커밋된 실행의 기준본이 `0c323056c`(= `quote901.py` 를 고친 그 커밋)라
    #    작업본과 **바이트 동일**이었고 13/13 이 나왔다. 진짜 편집 전 rev(`6a27a645f`)로
    #    돌리면 **12/13 · 다른 것 `--selftest`** 다.
    #    🔴 티처 #64 M4 의 「16/16」이 「13/13」으로 **얼굴만 바꿔 재발**했다.
    #    그래서 기본값을 **취합 시작 rev(`--base`)** 로 바꾼다 --- 그게 「편집 전」이다.
    ap.add_argument("--quote-ref", default=None,
                    help="quote901 기준본 rev(기본: --base = 취합 시작 rev)")
    ap.add_argument("--quote-now", default=None,
                    help="🔴 작업본 대신 이 파일을 견준다 --- **심어서 검정력을 재는** 자리")
    ap.add_argument("--out", default=str(OUT_DEFAULT))
    ap.add_argument("--docstamp", default=DOCSTAMP,
                    help="🔴 문서 대조가 읽을 도장 파일(기본: %s)" % DOCSTAMP)
    # 🔴 949 --- 45 개 사유를 손으로 치면 **증거가 셸 히스토리에만 남는다**.
    #    사유를 커밋된 JSON 으로 받는다(`{경로: 사유}`). 사유는 `[자:<이름>]` 으로 시작한다.
    # 🔴 957 (티처 #95 C1) --- 산문 주장을 산출물 키에 물린다. 모듈이 `CLAIMS` 를 갖는다.
    ap.add_argument("--prose", default=None,
                    help="🔴 산문 주장 목록 모듈(예: runners.prose_check)")
    ap.add_argument("--exempt-file", default=None,
                    help="🔴 면제 사유를 담은 JSON(`{경로: \"[자:…] 사유\"}`)")
    # ── 🔴 955 R6 --- `[수리]` 레인을 **기계가 센다**(티처 #93 C4·㉤)
    ap.add_argument("--expected-repairs", type=int, default=None,
                    help="🔴 사전등록이 예고한 `[수리]` 레인 수. 안 주면 `--prereg` 에서 읽고, "
                         "그것도 없으면 **「모른다」**를 낸다(0 이 아니다)")
    ap.add_argument("--prereg", default=None,
                    help="🔴 사전등록 파일(§8 표의 `| R<n> |` 줄을 센다 · 예: docs/prereg_955_D.md)")
    ap.add_argument("--repair-main", default="main",
                    help="`[수리]` 계수 범위의 기준 가지(`git merge-base <이것> <head>`)")
    a = ap.parse_args(argv)

    if a.quote_ref is None:
        a.quote_ref = a.base          # 🔴 위 주석 참조 --- HEAD 는 자기 자신이다
    # 🔴 955 R5 --- 「어느 트리를 되짚나」를 여기서 한 번에 정한다.
    #    `docs/루프.md:148`(v3.2): ⑤′ 는 **커밋된 트리**에서 되짚는다.
    worktree_mode = str(a.tree).lower() in ("작업트리", "worktree", "work", "none")
    if a.tree is None:
        a.tree = a.head               # 🔴 기본이 커밋된 트리다
    elif worktree_mode:
        a.tree = None                 # 옛 동작(작업 트리) --- 일부러 준 때만
    read_tree = a.head if a.tree is None else a.tree

    t0 = time.time()
    exempt = {}
    if a.exempt_file:
        exempt.update(json.loads((ROOT / a.exempt_file).read_text(encoding="utf-8")))
    for e in a.exempt:
        k, _, v = e.partition("=")
        exempt[k.strip()] = v.strip() or "🔴 사유가 비었다"
    # 🔴 953 --- 대상을 **이 사이클이 찍은 산출물**로 정한다(옛 하드코딩 한 줄을 대신한다)
    ka = keyaudit_targets(a.base, a.head)
    st = stamp(KEYAUDIT_MUST + list(ka["🔴 대상"]) + list(a.keyaudit))   # 🔴 시작에서 찍는다

    ran = list(a.ran)
    if a.gates:
        ran.append("ingest/audit.py")

    res = {"무엇": "⑤′ 취합 검사 러너 --- 이슈 #140 M3·M4·M6",
           # 🔴 949 --- **인자를 산출물에 남긴다**. 948 은 45 개 `--exempt` 를 손으로 쳤는데
           #    그 문자열이 어디에도 안 남아 다음 세션이 재현할 수 없었다(티처 #88 C4).
           "🔴 인자(argv)": list(argv if argv is not None else sys.argv[1:]),
           "🔴 사유 파일": a.exempt_file or "없음",
           # 🔴 955 R5 --- **어느 기준을 썼는지 산출물에 박는다**(티처 #93 M5)
           "🔴 되짚은 기준(955 R5 · `docs/루프.md:148` v3.2)": {
               "기준": "🔴 **커밋된 트리**",
               "읽기·해싱 트리(절 3·4·7·8)": read_tree,
               "그 커밋 sha": _rev(read_tree),
               "역참조(grep) 트리(절 1·2)": a.tree or "🔴 작업 트리(`--tree 작업트리` 를 줬다)",
               "머리(--head)": "%s = %s" % (a.head, _rev(a.head)),
               "취합 시작(--base)": "%s = %s" % (a.base, _rev(a.base)),
               "⚠ 954 까지": "작업 트리를 되짚었다 --- 커밋 안 된 편집이 검사에 섞였다",
               "🔴 「커밋 안 됨」은 「없다」가 아니다": "절 3·4·7 이 그것을 **따로 센다**(조항 59)",
           },
           "🔴 규약": [
               "① 소비자는 **기계 역참조**로 뽑고 **목록을 이 파일에 남긴다**",
               "② 🔴 분모 넷을 나란히 박는다 --- 바뀐 경로 · 역참조 소비자 · 돌린 것 · **안 돌린 것**",
               "③ 모든 절이 `통과` 키를 갖는다. 없는 절을 소비할 땐 **「모른다」로 센다**",
               "④ 「안 돌렸다」는 「없다」가 아니다(조항 59)",
           ]}
    res["⓪ 관문(작업 트리)"] = gate_worktree()
    try:
        res["1 소비자 역참조"] = backref(a.base, a.head, a.tree, ran, exempt)
    except Exception as e:                                        # noqa: BLE001
        res["1 소비자 역참조"] = {"🔴 예외": "%s: %s" % (type(e).__name__, e), "통과": False}
    # 🔴 947 --- 「날 것 호출은 ⑤′ 가 잡는다」를 **배선**으로 만든다(티처 #86 M2)
    for key, fn in (("1-나 🔴 날 것 git 호출 전수(947 상설)", rawgit_gate),
                    ("1-다 🔴 그 게이트의 검정력(심어서 확인)", rawgit_power)):
        try:
            res[key] = fn()
        except Exception as e:                                    # noqa: BLE001
            res[key] = {"🔴 예외": "%s: %s" % (type(e).__name__, e), "통과": False}
    try:
        res["1-라 🔴 `_grep_l` 건초더미 대조(947)"] = grepl_regress(a.base, a.head, a.tree)
    except Exception as e:                                        # noqa: BLE001
        res["1-라 🔴 `_grep_l` 건초더미 대조(947)"] = {
            "🔴 예외": "%s: %s" % (type(e).__name__, e), "통과": False}

    _cons = res["1 소비자 역참조"].get("역참조 소비자(전량)", [])
    # 🔴 948 (티처 #87 M2) --- `exempt` 를 **넘긴다**. 947 은 이미 만들어 놓고 안 넘겼다.
    res["2 게이트"] = run_gates(a.gates, a.tree,
                             _cons if isinstance(_cons, list) else [], ran,
                             exempt=exempt)
    res["3 판정 키 규약"] = keyaudit(a.keyaudit, ka, read_tree)
    res["4 도장 확인"] = stamp_audit(read_tree)
    res["5 quote901 무변"] = quote_regress(a.quote_ref, a.quote_now)
    res["5-나 무변 시험의 검정력(심어서 확인)"] = quote_power(a.quote_ref)
    res["6 D1 실측"] = d1_census()
    try:
        res["7 🔴 문서 대조(950 · 티처 #89 M1)"] = doc_check(a.docstamp, read_tree)
    except Exception as e:                                        # noqa: BLE001
        res["7 🔴 문서 대조(950 · 티처 #89 M1)"] = {
            "🔴 예외": "%s: %s" % (type(e).__name__, e), "통과": False}
    # 🔴 955 R6 --- `[수리]` 레인을 기계가 센다(티처 #93 C4·㉤)
    try:
        res["8 🔴 `[수리]` 레인 계수(955 R6)"] = repair_lanes(
            a.base, a.head, a.expected_repairs, a.prereg, a.repair_main, read_tree)
    except Exception as e:                                        # noqa: BLE001
        res["8 🔴 `[수리]` 레인 계수(955 R6)"] = {
            "🔴 예외": "%s: %s" % (type(e).__name__, e), "통과": False}

    # 🔴🔴 957 (티처 #95 C1) --- **도장은 수만 보고 산문은 원리상 안 본다.**
    #    956 에서 원장·노트가 「안 했다」고 적은 일을 실제로는 했고, 도장은 그걸 못 봤다
    #    (도장 자신이 *「산출물의 수 자체가 옳은지는 안 본다」* 고 적는다).
    #    이 절은 **문서의 문장**과 **산출물의 키**를 맞댄다.
    if a.prose:
        try:
            import importlib
            mod = importlib.import_module(a.prose)
            from runners.prose_check import check as _pcheck
            r8 = _pcheck(getattr(mod, "CLAIMS"), stdout=False)
            r8["🔴 주장 목록 모듈"] = a.prose
            res["8 🔴 산문 주장 대 산출물 키(957 · 티처 #95 C1)"] = r8
        except Exception as e:                                    # noqa: BLE001
            res["8 🔴 산문 주장 대 산출물 키(957 · 티처 #95 C1)"] = {
                "🔴 예외": "%s: %s" % (type(e).__name__, e), "통과": False}
    else:
        res["8 🔴 산문 주장 대 산출물 키(957 · 티처 #95 C1)"] = {
            "🔴 안 돌렸다": "`--prose <모듈>` 을 안 줬다 --- 「없다」가 아니라 「안 돌렸다」다(조항 59)",
            "통과": False}

    secs = {k: v for k, v in res.items() if isinstance(v, dict) and "통과" in v}
    fail = sorted(k for k, v in secs.items() if not v["통과"])
    res["🔴 절 수(분모)"] = len(secs)
    res["🔴 `통과` 키를 가진 절"] = len(secs)
    res["🔴 실패한 절"] = fail or "없음"
    res["통과"] = (not fail)
    res.update(stamp_close(st, t0))

    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    # 화면 요약은 **절만** 줄인다(도장 dict 를 줄이면 도장이 빈 것처럼 보인다)
    print(json.dumps({k: ({kk: vv for kk, vv in v.items()
                           if kk.startswith(("🔴", "통과", "검사"))}
                          if (isinstance(v, dict) and "통과" in v) else v)
                      for k, v in res.items()}, ensure_ascii=False, indent=1))
    print("산출물: %s" % a.out)
    return 0 if res["통과"] else 1


if __name__ == "__main__":
    sys.exit(main())
