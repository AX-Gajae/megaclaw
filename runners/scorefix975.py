#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""975 --- **채점기의 분모를 고친다** (티처 #113 3순위 · 수리 레인 · 상한 5).

수리 다섯을 **묶지 않는다**. 이 러너는 그 중 셋(ⓑ 일부·ⓒ·ⓓ·ⓔ)의 **실측**을 낸다.

- **수리 2(ⓑ)** 「출처 키 경로 일치」 채점기의 **양성 대조** --- `525 → 524` 를
  974 판(값 집합 일치)은 **못 잡고** 975 판(키 경로 일치)은 **잡는다**.
- **수리 3(ⓒ)** `meta965` 의 `통과` 키 규칙 --- `exact` 분모가 **0** 인가(= 죽은 채점).
- **수리 4(ⓓ)** `predict972.perm_null` 의 부호 일관성 p --- **관측 양수 수를 본다**.
- **수리 5(ⓔ)** `harvest_daemon.head_vs_disk` --- **진짜 기전에 발화하는가** ·
  **데몬이 부르는가**.

씀:
    python3 runners/scorefix975.py --stage scorefix --ref <40자 sha>
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
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for p in (str(ROOT), str(ROOT / "runners")):
    if p not in sys.path:
        sys.path.insert(0, p)

import runners.predict971 as P                    # noqa: E402
import meta965 as M                               # noqa: E402
import harvest_daemon as HD                       # noqa: E402
import ledger975 as LG                            # noqa: E402

RAN = ("runners/scorefix975.py", "runners/ledger975.py", "runners/meta965.py",
       "runners/harvest_daemon.py", "runners/predict972.py", "runners/predict971.py")
OUT = ROOT / "runners"
SEED = 975

R974 = ["runners/precision974.py", "runners/loso974.py", "runners/ledger974.py",
        "runners/daemonfix974.py"]
R975 = ["runners/c4_975.py", "runners/precfix975.py", "runners/scorefix975.py",
        "runners/ledger975.py", "runners/note975_gen.py"]


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
        "🔴 F1 기준 ref(준 대로)": ref,
        "🔴 40자 고정 sha 인가": bool(re.fullmatch(r"[0-9a-f]{40}", ref or "")),
        "🔴 기준 ref 가 0000…0000 인가": bool(re.fullmatch(r"0{40}", ref or "")),
        "러너별": runner, "🔴 분자/분모": "%d / %d" % (ok, len(RAN)),
        "🔴 F5 통과": ok == len(RAN) and bool(re.fullmatch(r"[0-9a-f]{40}", ref or ""))
        and not re.fullmatch(r"0{40}", ref or ""),
    }


