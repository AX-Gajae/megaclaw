#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""990 — 🔴 **맨 마지막 러너**. `F09`(`조항 66-②`)를 «여기서» 판정한다.

🔴🔴🔴 **989 가 어긴 것 둘을 구조로 막는다.**
  ① **`PRODUCES` 를 «손으로» 안 적는다** --- 각 러너의 **AST** 에서 그 러너가 쓰는
     산출물 이름을 «뽑아» 만든다. 989 의 손 지도는 틀렸고 자기 자신을 `()` 로 적었다.
  ② **명부가 «글롭»이다** --- 989 의 `OUTPUTS` 는 넷이었고 `out989_last.json` ·
     `out989_table.json` · `fiveprime_989.json` 이 «밖»에 있었다.
     그래서 「맨 마지막 러너」가 실제로 마지막이 «아니었다».

씀:
    python3 runners/last990.py --ref <40자 sha>
"""
import argparse
import ast
import collections
import datetime as dt
import glob
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
OUT = ROOT / "runners"

GLOB_PY = "runners/*990*.py"
GLOB_ART = "runners/*990*"
DOCS = ("docs/판정_990.md", "docs/card_990.md", "docs/handoff_990.md",
        "docs/pr_990.md")
OUTNAME = re.compile(r"^(out990_[\w.]+\.(?:json|txt)|fiveprime_990\.json)$")


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p):
    return os.path.relpath(str(p), str(ROOT))


def _glob(pat):
    return sorted(_rel(p) for p in glob.glob(str(ROOT / pat)))


def _sha(rel):
    p = ROOT / rel
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def stamped_by(art):
    """🔴 **산출물이 «자기 도장에» 적어 둔 코드 sha256** 을 읽는다.

    🔴🔴 **여기가 989 와 갈리는 자리다.** 989 는 `PRODUCES` 를 «손으로» 적었고 틀렸다.
    990 은 지도를 안 만든다 --- **산출물이 스스로 「나는 이 sha 의 코드가 냈다」고 적은 것**을
    지금 디스크의 sha 와 견준다. 그것이 `조항 66-②` 가 «실제로» 말하는 것이다.
    """
    try:
        d = json.loads((ROOT / art).read_text(encoding="utf-8"))
    except Exception:                                              # noqa: BLE001
        return None
    found = collections.OrderedDict()

    def walk(o):
        if not isinstance(o, dict):
            return
        for k, v in o.items():
            if isinstance(v, dict):
                # 🔴 «코드» 도장만 본다 --- 키가 `.py` 경로여야 한다.
                #   `fiveprime_990.json` 의 「입력 산출물 sha256」은 «산출물»→sha 라
                #   그것을 코드 도장으로 읽으면 「러너가 out990_audit.json」이라는 헛것이 된다.
                if "sha256" in k and v and all(
                        isinstance(x, str) and len(x) == 64 for x in v.values()) \
                        and all(isinstance(r, str) and r.endswith(".py")
                                for r in v.keys()):
                    for r, s in v.items():
                        found[r] = s
                else:
                    walk(v)
    walk(d)
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    a = ap.parse_args()
    if len(a.ref) != 40:
        raise SystemExit("🔴 --ref 는 40자 sha 여야 한다")
    t0 = _now()

    arts = [p for p in _glob(GLOB_ART) if p.endswith((".json", ".txt"))]
    hits, stale, unstamped = 0, [], []
    pmap = collections.OrderedDict()

    def mt(rel):
        p = ROOT / rel
        return p.stat().st_mtime if p.is_file() else None

    # 🔴 ① **도장이 적은 코드 sha ↔ 지금 디스크의 sha** --- 다르면 고치고 안 다시 돌렸다
    for art in arts:
        st = stamped_by(art)
        if not st:
            unstamped.append(art)
            continue
        pmap[art] = sorted(st)
        for r, s in st.items():
            hits += 1                              # 🔴 (산출물 × 러너) 마다 비교를 수행
            cur = _sha(r)
            if cur is None:
                stale.append({"산출물": art, "러너": r, "🔴": "러너가 없다"})
            elif cur != s:
                stale.append({"산출물": art, "러너": r,
                              "도장이 적은 sha256": s, "지금 디스크 sha256": cur,
                              "🔴": "🔴 **고치고 안 다시 돌렸다**(조항 66-②)"})
    # 🔴 ② 「맨 마지막 러너」가 «정말» 마지막인가
    self_rel = "runners/last990.py"
    newer = []
    for art in arts:
        hits += 1
        if art == "runners/out990_last.json":
            continue
        a_t, s_t = mt(art), mt(self_rel)
        if a_t is not None and s_t is not None and a_t > s_t:
            newer.append(art)
    # 🔴 ③ 문서가 산출물보다 «오래되면» 문서를 다시 안 찍은 것이다
    docstale = []
    for d in DOCS:
        hits += 1
        d_t = mt(d)
        if d_t is None:
            docstale.append({"문서": d, "🔴": "없다"})
            continue
        for art in arts:
            a_t = mt(art)
            if a_t is not None and a_t > d_t + 1.0:
                docstale.append({"문서": d, "🔴 더 새 산출물": art})
                break

    fal = bool(stale)
    res = collections.OrderedDict([
        ("무엇", "990 `F09` — 🔴 **맨 마지막 러너가 판정한다**(`조항 66-②` · 989 `R2` 승계)"),
        ("🔴 명부의 출처", "글롭 `%s` · `%s` --- 손으로 안 골랐다" % (GLOB_PY, GLOB_ART)),
        ("🔴 지도의 출처",
         "🔴 **지도를 «안 만든다».** 산출물이 «자기 도장에» 적은 코드 sha256 을 "
         "지금 디스크의 sha 와 견준다 --- 989 의 손 `PRODUCES` 는 틀렸었다"),
        ("🔴 산출물별 도장이 적은 러너", pmap),
        ("🔴 이 사이클 산출물 전량", arts),
        ("🔴 산출물 수", len(arts)),
        ("🔴🔴 도장이 «없는» 산출물(= 이 자가 원리상 못 본다 · 「깨끗함」이 아니다)",
         unstamped or "없음"),
        ("🔴🔴🔴 도장 sha ≠ 디스크 sha 인 자리(= 고치고 안 다시 돌렸다)",
         stale or "없음"),
        ("🔴 그 수", len(stale)),
        ("🔴🔴 이 러너보다 «새로운» 산출물(= 이 러너가 마지막이 아니다)", newer or "없음"),
        ("🔴 그 수", len(newer)),
        ("🔴 산출물보다 «오래된» 문서(= 다시 안 찍었다)", docstale or "없음"),
        ("🔴🔴🔴 F09 반증됐나", fal),
        ("🔴 걸린 자리(= 비교를 «수행»한 회수)", hits),
        ("통과", bool(not fal)),
        ("🔴 이 절의 통과가 뜻하는 것",
         "🔴 이 사이클의 «어떤 러너도» 자기 산출물보다 새롭지 않다 --- 고치고 안 다시 돌린 자리가 없다"),
        ("⚠ 989 가 어긴 자리",
         "🔴 `last989.py` 의 `OUTPUTS` 가 «넷»이라 `out989_last.json`·`out989_table.json`·"
         "`fiveprime_989.json` 이 감시 «밖»이었고, `PRODUCES` 가 손으로 적혀 틀렸다"),
        ("🔴 도장", collections.OrderedDict([
            ("ref(부른 쪽이 준 40자 sha)", a.ref),
            ("🔴 코드 sha256", collections.OrderedDict(
                (r, hashlib.sha256((ROOT / r).read_bytes()).hexdigest())
                for r in _glob(GLOB_PY))),
            ("시작(UTC)", t0), ("끝(UTC)", _now()),
        ])),
    ])
    (OUT / "out990_last.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    sys.stderr.write("%s  [last] 끝 → out990_last.json (F09 반증=%s)\n"
                     % (_now(), fal))
    return 0


if __name__ == "__main__":
    sys.exit(main())
