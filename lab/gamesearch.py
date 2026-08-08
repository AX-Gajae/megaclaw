# -*- coding: utf-8 -*-
# comingsoon 검색 쪽 파서 — gameknock864.fetch_page 동결 사본(번들 콤마 필터·중복은 호출측).
import re
import sys
import time

sys.path.insert(0, "/Users/ax/world_model")
from ingest.game_sample import _get  # noqa: E402
from lab.gamedate import granularity  # noqa: E402

SEARCH = ("https://store.steampowered.com/search/results/?query&count=50"
          "&category1=998&infinite=1&json=1&cc=kr&l=korean"
          "&filter=comingsoon&start={start}")
WIN_LO, WIN_HI = "2026-09-15", "2026-10-31"
ENG = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}


def fetch_page(start):
    """한 쪽 → [(appid, 제목, 원문, 입도, 표준일)] · 번들(콤마 appid) 제외."""
    d = _get(SEARCH.format(start=start))
    time.sleep(1.2)
    if not d:
        return None, None
    html_blob = d.get("results_html") or ""
    out = []
    for b in re.split(r'data-ds-appid="', html_blob)[1:]:
        mid = re.match(r'([\d,]+)"', b)
        if not mid or "," in mid.group(1):
            continue
        mt = re.search(r'<span class="title">([^<]{1,120})</span>', b)
        mr = re.search(r'search_released[^>]*>\s*([^<]{0,60})<', b)
        if not mt:
            continue
        rel = (mr.group(1) if mr else "").strip()
        g, std = granularity(rel)
        out.append({"appid": mid.group(1), "제목": mt.group(1).strip(),
                    "예정일 원문": rel, "입도": g, "표준일": std})
    return out, d.get("total_count")
