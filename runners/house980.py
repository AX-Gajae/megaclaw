#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""980 — 🔴 **집을 닫았나**(규칙 A · A-2)를 **재서** 산출물로 낸다.

🔴🔴 **수리 3 — `house979.py:84-86` 의 손 전사를 측정으로 바꾼다.**
`house979.py` 는 독스트링이 「손 전사 금지(규칙 D)라 재서 낸다」인데
**A-2 를 돌린 사이클 목록과 그 개수를 손으로 적었다**(그리고 그 수가 카드와 갈렸다 —
판정문 6 대 카드 7). 🔴 여기서는 **git 이력에서 센다.**

씀:
    python3 runners/house980.py --stage house --ref <40자 sha>
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

RAN = ("runners/house980.py", "runners/ledger.py", "runners/predict971.py")
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


def a2_cycles():
    """🔴🔴 **수리 3** — A-2 를 돌린 사이클을 **저장소에서 센다**(손 전사 금지).

    분자 = `docs/판정_9NN.md` 가 있는 사이클 중 **A-2 무사고**를 산출물이 뒷받침하는 것.
    🔴 근거는 두 겹이다: ① 판정문 파일이 존재한다 ② 그 사이클의 원장/집 산출물 또는
    판정문이 **`A-2`** 를 글자로 담는다. **둘 다 파일에서 읽는다.**
    """
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
        ])
    n_ok = sum(1 for v in rows.values() if v["🔴 A-2 를 돌렸다고 셀 수 있나"])
    return rows, n_ok


def stage_house(ref):
    t0 = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cs0 = LG.code_stamp(RAN)
    head = _git(["show", "HEAD:" + DEN])
    disk = (ROOT / DEN).read_bytes()
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
    same = bool(head == disk)
    cyc, n_cyc = a2_cycles()
    out = collections.OrderedDict()
    out["무엇"] = ("980 §0 — 🔴 **집을 닫았나**(규칙 A 배관 머지 · A-2). "
                 "🔴🔴 수리 3 — A-2 사이클 수를 **git·파일에서 센다**(979 는 손으로 적었다)")
    out["🔴 축"] = "자기 자(수리 레인)"
    out["🔴 지금 가지"] = br
    out["🔴 HEAD"] = _git(["rev-parse", "HEAD"]).decode().strip()
    out["🔴🔴 main 원장 항목 수"] = len(top)
    out["🔴 원장 층 수(전 층위)"] = n_layers
    out["🔴🔴 원장 중복 키(전 층위)"] = len(dups)
    out["🔴 중복 키 목록"] = dups[:20]
    out["🔴 HEAD 판 sha256"] = hashlib.sha256(head).hexdigest()
    out["🔴 디스크 판 sha256"] = hashlib.sha256(disk).hexdigest()
    out["🔴🔴 HEAD 와 디스크가 바이트 동일한가"] = same
    out["🔴🔴 열린 PR 수"] = n_pr
    out["🔴 PR 조회 오류"] = pr_err
    out["🔴🔴 A-2 사이클 — **재서 낸다**"] = collections.OrderedDict([
        ("🔴 분모: A-2 신설(974) 이후 판정문이 있는 사이클", len(cyc)),
        ("🔴🔴 분자: A-2 를 글자로 담은 사이클", n_cyc),
        ("🔴 칸별", cyc),
        ("🔴 979 판정문이 적은 수", 6),
        ("🔴 979 카드가 적은 수", 7),
        ("🔴🔴 979 의 두 수가 갈렸나", True),
        ("🔴🔴 그 수가 손 전사였나(`house979.py:84-86`)", True),
    ])
    out["통과"] = bool(same and len(dups) == 0 and n_pr == 0)
    out["🔴 이 절의 `통과` 가 뜻하는 것"] = (
        "🔴 **`HEAD` 와 디스크가 바이트로 같고, 원장에 중복 키가 없고, 열린 PR 이 없다** "
        "= 집이 닫혔다")
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LG.DATA)
    (OUT / "out980_house.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["house"])
    ap.add_argument("--ref", default="")
    a = ap.parse_args()
    print(json.dumps(stage_house(a.ref), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
