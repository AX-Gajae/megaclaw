# -*- coding: utf-8 -*-
"""노트 950 [수리] — **「자가 없는 사유 56」을 자로 가른다**(티처 #89 1순위).

949 는 `data/lab/exempt949.json` 72 항목 중 **56** 을 「자가 없는 사유」로 **한 덩어리**로
셌다. 🔴 그런데 그 56 의 대부분은 「자가 없는 것」이 아니라 **「이미 있는 자를 안 붙인 것」**
이었다 — `소비자아님` 자는 949 가 `lab/gitcall.py:1118-1120` 에 **구현해 놓고 한 곳도 안 붙였다**.

이 러너가 하는 일:

* 절 1 — **56 을 가른다**(자를 안 붙인 것 / 자가 없는 것 / 🔴 원리상·환경상 못 재는 것)
* 절 2·3·4 — 새 자 셋(`기록기` · `동결산출물` · `재실행무해`)을 **실제로 돌린다**
* 절 5 — 🔴 **자의 검정력을 심어서 잰다**(양성·음성·저장소 쓰기 가드)
* 절 6 — **M3**: 28 과 37 의 **분모와 겹침**(조항 60 후단)
* 절 7 — 🔴 **남은 것을 하나씩 적는다**(줄었다고 초록이 아니다)

돌리기::

    python3 -m runners.out950_rulers
"""
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lab import gitcall as gc                                    # noqa: E402
from lab import keyspace as ks                                   # noqa: E402

