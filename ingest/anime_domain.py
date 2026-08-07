"""일곱 번째 도메인 --- 애니메이션 스트리밍. 라프텔 공개 API에서 축과 라벨을 모은다.

노트 68이 남은 길을 하나로 좁혔다. 웹툰을 900건에서 2,817건으로 세 배 키워
전체 표본을 두 배(2,069→4,098)로 만들었는데 붓스트랩 구간 반폭이 0.0563에서
0.0556으로 1퍼센트밖에 안 줄었다. 유효 표본이 셀 수가 아니라 **도메인 수**에
지배되기 때문이다. 여섯 도메인이면 셀이 30개, 일곱이면 42개다.

**애니메이션을 고른 이유가 넷이다.**

  · 라벨이 **한줄평 수**다. 게임 리뷰 총계·도서 판매지수와 같은 누적 물리량이라
    탈추세 처리를 그대로 쓴다.
  · 축 대응물이 다섯 슬롯에 전부 있다. 특히 **제작사 사전 작품 수**가 아이돌
    소속사·도서 출판사·웹툰 작가 이력과 같은 자리이고, **시리즈 사전 작품 수**가
    '몇 번째 시즌인가'라 굿즈 규모의 새 대응물이 된다.
  · 팝업 IP의 가장 큰 원천 중 하나다. 제품 쪽에서 직접 쓸모가 있다.
  · 웹툰과 표면이 비슷해 보이지만 물리적으로 다르다 --- 영상이고, 대부분 일본
    제작이고, 플랫폼이 유통만 한다. 전이가 표면 유사성 때문인지 구조 때문인지
    가르는 데 쓸 수 있다.

엔드포인트 셋이 열려 있다(키 불필요).

    /api/search/v1/discover/?sort=recent&size=100&offset=N   목록 (9,456건)
    /api/items/v2/{id}/                                      상세(한줄평 수·태그·제작사)
    /api/episodes/v2/list/?item_id={id}&sort=oldest&size=1    1화 공개일

**시간 기준 주의.** `air_year_quarter`는 원작 방영 시기가 아니라 라프텔 서비스
시기다(은혼 1기가 2006년작인데 2021년으로 나온다). 라벨이 라프텔 한줄평이므로
**1화가 라프텔에 올라온 날**이 맞는 기준이고, 그래서 요청을 하나 더 쓴다.
게임·도서·웹툰과 같은 log 경과일 탈추세다(노트 13).

**누출 주의.** 화수(`count`)와 시즌 수는 인기가 있어야 늘어나므로 노트 21의
DLC 수와 같은 구조다. 그대로 안 쓰고 **자기보다 먼저 나온 같은 시리즈 작품 수**만
센다 --- 공개 시점에 이미 정해져 있는 값이다.

사용:
  python3 -m ingest.anime_domain --want 1200
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

OUT = Path("data/state/anime_records.json")
CACHE = Path("data/state/cache_anime")
API = "https://api.laftel.net/api"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
      "Accept": "application/json", "Referer": "https://laftel.net/"}
DELAY = 0.35


def _get(url: str, key: str) -> dict | None:
    """캐시 우선. 웹툰 수집기와 같은 규약이다."""
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / (key + ".json")
    if f.exists():
        try:
            return json.loads(f.read_text())
        except json.JSONDecodeError:
            f.unlink()
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=25) as r:
                d = json.loads(r.read().decode("utf-8"))
            f.write_text(json.dumps(d, ensure_ascii=False))
            time.sleep(DELAY)
            return d
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError):
            time.sleep(1.2 * (attempt + 1))
    return None


def item_ids(want: int) -> list[int]:
    """목록을 최신순으로 훑어 id를 모은다.

    최신순 하나로만 뽑으면 신작에 쏠린다. **최신순과 인기순을 절반씩** 섞는다 ---
    웹툰에서 요일별 목록만 쓰다가 완결작이 0건이 된 것과 같은 실수를 미리 막는다.
    """
    ids, seen = [], set()
    for sort in ("recent", "rank"):
        off, cap = 0, (want + 1) // 2
        got = 0
        while got < cap and off < 9600:
            d = _get(f"{API}/search/v1/discover/?sort={sort}&size=100&offset={off}",
                     f"list_{sort}_{off}")
            rows = (d or {}).get("results") or []
            if not rows:
                break
            for r in rows:
                try:
                    i = int(r["id"])
                except (KeyError, ValueError, TypeError):
                    continue
                if i not in seen:
                    seen.add(i)
                    ids.append(i)
                    got += 1
            off += 100
    return ids


def _first_air(q: str | None) -> str | None:
    """'2021년 2분기|2021년 3분기' → '2021-04-01'. 참고용이며 탈추세엔 안 쓴다."""
    head = (q or "").split("|")[0].strip()
    try:
        y = int(head.split("년")[0])
        qq = int(head.split("년")[1].strip().split("분기")[0])
    except (IndexError, ValueError):
        return None
    return f"{y:04d}-{(qq - 1) * 3 + 1:02d}-01"


def build(iid: int) -> dict | None:
    d = _get(f"{API}/items/v2/{iid}/", f"item_{iid}")
    if not d or d.get("cnt_short_review") in (None, 0):
        return None
    ep = _get(f"{API}/episodes/v2/list/?item_id={iid}&sort=oldest&size=1", f"ep_{iid}")
    rows = (ep or {}).get("results") or []
    if not rows:
        return None
    pub = (rows[0].get("published_datetime") or "")[:10]
    if len(pub) != 10 or not pub[:4].isdigit():
        return None

    # 대여가 --- 입장 허들의 재료. 무료면 0원이며 **관측된 0**이다(결측 아님).
    prods = rows[0].get("episode_products") or []
    price = min([p.get("list_price") or 0 for p in prods], default=0)
    rating = (d.get("rating") or {})

    return {"record_id": f"AN-{iid}", "item_id": iid,
            "title": d.get("name"),
            # ── 시간 기준 ── 1화가 라프텔에 올라온 날. air_year_quarter가 아니다.
            "start_date": pub,
            "air_quarter": _first_air(d.get("air_year_quarter")),
            # ── 라벨 ── 한줄평 수. 게임 리뷰·도서 판매지수와 같은 누적 물리량이다.
            "y_review": int(d["cnt_short_review"]),
            "avg_rating": d.get("avg_rating"),
            # ── 축 재료 ──
            "tags": (d.get("tags") or [])[:20], "n_tag": len(d.get("tags") or []),
            "genres": d.get("genres") or [], "n_genre": len(d.get("genres") or []),
            "production": (d.get("production") or "").strip() or None,
            "series_id": d.get("series_id"),
            "medium": d.get("medium"),
            "age": rating.get("rating"),
            "is_adult": bool(d.get("is_adult")),
            "price": int(price),
            "is_free": bool(rows[0].get("is_free")) or price == 0,
            "is_dubbed": bool(d.get("is_dubbed")),
            "is_only": bool(d.get("is_laftel_only")),
            "is_original": bool(d.get("is_laftel_original")),
            "is_ending": bool(d.get("is_ending")),
            "n_episode": int((ep or {}).get("count") or 0)}


def rebuild() -> dict:
    """캐시에서 레코드를 다시 만든다 --- 재요청 없이.

    웹툰에서 수집기 둘이 동시에 돌아 서로 덮어썼을 때 이 함수가 복구했다."""
    prev = json.loads(OUT.read_text()) if OUT.exists() else {}
    for f in sorted(CACHE.glob("item_*.json")):
        iid = int(f.stem.split("_")[1])
        if f"AN-{iid}" in prev or not (CACHE / f"ep_{iid}.json").exists():
            continue
        r = build(iid)
        if r:
            prev[r["record_id"]] = r
    OUT.write_text(json.dumps(prev, ensure_ascii=False, indent=1))
    return prev


def run(want: int = 1200) -> dict:
    """수집기 둘이 동시에 돌면 서로 덮어쓴다. 잠금 파일로 막는다."""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lock = OUT.with_suffix(".lock")
    if lock.exists() and time.time() - lock.stat().st_mtime < 3600:
        print("이미 수집 중(잠금)")
        return json.loads(OUT.read_text()) if OUT.exists() else {}
    lock.write_text(str(time.time()))
    try:
        return _run(want)
    finally:
        lock.unlink(missing_ok=True)


def _run(want: int = 1200) -> dict:
    prev = json.loads(OUT.read_text()) if OUT.exists() else {}
    ids = item_ids(want * 2)
    print(f"목록 {len(ids)}건 · 기존 {len(prev)}건")
    n = 0
    for iid in ids:
        if len(prev) >= want:
            break
        if f"AN-{iid}" in prev:
            continue
        r = build(iid)
        if r:
            prev[r["record_id"]] = r
            n += 1
            if n % 50 == 0:
                OUT.write_text(json.dumps(prev, ensure_ascii=False, indent=1))
                print(f"  {len(prev)}건")
    OUT.write_text(json.dumps(prev, ensure_ascii=False, indent=1))
    print(f"저장 {len(prev)}건 → {OUT}")
    return prev


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--want", type=int, default=1200)
    p.add_argument("--rebuild", action="store_true")
    a = p.parse_args()
    recs = rebuild() if a.rebuild else run(a.want)
    if recs:
        ys = sorted(r["y_review"] for r in recs.values())
        print(f"라벨 한줄평 수 --- 중앙 {ys[len(ys) // 2]} · 최대 {ys[-1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
