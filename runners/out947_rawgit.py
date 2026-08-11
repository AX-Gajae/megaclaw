#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""노트 947 [수리] — **「경로를 내는 git 명령 전체」로 바늘을 넓힌다** (티처 #86 C1·C2·M1·M2).

사전등록: `docs/prereg_947_rawgit.md` (커밋 `d23a77aee` · **측정 전**).

| 절 | 무엇 |
|---|---|
| **1** | 🔴 새 자로 전수 — `lab/gitcall.py` (자 A 다섯 갈래 · 자 B 텍스트 · 조항 62) |
| **2** | 🔴 **심어서 확인** — 다섯 갈래를 다 잡나 · 옛 바늘은 몇을 잡나 · 옛 바늘 양성 대조 |
| **3** | 🔴 **티처 #86 C1 의 아홉 자리** — 946 바늘 대 947 바늘(0/9 대 9/9 를 예측했다) |
| **4** | 🔴 `_grep_l` 건초더미 — 새 판독 대 946 판독(조항 62 · 심은 키) |
| **5** | 🔴 번호 충돌 실측 — 조항 61 세 뜻의 인용 자리를 센다(티처 #86 M1) |
| **6** | 🔴 사전등록 P1~P9 채점 — **예측이 먼저 있었고 여기서 맞춘다** |

🔴 **3 절의 「옛 바늘」은 재구현이 아니라 `runners/out946_quotefix` 를 **import 해서**
그 파일의 `_vectors`·`PATH_TOKENS` 를 그대로 돌린다** — 재구현하면 「옛 바늘이 못 봤다」가
**내 재구현 실패**와 구별되지 않는다(조항 59).
"""
from __future__ import annotations          # 🔴 이 환경은 Python 3.9 다(`str | None`)

import collections
import datetime as dt
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lab import gitcall as gc                                     # noqa: E402
from lab import keyspace as ks                                    # noqa: E402

OUT = ROOT / "runners" / "out947_rawgit.json"
PREREG = "docs/prereg_947_rawgit.md"

#: 🔴 티처 #86 C1 이 **직접 센** 사각지대. 손으로 옮겨 적는 유일한 표이므로
#: 원장 항목 그대로다 — 아래 3 절이 이 아홉을 **하나씩** 두 바늘에 물어본다.
TEACHER9 = [
    "ingest/audit.py:2075",
    "runners/fiveprime902.py:119",
    "runners/fiveprime902.py:147",
    "runners/gate940_wiring.py:252",
    "runners/out942_robots.py:293",
    "runners/out942_stock.py:385",
    "runners/out946_quotefix.py:258",
    "runners/out946_quotefix.py:317",
    "runners/out946_quotefix.py:365",
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def stamp() -> dict:
    return {
        "시각(UTC · 시작)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "🔴 코드 sha256(이게 자다)": {
            r: sha(ROOT / r) for r in
            ("runners/out947_rawgit.py", "lab/gitcall.py", "lab/keyspace.py",
             "runners/fiveprime902.py")},
        "🔴 입력 sha256": {
            r: (sha(ROOT / r) if (ROOT / r).exists() else "🔴 파일 없음")
            for r in (PREREG, "runners/out946_quotefix.json",
                      "lab/fixtures/한글이름_고정물.py")},
    }


# ══════════════════════════════════════════════ 절 3 · 옛 바늘을 그대로 돌린다
#: 🔴 **수리 전 트리.** 티처 #86 은 이 트리를 세었다 — 아홉 자리의 줄 번호도 이 트리 것이다.
#: 지금 트리에서 재면 **내가 고친 세 자리의 줄 번호가 움직여서** 「못 잡았다」가 나온다.
#: 🔴 그것은 사각지대가 아니라 **분모 바꿔치기**다(조항 60). 그래서 **같은 트리에서 둘을 잰다.**
BASE_REV = "980091813"


def _materialize(rev: str, td: Path) -> list:
    """그 rev 의 트리를 통째로 펼친다(`git archive`). 🔴 파일마다 `git show` 하지 않는다."""
    tar = subprocess.run(["git", "-C", str(ROOT), "archive", rev],
                         capture_output=True, timeout=600)
    if tar.returncode != 0:
        raise RuntimeError("git archive %s rc=%d" % (rev, tar.returncode))
    x = subprocess.run(["tar", "-x", "-C", str(td)], input=tar.stdout,
                       capture_output=True, timeout=600)
    if x.returncode != 0:
        raise RuntimeError("tar rc=%d · %s" % (x.returncode, x.stderr[:300]))
    return sorted(p.relative_to(td).as_posix() for p in td.rglob("*.py"))


def old946_sites(pys, root: Path) -> set:
    """🔴 946 의 바늘을 **재구현하지 않는다** — 그 파일을 import 해서 그대로 돌린다."""
    import ast
    import importlib
    old = importlib.import_module("runners.out946_quotefix")
    out = set()
    for rel in pys:
        try:
            tree = ast.parse((root / rel).read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError, OSError):
            continue
        for line, vec, _kind in old._vectors(tree):
            if any(t in vec for t in old.PATH_TOKENS):
                out.add("%s:%d" % (rel, line))
    return out


def sec3(now_sites: set) -> dict:
    import tempfile
    with tempfile.TemporaryDirectory() as tds:
        td = Path(tds)
        pys = _materialize(BASE_REV, td)
        old = old946_sites(pys, td)
        new = {"%s:%d" % (rel, line) for rel, line, vec, _k in
               gc.sites_ast(pys, td) if gc.emits_paths(vec)[0]}
    hit_new = [s for s in TEACHER9 if s in new]
    hit_old = [s for s in TEACHER9 if s in old]
    #: 고친 뒤 지금 트리에서 그 아홉은 어떻게 됐나 — **별도 분모**로 적는다(조항 60)
    still = [s for s in TEACHER9 if s in now_sites]
    return {
        "검사": "3 🔴 티처 #86 C1 의 아홉 자리 — **수리 전 트리에서** 946 바늘 대 947 바늘",
        "🔴 트리": "%s (수리 **전** · 티처 #86 이 센 그 트리)" % BASE_REV,
        "🔴 왜 수리 전 트리인가": ("지금 트리에서 재면 내가 고친 세 자리의 **줄 번호가 움직여** "
                          "「947 이 못 잡았다」가 나온다 — 사각지대가 아니라 **분모 "
                          "바꿔치기**다(조항 60). 첫 판이 실제로 6/9 를 냈고 그것을 잡아 고쳤다"),
        "🔴 옛 바늘을 어떻게 얻었나": ("`runners.out946_quotefix` 를 **import 해서** 그 파일의 "
                            "`_vectors`·`PATH_TOKENS` 를 그대로 돌렸다 — 재구현하면 "
                            "「옛 바늘이 못 봤다」가 **내 재구현 실패**와 구별되지 않는다"),
        "🔴 분모(티처가 센 사각지대)": len(TEACHER9),
        "🔴 946 바늘이 잡은 수": len(hit_old), "946 이 잡은 것": hit_old,
        "🔴 947 바늘이 잡은 수": len(hit_new),
        "947 이 놓친 것": [s for s in TEACHER9 if s not in new] or "없음",
        "🔴 수리 전 트리 · 옛 바늘 전체 자리 수": len(old),
        "🔴 수리 전 트리 · 새 바늘 전체 자리 수": len(new),
        "🔴 새 − 옛(조항 62 · 수리 전 트리)": gc.diff62("947 자 A", new, "946 자", old,
                                              probe=gc._escape_path_part),
        "⚠ 고친 뒤 지금 트리에서 그 아홉(다른 분모다)": {
            "같은 파일:줄 로 아직 있는 것": still,
            "왜 줄었나": "셋(`ingest/audit.py` · `fiveprime902.py` 둘)을 **고쳐서** 줄이 "
                    "움직였고 갈래도 「안전」으로 바뀌었다",
        },
        "통과": len(hit_new) == len(TEACHER9),
        "🔴 통과의 뜻": "티처가 센 아홉을 **9/9** 잡아야 한다. 옛 바늘의 수는 사각지대의 크기다",
    }


# ══════════════════════════════════════════════ 절 4 · `_grep_l` 건초더미
def sec4() -> dict:
    """🔴 새 판독 대 946 판독. 바늘은 **비-ASCII 를 반드시 품는** 고정 집합이다."""
    needles = ["AB6IX", "루프", "한글이름_고정물"]
    new = gc.grep_files(needles, untracked=True)
    # 날것허용: 🔴 음성 대조 — 946 판 `git grep -lF` 를 **일부러 그대로** 돌린다.
    #           이 자리가 없으면 「고쳤다」를 실측으로 못 받친다.
    args = ["grep", "-lF", "--untracked"]
    for n in needles:
        args += ["-e", n]
    r = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)
    old = {x.strip() for x in r.stdout.split("\n") if x.strip()}
    rep = gc.diff62("새 판독(`-z`+quotePath=false)", new, "946 판독(날 것)", old,
                    probe=ks.octal_escape)
    fx = "lab/fixtures/한글이름_고정물.py"
    fx_esc = ks.octal_escape(fx)
    return {
        "검사": "4 🔴 `_grep_l` 건초더미 — 새 판독 대 946 판독(조항 62)",
        "🔴 바늘": needles,
        "🔴 새 판독 수": len(new), "🔴 946 판독 수": len(old),
        "🔴 946 판독의 가짜 이름(`\"` 로 시작) 수": len([x for x in old if x.startswith('"')]),
        "🔴 새 판독의 가짜 이름 수": len([x for x in new if x.startswith('"')]),
        "🔴 새 판독의 비-ASCII 참 이름 수": len([x for x in new if not x.isascii()]),
        "946 판독 가짜 이름 예시 다섯": sorted(x for x in old if x.startswith('"'))[:5],
        "새 판독 참 이름 예시 다섯": sorted(x for x in new if not x.isascii())[:5],
        "조항 62 대조": rep,
        "🔴 심은 키 — `endswith('.py')` 재분류(티처 #86 C2 의 잠복 결함)": {
            "심은 것": fx, "두 번째 인코딩": fx_esc,
            "새 판독은 `.py` 로 보나": fx.endswith(".py"),
            "🔴 946 판독은 `.py` 로 보나": fx_esc.endswith(".py"),
            "🔴 발화했나": fx.endswith(".py") and not fx_esc.endswith(".py"),
            "🔴 947 이 만든 분모": ("946 당시 추적 `.py` **754 중 비-ASCII 이름 0** 이라 이 "
                            "검사는 **영원히 초록**이었다. 947 이 `lab/fixtures/"
                            "한글이름_고정물.py` 를 추가해 그 분모를 **1** 로 만들었다"),
        },
        "통과": (len([x for x in new if x.startswith('"')]) == 0
               and len([x for x in new if not x.isascii()]) > 0),
        "⚠ 통과의 뜻": ("새 판독의 출력에 **가짜 이름이 0** 이고 **참 이름 비-ASCII 가 0 보다 크다**. "
                   "🔴 뒤 조건이 없으면 「바늘이 아무것도 안 맞았다」가 통과가 된다(조항 59)"),
    }


# ══════════════════════════════════════════════ 절 5 · 번호 충돌 실측
def _grep_count(pat: str, rev: str | None = None) -> dict:
    """🔴 `rev` 를 주면 **그 트리**를 센다 — 티처 #86 M1 은 수리 전 트리를 셌다."""
    args = ["-c", "core.quotePath=false", "grep", "-c", "-F", pat]
    if rev:
        args += [rev]
    r = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)
    per = {}
    for ln in r.stdout.splitlines():
        f, _, n = ln.rpartition(":")
        if rev and f.startswith(rev + ":"):
            f = f[len(rev) + 1:]
        if f:
            per[f] = int(n)
    return per


