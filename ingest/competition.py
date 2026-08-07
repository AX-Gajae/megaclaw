"""경쟁밀도 — 같은 건물·같은 반경에서 동시에 돌아가던 팝업의 수.

`stg_sophy.platform_spots` 5,710건은 공간 마스터가 아니라 **팝업 행사 센서스**다
(1,058개 주소에 5,710건). 우리 space_key 상위값이 전부 들어 있다:
더현대서울 691건 · 롯데월드몰 274건 · 성수 권역 1,598건.

R1의 `host_calendar_competition`(같은 숙주 안의 경쟁)과 `same_ip_concurrent_event`가
가리키던 축이 여기 실측으로 있다. 우리에게 전혀 없던 축이다.

**시간 마스크가 이 모듈의 전부다.** 두 가지를 엄격히 갈랐다:

  already_open   우리 오픈일 **이전에 이미 열려서** 그날까지 운영 중이던 팝업 수.
                 예측 시점에 걸어가 보면 보이는 것이므로 안전하다.
  prior_at_venue 같은 주소에서 우리 오픈일 **이전에 이미 끝난** 팝업 누적 수.
                 그 건물이 얼마나 팝업을 많이 치르는 곳인지 — 완전히 사후 무관.

우리 오픈일 이후에 여는 팝업은 세지 않는다. 그건 그 시점에 공표됐는지 알 수 없고,
platform_spots에는 공표일이 없어 확인할 방법이 없다. 세면 누출이다.

반경 계산은 위경도 하버사인. 같은 건물(주소 일치)과 반경(500m·1km)을 따로 낸다 —
같은 몰 안의 경쟁과 상권 전체의 밀도는 다른 현상이기 때문이다.

사용:
  python3 -m ingest.competition --fetch     # BQ 읽기 전용 → 캐시
  python3 -m ingest.competition             # 분포 확인
  python3 -m ingest.competition --write     # 적용
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
from datetime import date
from pathlib import Path

CACHE = Path("data/state/platform_spots.csv")
RECORDS = Path("data/records")
RADII_M = (500, 1000)

# space_key → 도로명주소. platform_spots의 주소 클러스터를 그곳 팝업 제목으로 식별했다.
# 레코드에 좌표·주소가 없어서 이 다리가 없으면 매칭이 92/380에 그친다.
VENUE_ADDR = {
    "더현대서울": "서울 영등포구 여의대로 108",
    "더현대대구": "대구 중구 달구벌대로 2077",
    "잠실_롯데월드몰": "서울 송파구 올림픽로 300",
    "롯데월드몰": "서울 송파구 올림픽로 300",
    "용산_아이파크몰": "서울 용산구 한강대로23길 55",
    "현대백화점_판교점": "경기 성남시 분당구 판교역로146번길 20",
    "신세계백화점_강남점": "서울 서초구 신반포로 176",
    "롯데백화점_잠실점": "서울 송파구 올림픽로 240",
    "롯데백화점_본점": "서울 중구 남대문로 81",
    "성수": "서울 성동구 연무장15길 11",
    "성수_피치스도원": "서울 성동구 성수이로 74",
    "성수52": "서울 성동구 성수이로 97",
    "타임스퀘어": "서울 영등포구 영중로 15",
}


def venue_addr(rec: dict) -> str:
    """레코드의 장소를 도로명주소로. space_key 우선, 없으면 장소명 부분일치."""
    sk = str(rec["entities"].get("space_key") or "")
    if sk in VENUE_ADDR:
        return VENUE_ADDR[sk]
    vn = str((rec["conditions"].get("location") or {}).get("venue_name") or "")
    for k, a in VENUE_ADDR.items():
        core = k.split("_")[-1]
        if len(core) >= 3 and (core in vn or core in sk):
            return a
    return ""

QUERY = """
SELECT spot_id, title, road_address, address, latitude, longitude,
       open_date, close_date
