# -*- coding: utf-8 -*-
# 노트 865 P2′ — 후미 층 보충 코호트: 표준일 [9/25,10/31] 일-입도 전량(사전등록 '865' · day0b 불변)
import datetime as dt
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, "/Users/ax/world_model")
from lab.gamesearch import fetch_page  # noqa: E402 — 동결 사본(864 원문)

ROOT = Path("/Users/ax/world_model")
WIN_LO, WIN_HI = "2026-09-25", "2026-10-31"


def main():
    t0 = time.time()
    day0c, seen = [], set()
    walk_log = []
    off, pages_walked = 1850, 0
    while pages_walked < 60:
        items, _ = fetch_page(off)
        if items is None:
            break
        pages_walked += 1
        days = sorted(it["표준일"] for it in items if it["입도"] == "일")
        walk_log.append({"offset": off, "일 n": len(days),
                         "일 범위": [days[0], days[-1]] if days else None})
        for it in items:
            if it["입도"] == "일" and WIN_LO <= it["표준일"] <= WIN_HI and it["appid"] not in seen:
                seen.add(it["appid"])
                day0c.append(dict(it, _offset=off))
        if days and days[0] > WIN_HI:
            break
        off += 50
    ds = sorted(c["표준일"] for c in day0c)
    NOW = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    out = {"수집 시각(UTC)": NOW, "등록창": [WIN_LO, WIN_HI],
           "실커버리지": [ds[0], ds[-1]] if ds else None,
           "n": len(day0c), "걸은 쪽": pages_walked, "시작 오프셋": 1850,
           "코호트": day0c, "걷기": walk_log,
           "재수집": "2026-08-22 · 2026-08-29 gameday7.py 865 — 병기 전용(권위는 864)",
           "초": round(time.time() - t0, 1)}
    with open(ROOT / "runners/out865_day0c.json", "x") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k not in ("코호트", "걷기")},
                     ensure_ascii=False, indent=1), flush=True)
    from collections import Counter
    print("월별:", dict(sorted(Counter(s[:7] for s in ds).items())), flush=True)


if __name__ == "__main__":
    main()
