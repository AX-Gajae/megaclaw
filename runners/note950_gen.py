# -*- coding: utf-8 -*-
"""노트 950 — **M1 을 닫는다**: `docs/판정/949_수.md` 가 자기 산출물과 안 맞았다.

🔴 **병(티처 #89 M1)**: 949 는 *"노트의 숫자 칸을 러너가 산출물에서 읽어 찍는다"* 고
`runners/note949_gen.py` 를 만들었고 **손 전사는 정말 0** 이었다. 그런데
`runners/exp949_harm.json` 이 그 뒤 `e4c63bc64` 에서 **107줄 고쳐졌는데 `.md` 를
다시 안 찍었다.** 그래서 커밋된 `.md:96` 은 「넓은 자 **쟀다 7**」이라 적고 오늘 산출물은
「**쟀다 4**」다. 🔴 **하필 그 7 은 탐색 노트가 스스로 철회한 수다.**

🔴 **「다시 찍었다」로 끝내지 않는다**(티처 #89 3순위). 이 러너는

1. `note949_gen` 의 **입력 목록을 AST 로 뽑는다**(손으로 베끼면 그 목록이 또 낡는다)
2. 각 입력과 찍힌 `.md` 의 **sha256 을 산출물에 박는다**
3. ⑤′ 의 절 **`7 문서 대조`** 가 그 sha 를 **다시 계산해 견준다**

🔴 그러면 「입력이 바뀌었는데 문서를 안 다시 찍었다」가 **다음번에 자동으로 붉어진다** ---
949 가 정의한 **「대조」(읽고 · 기록된 sha 를 꺼내고 · 지금 다시 계산해 견준다)의 첫 자기 적용**이다.

⚠ **증거력의 한계(조항 61)**: 이 대조는 **낡음만** 잡는다. 문서의 수가 **옳은지**는 안 본다.

돌리기::

    python3 -m runners.note950_gen
"""
import ast
import difflib
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runners import note949_gen                                   # noqa: E402

OUT = ROOT / "runners/out950_docstamp.json"
GEN = "runners/note949_gen.py"
DOC = "docs/판정/949_수.md"


def _sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _sha(rel: str) -> str:
    return _sha_bytes((ROOT / rel).read_bytes())


def inputs_of(rel: str) -> list:
    """🔴 **입력 목록을 손으로 안 베낀다** --- `J("…")` 의 리터럴을 AST 로 뽑는다."""
    t = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
    out = []
    for n in ast.walk(t):
        if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "J" and n.args:
            a = n.args[0]
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                out.append(a.value)
    return sorted(set(out))


def committed(rel: str):
    r = subprocess.run(["git", "-C", str(ROOT), "cat-file", "blob", "HEAD:%s" % rel],
                       capture_output=True)
    return r.stdout if r.returncode == 0 else None


def main() -> None:
    if OUT.exists():
        OUT.unlink()
    t0 = time.time()
    ins = inputs_of(GEN)
    before = committed(DOC)
    before_txt = before.decode("utf-8") if before is not None else ""
    #: 🔴 **다시 찍는다** --- 949 의 생산기를 그대로 부른다(로직을 포크하지 않는다).
    note949_gen.main()
    after_txt = (ROOT / DOC).read_text(encoding="utf-8")
    dl = [l for l in difflib.unified_diff(before_txt.split("\n"), after_txt.split("\n"),
                                          "HEAD:" + DOC, "다시 찍은 " + DOC, lineterm="",
                                          n=0)]
    changed = [l for l in dl if (l.startswith("+") or l.startswith("-"))
               and not l.startswith(("+++", "---"))]
    res = {
        "무엇": "🔴 M1 --- `%s` 를 다시 찍고 **입력의 sha 를 박는다**(티처 #89 M1·3순위)" % DOC,
        "🔴 어느 트리를 읽나": {
            "다시 찍기의 입력": "작업 트리의 산출물",
            "diff 의 왼쪽": "HEAD(커밋된 `%s`)" % DOC,
            "⚠": "🔴 **한 실행 안에서 두 트리를 섞는다 --- 그래서 적는다**(티처 #89 C3)",
        },
        "🔴 입력 목록을 어떻게 얻었나":
            "`%s` 의 `J(\"…\")` 리터럴을 **AST 로** 뽑았다(손 전사 0)" % GEN,
        "🔴 입력 수(분모)": len(ins),
        "🔴 입력별 sha256(대조의 기록 쪽)": {r: _sha(r) for r in ins},
        "🔴 생산기 sha256": {GEN: _sha(GEN), "runners/note950_gen.py": _sha("runners/note950_gen.py")},
        "🔴 문서 sha256": {DOC: _sha_bytes(after_txt.encode("utf-8"))},
        "🔴 M1 diff --- 커밋된 판 대 다시 찍은 판": {
            "🔴 바뀐 줄 수": len(changed),
            #: 🔴 **둘은 다른 수다**(조항 60): 통합 diff 는 한 줄이 바뀌어도 `-`·`+` **둘**을 낸다.
            "🔴 바뀐 원본 줄 수(`-` 쪽)": len([l for l in changed if l.startswith("-")]),
            "🔴 새로 찍힌 줄 수(`+` 쪽)": len([l for l in changed if l.startswith("+")]),
            "바뀐 줄": changed or "없음",
            "🔴 뜻": ("0 이면 커밋된 `.md` 가 오늘 산출물과 **맞았다**. "
                   "0 이 아니면 **낡아 있었다** --- 그것이 M1 이다"),
        },
        "⚠ 증거력의 한계(조항 61)": (
            "이 대조는 **낡음만** 잡는다. 🔴 **문서의 수가 옳은지는 안 본다** --- "
            "입력 산출물 자체가 틀렸으면 이 대조는 초록인 채로 틀린 수를 나른다"),
        "시각(UTC)": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "초": round(time.time() - t0, 1),
        "통과": True,
        "🔴 통과의 뜻": "이 러너는 **찍는 쪽**이다. 견주는 쪽은 ⑤′ 의 `7 문서 대조` 다",
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("산출물: %s · 바뀐 줄 %d" % (OUT, len(changed)))


if __name__ == "__main__":
    main()
