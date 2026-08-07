"""venue_prior — 장소 조건부 일별 집객 사전분포.

RIPU2401(얼미부부/더현대서울, 예측 1,050 vs 실측 6,705, APE 84.3%) 사후분석에서
도출. 그 미스의 전부는 stimulus.conditions.location.venue_name == None 이었다는
단 하나의 사실로 설명된다. 장소를 알았다면 같은 뱅크 안에 이미 답이 있었다.

핵심 교훈
  - counting_method(participation/entry)는 규모의 예측자가 아니다. 장소가 예측자다.
    participation 버킷은 이봉분포이고, 그 봉우리를 가르는 것은 host traffic 유무다.
    (더현대 참가집계 1,328~1,538명/일  vs  대학·CGV 참가집계 49~114명/일)
  - v5는 participation 버킷에서 하위 3건(80/114/49명/일)만 앵커로 골랐다.
    같은 버킷 안에 있던 더현대 2건(1,328·1,538명/일)에는 닿지 못했다.
    장소 필드가 비어 있으면 장소로 선택할 수 없기 때문이다.
"""
from __future__ import annotations

import datetime
import glob
import json
import statistics as st
from collections import defaultdict

# 현대 계열 13개 레코드의 일별곡선에서 추정한 요일지수 (일평균=1.0 기준)
DOW_INDEX_HYUNDAI = {0: 0.80, 1: 0.78, 2: 0.73, 3: 0.74, 4: 0.91, 5: 1.52, 6: 1.47}

# 같은 존이라도 발자국이 작으면 처리량이 줄어든다. 19.5평 = 아이코닉존 최소급.
# 면적 선형 스케일은 오히려 틀린다(작은 팝업일수록 평당 밀도가 높다):
#   알라딘 89평 17.3명/평/일, 폴햄 80평 24명/평/일, 얼미부부 19.5평 49명/평/일
# 따라서 면적은 연속 스케일이 아니라 이산 축소계수로 쓴다.
FOOTPRINT_SHRINK = {"small": 0.55, "mid": 0.8, "large": 1.0}


def _f(d, *path, default=None):
    for k in path:
        d = (d or {}).get(k)
    return d if d is not None else default


def daily_rate(rec: dict) -> float | None:
    """매장당·일당 집객. store_count로 나눠 멀티스토어를 단일점으로 환원."""
    total = _f(rec, "outcome", "totals", "visitors")
    days = _f(rec, "conditions", "period", "days")
    stores = _f(rec, "conditions", "scale", "store_count", default=1) or 1
    if not total or not days:
        return None
    return total / days / max(stores, 1)


def venue_family(rec: dict) -> str | None:
    """장소를 집객 체급이 같은 패밀리로 정규화. venue_name 표기가 제각각이라 필요."""
    v = _f(rec, "conditions", "location", "venue_name", default="") or ""
    if "더현대" in v and "서울" in v:
        return "더현대서울"
    if "더현대" in v and "대구" in v:
        return "더현대대구"
    if "현대" in v:
        return "현대_기타"
    return None


def prior(records: list[dict], family: str, before: str) -> dict | None:
    """예측시점 이전(before) 같은 장소패밀리 라벨 선례의 일별 집객 사전분포.

    before를 강제하는 이유: 사후 레코드를 앵커로 쓰면 백테스트가 새는다.
    """
    rates = [
        r for rec in records
        if venue_family(rec) == family
        and _f(rec, "conditions", "period", "from", default="9999") < before
        and (r := daily_rate(rec)) is not None
    ]
    if not rates:
        return None
    return {"n": len(rates), "median": st.median(rates),
            "lo": min(rates), "hi": max(rates)}


def estimate(records, *, family, before, days, footprint="mid"):
    """장소 사전분포 × 발자국 축소 × 기간. 구간은 선례 min/max로 연다."""
    p = prior(records, family, before)
    if not p:
        return None
    k = FOOTPRINT_SHRINK[footprint]
    return {
        "point": round(p["median"] * k * days),
        "low": round(p["lo"] * k * 0.7 * days),
        "high": round(p["hi"] * days),
        "prior": p,
    }


def dow_residual(daily: list[dict]) -> list[tuple]:
    """일별 실측을 현대 요일지수로 나눈 잔차. 외생 충격(집회·기상) 탐지용.

    RIPU2401에 적용하면 12/14(토)만 -18%로 홀로 미달 — 그날 1.3km 거리
    국회 앞에서 24.5만명(경찰추산) 탄핵 집회가 있었다. 즉 집회는 순풍이 아니라
    역풍이었다. 과소예측의 원인이 아니다.
    """
    vals = [x["visitors"] for x in daily if x.get("visitors")]
    mean = sum(vals) / len(vals)
    out = []
    for x in daily:
        if not x.get("visitors"):
            continue
        w = datetime.date.fromisoformat(x["date"]).weekday()
        actual_idx = x["visitors"] / mean
        out.append((x["date"], "월화수목금토일"[w], x["visitors"],
                    round(actual_idx / DOW_INDEX_HYUNDAI[w] - 1, 3)))
    return out


if __name__ == "__main__":
    recs = [json.load(open(p)) for p in glob.glob("data/records/*.json")]

    est = estimate(recs, family="더현대서울", before="2024-12-12",
                   days=7, footprint="small")
    actual = 6705
    print("RIPU2401 반사실 — 장소만 채웠을 때")
    print(f"  선례 {est['prior']['n']}건  중앙값 {est['prior']['median']:,.0f}명/일")
    print(f"  point {est['point']:,}  구간 [{est['low']:,}, {est['high']:,}]")
    print(f"  실측 {actual:,}  APE {abs(est['point']-actual)/actual:.1%}"
          f"   (v5 실제 APE 84.3%)")

    rec = json.load(open("data/records/RIPU2401.json"))
    print("\n요일 잔차 (외생 충격 탐지)")
    for row in dow_residual(rec["outcome"]["daily"]):
        print("   ", row)
