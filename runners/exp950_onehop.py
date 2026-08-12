# -*- coding: utf-8 -*-
"""[탐색] 950 — **자가 조용히 하나를 삼킨다**: 「한 홉 변수」와 「집합으로 눌린 자리」.

🔴 **판정이 아니다**(`docs/루프.md` 레인 표 · 규칙 1). 여기서 나온 어떤 수도
이 사이클의 결론·원장 표제·커밋/PR 제목에 **안 들어간다.** 다음 사이클의 **후보**다.

두 갈래를 잰다 --- 티처 #89 2순위와 티처 #88 M4 는 **한 병**이다:

* **ㄱ 한 홉 변수** --- `gc._side_fresh` 는 「비교의 한쪽에 sha 호출이 **직접** 있어야」
  한다. `w = sha(...)` 로 **한 번 거치면 못 본다.** 그래서
  `runners/out946_recount.py:339-341` 이 **sites 에도 revonly 에도 안 들어가고 조용히
  사라진다**(티처 #89 C2). **한 홉까지 넓히면 무엇이 더 들어오는가**를 센다.
* **ㄴ 집합으로 눌린 자리** --- 호출 자리 수와 `|자 A|` 가 다르다(티처 #88 M4).
  **같은 줄에 둘이면 하나로 눌린다.**

돌리기::

    python3 -m runners.exp950_onehop
"""
import ast
import hashlib
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lab import gitcall as gc                                     # noqa: E402

OUT = ROOT / "runners/exp950_onehop.json"
TREE = "HEAD"
#: 티처 #89 C2 가 지목한 자리 --- 여기 들어오는지 본다.
TARGET = "runners/out946_recount.py"


def _assign_map(t: ast.AST) -> dict:
    """이름 → 그 이름에 대입된 값 노드들(한 홉)."""
    m: dict = {}
    for n in ast.walk(t):
        if isinstance(n, ast.Assign):
            for tg in n.targets:
                if isinstance(tg, ast.Name):
                    m.setdefault(tg.id, []).append(n.value)
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) \
                and n.value is not None:
            m.setdefault(n.target.id, []).append(n.value)
        elif isinstance(n, ast.NamedExpr) and isinstance(n.target, ast.Name):
            m.setdefault(n.target.id, []).append(n.value)
    return m


def _fresh_onehop(node, amap: dict) -> bool:
    """🔴 넓힌 자 --- 이 쪽이 sha 호출을 **직접** 담거나, **한 홉 앞의 대입**이 담나."""
    if gc._side_fresh(node):
        return True
    for x in ast.walk(node):
        if isinstance(x, ast.Name):
            for v in amap.get(x.id, []):
                if gc._side_fresh(v):
                    return True
    return False


def scan() -> dict:
    srcs = gc._head_sources(ROOT, TREE)
    now, wide = set(), set()
    wide_rows, per_file = {}, Counter()
    for rel, src in sorted(srcs.items()):
        try:
            t = ast.parse(src)
        except SyntaxError:
            continue
        amap = _assign_map(t)
        lines = src.split("\n")
        for n in ast.walk(t):
            if not isinstance(n, ast.Compare):
                continue
            if not any(isinstance(o, (ast.Eq, ast.NotEq)) for o in n.ops):
                continue
            side = [n.left] + list(n.comparators)
            key = "%s:%d" % (rel, n.lineno)
            if any(gc._side_fresh(s) for s in side):
                now.add(key)
            if any(_fresh_onehop(s, amap) for s in side):
                wide.add(key)
                if key not in now:
                    wide_rows[key] = lines[n.lineno - 1].strip()[:160]
                    per_file[rel] += 1
    return {"지금 자": now, "넓힌 자": wide, "새로 들어온 것": wide_rows,
            "파일별": per_file, "훑은 .py": len(srcs)}


