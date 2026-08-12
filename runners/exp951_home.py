# -*- coding: utf-8 -*-
"""[탐색] 951 — **「기록 쪽의 거처」로 가른다**(티처 #90 물음 ②).

🔴 **레인 [탐색] · 판정 안 함.** 여기 나온 수는 노트 951 의 결론·원장 표제·커밋/PR
제목에 **안 들어간다**(`docs/루프.md` 규칙 1).

950 탐색은 한 홉까지 넓히면 비교 자리가 **7 → 21** 이 된다고만 셌고, 갈래는 **눈으로**
넷을 적었다. 티처 #90 은 그중 셋째(`general853.py:83`·`era870.py:84`·`gap869.py:44` ---
「기록된 sha」가 **소스 상수**)가 진짜 물음이라 했다. 949 의 `CHECK_CRITERIA` 는
**기록 쪽이 산출물에 있다**고 전제한다. 🔴 **소스 상수로 박힌 지문은 소스를 고치면 같이
고쳐지므로 도장보다도 약하다.**

그래서 21 자리를 **거처**로 가른다(자로 --- 눈이 아니라):

  ① 산출물의 sha(대조)  ② rev 기준  ③ **소스 상수**(자기충족)
  ④ 파일과 무관(결정성 검사)  ⑤ 거짓 양성

돌리기::

    python3 -m runners.exp951_home
"""
import ast
import json
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lab import gitcall as gc                                    # noqa: E402
from runners.exp950_onehop import _assign_map, _fresh_onehop     # noqa: E402

OUT = ROOT / "runners/exp951_home.json"
TREE = "HEAD"

#: 지문처럼 보이는 소스 리터럴 --- 16진 8자 이상.
HEXLIT = re.compile(r"^[0-9a-f]{8,64}$")

#: 「다른 rev 의 내용」을 꺼내는 꼴.
REV_TOKENS = ("cat-file", "ls-tree", "git show", '"show"', "'show'", "HEAD:")


def _amap_tuple(t: ast.AST) -> dict:
    """🔴 **950/951 의 `_assign_map` 은 튜플 대입을 못 본다.**

    `TARGET, FP852 = 0.2969, "adb00d2827b0"` 꼴에서 `FP852` 가 이름 표에 안 들어간다.
    ⚠ **이 넓히기는 사후다** --- 티처가 이름으로 준 셋 중 둘이 `⑥ 못 갈랐다` 로 떨어진
    까닭을 눈으로 확인한 **뒤에** 넣었다. [탐색] 레인이라 판정에 안 쓰고, **좁은 자의 수와
    나란히** 싣는다.
    """
    m = _assign_map(t)
    for n in ast.walk(t):
        if isinstance(n, ast.Assign):
            for tg in n.targets:
                if isinstance(tg, ast.Tuple) and isinstance(n.value, ast.Tuple) \
                        and len(tg.elts) == len(n.value.elts):
                    for e, v in zip(tg.elts, n.value.elts):
                        if isinstance(e, ast.Name):
                            m.setdefault(e.id, []).append(v)
    return m


def _hexish(node, amap) -> bool:
    """이 쪽이 **소스에 박힌 지문 상수**인가(한 홉까지)."""
    cands = [node]
    for x in ast.walk(node):
        if isinstance(x, ast.Name):
            cands += amap.get(x.id, [])
    for c in cands:
        for y in ast.walk(c):
            if isinstance(y, ast.Constant) and isinstance(y.value, str) \
                    and HEXLIT.match(y.value.strip().lower()):
                return True
    return False