FROM `sweetspot-ax.stg_sophy.platform_spots`
WHERE open_date IS NOT NULL AND open_date != ''
"""


def fetch() -> int:
    """읽기 전용 SELECT만."""
    r = subprocess.run(["bq", "--project_id=sweetspot-ax", "query", "--nouse_legacy_sql",
                        "--format=csv", "--max_rows=20000", QUERY],
                       capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[:400])
        return 1
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(r.stdout)
    print(f"캐시 저장: {CACHE} ({len(r.stdout.splitlines())-1}행)")
    return 0


def _d(s):
    try:
        return date.fromisoformat(str(s)[:10])
    except Exception:
        return None


def haversine_m(a1, o1, a2, o2) -> float:
    R = 6371000.0
    p1, p2 = math.radians(a1), math.radians(a2)
    dp, dl = p2 - p1, math.radians(o2 - o1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def load_spots() -> list[dict]:
    out = []
    for r in csv.DictReader(CACHE.open()):
        o, c = _d(r["open_date"]), _d(r["close_date"])
        if not o:
            continue
        try:
            lat = float(r["latitude"]) if r["latitude"] else None
            lon = float(r["longitude"]) if r["longitude"] else None
        except ValueError:
            lat = lon = None
        out.append({"open": o, "close": c or o, "addr": (r["road_address"] or r["address"] or "").strip(),
                    "lat": lat, "lon": lon, "title": r["title"]})
    return out


def features(open_from: str, addr: str, lat, lon, spots: list[dict]) -> dict | None:
    d = _d(open_from)
    if not d:
        return None
    f = {"comp_same_addr_open": 0, "comp_prior_at_venue": 0}
    for r in RADII_M:
        f[f"comp_within_{r}m_open"] = 0
    same_addr = bool(addr)
    for s in spots:
        # ① 우리 오픈 전에 이미 열려서 그날까지 운영 중 — 예측 시점에 관측 가능
        already = s["open"] < d <= s["close"]
        # ② 우리 오픈 전에 이미 끝남 — 그 건물의 팝업 처리 이력
        finished = s["close"] < d
        if same_addr and s["addr"] == addr:
            if already:
                f["comp_same_addr_open"] += 1
            if finished:
                f["comp_prior_at_venue"] += 1
        if already and lat and lon and s["lat"] and s["lon"]:
            dist = haversine_m(lat, lon, s["lat"], s["lon"])
            for r in RADII_M:
                if dist <= r:
                    f[f"comp_within_{r}m_open"] += 1
    return f


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    if a.fetch:
        return fetch()
    if not CACHE.exists():
        print("캐시 없음 — 먼저 --fetch")
        return 1
    spots = load_spots()
    # 우리 레코드의 주소·좌표를 spots에서 찾는다(장소명 매칭)
    by_title: dict[str, dict] = {}
    for s in spots:
        if s["addr"]:
            by_title.setdefault(s["addr"], s)

    rows, hit = [], 0
    for p in sorted(RECORDS.glob("*.json")):
        rec = json.loads(p.read_text())
        per = rec["conditions"].get("period") or {}
        loc = rec["conditions"].get("location") or {}
        if not per.get("from"):
            continue
        addr = (loc.get("road_address") or loc.get("address") or "").strip()
        lat, lon = loc.get("latitude"), loc.get("longitude")
        if not addr:
            addr = venue_addr(rec)
        if addr and not (lat and lon):
            ref = by_title.get(addr)          # 그 주소의 좌표를 spots에서 빌린다
            if ref:
                lat, lon = ref["lat"], ref["lon"]
        f = features(per["from"], addr, lat, lon, spots)
        if not f:
            continue
        if addr:
            hit += 1
        rows.append((rec["record_id"], bool(rec["outcome"]["totals"].get("visitors")), f))
        if a.write:
            rec["conditions"].setdefault("derived", {})["competition"] = {
                **f, "matched_address": addr or None}
            p.write_text(json.dumps(rec, ensure_ascii=False, indent=1))

    lab = [f for _, v, f in rows if v]
    print(json.dumps({"레코드": len(rows), "주소 매칭": hit,
                      "라벨 보유": len(lab), "기록": bool(a.write)}, ensure_ascii=False))
    if lab:
        import statistics as st
        for k in lab[0]:
            vals = [f[k] for f in lab]
            nz = [v for v in vals if v]
            print(f"   {k:24s} 비영 {len(nz):3d}/{len(vals)}  중앙 {st.median(vals):5.0f}  최대 {max(vals):4d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
