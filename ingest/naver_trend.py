"""네이버 데이터랩 검색 트렌드 — 집단 상태의 '큰 창'.

배경(2026-07-27): popga 행동 데이터는 방문객의 프록시가 아님이 확정됐다(전 채널 r<0.25,
원인은 모집단 스케일 불일치 — 조회 중앙값 86명 vs 방문 수천~수만). 집단 상태를 재려면
모집단이 큰 관측 창이 필요하다. 데이터랩은 전 국민 검색을 커버하고 2016년까지 소급되며
공식 API라 시간 마스크가 완벽하다.

**결정적 설계 — 앵커 정규화**:
  데이터랩은 절대 검색량이 아니라 요청 묶음 내 최댓값=100인 **상대지수**를 준다. 따라서
  서로 다른 요청의 값은 비교 불가다. 모든 요청에 고정 앵커 키워드를 함께 넣어
  (대상 지수 / 앵커 지수)로 환산해야 IP 간·시점 간 비교가 성립한다.
  앵커는 검색량이 크고 안정적이며 계절성이 약한 일반어를 쓴다.

키: .env 에 NAVER_CLIENT_ID / NAVER_CLIENT_SECRET
  발급 https://developers.naver.com/apps/#/register (데이터랩 API 선택, 무료·일 1,000회)

사용:
  python3 -m ingest.naver_trend --probe "뉴진스"            # 단건 확인
  python3 -m ingest.naver_trend --records --domain popup     # 뱅크 전체 수집
"""
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import date, timedelta
from pathlib import Path

import requests

API = "https://openapi.naver.com/v1/datalab/search"
OUT = Path("data/state/naver")
ANCHORS = ["날씨"]          # 검색량 크고 안정적 — 스케일 앵커
MAX_GROUPS = 5              # API 제한: 요청당 키워드 그룹 5개


def creds() -> tuple[str, str] | None:
    cid = os.environ.get("NAVER_CLIENT_ID")
    sec = os.environ.get("NAVER_CLIENT_SECRET")
    if cid and sec:
        return cid, sec
    env = Path(".env")
    if env.exists():
        kv = dict(l.split("=", 1) for l in env.read_text().splitlines() if "=" in l)
        cid, sec = kv.get("NAVER_CLIENT_ID"), kv.get("NAVER_CLIENT_SECRET")
        if cid and sec:
            return cid.strip(), sec.strip()
    return None


def fetch(keywords: list[str], start: str, end: str, unit: str = "week") -> dict | None:
    """keywords(≤4) + 앵커를 한 요청에 담아 상대지수를 받는다."""
    c = creds()
    if not c:
        raise RuntimeError("NAVER_CLIENT_ID/SECRET 없음 — .env에 추가 필요")
    cid, sec = c
    groups = [{"groupName": k, "keywords": [k]} for k in keywords[:MAX_GROUPS - len(ANCHORS)]]
    groups += [{"groupName": a, "keywords": [a]} for a in ANCHORS]
    body = {"startDate": start, "endDate": end, "timeUnit": unit, "keywordGroups": groups}
    r = requests.post(API, headers={"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": sec,
                                     "Content-Type": "application/json"},
                      data=json.dumps(body), timeout=20)
    if r.status_code != 200:
        print(f"  API {r.status_code}: {r.text[:160]}")
        return None
    return r.json()


def anchored(res: dict) -> dict:
    """앵커 대비 비율로 환산 — 요청 간 비교 가능한 스케일."""
    series = {g["title"]: {p["period"]: p["ratio"] for p in g["data"]} for g in res["results"]}
    anc = series.get(ANCHORS[0], {})
    out = {}
    for name, s in series.items():
        if name in ANCHORS:
            continue
        out[name] = {p: (v / anc[p] if anc.get(p) else None) for p, v in s.items()}
    return out


