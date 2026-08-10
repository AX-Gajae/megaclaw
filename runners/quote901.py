#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""🔴 **인용할 수를 산출물에서 뽑는다** --- 이슈 #136 M5.

병: PR #135 와 커밋 `cabfa3792` 가 「`.py` **629**개」라고 적었는데
**629 는 어느 산출물에도 없는 수**다. 실측 --- 커밋본 630 · 작업본 632 ·
오늘 `runners/out899a_gates.json` 의 `정적 ② 반입 금지/훑은 .py` = **633**.
🔴 이건 수치 오류 하나가 아니라 **「사람이 커밋 메시지에 손으로 적은 수」가 산출물과
갈라지는 구조**다. 손으로 옮겨 적는 한 계속 갈라진다.

그래서 **읽어서 붙인다**:

    python3 runners/quote901.py runners/out899a_gates.json '정적 ② 반입 금지/훑은 .py'
    → 633

    python3 runners/quote901.py --cite runners/out899a_gates.json '정적 ② 반입 금지/훑은 .py'
    → 633 (`runners/out899a_gates.json:정적 ② 반입 금지/훑은 .py`)

    python3 runners/quote901.py --check 629 runners/out899a_gates.json '정적 ② 반입 금지/훑은 .py'
    → 🔴 어긋난다: 적은 값 629 · 산출물 633   (종료 6)

🔴 **조항 59 --- 「없다」·「널이다」·「못 읽었다」는 셋이다.** 이 도구는 넷을 갈라 죽는다:

| 일 | 종료 | 무엇을 찍나 |
|---|---:|---|
| 값을 찾았다 | 0 | 값 |
| 파일이 없다 | 2 | `🔴 그 파일이 없다` |
| JSON 이 아니다 | 3 | `🔴 그 파일은 JSON 이 아니다` |
| **그 키가 없다** | 4 | `🔴 그 키가 없다` + 어디까지 갔는지 + **그 자리의 형제 키** |
| 값이 `null` 이다 | 5 | `🔴 그 키의 값이 null 이다` (「없다」가 **아니다**) |
| `--check` 가 어긋난다 | 6 | 적은 값과 산출물 값을 나란히 |

🔴 **절대로 빈 문자열이나 0 을 찍고 종료 0 으로 죽지 않는다** --- 그게 바로 조항 59 가
막으려는 길이다. 키가 없으면 **「그 키가 없다」** 로 죽는다.

키 경로는 `/` 로 나눈다(`--sep` 로 바꾼다). 리스트는 정수 첨자로 들어간다.
`--list` 는 그 자리의 키/첨자를 늘어놓는다(경로를 모를 때).
🔴 **키 자체가 `/` 를 품어도 된다** --- 각 자리에서 긴 조각부터 맞춰 본다
(실물: `out900h_backout.json` 의 `🔴 안 잡힘(none/both)`). 모호하면 긴 쪽이 이긴다.

