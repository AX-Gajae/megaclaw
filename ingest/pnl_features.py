"""오픈 **전 달**에 이미 계상된 비용 — 예측 시점에 알 수 있는 준비 강도.

PnL 판매관리비는 프로젝트 355건을 덮는다. 라벨(방문 96 / 매출 70)보다 3.5배 조밀한
유일한 수치 계열이라 피처로 쓸 값어치가 있다. 문제는 시간 마스크다.

**월 단위 계상이라는 함정.** 계정별 첫 계상일과 오픈일의 중앙 차이는 전부 음수다
(여비교통비 -30일, 시공비 -10일, 디자인 +1일). 그런데 `period_start`는 월초이므로,
11/20 오픈 팝업의 첫 계상이 11/01이면 차이는 -19일이지만 **실제 비용은 11월 중
언제 발생했는지 모른다.** 오픈 후일 수도 있다.

그래서 `first_month < DATE_TRUNC(open_date, MONTH)` — **엄격히 이전 달**만 쓴다.
이 기준에서 계정별 커버리지는 크게 줄어든다:

    복리후생비_식음료대  144/292      지급수수료_물품대여   52/208
    여비교통비_외근      134/276      지급수수료_제작비     47/136
    소모품비_현장        114/277      지급수수료_시공       29/191
    여비교통비_야근       98/211      지급수수료_공간수수료 26/89

시공비는 191건 중 29건(15%)만 남는다. "시공비 124건이 시작월 이내·이전"이라는 집계는
'이내'(같은 달, 안전하지 않음)와 '이전'(안전)을 섞은 것이다.

만드는 피처 — 계정별 금액이 아니라 **집계량**이다. 계정 하나하나를 컬럼으로 만들면
n=82에 20컬럼이 추가돼 과적합만 늘린다.
    pnl_pre_total     오픈 전 달까지 계상된 판관비 합 (log1p)
    pnl_pre_accounts  그 시점까지 계상된 계정 종류 수 — 준비의 폭
    pnl_pre_months    첫 계상월부터 오픈월까지의 개월 — 준비 기간

사용:
  python3 -m ingest.pnl_features --fetch      # BQ 읽기 전용 조회 → 캐시
  python3 -m ingest.pnl_features              # 커버리지 확인
  python3 -m ingest.pnl_features --write      # 적용
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
from collections import defaultdict
from datetime import date
from pathlib import Path

CACHE = Path("data/state/pnl_cost.csv")
RECORDS = Path("data/records")

QUERY = """
SELECT project_code, account_name, CAST(period_start AS STRING) period_start,
       ROUND(SUM(amount)) amt
FROM `sweetspot-ax.core.project_pnl_monthly`
WHERE section_name='판매관리비'
  AND REGEXP_CONTAINS(project_code, r'^R[A-Z][A-Z][A-Z][0-9]{4}$')
GROUP BY 1,2,3
"""


def fetch() -> int:
    """읽기 전용 SELECT만."""
    r = subprocess.run(["bq", "--project_id=sweetspot-ax", "query", "--nouse_legacy_sql",
                        "--format=csv", "--max_rows=100000", QUERY],
                       capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[:400])
        return 1
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(r.stdout)
    print(f"캐시 저장: {CACHE} ({len(r.stdout.splitlines())-1}행)")
    return 0


def compute(code: str, open_from: str, rows: list) -> dict | None:
    """오픈 **전 달**까지 계상된 것만 집계."""
    try:
        cutoff = date.fromisoformat(open_from).replace(day=1)
    except Exception:
        return None
    pre = [r for r in rows if date.fromisoformat(r["period_start"]) < cutoff]
    if not pre:
        return None
    months = {r["period_start"] for r in pre}
    return {"pnl_pre_total": sum(float(r["amt"]) for r in pre),
            "pnl_pre_accounts": len({r["account_name"] for r in pre}),
            "pnl_pre_months": len(months),
            "pnl_pre_first": min(months)}


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
    by = defaultdict(list)
    for r in csv.DictReader(CACHE.open()):
        by[r["project_code"]].append(r)

    n = lab = 0
    for p in sorted(RECORDS.glob("*.json")):
        rec = json.loads(p.read_text())
        per = rec["conditions"].get("period") or {}
        f = compute(rec["record_id"], per.get("from") or "", by.get(rec["record_id"], []))
        if not f:
            continue
        n += 1
        if rec["outcome"]["totals"].get("visitors"):
            lab += 1
        if a.write:
            rec["conditions"].setdefault("derived", {})["pnl_pre"] = f
            p.write_text(json.dumps(rec, ensure_ascii=False, indent=1))
    print(json.dumps({"PnL 보유 프로젝트": len(by), "오픈 전 달 계상 있음": n,
                      "그중 방문 라벨 보유": lab, "기록": bool(a.write)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
