"""PnL에서 소비자 판매액 라벨을 가져온다 — 대행 수수료가 아니라 총 결제액을.

`core.project_pnl_monthly`의 매출액 섹션에는 두 가지가 섞여 있다:
    서비스매출_팝업스토어   우리(대행사) 수수료 = 이미 rev_mm_recognized로 쓰는 값
    상품매출_카드매출        **팝업의 총 결제액** ← 이게 소비자 판매액이다
    상품매출 (음수)          입점사 정산 지급(패스스루)을 빼는 대변 계정

순액(SUM(amount))을 쓰면 우리 수수료가 나온다. 실제로 문서 매출과 대조하니
비율이 0.04~1.07로 흩어졌다 — 서로 다른 수량이었다.
**양수 계정만 합산**하면 문서와 정합한다:

    RCCP2505 0.91 · RCCP2517 0.91 · RCPU2607 0.98 · RIPU2602 0.96
    RTPU2519 0.87 · RTPU2570 0.91 · RXPU2411 0.91 · RXPU2417 0.96

12건 중 8건이 0.87~0.98이고 **중앙값 0.91 = 1/1.1**이다. PnL은 공급가액,
문서는 부가세 포함이다. 그래서 총액 × 1.1로 맞춘다.

정합하지 않는 4건은 붙이지 않고 표시만 한다:
    RTPU2507 0.18 · RTPU2580 0.14   PnL이 훨씬 작다 — 부분 인식이거나 스코프가 다르다
    RTPU2534 2.16                    PnL이 훨씬 크다 — 문서가 한 레그만 담았을 수 있다
    RTPU2521 1.15                    경계선

또 하나의 함정: PnL은 **월별 인식액**이라 인식 기간이 팝업 운영 기간보다 길 수 있다.
인식 개월 수가 운영 기간의 2배를 넘으면 그 총액이 이 팝업만의 것이라고 보기 어려우므로
표시하고 붙이지 않는다(RXST 계열이 9~15개월인데 상설 매장으로 보인다).

사용:
  python3 -m ingest.pnl_sales --fetch          # BQ에서 읽어 캐시 (읽기 전용)
  python3 -m ingest.pnl_sales                  # 무엇이 붙는지
  python3 -m ingest.pnl_sales --write          # 적용
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
from datetime import date
from pathlib import Path

CACHE = Path("data/state/pnl_sales.csv")
RECORDS = Path("data/records")
VAT = 1.1                 # PnL 공급가액 → 문서 부가세포함 기준으로 환산
RATIO_OK = (0.75, 1.25)   # 문서와 대조 가능한 건의 허용 비율
MONTH_SLACK = 2.0         # 인식 개월 / 운영 개월 이 이보다 크면 스코프 의심
MAX_RUN_DAYS = 180        # 이보다 길면 팝업이 아니라 상설 매장·연간 계약이다
OFFLINE_EXCLUDE = ("온라인", "이커머스", "라이선", "licens")   # 오프라인 접점이 아닌 건

QUERY = """
SELECT project_code, ROUND(SUM(IF(amount>0, amount, 0))) gross,
       ROUND(SUM(amount)) net, COUNT(DISTINCT close_period) months,
       MIN(period_start) first_period, MAX(period_start) last_period
