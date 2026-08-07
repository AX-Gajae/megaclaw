"""게임 도메인의 **균일 표본** --- 상위 판매 목록이 아니라 목록 전체에서 뽑는다.

노트 382. `ingest/game_domain.top_appids` 는 스팀 검색을
``filter=topsellers`` 로 걸고 앞에서부터 600건을 받는다. 같은 검색이
보고하는 전체는 **167,368건**이라 우리 표본은 목록의 **위 0.36%** 다.
그 위에 `build()` 가 ``리뷰 총계 50 미만은 라벨이 못 된다''로 한 번 더
자른다 --- **바닥이 둘이고 둘 다 우리 것이다.**

두 선택 모두 근거가 적혀 있다(원본 주석: ``셔블웨어를 피하면서 연도 분포도
얻는 방법이다 --- 2024년 한 해에만 116,830개가 출시됐고 대부분은 반응
자체가 없다''). **그래서 이 파일은 그 선택을 뒤집지 않는다.** 노트 379가
펀딩에서 같은 모양을 재니 도메인 점수가 4배 부풀어 있었으므로, 게임에서도
**크기를 먼저 재자는 것**이다. 셔블웨어를 모집단에 넣을지는 과제를 바꾸는
결정이라 점수로 정하지 않는다(노트 224).

**씨앗을 고정한다** --- 자료 결정은 재현 가능해야 한다(노트 367).
**`n_rev < 50` 을 여기서는 안 자른다.** 두 바닥의 값을 따로 재려면 잘린
것도 받아 둬야 한다. 대신 `y_raw` 와 함께 기록만 한다.

    python3 -m ingest.game_sample --want 2000
"""
from __future__ import annotations

import argparse
import gzip
import json
import random
import re
import time
import urllib.request
from pathlib import Path

OUT = Path("data/state/game_uniform.json")
CK = Path("data/state/game_uniform.jsonl")
SEED = 20260801
TOTAL_URL = ("https://store.steampowered.com/search/results/?query&count=50"
             "&start={start}&category1=998&infinite=1&json=1&cc=kr&l=korean")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"


def _get(url: str, timeout: int = 45):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                       "Accept-Encoding": "gzip"})
            r = urllib.request.urlopen(req, timeout=timeout)
            raw = r.read()
            if r.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            return json.loads(raw)
        except Exception:
            time.sleep(2 + 3 * attempt)
    return None


def total_count() -> int:
    d = _get(TOTAL_URL.format(start=0))
    return int((d or {}).get("total_count") or 0)


def sample_ids(want: int, total: int) -> list[str]:
    """목록 전체에서 씨앗 고정으로 고른 쪽들을 훑는다.

    한 쪽이 50건이라 필요한 쪽 수는 want/50 인데, 상세에서 떨어지는 것이
    있어 1.6배로 잡는다. 쪽은 **겹치지 않게** 뽑는다."""
    rng = random.Random(SEED)
    pages = sorted(rng.sample(range(0, max(1, total - 50), 50),
                              min(int(want / 50 * 1.6) + 1, total // 50)))
    ids, seen = [], set()
    for i, st in enumerate(pages, 1):
        d = _get(TOTAL_URL.format(start=st))
        if not d:
            continue
        got = [g for g in re.findall(r'data-ds-appid="(\d+)"',
                                     d.get("results_html", ""))
               if "," not in g and g not in seen]
        seen.update(got)
        ids += [(g, st) for g in got]
        if i % 10 == 0:
            print(f"  쪽 {i}/{len(pages)} · appid {len(ids)}", flush=True)
        time.sleep(0.6)
    # **섞는다.** 안 섞으면 상세를 오프셋 오름차순으로 받게 되고, 중간에
    # 멈춘 부분 결과가 목록 앞쪽만 담는다 --- 첫 31건이 전부 오프셋 2,900
    # (목록의 위 1.7%)에서 나와 "균일 표본"이 아니었다. 씨앗은 같으므로
    # 재현된다.
    random.Random(SEED + 1).shuffle(ids)
    return ids


def run(want: int = 2000) -> dict:
    from .game_domain import detail, parse_date, reviews

    tot = total_count()
    print(f"목록 전체 {tot:,}건 · 목표 {want}건", flush=True)
    done = {}
    if CK.exists():
        for line in CK.read_text().splitlines():
            try:
                o = json.loads(line)
                done[o["record_id"]] = o
            except Exception:
                pass
    print(f"이어받기 {len(done)}건", flush=True)
    ids = sample_ids(want, tot)
    print(f"appid {len(ids)}개 뽑았다", flush=True)
    ck = CK.open("a")
    n = 0
    for appid, page in ids:
        rid = f"GAME-{appid}"
        if rid in done:
            continue
        if len(done) >= want:
            break
        a = detail(appid)
        time.sleep(0.5)
        if not a or a.get("type") != "game":
            continue
        q = reviews(appid) or {}
        time.sleep(0.4)
        rd = parse_date((a.get("release_date") or {}).get("date"))
        if not rd or (a.get("release_date") or {}).get("coming_soon"):
            continue
        po = a.get("price_overview") or {}
        langs = re.sub(r"<[^>]+>", "", a.get("supported_languages") or "")
        rec = {"record_id": rid, "appid": appid, "name": a.get("name"),
               "_page": page,
               "release_date": rd,
               "publishers": a.get("publishers") or [],
               "developers": a.get("developers") or [],
               "genres": [g["description"] for g in (a.get("genres") or [])],
               "n_dlc": len(a.get("dlc") or []),
               "n_lang": len([x for x in re.split(r"[,、]", langs) if x.strip()]),
               "price_krw": 0 if a.get("is_free") else (po.get("initial") or 0) / 100.0,
               "is_free": bool(a.get("is_free")),
               "n_platform": sum(bool(v) for v in (a.get("platforms") or {}).values()),
               "n_category": len(a.get("categories") or []),
               "y_raw": int(q.get("total_reviews") or 0),
               "y_positive": int(q.get("total_positive") or 0),
               "below_old_cut": bool((q.get("total_reviews") or 0) < 50),
               "label_basis": "steam_total_reviews",
               "source": f"https://store.steampowered.com/app/{appid}"}
        done[rid] = rec
        ck.write(json.dumps(rec, ensure_ascii=False) + "\n")
        ck.flush()
        n += 1
        if n % 10 == 0:
            OUT.write_text(json.dumps(done, ensure_ascii=False))
            below = sum(1 for v in done.values() if v["below_old_cut"])
            print(f"  {len(done)}건 · 옛 문턱(리뷰 50) 아래 {below} "
                  f"({100*below/max(1,len(done)):.0f}%)", flush=True)
    OUT.write_text(json.dumps(done, ensure_ascii=False))
    below = sum(1 for v in done.values() if v["below_old_cut"])
    print(f"끝: {len(done)}건 · 리뷰 50 미만 {below}건 "
          f"({100*below/max(1,len(done)):.0f}%)", flush=True)
    return {"n": len(done), "below_old_cut": below, "total": tot}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--want", type=int, default=2000)
    a = ap.parse_args()
    run(a.want)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
