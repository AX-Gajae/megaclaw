"""record_store_link 감사 — 36%가 다른 팝업을 가리킨다.

`data/state/record_store_link.json`(555건)은 우리 레코드를 팝업 플랫폼의 spot_id에
연결한다. 위경도가 여기에만 있으므로, 격자 생활인구·경쟁밀도 같은 공간 피처는
전부 이 링크를 거친다.

그런데 감사해 보니 **기간이 겹치는 링크는 114/177(64%)뿐이다.** 나머지 63건은
8일에서 164일까지 어긋나 전혀 다른 팝업을 가리킨다:

    RCPU2410  레코드 2024-05-27~06-09  ↔  링크 '신카이 마코토 천호 팝업' 08-24~09-05
    RCPU2406  레코드 2024-04-30~05-07  ↔  링크 '디즈니 100주년 전시' 10-18~2025-06-01
    RXPU2511  성수 도원 메인동          ↔  링크 여의대로 108 '맥 팝업'

이름이 비슷한 팝업(신카이 마코토 천호 팝업이 3개 레코드에 중복 링크)이나 같은 브랜드의
다른 회차에 붙은 것으로 보인다. 링크를 만들 때 기간을 대조하지 않은 결과다.

**공간 피처는 잘못된 좌표를 쓰면 조용히 오염된다.** 지오코딩 오차 몇백 미터는 격자
한두 칸이지만, 16~236km 어긋난 링크는 완전히 다른 상권을 읽는다. 그래서 기간 겹침을
통과한 링크만 쓴다.

판정: 레코드 기간과 spot 기간의 간극이 ±7일 이내면 정합. 팝업은 짧고 날짜가 정확히
기록되므로 7일이면 충분히 관대하다.

사용:
  python3 -m ingest.link_audit            # 감사 결과
  python3 -m ingest.link_audit --write    # 정합 링크만 남긴 파일 생성
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path

LINK = Path("data/state/record_store_link.json")
SPOTS = Path("data/state/platform_spots.csv")
OUT = Path("data/state/record_store_link_verified.json")
TOL_DAYS = 7


def _d(s):
    try:
        return date.fromisoformat(str(s)[:10])
    except Exception:
        return None


def audit() -> dict:
    link = json.loads(LINK.read_text())
    spots = {r["spot_id"]: r for r in csv.DictReader(SPOTS.open())}
    good, bad, nolink = {}, [], 0
    for p in sorted(Path("data/records").glob("*.json")):
        rec = json.loads(p.read_text())
        code = rec["record_id"]
        per = rec["conditions"].get("period") or {}
        f = _d(per.get("from"))
        t = _d(per.get("to")) or f
        if not f:
            continue
        e = link.get(code) or {}
        sid = str(e.get("store", "")).rsplit("/", 1)[-1]
        sp = spots.get(sid)
        if not sp:
            nolink += 1
            continue
        so, sc = _d(sp["open_date"]), _d(sp["close_date"])
        sc = sc or so
        if not so:
            continue
        gap = max((f - sc).days if sc < f else 0, (so - t).days if so > t else 0)
        row = {"spot_id": sid, "lat": sp["latitude"], "lon": sp["longitude"],
               "addr": (sp["road_address"] or sp["address"] or "").strip(),
               "spot_title": sp["title"], "gap_days": gap,
               "labeled": bool(rec["outcome"]["totals"].get("visitors"))}
        if gap <= TOL_DAYS:
            good[code] = row
        else:
            bad.append({"code": code, **row,
                        "rec_period": f"{f}~{t}", "spot_period": f"{so}~{sc}"})
    return {"good": good, "bad": bad, "nolink": nolink}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    r = audit()
    g, b = r["good"], r["bad"]
    gl = sum(1 for v in g.values() if v["labeled"])
    bl = sum(1 for v in b if v["labeled"])
    coord = sum(1 for v in g.values() if v["lat"] and v["lon"])
    print(json.dumps({"정합": len(g), "불일치": len(b), "링크 없음": r["nolink"],
                      "정합 중 라벨 보유": gl, "불일치 중 라벨 보유": bl,
                      "정합 중 좌표 보유": coord, "기록": a.write}, ensure_ascii=False))
    print(f"\n■ 불일치 상위 (라벨 보유 우선)")
    for x in sorted(b, key=lambda z: (not z["labeled"], -z["gap_days"]))[:12]:
        print(f"   {x['code']:10s} {'라벨O' if x['labeled'] else '     '} "
              f"{x['rec_period']:23s} ↔ {x['spot_period']:23s} {x['gap_days']:4d}일  "
              f"{x['spot_title'][:26]}")
    if a.write:
        OUT.write_text(json.dumps(g, ensure_ascii=False, indent=1))
        print(f"\n정합 링크만 저장: {OUT} ({len(g)}건)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
