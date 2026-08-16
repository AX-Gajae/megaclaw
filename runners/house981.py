#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""981 — 🔴 **집을 닫았나**(규칙 A · A-2)를 재서 낸다.

🔴 **980 에서 무엇이 틀렸나 (티처 #119 치명 4 · 중대 10).**
① **A-2 사이클 수 `4 / 7` 은 자기 판정문을 읽는 순환이다** — `house980.a2_cycles()` 가
   `docs/판정_9NN.md` 를 훑으면서 **자기 사이클의 판정문**을 분자에도 분모에도 넣었다.
   그 판정문은 그 러너가 도는 시점에는 **아직 안 씌었거나 자기가 쓴 것**이다.
   🔴 **981 은 「도는 사이클」을 분자·분모에서 뺀 값을 정본으로 낸다**(포함판도 같이 낸다).
② 🔴 **`HEAD` 와 디스크의 두 sha 중 하나만 인용해 「바이트 동일」이라 적었다.**
   **981 은 둘 다 산출물에 싣고, 판정 키도 둘의 «비교»에서 온다.**

씀:
    python3 runners/house981.py --stage house --ref <40자 sha> --cycle 981
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

RAN = ("runners/house981.py", "runners/ledger.py", "runners/predict971.py")
OUT = ROOT / "runners"
DEN = "data/lab/denominator.json"

#: 🔴 A-2 는 974 가 개정해 신설됐다 — 그 앞은 분모 밖이다(`docs/루프.md` 규칙 A-2).
A2_FIRST = 974


def _git(args):
    return subprocess.check_output(["git"] + args, cwd=str(ROOT))


def _dups(txt):
    """🔴 **전 층위** 중복 키를 센다(맨 위만 보면 안 된다)."""
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


def a2_cycles(cycle=None):
    """🔴🔴 A-2 를 돌린 사이클을 **저장소에서 센다** · 🔴 **도는 사이클을 뺀다.**"""
    rows = collections.OrderedDict()
    for p in sorted((ROOT / "docs").glob("판정_9*.md")):
        m = re.match(r"판정_(\d+)\.md$", p.name)
        if not m:
            continue
        n = int(m.group(1))
        if n < A2_FIRST:
            continue
        txt = p.read_text(encoding="utf-8", errors="replace")
        ev = [p.name] if "A-2" in txt else []
        for cand in ("runners/out%d_house.json" % n, "docs/ledger_%d.json" % n,
                     "docs/card_%d.md" % n):
            q = ROOT / cand
            if q.is_file() and "A-2" in q.read_text(encoding="utf-8",
                                                    errors="replace"):
                ev.append(cand)
        rows["노트 %d" % n] = collections.OrderedDict([
            ("🔴 판정문이 있나", True),
            ("🔴 A-2 를 글자로 담은 파일", ev),
            ("🔴 A-2 를 돌렸다고 셀 수 있나", bool(ev)),
            ("🔴🔴 도는 사이클 자신인가(순환)", bool(cycle is not None and n == cycle)),
        ])
    inc_d = len(rows)
    inc_n = sum(1 for v in rows.values() if v["🔴 A-2 를 돌렸다고 셀 수 있나"])
    ex = {k: v for k, v in rows.items() if not v["🔴🔴 도는 사이클 자신인가(순환)"]}
    ex_d = len(ex)
    ex_n = sum(1 for v in ex.values() if v["🔴 A-2 를 돌렸다고 셀 수 있나"])
    return rows, (inc_n, inc_d), (ex_n, ex_d)


def stage_house(ref, cycle):
    t0 = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cs0 = LG.code_stamp(RAN)
    head = _git(["show", "HEAD:" + DEN])
    disk = (ROOT / DEN).read_bytes()
    sha_head = hashlib.sha256(head).hexdigest()
    sha_disk = hashlib.sha256(disk).hexdigest()
    n_layers, dups = _dups(disk.decode("utf-8"))
    top = json.loads(disk.decode("utf-8"))
    try:
        prs = json.loads(subprocess.check_output(
            ["gh", "pr", "list", "--state", "open", "--json", "number"],
            cwd=str(ROOT)).decode("utf-8"))
        n_pr, pr_err = len(prs), None
    except Exception as e:                                         # noqa: BLE001
        n_pr, pr_err = None, "%s: %s" % (type(e).__name__, e)
    br = _git(["symbolic-ref", "-q", "HEAD"]).decode().strip()
    same = bool(sha_head == sha_disk)
    #: 🔴🔴 갈렸으면 **왜 갈렸는지를 잰다** — 「이 사이클 항목이 아직 안 커밋됐다」와
    #: 「데몬이 남의 항목을 지웠다」는 둘이고, 980 은 그 둘을 안 갈랐다.
    hj = json.loads(head.decode("utf-8"))
    dj = json.loads(disk.decode("utf-8"))
    added = [k for k in dj if k not in hj]
    lost = [k for k in hj if k not in dj]
    changed = [k for k in hj if k in dj and hj[k] != dj[k]]
    mine = "노트 %s" % cycle
    benign = bool((not same) and not lost and not changed
                  and added == [mine])
    rows, inc, exc = a2_cycles(cycle)
    out = collections.OrderedDict()
    out["무엇"] = ("981 §0 — 🔴 **집을 닫았나**(규칙 A 배관 머지 · A-2). "
                 "🔴🔴 A-2 수에서 **도는 사이클을 뺀다**(980 의 4/7 은 자기 판정문을 읽는 순환)")
    out["🔴 축"] = "자기 자(수리 레인)"
    out["🔴 도는 사이클"] = cycle
    out["🔴 지금 가지"] = br
    out["🔴 HEAD"] = _git(["rev-parse", "HEAD"]).decode().strip()
    out["🔴🔴 main 원장 항목 수"] = len(hj)
    out["🔴🔴 디스크 원장 항목 수"] = len(top)
    out["🔴 원장 층 수(전 층위)"] = n_layers
    out["🔴🔴 원장 중복 키(전 층위)"] = len(dups)
    out["🔴 중복 키 목록"] = dups[:20]
    #: 🔴🔴 **두 sha 를 둘 다 싣는다**(반증조건 8 · 980 은 하나만 인용했다)
    out["🔴🔴 HEAD 판 sha256"] = sha_head
    out["🔴🔴 디스크 판 sha256"] = sha_disk
    out["🔴🔴🔴 HEAD 와 디스크가 바이트 동일한가"] = same
    out["🔴 이 판정이 무엇에서 오나"] = (
        "🔴 위의 두 sha256 «문자열 비교» 하나. 리터럴이 아니고 한쪽만 인용하지도 않는다")
    out["🔴🔴 갈렸다면 왜 갈렸나"] = collections.OrderedDict([
        ("🔴 디스크에만 있는 항목", added),
        ("🔴🔴 HEAD 에만 있는 항목(= 지워진 것)", lost),
        ("🔴 값이 달라진 항목", changed),
        ("🔴🔴🔴 갈린 것이 「이 사이클 항목이 아직 안 커밋됐다」 하나인가", benign),
        ("🔴 왜 이 칸이 있나",
         "🔴 「데몬이 남의 항목을 지웠다」(2026-08-16 의 실측 사고)와 "
         "「내 항목이 아직 커밋 전이다」는 둘이다. 980 은 그 둘을 안 갈랐다"),
    ])
    out["🔴🔴 열린 PR 수"] = n_pr
    out["🔴 PR 조회 오류"] = pr_err
    out["🔴🔴 A-2 사이클 — **재서 낸다**"] = collections.OrderedDict([
        ("🔴🔴🔴 정본(도는 사이클을 뺀 값) 분자/분모", "%d / %d" % exc),
        ("🔴 정본 분자", exc[0]),
        ("🔴 정본 분모", exc[1]),
        ("⚠ 포함판(순환) 분자/분모", "%d / %d" % inc),
        ("🔴🔴 순환판과 정본판이 갈리나", bool(inc != exc)),
        ("🔴 칸별", rows),
    ])
    out["통과"] = bool((same or benign) and len(dups) == 0 and n_pr == 0)
    out["🔴🔴 엄격 통과(`HEAD` == 디스크만 본다)"] = bool(
        same and len(dups) == 0 and n_pr == 0)
    out["🔴 이 절의 `통과` 가 뜻하는 것"] = (
        "🔴 **원장에 중복 키가 없고, 열린 PR 이 없고, `HEAD` 와 디스크가 바이트로 같거나 "
        "«갈린 것이 이 사이클 자신의 원장 항목 하나뿐»이다**(그 항목은 아직 커밋 전이다). "
        "🔴 「엄격 통과」 칸은 그 예외 없이 잰 값이다 — 둘 다 싣는다")
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LG.DATA)
    (OUT / "out981_house.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["house"])
    ap.add_argument("--ref", default="")
    ap.add_argument("--cycle", type=int, default=981)
    a = ap.parse_args()
    r = stage_house(a.ref, a.cycle)
    print(json.dumps({"통과": r["통과"],
                      "A-2": r["🔴🔴 A-2 사이클 — **재서 낸다**"]["🔴🔴🔴 정본(도는 사이클을 뺀 값) 분자/분모"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
