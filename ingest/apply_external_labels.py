"""외부 보도 라벨 충전 — 역검색(W1)으로 확보한 방문·매출·수요신호를 내부 레코드에 반영.

원칙(2026-07-27):
  ① 스코프 판정 통과분만(행사 전체 참관객·권역 집계 거부 — 지스타 202,000 류 재발 방지)
  ② 기존 라벨이 있으면 덮어쓰지 않고 교차검증 기록만
  ③ 외부 보도 라벨은 내부 실측과 등급이 다르다 → label_source='external_press',
     label_trust 기본 C(2차 출처·주최측 발표 계열), 출처 3종을 provenance에 영구 기록
  ④ 수요 신호(대기·완판)는 방문 라벨이 없어도 conditions.demand_signals에 적재

사용: python3 -m ingest.apply_external_labels [--dry]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROWS = Path("data/market_raw/crawl2_w1_parsed.json")
SCOPE = Path("cycle_log/crawl2_w1_scope.json")
LOG = Path("cycle_log/external_labels.jsonl")

BASIS_TO_METHOD = {"entry": "entry", "participation": "participation",
                   "organizer_claim": "unknown", "media_estimate": "unknown", "unknown": "unknown"}


def main() -> int:
    dry = "--dry" in sys.argv
    rows = {r["internal_code"]: r for r in json.loads(ROWS.read_text())
            if r.get("internal_code") and r.get("found")}
    scope = json.loads(SCOPE.read_text())
    keep = set(scope["keep"])

    log = open(LOG, "a")
    filled = crosscheck = signals = skipped = 0
    for code, r in rows.items():
        p = Path(f"data/records/{code}.json")
        if not p.exists():
            skipped += 1
            continue
        rec = json.loads(p.read_text())
        o = rec["outcome"]
        changed = False
        entry = {"code": code, "event": r.get("event_name"), "action": []}

        v = r.get("visitors_total")
        if v and code in keep:
            existing = o["totals"].get("visitors")
            if existing:
                diff = abs(existing - v) / existing
                entry["action"].append(f"crosscheck diff={diff:.2f} (기존 {existing} vs 보도 {v})")
                crosscheck += 1
            else:
                o["totals"]["visitors"] = v
                o["counting_method"] = BASIS_TO_METHOD.get(r.get("counting_basis"), "unknown")
                o["counting_basis"] = (str(r.get("counting_basis_note") or "")[:200]
                                        or f"외부 보도({r.get('counting_basis')})")
                o["label_source"] = "external_press"
                o["label_trust"] = {"grade": "C", "flags": ["external"],
                                     "why": f"외부 보도 2차 출처({r.get('counting_basis')}) — 내부 실측 아님"}
                o["source"] = (f"방문: 역검색 외부 보도 — {r.get('visitors_source_url')} "
                                f"({r.get('visitors_source_date')}) | 인용: {str(r.get('visitors_source_quote'))[:150]}")
                entry["action"].append(f"방문 라벨 충전 {v}")
                filled += 1
                changed = True
        elif v:
            entry["action"].append(f"스코프 거부 — 보도치 {v} 미채택")

        s = r.get("sales_krw")
        if s and not o["totals"].get("sales_krw") and code in keep:
            o["totals"]["sales_krw"] = s
            entry["action"].append(f"매출 충전 {s}")
            changed = True

        if r.get("waiting") or r.get("sold_out"):
            rec["conditions"].setdefault("demand_signals", {})
            rec["conditions"]["demand_signals"].update(
                {"waiting_reported": r.get("waiting"), "sold_out": r.get("sold_out"),
                 "source": "역검색 외부 보도(2026-07-27)"})
            entry["action"].append("수요신호 적재")
            signals += 1
            changed = True

        if changed and not dry:
            rec["provenance"]["notes"] += (
                f" | 외부 라벨 역검색(2026-07-27): {'; '.join(entry['action'])}")
            p.write_text(json.dumps(rec, ensure_ascii=False, indent=2))
        if entry["action"]:
            log.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(json.dumps({"방문충전": filled, "교차검증": crosscheck, "신호적재": signals,
                       "레코드없음": skipped, "dry": dry}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
