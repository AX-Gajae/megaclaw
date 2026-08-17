#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""987 §0 — 🔴 **집을 닫았나**(규칙 A 배관 머지 · A-2) · 원장 지문은 **자기 항목 제외 고정점**.

986 판(`house986.py`)의 자를 그대로 물려받는다. **바뀐 것 둘뿐이다:**
1. `SELF` 가 `노트 987` 이고 `REG_CHANGED` 가 `["노트 986"]` 다 ---
   🔴 987 은 **986 의 두 문장에 정정을 얹으므로** 원장 `노트 986` 항목이 «반드시» 달라진다.
   **사전등록 §2-2 가 그것을 측정 «전»에 박았다.**
2. **PR 본문(`docs/pr_987.md`)이 규칙 D 대상이라** 그 파일의 존재와 sha 를 여기서도 센다.

씀:
    python3 runners/house987.py --stage house --ref <40자 sha> --branch <가지>
"""
import argparse
import collections
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

import cycle987 as CY                                   # noqa: E402
import house983 as H                                    # noqa: E402

OUT = "runners/out987_house.json"
DEN = "data/lab/denominator.json"
SELF = "노트 987"
#: 🔴 사전등록 §2-2 가 «측정 전»에 등록한 「값이 달라져도 되는 항목」
REG_CHANGED = ["노트 986"]
PR_BODY = "docs/pr_987.md"


def _git(args):
    return subprocess.check_output(["git"] + args, cwd=str(ROOT))


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _minus_self(raw_bytes, key=SELF):
    """🔴🔴 **자기 항목을 뺀 판의 sha256** --- 이 값이 «고정점»이다(985 신설)."""
    d = json.loads(raw_bytes.decode("utf-8"))
    d.pop(key, None)
    return _sha(json.dumps(d, ensure_ascii=False, sort_keys=True).encode("utf-8")), len(d)


def stage(ref, cycle, branch):
    t0 = CY.now()
    CY.begin(ref)
    cs0 = CY.code_stamp()
    head = _git(["show", "HEAD:" + DEN])
    main_b = _git(["show", "main:" + DEN])
    disk = (ROOT / DEN).read_bytes()
    br_b = _git(["show", branch + ":" + DEN]) if branch else b"{}"
    n_lay_main, dup_main = H._dups(main_b.decode("utf-8"))
    n_lay_disk, dup_disk = H._dups(disk.decode("utf-8"))
    hj, mj, dj, bj = (json.loads(x.decode("utf-8"))
                      for x in (head, main_b, disk, br_b))
    fx_head, n_head_ms = _minus_self(head)
    fx_disk, n_disk_ms = _minus_self(disk)
    fx_br, n_br_ms = _minus_self(br_b)
    try:
        prs = json.loads(subprocess.check_output(
            ["gh", "pr", "list", "--state", "open", "--json", "number"],
            cwd=str(ROOT)).decode("utf-8"))
        n_pr, pr_err = len(prs), None
    except Exception as e:                                         # noqa: BLE001
        n_pr, pr_err = None, "%s: %s" % (type(e).__name__, e)
    same = bool(_sha(head) == _sha(disk))
    added = [k for k in dj if k not in hj]
    lost = [k for k in hj if k not in dj]
    changed = [k for k in hj if k in dj and hj[k] != dj[k]]
    strict = bool((not same) and not lost and not changed and added == [SELF])
    benign = bool((not same) and not lost and added == [SELF]
                  and set(changed) <= set(REG_CHANGED))
    rows, cnts = H.a2_cycles(cycle)

    close = collections.OrderedDict([
        ("🔴 지금 가지(`git symbolic-ref HEAD`)",
         _git(["symbolic-ref", "-q", "HEAD"]).decode().strip()),
        ("🔴 HEAD", _git(["rev-parse", "HEAD"]).decode().strip()),
        ("🔴 main", _git(["rev-parse", "main"]).decode().strip()),
        ("🔴 이 사이클 가지", branch),
        ("🔴🔴 main 원장 항목 수", len(mj)),
        ("🔴🔴 HEAD 원장 항목 수", len(hj)),
        ("🔴🔴🔴 디스크 원장 항목 수(🔴 실제로 쟀다)", len(dj)),
        ("🔴🔴 이 사이클 가지 원장 항목 수", len(bj)),
        ("🔴 원장 층 수(전 층위) — `main`", n_lay_main),
        ("🔴 원장 층 수(전 층위) — 디스크", n_lay_disk),
        ("🔴 원장 중복 키(전 층위) — `main`", len(dup_main)),
        ("🔴 원장 중복 키(전 층위) — 디스크", len(dup_disk)),
        ("🔴🔴🔴 원장 sha256(자기 항목 제외 · 🔴 이것이 «고정점»이다) — 디스크", fx_disk),
        ("🔴🔴 원장 sha256(자기 항목 제외) — `HEAD`", fx_head),
        ("🔴🔴 원장 sha256(자기 항목 제외) — 이 사이클 가지", fx_br),
        ("🔴 자기 항목을 뺀 항목 수 — 디스크 / `HEAD` / 가지",
         [n_disk_ms, n_head_ms, n_br_ms]),
        ("⚠ 원장 sha256(전량) — `HEAD`(🔴 잰 시각의 값이다)", _sha(head)),
        ("⚠ 원장 sha256(전량) — `main`", _sha(main_b)),
        ("⚠ 원장 sha256(전량) — 디스크(🔴 잰 시각의 값이다)", _sha(disk)),
        ("⚠ 이 러너가 돈 시각(UTC)", t0),
        ("🔴🔴🔴 HEAD 와 디스크가 바이트 동일한가", same),
        ("🔴🔴 갈렸다면 왜", collections.OrderedDict([
            ("🔴 디스크에만 있는 항목", added or "없음"),
            ("🔴🔴 HEAD 에만 있는 항목(= 지워진 것)", lost or "없음"),
            ("🔴 값이 달라진 항목", changed or "없음"),
            ("🔴🔴 사전등록 §2-4 가 «측정 전»에 등록한 「값이 달라져도 되는 항목」", REG_CHANGED),
            ("⚠ 엄격 자(값이 달라진 항목이 «하나도» 없어야 한다)", strict),
            ("🔴🔴🔴 갈린 것이 «이 사이클 자신의 원장 항목 하나»뿐인가", benign),
            ("🔴 두 자가 갈리나(= 등록한 정정 때문에)", bool(strict != benign)),
            ("🔴 왜 자를 넓혔나",
             "🔴 **사전등록 §2-2 가 986 의 두 문장(「원리상 못 재는 설계」 · "
             "「δ 를 아무리 키워도」)에 정정을 «얹으라» 했고 그러면 원장 `노트 986` 항목이 "
             "«반드시» 달라진다.** 🔴 넓힌 것은 **이름 하나**뿐이고 그 이름을 여기 박았다 --- "
             "조항 60-나 개정판 요건 셋(사전 등록 ✅ · 전후 병기 ✅ · 잰 날 것 게재 ✅)"),
        ])),
        ("🔴🔴 열린 PR 수", n_pr),
        ("🔴 PR 조회 오류", pr_err),
        ("🔴🔴🔴 머지 뒤 규칙 A-2 가 참인가(= 같거나, 갈린 것이 등록한 것뿐)",
         bool(same or benign)),
        # ── 🔴 986 신설 --- PR 본문도 규칙 D 대상이라 존재를 «센다» ──────
        ("🔴🔴 PR 본문 파일(규칙 D 여섯째 대상)", collections.OrderedDict([
            ("경로", PR_BODY),
            ("있나", (ROOT / PR_BODY).is_file()),
            ("sha256", CY.sha_file(PR_BODY)),
            ("🔴 왜 여기서 세나",
             "🔴 **PR #243 본문이 네 곳에서 문서와 달랐다**(티처 #124 C2). "
             "987 도 PR 본문을 **치환표에서 짓고** 규칙 D 분모에 넣는다"),
        ])),
        ("통과", bool((same or benign) and len(dup_disk) == 0
                    and len(dup_main) == 0 and n_pr == 0)),
        ("🔴🔴 엄격 통과(`HEAD` == 디스크만 본다 · 판정 시점에는 원리상 거짓이다)", same),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **`main`·디스크 둘 다 중복 키 0 · 열린 PR 0 · 그리고 `HEAD` 와 디스크가 "
         "바이트 동일하거나 «갈린 것이 등록한 항목뿐».**"),
    ])

    a2 = collections.OrderedDict([
        ("🔴 무엇", "🔴 **A-2 를 「돌렸나」로 센다**(글자는 안 센다 · 982 가 바꾼 자)"),
        ("🔴 신판(「돌렸다」는 물증: 서로 다른 sha256 둘 + 비교 판정) 분자",
         cnts["신판 정본(도는 사이클 뺌)"][0]),
        ("🔴 신판 분모(974 이후 · 도는 사이클 뺌)", cnts["신판 정본(도는 사이클 뺌)"][1]),
        ("⚠ 구판(「A-2」라는 «글자»가 있나) 분자", cnts["구판 정본(도는 사이클 뺌)"][0]),
        ("⚠ 구판 분모", cnts["구판 정본(도는 사이클 뺌)"][1]),
        ("🔴🔴 신판과 구판이 갈리나",
         bool(cnts["신판 정본(도는 사이클 뺌)"] != cnts["구판 정본(도는 사이클 뺌)"])),
        ("🔴 칸별", rows),
        ("통과", bool(cnts["신판 정본(도는 사이클 뺌)"][1] > 0
                    and cnts["구판 정본(도는 사이클 뺌)"][1] > 0)),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "🔴 **두 자가 둘 다 «분모를 냈는가»** 하나다"),
    ])

    out = collections.OrderedDict()
    out["무엇"] = "987 §0 — 🔴 **집을 닫았나**(규칙 A 배관 머지 · A-2)"
    out["🔴 축"] = "자기 자(집 닫기)"
    out["🔴 도는 사이클"] = cycle
    out["§0-가 🔴🔴 집을 닫았나"] = close
    out["§0-나 🔴 A-2 사이클 계수"] = a2
    out["통과"] = bool(close["통과"] and a2["통과"])
    CY.write(OUT, out, ref, cs0, t0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["house"])
    ap.add_argument("--ref", required=True)
    ap.add_argument("--cycle", type=int, default=987)
    ap.add_argument("--branch", default="note/987-ceiling-identity-fixed-ref")
    a = ap.parse_args()
    r = stage(a.ref, a.cycle, a.branch)
    c = r["§0-가 🔴🔴 집을 닫았나"]
    print(json.dumps({
        "통과": r["통과"],
        "main 원장": c["🔴🔴 main 원장 항목 수"],
        "디스크 원장": c["🔴🔴🔴 디스크 원장 항목 수(🔴 실제로 쟀다)"],
        "가지 원장": c["🔴🔴 이 사이클 가지 원장 항목 수"],
        "HEAD==디스크": c["🔴🔴🔴 HEAD 와 디스크가 바이트 동일한가"],
        "열린 PR": c["🔴🔴 열린 PR 수"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
