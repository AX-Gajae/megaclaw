# -*- coding: utf-8 -*-
"""노트 966 — 단계별 산출물 셋을 **하나로 합친다**.

`runners/longmem966.py` 를 `--stage wiring|prop|board` 로 나눠 돌렸다(판 24주행이 길어서
배선과 명제를 먼저 확인해야 했다 --- 사전등록의 **순서 강제**가 「배선 검사 → 측정」이다).

🔴 **합치기 전에 세 산출물의 `코드 sha256` 이 **같은지** 확인한다.** 하나라도 다르면
**서로 다른 코드가 낸 수를 이어 붙이는 것**이라 종료 3 으로 죽는다(조항 60).
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
OUT = ROOT / "runners/out966_longmem.json"
SRC = ["/tmp/out966_wiring.json", "/tmp/out966_prop.json", "/tmp/out966_board.json"]

parts = [json.loads(Path(p).read_text(encoding="utf-8"),
                    object_pairs_hook=collections.OrderedDict) for p in SRC]
shas = {p["🔴 코드 sha256"] for p in parts}
if len(shas) != 1:
    print("🔴 코드 sha256 이 갈렸다:", shas)
    sys.exit(3)

R = collections.OrderedDict(parts[0])
R["단계"] = {"합친 것": [p["단계"] for p in parts],
           "🔴 세 단계의 코드 sha256 이 같은가": True,
           "단계별 끝 시각(UTC)": {p["단계"]: p["🔴 끝 시각(UTC)"] for p in parts},
           "🔴 왜 나눠 돌렸나": ("판 24주행이 길다. 사전등록의 순서 강제가 "
                        "「배선 검사 → 측정」이라 배선을 먼저 확인했다")}
for p in parts[1:]:
    for k, v in p.items():
        if k.startswith("§") and k not in R:
            R[k] = v
#: 🔴 **§9 를 갈아 끼운다 — 자백**: `longmem966.explore_kopis()` 가 `.json`/`.jsonl` 만 열었고
#: KOPIS 는 전부 `.jsonl.gz` 라 **행 0** 을 냈다. 「0 행」과 「안 읽었다」는 둘이다(조항 59).
#: 그 자리를 고치면 `longmem966.py` 의 코드 sha256 이 바뀌어 단계 셋 대조가 깨지므로
#: `runners/explore966_kopis.py` 가 다시 세고, 여기서 **옛 값을 지우지 않고 나란히** 둔다.
_k = ROOT / "runners/out966_kopis.json"
if _k.exists():
    R["§9 탐색(KOPIS)"] = {
        "🔴 초판(이 러너의 `explore_kopis()`)": dict(R.get("§9 탐색(KOPIS)", {})),
        "🔴 초판이 왜 0 이었나": ("`.json`/`.jsonl` 만 열었다. KOPIS 는 전부 `.jsonl.gz` 다 — "
                        "**「0 행」과 「안 읽었다」는 둘이다**(조항 59)"),
        "🔴 다시 센 것": json.loads(_k.read_text(encoding="utf-8")),
    }

R["초"] = round(sum(p["초"] for p in parts), 1)
R["🔴 끝 시각(UTC)"] = max(p["🔴 끝 시각(UTC)"] for p in parts)

OUT.write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")

# 🔴 합친 산출물의 `통과` 키를 모든 중첩 레벨에서 센다
def count(o):
    n = 0
    if isinstance(o, dict):
        for k, v in o.items():
            n += (k == "통과") + count(v)
    elif isinstance(o, list):
        for v in o:
            n += count(v)
    return n

print("wrote %s · 절 %s · `통과` 키(모든 중첩 레벨) %d"
      % (OUT, [k for k in R if k.startswith("§")], count(R)))
