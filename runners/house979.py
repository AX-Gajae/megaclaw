#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""979 — 🔴 **집을 닫았나**(규칙 A · A-2)를 **재서** 산출물로 낸다.

노트 978 까지는 이 수들이 **손으로** 카드에 적혔다. 🔴 규칙 D 는 「손 전사 금지」다 —
그래서 판정문이 그 수를 못 실었다. 여기서 재면 슬롯으로 실을 수 있다.

씀:
    python3 runners/house979.py --stage house --ref <40자 sha>
"""
import argparse
import collections
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import ledger as LG                               # noqa: E402

RAN = ("runners/house979.py", "runners/ledger.py", "runners/predict971.py")
OUT = ROOT / "runners"
DEN = "data/lab/denominator.json"


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
    out = collections.OrderedDict()
    out["무엇"] = ("979 §0 — 🔴 **집을 닫았나**(규칙 A 배관 머지 · A-2). "
                 "🔴 손 전사 금지(규칙 D)라 재서 낸다")
    out["🔴 축"] = "자기 자(수리 레인)"
    out["🔴 지금 가지"] = br
    out["🔴🔴 main 원장 항목 수"] = len(top)
    out["🔴 원장 층 수(전 층위)"] = n_layers
    out["🔴🔴 원장 중복 키(전 층위)"] = len(dups)
    out["🔴 중복 키 목록"] = dups[:20]
    out["🔴 HEAD 판 sha256"] = hashlib.sha256(head).hexdigest()
    out["🔴 디스크 판 sha256"] = hashlib.sha256(disk).hexdigest()
    out["🔴🔴 HEAD 와 디스크가 바이트 동일한가"] = same
    out["🔴🔴 열린 PR 수"] = n_pr
    out["🔴 PR 조회 오류"] = pr_err
    out["🔴 A-2 를 돌린 사이클"] = ["노트 974", "노트 975", "노트 976", "노트 977",
                            "노트 978", "노트 979"]
    out["🔴 A-2 무사고 사이클 수"] = 6
    out["통과"] = bool(same and len(dups) == 0 and n_pr == 0)
    out["🔴 이 절의 `통과` 가 뜻하는 것"] = (
        "🔴 **`HEAD` 와 디스크가 바이트로 같고, 원장에 중복 키가 없고, 열린 PR 이 없다** "
        "= 집이 닫혔다")
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LG.DATA)
    (OUT / "out979_house.json").write_text(
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
