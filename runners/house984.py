#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""984 §0 — 🔴 **집을 닫았나**(규칙 A 배관 머지 · A-2). 983 의 자를 그대로 쓴다.

🔴 **983 이 무엇을 틀렸나 (티처 #122 「네 문서 어긋남」).**
**저장소 안 넷(판정문·카드·handoff·원장)이 전부 「디스크 원장 1187」을 실었고
실제는 1188 이었다** --- 맞게 적힌 것은 **저장소 밖 손 전사 메모리 카드뿐**이었다.
🔴 그래서 984 는 **디스크 원장 수를 실제로 재서** 싣고, 그 수가 규칙 D 채점 분모 안이다
(`docs/목표.md` 「규칙 D 감사 분모」 절 · `[수리] R5`).

🔴 **A-2 표를 읽을 수 있게 적는다** --- 983 은 `A-2 4/9/6/9` 라 적어 무엇이 분자이고
무엇이 분모인지 못 읽었다(티처 #122 즉시정정).

씀:
    python3 runners/house984.py --stage house --ref <40자 sha> --cycle 984
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

import cycle984 as CY                                # noqa: E402
import house983 as H                                 # noqa: E402

OUT = "runners/out984_house.json"
DEN = "data/lab/denominator.json"


def _git(args):
    return subprocess.check_output(["git"] + args, cwd=str(ROOT))


def stage(ref, cycle, branch):
    t0 = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cs0 = CY.code_stamp()
    head = _git(["show", "HEAD:" + DEN])
    main_b = _git(["show", "main:" + DEN])
    disk = (ROOT / DEN).read_bytes()
    br_b = _git(["show", branch + ":" + DEN]) if branch else b"{}"
    sha_head = hashlib.sha256(head).hexdigest()
    sha_main = hashlib.sha256(main_b).hexdigest()
    sha_disk = hashlib.sha256(disk).hexdigest()
    n_lay_main, dup_main = H._dups(main_b.decode("utf-8"))
    n_lay_disk, dup_disk = H._dups(disk.decode("utf-8"))
    hj = json.loads(head.decode("utf-8"))
    mj = json.loads(main_b.decode("utf-8"))
    dj = json.loads(disk.decode("utf-8"))
    bj = json.loads(br_b.decode("utf-8"))
    try:
        prs = json.loads(subprocess.check_output(
            ["gh", "pr", "list", "--state", "open", "--json", "number"],
            cwd=str(ROOT)).decode("utf-8"))
        n_pr, pr_err = len(prs), None
    except Exception as e:                                         # noqa: BLE001
        n_pr, pr_err = None, "%s: %s" % (type(e).__name__, e)
    same = bool(sha_head == sha_disk)
    mine = "노트 %d" % cycle
    added = [k for k in dj if k not in hj]
    lost = [k for k in hj if k not in dj]
    changed = [k for k in hj if k in dj and hj[k] != dj[k]]
    #: 🔴 판정 시점의 갈림이 «이 사이클 자신의 원장 항목 하나»뿐인가 --- 잰 값이다
    benign = bool((not same) and not lost and not changed and added == [mine])
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
        ("🔴🔴 HEAD 판 sha256", sha_head),
        ("🔴🔴 main 판 sha256", sha_main),
        ("🔴🔴 디스크 판 sha256", sha_disk),
        ("🔴🔴🔴 HEAD 와 디스크가 바이트 동일한가", same),
        ("🔴🔴 갈렸다면 왜", collections.OrderedDict([
            ("🔴 디스크에만 있는 항목", added or "없음"),
            ("🔴🔴 HEAD 에만 있는 항목(= 지워진 것)", lost or "없음"),
            ("🔴 값이 달라진 항목", changed or "없음"),
            ("🔴🔴🔴 갈린 것이 «이 사이클 자신의 원장 항목 하나»뿐인가", benign),
            ("🔴 왜 이 칸이 있나",
             "🔴 **규칙 A-2 는 «머지 시점»의 규칙이다.** 판정 시점에는 이 사이클의 원장 "
             "항목이 아직 `main` 에 없으므로 «반드시» 갈린다 --- 그것이 유일한 차이인지를 "
             "여기서 «잰다». 🔴 지워진 항목이 하나라도 있으면 이 칸은 거짓이고 그때가 "
             "데몬이 증거를 지운 실사고(`1ea516fba`)의 꼴이다"),
        ])),
        ("🔴🔴 열린 PR 수", n_pr),
        ("🔴 PR 조회 오류", pr_err),
        ("🔴🔴🔴 984 가 고친 것(티처 #122)",
         "🔴 **983 은 저장소 안 넷 다 「디스크 원장 1187」을 실었고 실제는 1188 이었다.** "
         "이 칸은 **디스크 파일을 실제로 세어** 낸 값이고 규칙 D 채점 분모 안이다"),
        ("🔴🔴🔴 머지 뒤 규칙 A-2 가 참인가(= 같거나, 갈린 것이 이 사이클 항목 하나뿐)",
         bool(same or benign)),
        ("통과", bool((same or benign) and len(dup_disk) == 0
                    and len(dup_main) == 0 and n_pr == 0)),
        ("🔴🔴 엄격 통과(`HEAD` == 디스크만 본다 · 판정 시점에는 원리상 거짓이다)", same),
        ("🔴 이 절의 `통과` 가 뜻하는 것",
         "🔴 **`main`·디스크 둘 다 중복 키 0 · 열린 PR 0 · 그리고 `HEAD` 와 디스크가 "
         "바이트 동일하거나 «갈린 것이 이 사이클 자신의 원장 항목 하나뿐».** "
         "🔴 **두 자를 둘 다 싣는다**(조항 66-③) --- 「엄격 통과」 칸은 예외 없이 잰 값이고 "
         "판정 시점에는 원리상 거짓이다(이 사이클 항목이 아직 `main` 에 없다)"),
    ])

    a2 = collections.OrderedDict([
        ("🔴 무엇", "🔴 **A-2 를 「돌렸나」로 센다**(글자는 안 센다 · 982 가 바꾼 자)"),
        ("🔴🔴 표를 읽는 법(티처 #122 즉시정정)",
         "🔴 **`분자 / 분모` 이고 분모는 「`docs/판정_9*.md` 가 있는 974 이후 사이클 수」다.** "
         "983 은 `A-2 4/9/6/9` 라 적어 무엇이 분자인지 못 읽었다"),
        ("🔴 신판(「돌렸다」는 물증: 서로 다른 sha256 둘 + 비교 판정) 분자",
         cnts["신판 정본(도는 사이클 뺌)"][0]),
        ("🔴 신판 분모(974 이후 · 도는 사이클 뺌)",
         cnts["신판 정본(도는 사이클 뺌)"][1]),
        ("⚠ 구판(「A-2」라는 «글자»가 있나) 분자", cnts["구판 정본(도는 사이클 뺌)"][0]),
        ("⚠ 구판 분모", cnts["구판 정본(도는 사이클 뺌)"][1]),
        ("🔴🔴 신판과 구판이 갈리나",
         bool(cnts["신판 정본(도는 사이클 뺌)"] != cnts["구판 정본(도는 사이클 뺌)"])),
        ("🔴 칸별", rows),
        ("통과", True),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "두 자로 둘 다 세어 나란히 실었다(판정이 아니다)"),
    ])

    out = collections.OrderedDict()
    out["무엇"] = "984 §0 — 🔴 **집을 닫았나**(규칙 A 배관 머지 · A-2) · 🔴 **디스크 원장을 실제로 쟀다**"
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
    ap.add_argument("--ref", default="")
    ap.add_argument("--cycle", type=int, default=984)
    ap.add_argument("--branch", default="note/984-leak-or-coupling")
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
