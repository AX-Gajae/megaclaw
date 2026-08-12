# -*- coding: utf-8 -*-
"""게이트 940 — **비교가능성 관문의 배선을 기계로 잠근다.**

🔴 이것이 사전등록 §4 판정규칙의 **③ 조건**이다: *「새 소비자가 생겼을 때 붉어지는 기계 검사」*.
`state/ratio940.CONSUMERS` 명부와 **커밋된 트리 실측**을 대조해서, 명부 밖의 새 소비자가
생기면 그 절이 붉어진다.

🔴 규약 60 — 전수 계수는 **① 세는 명령 ② 범위 ③ 어느 트리** 셋을 산출물에 박는다.
**인덱스와 작업 트리를 섞어 읽지 않는다** — 이 러너는 `git ls-tree`/`git show` 로
**한 rev 의 트리만** 읽는다. 작업 트리는 **별도 절에서 따로** 잰다(섞지 않는다).

🔴 규약 48 부칙 — 모든 절이 `"통과"` **키**를 갖는다(⑤′ 2절이 `git grep -lF -e '"통과":'`
로 게이트 명부를 뽑는다). 금지어는 *결론 문장*에만 걸린다.

사용:
    python3 runners/gate940_wiring.py [--rev HEAD]
"""
from __future__ import annotations

import argparse
import ast
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lab import keyspace as ks                                 # noqa: E402
from state import ratio940                                    # noqa: E402

OUT = ROOT / "runners/out940_gate.json"
NEEDLE = "COMPARABLE_REL"
GATE_KEY_MARK = "통과"


def git(*a: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *a],
                          capture_output=True, text=True).stdout


#: 🔴 rev 의 트리를 **한 번에** 풀어 놓는다 — `git show` 를 파일마다 부르면 1,600 회 프로세스가
#: 뜬다. 푸는 곳은 scratchpad 이고 **작업 트리를 안 건드린다**(규약 60 — 안 섞는다).
SCRATCH = Path("/private/tmp/claude-501/-Users-ax-world-model/"
               "511dc308-36bf-409d-9afe-b82a8bb5d7ae/scratchpad/g940tree")
_EXPORTED: dict = {}


def export(rev: str) -> Path:
    if rev in _EXPORTED:
        return _EXPORTED[rev]
    sha = git("rev-parse", rev).strip()
    d = SCRATCH / sha
    if not (d / ".ok").exists():
        d.mkdir(parents=True, exist_ok=True)
        p1 = subprocess.Popen(["git", "-C", str(ROOT), "archive", sha],
                              stdout=subprocess.PIPE)
        subprocess.run(["tar", "-x", "-C", str(d)], stdin=p1.stdout, check=True)
        p1.wait()
        (d / ".ok").write_text("ok")
    _EXPORTED[rev] = d
    return d


def tree_py_files(rev: str) -> list:
    raw = git("ls-tree", "-r", "-z", "--name-only", rev)
    return sorted(f for f in raw.split("\0") if f.endswith(".py"))


def blob(rev: str, path: str) -> str:
    p = export(rev) / path
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except (OSError, IsADirectoryError):
        return ""


# ══════════════════════════════════════════════ 1 · 소비자 명부 대조
def importers(rev: str, files: list) -> dict:
    """🔴 **ast 로** `COMPARABLE_REL` 을 import 하는 .py 를 전량 뽑는다(문자열 검색 아님)."""
    hit, unparsable = {}, []
    for f in files:
        src = blob(rev, f)
        if NEEDLE not in src:
            continue
        try:
            tree = ast.parse(src)
        except SyntaxError as e:
            unparsable.append({"파일": f, "사유": str(e)})
            continue
        names = []
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom):
                for al in n.names:
                    if al.name == NEEDLE:
                        names.append({"모듈": n.module, "줄": n.lineno})
        if names:
            hit[f] = names
    return {"소비자": hit, "🔴 ast 로 못 읽은 파일": unparsable}


