"""여덟 번째 도메인 --- 모바일 게임. 앱스토어 공개 API에서 축과 라벨을 모은다.

노트 73이 여덟째 도메인의 값을 정확히 계산했다.

    셀 42 → 56          판정치 구간이 좁아진다(노트 69의 확증)
    게이트 유효 표본 6 → 7  도메인 수준 특징이 상수인 것이 병목이었다
    합의 투표자 6 → 7     뒤집힌 출처를 찾는 표가 하나 는다

**모바일 게임을 고른 이유가 셋이다.**

  · 라벨이 **평가 참여자 수**다. 게임(스팀) 리뷰 총계와 같은 물리량이라
    탈추세 처리를 그대로 쓴다.
  · 축 대응물이 스팀 게임과 **거의 일대일**이다 --- 언어 수 · 퍼블리셔 이력 ·
    가격 · 설치 용량. 노트 40의 법칙(자기 상관이 높으면 대상으로 좋다)이
    가까운 도메인 쌍에서 어떻게 나오는지 처음 본다.
  · 모바일 게임 IP는 팝업의 실제 원천이다(쿠키런 · 원신 · 붕괴 등).

**표본은 차트다.** 스팀 도메인이 topsellers 를 썼으므로 같은 방식으로 앱스토어
인기 차트를 쓴다 --- 게임 대분류와 하위 장르 열아홉, 무료/유료/매출 세 차트,
각 100위. 재현 가능하고 정의가 분명하다. 대신 **차트 밖은 안 본다** --- 스팀
도메인과 같은 한계다.

    /kr/rss/top{free,paid,grossing}applications/limit=100/genre=G/json
    /lookup?id=ID&country=kr

**누출 주의.** `fileSizeBytes`는 현재 용량이라 업데이트로 늘어난다. 스팀의 설치
용량도 같은 성질이고 검정을 통과해 쓰고 있으므로 같은 자리에 둔다 --- 다만
노트 21의 DLC 수만큼 강한 누적은 아니다. 개발사 이력은 **자기보다 먼저 나온
것만** 센다.

사용:
  python3 -m ingest.mobile_domain --want 1200
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

OUT = Path("data/state/mobile_records.json")
CACHE = Path("data/state/cache_mobile")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
      "Accept": "application/json"}
DELAY = 0.35
# 게임 대분류와 하위 장르. 애플이 쓰는 번호다.
GENRES = [6014] + list(range(7001, 7020))
CHARTS = ("topfreeapplications", "toppaidapplications", "topgrossingapplications")


def _get(url: str, key: str) -> dict | None:
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / (key + ".json")
    if f.exists():
        try:
            return json.loads(f.read_text())
        except json.JSONDecodeError:
            f.unlink()
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                        timeout=25) as r:
                d = json.loads(r.read().decode("utf-8"))
            f.write_text(json.dumps(d, ensure_ascii=False))
            time.sleep(DELAY)
            return d
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError):
            time.sleep(1.2 * (attempt + 1))
    return None


def chart_ids() -> list[str]:
    """차트에서 앱 id를 모은다. 장르 스무 개 × 차트 셋 × 100위."""
    ids, seen = [], set()
    for g in GENRES:
        for c in CHARTS:
            d = _get(f"https://itunes.apple.com/kr/rss/{c}/limit=100/genre={g}/json",
                     f"rss_{c}_{g}")
            for e in ((d or {}).get("feed") or {}).get("entry") or []:
                i = ((e.get("id") or {}).get("attributes") or {}).get("im:id")
                if i and i not in seen:
                    seen.add(i)
                    ids.append(i)
    return ids


def build(aid: str) -> dict | None:
    d = _get(f"https://itunes.apple.com/lookup?id={aid}&country=kr", f"app_{aid}")
    rs = (d or {}).get("results") or []
    if not rs:
        return None
    r = rs[0]
    n = r.get("userRatingCount")
    rel = (r.get("releaseDate") or "")[:10]
    if not n or len(rel) != 10 or not rel[:4].isdigit():
        return None
    shots = len(r.get("screenshotUrls") or []) + len(r.get("ipadScreenshotUrls") or [])
    return {"record_id": f"MB-{aid}", "app_id": str(aid),
            "title": r.get("trackName"),
            "release_date": rel,
            "updated": (r.get("currentVersionReleaseDate") or "")[:10],
            # ── 라벨 ── 평가 참여자 수. 스팀 리뷰 총계와 같은 물리량이다.
            "y_rating_count": int(n),
            "avg_rating": r.get("averageUserRating"),
            # ── 축 재료 ──
            "n_lang": len(r.get("languageCodesISO2A") or []),
            "langs": (r.get("languageCodesISO2A") or [])[:12],
            "price": float(r.get("price") or 0.0),
            "size_mb": round(float(r.get("fileSizeBytes") or 0) / 1e6, 1),
            "n_genre": len(r.get("genres") or []),
            "genres": r.get("genres") or [],
            "n_shot": shots,
            "artist_id": r.get("artistId"),
            "artist": r.get("artistName"),
            "advisory": r.get("contentAdvisoryRating"),
            "n_device": len(r.get("supportedDevices") or [])}


def rebuild() -> dict:
    prev = json.loads(OUT.read_text()) if OUT.exists() else {}
    for f in sorted(CACHE.glob("app_*.json")):
        aid = f.stem.split("_", 1)[1]
        if f"MB-{aid}" in prev:
            continue
        r = build(aid)
        if r:
            prev[r["record_id"]] = r
    OUT.write_text(json.dumps(prev, ensure_ascii=False, indent=1))
    return prev


def run(want: int = 1200) -> dict:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lock = OUT.with_suffix(".lock")
    if lock.exists() and time.time() - lock.stat().st_mtime < 3600:
        print("이미 수집 중(잠금)")
        return json.loads(OUT.read_text()) if OUT.exists() else {}
    lock.write_text(str(time.time()))
    try:
        prev = json.loads(OUT.read_text()) if OUT.exists() else {}
        ids = chart_ids()
        print(f"차트 {len(ids)}건 · 기존 {len(prev)}건")
        n = 0
        for aid in ids:
            if len(prev) >= want:
                break
            if f"MB-{aid}" in prev:
                continue
            r = build(aid)
            if r:
                prev[r["record_id"]] = r
                n += 1
                if n % 50 == 0:
                    OUT.write_text(json.dumps(prev, ensure_ascii=False, indent=1))
                    print(f"  {len(prev)}건", flush=True)
        OUT.write_text(json.dumps(prev, ensure_ascii=False, indent=1))
        print(f"저장 {len(prev)}건 → {OUT}")
        return prev
    finally:
        lock.unlink(missing_ok=True)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--want", type=int, default=1200)
    p.add_argument("--rebuild", action="store_true")
    a = p.parse_args()
    recs = rebuild() if a.rebuild else run(a.want)
    if recs:
        ys = sorted(r["y_rating_count"] for r in recs.values())
        print(f"라벨 평가 수 --- 중앙 {ys[len(ys) // 2]} · 최대 {ys[-1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
