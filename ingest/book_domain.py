"""네 번째 도메인 --- 도서 출간. 알라딘 상품 페이지에서 축과 라벨을 수집한다.

노트 33이 병목을 확정했다. ``전이 상관 = 대상 자기 상관''(r=+0.988)이라는 결론이
대상 셋에서 나왔으므로 세 점의 상관을 여섯 번 센 것에 가깝다. 네 번째 도메인이
없으면 전이 알고리즘 개선 중단 결정도, 겹침 유도 λ도, 가법 모형도 미검증이다.

**선정 기준이 바뀌었다.** 노트 24와 33에 따르면 출처로서의 품질은 무의미하고
대상으로서 자기 라벨을 설명할 수 있는지가 전부다. 그래서 라벨이 명확하고 축이
많이 관측되는 도메인을 고른다.

도서를 고른 이유:
  · 라벨이 명확하다 --- 알라딘 판매지수(Sales Point)는 판매량과 기간의 함수다.
  · 축이 잘 관측된다 --- 쪽수, 정가, 판형, 출판사 이력이 모두 상품 페이지에 있다.
  · 굿즈 규모의 대응물이 자연스럽다 --- **쪽수 = 콘텐츠 분량**이고, 게임에서
    설치 용량을 쓴 것과 같은 논리다(노트 25).
  · 크라우드펀딩(텀블벅·와디즈)을 먼저 시도했으나 SPA와 403으로 막혔다.

**시간 누적 주의.** 판매지수는 누적 판매에 근거하므로 오래된 책일수록 크다.
게임 리뷰와 같은 구조이며(노트 13) 출간일 기준 탈추세가 필수다.

사용:
  python3 -m ingest.book_domain --want 400
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path("data/state/book_records.json")
CACHE = Path("data/state/cache_aladin_book")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
      "Accept-Language": "ko-KR,ko;q=0.9"}
DELAY = 2.0
RETRY = 3
COOLDOWN_EVERY = 25


def _fetch(url: str, key: str) -> str | None:
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / (re.sub(r"[^0-9A-Za-z_.-]", "_", key)[:90] + ".html")
    if f.exists():
        return f.read_text(encoding="utf-8", errors="ignore")
    for attempt in range(RETRY):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                        timeout=25) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                html = raw.decode("utf-8", "ignore")
            time.sleep(DELAY)
            f.write_text(html, encoding="utf-8")
            return html
        except (urllib.error.HTTPError, urllib.error.URLError, OSError,
                TimeoutError) as e:
            w = DELAY * (4 ** attempt)
            print(f"    [재시도 {attempt+1}/{RETRY}] {key}: {type(e).__name__} — {w:.0f}초")
            time.sleep(w)
    return None


def item_ids(want: int) -> list[str]:
    """베스트셀러 목록에서 상품 번호를 모은다.

    주간 베스트셀러를 여러 분야·여러 주차로 훑는다. 한 목록만 쓰면 분야가
    치우치고, 판매지수 분포가 상위에 몰려 축의 변별력이 떨어진다(노트 11의
    '축은 변해야 쓸모가 있다')."""
    ids, seen = [], set()
    # 분야 코드 --- 소설, 경제경영, 인문, 자기계발, 과학, 역사, 사회과학, 에세이
    cats = [1, 170, 656, 336, 987, 74, 798, 55889]
    for cat in cats:
        for page in (1, 2, 3):
            u = ("https://www.aladin.co.kr/shop/common/wbest.aspx"
                 f"?BranchType=1&CID={cat}&page={page}&cnt=1000&SortOrder=1")
            h = _fetch(u, f"best_{cat}_{page}")
            if not h:
                break
            got = list(dict.fromkeys(re.findall(r"ItemId=(\d+)", h)))
            got = [g for g in got if g not in seen]
            if not got:
                break
            seen.update(got)
            ids += got
            if len(ids) >= want:
                return ids[:want]
    return ids[:want]


# 텍스트에서만 나오는 것들. 나머지는 JSON-LD 구조화 데이터에서 받는다 ---
# 정규식보다 안정적이고 '@type: Book' 으로 도서 여부까지 걸러진다
# (베스트셀러 목록에 LP·DVD가 섞여 들어온다).
TXT_PAT = {
    "sales_point": re.compile(r"Sales\s*Point\s*:\s*([\d,]+)"),
    "pages": re.compile(r"(\d{2,4})\s*쪽"),
    "weight_g": re.compile(r"(\d{2,4})\s*g\b"),
}
SIZE = re.compile(r"(\d{2,3})\s*\*\s*(\d{2,3})\s*mm")
LD = re.compile(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', re.S)


def parse(html: str, item_id: str) -> dict | None:
    m = LD.search(html)
    if not m:
        return None
    try:
        d = json.loads(m.group(1).strip())
    except json.JSONDecodeError:
        return None
    if isinstance(d, list):
        d = d[0] if d else {}
    if d.get("@type") != "Book":          # LP·DVD 제외
        return None

    we = d.get("workExample") or []
    we = we[0] if isinstance(we, list) and we else (we if isinstance(we, dict) else {})
    offers = d.get("offers") or {}
    rating = d.get("aggregateRating") or {}
    genre = [g.strip() for g in (d.get("genre") or "").split(",") if g.strip()]

    out = {"record_id": f"BOOK-{item_id}", "item_id": item_id,
           "title": d.get("name"),
           "publisher": ((d.get("publisher") or {}).get("name")),
           "pub_date": we.get("datePublished"),
           "isbn": we.get("isbn"),
           "book_format": (we.get("bookFormat") or "").rsplit("/", 1)[-1],
           "price": offers.get("price"),
           "n_genre": len(genre), "genre": genre[:6],
           "review_count": int(rating.get("reviewCount") or 0),
           "rating": float(rating.get("ratingValue") or 0) or None}

    txt = re.sub(r"<script.*?</script>", " ", html, flags=re.S)
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = re.sub(r"\s+", " ", txt)
    for k, rx in TXT_PAT.items():
        mm = rx.search(txt)
        if mm:
            out[k] = int(mm.group(1).replace(",", ""))
    sm = SIZE.search(txt)
    if sm:
        out["width_mm"], out["height_mm"] = int(sm.group(1)), int(sm.group(2))

    if not out.get("sales_point") or not out.get("pub_date"):
        return None
    return out


def run(want: int = 400) -> dict:
    prev = json.loads(OUT.read_text()) if OUT.exists() else {}
    ids = item_ids(want)
    print(f"도서 도메인 수집 --- 후보 {len(ids)}건 (기수집 {len(prev)})")
    for i, iid in enumerate(ids, 1):
        rid = f"BOOK-{iid}"
        if rid in prev:
            continue
        h = _fetch(f"https://www.aladin.co.kr/shop/wproduct.aspx?ItemId={iid}",
                   f"item_{iid}")
        if not h:
            continue
        rec = parse(h, iid)
        if rec:
            prev[rid] = rec
        if i % 25 == 0:
            OUT.write_text(json.dumps(prev, ensure_ascii=False, indent=1))
            print(f"  {i}/{len(ids)} 처리 · 채택 {len(prev)}")
        if i % COOLDOWN_EVERY == 0:
            time.sleep(12)
    OUT.write_text(json.dumps(prev, ensure_ascii=False, indent=1))
    import collections
    import numpy as np
    yr = collections.Counter(v["pub_date"][:4] for v in prev.values())
    sp = np.array([v["sales_point"] for v in prev.values()], float)
    print(f"\n총 {len(prev)}건  연도: {dict(sorted(yr.items()))}")
    if len(sp):
        print(f"판매지수 log10  평균 {np.log10(np.maximum(sp,1)).mean():.2f}  "
              f"SD {np.log10(np.maximum(sp,1)).std():.2f}")
        for k in ("pages", "price", "weight_g", "publisher", "n_genre",
                  "review_count", "book_format"):
            c = sum(1 for v in prev.values() if v.get(k))
            print(f"  {k:<12}{c:>4}/{len(prev)} ({c/len(prev):.0%})")
    return prev


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--want", type=int, default=400)
    a = ap.parse_args()
    run(a.want)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
