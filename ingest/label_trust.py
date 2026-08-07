"""라벨 신뢰등급 태깅 — 쌍둥이 해부(2026-07-27)의 1위 변수(counting_basis 측정 아티팩트) 정제.

등급 (우선순위 순으로 판정):
  D  스코프 혼합 — 멀티스토어 합산·행사 전체·온오프 총계 (단위가 다른 값)
  E  재활용/추정 의심 — 사전 예상치와 동일, 추산·추정, media_estimate
  C  하한값 — "N명 돌파/이상/넘는" (실제값은 그 위)
  A  정밀 집계 — 계수기·등록·티켓·POS·예약명단, 또는 일별 표가 기간을 커버
  B  주최측 단정 발표 (기본값 — 반올림 노이즈 ±수%)

저장: 레코드 outcome.label_trust = {grade, flags, why}
사용: python3 -m ingest.label_trust
"""
from __future__ import annotations

import json
import re
from pathlib import Path

PAT = {
    # D는 '단위가 다른 것들의 합'만 — 일별/시간대별 합산은 정상 집계라 제외(NEG)
    "D": r"(존|지점|매장|채널|활동|컬럼|무빙|거리|사전\+현장|온·?오프|온라인|야외|투어) ?[^,]{0,6}(합산|합계|총합|포함)"
         r"|2개 ?점|양 ?점|행사 ?전체|전 ?지점|둘을 합|전국 합",
    "E": r"예상.{0,10}동일|사전 ?예상|추산|추정|목표치.{0,8}(재|동일)|기대치|expected|계획.{0,6}수치|소진.{0,8}(기준|환산)",
    "C": r"돌파|이상[이가 ]|넘는|넘어|넘었|초과|이상의 |\d\s*명? ?이상",
    "A": r"계수기|카운터|등록 ?인원|입장권|티켓 ?(판매|발권)|POS|예약 ?명단|리스트 ?체크|QR ?(체크인|코드 ?스캔|스캔)|발권|실제 ?입장",
}
NEG_D = r"일별 ?(합산|합계)|시간대별 ?(합산|합계)|구간만|참고치"


def grade(basis: str, note: str, notes: str, daily_cover: float | None,
          counting: str | None) -> tuple[str, list[str], str]:
    blob = " ".join(x for x in (basis, note, notes) if x)
    flags = [g for g, p in PAT.items() if re.search(p, blob)]
    if "D" in flags and re.search(NEG_D, blob) and not re.search(PAT["D"], re.sub(NEG_D, "", blob)):
        flags.remove("D")
    if "D" in flags:
        return "D", flags, "스코프 혼합(합산/총계) 표현"
    if "E" in flags or counting == "media_estimate":
        return "E", flags, "예상치 재활용·추산 표현"
    if "C" in flags:
        return "C", flags, "하한값 표현(돌파/이상/넘는)"
    if "A" in flags or (daily_cover is not None and daily_cover >= 0.7):
        why = "정밀 집계 표현" if "A" in flags else f"일별 표가 기간의 {daily_cover:.0%} 커버"
        return "A", flags, why
    return "B", flags, "단정 발표(기본)"


def main() -> int:
    dist = {}
    # 내부 레코드
    for p in Path("data/records").glob("*.json"):
        r = json.loads(p.read_text())
        o = r["outcome"]
        if not o["totals"].get("visitors"):
            continue
        days = (r["conditions"].get("period") or {}).get("days")
        daily = o.get("daily") or []
        cover = len(daily) / days if days else None
        # 내부는 counting_basis만 판정 재료로 — provenance 노트는 무관 문맥('추정' 등)으로 오염됨
        g, flags, why = grade(o.get("counting_basis") or "", "", "",
                               cover, o.get("counting_method"))
        o["label_trust"] = {"grade": g, "flags": flags, "why": why}
        p.write_text(json.dumps(r, ensure_ascii=False, indent=2))
        dist.setdefault("internal", {}).setdefault(g, 0)
        dist["internal"][g] += 1
    # 시장 레코드 (방문 라벨 보유만)
    for p in Path("data/market_records").glob("*.json"):
        r = json.loads(p.read_text())
        o = r["outcome"]
        if not o.get("visitors_total"):
            continue
        quotes = " ".join(q.get("quote", "") if isinstance(q, dict) else str(q)
                           for q in (o.get("demand_signals") or {}).get("signal_quotes") or [])
        blob_note = " ".join(x for x in (o.get("counting_basis_note"), o.get("visitors_source_quote"), quotes) if x)
        g, flags, why = grade(o.get("counting_basis") or "", blob_note, str(r.get("notes") or ""),
                               None, o.get("counting_basis"))
        o["label_trust"] = {"grade": g, "flags": flags, "why": why}
        p.write_text(json.dumps(r, ensure_ascii=False, indent=2))
        dist.setdefault("market", {}).setdefault(g, 0)
        dist["market"][g] += 1
    print(json.dumps(dist, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
