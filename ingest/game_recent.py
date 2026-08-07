"""게임 도메인의 **2025년 이후 균일 표본** --- 유보 대응물(노트 384).

노트 382가 짚었다: `game_domain.top_appids` 는 스팀 검색을
``filter=topsellers`` 로 걸고 앞 600건을 받는데 같은 검색이 보고하는 전체가
167,368건이다. 노트 379가 펀딩에서 같은 모양을 재니 도메인 점수가 4.8배
부풀어 있었다.

**목록 전체를 균일 추출하는 것(`game_sample`)은 열 시간이 넘게 걸린다.**
노트 379 절차가 필요로 하는 것은 **유보 대응물뿐**이라 --- 새 행은 유보에만
넣고 학습은 고정한다 --- 2025년 이후만 뽑으면 된다.

``sort_by=Released_DESC`` 는 먹는다(``released_date_range`` 는 무시된다 ---
원본 주석이 적은 그 함정이 여기서도 같다). 출시일 내림차순 117,266건에서
**오프셋 0~33,000 이 2025-01-01 이후**다(오프셋 30,000 이 2025-03-11,
40,000 이 2024-08-12 이라 경계가 그 사이). 출시일 정렬이므로 **오프셋이
인기와 상관없다** --- 앞에서부터 받아도 상위 표본이 안 된다.

**라벨은 `y_w30`** (노트 210). `appreviews` 에 ``date_range_type=include``
와 출시일~30일 창을 주면 나온다 --- 저장된 값과 1~2% 안에서 맞는 것을
기존 레코드 넷으로 확인했다. 긁는 날 기준 30일이 안 지난 것은
``y_w30_truncated`` 로 표시하고 쓰지 않는다(노트 210).

**마찰 축도 같은 응답에서 뽑는다** --- `game_friction.parse_min` 이
`pc_requirements` 와 `required_age` 만 보므로 상세 한 번으로 램·용량·연령이
같이 나온다. 이것이 없으면 새 행에서 `goods_scale`·`ram_gb`·`age_rating`
셋이 통째로 마스크 0 이 되어 **표시자가 배치가 된다**(노트 354·379).

**출처 좌표를 남긴다**(노트 383) --- `_offset`.

    python3 -m ingest.game_recent --want 250
"""
from __future__ import annotations

import argparse
import datetime
import json
import random
import re
import time
from pathlib import Path

from .game_domain import detail, parse_date, reviews  # noqa: F401
from .game_friction import parse_min
from .game_sample import _get

OUT = Path("data/state/game_recent.json")
CK = Path("data/state/game_recent.jsonl")
SEED = 20260801
HI = 33000                       # 이 오프셋까지가 2025-01-01 이후
SEARCH = ("https://store.steampowered.com/search/results/?query&count=50"
          "&category1=998&infinite=1&json=1&cc=kr&l=korean"
          "&sort_by=Released_DESC&start={start}")
TODAY = datetime.date(2026, 8, 1)


def w30(appid: str, rd: str) -> tuple[int | None, bool]:
    """출시 후 30일 창 리뷰 수. (값, 잘렸나)"""
    d0 = datetime.date.fromisoformat(rd)
    end = d0 + datetime.timedelta(days=30)
    trunc = end > TODAY
    s = int(datetime.datetime.combine(d0, datetime.time()).timestamp())
    e = int(datetime.datetime.combine(end, datetime.time()).timestamp())
    d = _get(f"https://store.steampowered.com/appreviews/{appid}?json=1"
             f"&num_per_page=0&filter=all&language=all&purchase_type=all"
             f"&date_range_type=include&start_date={s}&end_date={e}")
    q = (d or {}).get("query_summary") or {}
    n = q.get("total_reviews")
    return (int(n) if n is not None else None), trunc


def run(want: int = 250, pages: int = 40) -> dict:
    rng = random.Random(SEED)
    offs = sorted(rng.sample(range(0, HI, 50), pages))
    ids = []
    seen = set()
    for i, st in enumerate(offs, 1):
        d = _get(SEARCH.format(start=st))
        got = [g for g in re.findall(r'data-ds-appid="(\d+)"',
                                     (d or {}).get("results_html", ""))
               if "," not in g and g not in seen]
        seen.update(got)
        ids += [(g, st) for g in got]
        if i % 10 == 0:
            print(f"  쪽 {i}/{pages} · appid {len(ids)}", flush=True)
        time.sleep(0.5)
    rng.shuffle(ids)                       # 노트 383 --- 부분 결과도 고르게
    print(f"appid {len(ids)}개 · 목표 {want}", flush=True)
    done = {}
    if CK.exists():
        for line in CK.read_text().splitlines():
            try:
                o = json.loads(line)
                done[o["record_id"]] = o
            except Exception:
                pass
    ck = CK.open("a")
    for appid, off in ids:
        rid = f"GAME-{appid}"
        if rid in done:
            continue
        if len(done) >= want:
            break
        a = detail(appid)
        time.sleep(0.35)
        if not a or a.get("type") != "game":
            continue
        rd = parse_date((a.get("release_date") or {}).get("date"))
        if not rd or rd < "2025-01-01" or (a.get("release_date") or {}).get("coming_soon"):
            continue
        n30, trunc = w30(appid, rd)
        time.sleep(0.35)
        q = reviews(appid) or {}
        time.sleep(0.3)
        po = a.get("price_overview") or {}
        langs = re.sub(r"<[^>]+>", "", a.get("supported_languages") or "")
        rec = {"record_id": rid, "appid": appid, "name": a.get("name"),
               "_offset": off, "release_date": rd,
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
               "y_w30": n30, "y_w30_truncated": bool(trunc),
               "below_old_cut": bool((q.get("total_reviews") or 0) < 50),
               "_friction": parse_min(a),
               "label_basis": "steam_total_reviews",
               "source": f"https://store.steampowered.com/app/{appid}"}
        done[rid] = rec
        ck.write(json.dumps(rec, ensure_ascii=False) + "\n")
        ck.flush()
        if len(done) % 10 == 0:
            OUT.write_text(json.dumps(done, ensure_ascii=False))
            us = [v for v in done.values() if not v["y_w30_truncated"] and v["y_w30"] is not None]
            below = sum(1 for v in done.values() if v["below_old_cut"])
            print(f"  {len(done)}건 (쓸 수 있는 것 {len(us)}) · "
                  f"옛 문턱 아래 {below} ({100*below/len(done):.0f}%)", flush=True)
    OUT.write_text(json.dumps(done, ensure_ascii=False))
    us = [v for v in done.values() if not v["y_w30_truncated"] and v["y_w30"] is not None]
    print(f"끝: {len(done)}건 · 쓸 수 있는 것 {len(us)}", flush=True)
    return {"n": len(done), "usable": len(us)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--want", type=int, default=250)
    ap.add_argument("--pages", type=int, default=40)
    a = ap.parse_args()
    run(a.want, a.pages)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