def mentions(rev: str, exts: tuple) -> dict:
    """낱말이 나오는 **모든** 파일 — import 와 **다른 분모**다(조항 60)."""
    raw = git("ls-tree", "-r", "-z", "--name-only", rev)
    files = [f for f in raw.split("\0") if f.endswith(exts)]
    per = {}
    for f in files:
        src = blob(rev, f)
        if NEEDLE in src:
            per[f] = sum(1 for ln in src.split("\n") if NEEDLE in ln)
    return {"파일 수": len(per), "줄 수 합": sum(per.values()), "파일별": per,
            "🔴 이 분모는 import 분모와 다르다": "낱말 언급 ⊇ import"}


def part1(rev: str, files: list) -> dict:
    imp = importers(rev, files)
    found = set(imp["소비자"])
    registered = set(ratio940.CONSUMERS)
    새로 = sorted(found - registered)
    사라진 = sorted(registered - found)
    return {
        "무엇": "🔴 `COMPARABLE_REL` 소비자 명부 대조 — 명부 밖의 새 소비자가 생기면 붉어진다",
        "🔴 세는 명령": f"git ls-tree -r -z --name-only {rev} → .py 만 → "
                  f"git archive {rev} | tar -x → ast.ImportFrom(name=='{NEEDLE}')",
        "🔴 범위": ".py **만** · 저장소 전량 · 경로 제한 없음",
        "🔴 어느 트리": f"{rev} = {git('rev-parse', rev).strip()} (커밋된 트리 하나 · "
                  "🔴 인덱스·작업 트리와 **안 섞었다**)",
        "실측 소비자": imp["소비자"],
        "실측 소비자 수": len(found),
        "명부 소비자 수": len(registered),
        "🔴 명부에 없는 새 소비자": 새로,
        "명부에 있는데 실측에 없는 것": 사라진,
        "ast 로 못 읽은 파일": imp["🔴 ast 로 못 읽은 파일"],
        "통과": bool(not 새로 and not 사라진 and not imp["🔴 ast 로 못 읽은 파일"]),
        "🔴 붉으면 무엇을 하나": "새 소비자를 `state/ratio940.CONSUMERS` 에 갈래와 증거와 함께 "
                        "등록하거나, 그 소비자가 옛 상수 대신 `ratio940.sensitivity_ratio` 를 "
                        "쓰게 고친다. **등록 없이 넘어갈 길은 없다**",
    }


# ══════════════════════════════════════════════ 2 · 분기 자리 회계
def branch_sites(rev: str, files: list) -> dict:
    """관문 결과가 **조건**으로 쓰인 자리를 ast 로 전량 뽑고 세 갈래로 가른다."""
    IF, COMP, TERN = [], [], []
    for f in files:
        src = blob(rev, f)
        if GATE_KEY_MARK not in src:
            continue
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for n in ast.walk(tree):
            tests = []
            if isinstance(n, ast.If):
                tests = [(n.test, IF)]
            elif isinstance(n, ast.IfExp):
                tests = [(n.test, TERN)]
            elif isinstance(n, (ast.ListComp, ast.SetComp, ast.DictComp,
                                ast.GeneratorExp)):
                tests = [(t, COMP) for g in n.generators for t in g.ifs]
            for t, bucket in tests:
                try:                      # 🔴 3.9 의 get_source_segment 는 다바이트에서 깨진다
                    seg = ast.unparse(t)
                except Exception:         # noqa: BLE001
                    seg = ""
                if GATE_KEY_MARK in seg and ("비교가능성" in seg or "cmp" in seg
                                             or "cm[" in seg):
                    bucket.append({"파일": f, "줄": t.lineno, "조건식": seg.strip()})
    return {"if 문": IF, "내포 조건": COMP, "삼항": TERN}


