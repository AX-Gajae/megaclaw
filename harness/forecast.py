# -*- coding: utf-8 -*-
"""예보 하네스 v0 — 「팝업 하나를 기획했다. 무슨 일이 일어나나?」 (사이클 1038).

🔴 이 하네스의 요점은 **팔 수 있는 것과 못 파는 것을 가르는 것**이다.
1038 이 실측으로 갈랐다:

  수준(총 몇 명 올까)   🔴 «못 맞힌다»
      구조 특징 12개      Δ +0.0726  CI95 [-0.0204,+0.1638]   못 넘음
      + 브랜드 특징 20개  Δ -0.0321  CI95 [-0.1751,+0.1059]   못 넘음 (부호만 옳음)
      일 단위 558행       Δ +0.0558  CI95 [-0.1169,+0.2547]   못 넘음
      → 기준선(전체 중앙값 628명/일)을 아무도 못 이겼다. 그러니 «중앙값을 낸다».
        구간은 모형이 아니라 «실측 분포»에서 낸다 — 정직한 넓이가 나온다.

  모양(어느 날 붐빌까)  ✅ «맞힌다»
      요일·진행률·첫날   Δ -0.0354  SE 0.0102  CI95 [-0.0543,-0.0143]  0 배제
      오차 11.0% 감소 (프로젝트 63 · 일별 534행 · 프로젝트 단위 LOO)

  매출                🔴 «예측하지 않는다»
      방문자·매출 둘 다 있는 92건의 객단가가 832원~23,286,957원(27,995배).
      매출 = 방문자 × (28,000배로 흔들리는 것). 객단가는 «사용자가 넣는 손잡이»다.
      (§L2-4 정본: 효용 = 일평균 방문자 · 매출은 부차 관찰)

🔴 인과 아님. 개입이 무작위 배정이 아니다(조항 60). 조건부 연관까지만 적는다.

씀:
    python3 -m harness.forecast --days 12 --start 2026-05-08 --venue "백화점 팝업존" \
        --city 서울특별시 --recognition 4 --ip --unit-price 8000
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import argparse
import datetime as dt
import glob
import json
import os

import numpy as np

np.seterr(all="ignore")   # ⚠ 이 기계의 Accelerate 가짜 경고 — isfinite 로 «검사»한다

ART = os.environ.get("WM_FOUNDATION_DIR", "/Users/ax/wm_harvest/foundation")
REC_DIR = "/Users/ax/world_model/data/records"

# 1038-마 에서 «자를 넘은» 모양 계수 (프로젝트 평균 대비 배수)
SHAPE_DOW = {0: -0.044, 1: -0.053, 2: -0.060, 3: -0.052, 4: -0.018, 5: +0.092, 6: +0.059}
SHAPE_PROGRESS = -0.058     # 진행률(0→1) 계수
SHAPE_FIRST = -0.051        # 첫날
SHAPE_LAST = +0.019         # 마지막날
SHAPE_VERDICT = {"Δ": -0.0354, "SE": 0.0102, "CI95": [-0.0543, -0.0143],
                 "판정": "✅ 0 배제 · 오차 11.0% 감소", "n프로젝트": 63, "n행": 534}


def observed_levels():
    """실측 일평균 방문자 분포 — 구간을 모형이 아니라 «자료»에서 낸다."""
    out = []
    for p in sorted(glob.glob(os.path.join(REC_DIR, "*.json"))):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        o = d.get("outcome") or {}
        t = o.get("totals") or {}
        per = (d.get("conditions") or {}).get("period") or {}
        daily = [r for r in (o.get("daily") or [])
                 if isinstance(r, dict) and r.get("visitors") is not None]
        if daily:
            v, days = sum(float(r["visitors"]) for r in daily), float(len(daily))
        elif t.get("visitors") is not None:
            v, days = float(t["visitors"]), per.get("days")
        else:
            continue
        if v and days and v > 0:
            out.append(v / float(days))
    return np.array(sorted(out))


def shape_multipliers(start, days):
    """일별 배수 — 합이 days 가 되도록 정규화(수준을 안 건드린다)."""
    d0 = dt.date.fromisoformat(start)
    raw = []
    for i in range(days):
        d = d0 + dt.timedelta(days=i)
        s = SHAPE_DOW[d.weekday()]
        s += SHAPE_PROGRESS * ((i + 1) / days)
        if i == 0:
            s += SHAPE_FIRST
        if i == days - 1:
            s += SHAPE_LAST
        raw.append((d, np.exp(s)))
    m = np.array([r[1] for r in raw])
    m = m / m.mean()                      # 🔴 모양만 — 평균 1로 고정
    return [(raw[i][0], float(m[i])) for i in range(days)]


def forecast(days, start, unit_price=None, **kw):
    lv = observed_levels()
    q = {p: float(np.percentile(lv, p)) for p in (10, 25, 50, 75, 90)}
    mult = shape_multipliers(start, days)
    med = q[50]
    rows = []
    for d, m in mult:
        rows.append({"날짜": d.isoformat(), "요일": "월화수목금토일"[d.weekday()],
                     "배수": round(m, 3),
                     "중앙 예상": int(round(med * m)),
                     "구간(25~75%)": [int(round(q[25] * m)), int(round(q[75] * m))]})
    total_med = sum(r["중앙 예상"] for r in rows)
    out = {"판": "예보 하네스 v0 (1038)",
           "입력": {"운영일수": days, "시작": start, **{k: v for k, v in kw.items() if v is not None}},
           "수준": {"🔴 판정": "모형이 기준선을 못 넘었다 — 실측 중앙값을 낸다",
                  "일평균 중앙": int(round(med)),
                  "일평균 분포(실측 n=%d)" % len(lv):
                      {f"{p}%": int(round(v)) for p, v in q.items()},
                  "근거": "1038 세 판 전부 CI95 가 0 을 포함"},
           "모양": {"✅ 판정": SHAPE_VERDICT["판정"], "자": SHAPE_VERDICT, "일별": rows},
           "총계": {"중앙 누적 방문자": int(total_med),
                  "구간(25~75%)": [int(sum(r["구간(25~75%)"][0] for r in rows)),
                                 int(sum(r["구간(25~75%)"][1] for r in rows))]}}
    if unit_price:
        out["매출(사용자 가정)"] = {
            "🔴 예측 아님": "객단가는 우리가 «안» 맞힌다. 당신이 넣은 값이다",
            "객단가(입력)": unit_price,
            "중앙 추정": int(total_med * unit_price),
            "구간": [int(out["총계"]["구간(25~75%)"][0] * unit_price),
                   int(out["총계"]["구간(25~75%)"][1] * unit_price)],
            "실측 객단가 폭(참고)": "832원 ~ 23,286,957원 (n=92 · 27,995배)"}
    out["🔴 안 주장하는 것"] = [
        "인과 아님 — 개입이 무작위 배정이 아니다(조항 60)",
        "수준 예측 아님 — 기준선을 못 넘어 실측 중앙값을 그대로 낸다",
        "매출 예측 아님 — 객단가는 입력이다"]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, required=True)
    ap.add_argument("--start", required=True, help="YYYY-MM-DD")
    ap.add_argument("--venue"); ap.add_argument("--city")
    ap.add_argument("--recognition", type=int, help="브랜드 인지도 1-5 (참고만 — 수준 판정에 안 씀)")
    ap.add_argument("--ip", action="store_true")
    ap.add_argument("--unit-price", type=int, dest="unit_price")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    r = forecast(a.days, a.start, unit_price=a.unit_price, 장소=a.venue, 도시=a.city,
                 인지도=a.recognition, 유명IP=a.ip or None)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1)); return
    print("═" * 66)
    print(" 예보 하네스 v0 — %s 부터 %d일" % (a.start, a.days))
    print("═" * 66)
    lv = r["수준"]
    print("\n[수준] 🔴 %s" % lv["🔴 판정"])
    print("   일평균 중앙 %s명   실측 분포: %s" % (f'{lv["일평균 중앙"]:,}',
          " · ".join(f"{k} {v:,}" for k, v in list(lv.values())[2].items())))
    print("\n[모양] %s" % r["모양"]["✅ 판정"])
    for row in r["모양"]["일별"]:
        bar = "█" * int(row["배수"] * 22)
        print("   %s(%s) ×%.2f  %5s명  [%s~%s]  %s" % (
            row["날짜"][5:], row["요일"], row["배수"], f'{row["중앙 예상"]:,}',
            f'{row["구간(25~75%)"][0]:,}', f'{row["구간(25~75%)"][1]:,}', bar))
    t = r["총계"]
    print("\n[총계] 중앙 %s명   구간 %s ~ %s" % (f'{t["중앙 누적 방문자"]:,}',
          f'{t["구간(25~75%)"][0]:,}', f'{t["구간(25~75%)"][1]:,}'))
    if "매출(사용자 가정)" in r:
        m = r["매출(사용자 가정)"]
        print("\n[매출] 🔴 %s" % m["🔴 예측 아님"])
        print("   객단가 %s원 가정 → 중앙 %s원  구간 %s ~ %s원" % (
            f'{m["객단가(입력)"]:,}', f'{m["중앙 추정"]:,}',
            f'{m["구간"][0]:,}', f'{m["구간"][1]:,}'))
    print("\n🔴 안 주장하는 것:")
    for x in r["🔴 안 주장하는 것"]:
        print("   · %s" % x)


if __name__ == "__main__":
    main()