FROM `sweetspot-ax.core.project_pnl_monthly`
WHERE section_name='매출액' AND account_name LIKE '상품매출%'
GROUP BY 1 HAVING gross > 0
"""


def fetch() -> int:
    """BQ에서 읽어 캐시. **읽기 전용 SELECT만 수행한다.**"""
    r = subprocess.run(["bq", "--project_id=sweetspot-ax", "query", "--nouse_legacy_sql",
                        "--format=csv", "--max_rows=1000", QUERY],
                       capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[:400])
        return 1
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(r.stdout)
    print(f"캐시 저장: {CACHE} ({len(r.stdout.splitlines())-1}행)")
    return 0


def _months_of(rec: dict) -> float | None:
    per = rec["conditions"].get("period") or {}
    try:
        f, t = date.fromisoformat(per["from"]), date.fromisoformat(per["to"])
    except Exception:
        return None
    return max(1.0, (t - f).days / 30.4)


def not_a_popup(rec: dict) -> str | None:
    """팝업이 아닌 건을 걸러낸다. PnL은 팝업이든 상설이든 똑같이 매출을 담는다.

    실제로 걸린 것: RXST 계열은 삼성전자 shop Atpisode **상설 매장**이라 종료일이 없고
    인식이 9~15개월 이어진다. RTSO2402는 365일 라이선싱 계약, RCSO2401은 온라인몰이다.
    이런 건의 매출을 팝업 라벨에 섞으면 타깃의 물리량이 달라진다.
    """
    per = rec["conditions"].get("period") or {}
    if not per.get("to"):
        return "종료일 없음 — 상설 운영 또는 진행 중"
    try:
        d = (date.fromisoformat(per["to"]) - date.fromisoformat(per["from"])).days
    except Exception:
        return "기간 파싱 불가"
    if d > MAX_RUN_DAYS:
        return f"운영 {d}일 — 팝업이 아니라 상설·연간 계약"
    blob = (str(rec["entities"].get("space_key")) + " "
            + str((rec["conditions"].get("location") or {}).get("venue_type")) + " "
            + str(rec["intervention"].get("concept"))[:200]).lower()
    for w in OFFLINE_EXCLUDE:
        if w in blob:
            return f"오프라인 접점 아님 ('{w}')"
    return None


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
    pnl = {r["project_code"]: r for r in csv.DictReader(CACHE.open())}

    add, conflict, spread, notpop = [], [], [], []
    for p in sorted(RECORDS.glob("*.json")):
        rec = json.loads(p.read_text())
        code = rec["record_id"]
        if code not in pnl:
            continue
        row = pnl[code]
        gross = float(row["gross"]) * VAT
        cur = (rec["outcome"].get("totals") or {}).get("sales_krw")
        mo_rec, mo_run = int(row["months"]), _months_of(rec)
        why = not_a_popup(rec)
        if why and not cur:
            notpop.append((code, float(row["gross"]) * VAT, why))
            continue

        if cur:                                   # 대조만 한다 — 덮어쓰지 않는다
            ratio = gross / cur
            if not (RATIO_OK[0] <= ratio <= RATIO_OK[1]):
                conflict.append((code, cur, gross, ratio))
            continue
        if mo_run and mo_rec / mo_run > MONTH_SLACK:
            spread.append((code, gross, mo_rec, round(mo_run, 1)))
            continue
        add.append((code, gross, mo_rec))
        if a.write:
            rec["outcome"].setdefault("totals", {})["sales_krw"] = round(gross)
            rec["outcome"]["sales_basis"] = "PnL 상품매출 양수계정 합 × 1.1 (부가세 포함 기준)"
            rec["outcome"].setdefault("label_history", []).append(
                {"at": "pnl_sales (2026-07-28)", "action": "mine",
                 "changes": [f"sales_krw {gross:,.0f} (PnL 총 결제액)"],
                 "evidence": f"core.project_pnl_monthly 상품매출 양수계정 합 "
                             f"{float(row['gross']):,.0f}(공급가) × 1.1, 인식 {mo_rec}개월"})
            p.write_text(json.dumps(rec, ensure_ascii=False, indent=1))

    print(json.dumps({"PnL 보유": len(pnl), "신규 매출 라벨": len(add),
                      "기존과 불일치": len(conflict), "인식기간 과다로 보류": len(spread),
                      "팝업 아님으로 제외": len(notpop),
                      "기록": bool(a.write)}, ensure_ascii=False))
    print(f"\n■ 신규 ({len(add)}건)")
    for c, g, m in sorted(add, key=lambda x: -x[1])[:20]:
        print(f"   {c:10s} {g:>16,.0f}원  인식 {m}개월")
    if spread:
        print(f"\n■ 인식기간이 운영기간의 {MONTH_SLACK}배 초과 — 이 팝업만의 매출로 보기 어려움")
        for c, g, mr, mn in spread:
            print(f"   {c:10s} {g:>16,.0f}원  인식 {mr}개월 vs 운영 {mn}개월")
    if notpop:
        print("\n■ 팝업이 아니라 제외")
        for c, g, w in notpop:
            print(f"   {c:10s} {g:>16,.0f}원  {w}")
    if conflict:
        print("\n■ 기존 라벨과 불일치 — 덮어쓰지 않고 표시만 (스코프·인식 차이 조사 필요)")
        for c, cur, g, r in conflict:
            print(f"   {c:10s} 기존 {cur:>14,.0f}  PnL {g:>14,.0f}  비율 {r:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