def part2(rev: str, files: list) -> dict:
    b = branch_sites(rev, files)
    ifs = b["if 문"]
    ifs_files = sorted({x["파일"] for x in ifs})
    return {
        "무엇": "🔴 관문 결과가 **조건**으로 쓰인 자리 전량 — 세 갈래로 가른다",
        "🔴 세는 명령": f"git archive {rev} | tar -x → ast.walk → If/IfExp/comprehension.ifs 의 "
                  f"test 를 `ast.unparse` 로 떠서 '{GATE_KEY_MARK}' 를 찾는다",
        "🔴 범위": ".py **만** · 저장소 전량",
        "🔴 어느 트리": f"{rev} = {git('rev-parse', rev).strip()}",
        "🔴 갈래 ㄱ — `if` 문 (판정 갈래를 고른다)": ifs,
        "갈래 ㄴ — 내포 조건 (부분집합을 만든다)": b["내포 조건"],
        "갈래 ㄷ — 삼항": b["삼항"],
        "🔴 갈래 ㄱ 의 파일": ifs_files,
        "🔴 갈래 ㄱ 이 한 파일뿐인가(사전등록 P2)": len(ifs_files) == 1,
        "통과": len(ifs_files) <= 1,
        "🔴 붉으면 무엇을 하나": "관문이 판정 갈래를 고르는 자리가 둘 이상이면 **각 자리마다** "
                        "「이 r 로 무엇을 갈랐나」를 산출물에 적어야 한다(규약 61 의무 필드 6)",
    }


# ══════════════════════════════════════════════ 3 · 기본 인자 동결
def part3() -> dict:
    """🔴 `comparability` 의 `rel_thr` 기본값은 **import 시점에 동결**된다.

    그래서 `perm922.COMPARABLE_REL = X` 를 나중에 넣어도 관문은 옛 값을 계속 쓴다.
    **이 게이트는 그 사실을 실측으로 신고한다** — 고치라는 게 아니라 **모르고 지나가지 말라는** 것.
    """
    from state import perm922
    kd = perm922.comparability.__kwdefaults__ or {}
    frozen = kd.get("rel_thr")
    const0 = perm922.COMPARABLE_REL
    perm922.COMPARABLE_REL = -12345.0            # 심는다
    kd_after = (perm922.comparability.__kwdefaults__ or {}).get("rel_thr")
    perm922.COMPARABLE_REL = const0              # 되돌린다
    return {
        "무엇": "🔴 상수를 바꿔 넣어도 관문이 옛 값을 쓰는가 — **심어서 확인**",
        "import 직후 상수": const0,
        "함수 기본값 rel_thr": frozen,
        "상수를 −12345.0 으로 심은 뒤의 기본값": kd_after,
        "🔴 상수를 바꿨더니 기본값이 따라 바뀌었나": kd_after != frozen,
        "🔴 뜻": "따라 안 바뀌면 — **상수는 신고용이고 관문이 쓰는 수는 따로 동결돼 있다**. "
              "그러면 「상수를 고쳐서 문턱을 바꾼다」는 길은 **원리상 없다**",
        "복원됐나": perm922.COMPARABLE_REL == const0,
        "통과": bool(kd_after == frozen and perm922.COMPARABLE_REL == const0),
        "⚠ 이 절의 「통과」의 뜻": "🔴 **「좋다」가 아니다.** 동결이 실측대로 재현됐다는 뜻이다 — "
                        "동결 자체는 이 저장소의 결함이고, 그것을 **드러내 놓는 것**이 이 절의 일이다",
    }


