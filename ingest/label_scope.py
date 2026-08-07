"""라벨 스코프 재발굴 — 라벨이 '언제, 며칠을' 센 것인지를 라벨 자신에게서 읽는다.

위생 감사가 잡은 13건을 들여다보니 공통 구조가 있었다: **daily 합이 총계와 일치**한다.
즉 라벨 산수는 맞고, 틀린 것은 conditions.period다. period는 ERP 계약등록창이라
운영창과 다른 경우가 잦고(51건 중 12건), 심하면 아예 다른 레그를 가리킨다
(RTPU2412: period 6/27~7/3인데 daily는 8/5~8/11).

그래서 daily 일자에서 스코프를 유도한다:
    label_from / label_to    = min/max(daily.date)
    label_active_days        = 고유 일자 수          ← 타깃의 진짜 분모
    label_contiguous         = (to − from + 1 == active_days)
    sum_agrees               = daily 합이 총계와 맞는가 (별개 사실)

**일자와 합계를 분리한다.** 일자는 방문객 수가 결측이거나 합이 어긋나도 신뢰할 수
있다 — 그 날 운영했다는 기록 자체이기 때문이다. 합계 불일치는 별개 결함이고,
어긋난 5건은 원문 재발굴 큐로 보낸다(총계가 순방문이고 daily가 연방문이면
이렇게 되는데, 단위 차이는 문서 없이 판정할 수 없다).

누출 구분 — 이 값들은 **채점용**이다:
  · label_active_days는 타깃의 분모다. y = visitors / days 에서 days가 무엇이었는지는
    라벨 자신의 정의이므로, 라벨에서 읽는 것이 옳다.
  · 예측 피처로 쓰는 것은 문서에서 읽은 planned_operating_days다(T1c). 둘은 다르다.
    한쪽은 '무슨 일이 있었나', 다른 쪽은 '무엇을 계획했나'다.

사용:
  python3 -m ingest.label_scope            # 무엇이 어떻게 바뀌는지
  python3 -m ingest.label_scope --write    # 적용
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from harness.label_hygiene import norm_date

SUM_TOL = 0.02          # daily 합이 총계와 이만큼 안에서 맞아야 '완결된 계열'


def derive(rec: dict) -> dict | None:
    """daily에서 라벨 스코프를 유도.

    **날짜와 합계를 분리해 다룬다.** 일자는 방문객 수가 결측이거나 합이 안 맞아도
    신뢰할 수 있다 — 그 날 운영했다는 기록 자체이기 때문이다. 반면 합계 일치는
    별개 사실이고, 어긋나면 라벨 충돌로 표시해 원문 재발굴 큐에 올린다.

    실제로 세 유형이 있었다:
      · 정상            합 = 총계                        (60건)
      · 방문객 결측     daily가 매출만 담고 있다          (RTPU2519 12/12행, RTPU2563 5/5행)
      · 합 > 총계       총계가 부분의 합보다 작다          (RTPU2582 +12.7%, RTPU2454 +9.4%)
        — 총계가 순방문(unique)이고 daily가 연방문(visits)일 때 이렇게 된다.
          단위가 다르므로 문서 없이는 판정할 수 없다.
    """
    o = rec["outcome"]
    total = o["totals"].get("visitors")
    daily = o.get("daily") or []
    if not total or len(daily) < 2:
        return None
    per = (rec["conditions"].get("period") or {})
    ds = sorted({d for d in (norm_date(x.get("date"), per.get("from")) for x in daily) if d})
    if len(ds) < 2:
        return None                          # 월 단위 등 일자 해석 불가 (RXPU2411)
    vals = [x.get("visitors") for x in daily]
    s = sum(v or 0 for v in vals)
    n_null = sum(1 for v in vals if v is None)
    if n_null == len(vals):
        agree, note = None, "daily에 방문객 수 없음(매출만) — 일자만 사용"
    elif abs(s - total) / total <= SUM_TOL:
        agree, note = True, "합이 총계와 일치"
    else:
        agree, note = False, (f"합 {s:,} 이 총계 {total:,} 와 {((s-total)/total):+.1%} 어긋남"
                              f"{f' (방문객 결측 {n_null}행)' if n_null else ''}")
    span = (date.fromisoformat(ds[-1]) - date.fromisoformat(ds[0])).days + 1
    return {"label_from": ds[0], "label_to": ds[-1], "label_active_days": len(ds),
            "label_span_days": span, "label_contiguous": span == len(ds),
            "daily_sum": s if n_null < len(vals) else None,
            "sum_agrees": agree, "source": f"daily 일자에서 유도 — {note}"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    rows, skipped = [], []
    for p in sorted(Path("data/records").glob("*.json")):
        r = json.loads(p.read_text())
        if not r["outcome"]["totals"].get("visitors"):
            continue
        sc = derive(r)
        if not sc:
            if len(r["outcome"].get("daily") or []) >= 2:
                skipped.append((r["record_id"], len(r["outcome"]["daily"])))
            continue
        per = r["conditions"].get("period") or {}
        du = ((r["conditions"].get("derived") or {}).get("duration") or {}).get("days")
        at = r["intervention"].get("attributes") or {}
        drift = (per.get("from") != sc["label_from"] or per.get("to") != sc["label_to"])
        rows.append((r["record_id"], per.get("from"), per.get("to"), du,
                     sc["label_from"], sc["label_to"], sc["label_active_days"],
                     sc["label_contiguous"], at.get("planned_operating_days"), drift,
                     sc["sum_agrees"], sc["source"]))
        if a.write:
            r["outcome"]["label_scope"] = sc
            p.write_text(json.dumps(r, ensure_ascii=False, indent=1))

    drifted = [x for x in rows if x[9]]
    daymis = [x for x in rows if x[3] and x[6] != x[3]]
    conflict = [x for x in rows if x[10] is False]
    nosum = [x for x in rows if x[10] is None]
    print(json.dumps({"유도 성공": len(rows), "유도 불가(일자 해석 불가)": len(skipped),
                      "합 일치": sum(1 for x in rows if x[10] is True),
                      "합 충돌(재발굴 필요)": len(conflict), "방문객 결측": len(nosum),
                      "period와 창이 다름": len(drifted),
                      "운영일수가 period days와 다름": len(daymis),
                      "비연속 운영": sum(1 for x in rows if not x[7]),
                      "기록": bool(a.write)}, ensure_ascii=False))
    print(f"\n■ period 창이 라벨 창과 어긋난 {len(drifted)}건")
    print(f"   {'코드':10s} {'period':>23s}   {'라벨 실제창':>23s} {'일수':>4s} {'연속':>4s} {'문서':>4s}")
    for x in sorted(drifted, key=lambda z: z[0]):
        print(f"   {x[0]:10s} {str(x[1]):>11s}~{str(x[2]):<11s}   "
              f"{x[4]:>11s}~{x[5]:<11s} {x[6]:4d} {'연속' if x[7] else '비연속':>4s} "
              f"{str(x[8] or '-'):>4s}")
    if conflict:
        print(f"\n■ 합 충돌 — 총계와 daily가 다른 것을 세고 있다. 원문 재발굴 대상")
        for x in conflict:
            print(f"   {x[0]:10s} {x[11]}")
    if nosum:
        print(f"\n■ 방문객 결측 (일자만 사용, 총계는 그대로)")
        for x in nosum:
            print(f"   {x[0]:10s} 운영 {x[6]}일 {x[4]}~{x[5]}")
    if skipped:
        print(f"\n■ 유도 불가 (일자 해석 불가)")
        for s in skipped:
            print(f"   {s[0]} — daily {s[1]}행")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
