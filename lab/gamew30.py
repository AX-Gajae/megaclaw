# -*- coding: utf-8 -*-
# y_w30 UTC 정본의 유일한 실행 가능 구현 — gameknock864.w30_epoch 동결 사본(티처 #30 P3′ⓐ).
# 규칙(program.json 등재): 게임 수확 러너가 이 모듈을 임포트하지 않으면 UTC 정본 선언은 자동 철회된다.
# tz_utc=True 가 정본 정의: [출시일 00:00 UTC, +30일) appreviews total_reviews.
import datetime as dt
import sys
import time

sys.path.insert(0, "/Users/ax/world_model")
from ingest.game_sample import _get  # noqa: E402 — 무캐시 HTTP


def w30_epoch(appid, rd, tz_utc):
    d0 = dt.date.fromisoformat(rd)
    end = d0 + dt.timedelta(days=30)
    if tz_utc:
        s = int(dt.datetime.combine(d0, dt.time(), tzinfo=dt.timezone.utc).timestamp())
        e = int(dt.datetime.combine(end, dt.time(), tzinfo=dt.timezone.utc).timestamp())
    else:
        s = int(dt.datetime.combine(d0, dt.time()).timestamp())
        e = int(dt.datetime.combine(end, dt.time()).timestamp())
    d = _get(f"https://store.steampowered.com/appreviews/{appid}?json=1"
             f"&num_per_page=0&filter=all&language=all&purchase_type=all"
             f"&date_range_type=include&start_date={s}&end_date={e}")
    time.sleep(1.0)
    q = (d or {}).get("query_summary") or {}
    return q.get("total_reviews")
