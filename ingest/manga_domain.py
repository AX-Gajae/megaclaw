"""아홉 번째 도메인 --- 일본 만화. AniList 공개 GraphQL에서 축과 라벨을 모은다.

노트 76이 배선을 닫았고 노트 77이 누출을 다 막았다. 남은 지렛대는 도메인
하나뿐이다 --- 셀 54$\\to$72.

**만화를 고른 이유가 셋이다.**

  · 라벨이 **서재 등록 수**(popularity)다. 웹툰 관심 등록 수·게임 리뷰 총계와
    같은 누적 물리량이라 log 경과일 탈추세를 그대로 쓴다.
  · 웹툰과 표면이 가장 가까운데 시장이 완전히 다르다 --- 일본 출판 만화 대
    한국 플랫폼 웹툰. 노트 74가 ``닮은 것이 특별하지 않다''를 스팀/모바일에서
    봤는데 두 번째 사례가 된다.
  · **만화 IP는 팝업의 최대 원천 중 하나다**(원피스 · 체인소맨 · 주술회전).

엔드포인트 하나다(키 불필요).

    POST https://graphql.anilist.co   type: MANGA, sort: POPULARITY_DESC

**표본은 인기순 상위다.** 스팀 topsellers · 앱스토어 차트와 같은 방식이며 같은
한계를 갖는다 --- 롱테일이 없다.

**누출 주의.** 권수와 화수는 연재가 이어지면 늘어난다(노트 21의 DLC 구조).
웹툰과 같은 처리를 쓴다 --- 경과 주로 나눈 **연재 밀도**. 작가 이력은 표본 안에서
**자기보다 먼저 시작한 것만** 센다.

사용:
  python3 -m ingest.manga_domain --want 2000
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

OUT = Path("data/state/manga_records.json")
CACHE = Path("data/state/cache_manga")
API = "https://graphql.anilist.co"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
      "Content-Type": "application/json", "Accept": "application/json"}
DELAY = 2.0
PER = 50

Q = """
query ($p: Int, $n: Int) {
  Page(page: $p, perPage: $n) {
    pageInfo { total hasNextPage }
    media(type: MANGA, sort: POPULARITY_DESC) {
      id title { romaji } genres tags { name rank }
      chapters volumes format status countryOfOrigin isAdult
      popularity favourites meanScore
      startDate { year month day }
      staff(perPage: 6) { edges { role node { id } } }
    }
  }
}
"""


def _post(page: int) -> dict | None:
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"page_{page}.json"
    if f.exists():
        try:
            return json.loads(f.read_text())
        except json.JSONDecodeError:
            f.unlink()
    body = json.dumps({"query": Q, "variables": {"p": page, "n": PER}}).encode()
    for attempt in range(4):
        try:
            req = urllib.request.Request(API, data=body, headers=UA, method="POST")
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read().decode("utf-8"))
            if "errors" in d and not d.get("data"):
                time.sleep(4 * (attempt + 1))
                continue
            f.write_text(json.dumps(d, ensure_ascii=False))
            time.sleep(DELAY)
            return d
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError):
            time.sleep(4 * (attempt + 1))
    return None


def build(m: dict) -> dict | None:
    pop = m.get("popularity")
    sd = m.get("startDate") or {}
    yy = sd.get("year")
    if not pop or not yy:
        return None
    mm, dd = sd.get("month") or 1, sd.get("day") or 1
    staff = [(e.get("role") or "", ((e.get("node") or {}).get("id")))
             for e in ((m.get("staff") or {}).get("edges") or [])]
    # 원작·작화만 센다. 편집·번역은 체급 신호가 아니다.
    auth = [i for r, i in staff if i and any(
        k in r for k in ("Story", "Art", "Original"))]
    return {"record_id": f"MG-{m['id']}", "media_id": m["id"],
            "title": ((m.get("title") or {}).get("romaji")),
            "start_date": f"{yy:04d}-{mm:02d}-{dd:02d}",
            # ── 라벨 ── 서재 등록 수. 웹툰 관심 수와 같은 물리량이다.
            "y_popularity": int(pop),
            "favourites": m.get("favourites"),
            "mean_score": m.get("meanScore"),
            # ── 축 재료 ──
            "n_genre": len(m.get("genres") or []),
            "genres": (m.get("genres") or [])[:8],
            "n_tag": len(m.get("tags") or []),
            "n_chapter": m.get("chapters"),
            "n_volume": m.get("volumes"),
            "format": m.get("format"), "status": m.get("status"),
            "country": m.get("countryOfOrigin"),
            "is_adult": bool(m.get("isAdult")),
            "authors": auth, "n_author": len(auth)}


def run(want: int = 2000) -> dict:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lock = OUT.with_suffix(".lock")
    if lock.exists() and time.time() - lock.stat().st_mtime < 3600:
        print("이미 수집 중(잠금)")
        return json.loads(OUT.read_text()) if OUT.exists() else {}
    lock.write_text(str(time.time()))
    try:
        prev = json.loads(OUT.read_text()) if OUT.exists() else {}
        page = 1
        while len(prev) < want and page <= 200:
            d = _post(page)
            pg = (((d or {}).get("data") or {}).get("Page") or {})
            rows = pg.get("media") or []
            if not rows:
                break
            for m in rows:
                r = build(m)
                if r:
                    prev.setdefault(r["record_id"], r)
            if page % 5 == 0:
                OUT.write_text(json.dumps(prev, ensure_ascii=False, indent=1))
                print(f"  {len(prev)}건 (page {page})", flush=True)
            if not (pg.get("pageInfo") or {}).get("hasNextPage"):
                break
            page += 1
        OUT.write_text(json.dumps(prev, ensure_ascii=False, indent=1))
        print(f"저장 {len(prev)}건 → {OUT}")
        return prev
    finally:
        lock.unlink(missing_ok=True)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--want", type=int, default=2000)
    a = p.parse_args()
    recs = run(a.want)
    if recs:
        ys = sorted(r["y_popularity"] for r in recs.values())
        print(f"라벨 서재 등록 수 --- 중앙 {ys[len(ys) // 2]} · 최대 {ys[-1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