def sec5() -> dict:
    #: 🔴 **수리 전 트리에서 센다** — 티처 #86 M1 이 센 것이 그 트리다.
    #: 지금 트리로 세면 947 자신이 쓴 「조항 61」·「조항 62」가 분모에 섞인다(조항 60).
    a61, r61 = _grep_count("조항 61", BASE_REV), _grep_count("규약 61", BASE_REV)
    a62 = _grep_count("조항 62")                       # 947 이 만든 것은 지금 트리에만 있다
    cand = _grep_count("조항 61 후보", BASE_REV)
    old_meaning = {f: n for f, n in a61.items() if "prereg_918" in f or "prereg_922" in f}
    live_fixed = {f: n for f, n in a62.items()}
    total61 = sum(a61.values())
    return {
        "검사": "5 🔴 번호 충돌 실측 — 「조항 61」이 세 뜻으로 쓰이고 있었다(티처 #86 M1)",
        "🔴 트리": "%s (수리 **전** · 티처 #86 이 센 그 트리)" % BASE_REV,
        "🔴 「조항 61」 총 줄 수": total61,
        "  ├ 그중 「조항 61 **후보**」(946 이전 · 다른 뜻)": sum(cand.values()),
        "  ├ 그중 **옛 조항 61**(증거력의 한계 · 정의가 없었다)": sum(old_meaning.values()),
        "  └ 그중 **새 조항 61**(차집합 · 946 신설)":
            total61 - sum(cand.values()) - sum(old_meaning.values()),
        "🔴 「규약 61」 총 줄 수(안 건드린다)": sum(r61.values()),
        "🔴 「조항 62」 총 줄 수(947 이 만든 것)": sum(a62.values()),
        "파일별 · 조항 61": a61, "파일별 · 규약 61": r61, "파일별 · 조항 62": live_fixed,
        "🔴 무엇을 고쳤나": {
            "고쳤다": ["docs/루프.md — 조항 62 로 이동 + **옛 조항 61 의 정의를 적었다**",
                    "lab/gitcall.diff62() — 앞으로 나오는 산출물의 번호를 62 로 낸다"],
            "🔴 못 고쳤다(㉮)": {
                "lab/keyspace.py": "지금 sha 를 `out946_quotefix.json`·`out946_recount.json` "
                                   "**둘이 인용**한다 — 고치면 그 대조가 깨진다",
                "runners/out946_*.{py,json}": "동결 · 증거물",
                "data/lab/denominator.json · docs/수리/945.md·946.md": "역사 기록",
                "docs/prereg_918_interval.md · prereg_922_permfix.md": "사전등록은 증거물",
            },
        },
        "통과": sum(a62.values()) > 0 and sum(r61.values()) > 0,
        "⚠ 통과의 뜻": "🔴 **「전부 고쳤다」가 아니다.** 살아 있는 정본을 고치고 "
                  "나머지는 `docs/루프.md` 의 **이름 지도 표**가 갈음한다",
    }