def state_features(ratio: dict[str, float | None], open_date: str, weeks: int = 12) -> dict | None:
    """오픈일 기준 사전 검색 상태 — 시간 마스크(오픈 이전만)."""
    pts = sorted((p, v) for p, v in ratio.items() if v is not None and p < open_date)
    if len(pts) < 4:
        return None
    vals = [v for _, v in pts][-weeks:]
    import math
    import numpy as np
    a = np.array(vals, float)
    last4 = a[-4:].mean()
    prev4 = a[-8:-4].mean() if len(a) >= 8 else a[:max(1, len(a) - 4)].mean()
    return {
        "level": float(math.log1p(last4 * 1000)),                  # 규모(앵커 대비)
        "momentum": float(math.log1p(last4 * 1000) - math.log1p(prev4 * 1000 + 1e-9)),
        "volatility": float(np.std(a) / (np.mean(a) + 1e-9)),
        "peak_ratio": float(a.max() / (last4 + 1e-9)),
        "n_weeks": len(a),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe")
    ap.add_argument("--records", action="store_true")
    ap.add_argument("--domain", default="popup")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    if not creds():
        print(json.dumps({
            "상태": "네이버 API 키 없음",
            "필요": "NAVER_CLIENT_ID / NAVER_CLIENT_SECRET",
            "발급": "https://developers.naver.com/apps/#/register — 애플리케이션 등록 후 "
                    "'데이터랩(검색어트렌드)' API 추가. 무료, 일 1,000회.",
            "설정": "world_model/.env 에 두 줄 추가",
        }, ensure_ascii=False, indent=1))
        return 2

    if args.probe:
        end = date.today() - timedelta(days=1)
        start = end - timedelta(days=365 * 2)
        res = fetch([args.probe], start.isoformat(), end.isoformat())
        if res:
            r = anchored(res)[args.probe]
            pts = [(p, v) for p, v in sorted(r.items()) if v]
            print(f"{args.probe}: {len(pts)}주 / 앵커대비 최근값 {pts[-1][1]:.4f} / 최대 {max(v for _,v in pts):.4f}")
        return 0

    if args.records:
        # 대상: 라벨 보유 레코드의 IP·브랜드 키워드
        targets = []
        if args.domain == "popup":
            for p in sorted(Path("data/records").glob("*.json")):
                r = json.loads(p.read_text())
                if not r["outcome"]["totals"].get("visitors"):
                    continue
                kw = r["entities"].get("brand_key") or r["intervention"].get("brand_name")
                pf = (r["conditions"].get("period") or {}).get("from")
                if kw and pf:
                    targets.append({"id": r["record_id"], "kw": str(kw)[:20], "open": pf})
        else:
            for p in sorted(Path("data/idol_records").glob("*.json")):
                r = json.loads(p.read_text())
                if r.get("chodong") and r.get("debut_date") and r.get("group_name"):
                    targets.append({"id": r["record_id"], "kw": r["group_name"][:20],
                                     "open": r["debut_date"]})
        if args.limit:
            targets = targets[:args.limit]
        print(f"대상 {len(targets)}건 — 요청 {(len(targets) + 3) // 4}회 (배치 4키워드 + 앵커)")
        store = {}
        f = OUT / f"{args.domain}_trend.json"
        if f.exists():
            store = json.loads(f.read_text())
        todo = [t for t in targets if t["id"] not in store]
        for i in range(0, len(todo), MAX_GROUPS - len(ANCHORS)):
            batch = todo[i:i + MAX_GROUPS - len(ANCHORS)]
            lo = min(t["open"] for t in batch)
            start = (date.fromisoformat(lo) - timedelta(days=180)).isoformat()
            end = max(t["open"] for t in batch)
            res = fetch([t["kw"] for t in batch], start, end)
            if res:
                ar = anchored(res)
                for t in batch:
                    sf = state_features(ar.get(t["kw"], {}), t["open"])
                    store[t["id"]] = {"kw": t["kw"], "open": t["open"], "state": sf}
                f.write_text(json.dumps(store, ensure_ascii=False, indent=1))
            time.sleep(0.3)
            if (i // 4) % 20 == 0:
                print(f"  {i}/{len(todo)} …", flush=True)
        ok = sum(1 for v in store.values() if v.get("state"))
        print(json.dumps({"수집": len(store), "상태 산출": ok, "저장": str(f)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
