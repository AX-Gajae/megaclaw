#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""974 --- 데몬 수리 둘을 **심어서 재현**한다(973 의 `daemonguard973.py` 와 같은 꼴).

🔴 티처 #112 가 잡은 둘:
  ① **`_only_paths` 는 문자열 접두 검사라 `data/ingest/../lab/x.json` 이 통과한다**(실측).
  ② **규칙 A-2 를 강제하는 러너가 0 이다** --- `HEAD ≠ 디스크`면 붉게 적는 게이트가 없다.

씀: python3 runners/daemonfix974.py --ref <40자 sha>
"""
import argparse
import datetime as dt
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import runners.predict971 as P                    # noqa: E402
import runners.harvest_daemon as HD               # noqa: E402

RAN = ("runners/daemonfix974.py", "runners/harvest_daemon.py", "runners/predict971.py")
OUT = ROOT / "runners"

# 🔴 973 판을 **글자 그대로** 옮긴 것 --- 견주려고 둔다. 생산 코드가 아니다.
def only_paths_973(rels, paths):
    return [r for r in rels if any(r == p or r.startswith(p + "/") for p in paths)]


PROBE = [
    ("data/ingest/x.json", True, "PATHS 안 --- 통과해야 한다"),
    ("data/state/y.jsonl", True, "PATHS 안 --- 통과해야 한다"),
    ("data/lab/denominator.json", False, "🔴 원장 --- 막아야 한다"),
    ("data/ingest/../lab/denominator.json", False,
     "🔴🔴 티처 #112 가 잡은 그 구멍 --- `..` 로 원장에 닿는다"),
    ("data/state/../lab/denominator.json", False, "🔴 같은 구멍(다른 뿌리)"),
    ("data/ingest/../../etc/passwd", False, "🔴 저장소 밖"),
    ("/etc/passwd", False, "🔴 절대 경로"),
    ("../outside.json", False, "🔴 뿌리 위"),
    ("data/ingestX/z.json", False, "🔴 접두만 같은 다른 디렉터리"),
    ("data/ingest/./sub/a.json", True, "`./` 는 정규화하면 PATHS 안이다"),
]


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def code_stamp():
    files = sorted(glob.glob(str(ROOT / "lab/*.py")))
    files += [str(ROOT / r) for r in RAN]
    return {str(Path(p).relative_to(ROOT)): P._sha_file(p)
            for p in sorted(set(files)) if Path(p).is_file()}


def stamp_block(ref, cs0, cs1, t0):
    runner, ok = {}, 0
    for r in RAN:
        disk = P._sha_file(str(ROOT / r))
        try:
            cm = hashlib.sha256(subprocess.check_output(
                ["git", "show", "%s:%s" % (ref, r)], cwd=str(ROOT))).hexdigest()
        except Exception:                                          # noqa: BLE001
            cm = None
        runner[r] = {"디스크 sha256": disk, "커밋 blob sha256": cm, "일치": disk == cm}
        ok += 1 if disk == cm else 0
    return {
        "언제(시작)": t0, "언제(끝)": _now(),
        "시작 code_stamp 요약": hashlib.sha256(
            json.dumps(cs0, sort_keys=True).encode()).hexdigest(),
        "끝 code_stamp 요약": hashlib.sha256(
            json.dumps(cs1, sort_keys=True).encode()).hexdigest(),
        "🔴 시작=끝": cs0 == cs1, "분모: 도장이 덮는 파일": len(cs1),
        "🔴 자료 지문": {"(자료 안 읽는 러너다)": None}, "분모: 연 자료 파일": 0,
        "🔴 F1 기준 ref(준 대로)": ref,
        "🔴 40자 고정 sha 인가": bool(re.fullmatch(r"[0-9a-f]{40}", ref or "")),
        "🔴 기준 ref 가 0000…0000 인가": bool(re.fullmatch(r"0{40}", ref or "")),
        "러너별": runner, "🔴 분자/분모": "%d / %d" % (ok, len(RAN)),
        "🔴 F5 통과": ok == len(RAN) and bool(re.fullmatch(r"[0-9a-f]{40}", ref or ""))
        and not re.fullmatch(r"0{40}", ref or ""),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="")
    a = ap.parse_args()
    t0 = _now()
    cs0 = code_stamp()
    paths = list(HD.PATHS)

    rels = [x[0] for x in PROBE]
    got973 = set(only_paths_973(rels, paths))
    got974 = set(HD._only_paths(rels))
    table, ok973, ok974 = [], 0, 0
    for rel, want, why in PROBE:
        p973, p974 = rel in got973, rel in got974
        ok973 += 1 if p973 == want else 0
        ok974 += 1 if p974 == want else 0
        table.append({"경로": rel, "통과해야 하나": want, "왜": why,
                      "973 판이 통과시켰나": p973, "974 판이 통과시켰나": p974,
                      "🔴 973 이 틀렸나": p973 != want,
                      "🔴 974 가 틀렸나": p974 != want})
    holes = [r["경로"] for r in table if r["🔴 973 이 틀렸나"] and not r["🔴 974 가 틀렸나"]]

    gate = HD.head_vs_disk()
    gate_neg = HD.head_vs_disk("data/ingest/이런파일은없다.json")   # 🔴 음성 대조

    out = {
        "무엇": "974 --- 데몬 수리 둘을 심어서 재현(`_only_paths` 경로 정규화 · A-2 강제 게이트)",
        "🔴 근거": "티처 #112 중대 --- 「문자열 접두 검사라 `../` 가 통과한다」 · 「A-2 를 강제하는 러너 0」",
        "PATHS": paths,
        "🔴 심은 경로": len(PROBE),
        "🔴 973 판 맞은 칸": "%d / %d" % (ok973, len(PROBE)),
        "🔴🔴 974 판 맞은 칸": "%d / %d" % (ok974, len(PROBE)),
        "🔴🔴 974 가 새로 막은 구멍": holes,
        "🔴 그 수": len(holes),
        "칸별": table,
        "🔴🔴 A-2 강제 게이트(원장)": gate,
        "🔴 A-2 게이트 음성 대조(없는 파일)": gate_neg,
        "🔴 게이트가 음성 대조에서 위반을 외치나(외쳐야 한다)": gate_neg["🔴 A-2 위반"],
        "🔴 도는 데몬은 아직 옛 코드인가": {
            "왜": "규칙 B --- 데몬을 안 죽인다. 고침은 **다음 기동부터** 문다.",
            "디스크 harvest_daemon.py sha256": P._sha_file(str(ROOT / "runners/harvest_daemon.py")),
        },
    }
    out["🔴 도장"] = stamp_block(a.ref, cs0, code_stamp(), t0)
    (OUT / "out974_daemonfix.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "칸별"},
                     ensure_ascii=False, indent=1)[:2500])
    return 0


if __name__ == "__main__":
    sys.exit(main())
