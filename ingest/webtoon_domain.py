"""여섯 번째 도메인 --- 웹툰 연재. 네이버 웹툰 공개 API에서 축과 라벨을 모은다.

노트 45가 두 지렛대 중 배선을 소진했다(후보 50개 중 문턱 통과 0개). 남은 것은
새로 재는 것뿐이고, 그중 가장 싼 길이 도메인 추가다 --- 셀이 20개에서 30개로
늘어 평균 순위 상관의 구간이 좁아지고, 새 배선 후보가 함께 들어온다.

**웹툰을 고른 이유가 셋이다.**

  · 라벨이 **관심 등록 수**다. 팝업 일평균 방문자, 펀딩 후원자와 같은 물리량
    --- 몇 명이 반응했나. 노트 40에서 확인한 대로 이 일치가 전이를 돕는다.
  · 축 대응물이 물리적으로 새롭다. 특히 **연령 등급**이 타깃 폭의 가장 직접적인
    측정이다 --- 전체 이용가와 성인물은 닿을 수 있는 사람 수가 애초에 다르다.
    앞선 다섯 도메인에서 타깃 폭은 언어 수·판형·리워드 제한 같은 간접 대리였다.
  · 팝업 IP의 원천 중 하나다. 제품 쪽에서 직접 쓸모가 있다.

엔드포인트 셋이 열려 있다.

    /api/webtoon/titlelist/weekday?week=mon    요일별 연재작
    /api/webtoon/titlelist/finished?page=N     완결작
    /api/article/list/info?titleId=            상세(관심 수·연령·태그·요일)
    /api/article/list?titleId=&sort=ASC        1화 날짜(연재 시작일)

**시간 누적 주의.** 관심 수는 연재 시작부터 쌓이므로 게임 리뷰·도서 판매지수와
같은 구조다(노트 13). 연재 시작일 기준 log 경과일로 탈추세한다.

**누출 주의.** 회차 수(`totalCount`)는 연재 기간에 비례해 사후에 늘어난다 ---
노트 21의 DLC 수와 같은 구조다. 그대로 굿즈 규모에 쓰지 않고, 경과 주로 나눈
**연재 밀도**로 쓴다. 밀도는 창작자가 시작 시점에 정하는 값에 가깝다.

사용:
  python3 -m ingest.webtoon_domain --want 500
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

OUT = Path("data/state/webtoon_records.json")
CACHE = Path("data/state/cache_webtoon")
API = "https://comic.naver.com/api"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
      "Accept": "application/json", "Referer": "https://comic.naver.com/"}
DELAY = 0.55
WEEK = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


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
                                        timeout=20) as r:
                d = json.loads(r.read().decode("utf-8", "ignore"))
            time.sleep(DELAY)
            f.write_text(json.dumps(d, ensure_ascii=False))
            return d
        except (urllib.error.HTTPError, urllib.error.URLError, OSError,
                TimeoutError, json.JSONDecodeError) as e:
            if isinstance(e, urllib.error.HTTPError) and e.code in (404, 500):
                return None
            time.sleep(DELAY * (4 ** attempt))
    return None


def title_ids(want: int) -> list[int]:
    """연재작과 완결작을 **반씩** 모은다.

    처음에는 요일별 연재작을 먼저 다 모으고 남으면 완결작을 채우게 했다.
    그러면 요일 목록만으로 상한에 닿아 **완결작이 한 건도 안 들어온다** ---
    실제로 379건이 전부 연재작이었고 2024년 이후가 303건이었다. 관심 수는
    연재 시작부터 쌓이므로 연재작만 있으면 경과시간 편향이 그대로 남는다
    (노트 46의 한계 항목).

    둘을 섞어야 축의 변별력이 산다(노트 11). 절반씩 잡고 부족한 쪽을 다른
    쪽으로 채운다."""
    half = int(want * 0.55)
    on, fin, seen = [], [], set()
    for w in WEEK:
        d = _get(f"{API}/webtoon/titlelist/weekday?week={w}&order=user", f"wk_{w}")
        for t in ((d or {}).get("titleList") or []):
            if t["titleId"] not in seen:
                seen.add(t["titleId"]); on.append(t["titleId"])
    for p in range(1, 60):
        d = _get(f"{API}/webtoon/titlelist/finished?page={p}&order=UPDATE", f"fin_{p}")
        tl = (d or {}).get("titleList") or []
        if not tl:
            break
        for t in tl:
            if t["titleId"] not in seen:
                seen.add(t["titleId"]); fin.append(t["titleId"])
        if len(fin) >= half:
            break
    a, b = on[:half], fin[:half]
    a += on[len(a):len(a) + max(0, half - len(b))]
    b += fin[len(b):len(b) + max(0, half - len(a))]
    return a + b


AGE_ORDER = {"ALL": 0, "RATE_12": 1, "RATE_15": 2, "RATE_18": 3}


def build(tid: int) -> dict | None:
    info = _get(f"{API}/article/list/info?titleId={tid}", f"info_{tid}")
    if not info or not info.get("favoriteCount"):
        return None
    first = _get(f"{API}/article/list?titleId={tid}&page=1&sort=ASC", f"asc_{tid}")
    lst = ((first or {}).get("articleList") or [])
    if not lst:
        return None
    sd = lst[0].get("serviceDateDescription") or ""      # 'YY.MM.DD'
    try:
        yy, mm, dd = [int(x) for x in sd.split(".")]
        start = f"{2000 + yy:04d}-{mm:02d}-{dd:02d}"
    except (ValueError, TypeError):
        return None
    total = ((first or {}).get("pageInfo") or {}).get("totalRows") or 0
    age = (info.get("age") or {}).get("type")
    tags = [t.get("tagName") for t in (info.get("curationTagList") or []) if t.get("tagName")]
    days = info.get("publishDayOfWeekList") or []
    artists = [a.get("name") for a in (info.get("communityArtists") or []) if a.get("name")]
    return {"record_id": f"WT-{tid}", "title_id": tid,
            "title": info.get("titleName"),
            "start_date": start,
            "finished": bool(info.get("finished")),
            # ── 라벨 ── 관심 등록 수. 팝업 방문자·펀딩 후원자와 같은 물리량이다.
            "y_favorite": int(info["favoriteCount"]),
            "star": info.get("starScore"),
            # ── 축 재료 ──
            "age_type": age, "age_rank": AGE_ORDER.get(age),
            "n_tag": len(tags), "tags": tags[:10],
            "n_day": len(days), "days": days,
            "n_episode": int(total),
            "artists": artists, "n_artist": len(artists),
            "daily_pass": bool(info.get("dailyPass")),
            "level": info.get("webtoonLevelCode")}


def rebuild() -> dict:
    """캐시에서 레코드를 다시 만든다 --- 재요청 없이.

    수집기를 두 개 동시에 돌렸다가 레코드 파일이 490건에서 392건으로 줄었다.
    둘 다 시작 시점의 `prev` 를 읽고 전체를 덮어쓰므로 나중에 쓰는 쪽이 앞의
    성과를 지운다. **캐시는 요청 단위라 온전하다** --- 거기서 복원하면 된다.

    교훈은 캐시와 산출물을 분리해 둔 것이 옳았다는 것이다. 산출물이 망가져도
    네트워크를 다시 때리지 않는다."""
    prev = json.loads(OUT.read_text()) if OUT.exists() else {}
    n0 = len(prev)
    for f in sorted(CACHE.glob("info_*.json")):
        tid = int(f.stem.split("_")[1])
        rid = f"WT-{tid}"
        if rid in prev:
            continue
        if not (CACHE / f"asc_{tid}.json").exists():
            continue
        r = build(tid)
        if r:
            prev[rid] = r
    OUT.write_text(json.dumps(prev, ensure_ascii=False, indent=1))
    print(f"캐시에서 복원: {n0} → {len(prev)}건")
    return prev


def run(want: int = 500) -> dict:
    # **수집기를 두 개 동시에 돌리면 서로를 지운다**(노트 48). 둘 다 시작 시점의
    # 레코드 파일을 읽고 전체를 덮어쓰므로 나중에 쓰는 쪽이 앞의 성과를 지운다.
    # 실제로 490건이 392건이 됐고 캐시에서 복원해야 했다. 잠금으로 막는다.
    lock = OUT.with_suffix(".lock")
    if lock.exists():
        age = time.time() - lock.stat().st_mtime
        if age < 3600:
            raise SystemExit(f"이미 수집기가 돌고 있다 ({age:.0f}초 전 시작). "
                             f"강제로 지우려면 {lock} 삭제.")
        lock.unlink()
    lock.write_text(str(time.time()))
    try:
        return _run(want)
    finally:
        lock.unlink(missing_ok=True)


def _run(want: int = 500) -> dict:
    prev = json.loads(OUT.read_text()) if OUT.exists() else {}
    ids = title_ids(want)
    print(f"웹툰 수집 --- 후보 {len(ids)}건 (기수집 {len(prev)})")
    for i, tid in enumerate(ids, 1):
        rid = f"WT-{tid}"
        if rid in prev:
            continue
        r = build(tid)
        if r:
            prev[rid] = r
        if i % 40 == 0:
            OUT.write_text(json.dumps(prev, ensure_ascii=False, indent=1))
            print(f"  {i}/{len(ids)} 처리 · 채택 {len(prev)}")
        if len(prev) >= want:
            break
    OUT.write_text(json.dumps(prev, ensure_ascii=False, indent=1))

    import collections

    import numpy as np
    y = np.log10(np.maximum([v["y_favorite"] for v in prev.values()], 1))
    yr = collections.Counter(v["start_date"][:4] for v in prev.values())
    print(f"\n총 {len(prev)}건")
    print("연재 시작 연도:", dict(sorted(yr.items())))
    print("연령 등급:", dict(collections.Counter(v["age_type"] for v in prev.values())))
    print("완결:", sum(1 for v in prev.values() if v["finished"]), "/", len(prev))
    print(f"라벨 log10(관심 수)  평균 {y.mean():.2f}  SD {y.std():.2f}  "
          f"범위 {y.min():.2f}~{y.max():.2f}")
    for k in ("age_rank", "n_tag", "n_day", "n_episode", "n_artist"):
        c = sum(1 for v in prev.values() if v.get(k) is not None)
        print(f"  {k:<12}{c:>4}/{len(prev)} ({c/max(1,len(prev)):.0%})")
    return prev


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--want", type=int, default=500)
    ap.add_argument("--rebuild", action="store_true")
    a = ap.parse_args()
    if a.rebuild:
        rebuild()
    else:
        run(a.want)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
