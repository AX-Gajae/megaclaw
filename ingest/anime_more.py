"""애니 빠진 편 수집(노트 388) --- 라프텔 목록 9,472 중 우리는 2,073(22%)이다.

노트 387이 웹툰에서 같은 일을 했다: 덮음 74\% 를 95\% 로 올리니 판이
$+0.0071$(11/12) 올랐고, 위약(새 행 라벨 섞기)이 그 이득을 통째로 지웠다 ---
행 수가 아니라 **그 라벨이 말하는 것**이 이득이었다.

애니는 같은 모양인데 구멍이 훨씬 크다. `item_ids` 가 최신순·인기순을
절반씩만 훑어서, 우리 표본이 **오프셋 0 근처에 몰려 있다**:

    오프셋      0   1000   2000   3000   4500   6000   7500   9000
    이미 있음  74%     0%    12%    24%    28%     6%     8%     2%

최신순 정렬이라 깊은 오프셋이 곧 옛 작품이다. **웹툰에서 값이 났던 바로
그 구역이 통째로 비어 있다.**

**섞어서 받는다**(노트 383) --- 오프셋 오름차순으로 받으면 중간에 멈춘
부분 결과가 최신 쪽만 담는다. 씨앗 고정이라 재현된다.
**출처 좌표(`_offset`)를 남긴다**(노트 383).

    python3 -m ingest.anime_more --want 3000
"""
from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

from .anime_domain import API, _get, build

OUT = Path("data/state/anime_more.json")
CK = Path("data/state/anime_more.jsonl")
SEED = 20260801


def missing_ids() -> list[tuple[int, int]]:
    have = set(int(k.split("-")[-1])
               for k in json.loads(Path("data/state/anime_axes.json").read_text()))
    out, seen = [], set()
    off = 0
    while True:
        d = _get(f"{API}/search/v1/discover/?sort=recent&size=100&offset={off}",
                 f"more_recent_{off}")
        rs = (d or {}).get("results") or []
        if not rs:
            break
        for r in rs:
            i = r.get("id")
            if i and i not in seen and i not in have:
                seen.add(i)
                out.append((i, off))
        if off % 2000 == 0:
            print(f"  목록 오프셋 {off} · 빠진 것 {len(out)}", flush=True)
        if not (d or {}).get("next"):
            break
        off += 100
        time.sleep(0.25)
    random.Random(SEED).shuffle(out)     # 노트 383 --- 부분 결과도 고르게
    return out


def run(want: int = 3000) -> dict:
    ids = missing_ids()
    print(f"빠진 것 {len(ids)}편 · 목표 {want}", flush=True)
    done = {}
    if CK.exists():
        for line in CK.read_text().splitlines():
            try:
                o = json.loads(line)
                done[o["record_id"]] = o
            except Exception:
                pass
    print(f"이어받기 {len(done)}", flush=True)
    ck = CK.open("a")
    n = 0
    for iid, off in ids:
        rid = f"AN-{iid}"
        if rid in done:
            continue
        if len(done) >= want:
            break
        r = build(iid)
        if r:
            r["_offset"] = off
            done[rid] = r
            ck.write(json.dumps(r, ensure_ascii=False) + "\n")
            ck.flush()
            n += 1
            if n % 50 == 0:
                OUT.write_text(json.dumps(done, ensure_ascii=False))
                pre = sum(1 for v in done.values()
                          if (v.get("start_date") or "9") < "2025")
                print(f"  {len(done)}/{want} · 2025 이전 {pre}", flush=True)
        time.sleep(0.2)
    OUT.write_text(json.dumps(done, ensure_ascii=False))
    pre = sum(1 for v in done.values() if (v.get("start_date") or "9") < "2025")
    print(f"끝: {len(done)}편 · 2025 이전 {pre} · 2025+ {len(done)-pre}", flush=True)
    return {"n": len(done), "pre2025": pre}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--want", type=int, default=3000)
    a = ap.parse_args()
    run(a.want)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
