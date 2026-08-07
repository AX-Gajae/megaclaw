"""달력 파생 변수 — 발견 루프 1라운드 채택 후보 중 수집 비용이 0인 것들.

전부 공개 달력과 파일명만으로 계산되고, 오픈일 훨씬 전에 확정되므로 시간 마스크를
자동으로 통과한다. 크롤·API·에이전트 호출이 전혀 없다.

  ① holiday_gap_days   직전 장기연휴 종료일 → 오픈일 (양수=연휴 놓침, 음수=연휴 전)
     "연휴를 포함했는가"가 아니라 "놓쳤는가"가 핵심. RTPU2534는 2025 추석 골든위크
     (10/03~10/09, 최장 10일) 종료 바로 다음날 오픈해 수요를 통째로 흘려보냈다.
  ② holiday_block_in   운영기간이 장기연휴 블록과 겹치는 일수
  ③ nat_event_gap      전국 단위 일정(수능·선거·APEC)과 오픈일의 절대 거리(일).
     미디어 사이클을 독점당하면 화제성 획득 확률이 급락한다.
  ④ doc_lag_days       가장 늦은 사전문서 작성일 → 오픈일. 크면 그 기획은 실행안이
     아니라 아이데이션이라 intervention 속성의 신뢰도가 낮다.

장기연휴 블록 = 공휴일/주말이 연속 3일 이상 이어지는 구간(달력에서 기계적으로 도출).

사용: python3 -m ingest.calendar_features [--write]
산출: conditions.derived.calendar = {...}
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date, timedelta
from pathlib import Path

from .derive_features import HOLIDAYS

# 전국 미디어 사이클을 독점하는 일정. 모두 수개월~수년 전 확정 — 사전 관측 가능.
NATIONAL = {
    "2023-11-16": "수능", "2024-11-14": "수능", "2025-11-13": "수능", "2026-11-19": "수능",
    "2024-04-10": "국회의원 총선", "2025-06-03": "대통령 선거", "2026-06-03": "지방선거",
    "2025-10-31": "APEC 경주 정상회의", "2025-11-01": "APEC 경주 정상회의",
}


def _long_blocks(y0: int = 2023, y1: int = 2026) -> list[tuple[date, date]]:
    """공휴일·주말이 3일 이상 연속되는 구간을 달력에서 도출."""
    blocks, run = [], []
    d, end = date(y0, 1, 1), date(y1, 12, 31)
    while d <= end:
        off = d.weekday() >= 5 or d.isoformat() in HOLIDAYS
        if off:
            run.append(d)
        else:
            if len(run) >= 3:
                blocks.append((run[0], run[-1]))
            run = []
        d += timedelta(days=1)
    if len(run) >= 3:
        blocks.append((run[0], run[-1]))
    return blocks


BLOCKS = _long_blocks()


def _doc_dates(docs: list) -> list[date]:
    out = []
    for x in docs or []:
        nm = x.get("name") or x.get("title") or ""
        for m in re.finditer(r"(?<!\d)(\d{8}|\d{6})(?!\d)", nm):
            s = m.group(1)
            try:
                out.append(date.fromisoformat(f"{s[:4]}-{s[4:6]}-{s[6:]}") if len(s) == 8
                           else date.fromisoformat(f"20{s[:2]}-{s[2:4]}-{s[4:]}"))
            except ValueError:
                continue
    return out


def calendar_features(period_from: str | None, period_to: str | None,
                      docs: list | None = None) -> dict | None:
    if not period_from:
        return None
    try:
        f = date.fromisoformat(period_from)
        t = date.fromisoformat(period_to) if period_to else f
    except ValueError:
        return None

    # ① 장기연휴와의 거리. 지난 것과 다가올 것은 효과 방향이 반대라 따로 낸다
    #    (놓친 연휴 = 수요 유실 / 다가올 연휴 = 지출 유보). 한 변수로 뭉개면 상쇄된다.
    inside = any(b[0] <= f <= b[1] for b in BLOCKS)
    past = [b for b in BLOCKS if b[1] < f]
    upcoming = [b for b in BLOCKS if b[0] > f]
    since = 0 if inside else ((f - max(past, key=lambda b: b[1])[1]).days if past else None)
    until = 0 if inside else ((min(upcoming, key=lambda b: b[0])[0] - f).days if upcoming else None)

    # ② 운영기간과 장기연휴의 겹침 일수
    overlap = 0
    for b0, b1 in BLOCKS:
        lo, hi = max(f, b0), min(t, b1)
        if lo <= hi:
            overlap += (hi - lo).days + 1

    # ③ 전국 일정과의 최소 거리
    ng, nname = None, None
    for ds, nm in NATIONAL.items():
        d = abs((date.fromisoformat(ds) - f).days)
        if ng is None or d < ng:
            ng, nname = d, nm

    # ④ 문서 지연 — 오픈 전에 쓰인 문서 중 가장 늦은 것
    dd = [d for d in _doc_dates(docs or []) if d <= f]
    lag = (f - max(dd)).days if dd else None

    return {"holiday_since": since, "holiday_until": until, "holiday_block_in": overlap,
            "nat_event_gap": ng, "nat_event": nname if (ng is not None and ng <= 14) else None,
            "doc_lag_days": lag, "doc_dates_found": len(dd)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    n, hit, samples = 0, 0, []
    for p in sorted(Path("data/records").glob("*.json")):
        r = json.loads(p.read_text())
        c = r["conditions"]
        per = c.get("period") or {}
        cf = calendar_features(per.get("from"), per.get("to"), r.get("docs"))
        n += 1
        if not cf:
            continue
        hit += 1
        if a.write:
            c.setdefault("derived", {})["calendar"] = cf
            p.write_text(json.dumps(r, ensure_ascii=False, indent=1))
        if r["outcome"]["totals"].get("visitors") and cf.get("nat_event"):
            samples.append((r["record_id"], per.get("from"), cf["nat_event"],
                            cf["nat_event_gap"], cf["holiday_since"], cf["doc_lag_days"]))
    print(json.dumps({"레코드": n, "산출": hit, "기록": bool(a.write),
                      "장기연휴 블록": len(BLOCKS)}, ensure_ascii=False))
    print("\n■ 전국 일정 ±14일 내 오픈 (라벨 보유)")
    for s in sorted(samples, key=lambda x: x[3]):
        print(f"  {s[0]} {s[1]} · {s[2]} D{s[3]:+d} · 연휴거리 {s[4]} · 문서지연 {s[5]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