`--selftest` 가 위 표의 종료 코드를 **전부 심어서 확인**한다(15가지 · 지금 15/15).
"""
import argparse
import json
import sys
from pathlib import Path

E_OK, E_NOFILE, E_NOTJSON, E_NOKEY, E_NULL, E_MISMATCH = 0, 2, 3, 4, 5, 6


def die(code: int, msg: str):
    print(msg, file=sys.stderr)
    sys.exit(code)


def children(node) -> str:
    if isinstance(node, dict):
        ks = list(node.keys())
        return "키 %d개: %s" % (len(ks), " · ".join(repr(k) for k in ks[:40]) + (" …" if len(ks) > 40 else ""))
    if isinstance(node, list):
        return "리스트 길이 %d (첨자 0..%d)" % (len(node), len(node) - 1)
    return "잎이다(%s) --- 더 들어갈 데가 없다" % type(node).__name__


def walk(doc, path, sep):
    """경로를 따라간다. 🔴 못 가면 **어디서** 못 갔는지와 **그 자리의 형제**를 들고 죽는다.

    🔴 **키 자체가 구분자를 품을 수 있다.** 실물: `out900h_backout.json` 의
    `🔴 안 잡힘(none/both)`. 그래서 각 자리에서 **긴 조각부터 맞춰 본다**.
    모호하면(긴 키와 짧은 키가 둘 다 있으면) **긴 쪽이 이긴다** --- 가르고 싶으면 `--sep`.
    맞춘 실제 조각을 돌려주므로 `--cite` 의 출처가 거짓말하지 않는다.
    """
    node, i, taken = doc, 0, []
    while i < len(path):
        here = sep.join(taken) or "(뿌리)"
        if isinstance(node, dict):
            for j in range(len(path), i, -1):
                cand = sep.join(path[i:j])
                if cand in node:
                    node, i = node[cand], j
                    taken.append(cand)
                    break
            else:
                die(E_NOKEY, "🔴 그 키가 없다: %r\n   어디까지 갔나: %s\n   그 자리: %s"
                    % (path[i], here, children(node)))
        elif isinstance(node, list):
            seg = path[i]
            try:
                idx = int(seg)
            except ValueError:
                die(E_NOKEY, "🔴 그 키가 없다: %r --- 이 자리는 리스트라 정수 첨자가 와야 한다\n"
                             "   어디까지 갔나: %s\n   그 자리: %s" % (seg, here, children(node)))
            if not (-len(node) <= idx < len(node)):
                die(E_NOKEY, "🔴 그 첨자가 없다: %d\n   어디까지 갔나: %s\n   그 자리: %s"
                    % (idx, here, children(node)))
            node, i = node[idx], i + 1
            taken.append(seg)
        else:
            die(E_NOKEY, "🔴 그 키가 없다: %r --- %s 에서 더 못 들어간다(%s)"
                % (path[i], here, children(node)))
    return node, taken


def render(v) -> str:
    if isinstance(v, str):
        return v
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    return json.dumps(v, ensure_ascii=False)


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="quote901.py",
        description="산출물 JSON 에서 인용할 값을 읽는다. 🔴 키가 없으면 「없다」가 아니라 「그 키가 없다」로 죽는다(조항 59).")
    ap.add_argument("file", help="산출물 JSON 경로")
    ap.add_argument("keypath", nargs="?", help="키 경로 (기본 구분자 '/'). 생략하면 --list 가 필요하다")
    ap.add_argument("--sep", default="/", help="키 경로 구분자 (기본 '/')")
    ap.add_argument("--list", action="store_true", help="그 자리의 키/첨자를 늘어놓는다")
    ap.add_argument("--cite", action="store_true", help="값 뒤에 출처 `파일:키` 를 붙여 찍는다(⑦ 절 규약)")
    ap.add_argument("--check", metavar="적은값",
                    help="커밋 메시지·PR 에 적으려는 값과 대조한다. 어긋나면 종료 6")
    ap.add_argument("--selftest", action="store_true",
                    help="🔴 종료 코드 여섯을 전부 심어서 확인한다(15가지 · 다른 인자 없이 단독으로)")
    a = ap.parse_args(argv)

    p = Path(a.file)
    if not p.exists():
        die(E_NOFILE, "🔴 그 파일이 없다: %s\n   (「값이 없다」가 아니다 --- 러너를 아직 안 돌렸을 수 있다)" % p)
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(E_NOTJSON, "🔴 그 파일은 JSON 이 아니다: %s\n   %s" % (p, e))
    except (OSError, UnicodeDecodeError) as e:
        die(E_NOTJSON, "🔴 그 파일을 못 읽었다: %s\n   %s" % (p, e))

    path = [s for s in (a.keypath or "").split(a.sep) if s != ""] if a.keypath else []
    node, path = walk(doc, path, a.sep)

    if a.list:
        print(children(node))
        return E_OK

    if not path:
        die(E_NOKEY, "🔴 키 경로를 안 줬다.\n   뿌리: %s" % children(doc))

    if node is None:
        die(E_NULL, "🔴 그 키의 값이 null 이다: %s\n   (「그 키가 없다」와 **다르다** --- 조항 59)"
            % a.sep.join(path))

    cite = "`%s:%s`" % (a.file, a.sep.join(path))
    out = render(node)

    if a.check is not None:
        same = (a.check.strip() == out.strip())
        if not same:
            try:
                same = float(a.check) == float(out)
            except ValueError:
                same = False
        if not same:
            die(E_MISMATCH, "🔴 어긋난다: 적은 값 %s · 산출물 %s\n   출처 %s" % (a.check, out, cite))
        print("✅ 같다: %s   출처 %s" % (out, cite))
        return E_OK

    print("%s (%s)" % (out, cite) if a.cite else out)
    return E_OK


#: 🔴 **자기 시험** --- 「종료 코드로 갈라 죽는다」가 이 도구의 전부인데, 그걸 안 재면
#: 조항 59 를 말로만 지키는 것이다. `python3 runners/quote901.py --selftest`
SELFTEST_DOC = {
    "수": 633, "널": None, "참": True, "실수": 0.5,
    "묶음": {"안": 1, "가/나": 2},
    "리스트": [{"rid": "A"}, {"rid": "B"}],
}


def selftest() -> int:
    import tempfile
    ok, bad = 0, []
    with tempfile.TemporaryDirectory() as td:
        j = Path(td) / "t.json"
        j.write_text(json.dumps(SELFTEST_DOC, ensure_ascii=False), encoding="utf-8")
        notjson = Path(td) / "t.txt"
        notjson.write_text("이건 JSON 이 아니다", encoding="utf-8")
        cases = [
            ("값을 찾았다", [str(j), "수"], E_OK),
            ("불리언", [str(j), "참"], E_OK),
            ("중첩", [str(j), "묶음/안"], E_OK),
            ("🔴 키가 구분자를 품는다", [str(j), "묶음/가/나"], E_OK),
            ("리스트 첨자", [str(j), "리스트/1/rid"], E_OK),
            ("--check 맞음", ["--check", "633", str(j), "수"], E_OK),
            ("🔴 --check 어긋남", ["--check", "629", str(j), "수"], E_MISMATCH),
            ("🔴 파일이 없다", [str(Path(td) / "없다.json"), "수"], E_NOFILE),
            ("🔴 JSON 이 아니다", [str(notjson), "수"], E_NOTJSON),
            ("🔴 그 키가 없다", [str(j), "없는키"], E_NOKEY),
            ("🔴 잎에서 더 들어간다", [str(j), "수/더"], E_NOKEY),
            ("🔴 리스트에 문자열 첨자", [str(j), "리스트/rid"], E_NOKEY),
            ("🔴 첨자가 범위 밖", [str(j), "리스트/9/rid"], E_NOKEY),
            ("🔴 값이 null 이다(≠ 없다)", [str(j), "널"], E_NULL),
            ("🔴 키 경로를 안 줬다", [str(j)], E_NOKEY),
        ]
        for name, argv, want in cases:
            try:
                got = main(argv) or E_OK
            except SystemExit as e:
                got = e.code
            if got == want:
                ok += 1
            else:
                bad.append((name, want, got))
            print("  %-28s 기대 %d · 실제 %s  %s" % (name, want, got, "✅" if got == want else "🔴"))
    print("자기 시험 %d/%d" % (ok, len(cases)))
    if bad:
        print("🔴 어긋난 것: %r" % (bad,), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        sys.exit(selftest())
    sys.exit(main())
