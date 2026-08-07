"""시장 레코드 층 편입 — Kimi 크롤링 검증분을 data/market_records/에 적재.

내부 실측 뱅크(data/records)와 절대 혼합하지 않는 별도 층:
  tier=market_claim (counting_basis 대부분 organizer_claim — 주최측 발표 계열)
단일 이벤트 필터: 통합/합산 집계, 연도 걸침(>90일), 기간 미상은 anchor 부적격(참고층으로만).

사용: python3 -m ingest.market_layer
"""
from __future__ import annotations

import json
from pathlib import Path

RAW = Path("data/market_raw/records_merged.jsonl")
VER = Path("data/market_raw/verify_results.jsonl")
OUT = Path("data/market_records")


def days_of(r) -> int | None:
    c = r["conditions"]
    if not (c.get("period_from") and c.get("period_to")):
        return None
    from datetime import date
    try:
        f = date.fromisoformat(c["period_from"])
        t = date.fromisoformat(c["period_to"])
        return (t - f).days + 1
    except ValueError:
        return None


def single_event(r) -> tuple[bool, str]:
    name, notes = r.get("event_name") or "", str(r.get("notes") or "")
    if "통합" in name or "합산" in name or "합산" in notes.split("|")[0]:
        return False, "집계형(통합/합산)"
    d = days_of(r)
    if d is None:
        return False, "기간 미상"
    if d > 90:
        return False, f"기간 {d}일 > 90일(장기·집계 의심)"
    return True, ""


def main() -> int:
    recs = [json.loads(l) for l in open(RAW)]
    ver = {}
    if VER.exists():
        for l in open(VER):
            v = json.loads(l)
            ver.setdefault(v["record_id"], {})[v["metric"]] = v["status"]

    OUT.mkdir(exist_ok=True)
    stats = {"total": len(recs), "anchor": 0, "reference_only": 0, "verified_visitors": 0}
    for r in recs:
        ok, why = single_event(r)
        r["tier"] = "market_claim"
        r["single_event"] = ok
        r["exclude_reason"] = why or None
        r["verification"] = ver.get(r["market_record_id"], {})
        r["ingested_from"] = "kimi-crawl-2026-07 (records_merged.jsonl)"
        (OUT / f"{r['market_record_id']}.json").write_text(json.dumps(r, ensure_ascii=False, indent=2))
        if ok:
            stats["anchor"] += 1
        else:
            stats["reference_only"] += 1
        if r["verification"].get("visitors") == "verified":
            stats["verified_visitors"] += 1
    print(json.dumps(stats, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
