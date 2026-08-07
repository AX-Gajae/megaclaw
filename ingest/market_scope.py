"""시장 라벨의 스코프 판정 — 무엇을, 언제까지, 어디까지 센 숫자인가.

스텝 1에서 주최자 발표와 게이트 계수가 2.75배 벌어져 있음을 보였다. 그런데 발표 수치
안에서도 같은 행사를 다른 매체가 최대 12배까지 다르게 적는다. 그 불일치를 원문
인용문으로 대조해 보니 **측정 잡음이 아니라 스코프·시점 차이**였다:

    MKT-2025-0042  12,000(8일 누적) vs  1,000(일평균)          단위
    MKT-2026-0034  40,000(종료 직전) vs 10,000(개장 3일) vs 50,000(전망)  시점
    MKT-2023-0037  63,000(더현대 단독) vs 170,000(3회차 합계)   범위
    MKT-2023-0014  100만(2023~25 시리즈) vs 40만(작년 10일)     기간

즉 시장 라벨은 서로 다른 네 가지 질문의 답을 한 컬럼에 담고 있다.
이 모듈은 원문 인용문에서 그 넷을 판정한다.

판정 축(서로 배타적이지 않다):
  final       운영이 끝난 뒤의 최종 집계인가            ← 이것만 타깃으로 쓸 수 있다
  interim     운영 중간의 누적치인가 ("개장 3일 만에")
  forecast    아직 오지 않은 수치인가 ("~할 전망")
  multi_run   여러 회차·여러 점포의 합인가
  wider_scope 부스가 아니라 행사·상권 전체인가
  per_day     총계가 아니라 일평균인가

**중요**: '누적'이라는 말만으로는 판정할 수 없다. "8일간 누적 1만2000명"은 단일 행사의
정당한 총계이고, "3회차 누적 17만명"은 다른 행사들의 합이다. 회차·점포를 세는 표현이
함께 있을 때만 multi_run으로 본다.

사용:
  python3 -m ingest.market_scope            # 분포
  python3 -m ingest.market_scope --write    # outcome.scope_class 기록
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

MARKET = Path("data/market_records")

# 운영 중간 시점의 집계
INTERIM = re.compile(
    r"개장\s*(후|이후)|오픈\s*(후|이후)|첫\s*\d+\s*일|\d+\s*일\s*만에|"
    r"현재까지|지금까지|중간\s*집계|\d+일\s*차\s*까지|진행\s*중")
# 아직 오지 않은 수치
FORECAST = re.compile(
    r"할\s*것으로\s*(전망|예상|보인|기대)|전망이다|예상된다|목표(로|는|이)|"
    r"넘어설|달할\s*것|기대(하고|된다)")
# 여러 회차·점포의 합
MULTI_RUN = re.compile(
    r"(총\s*)?(세|네|다섯|여러|\d+)\s*(차례|회차|번째|개\s*점|개\s*지점|곳)에서|"
    r"판교[·,、]\s*대구|여러\s*지점|전국\s*\d+개|시리즈\s*누적|역대\s*누적|"
    r"\d{4}\s*[~-]\s*\d{4}|통산")
# 부스가 아니라 행사·상권 전체
WIDER = re.compile(
    r"일대(에|를|의)|행사\s*전체|축제\s*전체|페스티벌\s*전체|전시\s*전체|"
    r"타운(에|을)|백화점을\s*포함|호수\s*등")
# 총계가 아니라 일평균
PERDAY = re.compile(r"일\s*평균|하루\s*평균|일평균|하루\s*(최대|약)\s*[\d,]+\s*(여\s*)?명")
# 최종 집계임을 명시
FINAL = re.compile(
    r"최종|마감(일)?까지|종료(일)?까지|운영\s*기간\s*동안|총\s*\d+\s*일간|"
    r"기간\s*중\s*누적|폐막|마쳤|마무리")


# 인용문에 명시된 운영 기간 — 저장된 일수와 어긋나면 타깃 분모가 틀린다
DURATION = re.compile(
    r"(\d+)\s*일\s*(?:간|동안|째|만에)|(\d+)\s*주\s*(?:간|동안)|(\d+)\s*개?월\s*(?:간|동안|여)")


def stated_days(quote: str) -> int | None:
    """인용문이 말하는 기간(일). '오픈 3일 만에 10만명'이면 3."""
    m = DURATION.search(quote or "")
    if not m:
        return None
    if m.group(1):
        return int(m.group(1))
    if m.group(2):
        return int(m.group(2)) * 7
    if m.group(3):
        return int(m.group(3)) * 30
    return None


def classify(quote: str, event_name: str = "") -> dict:
    q = f"{quote} {event_name}"
    c = {
        "interim": bool(INTERIM.search(q)),
        "forecast": bool(FORECAST.search(q)),
        "multi_run": bool(MULTI_RUN.search(q)),
        "wider_scope": bool(WIDER.search(q)),
        "per_day": bool(PERDAY.search(q)),
        "final_marked": bool(FINAL.search(q)),
    }
    # 최종 집계로 쓸 수 있는가 — 넷 중 하나라도 걸리면 안 된다
    c["usable"] = not (c["interim"] or c["forecast"] or c["multi_run"] or c["wider_scope"])
    return c


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    tally, rows = Counter(), []
    n = 0
    for p in sorted(MARKET.glob("*.json")):
        m = json.loads(p.read_text())
        o = m["outcome"]
        if not o.get("visitors_total"):
            continue
        n += 1
        q = str(o.get("visitors_source_quote") or "")
        c = classify(q, str(m.get("event_name") or ""))
        # 분모 교정 — 인용 기간이 저장 일수와 25% 넘게 다르면 인용을 따른다.
        # 21건 전부 저장 일수가 더 컸다(중간 집계 라벨에 전체 기간을 분모로 쓴 결과).
        du = (m["conditions"].get("derived") or {}).get("duration") or {}
        d0 = du.get("days") or o.get("visitors_period_days")
        sd = stated_days(q)
        if d0 and sd and abs(sd - d0) / max(sd, d0) > 0.25:
            c["days_stated"] = sd
            c["days_stored"] = d0
            c["days_corrected"] = True
            tally["분모 교정"] += 1
        for k, v in c.items():
            if v and k != "usable":
                tally[k] += 1
        tally["usable" if c["usable"] else "오염"] += 1
        rows.append((m["market_record_id"], o["visitors_total"], c,
                     str(o.get("visitors_source_quote") or "")[:60]))
        if a.write:
            o["scope_class"] = c
            p.write_text(json.dumps(m, ensure_ascii=False, indent=1))
    print(json.dumps({"시장 라벨": n,
                      "최종 집계로 사용 가능": tally["usable"],
                      "스코프 오염": tally["오염"],
                      "유형별": {k: tally[k] for k in
                                 ("interim", "forecast", "multi_run", "wider_scope",
                                  "per_day", "final_marked")},
                      "기록": a.write}, ensure_ascii=False, indent=1))
    bad = [r for r in rows if not r[2]["usable"]]
    print(f"\n■ 오염 상위 (값 큰 순)")
    for r in sorted(bad, key=lambda x: -x[1])[:14]:
        tags = "+".join(k for k, v in r[2].items() if v and k not in ("usable", "final_marked"))
        print(f"   {r[0]:16s} {r[1]:>10,}  {tags}")
        print(f"      {r[3]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
