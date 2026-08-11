"""노트 946 --- **두 번째 경로**. 🔴 첫 경로와 **결함을 공유하지 않는다**.

## 왜 이 러너가 따로 있나

945 는 두 경로로 셌는데 **둘 다 인용부호를 놓쳤다**(티처 #85 C2). 규칙 A 는
`git log --name-only`, 규칙 B 는 `git ls-tree --name-only` + `startswith` 필터 ---
🔴 **둘 다 git 의 「경로 포매팅 층」을 통과한 문자열을 받았다.** 그 층이 결함의 자리였다.
경로를 둘로 나눠도 **같은 층을 지나면 하나다.**

## 그래서 이 경로는 그 층을 **아예 안 지난다**

| | 첫 경로 (`out946_quotefix.py`) | **두 번째 경로 (이 파일)** |
|---|---|---|
| git 쪽 | `git ls-tree --name-only -z -c core.quotePath=false` --- 포매팅 층을 **쓰되 인용을 끈다** | 🔴 `git cat-file --batch` 로 **트리 객체 원 바이트**를 읽어 직접 파싱 --- 포매팅 층이 **없다** |
| 디스크 쪽 | `pathlib.Path.rglob` (str) | 🔴 `os.scandir(bytes)` --- **바이트로만** 훑는다 (str 디코딩이 없다) |
| 비교 공간 | `str` | 🔴 `bytes` |
| 계수 방식(러너 census) | `ast` 파싱 | 🔴 `tokenize` --- 문자열 토큰의 **줄 번호**로 센다 |

git 의 트리 객체는 `<모드> <이름>\\0<20바이트 sha>` 의 나열이고 **이름은 원 바이트**다 ---
인용이라는 개념 자체가 없다. 그래서 이 경로는 `core.quotepath` 가 무엇이든 **같은 답**을 낸다.
그것을 **실측으로 확인한다**(`quotepath` 를 켜고 끄고 두 번 돌린다).

    python3 runners/out946_recount.py        # → runners/out946_recount.json
"""
from __future__ import annotations

import datetime as dt
import hashlib
import io
import json
import os
import subprocess
import sys
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOTB = os.fsencode(str(ROOT))
OUT = ROOT / "runners" / "out946_recount.json"

