#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""984 §2-5 — 🔴🔴🔴 **`⑤′` 를 「수렴할 때까지」 돌리고 반복 횟수를 박는다**.

🔴 **왜 (티처 #122 C1).** **983 의 `⑤′` 마지막 판이 인증한 트리가 사라졌다.** 그 판이
박은 입력 sha 셋(`out983_score`·`table`·`prose`)이 **전부 `⑤′` 뒤에 다시 지어졌고**,
그 재주행이 **반증조건 11 을 `false → true` 로 뒤집어 `15/16 → 16/16`** 을 만들었다 ---
**자기가 채점할 대상을 만들어 놓고 다시 채점한 값이다.**

🔴 **수렴의 정의는 사전등록 §2-5 가 «측정 전»에 박았다**: 연속 두 판의
**① `통과` · ② `실패한 절` 목록 · ③ `절 수(분모)`** 세 칸이 **전부 같으면** 수렴이다.
🔴 **입력 sha 는 수렴 판별에 안 쓴다** --- 문서가 `⑤′` 결과를 담으므로 문서 sha 는
정의상 매 판 바뀐다. 그 대신 **`⑤′` 산출물을 반증조건 11 의 도장 분모에서 «사전»에 뺐다.**

    python3 runners/fixpoint984.py --record --ref <40자 sha> --run <파일>...
"""
import argparse
import collections
import datetime as dt
import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import cycle984 as CY                                # noqa: E402

OUT = "runners/out984_fixpoint.json"


def _sig(path):
    p = ROOT / path
    if not p.is_file():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    fail = d.get("🔴 실패한 절")
    return collections.OrderedDict([
        ("판", path),
        ("통과", d.get("통과")),
        ("실패한 절", fail if isinstance(fail, list) else []),
        ("절 수(분모)", d.get("🔴 절 수(분모)")),
        ("⚠ 참고: 코드 sha256(수렴 판별에 안 쓴다)",
         (d.get("🔴 코드 sha256") or {}).get("runners/fiveprime902.py")),
        ("⚠ 참고: 끝 시각", d.get("시각(UTC · 끝)")),
    ])


def stage(ref, runs):
    t0 = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cs0 = CY.code_stamp()
    sigs = [_sig(r) for r in runs]
    got = [s for s in sigs if s is not None]
    conv, why = False, "🔴 판이 하나뿐이라 아직 못 잰다(조항 59: 「안 수렴」이 아니다)"
    if len(got) >= 2:
        a, b = got[-2], got[-1]
        same = (a["통과"] == b["통과"] and a["실패한 절"] == b["실패한 절"]
                and a["절 수(분모)"] == b["절 수(분모)"])
        conv = bool(same)
        why = ("🔴 연속 두 판의 `통과`·`실패한 절`·`절 수` 가 **전부 같다** → 수렴" if same
               else "🔴 연속 두 판이 다르다 → 아직 안 수렴")
    body = collections.OrderedDict([
        ("🔴 무엇", "🔴🔴🔴 **`⑤′` 를 수렴할 때까지 돌린 기록**(사전등록 §2-5)"),
        ("🔴 수렴의 정의(측정 전에 박았다)",
         "연속 두 판의 ① `통과` ② `실패한 절` 목록 ③ `절 수(분모)` 세 칸이 전부 같다"),
        ("🔴🔴 반복 횟수", len(got)),
        ("🔴 판별", why),
        ("🔴 판별에 쓴 판", [s["판"] for s in got]),
        ("🔴 판별에 못 쓴 판(파일이 없다)",
         [r for r, s in zip(runs, sigs) if s is None] or "없음"),
        ("🔴 판별", why),
        ("🔴 판별표", got),
        ("🔴🔴🔴 수렴했나", conv),
        ("🔴 왜 입력 sha 를 수렴 판별에 안 쓰나",
         "🔴 문서가 `⑤′` 결과를 담으므로 문서 sha 는 **정의상 매 판 바뀐다.** "
         "입력 sha 를 판별에 넣으면 고정점이 원리상 존재할 수 없다. "
         "🔴 **대신 `⑤′` 산출물을 반증조건 11 의 도장 분모에서 «사전»에 뺐고 뺀 수를 "
         "분모와 나란히 싣는다**(사전등록 §2-5 · 조항 59)"),
        ("🔴🔴 983 이 왜 고정점이 아니었나",
         "🔴 983 의 `⑤′` 마지막 판이 인증한 트리(`dd15dec23`)가 사라졌다 --- 그 판이 박은 "
         "입력 sha 셋(`out983_score`·`table`·`prose`)이 전부 `⑤′` 뒤에 다시 지어졌고, "
         "그 재주행이 **반증조건 11 을 `false → true` 로 뒤집어 `15/16 → 16/16`** 을 만들었다. "
         "**자기가 채점할 대상을 만들어 놓고 다시 채점한 값이다**(티처 #122 C1)"),
        ("통과", conv),
        ("🔴 이 절의 `통과` 가 뜻하는 것", "🔴 **수렴했는가** 하나다. `⑤′` 자신의 통과와 무관하다"),
    ])
    out = collections.OrderedDict()
    out["무엇"] = "984 §2-5 — 🔴 **`⑤′` 고정점 기록**"
    out["🔴 축"] = "자기 자(절차)"
    out["§2-5 🔴🔴🔴 `⑤′` 고정점"] = body
    out["🔴🔴 반복 횟수"] = len(got)
    out["🔴 판별"] = why
    out["🔴🔴🔴 수렴했나"] = conv
    out["통과"] = conv
    CY.write(OUT, out, ref, cs0, t0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", action="store_true")
    ap.add_argument("--ref", default="")
    ap.add_argument("--run", action="append", default=[])
    a = ap.parse_args()
    r = stage(a.ref, a.run)
    print(json.dumps({"반복 횟수": r["🔴🔴 반복 횟수"], "수렴했나": r["🔴🔴🔴 수렴했나"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
