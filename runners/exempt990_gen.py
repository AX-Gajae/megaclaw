#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""990 `R3` — **`⑤′` 절 1 의 「사유」를 «커밋된 파일»로 등기한다.**

🔴 **왜.** `⑤′` 절 1 은 「바뀐 경로를 역참조하는 소비자」마다
**「돌렸나 · 아니면 «사유»가 있나」**를 묻는다. 사유는
**`--exempt-file` 로 넘긴 «커밋된 JSON»** 이어야 하고, 각 사유는
`lab.gitcall` 에 **등기된 자 이름**(`[자:…]`)을 달아야 «자가 낸다».
🔴 **989 는 `--exempt-file` 을 «안 줬고» 그래서 소비자 136 이 전부 「사유 없음」이었다.**

🔴🔴 **사유를 손으로 안 쓴다.** 이 러너가 «자를 미리 돌려» 참인 것에만 사유를 붙인다 ---
등기부에 있는 자가 «거짓»을 내는 자리에는 사유를 «안 붙인다»(그것이 정직이다).

씀:
    python3 runners/exempt990_gen.py
"""
import ast
import collections
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

OUTP = ROOT / "data/lab/exempt990.json"


def tracked_py():
    r = subprocess.run(["git", "-c", "core.quotePath=false", "ls-files", "-z", "--",
                        "*.py"], cwd=str(ROOT), capture_output=True)
    return sorted(p for p in r.stdout.decode("utf-8").split("\0") if p.endswith(".py"))


def has_main(rel):
    """🔴 `lab.gitcall` 의 `모듈` 자와 «같은 식»으로 본다 --- 다른 식으로 재지 않는다."""
    try:
        tt = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return True                                # 못 읽으면 「모듈이다」라고 «안» 한다
    return any(isinstance(x, ast.If) and "__main__" in ast.dump(x.test)
               for x in tt.body)


def main():
    out = collections.OrderedDict()
    stat = collections.Counter()
    for rel in tracked_py():
        stat["훑은 .py"] += 1
        if has_main(rel):
            stat["진입점이 있어 「모듈」 자를 못 붙인다"] += 1
            continue
        out[rel] = ("[자:모듈] 🔴 실행 진입점(`__main__`)이 없다 --- 임포트해서 쓰는 모듈이라 "
                    "「돌린다」가 성립하지 않는다. 소비자로 잡혀도 이 사이클이 «돌릴 대상»이 아니다")
        stat["「모듈」 자로 사유를 붙였다"] += 1
    OUTP.parent.mkdir(parents=True, exist_ok=True)
    OUTP.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    meta = collections.OrderedDict([
        ("무엇", "990 R3 — ⑤′ 절 1 의 사유 등기(`--exempt-file` 이 읽는다)"),
        ("🔴 사유를 붙인 경로 수", len(out)),
        ("🔴 계수", dict(stat)),
        ("🔴 쓴 자", "[자:모듈] --- `lab.gitcall.exempt_rulers` 의 등기된 자"),
        ("🔴 안 붙인 것", "🔴 진입점이 있는 `.py` 에는 «안 붙였다» --- 그것은 「돌릴 수 있는 것」이고 "
                     "「안 돌린 것」을 사유로 덮으면 그것이 조용한 면제다"),
        ("🔴 이 자의 한계(조항 61)",
         "🔴 **이 파일은 절 1 을 «초록으로» 만들려는 것이 아니다.** "
         "「사유 등록 0」을 「사유 등록 N」으로 바꿔 «남은 자리»를 드러내려는 것이다"),
    ])
    print(json.dumps(meta, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