# ══════════════════════════════════════════════ 4 · 새 자의 자가검사
def part4() -> dict:
    ok = ratio940.sensitivity_ratio(
        "자가시험(합성)", rel_values=[0.01, 0.02, 0.03], G=0.4, cr=12.0,
        L_used=2.0, L_bca_hi=2.0, used_for="자가시험이라 아무것도 안 갈랐다")
    r = ok["🔴🔴 r = m · L_used · cr / G"]
    expect = 0.03 * 2.0 * 12.0 / 0.4
    miss = ratio940.sensitivity_ratio(
        "자가시험(입력 결손)", rel_values=[0.01], G=None, cr=12.0, L_used=1.0,
        used_for="자가시험이라 아무것도 안 갈랐다")
    return {
        "무엇": "새 자가 ① 공식대로 계산하나 ② 결손을 「못 잰다」로 내나 ③ 금지어를 안 쓰나",
        "합성 r": r, "손 계산": expect, "🔴 같은가": abs(r - expect) < 1e-12,
        "결손 입력의 답": miss.get("🔴 못 잰다"),
        "🔴 결손을 「못 잰다」로 냈나": "🔴 못 잰다" in miss,
        "금지어 자가검사": ok["🔴 금지어 자가검사(「통과」·「검정력 0」)"],
        "폐기한 신고 확인": ok["🔴 폐기한 신고를 안 넣었나"],
        "통과": bool(abs(r - expect) < 1e-12
                   and "🔴 못 잰다" in miss
                   and ok["🔴 금지어 자가검사(「통과」·「검정력 0」)"] == "없다"
                   and not any(ok["🔴 폐기한 신고를 안 넣었나"].values())),
    }


# ══════════════════════════════════════════════ 5 · 작업 트리 (섞지 않고 따로)
def part5(rev: str) -> dict:
    # 🔴🔴 **949 수리 (티처 #88 C1 · 순㉯)** --- 여기는 947~948 이 「원리상 못 고친다(㉮)」로
    #    분류한 자리였다. 근거는 「이 파일의 sha 를 산출물이 인용한다」였는데 그 인용은
    #    **도장**이지 **대조**가 아니다(HEAD 전량에서 이 파일을 대조하는 `.py` 는 **0**).
    #    막는 것이 아무것도 없으므로 **오늘 고친다** --- 정본 판독기를 지난다.
    dirty = [x for x in sorted(ks.git_paths("status", "--porcelain", root=ROOT))
             if x.strip()]
    return {
        "무엇": "🔴 작업 트리는 **커밋된 트리와 안 섞는다**(규약 60) — 여기서 따로 잰다",
        "git status --porcelain 줄 수": len(dirty),
        "목록": dirty,
        "🔴 위 절들이 읽은 트리": f"{rev} = {git('rev-parse', rev).strip()}",
        "통과": len(dirty) == 0,
        "⚠ 붉어도 위 절의 계수는 안 흔들린다": "위 절은 `git show <rev>:` 로만 읽었다 — "
                                "작업 트리가 더러워도 그 수는 rev 의 수다",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rev", default="HEAD")
    a = ap.parse_args()
    rev = a.rev
    t0 = dt.datetime.now(dt.timezone.utc)
    files = tree_py_files(rev)

    out = {
        "게이트": "940 — 비교가능성 관문의 배선 잠금",
        "사전등록": "docs/prereg_940_ratio.md §4 판정규칙 ③",
        "🔴 rev": git("rev-parse", rev).strip(),
        "🔴 트리의 .py 수(분모)": len(files),
        "코드 sha256": {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest()
                      for f in ["state/ratio940.py", "runners/gate940_wiring.py"]},
        "1 소비자 명부 대조": part1(rev, files),
        "2 분기 자리 회계": part2(rev, files),
        "3 기본 인자 동결": part3(),
        "4 새 자의 자가검사": part4(),
        "5 작업 트리(따로)": part5(rev),
        "낱말 언급(병기 · import 와 **다른 분모**)": mentions(rev, (".py", ".md", ".json")),
        "시작 UTC": t0.isoformat(),
    }
    secs = [k for k in out if k[0].isdigit()]
    out["🔴 절별 판정"] = {k: out[k]["통과"] for k in secs}
    out["🔴 전체"] = {
        "절 수(분모)": len(secs),
        "🔴 붉은 절": [k for k in secs if not out[k]["통과"]],
        "통과": all(out[k]["통과"] for k in secs),
    }
    out["끝 UTC"] = dt.datetime.now(dt.timezone.utc).isoformat()
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out["🔴 전체"], ensure_ascii=False))
    print(json.dumps(out["🔴 절별 판정"], ensure_ascii=False))


if __name__ == "__main__":
    main()