# ══════════════════════════════════════════════════════════════════════
def a2_controls():
    """🔴 수리 5 --- **진짜 기전(양쪽에 있고 바이트가 다름)** 에 발화하는가."""
    tmp = tempfile.mkdtemp(prefix="a2ctl975_")
    try:
        sub = Path(tmp)
        (sub / "data/lab").mkdir(parents=True)
        (sub / "data/lab/denominator.json").write_text('{"a": 1}\n', encoding="utf-8")
        for c in (["git", "init", "-q"], ["git", "add", "-A"]):
            subprocess.run(c, cwd=tmp, capture_output=True)
        subprocess.run(["git", "-c", "user.email=a@b", "-c", "user.name=a",
                        "commit", "-q", "-m", "x"], cwd=tmp, capture_output=True)
        same = HD.head_vs_disk(root=tmp)
        # 🔴 양성 대조 --- **양쪽에 있고 바이트가 다르다**(972 사고의 기전)
        (sub / "data/lab/denominator.json").write_text('{"a": 2}\n', encoding="utf-8")
        diff = HD.head_vs_disk(root=tmp)
        # 🔴 음성 대조 그 하나 --- 974 가 쓴 「양쪽 다 없음」
        none = HD.head_vs_disk("data/lab/이런파일은없다.json", root=tmp)
        # 🔴 음성 대조 둘 --- 디스크에만 있다
        (sub / "data/lab/새것.json").write_text("{}\n", encoding="utf-8")
        onlyd = HD.head_vs_disk("data/lab/새것.json", root=tmp)
        return collections.OrderedDict([
            ("① 양쪽에 있고 같다", same), ("🔴🔴 ② 양쪽에 있고 다르다(진짜 기전)", diff),
            ("③ 양쪽 다 없다(974 의 음성 대조)", none), ("④ 디스크에만 있다", onlyd),
            ("🔴 ② 에서만 A-2 위반이 나는가", bool(
                diff["🔴 A-2 위반"] and not same["🔴 A-2 위반"]
                and not none["🔴 A-2 위반"] and not onlyd["🔴 A-2 위반"])),
            ("🔴 974 판이었다면 ③ 도 위반으로 셌다",
             "974 판 `same = bool(blob) and blob == disk` 는 blob 이 비면 False → 위반"),
        ])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def daemon_calls_gate():
    """🔴 수리 5 --- **데몬 본체가 게이트를 실제로 부르는가**(974 는 0 이었다)."""
    src = (ROOT / "runners/harvest_daemon.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id in ("head_vs_disk", "a2_gate_tick"):
            calls.append({"줄": node.lineno, "부른 이름": node.func.id})
    inmain = [c for c in calls if c["줄"] > src[:src.index("def main()")].count("\n")]
    return {"🔴 데몬 안에서 게이트를 부르는 자리": calls,
            "🔴 분자/분모": "%d / %d" % (len(calls), max(len(calls), 1)),
            "🔴 `main()` 뒤에서 부르는 자리": len(inmain),
            "🔴🔴 데몬이 부르는가": len(inmain) > 0,
            "🔴 974 실측": "0 --- 함수만 있고 부르는 자리가 없었다(탐침이지 게이트가 아니다)",
            "⚠ 도는 프로세스는 옛 코드다":
                "규칙 B 로 안 죽인다 --- 이 고침은 **다음 기동부터** 문다"}


def passkey_census(rels):
    out = collections.OrderedDict()
    for rel in rels:
        p = ROOT / rel
        if not p.is_file():
            out[rel] = {"🔴 파일이 없다": True}
            continue
        src = p.read_text(encoding="utf-8")
        c = M.passkey_census(rel, ast.parse(src))
        c["줄 수"] = src.count("\n") + 1
        out[rel] = c
    return out


def stage_scorefix(ref: str) -> dict:
    t0 = _now()
    cs0 = code_stamp()

    # ── 수리 3 --- `통과` 키 규칙 ────────────────────────────────────────
    c974 = passkey_census(R974)
    c975 = passkey_census(R975)
    n974 = sum(v.get("줄 수", 0) for v in c974.values())
    dead974 = [k for k, v in c974.items()
               if v.get("🔴🔴 정확 일치 분모가 0 인가(= 이 파일에서 965 판 채점은 죽었다)")]
    dead975 = [k for k, v in c975.items()
               if v.get("🔴🔴 정확 일치 분모가 0 인가(= 이 파일에서 965 판 채점은 죽었다)")]

    # ── 수리 2 --- 「출처 키 경로 일치」 채점기의 양성 대조 ────────────────
    ctl = LG.keypath_control()

    # ── 수리 4 --- 부호 일관성 p ────────────────────────────────────────
    fx = OUT / "out975_factors.json"
    pn = (json.loads(fx.read_text(encoding="utf-8"))
          ["🔴 3순위 ⓓ 대조 --- 974 LOSO 를 이 주행에서 다시"]) if fx.is_file() else {}

    out = {
        "무엇": "975 --- 채점기의 분모를 고친다(수리 레인)",
        "🔴 축": "축은 안 민다 --- 자에 대한 자다",
        "사전등록": "docs/prereg_975_c4.md §6",
        "🔴🔴 수리 3 --- `meta965` 의 `통과` 키 규칙": {
            "🔴 974 러너 넷": c974,
            "🔴 974 러너 줄 수 합": n974,
            "🔴🔴 974 에서 `exact` 분모가 0 인 파일": dead974,
            "🔴 분자/분모(974)": "%d / %d" % (len(dead974), len(c974)),
            "🔴 975 러너": c975,
            "🔴🔴 975 에서 `exact` 분모가 0 인 파일": dead975,
            "🔴 분자/분모(975)": "%d / %d" % (len(dead975), len(c975)),
            "🔴 고침": ("`contains`(`\"통과\" in k`) 갈래를 더하고, **분모 0 이면 "
                     "「모른다 --- 분모 0」** 으로 내려앉힌다. 🔴 **기본값은 `exact` 그대로** "
                     "--- 옛 산출물의 뜻을 조용히 안 바꾼다(노트 898)."),
        },
        "🔴🔴 수리 2 --- 「출처 키 경로 일치」 채점기": ctl,
        "🔴🔴 수리 4 --- 부호 일관성 p": {
            "🔴 974 산출물이 적은 것": "부호 일관성 p 0.010247 · 채택 True",
            "🔴 974 판이 잰 것": "귀무가 **7/7 양수**를 낼 확률 --- 관측 4/7 을 한 번도 안 본다",
            "🔴🔴 975 수리 뒤": {k: pn.get(k) for k in (
                "🔴 실측 양수 도메인",
                "🔴🔴 부호 일관성 --- 전 도메인 양수인 뽑기",
                "🔴🔴🔴 부호 일관성 p(975 수리 · 관측 양수 수를 본다)",
                "🔴🔴 부호 일관성 채택(p ≤ 0.05)",
                "🔴 974 판 부호 일관성 p(전 도메인 양수 · 자료와 무관)",
                "🔴 974 판이 냈을 채택",
                "🔴 975 수리가 판정을 뒤집었나") if k in pn},
        },
        "🔴🔴 수리 5 --- `head_vs_disk`": {
            "대조": a2_controls(),
            "데몬이 부르는가": daemon_calls_gate(),
        },
        "🔴 수리 계수(부풀리지 않는다)": {
            "🔴 이 사이클의 수리": [
                "1. numaudit 대상을 넷 전부로(판정문·논문·카드·원장)",
                "2. 정수 오탐 --- 값 일치 → 출처 키 경로 일치",
                "3. `meta965` 의 `통과` 키 규칙 + 분모 0 게이트",
                "4. `predict972.perm_null` 의 부호 일관성 p",
                "5. `harvest_daemon.head_vs_disk` --- 상태 다섯 + 데몬이 부른다",
            ],
            "🔴 분자/분모": "5 / 5",
            "🔴 상한": 5,
            "🔴 넘었나": False,
            "🔴 묶었나": False,
            "⚠ 이 사이클엔 수리 말고 **정정 다섯**이 더 있다(2순위 ⓐ~ⓔ)":
                "정정은 **같은 라벨 위에서 추정량·문구를 고친 것**이라 수리 레인에 안 넣었다. "
                "🔴 정정을 수리로 세면 **열이고 상한을 다섯 넘는다** --- 그렇게 적는다.",
        },
    }
    out["🔴 도장"] = stamp_block(ref, cs0, code_stamp(), t0)
    (OUT / "out975_scorefix.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["scorefix"])
    ap.add_argument("--ref", default="")
    a = ap.parse_args()
    r = stage_scorefix(a.ref)
    print(json.dumps(r, ensure_ascii=False, indent=1, default=str)[:5000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
