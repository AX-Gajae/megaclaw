"""목록 대조 --- 긁어 놓고 안 읽는 자료가 있나(노트 337).

이 판에는 같은 결정이 **여러 층에 목록으로** 적혀 있다.

    거르는 쪽   ``ingest/idol_axes``       한터 필터           노트 326
    긁는 쪽     ``wiki_views.idol_items``  축 파일을 읽음      노트 332
                ``idol_album_meta.run``    같은 필터 복사      노트 333
    읽는 쪽     ``lab/trendaxes.FILE``     만화 · 세계애니 없음  노트 336
                ``lab/wikiaxes.AXF``       네 도메인 없음      노트 337

**다섯 자리가 같은 모양이다** --- 한쪽만 고쳐졌고 다른 쪽은 그대로다.
그리고 매번 조용했다: 덮음 0% 는 ``자료가 없다''로 읽혔지 ``목록이
다르다''로 안 읽혔다. 노트 337에서 세어 보니 위키 캐시 894건이 안 읽히고
있었고 그중 아이돌 78건이 짝지은 차 +0.0737(11/12) 짜리였다.

**수집은 비싸고 목록 대조는 공짜다.** 이 파일이 그 대조다.

**이름표지 거부권이 아니다**(``hearing`` · ``overlap`` · ``marker`` ·
``ordering`` · ``poolshadow`` 와 같은 규약). 목록이 갈라진 것이 늘 잘못은
아니다 --- 일부러 뺀 자리도 있다(팝업은 ``popupset`` 이 따로 만든다).
매 실행에 **어디가 갈라져 있는지**를 적어 둘 뿐이다.
"""
from __future__ import annotations

import json
from pathlib import Path


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def trend() -> dict:
    """검색 --- 쓰는 쪽(``trend_all.SPEC``) 대 읽는 쪽(``trendaxes.FILE``)."""
    KO = {"book": "도서", "funding": "펀딩", "game": "게임", "mobile": "모바일",
          "anime": "애니", "webtoon": "웹툰", "manga": "만화",
          "wanime": "세계애니", "popup": "팝업", "idol": "아이돌"}
    w = _safe(lambda: {KO[k] for k in __import__(
        "ingest.trend_all", fromlist=["SPEC"]).SPEC}, set())
    r = set(_safe(lambda: __import__(
        "lab.trendaxes", fromlist=["FILE"]).FILE, {}))
    have = {KO.get(p.stem.replace("_trend", ""), p.stem.replace("_trend", ""))
            for p in Path("data/state/naver").glob("*_trend.json")}
    return {"쓰는 쪽": sorted(w), "읽는 쪽": sorted(r), "파일 있음": sorted(have),
            "긁는데 안 읽음": sorted(w - r),
            "**파일 있는데 안 읽음**": sorted(have - r)}


def wiki() -> dict:
    """위키 --- 쓰는 쪽(``wiki_views.SRC``) 대 읽는 쪽(``wikiaxes.AXF``)."""
    w = set(_safe(lambda: __import__(
        "ingest.wiki_views", fromlist=["SRC"]).SRC, {}))
    r = set(_safe(lambda: __import__(
        "lab.wikiaxes", fromlist=["AXF"]).AXF, {}))
    r |= {"팝업"}                      # 팝업은 popupset 이 따로 붙인다
    pre = {"AN": "애니", "WA": "세계애니", "MB": "모바일", "GAME": "게임",
           "WT": "웹툰", "MG": "만화", "BOOK": "도서", "IDOL": "아이돌",
           "FUND": "펀딩", "MKT": "시장팝업", "MKT2": "시장팝업"}
    cnt = {}
    for p in Path("data/state/wiki_views").glob("*.json"):
        d = pre.get(p.stem.split("-")[0])
        if d:
            cnt[d] = cnt.get(d, 0) + 1
    return {"쓰는 쪽": sorted(w), "읽는 쪽": sorted(r),
            "캐시 건수": cnt,
            "긁는데 안 읽음": sorted(w - r),
            "**캐시 있는데 안 읽음**":
                {d: n for d, n in cnt.items() if d not in r}}


def axes_files() -> dict:
    """축 파일 --- ``trendaxes.AXF``(id 목록) 대 디스크."""
    r = _safe(lambda: __import__("lab.trendaxes", fromlist=["AXF"]).AXF, {})
    disk = {p.stem for p in Path("data/state").glob("*_axes.json")}
    return {"목록": sorted(r), "목록인데 파일 없음":
            [d for d, f in r.items() if not (Path("data/state") / f"{f}.json").exists()],
            "파일인데 목록 밖": sorted(disk - set(r.values()))}