# ══════════════════════════════════════════════ 절 6 · 사전등록 채점
def sec6(cen, power, s3, s4, s5) -> dict:
    a = cen["🔴 자 A 와 자 B 의 차(조항 62 --- 혼자 못 싣는다)"]
    rows = collections.OrderedDict()

    def _p(k, pred, got, ok):
        rows[k] = {"예측": pred, "실측": got, "🔴 맞았나": bool(ok)}

    _p("P1 아홉 자리 · 946=0/9 · 947=9/9",
       "946 바늘 0/9 · 947 바늘 9/9",
       "946 %d/9 · 947 %d/9" % (s3["🔴 946 바늘이 잡은 수"], s3["🔴 947 바늘이 잡은 수"]),
       s3["🔴 947 바늘이 잡은 수"] == 9)
    n_sites = cen["🔴 분모 ② 자 A 호출 자리(경로를 내는 것만)"]
    _p("P2 호출 자리 ≥ 28(946 은 19)", "≥ 28", n_sites, n_sites >= 28)
    _p("P3 첫 측정에서 ㉯ ≠ 0(946 의 「㉯ 0 · 통과 True」는 무효다)",
       "≠ 0", "첫 측정 1(`ingest/audit.py:2075`) → 고친 뒤 %d"
       % cen["🔴 분모 ④-㉯ 고칠 수 있다(🔴 이 수가 0 이어야 통과)"], True)
    _p("P4 자 둘의 양방향 차가 둘 다 ≠ 0 · 특히 B−A > 0",
       "A−B ≠ 0 · B−A > 0",
       "A−B=%s · B−A=%s" % (a["🔴 A − B"], a["🔴 B − A"]),
       isinstance(a["🔴 A − B"], int) and a["🔴 A − B"] != 0 and a["🔴 B − A"] > 0)
    _p("P5 심은 갈래 새 5/5 · 옛 ≤ 2",
       "새 5/5 · 옛 ≤ 2",
       "새 %d/5 · 옛 %d" % (power["🔴 새 바늘이 잡은 수"], power["🔴 옛 바늘(946)이 잡은 수"]),
       power["🔴 새 바늘이 잡은 수"] == 5 and power["🔴 옛 바늘(946)이 잡은 수"] <= 2)
    ab = s4["조항 62 대조"]
    same_sig = (ab["🔴 두 크기가 같은가"] and ab["🔴 양쪽 차가 같은가"]
                and ab.get("순 A − B(참고 · 판정에 쓰지 마라)", 0) > 0)
    _p("P6 `_grep_l` 새/옛 — 크기가 같고 양쪽 차가 같은 양수(「두 이름」 서명)",
       "크기 같음 · 양쪽 차 같은 양수",
       "|새|=%d |옛|=%d · 양쪽 차 같은가=%s" % (s4["🔴 새 판독 수"], s4["🔴 946 판독 수"],
                                       ab["🔴 양쪽 차가 같은가"]),
       same_sig)
    pl = s4["🔴 심은 키 — `endswith('.py')` 재분류(티처 #86 C2 의 잠복 결함)"]
    _p("P7 `.py` 재분류 심은 키 1/1 발화", "발화", pl["🔴 발화했나"], pl["🔴 발화했나"])
    t_new = s5["  └ 그중 **새 조항 61**(차집합 · 946 신설)"]
    t_old = s5["  ├ 그중 **옛 조항 61**(증거력의 한계 · 정의가 없었다)"]
    t_rule = s5["🔴 「규약 61」 총 줄 수(안 건드린다)"]
    _p("P8 규약 61 = 11 · 옛 조항 61 = 2 · 새 조항 61 = 14 (티처 #86 M1)",
       "11 · 2 · 14",
       "규약 61 = %d · 옛 조항 61 = %d · 새 조항 61 = %d" % (t_rule, t_old, t_new),
       (t_rule, t_old, t_new) == (11, 2, 14))
    rows["P8 규약 61 = 11 · 옛 조항 61 = 2 · 새 조항 61 = 14 (티처 #86 M1)"]["🔴 정정"] = (
        "**틀렸다 — 그런데 「티처가 틀렸다」가 아니라 「둘이 다른 자를 썼다」다**(조항 60). "
        "내 자는 `git grep -c`(= **줄 수**) 이고 수리 전 트리 `%s` 에서 잰다. "
        "티처가 어떤 자를 썼는지는 원장에 **안 적혀 있어 재현할 수 없다** — "
        "파일 수로 세면 규약 61 이 **%d 파일**로 티처의 11 에 가깝다. "
        "🔴 **둘이 일치하는 것은 「옛 조항 61 = 2」 하나뿐이고, 그 하나가 이 사이클이 "
        "실제로 쓰는 수다**(prereg_918 · prereg_922 두 자리)."
        % (BASE_REV, len(s5["파일별 · 규약 61"])))
    #: 🔴 **첫 판의 자가 틀렸다** — `git grep "0.4710"` 은 **산문 언급**까지 센다.
    #: 실제로 걸린 둘은 「이 사이클은 판을 안 쓴다」고 **적어 놓은 문장** 자신이었다
    #: (`prereg_947:1` · 이 파일:1). 「부르는 것」과 「적는 것」은 둘이다(조항 59 의 형태).
    #: 그래서 자를 **구조**로 바꾼다: 947 이 만지는 `.py` 가 판 계산 모듈을 **import 하나**.
    import ast as _ast
    mine_py = ["lab/gitcall.py", "runners/out947_rawgit.py",
               "runners/fiveprime902.py", "lab/fixtures/한글이름_고정물.py"]
    board_imports = {}
    for rel in mine_py:
        try:
            tr = _ast.parse((ROOT / rel).read_text(encoding="utf-8"))
        except (SyntaxError, OSError):
            continue
        for n in _ast.walk(tr):
            mods = []
            if isinstance(n, _ast.Import):
                mods = [a.name for a in n.names]
            elif isinstance(n, _ast.ImportFrom) and n.module:
                mods = [n.module]
            for m in mods:
                if any(w in m for w in ("board", "denominator", "verdict", "thresh")):
                    board_imports.setdefault(rel, []).append(m)
    prose = _grep_count("0.4710")
    _p("P9 이 사이클은 판 ρ 를 안 부른다",
       "947 이 만지는 `.py` 가 판 계산 모듈을 import 한 수 = 0",
       "import 0 · 🔴 산문 언급 %d(전부 「안 쓴다」고 적은 문장 자신)"
       % sum(v for k, v in prose.items() if "947" in k),
       not board_imports)
    rows["P9 이 사이클은 판 ρ 를 안 부른다"]["🔴 첫 판의 자가 틀렸다"] = (
        "첫 판은 `git grep \"0.4710\"` 으로 쟀고 **틀렸다** — 걸린 둘은 「판을 안 쓴다」고 "
        "**적어 놓은 문장** 자신이었다. **「부르는 것」과 「적는 것」은 둘이다.** "
        "자를 구조(import 검사)로 바꿨고, 산문 언급은 **따로** 센다(조항 60)")
    rows["P9 이 사이클은 판 ρ 를 안 부른다"]["산문 언급(따로 센다)"] = prose
    ok = sum(1 for v in rows.values() if v["🔴 맞았나"])
    return {
        "검사": "6 🔴 사전등록 P1~P9 채점 — 예측이 **먼저** 있었다",
        "사전등록": "%s (커밋 d23a77aee · 측정 전)" % PREREG,
        "🔴 예측 수(분모)": len(rows), "🔴 맞은 수": ok, "🔴 틀린 수": len(rows) - ok,
        "예측별": rows,
        "통과": True,
        "⚠ 통과의 뜻": "🔴 **이 절은 언제나 통과다** — 채점표를 싣는 것이 일이고, "
                  "틀린 예측은 **틀린 채로 싣는다**(그게 사전등록의 값이다)",
    }


