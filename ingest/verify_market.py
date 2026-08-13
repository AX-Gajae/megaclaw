"""시장 레코드 Stage 4 검증 프리패스 — URL 접속 → quote 존재 → 숫자 일치 (결정론).

Kimi 크롤링 산출물(records_merged.jsonl)의 방문·매출 라벨을 원 기사에서 대조한다.
결과: data/market_raw/verify_results.jsonl — {record_id, metric, status, detail}
  status: verified(quote+숫자 확인) / quote_only(quote는 있으나 숫자 표기 미확인) /
          quote_missing(페이지는 열리나 quote 부재) / unreachable(접속 실패) / no_url
프리패스에서 verified 안 된 건만 에이전트(WebFetch) 판정으로 넘긴다.
"""
from __future__ import annotations

import json
import re
import time
import urllib.parse
from pathlib import Path

import requests

RAW = Path("data/market_raw/records_merged.jsonl")
OUT = Path("data/market_raw/verify_results.jsonl")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def number_variants(v: float) -> list[str]:
    """한국어 기사 표기 변형: 550000 → 550,000 / 55만 / 55만명 / 5억5000만 등."""
    v = int(v)
    out = [f"{v:,}", str(v)]
    if v >= 10000 and v % 10000 == 0:
        man = v // 10000
        if man >= 10000 and man % 10000 == 0:
            out.append(f"{man // 10000}억")
        out.append(f"{man:,}만".replace(",", ""))
        out.append(f"{man:,}만")
    elif v >= 10000:
        man, rest = divmod(v, 10000)
        out.append(f"{man}만{rest:,}".replace(",", ""))
        out.append(f"{man}만 {rest:,}")
        if rest >= 1000 and rest % 1000 == 0:
            out.append(f"{man}만{rest // 1000}천")
    if v >= 100_000_000:
        eok, rest = divmod(v, 100_000_000)
        out.append(f"{eok}억" if rest == 0 else f"{eok}억{rest // 10000}만")
        if rest and rest % 10_000_000 == 0:
            out.append(f"{eok}.{rest // 10_000_000}억")
    return out


def fetch(url: str, cache: dict) -> str | None:
    if url in cache:
        return cache[url]
    try:
        r = requests.get(url, headers=UA, timeout=15, allow_redirects=True)
        text = r.text if r.status_code == 200 else None
    except Exception:
        text = None
    cache[url] = norm(text) if text else None
    return cache[url]


def check(page_norm: str, quote: str, value) -> str:
    q = norm(quote)
    core = q[len(q) // 2 - 20: len(q) // 2 + 20] if len(q) > 40 else q  # 중간 40자
    has_quote = core in page_norm or (len(q) > 60 and q[:40] in page_norm)
    has_num = any(norm(nv) in page_norm for nv in number_variants(value)) if value else False
    if has_quote and has_num:
        return "verified"
    if has_quote:
        return "quote_only"
    if has_num:
        return "num_only"
    return "quote_missing"


def main() -> int:
    import sys
    if "--records" in sys.argv:   # 편입된 market_records 전체(2차 수집분 포함) 검증
        from pathlib import Path as _P
        recs = [json.loads(p.read_text()) for p in sorted(_P("data/market_records").glob("*.json"))]
        only_new = "--new-only" in sys.argv
        if only_new:
            recs = [r for r in recs if r["market_record_id"].startswith("MKT2-")]
        globals()["OUT"] = _P("data/market_raw/verify_results2.jsonl")
    else:
        recs = [json.loads(l) for l in open(RAW)]
    cache: dict = {}
    # 🔴 **960 수리 --- `open(OUT, "w")` 는 여는 순간 자른다.**
    #
    # 이 함수는 그 손잡이를 쥔 채 **수백 번의 HTTP 요청**을 돈다(도메인마다 1초 대기).
    # 그 사이 파일은 **비어 있고**, 러너가 중간에 죽으면 옛 결과가 통째로 사라진다.
    # `kopis953`(954 수리) · `wikidaily941`(959 수리) · `steamrev941`(952 수리) 과
    # **같은 병**이고, 티처 #98 이 세 번째 자리로 이것을 지목했다.
    #
    # 🔴 그래서 **`.part` 에 쓰고 끝에 갈아 끼운다**(같은 파일계라 `os.replace` 는 원자적).
    # 러너가 죽으면 `.part` 만 남고 **옛 결과는 멀쩡히 살아 있다.**
    _final = Path(OUT)
    _part = _final.with_suffix(_final.suffix + ".part")
    _final.parent.mkdir(parents=True, exist_ok=True)
    out = open(_part, "w")
    counts: dict = {}
    last_domain_hit: dict = {}
    for i, r in enumerate(recs):
        o = r["outcome"]
        for metric, vkey, qkey, ukey in (("visitors", "visitors_total", "visitors_source_quote", "visitors_source_url"),
                                          ("sales", "sales_krw", "sales_source_quote", "sales_source_url")):
            if not o.get(vkey):
                continue
            url, quote = o.get(ukey), o.get(qkey)
            if not url or not quote:
                status, detail = "no_url", ""
            else:
                dom = urllib.parse.urlparse(url).netloc
                wait = last_domain_hit.get(dom, 0) + 1.0 - time.time()
                if wait > 0 and url not in cache:
                    time.sleep(wait)
                page = fetch(url, cache)
                if url not in last_domain_hit or True:
                    last_domain_hit[dom] = time.time()
                if page is None:
                    status, detail = "unreachable", dom
                else:
                    status, detail = check(page, quote, o.get(vkey)), dom
            counts[status] = counts.get(status, 0) + 1
            out.write(json.dumps({"record_id": r["market_record_id"], "metric": metric,
                                    "value": o.get(vkey), "url": url, "status": status,
                                    "detail": detail}, ensure_ascii=False) + "\n")
        if (i + 1) % 50 == 0:
            print(f"{i+1}/{len(recs)} … {counts}", flush=True)
    out.close()
    import os as _os
    _os.replace(_part, _final)                   # 🔴 원자적 갈아 끼우기(960 수리)
    n = sum(1 for _ in open(_final))             # 🔴 「썼다」가 아니라 다시 열어 센다(조항 59)
    print(json.dumps({**counts, "🔴 다시 열어 센 줄": n,
                      "🔴 쓴 것 == 다시 센 것": n == sum(counts.values())},
                     ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