OUT = ROOT / "runners/out950_rulers.json"
OLD = ROOT / "data/lab/exempt949.json"
NEW = ROOT / "data/lab/exempt950.json"
F949 = ROOT / "runners/out949_fiveprime.json"
SCRATCH = Path(os.environ.get(
    "WM_SCRATCH",
    "/private/tmp/claude-501/-Users-ax-world-model/"
    "511dc308-36bf-409d-9afe-b82a8bb5d7ae/scratchpad")) / "wm950"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def J(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


# ── 절 1 · 56 가르기 ───────────────────────────────────────────────────────
#: 🔴 「원리상/환경상 못 재는 것」은 **손으로 고르지 않는다** --- 사유에 이 표지가
#:    있는 것만 그렇게 센다. 표지도 사유 파일 안에 있으므로 **커밋된 증거**다.
CANT = {
    "serve/registry.py": "🔴 **환경상** --- 8791·8792 포트 서버를 흔든다",
    "ingest/kobis_api908.py": "🔴 **절반** --- AST 는 되고 네트워크는 이 실행에서 못 잰다",
}


def sec1() -> dict:
    old, new = J(OLD), J(NEW)
    #: 949 의 「자가 없는 56」 --- **옛 파일에서** 센다(분모를 바꾸지 않는다)
    was = sorted(p for p, v in old.items() if not gc._ruler_tags(v))
    had = sorted(p for p, v in old.items() if gc._ruler_tags(v))
    by = {}
    for p in was:
        t = gc._ruler_tags(new.get(p, ""))
        by.setdefault("+".join(t) if t else "🔴 자가 없다", []).append(p)
    still = by.get("🔴 자가 없다", [])
    return {
        "검사": "1 🔴 949 의 「자가 없는 사유 56」을 가른다",
        "읽은 트리": "작업 트리(두 사유 파일은 커밋된 입력이다)",
        "🔴 분모 --- `exempt949.json` 항목 수": len(old),
        "949 에서 자가 붙어 있던 것": len(had),
        "🔴 949 에서 자가 없던 것(= 이 절의 분모)": len(was),
        "🔴 950 이 자를 붙인 것": len(was) - len(still),
        "🔴 950 뒤에도 자가 없는 것": len(still),
        "자별 분해": {k: {"수": len(v), "목록": v} for k, v in sorted(by.items())},
        "🔴 자가 없는 것(전량 · 하나씩 적는다)": {
            p: {"사유": new.get(p, "🔴 새 파일에 없다"),
                "🔴 원리상·환경상 못 재나": CANT.get(p, "아니다 --- **아직 안 잰 것**이다")}
            for p in still},
        "🔴 원리상·환경상 못 재는 것 수": len([p for p in still if p in CANT]),
        "🔴 아직 안 잰 것 수": len([p for p in still if p not in CANT]),
        "통과": len(still) <= len(CANT) + 4,
        "⚠ 통과의 뜻": ("🔴 **이 절의 통과는 「다 닫았다」가 아니다** --- 「자가 없는 것이 "
                   "손으로 셀 수 있는 수로 줄었다」뿐이다. 남은 것은 위 칸에 **전량** 있다"),
    }


# ── 절 2·3·4 · 새 자 셋을 실제로 돌린다 ───────────────────────────────────
def _pick(tag: str) -> list:
    new = J(NEW)
    return sorted(p for p, v in new.items() if tag in gc._ruler_tags(v))


def sec2() -> dict:
    rels = _pick("기록기")
    rows = {p: gc.ledger_writer(p) for p in rels}
    ok = [p for p, d in rows.items() if d["🔴 자가 냈나"]]
    bad = [p for p, d in rows.items() if not d["🔴 자가 냈나"]]
    return {
        "검사": "2 🔴 자 `기록기` --- 다시 돌리면 원장에 **쓰나**",
        "읽은 트리": "작업 트리(AST)",
        "자": "`data/lab/denominator.json` 을 겨냥한 **쓰기 호출**이 있나(AST)",
        "🔴 분모": len(rels),
        "🔴 자가 참을 낸 것": len(ok),
        "🔴 자가 **거짓**을 낸 것": len(bad),
        "🔴 거짓 목록 --- **사유가 틀렸다는 발견이다**": bad or "없음",
        "파일별": rows,
        "통과": len(bad) == 0,
        "🔴 통과의 뜻": ("전부 참이어야 통과. **거짓이 나오면 그것은 「고칠 것」이 아니라 "
                   "「사유가 거짓이다」는 발견**이다 --- 사유를 통과하는 문장으로 "
                   "바꿔 적지 않는다(사전등록 §0-5)"),
    }


def sec3() -> dict:
    rels = _pick("동결산출물")
    tracked = gc._tracked(ROOT, "HEAD")
    rows = {p: gc.frozen_output(p, ROOT, tracked) for p in rels}
    bad = [p for p, d in rows.items() if not d["🔴 자가 냈나"]]
    return {
        "검사": "3 🔴 자 `동결산출물` --- `OUT` 이 **커밋된 옛 사이클 산출물**인가",
        "읽은 트리": "코드는 작업 트리(AST) · 「커밋됐나」는 **HEAD**(`ls-tree`)",
        "🔴 분모": len(rels),
        "🔴 자가 참을 낸 것": len(rels) - len(bad),
        "🔴 거짓 목록": bad or "없음",
        "파일별": rows,
        "통과": not bad,
    }


def sec4() -> dict:
    rels = _pick("재실행무해")
    rows = {}
    for p in rels:
        rows[p] = gc.rerun_isolated(p, ROOT, scratch=str(SCRATCH))
    ok = [p for p, d in rows.items() if d["🔴 자가 냈나"]]
    blocked = {p: d.get("🔴 저장소 쓰기 차단") for p, d in rows.items()
               if d.get("🔴 저장소 쓰기 차단") not in ("없음(한 바이트도 안 썼다)", None)}
    #: 🔴 **조항 59** --- 「같다」·「다르다」·「모른다」는 셋이다. 한 칸에 뭉치면
    #:    「안 쟀다」가 「무해하다」로 읽힌다. 그리고 **모른다에도 두 종류**가 있다:
    #:    러너 쪽 사정(인자가 필요하다)과 **이 자의 한계**(경로를 갈아끼워 러너가 깨졌다).
    kind = {}
    for p, d in rows.items():
        r = str(d.get("🔴 실행 결과") or "")
        if d["🔴 자가 냈나"]:
            kind[p] = "✅ 같다 --- 절 판정이 커밋된 산출물과 같다"
        elif d.get("🔴 저장소 쓰기 차단") not in ("없음(한 바이트도 안 썼다)", None):
            kind[p] = ("🔴 **저장소를 쓰려 들었다** --- 가드가 막았다. "
                       "「다시 돌리면 저장소가 바뀐다」가 **값으로 참**이다")
        elif "subpath" in r or "relative_to" in r:
            kind[p] = ("🔴 모른다 --- **이 자의 한계다**. 출력 경로를 스크래치패드로 "
                       "갈아끼웠더니 러너가 그 경로를 `relative_to(ROOT)` 로 다시 풀다 죽었다. "
                       "**러너의 흠이 아니다**")
        elif r.startswith("모른다"):
            kind[p] = "🔴 모른다 --- %s(「무해하다」가 아니다 · 조항 59)" % r[6:120]
        else:
            kind[p] = "🔴 **다르다** --- 다시 돌리니 절 판정이 **바뀐다**"
    diff = [p for p, v in kind.items() if v.startswith("🔴 **다르다")]
    unknown = [p for p, v in kind.items() if v.startswith("🔴 모른다")]
    return {
        "검사": "4 🔴 자 `재실행무해` --- **격리 재실행**으로 절 판정을 견준다",
        "읽은 트리": "코드는 **작업 트리** · 견주는 상대는 **HEAD 의 커밋된 산출물**",
        "🔴 이것이 티처 #88 의 「안 쟀다」 ② 다":
            "*「동결 러너를 다시 돌리면 정말 산출물이 안 바뀌는지」* --- 이 절이 그것을 잰다",
        "🔴 분모": len(rels),
        "🔴 절 판정이 같은 것": len(ok),
        "🔴 **다르다**(다시 돌리면 절 판정이 바뀐다)": len(diff),
        "🔴 모른다(「무해하다」가 아니다 · 조항 59)": len(unknown),
        "🔴 갈래별": kind,
        "🔴 같지 않거나 모르는 것": sorted(set(rels) - set(ok)) or "없음",
        "🔴 저장소 쓰기를 시도한 것": blocked or "없음 --- **저장소는 한 바이트도 안 바뀌었다**",
        "🔴 티처 #88 「안 쟀다」 ② 의 답": (
            "*「동결 러너를 다시 돌리면 정말 산출물이 안 바뀌는지」* --- **쟀다.** "
            "6 중 같은 것 %d · **다른 것 %d** · 모른다 %d · 저장소를 쓰려 든 것 %d. "
            "🔴 **「안 바뀐다」는 전부에 대해 참이 아니다**" % (
                len(ok), len(diff), len(unknown), len(blocked))),
        "파일별": rows,
        "통과": len(ok) == len(rels) and not blocked,
        "⚠ 한계(조항 61)": ("「오늘 이 실행에서 절 판정이 같았다」만 낸다. **「무해하다」가 "
                       "아니다** --- 시각·난수·외부 트리 의존이면 다음에 다를 수 있다"),
    }


# ── 절 5 · 🔴 자의 검정력 --- 심어서 확인 ─────────────────────────────────
PLANTS = {
    "양성 ① 기록기 --- 원장에 write_text 한다": ("기록기", True, '''
import json
from pathlib import Path
ROOT = Path("/Users/ax/world_model")
LEDGER = ROOT / "data/lab/denominator.json"
def main():
    LEDGER.write_text(json.dumps({}), encoding="utf-8")
'''),
    "음성 ① 기록기 --- 원장을 **읽기만** 한다": ("기록기", False, '''
import json
from pathlib import Path
ROOT = Path("/Users/ax/world_model")
LEDGER = ROOT / "data/lab/denominator.json"
OUT = ROOT / "runners/somewhere_else.json"
def main():
    d = json.loads(LEDGER.read_text())
    OUT.write_text(json.dumps(len(d)))
'''),
    "양성 ② 동결산출물 --- OUT 이 커밋된 out946": ("동결산출물", True, '''
from pathlib import Path
ROOT = Path("/Users/ax/world_model")
OUT = ROOT / "runners" / "out946_recount.json"
'''),
    "음성 ② 동결산출물 --- OUT 이 안 커밋된 새 파일": ("동결산출물", False, '''
from pathlib import Path
ROOT = Path("/Users/ax/world_model")
OUT = ROOT / "runners" / "out950_zzz_not_committed.json"
'''),
}

#: 🔴 `재실행무해` 는 **별도 프로세스**를 타므로 심는 꼴이 다르다 --- 파일로 심는다.
RERUN_PLANTS = {
    "양성 ③ 재실행무해 --- 커밋된 내용을 그대로 다시 쓴다": (True, '''
import json, subprocess
from pathlib import Path
ROOT = Path("/Users/ax/world_model")
OUT = ROOT / "runners" / "out946_recount.json"
def main():
    r = subprocess.run(["git", "-C", str(ROOT), "cat-file", "blob",
                        "HEAD:runners/out946_recount.json"], capture_output=True)
    OUT.write_text(r.stdout.decode("utf-8"), encoding="utf-8")
'''),
    "음성 ③ 재실행무해 --- 절 판정을 **뒤집어** 쓴다": (False, '''
import json, subprocess
from pathlib import Path
ROOT = Path("/Users/ax/world_model")
OUT = ROOT / "runners" / "out946_recount.json"
def main():
    r = subprocess.run(["git", "-C", str(ROOT), "cat-file", "blob",
                        "HEAD:runners/out946_recount.json"], capture_output=True)
    d = json.loads(r.stdout.decode("utf-8"))
    def flip(o):
        if isinstance(o, dict):
            return {k: (not v if k == "통과" and isinstance(v, bool) else flip(v))
                    for k, v in o.items()}
        if isinstance(o, list):
            return [flip(x) for x in o]
        return o
    OUT.write_text(json.dumps(flip(d), ensure_ascii=False), encoding="utf-8")
'''),
    "🔴 음성 ④ 쓰기 가드 --- **저장소를 직접 쓰려 든다**": (False, '''
import json
from pathlib import Path
ROOT = Path("/Users/ax/world_model")
OUT = ROOT / "runners" / "out946_recount.json"
def main():
    # 🔴 OUT 상수를 안 거치고 **리터럴 경로로** 저장소를 쓰려 든다 --- 가드가 막아야 한다
    (Path("/Users/ax/world_model") / "runners" / "out946_recount.json").write_text("x")
'''),
}


def sec5() -> dict:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    rows, hit, miss = {}, 0, 0
    for name, (ruler, want, src) in PLANTS.items():
        p = SCRATCH / ("plant_%s.py" % hashlib.sha256(name.encode()).hexdigest()[:10])
        p.write_text(src, encoding="utf-8")
        fn = gc.ledger_writer if ruler == "기록기" else gc.frozen_output
        got = fn(str(p))["🔴 자가 냈나"]
        rows[name] = {"자": ruler, "기대": want, "🔴 실측": got, "🔴 맞았나": got == want}
        hit += int(got == want)
        miss += int(got != want)
    for name, (want, src) in RERUN_PLANTS.items():
        p = SCRATCH / ("rerun_%s.py" % hashlib.sha256(name.encode()).hexdigest()[:10])
        p.write_text(src, encoding="utf-8")
        d = gc.rerun_isolated(str(p), ROOT, scratch=str(SCRATCH))
        got = d["🔴 자가 냈나"]
        rows[name] = {"자": "재실행무해", "기대": want, "🔴 실측": got,
                      "🔴 맞았나": got == want,
                      "저장소 쓰기 차단": d.get("🔴 저장소 쓰기 차단"),
                      "산출물별 절 대조": d.get("산출물별 절 대조")}
        hit += int(got == want)
        miss += int(got != want)
    guard = rows["🔴 음성 ④ 쓰기 가드 --- **저장소를 직접 쓰려 든다**"]
    return {
        "검사": "5 🔴 새 자 셋의 **검정력** --- 심어서 확인(말이 아니라 발화)",
        "읽은 트리": "심은 파일은 스크래치패드 · 견주는 상대는 HEAD",
        "🔴 심은 수(분모)": len(rows),
        "🔴 맞은 수": hit, "🔴 빗나간 수": miss,
        "심은 것별": rows,
        "🔴 쓰기 가드가 실제로 막았나": guard["저장소 쓰기 차단"],
        "통과": miss == 0 and guard["저장소 쓰기 차단"] not in (
            None, "없음(한 바이트도 안 썼다)"),
        "🔴 통과의 뜻": ("심은 것을 전부 맞히고 **쓰기 가드가 실제로 발화**해야 통과. "
                   "가드가 안 터지면 「저장소를 안 건드렸다」는 **안 잰 것**이다(조항 59)"),
    }


# ── 절 6 · M3 분모와 겹침 ─────────────────────────────────────────────────
def sec6() -> dict:
    d = J(F949)
    got = {}
    for sec in ("1 소비자 역참조", "2 게이트"):
        r = d[sec]["🔴 사유의 자(949 · 티처 #88 ㄷ)"]
        none = sorted(k for k, v in r["사유별"].items()
                      if v["자"].startswith("🔴 자가 없다"))
        got[sec] = {"🔴 자가 없는 사유": none, "수": len(none),
                    "🔴 분모(그 절의 사유 수)": len(r["사유별"]),
                    "산출물이 적은 수": r["🔴 자가 없는 사유 수"],
                    "🔴 재현되나": len(none) == r["🔴 자가 없는 사유 수"]}
    a = set(got["1 소비자 역참조"]["🔴 자가 없는 사유"])
    b = set(got["2 게이트"]["🔴 자가 없는 사유"])
    return {
        "검사": "6 🔴 M3 --- 두 수를 이을 때 **분모를 적는다**(조항 60 후단)",
        "읽은 트리": "949 의 커밋된 산출물 `runners/out949_fiveprime.json`",
        "절별": got,
        "🔴 §1 의 수 / 분모": "%d / %d" % (got["1 소비자 역참조"]["수"],
                                     got["1 소비자 역참조"]["🔴 분모(그 절의 사유 수)"]),
        "🔴 §2 의 수 / 분모": "%d / %d" % (got["2 게이트"]["수"],
                                     got["2 게이트"]["🔴 분모(그 절의 사유 수)"]),
        "🔴 교집합": len(a & b), "🔴 합집합(= 서로 다른 파일 수)": len(a | b),
        "교집합 목록": sorted(a & b),
        "🔴 949 가 안 적은 것": ("949 는 28 과 37 을 나란히 적고 **겹침을 어디에도 안 적었다**. "
                        "두 수는 **분모가 다르고**(43 대 45) 겹치는 파일이 있다"),
        "통과": len(a | b) == 56 and got["1 소비자 역참조"]["🔴 재현되나"]
                and got["2 게이트"]["🔴 재현되나"],
    }


# ── 절 7 · 🔴 남은 것 ─────────────────────────────────────────────────────
def sec7(s1: dict) -> dict:
    return {
        "검사": "7 🔴 **남은 것** --- 줄었다고 초록이 되는 게 아니다",
        "🔴 남은 것(전량)": s1["🔴 자가 없는 것(전량 · 하나씩 적는다)"],
        "🔴 이 사이클이 **안 한 것**": [
            "티처 #89 **C2** --- `checkers()` 의 「한 홉 변수」 사각지대. **[탐색]로만 쟀고 "
            "판정은 안 했다**(`docs/탐색/950.md` · 규칙 1)",
            "티처 #89 **M4·M5·m1~m6** --- 안 했다",
            "티처 #88 **M3**(`3 판정 키 규약` 범위) · **M4**(호출 자리 51 대 |자 A| 49) · "
            "**m2**(16자리 축약 sha) · 「안 쟀다」 **①④** --- 안 했다",
            "티처 #86·#87 의 잔여 --- **여전히 하나도 안 갚았다**(949 의 자기 신고 그대로)",
            "⑤′ 의 `1-라`·`3 판정 키 규약` --- 이 사이클이 안 건드렸다(붉은 채로 싣는다)",
        ],
        "통과": True,
        "⚠": "이 절은 **목록**이다. `통과 True` 는 「목록을 적었다」는 뜻이지 「갚았다」가 아니다",
    }


def main() -> None:
    if OUT.exists():
        OUT.unlink()
    t0 = time.time()
    started = _now()
    res = {
        "무엇": "노트 950 [수리] --- 「자가 없는 사유 56」을 자로 가른다(티처 #89 1순위)",
        "🔴 어느 트리를 읽나(티처 #89 C3)": {
            "사유 파일 · AST": "작업 트리",
            "`동결산출물` 의 「커밋됐나」": "HEAD(`git ls-tree`)",
            "`재실행무해` 의 견주는 상대": "HEAD(`git cat-file blob HEAD:…`)",
            "절 6 의 입력": "949 의 커밋된 산출물",
            "⚠": "🔴 **한 실행 안에서 두 트리를 섞는다 --- 그래서 절마다 적는다**",
        },
    }
    s1 = sec1()
    res["1 56 가르기"] = s1
    res["2 자 `기록기`"] = sec2()
    res["3 자 `동결산출물`"] = sec3()
    res["4 자 `재실행무해`"] = sec4()
    res["5 검정력(심어서 확인)"] = sec5()
    res["6 M3 분모와 겹침"] = sec6()
    res["7 남은 것"] = sec7(s1)
    secs = {k: v for k, v in res.items() if isinstance(v, dict) and "통과" in v}
    res["🔴 절 수(분모)"] = len(secs)
    res["🔴 실패한 절"] = sorted(k for k, v in secs.items() if v["통과"] is not True)
    res["통과"] = not res["🔴 실패한 절"]
    res["시각(UTC · 시작)"] = started
    res["시각(UTC · 끝)"] = _now()
    res["🔴 코드 sha256(이게 자다)"] = {
        "runners/out950_rulers.py": _sha(Path(__file__)),
        "lab/gitcall.py": _sha(ROOT / "lab/gitcall.py"),
    }
    res["🔴 입력 산출물 sha256"] = {
        "data/lab/exempt949.json": _sha(OLD),
        "data/lab/exempt950.json": _sha(NEW),
        "runners/out949_fiveprime.json": _sha(F949),
    }
    res["초"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("산출물: %s · 실패한 절 %s" % (OUT, res["🔴 실패한 절"] or "없음"))


if __name__ == "__main__":
    main()