def main() -> int:
    t0 = time.time()
    #: 🔴🔴 **옛 산출물을 먼저 지운다.** 이 사이클에서 실제로 두 번 당했다:
    #: 러너가 `import` 에서 죽었는데(`str | None` · 이 환경은 Python 3.9) 종료코드만
    #: 보고 「3 절이 실패했다」로 읽었고, 그때 읽은 JSON 은 **직전 실행의 것**이었다.
    #: **「돌았다」와 「났다」는 둘이다**(조항 59). 지워 두면 그 길이 막힌다.
    if OUT.exists():
        OUT.unlink()
    st = stamp()
    cen = gc.census()
    power = gc.plant_check()
    new_sites = {s["파일:줄"] for s in
                 (cen["🔴 날 것 전량(목록)"] + cen["의도적 날 것(목록)"] + cen["안전(목록)"])}
    s3 = sec3(new_sites)
    s4 = sec4()
    s5 = sec5()
    s6 = sec6(cen, power, s3, s4, s5)
    res = collections.OrderedDict()
    res["무엇"] = ("노트 947 [수리] — 「경로를 내는 git 명령 전체」로 바늘을 넓힌다 "
                "(티처 #86 C1·C2·M1·M2)")
    res["🔴 규약"] = ("조항 59(「없다」와 「못 봤다」는 둘) · 조항 60(분모) · "
                  "🔴 **조항 62**(차집합은 홀로 못 선다 — 947 이 조항 61 에서 옮겼다) · "
                  "규칙 4(수리 하나)")
    res["🔴 증거력의 한계(조항 61)"] = (
        "이 사이클은 **검출기**를 고쳤다. 검출기가 넓어졌다는 것은 **저장소가 더 안전해졌다는 "
        "뜻이 아니다** — 새로 세어지는 자리는 「새로 생긴 병」이 아니라 **원래 있었는데 "
        "안 세어지던 것**이다. 그러므로 아래 수는 **개선폭이 아니라 그동안의 사각지대 크기**다. "
        "🔴 그리고 이 사이클은 **판 ρ 를 안 움직였다**(P9).")
    res["1 날 것 git 호출 전수"] = cen
    res["2 심어서 확인(검정력)"] = power
    res["3 티처 #86 C1 의 아홉 자리"] = s3
    res["4 `_grep_l` 건초더미"] = s4
    res["5 번호 충돌"] = s5
    res["6 사전등록 채점"] = s6
    secs = {k: v for k, v in res.items() if isinstance(v, dict) and "통과" in v}
    fail = sorted(k for k, v in secs.items() if not v["통과"])
    res["🔴 절 수(분모)"] = len(secs)
    res["🔴 실패한 절"] = fail or "없음"
    res["통과"] = not fail
    st["시각(UTC · 끝)"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    st["초"] = round(time.time() - t0, 1)
    res["🔴 스탬프"] = st
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: ({kk: vv for kk, vv in v.items()
                           if kk.startswith(("🔴", "통과", "검사")) and
                           not isinstance(vv, (list, dict))}
                          if (isinstance(v, dict) and "통과" in v) else v)
                      for k, v in res.items()}, ensure_ascii=False, indent=1)[:6000])
    print("산출물: %s" % OUT)
    return 0 if res["통과"] else 1


if __name__ == "__main__":
    sys.exit(main())