CACHE_PREFIX = b"data/state/cache_"
PATH_TOKENS = ("ls-files", "ls-tree", "--name-only", "--name-status")
SAFE = ("-z", "core.quotepath=false", "core.quotePath=false")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _git(*a: str, quotepath: bool | None = None) -> bytes:
    pre = [] if quotepath is None else ["-c", "core.quotePath=%s" % str(quotepath).lower()]
    r = subprocess.run(["git", "-C", str(ROOT), *pre, *a], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError("git %s → %d · %s" % (a, r.returncode, r.stderr[:300]))
    return r.stdout


# ══════════════════════════════════ 가 · 트리 객체 원 바이트를 직접 파싱
def _parse_tree(payload: bytes) -> list[tuple[bytes, bytes, bool]]:
    """`<모드> <이름>\\0<20바이트 sha>` 의 나열. 🔴 이름은 **원 바이트**다."""
    out, i, n = [], 0, len(payload)
    while i < n:
        sp = payload.index(b" ", i)
        mode = payload[i:sp]
        nul = payload.index(b"\0", sp)
        name = payload[sp + 1:nul]
        oid = payload[nul + 1:nul + 21].hex().encode()
        out.append((name, oid, mode == b"40000"))
        i = nul + 21
    return out


def _cat_file(oids: list[bytes]) -> dict[bytes, bytes]:
    """`git cat-file --batch` --- 🔴 stdout 은 **바이너리**다. 문자열로 안 만든다."""
    p = subprocess.Popen(["git", "-C", str(ROOT), "cat-file", "--batch"],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    data, _ = p.communicate(b"\n".join(oids) + b"\n")
    res, i = {}, 0
    for _ in oids:
        nl = data.index(b"\n", i)
        oid, _typ, size = data[i:nl].split(b" ")
        res[oid] = data[nl + 1:nl + 1 + int(size)]
        i = nl + 1 + int(size) + 1
    return res


def tree_paths(rev: str, under: bytes) -> set[bytes]:
    """`rev` 의 끝 트리에서 `under` 아래의 **파일 경로 전량**(바이트)."""
    root_oid = _git("rev-parse", "%s^{tree}" % rev).strip()
    #: BFS --- 한 겹씩 `cat-file --batch` 로 통째 읽는다.
    layer = [(b"", root_oid)]
    files: set[bytes] = set()
    while layer:
        blobs = _cat_file([o for _, o in layer])
        nxt = []
        for prefix, oid in layer:
            for name, child, is_tree in _parse_tree(blobs[oid]):
                full = name if not prefix else prefix + b"/" + name
                if is_tree:
                    #: 🔴 가지치기 --- `under` 와 접두어가 겹칠 수 있는 가지만 내려간다
                    if full.startswith(under[:len(full)]) or full.startswith(under):
                        nxt.append((full, child))
                elif full.startswith(under):
                    files.add(full)
        layer = nxt
    return files


# ══════════════════════════════════ 나 · 디스크를 **바이트로** 훑는다
def disk_paths(under: bytes) -> set[bytes]:
    out: set[bytes] = set()
    stack = [ROOTB + b"/" + under]
    while stack:
        d = stack.pop()
        try:
            it = os.scandir(d)
        except (FileNotFoundError, NotADirectoryError):
            continue
        with it:
            for e in it:
                if e.is_dir(follow_symlinks=False):
                    stack.append(e.path)
                elif e.is_file(follow_symlinks=False):
                    out.add(e.path[len(ROOTB) + 1:])
    return out


# ══════════════════════════════════ 다 · census 재계수 (tokenize)
def recount_census(mine: set[str]) -> dict:
    """🔴 `ast` 가 아니라 `tokenize` --- 문자열 **토큰**을 줄 단위로 모아 센다.

    같은 답이 나오면 「자리 수」가 파서 선택에 안 걸린다는 뜻이다.
    자리 정의: **문자열 토큰이 경로 토큰을 담은 줄**을 논리 줄로 묶어, 그 묶음 안에
    안전 표지(`-z` · `core.quotePath=false`)가 있나 없나로 가른다.
    """
    py = [os.fsdecode(p) for p in
          _git("-c", "core.quotePath=false", "ls-files", "-z", "--", "*.py")
          .split(b"\0") if p]
    hits = []
    #: 🔴 **이 사이클이 만든 파일을 뺀다.** 두 경로의 「자리」 정의가 다르므로
    #: (첫 경로 = argv 로 건너가는 것만 · 이 경로 = 경로 토큰을 품은 문자열 뭉치)
    #: 946 자신의 파일에서는 두 수가 **원리상** 안 맞는다 --- 946 은 `PATH_TOKENS`
    #: 상수와 사유 문자열을 잔뜩 이고 있다. 🔴 **남의 파일에서 맞는지**가 이 대조의 물음이다.
    skipped = sorted(x for x in py if x in mine)
    for rel in sorted(x for x in py if x not in mine):
        try:
            src = (ROOT / rel).read_bytes()
            toks = list(tokenize.tokenize(io.BytesIO(src).readline))
        except (tokenize.TokenError, SyntaxError, OSError):
            continue
        #: 논리 줄 = 괄호 깊이가 0 으로 돌아올 때까지. 🔴 여기선 더 거칠게, **연속한
        #: 문자열 토큰 뭉치**를 한 자리로 본다(들어간 파서가 다르면 묶는 법도 달라야
        #: 「두 경로」다).
        run: list[tokenize.TokenInfo] = []
        groups = []
        for t in toks:
            if t.type == tokenize.STRING:
                run.append(t)
            elif t.type in (tokenize.NL, tokenize.NEWLINE, tokenize.COMMENT,
                            tokenize.INDENT, tokenize.DEDENT):
                continue
            elif t.type == tokenize.OP and t.string in ",[]()":
                continue
            else:
                if run:
                    groups.append(run); run = []
        if run:
            groups.append(run)
        for g in groups:
            vals = []
            for t in g:
                try:
                    v = json.loads(t.string) if t.string[0] in "\"'" and \
                        t.string[:3] not in ('"""', "'''") else None
                except Exception:
                    v = None
                vals.append(v if isinstance(v, str) else t.string.strip("\"'"))
            if not any(tok in vals for tok in PATH_TOKENS):
                continue
            #: 🔴 docstring 배제 --- 세 겹 따옴표 토큰이 섞이면 산문이다
            if any(t.string[:3] in ('"""', "'''") for t in g):
                continue
            safe = any(any(s in v for s in SAFE) for v in vals if isinstance(v, str))
            hits.append({"파일:줄": f"{rel}:{g[0].start[0]}", "인자": vals,
                         "안전": safe})
    raw = [h for h in hits if not h["안전"]]
    return {"검사": "다 · census 재계수 --- 🔴 `tokenize`(첫 경로는 `ast`)",
            "🔴 훑은 .py": len(py),
            "🔴 뺀 것(이 사이클이 만든 .py)": skipped,
            "🔴 실제로 훑은 .py(남의 것)": len(py) - len(skipped),
            "🔴 자리 수": len(hits),
            "🔴 날 것": len(raw),
            "날 것 목록": raw,
            "안전 목록": [h["파일:줄"] for h in hits if h["안전"]]}


# ══════════════════════════════════ main
def main() -> int:
    t0 = dt.datetime.now(dt.timezone.utc)
    under = b"data/state"

    tree = {p for p in tree_paths("HEAD", under) if p.startswith(CACHE_PREFIX)}
    disk = {p for p in disk_paths(under) if p.startswith(CACHE_PREFIX)}

    #: 🔴 **결함 공유 시험** --- `core.quotepath` 를 켜고 끄고 두 번 돌려 답이 같은지 본다.
    #: 첫 경로는 이 설정에 원리상 의존하고(끄기 때문에 옳다), 이 경로는 **의존하지 않아야** 한다.
    tree_q_on = {p for p in _tree_under_setting(True, under) if p.startswith(CACHE_PREFIX)}
    tree_q_off = {p for p in _tree_under_setting(False, under) if p.startswith(CACHE_PREFIX)}

    #: 첫 경로의 산출물과 견준다(파일에서 읽는다 --- 손 전사 금지)
    q = json.loads((ROOT / "runners" / "out946_quotefix.json").read_text(encoding="utf-8"))
    map_new = json.loads((ROOT / "data" / "state" / "obs_time946_cachemap.json")
                         .read_text(encoding="utf-8"))
    map_old = json.loads((ROOT / "data" / "state" / "obs_time945_cachemap.json")
                         .read_text(encoding="utf-8"))
    new_keys = {os.fsencode(k) for k in map_new["파일"]}
    old_keys = {os.fsencode(k) for k in map_old["파일"]}

    p1_cen = q["1 날 것 호출 전수"]
    #: 🔴 목록을 손으로 안 적는다 --- 첫 경로의 산출물에서 **읽는다**
    cen = recount_census(set(p1_cen["🔴 분모 ⓪ 이 사이클이 더한 .py(분모에서 가른다)"]))
    p1_sec2 = q["2 `215 → 0`"]

    secs = {
        "가 · 트리 객체 원 바이트": {
            "검사": "가 · `git cat-file --batch` 로 트리 객체를 직접 파싱 "
                  "(🔴 `--name-only` 를 안 쓴다 --- 포매팅 층이 없다)",
            "🔴 세는 명령": "git rev-parse HEAD^{tree} → git cat-file --batch (바이너리) → "
                        "`<모드> <이름>\\0<20바이트 sha>` 직접 파싱",
            "🔴 범위": "data/state/cache_* ", "🔴 트리": "HEAD 끝 트리(객체 DB)",
            "HEAD 트리 캐시 파일": len(tree),
            "디스크 캐시 파일": len(disk),
            "🔴 트리 − 디스크": len(tree - disk),
            "🔴 디스크 − 트리": len(disk - tree),
            "예시 다섯(트리)": sorted(os.fsdecode(x) for x in tree)[:5],
            "통과": tree == disk,
        },
        "나 · 🔴 결함 공유 시험": {
            "검사": "나 · 🔴 이 경로가 `core.quotepath` 에 의존하나 --- 켜고 끄고 두 번",
            "quotepath=true 로 센 수": len(tree_q_on),
            "quotepath=false 로 센 수": len(tree_q_off),
            "🔴 두 설정의 차(양방향)": [len(tree_q_on - tree_q_off),
                                len(tree_q_off - tree_q_on)],
            "🔴 뜻": ("차가 0 이면 이 경로는 그 설정을 **안 탄다** --- 945 의 두 경로가 "
                   "둘 다 탔던 층을 이 경로는 안 지난다는 실측"),
            "대조 --- 날 것 `ls-tree --name-only` 를 같은 두 설정으로": _raw_two_ways(),
            "통과": tree_q_on == tree_q_off == tree,
        },
        "다 · census 재계수": {
            **cen,
            "첫 경로(ast)가 낸 자리 수(남의 것)": p1_cen["🔴 분모 ③″ 남의 것"],
            "첫 경로(ast)가 낸 날 것": p1_cen["🔴 분모 ④ 날 것"],
            "첫 경로(ast)가 낸 의도적 날 것(남의 것)": 1,
            "⚠ 의도적 1 은 무엇인가": "runners/fiveprime902.py:178 --- ⑤′ 의 음성 대조. "
                              "나머지 셋은 946 자신의 파일이라 위에서 뺐다",
            "⚠ 분모를 맞춘다": ("이 경로는 `INTENTIONAL` 표를 안 본다 --- 그래서 「날 것」에 "
                        "⑤′ 의 음성 대조 자리가 **같이 들어간다**. 견줄 짝은 "
                        "`ast 날 것 + ast 의도적 날 것` 이다(조항 60)"),
            "🔴 두 파서가 같은가(자리 수 · 남의 것)":
                cen["🔴 자리 수"] == p1_cen["🔴 분모 ③″ 남의 것"],
            "🔴 두 파서가 같은가(날 것 + 의도적 · 남의 것)":
                cen["🔴 날 것"] == p1_cen["🔴 분모 ④ 날 것"] + 1,
            "통과": (cen["🔴 자리 수"] == p1_cen["🔴 분모 ③″ 남의 것"]
                   and cen["🔴 날 것"] == p1_cen["🔴 분모 ④ 날 것"] + 1)},
        "라 · 지도 대조": {
            "검사": "라 · 새 지도와 옛 지도를 **바이트 공간**에서 견준다",
            "새 지도 키": len(new_keys), "옛 지도 키": len(old_keys),
            "🔴 디스크 − 새 지도": len(disk - new_keys),
            "🔴 새 지도 − 디스크": len(new_keys - disk),
            "🔴 디스크 − 옛 지도": len(disk - old_keys),
            "🔴 옛 지도 − 디스크": len(old_keys - disk),
            "옛 지도 − 디스크 예시 다섯":
                sorted(os.fsdecode(x) for x in (old_keys - disk))[:5],
            "🔴 뜻": ("양쪽이 같은 수면 「없는 파일」이 아니라 **두 이름**이다(조항 61 ①). "
                   "945 는 한쪽만 실었다"),
            "통과": disk == new_keys and len(old_keys - disk) == len(disk - old_keys) > 0,
        },
        "마 · 첫 경로와 수 대조": {
            "검사": "마 · 첫 경로 산출물의 수를 **읽어서** 견준다(손 전사 금지)",
            "첫 경로 디스크 캐시": q["🔴 디스크 캐시 파일(분모)"],
            "이 경로 디스크 캐시": len(disk),
            "첫 경로 새 자 디스크−트리": p1_sec2["🔴 전 / 후"]["새 자 `디스크 − 트리`"],
            "이 경로 디스크−트리": len(disk - tree),
            "첫 경로 새 자 트리−디스크": p1_sec2["🔴 전 / 후"]["새 자 `트리 − 디스크`"],
            "이 경로 트리−디스크": len(tree - disk),
            "첫 경로 이스케이프된 키(945 지도)": p1_sec2["🔴 이스케이프된 키 수(945 지도)"],
            "이 경로 옛지도−디스크": len(old_keys - disk),
            "🔴 어긋난 항목": [k for k, (a, b) in {
                "디스크 캐시": (q["🔴 디스크 캐시 파일(분모)"], len(disk)),
                "디스크−트리": (p1_sec2["🔴 전 / 후"]["새 자 `디스크 − 트리`"], len(disk - tree)),
                "트리−디스크": (p1_sec2["🔴 전 / 후"]["새 자 `트리 − 디스크`"], len(tree - disk)),
                "215": (p1_sec2["🔴 이스케이프된 키 수(945 지도)"], len(old_keys - disk)),
            }.items() if a != b],
            "통과": (q["🔴 디스크 캐시 파일(분모)"] == len(disk)
                   and p1_sec2["🔴 전 / 후"]["새 자 `디스크 − 트리`"] == len(disk - tree)
                   and p1_sec2["🔴 전 / 후"]["새 자 `트리 − 디스크`"] == len(tree - disk)
                   and p1_sec2["🔴 이스케이프된 키 수(945 지도)"] == len(old_keys - disk)),
        },
    }
    secs["바 · 🔴 커밋된 실물과 대조"] = _committed_check([
        "runners/out946_quotefix.json", "data/state/obs_time946_cachemap.json",
        "data/state/obs_time945_cachemap.json", "runners/out946_quotefix.py",
        "lab/keyspace.py"])
    doc = {
        "무엇": "노트 946 두 번째 경로 --- 🔴 첫 경로와 결함을 공유하지 않는다",
        **secs,
        "🔴 절 수(분모)": len(secs),
        "🔴 `통과` 키를 가진 절": sum(1 for v in secs.values() if "통과" in v),
        "🔴 실패한 절": [k for k, v in secs.items() if v.get("통과") is not True],
        "통과": all(v.get("통과") is True for v in secs.values()),
        "시각(UTC · 시작)": t0.isoformat(timespec="seconds"),
        "시각(UTC · 끝)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "🔴 코드 sha256(이게 자다)": {
            "runners/out946_recount.py": sha(Path(__file__).resolve())},
        "🔴 입력 산출물 sha256": {
            r: sha(ROOT / r) for r in
            ("runners/out946_quotefix.json", "data/state/obs_time946_cachemap.json",
             "data/state/obs_time945_cachemap.json")},
        "⚠ git HEAD(시작 시점 · 판정에 쓰지 마라)": _git("rev-parse", "HEAD").decode().strip(),
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print("→", OUT.relative_to(ROOT), "· 통과", doc["통과"], "· 실패", doc["🔴 실패한 절"])
    return 0


def _committed_check(rels: list[str]) -> dict:
    """🔴 **내 입력이 커밋된 실물과 같은가** --- 945 C3 가 걸린 자리.

    945 의 `out945_verify.json` 은 입력 `out945_obstime.json` 의 sha 로
    `0bd2728e09ab…` 를 적었는데 **커밋된 파일의 실제 sha 는 `a9284b3574…`** 였다 ---
    검증기가 검증 대상보다 **2분 24초 먼저** 돌았고 그때 해싱한 파일은 저장소에 없다.
    🔴 그래서 여기서는 **작업 트리 sha 와 `git show HEAD:<경로>` 의 sha 를 둘 다 계산해
    견준다.** 손으로 적은 `--ran` 선언이 아니라 **바이트 대조**다.
    """
    rows = {}
    for rel in rels:
        w = sha(ROOT / rel) if (ROOT / rel).exists() else "🔴 작업 트리에 없다"
        r = subprocess.run(["git", "-C", str(ROOT), "cat-file", "blob",
                            "HEAD:%s" % rel], capture_output=True)
        c = (hashlib.sha256(r.stdout).hexdigest() if r.returncode == 0
             else "🔴 HEAD 에 없다(아직 안 커밋됐다 --- 「없다」가 아니라 「아직」)")
        rows[rel] = {"작업 트리 sha256": w, "커밋된 sha256": c, "같은가": w == c}
    same = [k for k, v in rows.items() if v["같은가"]]
    return {"검사": "바 · 🔴 내 입력이 **커밋된 실물**과 같은가(945 C3)",
            "🔴 분모(견준 파일)": len(rows),
            "🔴 같은 것": len(same),
            "🔴 다른 것": [k for k, v in rows.items() if not v["같은가"]],
            "파일별": rows,
            "🔴 뜻": ("「아직 안 커밋됐다」와 「내용이 다르다」는 둘이다(조항 59). "
                   "앞의 것이면 커밋한 뒤 이 러너를 **다시** 돌려라"),
            "통과": len(same) == len(rows)}


def _tree_under_setting(quotepath: bool, under: bytes) -> set[bytes]:
    os.environ["GIT_CONFIG_COUNT"] = "1"
    os.environ["GIT_CONFIG_KEY_0"] = "core.quotePath"
    os.environ["GIT_CONFIG_VALUE_0"] = "true" if quotepath else "false"
    try:
        return tree_paths("HEAD", under)
    finally:
        for k in ("GIT_CONFIG_COUNT", "GIT_CONFIG_KEY_0", "GIT_CONFIG_VALUE_0"):
            os.environ.pop(k, None)


def _raw_two_ways() -> dict:
    """🔴 음성 대조 --- **날 것**은 그 설정을 탄다는 것을 같은 자리에서 보인다."""
    on = {x for x in _git("ls-tree", "-r", "--name-only", "HEAD", "--", "data/state",
                          quotepath=True).split(b"\n") if x.startswith(CACHE_PREFIX)}
    off = {x for x in _git("ls-tree", "-r", "--name-only", "HEAD", "--", "data/state",
                           quotepath=False).split(b"\n") if x.startswith(CACHE_PREFIX)}
    return {"quotepath=true": len(on), "quotepath=false": len(off),
            "🔴 차": len(off - on),
            "🔴 뜻": "날 것은 설정을 **탄다**. 그래서 이것이 음성 대조가 된다"}


if __name__ == "__main__":
    raise SystemExit(main())
