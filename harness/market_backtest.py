"""시장 폴드 A/B — 미소모 시장 라벨로 시장층 주입 효과를 페어드 측정.

각 시장 레코드(MKT-*)를 홀드아웃 삼아:
  arm mkt   — 내부 뱅크 다이제스트 + 시장 층(타깃 오픈 전 마스크: 자기 자신은 종료일>오픈일이라 자동 제외)
  arm nomkt — 내부 뱅크만
채점: 시장 라벨(주최측 발표) 기준 APE. 라벨 등급이 claim이므로 절대 수준은 참고,
**페어 차이(mkt−nomkt)가 1차 지표** — 단일 런이어도 차분에서 run 분산이 상쇄되고 n으로 평균된다.

사용: python3 -m harness.market_backtest --targets MKT-...,... --out cycle_log/market-eval-v3
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from .predictor_llm import LLMPredictor
from .records import load_records


def market_stimulus(m: dict) -> dict:
    iv = m.get("intervention") or {}
    c = m.get("conditions") or {}
    try:
        days = (date.fromisoformat(c["period_to"]) - date.fromisoformat(c["period_from"])).days + 1
    except Exception:
        days = None
    return {
        "record_id": m["market_record_id"],
        "entities": {"brand_key": m.get("ip_or_collab") or m.get("brand"), "space_key": c.get("venue")},
        "intervention": {"concept": iv.get("concept_description"), "brand_name": m.get("brand"),
                          "experience_elements": iv.get("experience_elements") or [],
                          "promotions": iv.get("promotions") or [],
                          "staging_tags": [m.get("category") or ""]},
        "conditions": {"location": {"venue_name": c.get("venue"), "city": c.get("city"),
                                      "venue_type": c.get("venue_type"), "district": c.get("neighborhood"),
                                      "foot_traffic_context": None},
                        "period": {"from": c.get("period_from"), "to": c.get("period_to"), "days": days},
                        "scale": {"store_count": 2 if c.get("multi_store") else 1,
                                   "venue_traffic_type": "host_venue" if c.get("venue_type") in ("department", "mall") else "standalone",
                                   "host_traffic_note": None},
                        "capacity": {"access_type": "reservation" if iv.get("reservation_required") else
                                      ("open" if iv.get("is_free_entry") else "unknown"),
                                      "total_capacity": None, "detail": ""},
                        "fee_structure": {"type": "unknown", "detail": "시장 공개 정보 — 계약 정보 없음"}},
        "measurement": {"visitors_counting_method": "unknown"},
        "docs": [],
        "_note": "시장 공개 정보 기반 폴드 (기획서·계약서 없음) — 시장층 평가 전용",
    }


def build_internal_manifest(cutoff: str) -> list[dict]:
    recs = [r for r in load_records("data/records") if str(r.start) <= cutoff]
    return [{"record_id": r.record_id, "record_path": str(r.path), "docs": r.doc_uris} for r in recs]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", required=True)
    ap.add_argument("--out", default="cycle_log/market-eval-v3")
    ap.add_argument("--arms", default="mkt,nomkt")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    for code in args.targets.split(","):
        m = json.loads(Path(f"data/market_records/{code}.json").read_text())
        actual = m["outcome"]["visitors_total"]
        stim = market_stimulus(m)
        cutoff = stim["conditions"]["period"]["from"]
        manifest = build_internal_manifest(cutoff)
        row = {"record_id": code, "actual": actual, "basis": m["outcome"].get("counting_basis"),
               "category": m.get("category"), "from": cutoff, "bank": len(manifest)}
        for arm in args.arms.split(","):
            arm_dir = out / arm
            arm_dir.mkdir(exist_ok=True)
            done = arm_dir / f"{code}.prediction.json"
            if done.exists():
                pred = json.loads(done.read_text())
            else:
                p = LLMPredictor(arm_dir, auto=True, market=(arm != "nomkt"),
                                 signals=(arm != "nosig"), features=(arm != "nofeat"),
                                 shuffle_sig=(arm == "shufsig"),
                                 shuffle_feat=(arm == "shuffeat"))
                pred = p.predict(stim, manifest)
            v = (pred.get("totals") or {}).get("visitors") or {}
            row[arm] = v.get("point")
            row[f"{arm}_int"] = [v.get("low"), v.get("high")]
            if v.get("point") is not None and actual:
                row[f"{arm}_ape"] = round(abs(v["point"] - actual) / actual, 4)
        with open(out / "results.jsonl", "a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(json.dumps({k: row.get(k) for k in ("record_id", "actual", "mkt_ape", "nomkt_ape")},
                          ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
