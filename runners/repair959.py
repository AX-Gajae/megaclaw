# -*- coding: utf-8 -*-
"""노트 959 [수리] — **main 을 진실하게 만든다**(지시서 3순위 · 티처 #97 ②).

세 가지를 **기계로** 한다. 손으로 안 고친다.

  **가** 원장(`data/lab/denominator.json`)의 **957 항목**과 논문 원장의 **500 항목**에
        「501/958 이 철회함」을 **필드로 더한다**. 🔴 **원장은 추가만 한다 — 옛 글자는 안 지운다.**
  **나** 층 채택 규칙에 **㉣ 더 싼 대체물**을 넣어(`lab/adopt.py`) 958 의 수를 다시 먹인다.
        🔴 **키 자체가 `false` 를 내야 한다** — 산문으로 「채택하면 안 된다」라고 적는 것은 안 된다.
  **다** `paper/steps/500_betweendomain/meta.json` 에 **철회 포인터**를 박는다.
        🔴 **제목·`claims` 는 그대로 둔다 — 역사 기록이다.** 포인터만 더한다.

    python3 runners/repair959.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from lab.adopt import adopt                                     # noqa: E402

LEDGER = ROOT / "data/lab/denominator.json"
PLEDGER = ROOT / "paper/ledger.json"
META500 = ROOT / "paper/steps/500_betweendomain/meta.json"
OUT = ROOT / "runners/out959_repair.json"

RETRACT = {
    "🔴🔴 959 철회 표시": (
        "이 항목의 헤드라인 「층 ③ 이득의 **전부**가 도메인 사이의 것이다」는 "
        "**철회됐다**(티처 #96 C1 · 노트 958 · 논문 스텝 501). 근거 +0.001635 를 만든 "
        "`layers957.py:666` 이 도메인 부분집합에서 **모형을 다시 적합한다** — 분해가 아니라 "
        "**표본 크기 실험**이었다. 모형을 고정하면 도메인 **안**이 **+0.087763** 으로 "
        "합산 +0.059774 **보다 크다**(안쪽 몫 43.6246%)."),
    "🔴 대신 서는 문장": (
        "「층 ③ 의 정보는 도메인 이름표로 **대체 가능**하다」까지만 선다 — 지시자 +0.087630 이 "
        "들고, 그 위에서 층 ③ 은 −0.007503 으로 **뺀다**."),
    "🔴 959 가 더한 것": (
        "958 이 그 +0.087763 에 「0 과 못 가른다」를 붙였는데 **그것도 철회한다** — "
        "958 의 부트가 재표집마다 묶음을 다시 골라 **추정량 자체를 흔들었다**. "
        "묶음을 원표본에 고정하면 씨앗 **24/24 에서 T 를 넘는다**(`runners/out959_d3.json`)."),
    "어디서 정정됐나": ["docs/판정/958.md", "paper/steps/501_retraction",
                 "runners/out959_d3.json", "docs/판정/959.md"],
}


def patch_ledger() -> dict:
    d = json.loads(LEDGER.read_text())
    keys = [k for k in d if "노트 957 [판정]" in k]
    done = []
    for k in keys:
        v = d[k]
        if not isinstance(v, dict):
            continue
        added = [f for f in RETRACT if f not in v]
        v.update({f: RETRACT[f] for f in added})
        done.append({"키(앞60)": k[:60], "더한 필드": added,
                     "🔴 지운 필드": [], "필드 수": len(v)})
    LEDGER.write_text(json.dumps(d, ensure_ascii=False, indent=1))
    return {"분자: 표시한 항목": len(done), "분모: 찾은 957 판정 항목": len(keys),
            "항목별": done, "🔴 원장 항목 수": len(d),
            "통과": bool(done)}


def patch_paper() -> dict:
    p = json.loads(PLEDGER.read_text())
    steps = p["steps"]
    hit = [s for s in steps if s.get("n") == 500]
    for s in hit:
        s["🔴 철회됨"] = "논문 스텝 501(`501_retraction`)이 이 스텝의 제목과 claims[1] 을 철회한다"
        s["철회 스텝"] = 501
    PLEDGER.write_text(json.dumps(p, ensure_ascii=False, indent=1))

    m = json.loads(META500.read_text())
    m["🔴 철회됨"] = {
        "누가": "논문 스텝 501 (`paper/steps/501_retraction`) · 노트 958 · 티처 #96 C1",
        "무엇을": "제목 전체와 claims[1](「도메인 안 평균은 +0.00163 이다」)",
        "왜": "그 +0.00163 은 도메인 부분집합에서 모형을 **다시 적합**한 값이다 — "
             "분해가 아니라 표본 크기 실험. 모형 고정 시 도메인 안이 +0.087763 으로 합산보다 크다",
        "🔴 제목과 claims 를 왜 안 고치나": "역사 기록이다. 밖으로 나간 문장을 지우면 "
                                "「나간 적 없다」가 되고 그것이 더 큰 거짓이다",
        "959 가 더한 것": "958 이 붙인 「0 과 못 가른다」도 철회된다 — 씨앗 24/24 에서 T 를 넘는다",
    }
    META500.write_text(json.dumps(m, ensure_ascii=False, indent=1))
    return {"논문 원장 500 항목": len(hit),
            "meta.json 에 철회 포인터": "🔴 철회됨" in m,
            "🔴 제목 그대로인가": m["title"].startswith("「무관 배경」은 배경이 아니라"),
            "🔴 claims 그대로인가": len(m["claims"]) == 4,
            "🔴 sent 그대로인가": m.get("sent") is True,
            "통과": bool(hit and "🔴 철회됨" in m)}


def redecide_adopt() -> dict:
    """🔴 958 의 「채택 = true」를 **고친 규칙**에 다시 먹인다."""
    blob = subprocess.run(
        ["git", "show", "note/958-within:runners/out958_within.json"],
        capture_output=True, text=True)
    if blob.returncode != 0:
        return {"🔴 못 읽었다": blob.stderr.strip()[:200], "통과": False}
    d = json.loads(blob.stdout)
    D5 = d["§6 D5 층 ③ 을 s 에 넣나"]
    ind = d["§6 ㉰ 도메인 지시자 (사전등록 · 957 은 사후였다)"]
    alt = ind["① → +지시자"]
    on_alt = ind["①+지시자 → +③"]
    old = D5["🔴🔴 채택(㉠㉡㉢)"]
    new = adopt(sum_pass=D5["㉠ 합산 Δρ > T"],
                sub_sign_pass=D5["㉡ 부 표적 부호 유지"],
                perm_pass=D5["㉢ 열 순열 상위 5% 밖(958 이 사전등록한 자)"],
                alt_delta=alt["Δρ"], alt_T=alt["T"],
                layer_on_alt_delta=on_alt["Δρ"], layer_on_alt_T=on_alt["T"])
    return {
        "🔴 자": "lab/adopt.adopt — ㉠㉡㉢ 에 ㉣ 더 싼 대체물을 더한 규칙",
        "읽은 것": "git show note/958-within:runners/out958_within.json (가지 blob)",
        "대체물": {"무엇": "도메인 지시자 9열", "Δρ": alt["Δρ"], "T": alt["T"],
                "혼자 드나": alt["Δρ"] > alt["T"]},
        "그 위에서 층 ③": {"Δρ": on_alt["Δρ"], "T": on_alt["T"], "판정": on_alt["판정"]},
        "🔴 958 이 찍은 값": old,
        "🔴🔴 959 규칙으로 다시 찍은 값": new["🔴🔴 채택(㉠㉡㉢㉣)"],
        "규칙 전체": new,
        "🔴 뒤집혔나": bool(old != new["🔴🔴 채택(㉠㉡㉢㉣)"]),
        "⚠ 아직 남은 것": "PR #216 의 `runners/out958_within.json` 자체는 여전히 true 를 담고 있다. "
                    "머지할 때 `within958.py` 가 `lab.adopt.adopt` 를 부르게 배선해야 한다 — "
                    "🔴 **이 파일은 그 배선을 대신하지 못한다**(조항 62).",
        "통과": bool(new["🔴🔴 채택(㉠㉡㉢㉣)"] is False),
    }


def main() -> dict:
    t0 = time.time()
    R = {"노트": 959, "레인": "수리", "논문 스텝": 502,
         "사전등록": "docs/prereg_959_reach.md §8 (커밋 4212af9ab · 상한 6)",
         "가 원장 957 항목에 철회 표시": patch_ledger(),
         "다 논문 500 에 철회 포인터": patch_paper(),
         "나 채택 규칙 ㉣ 을 넣고 다시 찍기": redecide_adopt(),
         "초": round(time.time() - t0, 1)}
    n = sum(1 for k, v in R.items() if isinstance(v, dict) and v.get("통과"))
    R["🔴 분자: 통과한 수리"] = n
    R["🔴 분모: 이 러너가 한 수리"] = 3
    OUT.write_text(json.dumps(R, ensure_ascii=False, indent=1))
    print(json.dumps(R, ensure_ascii=False, indent=1)[:4000])
    return R


if __name__ == "__main__":
    main()