def sec_a() -> dict:
    s = scan()
    chk = gc.checkers(ROOT, TREE)
    site_keys = {r["파일:줄"] for r in chk["대조 자리"]}
    rev_keys = {r["파일:줄"] for r in chk["🔴 이 자로 안 센 갈래(rev 기준 비교 · 기록된 상수와 안 견준다)"]["자리"]}
    new = s["새로 들어온 것"]
    tgt = sorted(k for k in new if k.startswith(TARGET + ":"))
    return {
        "무엇": "ㄱ 🔴 「한 홉 변수」까지 넓히면 무엇이 더 들어오나",
        "읽은 트리": "🔴 **HEAD**(`git ls-tree` + `cat-file --batch`) --- 한 트리만 읽는다",
        "🔴 훑은 `.py`(분모)": s["훑은 .py"],
        "🔴 지금 자가 보는 비교 자리": len(s["지금 자"]),
        "🔴 한 홉까지 넓히면": len(s["넓힌 자"]),
        "🔴 새로 들어오는 자리 수": len(new),
        "그중 `%s`" % TARGET: tgt or "🔴 없다",
        "🔴 티처 #89 C2 의 자리가 들어오나": bool(tgt),
        "새로 들어오는 자리(전량)": new,
        "파일별 새 자리 수": dict(s["파일별"]),
        "⚠ 지금 자의 분해(대조로 세느냐 rev 로 세느냐는 **다음 사이클**)": {
            "`checkers()` 의 대조 자리": len(site_keys),
            "`checkers()` 의 rev 갈래": len(rev_keys),
            "🔴 새 자리 중 지금 대조 자리와 겹치는 것": len(set(new) & site_keys),
            "🔴 새 자리 중 지금 rev 갈래와 겹치는 것": len(set(new) & rev_keys),
        },
        "🔴 이 절이 안 하는 것": (
            "**판정을 안 한다.** 새로 들어온 자리가 「대조」인지 「rev 갈래」인지 가르는 일도, "
            "㉮ 가 몇이 되는지도 **다음 사이클**이다(레인 규칙 1·2)"),
    }


def sec_b() -> dict:
    """ㄴ 🔴 집합으로 눌린 자리 --- 티처 #88 M4."""
    pys = sorted(gc.ks.git_paths("ls-files", "--", "*.py", root=ROOT))
    rows = list(gc.sites_ast(pys, ROOT))
    keys = ["%s:%d" % (rel, line) for rel, line, _v, _k in rows]
    c = Counter(keys)
    dup = {k: n for k, n in c.items() if n > 1}
    return {
        "무엇": "ㄴ 🔴 호출 자리 수 대 `|자 A|` --- **같은 줄에 둘이면 하나로 눌린다**",
        "읽은 트리": "🔴 **작업 트리/색인**(`git ls-files`) --- ㄱ 과 **다른 트리다**",
        "🔴 `sites_ast` 가 낸 행 수(호출 자리)": len(rows),
        "🔴 `파일:줄` 로 누른 뒤(= `|자 A|`)": len(c),
        "🔴 삼켜진 수": len(rows) - len(c),
        "🔴 같은 줄에 둘 이상인 자리": dup or "없음",
        "🔴 뜻": ("티처 #88 M4 가 지목한 「51 대 49」의 정체다. **자가 틀린 게 아니라 "
               "키가 `파일:줄` 이라 같은 줄의 둘이 하나로 눌린다.** 어느 쪽이 옳은 분모인지는 "
               "**다음 사이클**이 정한다 --- 여기서는 **세기만** 한다"),
    }


def main() -> None:
    if OUT.exists():
        OUT.unlink()
    t0 = time.time()
    res = {
        "무엇": "[탐색] 950 --- 🔴 **판정이 아니다**(레인 규칙 1). 다음 사이클의 후보다",
        "🔴 규칙 1": "여기 나온 수는 이 사이클의 결론·원장 표제·커밋/PR 제목에 **안 들어간다**",
        "ㄱ 한 홉 변수": sec_a(),
        "ㄴ 집합으로 눌린 자리": sec_b(),
        "시각(UTC)": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "🔴 코드 sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    res["초"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("산출물: %s" % OUT)


if __name__ == "__main__":
    main()
