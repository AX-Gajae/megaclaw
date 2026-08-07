"""파생 피처 3종 — 쌍둥이 해부 랭킹 2~4위를 전 레코드(내부+시장)에 계산·저장.

② duration_weekday_mix: days, weekend_share(주말일/총일), holiday_days(공휴일 수)
③ capacity_cap 플래그 확장: 텍스트 키워드로 access_type 승격(unknown/open → session/invite/reservation)
④ ip_cycle_stage: 같은 IP의 과거 개최 수·직전 간격(개월)·1회차 여부 — 내부+시장 통합 타임라인에서
   각 레코드의 '자기 오픈일 이전' 이력만 사용(시간 일관성 내장)

저장 위치: 내부 conditions.derived / 시장 conditions.derived
사용: python3 -m ingest.derive_features
"""
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path

# 한국 공휴일 2023-2026 (대체공휴일 포함, 주요일만)
# **2015~2022 를 채웠다**(노트 214). 목록이 2023년부터라 그 이전 레코드가
# ``다음 연휴까지''를 못 재고 상한(120)에 붙었고, 상한인 것의 100\%가 2023년
# 이전이라 그 축이 사실상 시간 분할 변수의 대리였다(노트 213).
#
# 설날 · 부처님오신날 · 추석의 양력 날짜는 영문 위키백과
# ``Public holidays in South Korea'' 의 표로 확인했다. **대체공휴일은
# 최선을 다한 것이고 완전하지 않을 수 있다** --- 축이 ``가장 가까운 사흘
# 이상 연휴까지의 날수''라 하루 어긋남은 min(gap,120) 에서 무시할 만하다.
HOLIDAYS = set("""
2015-01-01 2015-02-18 2015-02-19 2015-02-20 2015-03-01 2015-05-05 2015-05-25
2015-06-06 2015-08-14 2015-08-15 2015-09-26 2015-09-27 2015-09-28 2015-09-29
2015-10-03 2015-10-09 2015-12-25
2016-01-01 2016-02-07 2016-02-08 2016-02-09 2016-02-10 2016-03-01 2016-05-05
2016-05-14 2016-06-06 2016-08-15 2016-09-14 2016-09-15 2016-09-16 2016-10-03
2016-10-09 2016-12-25
2017-01-01 2017-01-27 2017-01-28 2017-01-29 2017-01-30 2017-03-01 2017-05-03
2017-05-05 2017-05-09 2017-06-06 2017-08-15 2017-10-02 2017-10-03 2017-10-04
2017-10-05 2017-10-06 2017-10-09 2017-12-25
2018-01-01 2018-02-15 2018-02-16 2018-02-17 2018-03-01 2018-05-05 2018-05-07
2018-05-22 2018-06-06 2018-06-13 2018-08-15 2018-09-23 2018-09-24 2018-09-25
2018-09-26 2018-10-03 2018-10-09 2018-12-25
2019-01-01 2019-02-04 2019-02-05 2019-02-06 2019-03-01 2019-05-05 2019-05-06
2019-05-12 2019-06-06 2019-08-15 2019-09-12 2019-09-13 2019-09-14 2019-10-03
2019-10-09 2019-12-25
2020-01-01 2020-01-24 2020-01-25 2020-01-26 2020-01-27 2020-03-01 2020-04-15
2020-04-30 2020-05-05 2020-06-06 2020-08-15 2020-08-17 2020-09-30 2020-10-01
2020-10-02 2020-10-03 2020-10-09 2020-12-25
2021-01-01 2021-02-11 2021-02-12 2021-02-13 2021-03-01 2021-05-05 2021-05-19
2021-06-06 2021-08-15 2021-08-16 2021-09-20 2021-09-21 2021-09-22 2021-10-03
2021-10-04 2021-10-09 2021-10-11 2021-12-25
2022-01-01 2022-01-31 2022-02-01 2022-02-02 2022-03-01 2022-03-09 2022-05-05
2022-05-08 2022-06-01 2022-06-06 2022-08-15 2022-09-09 2022-09-10 2022-09-11
2022-09-12 2022-10-03 2022-10-09 2022-10-10 2022-12-25
2023-01-01 2023-01-21 2023-01-22 2023-01-23 2023-01-24 2023-03-01 2023-05-05 2023-05-27 2023-05-29
2023-06-06 2023-08-15 2023-09-28 2023-09-29 2023-09-30 2023-10-02 2023-10-03 2023-10-09 2023-12-25
2024-01-01 2024-02-09 2024-02-10 2024-02-11 2024-02-12 2024-03-01 2024-04-10 2024-05-05 2024-05-06
2024-05-15 2024-06-06 2024-08-15 2024-09-16 2024-09-17 2024-09-18 2024-10-01 2024-10-03 2024-10-09 2024-12-25
2025-01-01 2025-01-27 2025-01-28 2025-01-29 2025-01-30 2025-03-01 2025-03-03 2025-05-05 2025-05-06
2025-06-03 2025-06-06 2025-08-15 2025-10-03 2025-10-05 2025-10-06 2025-10-07 2025-10-08 2025-10-09 2025-12-25
2026-01-01 2026-02-16 2026-02-17 2026-02-18 2026-03-01 2026-03-02 2026-05-05 2026-05-24 2026-05-25
2026-06-06 2026-08-15 2026-08-17 2026-10-03 2026-10-05 2026-09-24 2026-09-25 2026-09-26 2026-10-09 2026-12-25
""".split())

