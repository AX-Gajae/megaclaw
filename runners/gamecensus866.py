# -*- coding: utf-8 -*-
# 노트 866 P2 — 모집단 일-입도 직접 계수 마감(사전등록 '866' · 티처 #31 제안 2)
# 3350 부터 걷기 재개: 연속 3쪽 일-입도 0 → 소진 정지(상한 80쪽) · 조회실패 3연속 재시도 · 종료 사유 필드 의무.
# + 간극 탐침 {5000, 7000, 9000, 11000, 12400}. 산출: 실측 하한 · 조각 추정 · 상한(간극 전량 일 가정).
import datetime as dt
import json
import time
from pathlib import Path

import sys
sys.path.insert(0, "/Users/ax/world_model")
from lab.gamesearch import fetch_page  # noqa: E402

ROOT = Path("/Users/ax/world_model")
TOTAL = 12828


def page(off):
    for _ in range(3):                  # 조회실패 3연속 재시도(866 규율)
        items, _tc = fetch_page(off)
        if items is not None:
            return items
        time.sleep(3.0)
    return None


def main():
    t0 = time.time()
    walk = []
    off, zero_run, reason = 3350, 0, None
    while len(walk) < 80:
        items = page(off)
        if items is None:
            reason = f"조회실패(3회 재시도 실패) @ {off}"
            break
        nd = sum(1 for it in items if it["입도"] == "일")
        days = sorted(it["표준일"] for it in items if it["입도"] == "일")
        walk.append({"offset": off, "일 n": nd, "일 범위": [days[0], days[-1]] if days else None,
                     "구성": {}})
        for it in items:
            walk[-1]["구성"][it["입도"]] = walk[-1]["구성"].get(it["입도"], 0) + 1
        zero_run = zero_run + 1 if nd == 0 else 0
        if zero_run >= 3:
            reason = f"소진 정지(연속 3쪽 일 0) @ {off}"
            break
        off += 50
    if reason is None:
        reason = f"상한 80쪽 도달 @ {off}"
    walk_end = walk[-1]["offset"] + 50 if walk else 3350

    probes = {}
    for p in (5000, 7000, 9000, 11000, 12400):
        if p < walk_end:
            continue
        items = page(p)
        if items is None:
            probes[p] = None
            continue
        c = {}
        for it in items:
            c[it["입도"]] = c.get(it["입도"], 0) + 1
        probes[p] = c

    # 계수: 앞쪽(0~1900 · 863+864 실측 구간) + day0b/c 대역(1850~3350 · 865 실측) + 이번 걷기
    front = 1650                        # 864 눈금: 150~1650 전 쪽 일 50/50 + 1900 에 6 — 보간 병기
    mid = 352 + 163                     # day0c + day0b(중복 0 실측)
    new = sum(w["일 n"] for w in walk)
    counted = front + mid + new
    gaps = []
    prev = walk_end
    for p in sorted(probes):
        pc = probes[p]
        day_in_probe = (pc or {}).get("일", 0)
        gaps.append({"구간": [prev, p], "폭": p - prev, "탐침 일 n": day_in_probe})
        prev = p + 50
    tail_gap = max(0, TOTAL - prev)
    upper = counted + sum(g["폭"] for g in gaps if g["탐침 일 n"] is None or g["탐침 일 n"] > 0) + \
        (tail_gap if any((probes.get(p) or {}).get("일", 0) > 0 for p in probes) else 0)
    # 조각 추정: 간극은 인접 탐침의 일-비율로
    est = counted
    for g in gaps:
        pc = probes.get(g["구간"][1])
        rate = ((pc or {}).get("일", 0)) / 50 if pc else 0
        est += g["폭"] * rate

    out = {"시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "걷기": walk, "종료 사유": reason, "걷기 신규 일": new,
           "탐침": probes,
           "계수": {"실측+실측대역 하한": counted, "조각 추정": round(est),
                  "상한(간극 일-존재 가정)": round(upper),
                  "구성": {"앞쪽 0~1900(보간 병기)": front, "대역 1850~3350": mid, "이번 걷기": new}},
           "문턱": {"과반선": TOTAL // 2, "판정": ("과반 실측 승격(상한도 이하)" if upper <= TOTAL // 2 else
                                             ("추정 병기(상한 초과·추정 이하)" if est <= TOTAL // 2 else "표제 철회"))},
           "초": round(time.time() - t0, 1)}
    with open(ROOT / "runners/out866_census.json", "x") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "걷기"}, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
