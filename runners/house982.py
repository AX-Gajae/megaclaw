#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""982 — 🔴 **집을 닫았나**(규칙 A 배관 머지 · A-2)를 재서 낸다.

🔴🔴 **981 에서 무엇이 틀렸나 (티처 #120 M5·M10).**
① **조항 60** — 판정문이 「**main 원장** 1183 · 키 중복 0(**전 층위 2508 층**)」이라 적었는데
   `house981._dups()` 는 **디스크**에서 층을 셌다. 티처가 직접 세니 **main 은 2505** 였다.
   🔴 **982 는 `main`(= `HEAD`) 과 디스크에서 «따로» 세고 둘 다 싣는다.**
② **A-2 분자가 여전히 「A-2 라고 «적었나»」다** — `house981.a2_cycles()` 는 문서에
   `"A-2"` 라는 **글자**가 있으면 셌다. 🔴 **982 는 「돌렸나」로 바꾼다** —
   그 사이클의 산출물이 **`HEAD` 판 sha256 과 디스크 판 sha256 을 «둘 다»** 담고
   **그 둘의 비교 판정**을 담고 있는가. 🔴 **글자는 안 센다.**
   ⚠ 두 자를 **둘 다** 싣는다(조항 66-③ 구판/신판 전후).

씀:
    python3 runners/house982.py --stage house --ref <40자 sha> --cycle 982
"""
import argparse
import collections
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import ledger as LG                               # noqa: E402

RAN = ("runners/house982.py", "runners/ledger.py", "runners/predict971.py")
OUT = ROOT / "runners"
DEN = "data/lab/denominator.json"

#: 🔴 A-2 는 974 가 개정해 신설됐다 — 그 앞은 분모 밖이다(`docs/루프.md` 규칙 A-2).
A2_FIRST = 974

#: 🔴🔴 「A-2 를 돌렸나」의 자 — **두 sha 를 둘 다 담고 비교했는가**.
SHA64 = re.compile(r"\b[0-9a-f]{64}\b")


def _git(args):
    return subprocess.check_output(["git"] + args, cwd=str(ROOT))


def _dups(txt):
    """🔴 **전 층위** 층 수와 중복 키를 센다(맨 위만 보면 안 된다)."""
    layers = [0]
    bad = []

    def hook(ps):
        layers[0] += 1
        c = collections.Counter([k for k, _ in ps])
        for k, n in c.items():
            if n > 1:
                bad.append([k, n])
        return dict(ps)

    json.loads(txt, object_pairs_hook=hook)
    return layers[0], bad


def _ran_a2(n):
    """🔴🔴 사이클 `n` 이 A-2 를 **돌렸다는 물증**을 산출물에서 찾는다.

    자: 그 사이클의 산출물/원장 항목이 **서로 다른 sha256 «둘 이상»** 과
    **그 둘의 비교 판정**(불리언)을 같이 담고 있는가. 🔴 「A-2」라는 **글자는 안 센다.**
    """
    ev = []
    for cand in ("runners/out%d_house.json" % n, "docs/ledger_%d.json" % n):
        q = ROOT / cand
        if not q.is_file():
            continue
        try:
            obj = json.loads(q.read_text(encoding="utf-8"))
        except ValueError:
            continue
        flat = json.dumps(obj, ensure_ascii=False)
        shas = set(SHA64.findall(flat))
        cmpkey = [k for k in re.findall(r'"([^"]*)"\s*:\s*(?:true|false)', flat)
                  if ("동일" in k or "같은가" in k)]
        if len(shas) >= 2 and cmpkey:
            ev.append({"파일": cand, "🔴 서로 다른 sha256 수": len(shas),
                       "🔴 비교 판정 키": cmpkey[:4]})
    return ev


def _wrote_a2(n):
    """⚠ 구판 자 — 문서에 「A-2」라는 **글자**가 있는가(981 까지 쓰던 것)."""
    ev = []
    for cand in ("docs/판정_%d.md" % n, "runners/out%d_house.json" % n,
                 "docs/ledger_%d.json" % n, "docs/card_%d.md" % n):
        q = ROOT / cand
        if q.is_file() and "A-2" in q.read_text(encoding="utf-8", errors="replace"):
            ev.append(cand)
    return ev


def a2_cycles(cycle=None):
    """🔴🔴 A-2 를 **돌린** 사이클을 저장소에서 센다 · 🔴 **도는 사이클을 뺀다.**"""
    rows = collections.OrderedDict()
    for p in sorted((ROOT / "docs").glob("판정_9*.md")):
        m = re.match(r"판정_(\d+)\.md$", p.name)
        if not m:
            continue
        n = int(m.group(1))
        if n < A2_FIRST:
            continue
        ran, wrote = _ran_a2(n), _wrote_a2(n)
        rows["노트 %d" % n] = collections.OrderedDict([
            ("🔴 판정문이 있나", True),
            ("🔴🔴 A-2 를 «돌렸다」는 물증(두 sha + 비교 판정)", ran or "없음"),
            ("🔴🔴🔴 돌렸다고 셀 수 있나(신판)", bool(ran)),
            ("⚠ 「A-2」라는 «글자»를 담은 파일(구판)", wrote or "없음"),
            ("⚠ 적었다고 셀 수 있나(구판)", bool(wrote)),
            ("🔴🔴 도는 사이클 자신인가(순환)",
             bool(cycle is not None and n == cycle)),
        ])
    def _cnt(key, excl):
        it = [v for k, v in rows.items()
              if not (excl and v["🔴🔴 도는 사이클 자신인가(순환)"])]
        return sum(1 for v in it if v[key]), len(it)
    return rows, {
        "신판 포함": _cnt("🔴🔴🔴 돌렸다고 셀 수 있나(신판)", False),
        "신판 정본(도는 사이클 뺌)": _cnt("🔴🔴🔴 돌렸다고 셀 수 있나(신판)", True),
        "구판 포함": _cnt("⚠ 적었다고 셀 수 있나(구판)", False),
        "구판 정본(도는 사이클 뺌)": _cnt("⚠ 적었다고 셀 수 있나(구판)", True),
    }


def stage_house(ref, cycle):
    t0 = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cs0 = LG.code_stamp(RAN)
    head = _git(["show", "HEAD:" + DEN])
    main_b = _git(["show", "main:" + DEN])
    disk = (ROOT / DEN).read_bytes()
    sha_head = hashlib.sha256(head).hexdigest()
    sha_main = hashlib.sha256(main_b).hexdigest()
    sha_disk = hashlib.sha256(disk).hexdigest()
    #: 🔴🔴 조항 60 — **분모가 다른 두 수를 이어 붙이지 않는다.** 따로 센다.
    n_lay_main, dup_main = _dups(main_b.decode("utf-8"))
    n_lay_disk, dup_disk = _dups(disk.decode("utf-8"))
    hj = json.loads(head.decode("utf-8"))
    mj = json.loads(main_b.decode("utf-8"))
    dj = json.loads(disk.decode("utf-8"))
    try:
        prs = json.loads(subprocess.check_output(
            ["gh", "pr", "list", "--state", "open", "--json", "number"],
            cwd=str(ROOT)).decode("utf-8"))
        n_pr, pr_err = len(prs), None
    except Exception as e:                                         # noqa: BLE001
        n_pr, pr_err = None, "%s: %s" % (type(e).__name__, e)
    br = _git(["symbolic-ref", "-q", "HEAD"]).decode().strip()
    same = bool(sha_head == sha_disk)
    added = [k for k in dj if k not in hj]
    lost = [k for k in hj if k not in dj]
    changed = [k for k in hj if k in dj and hj[k] != dj[k]]
    mine = "노트 %s" % cycle
    benign = bool((not same) and not lost and not changed and added == [mine])
    rows, cnts = a2_cycles(cycle)

    out = collections.OrderedDict()
    out["무엇"] = ("982 §0 — 🔴 **집을 닫았나**(규칙 A 배관 머지 · A-2). "
                 "🔴🔴 **조항 60** — `main` 과 디스크의 층 수를 «따로» 센다 · "
                 "🔴🔴 **A-2 분자를 「적었나」에서 「돌렸나」로 바꿨다**")
    out["🔴 축"] = "자기 자(수리 레인)"
    out["🔴 도는 사이클"] = cycle
    out["🔴 지금 가지"] = br
    out["🔴 HEAD"] = _git(["rev-parse", "HEAD"]).decode().strip()
    out["🔴 main"] = _git(["rev-parse", "main"]).decode().strip()
    out["🔴🔴 main 원장 항목 수"] = len(mj)
    out["🔴🔴 HEAD 원장 항목 수"] = len(hj)
    out["🔴🔴 디스크 원장 항목 수"] = len(dj)
    #: 🔴🔴🔴 조항 60 — 「main 원장 N · 전 층위 M 층」을 붙이려면 **둘 다 main 에서** 재야 한다
    out["🔴🔴🔴 원장 층 수(전 층위) — `main`"] = n_lay_main
    out["🔴🔴🔴 원장 층 수(전 층위) — 디스크"] = n_lay_disk
    out["🔴🔴 두 층 수가 같은가"] = bool(n_lay_main == n_lay_disk)
    out["🔴🔴 원장 중복 키(전 층위) — `main`"] = len(dup_main)
    out["🔴🔴 원장 중복 키(전 층위) — 디스크"] = len(dup_disk)
    out["🔴 중복 키 목록(디스크)"] = dup_disk[:20]
    out["🔴 왜 이 칸이 둘인가"] = (
        "🔴 **조항 60** — 981 은 「`main` 원장 1183 · 키 중복 0(전 층위 2508 층)」이라 "
        "한 문장에 붙였는데 **2508 은 디스크 값**이고 `main` 은 2505 였다. "
        "🔴 **분모가 다른 두 수를 이어 붙이지 않는다**")
    out["🔴🔴 HEAD 판 sha256"] = sha_head
    out["🔴🔴 main 판 sha256"] = sha_main
    out["🔴🔴 디스크 판 sha256"] = sha_disk
    out["🔴🔴🔴 HEAD 와 디스크가 바이트 동일한가"] = same
    out["🔴 이 판정이 무엇에서 오나"] = (
        "🔴 위의 두 sha256 «문자열 비교» 하나. 리터럴이 아니고 한쪽만 인용하지도 않는다")
    out["🔴🔴 갈렸다면 왜 갈렸나"] = collections.OrderedDict([
        ("🔴 디스크에만 있는 항목", added),
        ("🔴🔴 HEAD 에만 있는 항목(= 지워진 것)", lost),
        ("🔴 값이 달라진 항목", changed),
        ("🔴🔴🔴 갈린 것이 「이 사이클 항목이 아직 안 커밋됐다」 하나인가", benign),
    ])
    out["🔴🔴 열린 PR 수"] = n_pr
    out["🔴 PR 조회 오류"] = pr_err
    out["🔴🔴 A-2 사이클 — 🔴 «돌렸나»로 센다"] = collections.OrderedDict([
        ("🔴🔴🔴 신판 정본(도는 사이클 뺌) 분자/분모",
         "%d / %d" % cnts["신판 정본(도는 사이클 뺌)"]),
        ("🔴 신판 정본 분자", cnts["신판 정본(도는 사이클 뺌)"][0]),
        ("🔴 신판 정본 분모", cnts["신판 정본(도는 사이클 뺌)"][1]),
        ("⚠ 구판(「A-2」라 «적었나») 정본 분자/분모",
         "%d / %d" % cnts["구판 정본(도는 사이클 뺌)"]),
        ("⚠ 신판 포함판(순환)", "%d / %d" % cnts["신판 포함"]),
        ("⚠ 구판 포함판(순환)", "%d / %d" % cnts["구판 포함"]),
        ("🔴🔴 신판과 구판이 갈리나",
         bool(cnts["신판 정본(도는 사이클 뺌)"] != cnts["구판 정본(도는 사이클 뺌)"])),
        ("🔴 자를 바꾼 근거", "🔴 티처 #120 M10 — 「A-2 4/7 은 여전히 「A-2 라 «적었나»」다」"),
        ("🔴 칸별", rows),
    ])
    out["통과"] = bool((same or benign) and len(dup_disk) == 0
                     and len(dup_main) == 0 and n_pr == 0)
    out["🔴🔴 엄격 통과(`HEAD` == 디스크만 본다)"] = bool(
        same and len(dup_disk) == 0 and len(dup_main) == 0 and n_pr == 0)
    out["🔴 이 절의 `통과` 가 뜻하는 것"] = (
        "🔴 **`main` 과 디스크 둘 다 중복 키가 없고, 열린 PR 이 없고, `HEAD` 와 디스크가 "
        "바이트로 같거나 «갈린 것이 이 사이클 자신의 원장 항목 하나뿐»이다.** "
        "🔴 「엄격 통과」 칸은 그 예외 없이 잰 값이다 — 둘 다 싣는다")
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LG.DATA)
    (OUT / "out982_house.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["house"])
    ap.add_argument("--ref", default="")
    ap.add_argument("--cycle", type=int, default=982)
    a = ap.parse_args()
    r = stage_house(a.ref, a.cycle)
    print(json.dumps({"통과": r["통과"],
                      "A-2(신판)": r["🔴🔴 A-2 사이클 — 🔴 «돌렸나»로 센다"][
                          "🔴🔴🔴 신판 정본(도는 사이클 뺌) 분자/분모"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