def _cannot_be_sha(node) -> bool:
    """이 쪽은 **지문일 수 없다** --- 숫자/불리언 상수이거나 ``len(...)`` 꼴."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float, bool)):
        return True
    if isinstance(node, ast.Call) and getattr(node.func, "id", None) in ("len", "int", "abs"):
        return True
    return False


def _reads_file(node, amap) -> bool:
    """이 쪽의 sha 호출이 **파일**을 먹나(경로 꼴이 인자에 있나)."""
    cands = [node]
    for x in ast.walk(node):
        if isinstance(x, ast.Name):
            cands += amap.get(x.id, [])
    for c in cands:
        for y in ast.walk(c):
            if isinstance(y, ast.Name) and y.id in ("ROOT", "Path", "p", "f", "fp"):
                return True
            if isinstance(y, ast.Attribute) and y.attr in (
                    "read_bytes", "read_text", "open", "resolve"):
                return True
            if isinstance(y, ast.Constant) and isinstance(y.value, str) and (
                    "/" in y.value or y.value.endswith((".py", ".json", ".npz", ".md"))):
                return True
    return False


def scan() -> dict:
    srcs = gc._head_sources(ROOT, TREE)
    chk = gc.checkers(ROOT, TREE)
    site_keys = {r["파일:줄"] for r in chk["대조 자리"]}
    rev_keys = {r["파일:줄"] for r in chk[
        "🔴 이 자로 안 센 갈래(rev 기준 비교 · 기록된 상수와 안 견준다)"]["자리"]}

    rows, per = {}, Counter()
    for rel, src in sorted(srcs.items()):
        try:
            t = ast.parse(src)
        except SyntaxError:
            continue
        amap = _assign_map(t)
        amap_w = _amap_tuple(t)          # 🔴 튜플 대입까지 넓힌 자(사후 · 나란히 싣는다)
        lines = src.split("\n")
        for n in ast.walk(t):
            if not isinstance(n, ast.Compare):
                continue
            if not any(isinstance(o, (ast.Eq, ast.NotEq)) for o in n.ops):
                continue
            side = [n.left] + list(n.comparators)
            if not any(_fresh_onehop(s, amap) for s in side):
                continue
            key = "%s:%d" % (rel, n.lineno)
            txt = lines[n.lineno - 1].strip()[:160]
            src_head = "\n".join(lines[max(0, n.lineno - 6):n.lineno])
            # ── 거처를 정한다(순서가 규칙이다) ────────────────────────
            if key in site_keys:
                home = "① 산출물의 sha(대조)"
            elif key in rev_keys:
                home = "② rev 기준"
            elif any(_cannot_be_sha(s) for s in side):
                home = "⑤ 거짓 양성 --- 한쪽이 지문일 수 없는 꼴(`len`/수 상수)"
            elif any(_hexish(s, amap) for s in side):
                home = "🔴 ③ 소스 상수(자기충족 --- 도장보다도 약하다)"
            elif any(_hexish(s, amap_w) for s in side):
                home = "🔴 ③ 소스 상수(🔴 **튜플 대입까지 넓혀야 보인다**)"
            elif any(w in src_head for w in REV_TOKENS):
                home = "② rev 기준"
            elif not any(_reads_file(s, amap) for s in side):
                home = "④ 파일과 무관(결정성 검사)"
            else:
                home = "🔴 ⑥ 못 갈랐다 --- 「없다」가 아니다(조항 59)"
            rows[key] = {"거처": home, "줄": txt}
            per[home] += 1
    return {"자리": rows, "거처별": dict(per), "훑은 .py": len(srcs),
            "지금 `checkers()` 의 대조 자리": len(site_keys),
            "지금 `checkers()` 의 rev 갈래": len(rev_keys)}


def main() -> None:
    if OUT.exists():
        OUT.unlink()
    t0 = time.time()
    s = scan()
    #: 티처 #90 이 이름으로 지목한 셋 --- 정말 ③ 으로 가나
    named = ["runners/general853.py:83", "runners/era870.py:84", "runners/gap869.py:44"]
    got = {k: s["자리"].get(k, {}).get("거처", "🔴 이 자리가 안 잡혔다") for k in named}
    res = {
        "무엇": "[탐색] 951 --- 한 홉 비교 자리를 **「기록 쪽의 거처」**로 가른다",
        "🔴 레인": ("**[탐색] · 판정 안 함.** 이 수는 노트 951 의 결론·원장 표제·"
                 "커밋/PR 제목에 **안 들어간다**(규칙 1)"),
        "읽은 트리": "🔴 **HEAD** 하나(`git ls-tree` + `cat-file --batch`)",
        "🔴 분모 ① 훑은 `.py`": s["훑은 .py"],
        "🔴 분모 ② 한 홉 비교 자리 수": len(s["자리"]),
        "🔴 거처별 수": s["거처별"],
        "🔴 티처 #90 이 이름으로 지목한 셋": got,
        "자리별": s["자리"],
        "지금 자의 분해": {"대조 자리": s["지금 `checkers()` 의 대조 자리"],
                    "rev 갈래": s["지금 `checkers()` 의 rev 갈래"]},
        "🔴 이 자의 한계(안 한 것)": [
            "**판정을 안 한다** --- ㉮ 가 몇이 되는지 여기서 안 센다",
            "거처를 정하는 순서가 **규칙**이다. ① ② 는 `checkers()` 에게 물었고 "
            "③ ④ ⑤ 는 **이 파일의 자**다 --- 자가 다르면 수가 달라진다",
            "🔴 **`⑥ 못 갈랐다`** 는 「없다」가 아니라 **못 갈랐다**이다",
            "소스 상수가 **언제 박혔는지**(사람이 손으로 쳤나, 러너가 찍었나)는 안 봤다",
        ],
        "초": round(time.time() - t0, 1),
        "시각(UTC · 끝)": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "🔴 코드 sha256(이게 자다)": {
            "runners/exp951_home.py": gc.hashlib.sha256(
                Path(__file__).read_bytes()).hexdigest(),
        },
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "자리별"},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