# ── 행 수 장부(노트 356) ──────────────────────────────────────────────
#
# **위의 셋은 도메인 목록을 견준다. 그것으로는 노트 354를 못 잡았다.**
# MKT2 는 시장팝업이라는 도메인 이름이 양쪽에 다 있었고, 갈라진 것은
# **행**이었다 --- 레코드 647건 중 축에 205건만 들어갔다(68% 버림).
# 일곱 번을 다 운으로 찾았으니 세는 것으로 만든다.
#
# 장부는 도메인마다 두 수를 견준다: 디스크의 레코드 수와 축 파일의 행 수.
# **판정하지 않는다** --- 버리는 데는 옳은 이유가 많다(도서 전자책 153건은
# 노트 35·253, 만화 비일본 611건은 ``ingest/manga_axes.py:118`` 노트 79,
# 아이돌 107건은 ``chodong`` 결측). 표시만 하고 근거를 찾는 것은 사람 몫이다.
#
# **소급 검증**: 이 장부를 노트 354 전에 돌렸으면 시장팝업 68%가 제일 큰
# 자리로 걸린다. 지금 돌리면 넷이 걸리고 넷 다 설명이 있다.
LEDGER = {
    "웹툰": ("webtoon_records", "webtoon_axes", None),
    "애니": ("anime_records", "anime_axes", None),
    "모바일": ("mobile_records", "mobile_axes", None),
    "만화": ("manga_records", "manga_axes", "비일본 --- manga_axes.KEEP_COUNTRY(노트 79)"),
    "세계애니": ("wanime_records", "wanime_axes", None),
    "게임": ("game_records", "game_axes", None),
    "도서": ("book_records", "book_axes", "전자책 --- 노트 35 · 253"),
    "펀딩": ("funding_records", "funding_axes", None),
    "아이돌": ("data/idol_records/*.json", "idol_axes",
             "chodong 결측 --- idolset 은 축 파일이 아니라 레코드를 직접 읽는다(173행)"),
    "시장팝업": ("data/market_records/*.json", "market_axes",
              "단일 행사 아님 · 방문객 없음 --- 노트 354 가 MKT2 44행을 되살렸다"),
}
DROP_WARN = 0.15          # 이만큼 넘게 버리면 표시한다


def _n(spec: str):
    if spec.endswith("*.json"):
        return len(list(Path(".").glob(spec)))
    try:
        d = json.loads((Path("data/state") / f"{spec}.json").read_text())
        return len(d)
    except Exception:
        return None


def ledger() -> dict:
    """도메인마다 디스크 레코드 수 대 축 행 수."""
    rows, warn = {}, []
    for dom, (rf, af, why) in LEDGER.items():
        nr, na = _n(rf), _n(af)
        if not nr or na is None:
            continue
        drop = 1.0 - na / nr
        rows[dom] = {"레코드": nr, "축": na, "버림": round(drop, 3),
                     "근거": why}
        if drop >= DROP_WARN:
            warn.append("%s %.0f%%(%d→%d)%s" % (dom, 100 * drop, nr, na,
                                                "" if why else " **근거 없음**"))
    return {"장부": rows, "버림 큰 곳": warn,
            "근거 없는 것": [d for d, v in rows.items()
                        if v["버림"] >= DROP_WARN and not v["근거"]]}


def report() -> dict:
    out = {"검색": trend(), "위키": wiki(), "축 파일": axes_files(),
           "장부": ledger()}
    bad = []
    for k in ("검색", "위키"):
        for key, v in out[k].items():
            if key.startswith("**") and v:
                bad.append(f"{k}·{key.strip('*')}: "
                           + (", ".join(v) if isinstance(v, list)
                              else ", ".join(f"{a}({b})" for a, b in v.items())))
    # 장부는 **근거 없는 버림**만 갈라진 곳으로 센다. 근거가 적힌 것은
    # 표에만 남는다 --- 버리는 데는 옳은 이유가 많다.
    for d in out["장부"]["근거 없는 것"]:
        bad.append("장부·근거 없는 버림: %s %.0f%%" % (d, 100 * out["장부"]["장부"][d]["버림"]))
    return {**out, "갈라진 곳": bad,
            "한 줄": ("목록 --- " + " | ".join(bad)) if bad
                    else "목록 --- 갈라진 곳 없음 (장부 %d 도메인)" % len(out["장부"]["장부"])}


if __name__ == "__main__":
    r = report()
    print(r["한 줄"])
    print(json.dumps({k: v for k, v in r.items() if k != "한 줄"},
                     ensure_ascii=False, indent=1))