CAP_PAT = {
    "session": r"회차|상영|세션|타임당|시간대 ?예약|공연|사인회 ?회|좌석",
    "invite": r"초청|초대|VIP ?(대상|한정)|인비테이션|RSVP",
    "reservation": r"사전 ?예약|예약제|예약 ?필수|캐치테이블|네이버 ?예약|입장 ?제한|웨이팅 ?예약|선착순 ?예약",
}


def _ipkey_mkt(r):
    k = (r.get("ip_or_collab") or r.get("brand") or "").strip()
    return re.sub(r"\(.*?\)", "", k).split(" X ")[0].split("X")[0].strip()


def _ipkey_int(r):
    e = r.get("entities", {})
    k = e.get("brand_key") or r["intervention"].get("brand_name") or ""
    return k.replace("unresolved:", "").strip()


def duration_features(f: str, t: str) -> dict | None:
    try:
        d0, d1 = date.fromisoformat(f), date.fromisoformat(t)
    except (ValueError, TypeError):
        return None
    days = (d1 - d0).days + 1
    if days <= 0 or days > 400:
        return None
    wk = hol = 0
    for i in range(days):
        d = d0 + timedelta(days=i)
        if d.weekday() >= 5:
            wk += 1
        if d.isoformat() in HOLIDAYS:
            hol += 1
    return {"days": days, "weekend_share": round(wk / days, 2), "holiday_days": hol}


def capacity_upgrade(existing: dict | None, blob: str) -> dict | None:
    cur = (existing or {}).get("access_type")
    if cur in ("session", "invite", "reservation"):
        return existing  # 이미 판정됨
    for k, p in CAP_PAT.items():
        if re.search(p, blob):
            out = dict(existing or {"total_capacity": None, "detail": ""})
            out["access_type"] = k
            out["detail"] = ((out.get("detail") or "") + f" | 키워드 승격({k})").strip(" |")
            return out
    return existing


def main() -> int:
    # 통합 타임라인 구축 (ip, open_date, source)
    events = []
    internals, markets = {}, {}
    for p in Path("data/records").glob("*.json"):
        r = json.loads(p.read_text())
        per = r["conditions"].get("period") or {}
        internals[p.stem] = (p, r)
        if per.get("from") and _ipkey_int(r):
            events.append((per["from"], _ipkey_int(r), p.stem))
    for p in Path("data/market_records").glob("*.json"):
        r = json.loads(p.read_text())
        markets[p.stem] = (p, r)
        c = r["conditions"]
        if c.get("period_from") and _ipkey_mkt(r):
            events.append((c["period_from"], _ipkey_mkt(r), p.stem))
    events.sort()

    def ip_history(ip: str, open_from: str) -> dict:
        prior = [e for e in events if e[1] == ip and e[0] < open_from and len(ip) >= 2]
        if not prior:
            return {"prior_count": 0, "months_since_last": None, "first_edition": True}
        last = max(e[0] for e in prior)
        months = None
        try:  # 2차 수집분에 'YYYY-MM' 등 불완전 날짜가 섞여 있어 방어
            months = round((date.fromisoformat(open_from) - date.fromisoformat(last)).days / 30.4, 1)
        except ValueError:
            pass
        return {"prior_count": len(prior), "months_since_last": months, "first_edition": False}

    n_int = n_mkt = n_cap = 0
    for stem, (p, r) in internals.items():
        per = r["conditions"].get("period") or {}
        der = {}
        df = duration_features(per.get("from"), per.get("to"))
        if df:
            der["duration"] = df
        if per.get("from"):
            der["ip_history"] = ip_history(_ipkey_int(r), per["from"])
        blob = json.dumps({"i": r["intervention"], "c": {k: v for k, v in r["conditions"].items() if k != "derived"}},
                           ensure_ascii=False)
        newcap = capacity_upgrade(r["conditions"].get("capacity"), blob)
        if newcap is not r["conditions"].get("capacity"):
            r["conditions"]["capacity"] = newcap
            n_cap += 1
        if der:
            r["conditions"]["derived"] = der
            n_int += 1
        p.write_text(json.dumps(r, ensure_ascii=False, indent=2))
    for stem, (p, r) in markets.items():
        c = r["conditions"]
        der = {}
        df = duration_features(c.get("period_from"), c.get("period_to"))
        if df:
            der["duration"] = df
        if c.get("period_from"):
            der["ip_history"] = ip_history(_ipkey_mkt(r), c["period_from"])
        iv = r.get("intervention") or {}
        blob = json.dumps(iv, ensure_ascii=False) + str(r.get("notes") or "")
        if iv.get("reservation_required"):
            blob += " 예약제"
        newcap = capacity_upgrade(c.get("capacity"), blob)
        if newcap:
            c["capacity"] = newcap
        if der:
            c["derived"] = der
            n_mkt += 1
        p.write_text(json.dumps(r, ensure_ascii=False, indent=2))
    print(json.dumps({"내부_derived": n_int, "시장_derived": n_mkt, "capacity_승격": n_cap}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
