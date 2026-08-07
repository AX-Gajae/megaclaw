"""세 번째 도메인 --- 게임 출시. Steam 공개 API에서 다섯 축과 라벨을 수집한다.

노트 12가 병목을 지목했다. 두 도메인 세 축으로는 셀이 24개뿐이라 어떤 가설도
확정할 검정력이 없다. 도메인을 늘리는 것이 축을 늘리는 것보다 셀을 빨리 늘린다.

게임 출시는 IP가 대중과 만나는 접점이고, 다섯 축이 전부 관측 가능하다.

    타깃 폭      지원 언어 수, 장르 수 --- 얼마나 많은 사람에게 닿을 수 있게 만들었나
    매장 노출도  관측 불가 (스토어 내 노출 데이터가 공개되지 않는다) → 마스크 0
    입장 허들    출시 가격. 무료 배포는 0원
    미디어 투입  퍼블리셔의 사전 실적 --- 시간 인과적으로 계산
    굿즈 규모    DLC 수 --- '닿으면 무엇을 얻는가'. 앨범 버전 수와 같은 자리다

**라벨은 리뷰 총계다.** 실제 플레이어 수는 공개되지 않으며, 리뷰 수는 플레이어 수의
잘 알려진 대리변수다. 다만 이것은 팝업의 '입장 계수'나 아이돌의 '초동'과 다른
물리량이므로 계수 기준을 명시해 기록한다 --- 노트 1이 규명한 병을 새 도메인에서
반복하지 않기 위해서다.

**시간 혼동이 구조적으로 있다.** 리뷰는 출시 후 계속 쌓이므로 오래된 게임일수록
리뷰가 많다. 아이돌 도메인과 반대 방향의 추세다. 노트 11에서 쓴 탈추세를 여기서도
반드시 적용해야 한다. 출시일을 반드시 기록한다.

사용:
  python3 -m ingest.game_domain --want 600
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

OUT = Path("data/state/game_records.json")
CACHE = Path("data/state/cache_steam")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
      "Accept-Language": "ko-KR,ko;q=0.9"}
DELAY = 1.5
RETRY = 3


def _get(url: str, key: str, as_json: bool = True):
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / (re.sub(r"[^0-9A-Za-z_.-]", "_", key)[:100] + (".json" if as_json else ".html"))
    if f.exists():
        t = f.read_text(encoding="utf-8", errors="ignore")
        try:
            return json.loads(t) if as_json else t
        except json.JSONDecodeError:
            pass
    for attempt in range(RETRY):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                t = raw.decode("utf-8", "ignore")
            time.sleep(DELAY)
            f.write_text(t, encoding="utf-8")
            return json.loads(t) if as_json else t
        except (urllib.error.HTTPError, urllib.error.URLError, OSError,
                TimeoutError, json.JSONDecodeError) as e:
            w = DELAY * (4 ** attempt)
            print(f"    [재시도 {attempt+1}/{RETRY}] {key}: {type(e).__name__} — {w:.0f}초")
            time.sleep(w)
    return None


def top_appids(want: int = 600) -> list[str]:
    """판매 상위작을 넓게 모은다. 출시 연도로는 **사후에** 나눈다.

    처음에는 검색에 `released_date_range` 를 붙여 연도별로 뽑으려 했는데,
    `filter=topsellers` 와 함께 쓰면 날짜 범위가 무시된다 --- 2024년으로 걸었더니
    2017년 PUBG와 2026년 팰월드가 같이 나왔다. 그래서 상위작을 통째로 받아
    실제 출시일로 분류한다. 셔블웨어를 피하면서 연도 분포도 얻는 방법이다
    (2024년 한 해에만 116,830개가 출시됐고 대부분은 반응 자체가 없다)."""
    ids, seen = [], set()
    for start in range(0, want * 2, 50):
        u = ("https://store.steampowered.com/search/results/?query&count=50"
             f"&start={start}&filter=topsellers&category1=998&infinite=1&json=1"
             "&cc=kr&l=korean")
        d = _get(u, f"top_{start}")
        if not d:
            break
        got = re.findall(r'data-ds-appid="(\d+)"', d.get("results_html", ""))
        got = [g for g in got if "," not in g and g not in seen]
        if not got:
            break
        seen.update(got)
        ids += got
        if len(ids) >= want:
            break
    return ids[:want]


def detail(appid: str) -> dict | None:
    d = _get(f"https://store.steampowered.com/api/appdetails?appids={appid}&cc=kr&l=korean",
             f"app_{appid}")
    if not d:
        return None
    x = d.get(str(appid)) or {}
    return x.get("data") if x.get("success") else None


def reviews(appid: str) -> dict | None:
    d = _get(f"https://store.steampowered.com/appreviews/{appid}"
             "?json=1&num_per_page=0&language=all&purchase_type=all", f"rev_{appid}")
    return (d or {}).get("query_summary")


DATE = re.compile(r"(\d{4})\s*년?\s*(\d{1,2})\s*월?\s*(\d{1,2})?")


def parse_date(s: str | None) -> str | None:
    if not s:
        return None
    m = DATE.search(s)
    if not m:
        return None
    y, mo, dd = m.group(1), m.group(2) or "1", m.group(3) or "1"
    return f"{int(y):04d}-{int(mo):02d}-{int(dd):02d}"


def build(a: dict, q: dict, appid: str) -> dict | None:
    n_rev = (q or {}).get("total_reviews")
    if not n_rev or n_rev < 50:            # 반응이 거의 없는 것은 라벨이 못 된다
        return None
    rd = parse_date(((a.get("release_date") or {}).get("date")))
    if not rd or (a.get("release_date") or {}).get("coming_soon"):
        return None
    po = a.get("price_overview") or {}
    price = 0 if a.get("is_free") else (po.get("initial") or 0) / 100.0
    langs = a.get("supported_languages") or ""
    n_lang = len([x for x in re.split(r"[,、]", re.sub(r"<[^>]+>", "", langs)) if x.strip()])
    return {"record_id": f"GAME-{appid}", "appid": appid, "name": a.get("name"),
            "release_date": rd,
            "publishers": a.get("publishers") or [], "developers": a.get("developers") or [],
            "genres": [g["description"] for g in (a.get("genres") or [])],
            "n_dlc": len(a.get("dlc") or []),
            "n_lang": n_lang,
            "price_krw": price, "is_free": bool(a.get("is_free")),
            "n_platform": sum(bool(v) for v in (a.get("platforms") or {}).values()),
            "n_category": len(a.get("categories") or []),
            "y_raw": int(n_rev), "y_positive": int(q.get("total_positive") or 0),
            "label_basis": "steam_total_reviews",
            "label_note": ("리뷰 총계. 실제 플레이어 수가 아니라 그 대리변수이며, "
                           "출시 후 계속 누적되므로 출시일 통제가 필수다."),
            "source": f"https://store.steampowered.com/app/{appid}"}


def run(want: int = 600) -> dict:
    prev = json.loads(OUT.read_text()) if OUT.exists() else {}
    ids = top_appids(want)
    print(f"게임 도메인 수집 --- 후보 {len(ids)}건 (기수집 {len(prev)})")
    for i, appid in enumerate(ids, 1):
        rid = f"GAME-{appid}"
        if rid in prev:
            continue
        a = detail(appid)
        if not a or a.get("type") != "game":
            continue
        rec = build(a, reviews(appid), appid)
        if rec:
            prev[rid] = rec
        if i % 25 == 0:
            OUT.write_text(json.dumps(prev, ensure_ascii=False, indent=1))
            print(f"  {i}/{len(ids)} 처리 · 채택 {len(prev)}")
    OUT.write_text(json.dumps(prev, ensure_ascii=False, indent=1))
    import collections
    yr = collections.Counter(v["release_date"][:4] for v in prev.values())
    print(f"\n총 {len(prev)}건  연도 분포: {dict(sorted(yr.items()))}")
    print(f"저장: {OUT}")
    return prev


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--want", type=int, default=600)
    a = ap.parse_args()
    run(a.want)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# ── 출시 창 라벨 ────────────────────────────────────────────────────────
def window_reviews(appid: str, release: str, days: int = 30) -> dict | None:
    """출시 후 N일 안에 달린 리뷰 수.

    노트 13이 남긴 반증 조건. 리뷰 총계는 출시 이후 수년의 누적 동역학
    (업데이트·세일·스트리머 노출)을 반영하므로 출시 시점 축이 담을 수 없다.
    출시 창으로 자르면 그 부분이 빠지고, 축의 설명력이 올라가야 한다.
    오르지 않으면 문제는 라벨이 아니라 축 매핑이다.

    Steam appreviews 는 date_range_type=include 와 start_date/end_date 를 받는다."""
    from datetime import datetime, timezone
    try:
        rel = datetime(*map(int, release.split("-")), tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None
    s = int(rel.timestamp())
    e = s + days * 86400
    # 창이 아직 안 닫힌 최신 출시작은 라벨이 절단된다 --- 표시해서 제외할 수 있게 한다
    truncated = e > int(datetime.now(timezone.utc).timestamp())
    d = _get(f"https://store.steampowered.com/appreviews/{appid}"
             f"?json=1&num_per_page=0&language=all&purchase_type=all&filter=all"
             f"&date_range_type=include&start_date={s}&end_date={e}",
             f"win{days}_{appid}")
    q = (d or {}).get("query_summary")
    if not q:
        return None
    return {"n": int(q.get("total_reviews") or 0),
            "positive": int(q.get("total_positive") or 0),
            "days": days, "truncated": truncated}


def collect_window(days: int = 30) -> dict:
    recs = json.loads(OUT.read_text())
    todo = [r for r in recs.values() if f"y_w{days}" not in r]
    print(f"출시 {days}일 창 라벨 수집 --- 대상 {len(todo)}/{len(recs)}건")
    for i, r in enumerate(todo, 1):
        w = window_reviews(r["appid"], r["release_date"], days)
        if w:
            r[f"y_w{days}"] = w["n"]
            r[f"y_w{days}_truncated"] = w["truncated"]
        if i % 40 == 0:
            OUT.write_text(json.dumps(recs, ensure_ascii=False, indent=1))
            print(f"  {i}/{len(todo)}")
    OUT.write_text(json.dumps(recs, ensure_ascii=False, indent=1))
    ok = [r for r in recs.values() if r.get(f"y_w{days}") and not r.get(f"y_w{days}_truncated")]
    import numpy as np
    if ok:
        a = np.array([r[f"y_w{days}"] for r in ok], float)
        b = np.array([r["y_raw"] for r in ok], float)
        print(f"\n완전 창 {len(ok)}건  창/전체 비율 중앙 {np.median(a/b):.3f}")
        print(f"  log10 창 라벨  평균 {np.log10(np.maximum(a,1)).mean():.2f}  "
              f"SD {np.log10(np.maximum(a,1)).std():.2f}")
    return recs
