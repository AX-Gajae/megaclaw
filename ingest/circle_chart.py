"""써클차트 기계 수집 — 리테일 일간(POS 실판매) API로 데뷔 앨범 7일 합산 = 초동 근사.

리서치(2026-07-27)에서 무인증 접근·2019-04 소급을 실호출로 검증한 경로.
  POST https://circlechart.kr/data/api/chart/retail_list  (termGbn=day, yyyymmdd)
  POST https://circlechart.kr/data/api/chart/album        (termGbn=week/month)

용도: 크롤링 에이전트가 모은 초동(한터/언론 계열)의 **교차검증 층**.
계열이 다르므로(패널 POS vs 한터 소매망) 절대치 일치가 아니라 상관·비율 확인용.

주의: 사이트에 AI/ML 학습·TDM 금지 고지가 있다. 본 스크립트는 연구 목적 소량 조회이며,
저장은 원숫자 대신 구간 라벨 권장(docs/idol_domain_prework.md §1).

사용: python3 -m ingest.circle_chart --date 2025-03-10 [--days 7] [--out data/idol_raw/circle]
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import date, timedelta
from pathlib import Path

import requests

BASE = "https://circlechart.kr/data/api/chart"
HDR = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
       "Referer": "https://circlechart.kr/page_chart/retail.circle",
       "X-Requested-With": "XMLHttpRequest"}


def retail_day(d: date) -> list[dict]:
    """일간 리테일 차트. 응답은 {"0": {...}, "1": {...}} 형태의 순번 키 딕셔너리."""
    r = requests.post(f"{BASE}/retail_list", headers=HDR, timeout=20,
                      data={"termGbn": "day", "yyyymmdd": d.strftime("%Y%m%d")})
    r.raise_for_status()
    js = r.json()
    if isinstance(js, dict):
        rows = js.get("List") or js.get("list")
        if isinstance(rows, list):
            return rows
        return [v for k, v in sorted(js.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 1e9)
                if isinstance(v, dict)]
    return js if isinstance(js, list) else []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="시작일 YYYY-MM-DD (앨범 발매일)")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--out", default="data/idol_raw/circle")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    d0 = date.fromisoformat(args.date)
    agg: dict[str, dict] = {}
    for i in range(args.days):
        d = d0 + timedelta(days=i)
        f = out / f"retail_{d.isoformat()}.json"
        if f.exists():
            cached = json.loads(f.read_text())
            rows = ([v for k, v in sorted(cached.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 1e9)
                     if isinstance(v, dict)] if isinstance(cached, dict) else cached)
        else:
            try:
                rows = retail_day(d)
            except Exception as e:
                print(f"  {d} 실패: {type(e).__name__}", flush=True)
                continue
            f.write_text(json.dumps(rows, ensure_ascii=False))
            time.sleep(1.2)   # 예의상 간격
        for row in rows:
            name = (row.get("Album") or row.get("ALBUM_NAME") or "").strip()
            art = (row.get("Artist") or row.get("ARTIST_NAME") or "").strip()
            cnt = row.get("KSum") or row.get("Album_CNT") or row.get("CNT") or 0
            try:
                cnt = int(str(cnt).replace(",", ""))
            except ValueError:
                cnt = 0
            key = f"{art}||{name}"
            a = agg.setdefault(key, {"artist": art, "album": name, "sum7": 0, "days": 0})
            a["sum7"] += cnt
            a["days"] += 1
        print(f"  {d}: {len(rows)}행", flush=True)

    top = sorted(agg.values(), key=lambda x: -x["sum7"])[:40]
    res = out / f"sum7_{args.date}.json"
    res.write_text(json.dumps(top, ensure_ascii=False, indent=1))
    print(json.dumps({"기준일": args.date, "일수": args.days, "집계앨범": len(agg),
                       "저장": str(res)}, ensure_ascii=False))
    for t in top[:10]:
        print(f"  {t['sum7']:>8,}  {t['artist'][:18]:20s} {t['album'][:34]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
