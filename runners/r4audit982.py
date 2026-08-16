#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""982 정정 — 🔴 **981 의 수리 `R4` 를 «981 이 고친 파일»에 돌린다** (티처 #120 M6).

🔴 **981 은 `ledger.audit_korean_magnitude()` 를 신설해 놓고 자기가 고친 파일에 안 돌렸다.**
그리고 판정문 §3 의 「표 밖 수사 넷을 잡는다」는 **어느 산출물 키에도 없는 손 주장**이었다.

982 가 돌린다. **구판(982 정정 전) 과 신판(정정 뒤)을 둘 다 낸다**(조항 66-③).

씀:
    python3 runners/r4audit982.py --ref <40자 sha>
"""
import argparse
import collections
import datetime as dt
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import ledger as LG                               # noqa: E402

RAN = ("runners/r4audit982.py", "runners/ledger.py", "runners/predict971.py")
OUT = ROOT / "runners/out982_r4.json"
TARGETS = ("paper/steps/980_mixture/meta.json",
           "paper/steps/979_denominator/meta.json",
           "docs/판정_981.md", "docs/card_981.md")
#: 🔴 981 가지의 마지막 커밋 — 「982 가 손대기 «전»」의 판
BEFORE = "7eb595e958b0dbaf09ab96cf70d9fbbbf5187331"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="")
    a = ap.parse_args()
    t0 = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cs0 = LG.code_stamp(RAN)
    S = LG.artifact_numbers("out98*_*.json")
    rows = collections.OrderedDict()
    n_before = n_after = 0
    for rel in TARGETS:
        p = ROOT / rel
        now = p.read_text(encoding="utf-8") if p.is_file() else ""
        try:
            old = subprocess.check_output(
                ["git", "show", "%s:%s" % (BEFORE, rel)],
                cwd=str(ROOT)).decode("utf-8")
        except Exception:                                          # noqa: BLE001
            old = ""
        r_old = LG.audit_korean_magnitude(old, S) if old else None
        r_new = LG.audit_korean_magnitude(now, S) if now else None
        rows[rel] = collections.OrderedDict([
            ("⚠ 구판(981 가지 끝 커밋) 표 밖 수사",
             r_old["🔴🔴🔴 치환표에 없는 수사"] if r_old else "🔴 못 읽었다"),
            ("🔴 신판(982 정정 뒤) 표 밖 수사",
             r_new["🔴🔴🔴 치환표에 없는 수사"] if r_new else "🔴 못 읽었다"),
            ("🔴 센 한자어 수사(신판)", r_new["🔴 센 한자어 수사"] if r_new else None),
            ("🔴 면제한 수사(인라인 코드 안 · 신판)",
             r_new["🔴 면제한 수사(인라인 코드 안)"] if r_new else None),
            ("🔴 어긋난 자리(구판)", (r_old or {}).get("🔴 어긋난 자리") or "없음"),
            ("🔴 어긋난 자리(신판)", (r_new or {}).get("🔴 어긋난 자리") or "없음"),
        ])
        if r_old:
            n_before += r_old["🔴🔴🔴 치환표에 없는 수사"]
        if r_new:
            n_after += r_new["🔴🔴🔴 치환표에 없는 수사"]
    out = collections.OrderedDict()
    out["무엇"] = ("982 정정 — 🔴 981 의 수리 `R4`(한자어 자릿수 수사)를 "
                 "**981 이 고친 파일**에 돌린다. 981 은 자기 검사를 자기 정정에 안 돌렸다")
    out["🔴 축"] = "자기 자(정정 · 수리로 «안» 센다)"
    out["🔴 티처"] = "🔴 티처 #120 M6"
    out["🔴 분모: 검사한 파일"] = list(TARGETS)
    out["🔴 대조한 치환표 수의 개수"] = len(S)
    out["🔴🔴🔴 표 밖 수사 — 구판 합"] = n_before
    out["🔴🔴🔴 표 밖 수사 — 신판 합"] = n_after
    out["🔴 파일별"] = rows
    out["🔴🔴 982 가 무엇을 고쳤나"] = (
        "🔴 `paper/steps/980_mixture/meta.json` 의 「981 정정」 블록이 **981 이 고친 옛 문구**"
        "(「천이백만 배」·「이천이백만 행」)를 «인용»하는데 **JSON 에는 인라인 코드 면제가 없어서** "
        "인용이 주장으로 읽혔다. 🔴 **그 두 인용을 백틱으로 감쌌다 — 내용은 한 글자도 안 바뀐다.**")
    out["🔴 981 의 손 주장"] = (
        "🔴 981 판정문 §3 의 「표 밖 수사 넷을 잡는다」는 **어느 산출물 키에도 없었다**. "
        "🔴 이 산출물이 그 자리를 메운다")
    out["통과"] = bool(n_after == 0)
    out["🔴 이 절의 `통과` 가 뜻하는 것"] = (
        "🔴 **검사한 파일 전량에서 한자어 자릿수 수사가 치환표 안이다.** "
        "🔴 구판 값을 같이 실어 「무엇이 바뀌었나」를 볼 수 있게 했다(조항 66-③)")
    LG.write_stamped(str(OUT), out, a.ref, cs0, t0, RAN, LG.DATA)
    print('{"구판": %d, "신판": %d, "통과": %s}' % (n_before, n_after,
                                              "true" if n_after == 0 else "false"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
